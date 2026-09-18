import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

EXAMPLE_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


# ---------- Auth ----------
class UserRegister(BaseModel):
    nombre: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["joven", "institucion", "empresa", "mentor"] = "joven"
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
    telefono: str | None = None
    ciudad: str | None = None
    # Area detectada por la IA al analizar el CV (ver POST /cv/review).
    area_formacion: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "edad": 22,
                "sector_interes": "Administracion",
                "nivel_experiencia": "sin experiencia",
                "ruta_preferida": "tradicional",
                "telefono": None,
                "ciudad": None,
                "area_formacion": None,
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


# ---------- Experiencia laboral (perfil) ----------
class ExperienciaIn(BaseModel):
    puesto: str
    empresa: str
    fecha_inicio: date
    # None = trabajo actual.
    fecha_fin: date | None = None
    referencia: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "puesto": "Asistente administrativo",
                "empresa": "Comercial Andina",
                "fecha_inicio": "2023-02-01",
                "fecha_fin": None,
                "referencia": "Maria Perez - Supervisora - 700-00000",
            }
        }
    )


class ExperienciaOut(ExperienciaIn):
    id: uuid.UUID

    class Config:
        from_attributes = True


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
    # Si la IA detecto datos de contacto/formacion en el CV, se actualiza el
    # Profile y se devuelve aca para que el frontend no tenga que pedirlo aparte.
    perfil_actualizado: ProfileOut | None = None

    class Config:
        from_attributes = True


# ---------- Interview / Negotiation (UC-08 / UC-08B) ----------
class InterviewStartIn(BaseModel):
    modo: Literal["tradicional", "freelance"]
    sector: str | None = None
    idioma: Literal["es", "en"] = "es"

    model_config = ConfigDict(
        json_schema_extra={"example": {"modo": "tradicional", "sector": "administracion", "idioma": "es"}}
    )


class InterviewStartOut(BaseModel):
    session_id: uuid.UUID
    mensaje_inicial: str


class InterviewMessageIn(BaseModel):
    session_id: uuid.UUID
    mensaje: str
    idioma: Literal["es", "en"] = "es"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"session_id": EXAMPLE_UUID, "mensaje": "Hola, soy nuevo en esto", "idioma": "es"}
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


class InterviewFeedbackOut(BaseModel):
    resumen: str
    fortalezas: list[str]
    a_mejorar: list[str]
    nota_ia: str | None = None


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


# ---------- Mentoreo ----------
class MentorProfileIn(BaseModel):
    area_expertise: str
    bio: str | None = None
    disponibilidad: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_expertise": "Desarrollo web",
                "bio": "5 anios de experiencia como desarrollador full-stack.",
                "disponibilidad": "Sabados por la manana",
            }
        }
    )


class MentorProfileOut(BaseModel):
    user_id: uuid.UUID
    nombre: str
    area_expertise: str
    bio: str | None
    disponibilidad: str | None


class MentoriaSolicitudIn(BaseModel):
    mentor_id: uuid.UUID
    mensaje_inicial: str | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"mentor_id": EXAMPLE_UUID, "mensaje_inicial": "Hola, me gustaria tu ayuda"}}
    )


class MentoriaRespuestaIn(BaseModel):
    estado: Literal["aceptada", "rechazada"]


class MentoriaOut(BaseModel):
    id: uuid.UUID
    mentor_id: uuid.UUID
    mentor_nombre: str
    joven_id: uuid.UUID
    joven_nombre: str
    estado: str
    fecha_solicitud: datetime


class MensajeIn(BaseModel):
    texto: str

    model_config = ConfigDict(json_schema_extra={"example": {"texto": "Hola, gracias por aceptar!"}})


class MensajeOut(BaseModel):
    id: uuid.UUID
    mentoria_id: uuid.UUID
    remitente_id: uuid.UUID
    texto: str
    fecha: datetime

    class Config:
        from_attributes = True


# ---------- Mentoria grupal ----------
class MentoriaGrupalIn(BaseModel):
    titulo: str
    descripcion: str
    cupo_maximo: int = Field(ge=1, le=500)
    meet_link: str
    fecha_hora: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "titulo": "Como armar tu primer CV",
                "descripcion": "Sesion grupal para revisar juntos la estructura de un buen CV.",
                "cupo_maximo": 15,
                "meet_link": "https://meet.google.com/abc-defg-hij",
                "fecha_hora": "2026-10-01T18:00:00",
            }
        }
    )


class MentoriaGrupalOut(BaseModel):
    id: uuid.UUID
    mentor_id: uuid.UUID
    mentor_nombre: str
    titulo: str
    descripcion: str
    cupo_maximo: int
    inscritos: int
    meet_link: str
    fecha_hora: datetime
    ya_inscrito: bool


class InscritoGrupalOut(BaseModel):
    joven_id: uuid.UUID
    nombre: str
    email: EmailStr
    fecha_inscripcion: datetime


# ---------- Vacantes / Postulaciones (KPIs) ----------
TipoEmpleo = Literal["pasantia", "medio_tiempo", "tiempo_completo", "freelance", "temporal"]
Modalidad = Literal["presencial", "remoto", "hibrido"]


class VacanteIn(BaseModel):
    titulo: str
    area: str
    pais: str
    descripcion: str = Field(min_length=1)
    tipo_empleo: TipoEmpleo
    modalidad: Modalidad
    ciudad: str | None = None
    salario: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "titulo": "Desarrollador/a junior",
                "area": "Desarrollo web",
                "pais": "Bolivia",
                "descripcion": "Buscamos alguien con ganas de aprender React y Python para sumarse al equipo.",
                "tipo_empleo": "tiempo_completo",
                "modalidad": "hibrido",
                "ciudad": "Santa Cruz de la Sierra",
                "salario": "Bs 3500 - 4500",
            }
        }
    )


class VacanteUpdate(BaseModel):
    titulo: str | None = None
    area: str | None = None
    pais: str | None = None
    descripcion: str | None = None
    tipo_empleo: TipoEmpleo | None = None
    modalidad: Modalidad | None = None
    ciudad: str | None = None
    salario: str | None = None
    activa: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"titulo": "Desarrollador/a junior (actualizado)", "activa": True}}
    )


class VacanteOut(BaseModel):
    id: uuid.UUID
    titulo: str
    area: str
    pais: str
    descripcion: str | None = None
    tipo_empleo: str | None = None
    modalidad: str | None = None
    ciudad: str | None = None
    salario: str | None = None
    fecha_publicacion: datetime
    activa: bool
    total_postulaciones: int


class PostulacionOut(BaseModel):
    id: uuid.UUID
    vacante_id: uuid.UUID
    fecha: datetime

    class Config:
        from_attributes = True


class PostulanteOut(BaseModel):
    postulacion_id: uuid.UUID
    joven_id: uuid.UUID
    nombre: str
    email: EmailStr
    fecha_postulacion: datetime
    sector_interes: str | None = None
    nivel_experiencia: str | None = None
    ruta_preferida: str | None = None
    ciudad: str | None = None
    experiencia: list[ExperienciaOut] = []


# ---------- KPIs de bienestar (institucion/empresa) ----------
class ResumenKPIsOut(BaseModel):
    usuarios_activos: int
    retencion_30_dias_pct: float | None
    tasa_abandono_pct: float | None
    tiempo_promedio_primera_entrevista_dias: float | None
    tiempo_promedio_primera_practica_freelance_dias: float | None


class BienestarMesOut(BaseModel):
    mes: str
    antes: float
    despues: float


class UsuariosPorRutaOut(BaseModel):
    ruta: str
    usuarios: int


class UsuariosActivosMesOut(BaseModel):
    mes: str
    activos: int


class InstitucionKPIsOut(BaseModel):
    resumen: ResumenKPIsOut
    bienestar_antes_despues: list[BienestarMesOut]
    usuarios_por_ruta: list[UsuariosPorRutaOut]
    usuarios_activos_por_mes: list[UsuariosActivosMesOut]


# ---------- Prediccion de demanda (institucion/empresa) ----------
class DemandaMesOut(BaseModel):
    mes: int
    area: str
    pais: str
    total_postulaciones: int


class PrediccionMesOut(BaseModel):
    mes: int
    postulaciones_esperadas: float


class PrediccionDemandaOut(BaseModel):
    area: str
    pais: str
    prediccion_por_mes: list[PrediccionMesOut]
    mes_recomendado: int
    mensaje: str


# ---------- Asistente de datos (chatbot institucion/empresa) ----------
class AsistenteIn(BaseModel):
    pregunta: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(
        json_schema_extra={"example": {"pregunta": "¿En que pais hay mas postulantes de Marketing digital?"}}
    )


class AsistenteOut(BaseModel):
    respuesta: str
