from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/wellbeing", tags=["wellbeing"])

RECURSOS_APOYO = [
    {
        "nombre": "Linea de escucha (ejemplo)",
        "descripcion": "Atencion telefonica gratuita para hablar sobre como te sentis.",
        "contacto": "0800-000-0000",
    },
    {
        "nombre": "Guia de primeros pasos para pedir ayuda profesional",
        "descripcion": "Como encontrar apoyo psicologico accesible cerca de tu zona.",
        "contacto": "Ver guia en la app",
    },
]


@router.get("/recursos-apoyo")
def recursos_apoyo(current_user: User = Depends(get_current_user)):
    return RECURSOS_APOYO
