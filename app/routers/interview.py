from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import InterviewSession, User
from app.schemas import InterviewMessageIn, InterviewMessageOut, InterviewStartIn, InterviewStartOut
from app.services.ai_service import continue_interview, start_interview
from app.services.badges_service import check_and_award_badges

router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/start", response_model=InterviewStartOut)
def interview_start(
    payload: InterviewStartIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mensaje_inicial = start_interview(payload.modo, payload.sector)

    session = InterviewSession(
        user_id=current_user.id,
        sector=payload.sector,
        modo=payload.modo,
        historial_json=[{"rol": "asistente", "texto": mensaje_inicial}],
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    check_and_award_badges(db, current_user.id)
    return InterviewStartOut(session_id=session.id, mensaje_inicial=mensaje_inicial)


@router.post("/message", response_model=InterviewMessageOut)
def interview_message(
    payload: InterviewMessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(InterviewSession, payload.session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")

    historial = list(session.historial_json)
    historial.append({"rol": "usuario", "texto": payload.mensaje})

    respuesta = continue_interview(session.modo, historial, payload.mensaje)
    historial.append({"rol": "asistente", "texto": respuesta})

    session.historial_json = historial
    db.commit()

    return InterviewMessageOut(session_id=session.id, respuesta=respuesta)
