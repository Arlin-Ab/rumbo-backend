import io
from typing import Literal

from docx import Document
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import CVReview, Profile, User
from app.schemas import CVReviewOut
from app.services.ai_service import review_cv
from app.services.badges_service import check_and_award_badges

router = APIRouter(prefix="/cv", tags=["cv"])


def _extraer_texto_pdf(contenido: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(contenido))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el PDF")
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extraer_texto_docx(contenido: bytes) -> str:
    try:
        documento = Document(io.BytesIO(contenido))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el documento Word (.docx)")
    return "\n".join(p.text for p in documento.paragraphs).strip()


def _extraer_texto_archivo(archivo: UploadFile) -> str:
    nombre = (archivo.filename or "").lower()
    contenido = archivo.file.read()
    if nombre.endswith(".pdf"):
        return _extraer_texto_pdf(contenido)
    if nombre.endswith(".docx"):
        return _extraer_texto_docx(contenido)
    raise HTTPException(
        status_code=400,
        detail="Formato no soportado. Subi un archivo .pdf o .docx (Word antiguo .doc no esta soportado)",
    )


def _actualizar_perfil_desde_cv(db: Session, user_id, datos: dict) -> Profile | None:
    """UC-07: si la IA detecto edad/telefono/ciudad/area_formacion en el CV, los
    guarda en el Profile (sin pisar campos existentes con datos vacios/null)."""
    campos = {k: v for k, v in (datos or {}).items() if k in ("edad", "telefono", "ciudad", "area_formacion") and v}
    if not campos:
        return None

    perfil = db.get(Profile, user_id)
    if perfil is None:
        perfil = Profile(user_id=user_id)
        db.add(perfil)

    for campo, valor in campos.items():
        setattr(perfil, campo, valor)

    db.commit()
    db.refresh(perfil)
    return perfil


@router.post("/review", response_model=CVReviewOut)
def cv_review(
    modo: Literal["tradicional", "freelance"] = Form(...),
    texto: str | None = Form(None),
    archivo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """UC-07/07B. Acepta el CV/pitch como texto o como archivo PDF/Word (uno de los dos)."""
    if archivo is not None:
        contenido = _extraer_texto_archivo(archivo)
    elif texto:
        contenido = texto
    else:
        raise HTTPException(status_code=400, detail="Envia 'texto' o 'archivo' (PDF o Word)")

    if not contenido:
        raise HTTPException(status_code=400, detail="El CV/pitch esta vacio")

    feedback = review_cv(modo, contenido)

    review = CVReview(user_id=current_user.id, modo=modo, feedback_json=feedback)
    db.add(review)
    db.commit()
    db.refresh(review)

    check_and_award_badges(db, current_user.id)
    perfil_actualizado = _actualizar_perfil_desde_cv(db, current_user.id, feedback.get("datos_extraidos"))

    return CVReviewOut(
        id=review.id,
        modo=review.modo,
        fecha=review.fecha,
        feedback_json=review.feedback_json,
        perfil_actualizado=perfil_actualizado,
    )


@router.get("/reviews", response_model=list[CVReviewOut])
def listar_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CVReview)
        .filter(CVReview.user_id == current_user.id)
        .order_by(desc(CVReview.fecha))
        .all()
    )
