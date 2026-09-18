import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # "joven" (app movil), "institucion" o "empresa" (panel web)
    role: Mapped[str] = mapped_column(String(30), default="joven")
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    checkins: Mapped[list["Checkin"]] = relationship(back_populates="user")
    cv_reviews: Mapped[list["CVReview"]] = relationship(back_populates="user")
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="user")
    badges: Mapped[list["Badge"]] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sector_interes: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nivel_experiencia: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # "tradicional" | "freelance" | "ambas"
    ruta_preferida: Mapped[str] = mapped_column(String(20), default="ambas")
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Area detectada por la IA al analizar el CV (distinta de sector_interes,
    # que el usuario declara a mano). Usa el mismo vocabulario que Vacante.area.
    area_formacion: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")


class ExperienciaLaboral(Base):
    __tablename__ = "experiencias_laborales"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    puesto: Mapped[str] = mapped_column(String(120))
    empresa: Mapped[str] = mapped_column(String(120))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    # None = trabajo actual ("hasta la actualidad").
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(300), nullable=True)


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # escala 1 (muy mal) a 5 (muy bien)
    nivel_emocional: Mapped[int] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="checkins")


class CVReview(Base):
    __tablename__ = "cv_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # "tradicional" | "freelance"
    modo: Mapped[str] = mapped_column(String(20))
    feedback_json: Mapped[dict] = mapped_column(JSON)
    # Texto del CV/pitch de esta version (extraido del archivo o pegado a mano).
    # Se guarda para poder comparar una version con la anterior (ver
    # GET /cv/comparacion). Puede ser None en reviews historicas previas a
    # esta funcionalidad.
    texto_cv: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Archivo original (PDF/.docx) si el CV se subio como archivo en vez de
    # texto pegado. archivo_path guarda solo el nombre en disco (ver
    # app/services/cv_storage.py), nunca el nombre que mando el usuario.
    archivo_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archivo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archivo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship(back_populates="cv_reviews")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # "tradicional" (entrevista) | "freelance" (negociacion con cliente)
    modo: Mapped[str] = mapped_column(String(20))
    historial_json: Mapped[list] = mapped_column(JSON, default=list)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="interview_sessions")


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(60))
    fecha_obtenida: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="badges")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(255))


class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    area_expertise: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    disponibilidad: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped["User"] = relationship()


class Mentoria(Base):
    __tablename__ = "mentorias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mentor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    joven_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    # "pendiente" | "aceptada" | "rechazada"
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MentoriaMensaje(Base):
    __tablename__ = "mentoria_mensajes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mentoria_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("mentorias.id"), index=True)
    remitente_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    texto: Mapped[str] = mapped_column(String(2000))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MentoriaGrupal(Base):
    __tablename__ = "mentorias_grupales"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mentor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str] = mapped_column(Text)
    cupo_maximo: Mapped[int] = mapped_column(Integer)
    meet_link: Mapped[str] = mapped_column(String(500))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MentoriaGrupalInscripcion(Base):
    __tablename__ = "mentorias_grupales_inscripciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mentoria_grupal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("mentorias_grupales.id"), index=True)
    joven_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    fecha_inscripcion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Vacante(Base):
    __tablename__ = "vacantes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(150))
    area: Mapped[str] = mapped_column(String(120), index=True)
    pais: Mapped[str] = mapped_column(String(80), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "pasantia" | "medio_tiempo" | "tiempo_completo" | "freelance" | "temporal"
    tipo_empleo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "presencial" | "remoto" | "hibrido"
    modalidad: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    salario: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fecha_publicacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    activa: Mapped[bool] = mapped_column(default=True)


class Postulacion(Base):
    __tablename__ = "postulaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vacante_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("vacantes.id"), index=True)
    joven_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
