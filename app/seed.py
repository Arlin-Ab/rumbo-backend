"""Llena todas las tablas con datos de ejemplo para poder ver la plataforma
con contenido real en vez de una base vacia.

Uso (con el venv activado, desde rumbo-backend):
    python -m app.seed

Advertencia: borra y recrea usuarios/profiles/checkins/cv_reviews/
interview_sessions/badges/mentores/vacantes/postulaciones antes de sembrar —
pensado para una base de desarrollo/demo, no para produccion.
"""
import calendar
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import (
    Badge,
    Checkin,
    CVReview,
    InterviewSession,
    Mentoria,
    MentoriaMensaje,
    MentorProfile,
    Postulacion,
    Profile,
    User,
    Vacante,
)
from app.security import hash_password

DEMO_PASSWORD = "demo12345"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# .test es un TLD reservado (RFC 2606): email-validator/pydantic lo rechaza en
# el login real, asi que los usuarios demo usan .dev para poder loguearse de verdad.
JOVENES = [
    {
        "nombre": "Ana Torres",
        "email": "ana.demo@rumbo.dev",
        "ruta": "tradicional",
        "sector": "Administracion",
        "edad": 22,
    },
    {
        "nombre": "Bruno Lima",
        "email": "bruno.demo@rumbo.dev",
        "ruta": "freelance",
        "sector": "Diseno grafico",
        "edad": 24,
    },
    {
        "nombre": "Camila Rios",
        "email": "camila.demo@rumbo.dev",
        "ruta": "ambas",
        "sector": "Marketing digital",
        "edad": 21,
    },
    {
        "nombre": "Diego Mamani",
        "email": "diego.demo@rumbo.dev",
        "ruta": "freelance",
        "sector": "Desarrollo web",
        "edad": 26,
    },
    {
        "nombre": "Elena Paz",
        "email": "elena.demo@rumbo.dev",
        "ruta": "tradicional",
        "sector": "Atencion al cliente",
        "edad": 19,
    },
]

INSTITUCIONES = [
    {"nombre": "UAGRM - Bienestar Estudiantil", "email": "uagrm.demo@rumbo.dev", "role": "institucion"},
    {"nombre": "TalentoJoven S.A.", "email": "empresa.demo@rumbo.dev", "role": "empresa"},
]

MENTORES = [
    {
        "nombre": "Laura Fernandez",
        "email": "laura.mentor@rumbo.dev",
        "area_expertise": "Desarrollo web",
        "bio": "Desarrolladora full-stack con 6 anios de experiencia, le gusta ayudar a quienes recien empiezan.",
        "disponibilidad": "Martes y jueves por la tarde",
    },
    {
        "nombre": "Roberto Salinas",
        "email": "roberto.mentor@rumbo.dev",
        "area_expertise": "Administracion",
        "bio": "Gerente administrativo con 10 anios liderando equipos de atencion al cliente.",
        "disponibilidad": "Fines de semana",
    },
    {
        "nombre": "Valeria Ortiz",
        "email": "valeria.mentor@rumbo.dev",
        "area_expertise": "Marketing digital",
        "bio": "Especialista en marketing digital para pymes y freelancers.",
        "disponibilidad": "Lunes por la manana",
    },
]

# ---------- Datos sinteticos de vacantes/postulaciones (para el KPI de demanda) ----------
AREAS_VACANTES = ["Administracion", "Diseno grafico", "Marketing digital", "Desarrollo web", "Atencion al cliente"]
PAISES = ["Bolivia", "Peru", "Argentina", "Chile", "Colombia"]

# Peso relativo de postulaciones por mes (indice 0 = enero) por area, a mano,
# para que la demo de prediccion de demanda tenga picos estacionales reconocibles.
ESTACIONALIDAD = {
    "Desarrollo web": [1.6, 1.7, 1.5, 1.0, 0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2],
    "Atencion al cliente": [0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 1.0, 1.0, 1.1, 1.3, 1.7, 1.8],
    "Administracion": [0.9, 1.0, 1.6, 1.2, 1.0, 0.9, 0.9, 1.5, 1.2, 1.0, 0.9, 0.9],
    "Diseno grafico": [0.8, 0.8, 0.9, 0.9, 1.0, 1.0, 1.0, 1.1, 1.6, 1.5, 1.0, 0.9],
    "Marketing digital": [0.8, 0.9, 1.0, 1.2, 1.6, 1.7, 1.1, 0.9, 0.9, 0.9, 1.0, 1.1],
}
FACTOR_PAIS = {"Bolivia": 1.0, "Peru": 1.3, "Argentina": 1.5, "Chile": 1.1, "Colombia": 1.4}
ESCALA_POSTULACIONES = 6


def _cargar_fixture(nombre: str) -> dict:
    with open(FIXTURES_DIR / nombre, encoding="utf-8") as f:
        return json.load(f)


def _wipe_all(db) -> None:
    db.query(Postulacion).delete()
    db.query(Vacante).delete()
    db.query(MentoriaMensaje).delete()
    db.query(Mentoria).delete()
    db.query(MentorProfile).delete()
    db.query(Badge).delete()
    db.query(InterviewSession).delete()
    db.query(CVReview).delete()
    db.query(Checkin).delete()
    db.query(Profile).delete()
    db.query(User).delete()
    db.commit()


def _mes_hace(offset: int) -> tuple[int, int]:
    """(anio, mes) del mes actual menos `offset` meses."""
    hoy = datetime.utcnow()
    total = hoy.year * 12 + (hoy.month - 1) - offset
    return total // 12, total % 12 + 1


def _seed_vacantes_y_postulaciones(db, empresa_id, jovenes_ids: list) -> None:
    """Genera 12 meses de historial sintetico por area/pais con estacionalidad,
    para que la regresion lineal de /institucion/prediccion-demanda tenga
    algo coherente que aprender."""
    hoy = datetime.utcnow()
    for area in AREAS_VACANTES:
        for pais in PAISES:
            for offset in range(11, -1, -1):
                anio, mes = _mes_hace(offset)
                peso = ESTACIONALIDAD[area][mes - 1]
                cantidad = max(1, round(peso * FACTOR_PAIS[pais] * ESCALA_POSTULACIONES + random.randint(-2, 2)))

                vacante = Vacante(
                    empresa_id=empresa_id,
                    titulo=f"Vacante {area} ({pais}) - {mes:02d}/{anio}",
                    area=area,
                    pais=pais,
                    fecha_publicacion=datetime(anio, mes, 1),
                )
                db.add(vacante)
                db.flush()

                dias_en_mes = calendar.monthrange(anio, mes)[1]
                if offset == 0:
                    dias_en_mes = min(dias_en_mes, hoy.day)

                for _ in range(cantidad):
                    dia = random.randint(1, dias_en_mes)
                    db.add(
                        Postulacion(
                            vacante_id=vacante.id,
                            joven_id=random.choice(jovenes_ids),
                            fecha=datetime(anio, mes, dia),
                        )
                    )
    db.commit()


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    cv_fallback = _cargar_fixture("cv_fallback.json")
    interview_fallback = _cargar_fixture("interview_fallback.json")

    db = SessionLocal()
    try:
        _wipe_all(db)

        jovenes_ids = []
        for j in JOVENES:
            user = User(
                nombre=j["nombre"],
                email=j["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                role="joven",
            )
            db.add(user)
            db.flush()  # asigna user.id antes de usarlo en las tablas hijas
            jovenes_ids.append(user.id)

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

        empresa_id = None
        for inst in INSTITUCIONES:
            user = User(
                nombre=inst["nombre"],
                email=inst["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                role=inst["role"],
            )
            db.add(user)
            db.flush()
            if inst["role"] == "empresa":
                empresa_id = user.id

        for m in MENTORES:
            user = User(
                nombre=m["nombre"],
                email=m["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                role="mentor",
            )
            db.add(user)
            db.flush()
            db.add(
                MentorProfile(
                    user_id=user.id,
                    area_expertise=m["area_expertise"],
                    bio=m["bio"],
                    disponibilidad=m["disponibilidad"],
                )
            )

        db.commit()

        _seed_vacantes_y_postulaciones(db, empresa_id, jovenes_ids)
    finally:
        db.close()

    print("Seed completo. Credenciales de prueba (password para todas: " f"{DEMO_PASSWORD}):\n")
    print(f"{'Email':32} {'Rol':12} Nombre")
    for j in JOVENES:
        print(f"{j['email']:32} {'joven':12} {j['nombre']}")
    for inst in INSTITUCIONES:
        print(f"{inst['email']:32} {inst['role']:12} {inst['nombre']}")
    for m in MENTORES:
        print(f"{m['email']:32} {'mentor':12} {m['nombre']}")
    print("\nHistorial sintetico de vacantes/postulaciones sembrado (12 meses x 5 areas x 5 paises).")


if __name__ == "__main__":
    seed()
