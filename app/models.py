import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid
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

    user: Mapped["User"] = relationship(back_populates="profile")


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
