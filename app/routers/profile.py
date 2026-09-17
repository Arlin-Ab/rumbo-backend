from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Profile, User
from app.schemas import PlanInicial, ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])

RECOMENDACIONES_POR_RUTA = {
    "tradicional": [
        "Completa tu CV para recibir feedback con IA",
        "Practica una simulacion de entrevista esta semana",
    ],
    "freelance": [
        "Crea tu pitch/perfil freelance con ayuda de la IA",
        "Practica una negociacion con cliente simulada",
    ],
    "ambas": [
        "Explora ambas rutas: CV tradicional y pitch freelance",
        "Elegi con cual practicar primero segun lo que sientas mas cerca",
    ],
}


@router.get("", response_model=ProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Todavia no completaste tu perfil")
    return profile


@router.post("", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, current_user.id)
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    profile.edad = payload.edad
    profile.sector_interes = payload.sector_interes
    profile.nivel_experiencia = payload.nivel_experiencia
    profile.ruta_preferida = payload.ruta_preferida

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/plan-inicial", response_model=PlanInicial)
def plan_inicial(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, current_user.id)
    ruta = profile.ruta_preferida if profile else "ambas"
    return PlanInicial(ruta=ruta, recomendaciones=RECOMENDACIONES_POR_RUTA.get(ruta, []))
