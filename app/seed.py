"""Llena todas las tablas con datos de ejemplo para poder ver la plataforma
con contenido real en vez de una base vacia.

Uso (con el venv activado, desde rumbo-backend):
    python -m app.seed

Advertencia: borra y recrea usuarios/profiles/checkins/cv_reviews/
interview_sessions/badges antes de sembrar — pensado para una base de
desarrollo/demo, no para produccion.
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import Badge, Checkin, CVReview, InterviewSession, Profile, User
from app.security import hash_password

DEMO_PASSWORD = "demo12345"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

JOVENES = [
    {
        "nombre": "Ana Torres",
        "email": "ana.demo@rumbo.test",
        "ruta": "tradicional",
        "sector": "Administracion",
        "edad": 22,
    },
    {
        "nombre": "Bruno Lima",
        "email": "bruno.demo@rumbo.test",
        "ruta": "freelance",
        "sector": "Diseno grafico",
        "edad": 24,
    },
    {
        "nombre": "Camila Rios",
        "email": "camila.demo@rumbo.test",
        "ruta": "ambas",
        "sector": "Marketing digital",
        "edad": 21,
    },
    {
        "nombre": "Diego Mamani",
        "email": "diego.demo@rumbo.test",
        "ruta": "freelance",
        "sector": "Desarrollo web",
        "edad": 26,
    },
    {
        "nombre": "Elena Paz",
        "email": "elena.demo@rumbo.test",
        "ruta": "tradicional",
        "sector": "Atencion al cliente",
        "edad": 19,
    },
]

INSTITUCIONES = [
    {"nombre": "UAGRM - Bienestar Estudiantil", "email": "uagrm.demo@rumbo.test", "role": "institucion"},
    {"nombre": "TalentoJoven S.A.", "email": "empresa.demo@rumbo.test", "role": "empresa"},
]


def _cargar_fixture(nombre: str) -> dict:
    with open(FIXTURES_DIR / nombre, encoding="utf-8") as f:
        return json.load(f)


def _wipe_all(db) -> None:
    db.query(Badge).delete()
    db.query(InterviewSession).delete()
    db.query(CVReview).delete()
    db.query(Checkin).delete()
    db.query(Profile).delete()
    db.query(User).delete()
    db.commit()


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    cv_fallback = _cargar_fixture("cv_fallback.json")
    interview_fallback = _cargar_fixture("interview_fallback.json")

    db = SessionLocal()
    try:
        _wipe_all(db)

        for j in JOVENES:
            user = User(
                nombre=j["nombre"],
                email=j["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                role="joven",
            )
            db.add(user)
            db.flush()  # asigna user.id antes de usarlo en las tablas hijas

            db.add(
                Profile(
                    user_id=user.id,
                    edad=j["edad"],
                    sector_interes=j["sector"],
                    nivel_experiencia="sin experiencia",
                    ruta_preferida=j["ruta"],
                )
            )

            # Checkins de los ultimos 7 dias, con animo variable.
            for dias_atras in range(6, -1, -1):
                db.add(
                    Checkin(
                        user_id=user.id,
                        fecha=datetime.utcnow() - timedelta(days=dias_atras),
                        nivel_emocional=random.randint(2, 5),
                    )
                )

            modo = "freelance" if j["ruta"] == "freelance" else "tradicional"
            db.add(CVReview(user_id=user.id, modo=modo, feedback_json=cv_fallback[modo]))

            historial = [
                {"rol": "asistente", "texto": interview_fallback[modo]["mensaje_inicial"]},
                {"rol": "usuario", "texto": f"Hola, soy {j['nombre'].split()[0]} y estoy buscando en {j['sector']}."},
                {"rol": "asistente", "texto": interview_fallback[modo]["respuestas"][0]},
            ]
            db.add(InterviewSession(user_id=user.id, sector=j["sector"], modo=modo, historial_json=historial))

            for tipo in ("constancia_checkin", "primer_cv_revisado", "primera_practica_entrevista"):
                db.add(Badge(user_id=user.id, tipo=tipo))

        for inst in INSTITUCIONES:
            db.add(
                User(
                    nombre=inst["nombre"],
                    email=inst["email"],
                    password_hash=hash_password(DEMO_PASSWORD),
                    role=inst["role"],
                )
            )

        db.commit()
    finally:
        db.close()

    print("Seed completo. Credenciales de prueba (password para todas: " f"{DEMO_PASSWORD}):\n")
    print(f"{'Email':32} {'Rol':12} Nombre")
    for j in JOVENES:
        print(f"{j['email']:32} {'joven':12} {j['nombre']}")
    for inst in INSTITUCIONES:
        print(f"{inst['email']:32} {inst['role']:12} {inst['nombre']}")


if __name__ == "__main__":
    seed()
