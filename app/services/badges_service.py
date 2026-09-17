import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Badge, Checkin, CVReview, InterviewSession

CHECKIN_STREAK_UMBRAL = 3
CV_REVIEW_UMBRAL = 1
INTERVIEW_UMBRAL = 1


def _has_badge(db: Session, user_id: uuid.UUID, tipo: str) -> bool:
    return db.query(Badge).filter(Badge.user_id == user_id, Badge.tipo == tipo).first() is not None


def _award(db: Session, user_id: uuid.UUID, tipo: str) -> None:
    if not _has_badge(db, user_id, tipo):
        db.add(Badge(user_id=user_id, tipo=tipo))


def check_and_award_badges(db: Session, user_id: uuid.UUID) -> None:
    total_checkins = db.query(func.count(Checkin.id)).filter(Checkin.user_id == user_id).scalar() or 0
    if total_checkins >= CHECKIN_STREAK_UMBRAL:
        _award(db, user_id, "constancia_checkin")

    total_cv = db.query(func.count(CVReview.id)).filter(CVReview.user_id == user_id).scalar() or 0
    if total_cv >= CV_REVIEW_UMBRAL:
        _award(db, user_id, "primer_cv_revisado")

    total_interviews = (
        db.query(func.count(InterviewSession.id)).filter(InterviewSession.user_id == user_id).scalar() or 0
    )
    if total_interviews >= INTERVIEW_UMBRAL:
        _award(db, user_id, "primera_practica_entrevista")

    db.commit()
