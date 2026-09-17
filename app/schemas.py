import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

EXAMPLE_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


# ---------- Auth ----------
class UserRegister(BaseModel):
    nombre: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["joven", "institucion", "empresa"] = "joven"
    # Requerido solo si role != "joven" (ver INSTITUTION_SIGNUP_CODE en el backend).
    codigo_institucional: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Ana Torres",
                "email": "ana.torres@example.com",
                "password": "supersegura123",
                "role": "joven",
                "codigo_institucional": None,
            }
        }
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ana.torres@example.com",
                "password": "supersegura123",
            }
        }
    )


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: uuid.UUID
    nombre: str
    email: EmailStr
    role: str
    fecha_registro: datetime

    class Config:
        from_attributes = True


# ---------- Profile (UC-02) ----------
class ProfileIn(BaseModel):
    edad: int | None = None
    sector_interes: str | None = None
    nivel_experiencia: str | None = None
    ruta_preferida: Literal["tradicional", "freelance", "ambas"] = "ambas"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "edad": 22,
                "sector_interes": "Administracion",
                "nivel_experiencia": "sin experiencia",
                "ruta_preferida": "tradicional",
            }
        }
    )


class ProfileOut(ProfileIn):
    user_id: uuid.UUID

    class Config:
        from_attributes = True


class PlanInicial(BaseModel):
    ruta: str
    recomendaciones: list[str]


# ---------- Checkin (UC-03 / UC-04) ----------
class CheckinIn(BaseModel):
    nivel_emocional: int = Field(ge=1, le=5)

    model_config = ConfigDict(json_schema_extra={"example": {"nivel_emocional": 3}})


class CheckinOut(BaseModel):
    id: uuid.UUID
    fecha: datetime
    nivel_emocional: int
    carga_recomendada: str
    mensaje: str
    mostrar_derivacion_apoyo: bool

    class Config:
        from_attributes = True


# ---------- CV / Pitch (UC-07 / UC-07B) ----------
# El input ya no usa un schema Pydantic: POST /cv/review recibe multipart/form-data
# (modo + texto y/o archivo PDF) para poder aceptar el selector de archivo del UC-07.
class CVReviewOut(BaseModel):
    id: uuid.UUID
    modo: str
    fecha: datetime
    feedback_json: dict

    class Config:
        from_attributes = True


# ---------- Interview / Negotiation (UC-08 / UC-08B) ----------
class InterviewStartIn(BaseModel):
    modo: Literal["tradicional", "freelance"]
    sector: str | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"modo": "tradicional", "sector": "administracion"}}
    )


class InterviewStartOut(BaseModel):
    session_id: uuid.UUID
    mensaje_inicial: str


class InterviewMessageIn(BaseModel):
    session_id: uuid.UUID
    mensaje: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"session_id": EXAMPLE_UUID, "mensaje": "Hola, soy nuevo en esto"}
        }
    )


class InterviewMessageOut(BaseModel):
    session_id: uuid.UUID
    respuesta: str


class InterviewSessionOut(BaseModel):
    id: uuid.UUID
    modo: str
    sector: str | None
    fecha: datetime
    historial_json: list[dict]

    class Config:
        from_attributes = True


# ---------- Badges (UC-11) ----------
class BadgeOut(BaseModel):
    id: uuid.UUID
    tipo: str
    fecha_obtenida: datetime

    class Config:
        from_attributes = True


# ---------- Dashboard (UC-12) ----------
class DashboardOut(BaseModel):
    total_checkins: int
    promedio_emocional: float | None
    total_cv_reviews: int
    total_interview_sessions: int
    badges: list[BadgeOut]
    ultimos_checkins: list[CheckinOut]
