import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import InterviewSession, Profile, User
from app.schemas import (
    InterviewFeedbackOut,
    InterviewMessageIn,
    InterviewMessageOut,
    InterviewSessionOut,
    InterviewStartIn,
    InterviewStartOut,
)
from app.services.ai_service import continue_interview, finalize_interview, start_interview
from app.services.badges_service import check_and_award_badges

router = APIRouter(prefix="/interview", tags=["interview"])


def _contexto_perfil(perfil: Profile | None) -> str | None:
    if perfil is None:
        return None
    partes = []
    if perfil.edad:
        partes.append(f"{perfil.edad} anios")
    if perfil.ciudad:
        partes.append(f"de {perfil.ciudad}")
    if perfil.area_formacion:
        partes.append(f"formacion en {perfil.area_formacion}")
    return ", ".join(partes) if partes else None


@router.post("/start", response_model=InterviewStartOut)
def interview_start(
    payload: InterviewStartIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    perfil = db.get(Profile, current_user.id)
    sector = payload.sector or (perfil.area_formacion if perfil else None) or (perfil.sector_interes if perfil else None)

    mensaje_inicial = start_interview(payload.modo, sector, payload.idioma, _contexto_perfil(perfil))

    session = InterviewSession(
        user_id=current_user.id,
        sector=sector,
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

    respuesta = continue_interview(session.modo, historial, payload.mensaje, payload.idioma)
    historial.append({"rol": "asistente", "texto": respuesta})

    session.historial_json = historial
    db.commit()

    return InterviewMessageOut(session_id=session.id, respuesta=respuesta)


@router.post("/{session_id}/finalizar", response_model=InterviewFeedbackOut)
def interview_finalizar(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(InterviewSession, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")

    feedback = finalize_interview(session.modo, session.historial_json)
    return InterviewFeedbackOut(**feedback)


@router.get("/sessions", response_model=list[InterviewSessionOut])
def listar_sesiones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(desc(InterviewSession.fecha))
        .all()
    )
