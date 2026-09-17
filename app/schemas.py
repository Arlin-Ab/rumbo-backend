from datetime import datetime

from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class UserRegister(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    role: str = "joven"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: int
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
    ruta_preferida: str = "ambas"


class ProfileOut(ProfileIn):
    user_id: int

    class Config:
        from_attributes = True


class PlanInicial(BaseModel):
    ruta: str
    recomendaciones: list[str]


# ---------- Checkin (UC-03 / UC-04) ----------
class CheckinIn(BaseModel):
    nivel_emocional: int


class CheckinOut(BaseModel):
    id: int
    fecha: datetime
    nivel_emocional: int
    carga_recomendada: str
    mensaje: str
    mostrar_derivacion_apoyo: bool

    class Config:
        from_attributes = True


# ---------- CV / Pitch (UC-07 / UC-07B) ----------
class CVReviewIn(BaseModel):
    modo: str  # "tradicional" | "freelance"
    texto: str


class CVReviewOut(BaseModel):
    id: int
    modo: str
    fecha: datetime
    feedback_json: dict

    class Config:
        from_attributes = True


# ---------- Interview / Negotiation (UC-08 / UC-08B) ----------
class InterviewStartIn(BaseModel):
    modo: str  # "tradicional" | "freelance"
    sector: str | None = None


class InterviewStartOut(BaseModel):
    session_id: int
    mensaje_inicial: str


class InterviewMessageIn(BaseModel):
    session_id: int
    mensaje: str


class InterviewMessageOut(BaseModel):
    session_id: int
    respuesta: str


# ---------- Badges (UC-11) ----------
class BadgeOut(BaseModel):
    id: int
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
