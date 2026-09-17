from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Checkin, Profile, User
from app.schemas import CheckinIn, CheckinOut
from app.services.badges_service import check_and_award_badges

router = APIRouter(prefix="/checkin", tags=["checkin"])

NIVEL_BAJO_UMBRAL = 2
RACHA_BAJA_PARA_DERIVACION = 3


def _carga_recomendada(nivel_emocional: int, ruta: str) -> tuple[str, str]:
    """UC-04: ajusta la carga diaria segun el nivel emocional y la ruta."""
    if nivel_emocional <= 2:
        carga = "liviana"
        mensaje = "Hoy vamos con calma: te proponemos solo una actividad breve."
    elif nivel_emocional == 3:
        carga = "moderada"
        mensaje = "Buen animo para avanzar a un ritmo moderado hoy."
    else:
        carga = "completa"
        mensaje = "¡Buena energia! Es un buen dia para avanzar con todas las actividades."

    if ruta == "freelance" and carga == "completa":
        mensaje += " Aprovecha para practicar tu pitch o una negociacion con cliente."
    elif ruta == "tradicional" and carga == "completa":
        mensaje += " Aprovecha para revisar tu CV o practicar una entrevista."

    return carga, mensaje


@router.post("", response_model=CheckinOut)
def crear_checkin(
    payload: CheckinIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, current_user.id)
    ruta = profile.ruta_preferida if profile else "ambas"

    checkin = Checkin(user_id=current_user.id, nivel_emocional=payload.nivel_emocional)
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    carga, mensaje = _carga_recomendada(payload.nivel_emocional, ruta)

    ultimos = (
        db.query(Checkin)
        .filter(Checkin.user_id == current_user.id)
        .order_by(desc(Checkin.fecha))
        .limit(RACHA_BAJA_PARA_DERIVACION)
        .all()
    )
    mostrar_derivacion = len(ultimos) == RACHA_BAJA_PARA_DERIVACION and all(
        c.nivel_emocional <= NIVEL_BAJO_UMBRAL for c in ultimos
    )

    check_and_award_badges(db, current_user.id)

    return CheckinOut(
        id=checkin.id,
        fecha=checkin.fecha,
        nivel_emocional=checkin.nivel_emocional,
        carga_recomendada=carga,
        mensaje=mensaje,
        mostrar_derivacion_apoyo=mostrar_derivacion,
    )


@router.get("/historial", response_model=list[CheckinOut])
def historial_checkin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, current_user.id)
    ruta = profile.ruta_preferida if profile else "ambas"

    checkins = (
        db.query(Checkin).filter(Checkin.user_id == current_user.id).order_by(desc(Checkin.fecha)).all()
    )
    resultado = []
    for c in checkins:
        carga, mensaje = _carga_recomendada(c.nivel_emocional, ruta)
        resultado.append(
            CheckinOut(
                id=c.id,
                fecha=c.fecha,
                nivel_emocional=c.nivel_emocional,
                carga_recomendada=carga,
                mensaje=mensaje,
                mostrar_derivacion_apoyo=False,
            )
        )
    return resultado
