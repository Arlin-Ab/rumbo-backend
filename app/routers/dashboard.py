from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Badge, Checkin, CVReview, InterviewSession, User
from app.schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_checkins = db.query(func.count(Checkin.id)).filter(Checkin.user_id == current_user.id).scalar() or 0
    promedio_emocional = (
        db.query(func.avg(Checkin.nivel_emocional)).filter(Checkin.user_id == current_user.id).scalar()
    )
    total_cv_reviews = (
        db.query(func.count(CVReview.id)).filter(CVReview.user_id == current_user.id).scalar() or 0
    )
    total_interview_sessions = (
        db.query(func.count(InterviewSession.id))
        .filter(InterviewSession.user_id == current_user.id)
        .scalar()
        or 0
    )
    badges = db.query(Badge).filter(Badge.user_id == current_user.id).all()
    ultimos_checkins = (
        db.query(Checkin)
        .filter(Checkin.user_id == current_user.id)
        .order_by(desc(Checkin.fecha))
        .limit(7)
        .all()
    )

    return DashboardOut(
        total_checkins=total_checkins,
        promedio_emocional=float(promedio_emocional) if promedio_emocional is not None else None,
        total_cv_reviews=total_cv_reviews,
        total_interview_sessions=total_interview_sessions,
        badges=badges,
        ultimos_checkins=[
            {
                "id": c.id,
                "fecha": c.fecha,
                "nivel_emocional": c.nivel_emocional,
                "carga_recomendada": "",
                "mensaje": "",
                "mostrar_derivacion_apoyo": False,
            }
            for c in ultimos_checkins
        ],
    )
