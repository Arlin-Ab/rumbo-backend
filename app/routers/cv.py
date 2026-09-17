import io
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import CVReview, User
from app.schemas import CVReviewOut
from app.services.ai_service import review_cv
from app.services.badges_service import check_and_award_badges

router = APIRouter(prefix="/cv", tags=["cv"])


def _extraer_texto_pdf(archivo: UploadFile) -> str:
    contenido = archivo.file.read()
    try:
        reader = PdfReader(io.BytesIO(contenido))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el PDF")
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


@router.post("/review", response_model=CVReviewOut)
def cv_review(
    modo: Literal["tradicional", "freelance"] = Form(...),
    texto: str | None = Form(None),
    archivo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """UC-07/07B. Acepta el CV/pitch como texto o como archivo PDF (uno de los dos)."""
    if archivo is not None:
        contenido = _extraer_texto_pdf(archivo)
    elif texto:
        contenido = texto
    else:
        raise HTTPException(status_code=400, detail="Envia 'texto' o 'archivo' (PDF)")

    if not contenido:
        raise HTTPException(status_code=400, detail="El CV/pitch esta vacio")

    feedback = review_cv(modo, contenido)

    review = CVReview(user_id=current_user.id, modo=modo, feedback_json=feedback)
    db.add(review)
    db.commit()
    db.refresh(review)

    check_and_award_badges(db, current_user.id)
    return review


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
