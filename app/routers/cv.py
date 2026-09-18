import io
import uuid
from typing import Literal

from docx import Document
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import CVReview, Profile, User
from app.schemas import ComparacionCVOut, CVReviewOut
from app.services.ai_service import comparar_cvs, normalizar_area, review_cv
from app.services.badges_service import check_and_award_badges
from app.services.cv_storage import MIME_POR_EXTENSION, guardar_cv

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


def _leer_archivo(archivo: UploadFile) -> tuple[bytes, str]:
    """Valida la extension y devuelve (bytes, extension) sin la IA todavia."""
    nombre = (archivo.filename or "").lower()
    if nombre.endswith(".pdf"):
        ext = "pdf"
    elif nombre.endswith(".docx"):
        ext = "docx"
    else:
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Subi un archivo .pdf o .docx (Word antiguo .doc no esta soportado)",
        )
    return archivo.file.read(), ext


def _extraer_texto(contenido: bytes, ext: str) -> str:
    return _extraer_texto_pdf(contenido) if ext == "pdf" else _extraer_texto_docx(contenido)


def _actualizar_perfil_desde_cv(db: Session, user_id, datos: dict) -> Profile | None:
    """UC-07: si la IA detecto edad/telefono/ciudad/area_formacion en el CV, los
    guarda en el Profile (sin pisar campos existentes con datos vacios/null)."""
    campos = {k: v for k, v in (datos or {}).items() if k in ("edad", "telefono", "ciudad", "area_formacion") and v}
    if "area_formacion" in campos:
        # "Otro" es una categoria valida para el feedback de CV, pero ninguna
        # vacante real la usa (ver AREAS en el panel/app): si la dejamos pasar
        # pisaria un sector_interes que si tiene matches.
        area_normalizada = normalizar_area(campos["area_formacion"])
        if area_normalizada is None or area_normalizada == "Otro":
            del campos["area_formacion"]
        else:
            campos["area_formacion"] = area_normalizada
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
    """UC-07/07B. Acepta el CV/pitch como texto o como archivo PDF/Word (uno de los dos).
    Si es archivo, ademas de analizarlo con IA se guarda el original en disco
    para que la empresa pueda verlo despues desde la lista de postulantes."""
    archivo_bytes: bytes | None = None
    archivo_ext: str | None = None
    if archivo is not None:
        archivo_bytes, archivo_ext = _leer_archivo(archivo)
        contenido = _extraer_texto(archivo_bytes, archivo_ext)
    elif texto:
        contenido = texto
    else:
        raise HTTPException(status_code=400, detail="Envia 'texto' o 'archivo' (PDF o Word)")

    if not contenido:
        raise HTTPException(status_code=400, detail="El CV/pitch esta vacio")

    feedback = review_cv(modo, contenido)

    # El id se genera aca (no se deja el default de la columna) porque
    # guardar_cv() lo necesita para nombrar el archivo, y el default de
    # SQLAlchemy recien se aplica al hacer flush/commit.
    review = CVReview(
        id=uuid.uuid4(),
        user_id=current_user.id,
        modo=modo,
        feedback_json=feedback,
        texto_cv=contenido,
    )
    if archivo_bytes is not None and archivo_ext is not None:
        review.archivo_nombre = archivo.filename
        review.archivo_mime = MIME_POR_EXTENSION[archivo_ext]
        review.archivo_path = guardar_cv(review.id, archivo_ext, archivo_bytes)
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
        archivo_nombre=review.archivo_nombre,
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


@router.get("/comparacion", response_model=ComparacionCVOut)
def comparacion(
    modo: Literal["tradicional", "freelance"],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compara las dos versiones mas recientes del CV/pitch del mismo modo y
    devuelve que mejoro respecto a la anterior. Solo tiene sentido cuando el
    usuario ya reviso su CV al menos dos veces."""
    reviews = (
        db.query(CVReview)
        .filter(CVReview.user_id == current_user.id, CVReview.modo == modo)
        .order_by(desc(CVReview.fecha))
        .limit(2)
        .all()
    )
    if len(reviews) < 2:
        return ComparacionCVOut(
            hay_comparacion=False,
            mensaje=(
                "Todavia no tenes una version anterior de tu CV en este modo para comparar. "
                "Subi una nueva version mas adelante y te mostramos que mejoraste."
            ),
        )

    actual, anterior = reviews[0], reviews[1]
    resultado = comparar_cvs(
        anterior={"texto": anterior.texto_cv, "feedback": anterior.feedback_json},
        actual={"texto": actual.texto_cv, "feedback": actual.feedback_json},
    )
    return ComparacionCVOut(
        hay_comparacion=True,
        fecha_anterior=anterior.fecha,
        fecha_actual=actual.fecha,
        resumen=resultado.get("resumen"),
        mejoras=resultado.get("mejoras", []),
        pendientes=resultado.get("pendientes", []),
        nuevas_sugerencias=resultado.get("nuevas_sugerencias", []),
        nota_ia=resultado.get("nota_ia"),
    )
