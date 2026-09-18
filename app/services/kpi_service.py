"""KPIs de bienestar para el panel de institucion/empresa (UC-13), calculados
sobre datos reales (Checkin/Profile/InterviewSession), sin mocks."""
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Checkin, InterviewSession, Profile, User

MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS_RETENCION = 30
MESES_ACTIVIDAD = 6
ETIQUETAS_RUTA = {"tradicional": "Tradicional", "freelance": "Freelance", "ambas": "Ambas"}


def _mes_hace(offset: int) -> tuple[int, int]:
    """(anio, mes) del mes actual menos `offset` meses."""
    hoy = datetime.utcnow()
    total = hoy.year * 12 + (hoy.month - 1) - offset
    return total // 12, total % 12 + 1


def _promedio_dias(pares: list[tuple[datetime, datetime]]) -> float | None:
    if not pares:
        return None
    dias = [(fin - inicio).total_seconds() / 86400.0 for inicio, fin in pares]
    return round(sum(dias) / len(dias), 1)


def _calcular_resumen(db: Session, corte_30_dias: datetime) -> dict:
    usuarios_activos = (
        db.query(func.count(func.distinct(Checkin.user_id)))
        .join(User, Checkin.user_id == User.id)
        .filter(User.role == "joven", Checkin.fecha >= corte_30_dias)
        .scalar()
        or 0
    )

    elegibles_retencion = (
        db.query(User.id).filter(User.role == "joven", User.fecha_registro <= corte_30_dias).subquery()
    )
    total_elegibles = db.query(func.count()).select_from(elegibles_retencion).scalar() or 0
    retencion_pct = None
    tasa_abandono_pct = None
    if total_elegibles:
        retenidos = (
            db.query(func.count(func.distinct(Checkin.user_id)))
            .filter(Checkin.user_id.in_(db.query(elegibles_retencion.c.id)), Checkin.fecha >= corte_30_dias)
            .scalar()
            or 0
        )
        retencion_pct = round(retenidos / total_elegibles * 100, 1)
        tasa_abandono_pct = round(100 - retencion_pct, 1)

    primeras_entrevistas = (
        db.query(User.fecha_registro, func.min(InterviewSession.fecha))
        .join(InterviewSession, InterviewSession.user_id == User.id)
        .group_by(User.id, User.fecha_registro)
        .all()
    )
    tiempo_primera_entrevista = _promedio_dias(primeras_entrevistas)

    primeras_practicas_freelance = (
        db.query(User.fecha_registro, func.min(InterviewSession.fecha))
        .join(InterviewSession, InterviewSession.user_id == User.id)
        .filter(InterviewSession.modo == "freelance")
        .group_by(User.id, User.fecha_registro)
        .all()
    )
    tiempo_primera_practica_freelance = _promedio_dias(primeras_practicas_freelance)

    return {
        "usuarios_activos": usuarios_activos,
        "retencion_30_dias_pct": retencion_pct,
        "tasa_abandono_pct": tasa_abandono_pct,
        "tiempo_promedio_primera_entrevista_dias": tiempo_primera_entrevista,
        "tiempo_promedio_primera_practica_freelance_dias": tiempo_primera_practica_freelance,
    }


def _calcular_bienestar_antes_despues(db: Session) -> list[dict]:
    checkins = (
        db.query(Checkin.user_id, Checkin.fecha, Checkin.nivel_emocional)
        .join(User, Checkin.user_id == User.id)
        .filter(User.role == "joven")
        .order_by(Checkin.user_id, Checkin.fecha)
        .all()
    )

    por_usuario: dict = {}
    for user_id, fecha, nivel in checkins:
        por_usuario.setdefault(user_id, []).append((fecha, nivel))

    acumulado_por_mes: dict[str, list[tuple[int, int]]] = {}
    for serie in por_usuario.values():
        if len(serie) < 2:
            continue
        antes = serie[0][1]
        despues = serie[-1][1]
        mes_cohorte = serie[0][0].strftime("%Y-%m")
        acumulado_por_mes.setdefault(mes_cohorte, []).append((antes, despues))

    resultado = []
    for mes_key in sorted(acumulado_por_mes):
        valores = acumulado_por_mes[mes_key]
        mes_num = int(mes_key.split("-")[1])
        resultado.append(
            {
                "mes": MESES_ES[mes_num - 1],
                "antes": round(sum(v[0] for v in valores) / len(valores), 1),
                "despues": round(sum(v[1] for v in valores) / len(valores), 1),
            }
        )
    return resultado


def _calcular_usuarios_por_ruta(db: Session) -> list[dict]:
    filas = (
        db.query(Profile.ruta_preferida, func.count(Profile.user_id))
        .join(User, Profile.user_id == User.id)
        .filter(User.role == "joven")
        .group_by(Profile.ruta_preferida)
        .all()
    )
    return [{"ruta": ETIQUETAS_RUTA.get(ruta, ruta), "usuarios": total} for ruta, total in filas]


def _calcular_usuarios_activos_por_mes(db: Session) -> list[dict]:
    resultado = []
    for offset in range(MESES_ACTIVIDAD - 1, -1, -1):
        anio, mes = _mes_hace(offset)
        inicio = datetime(anio, mes, 1)
        fin = datetime(anio + 1, 1, 1) if mes == 12 else datetime(anio, mes + 1, 1)

        activos = (
            db.query(func.count(func.distinct(Checkin.user_id)))
            .join(User, Checkin.user_id == User.id)
            .filter(User.role == "joven", Checkin.fecha >= inicio, Checkin.fecha < fin)
            .scalar()
            or 0
        )
        resultado.append({"mes": MESES_ES[mes - 1], "activos": activos})
    return resultado


def calcular_kpis(db: Session) -> dict:
    corte_30_dias = datetime.utcnow() - timedelta(days=DIAS_RETENCION)
    return {
        "resumen": _calcular_resumen(db, corte_30_dias),
        "bienestar_antes_despues": _calcular_bienestar_antes_despues(db),
        "usuarios_por_ruta": _calcular_usuarios_por_ruta(db),
        "usuarios_activos_por_mes": _calcular_usuarios_activos_por_mes(db),
    }
