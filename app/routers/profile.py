import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ExperienciaLaboral, Profile, User
from app.schemas import ExperienciaIn, ExperienciaOut, PlanInicial, ProfileIn, ProfileOut

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


def _validar_fechas(payload: ExperienciaIn) -> None:
    if payload.fecha_fin is not None and payload.fecha_fin < payload.fecha_inicio:
        raise HTTPException(status_code=400, detail="La fecha de fin no puede ser anterior a la fecha de inicio")


def _get_experiencia_propia(db: Session, experiencia_id: uuid.UUID, current_user: User) -> ExperienciaLaboral:
    experiencia = db.get(ExperienciaLaboral, experiencia_id)
    if experiencia is None or experiencia.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Experiencia no encontrada")
    return experiencia


@router.get("/experiencia", response_model=list[ExperienciaOut])
def listar_experiencia(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ExperienciaLaboral)
        .filter(ExperienciaLaboral.user_id == current_user.id)
        .order_by(desc(ExperienciaLaboral.fecha_inicio))
        .all()
    )


@router.post("/experiencia", response_model=ExperienciaOut, status_code=201)
def crear_experiencia(
    payload: ExperienciaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validar_fechas(payload)
    experiencia = ExperienciaLaboral(user_id=current_user.id, **payload.model_dump())
    db.add(experiencia)
    db.commit()
    db.refresh(experiencia)
    return experiencia


@router.put("/experiencia/{experiencia_id}", response_model=ExperienciaOut)
def editar_experiencia(
    experiencia_id: uuid.UUID,
    payload: ExperienciaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validar_fechas(payload)
    experiencia = _get_experiencia_propia(db, experiencia_id, current_user)
    for campo, valor in payload.model_dump().items():
        setattr(experiencia, campo, valor)

    db.commit()
    db.refresh(experiencia)
    return experiencia


@router.delete("/experiencia/{experiencia_id}", status_code=204)
def eliminar_experiencia(
    experiencia_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    experiencia = _get_experiencia_propia(db, experiencia_id, current_user)
    db.delete(experiencia)
    db.commit()
