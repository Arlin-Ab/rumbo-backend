import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Postulacion, Vacante
from app.schemas import AsistenteIn, AsistenteOut, DemandaMesOut, InstitucionKPIsOut, PrediccionDemandaOut
from app.services.ai_service import responder_asistente_institucion
from app.services.kpi_service import calcular_kpis
from app.services.ml_service import predecir_demanda

router = APIRouter(prefix="/institucion", tags=["institucion"])


@router.get("/kpis", response_model=InstitucionKPIsOut)
def kpis(db: Session = Depends(get_db), current_user=Depends(require_role("institucion", "empresa"))):
    """UC-13: KPIs de bienestar calculados sobre Checkin/Profile/InterviewSession reales."""
    return calcular_kpis(db)


@router.get("/demanda-historica", response_model=list[DemandaMesOut])
def demanda_historica(
    area: str | None = None,
    pais: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("institucion", "empresa")),
):
    """Serie real (no mock) de postulaciones por mes, agregada de Vacante/Postulacion."""
    query = db.query(
        extract("month", Postulacion.fecha),
        Vacante.area,
        Vacante.pais,
        func.count(Postulacion.id),
    ).join(Vacante, Postulacion.vacante_id == Vacante.id)

    if area:
        query = query.filter(Vacante.area == area)
    if pais:
        query = query.filter(Vacante.pais == pais)

    filas = query.group_by(extract("month", Postulacion.fecha), Vacante.area, Vacante.pais).all()
    return [
        DemandaMesOut(mes=int(mes), area=a, pais=p, total_postulaciones=total) for mes, a, p, total in filas
    ]


@router.get("/prediccion-demanda", response_model=PrediccionDemandaOut)
def prediccion_demanda(
    area: str,
    pais: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("institucion", "empresa")),
):
    """UC-13 (ML): mejor mes para publicar una vacante segun regresion lineal sobre el historico."""
    resultado = predecir_demanda(db, area, pais)
    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="No hay suficientes datos historicos para esa combinacion de area/pais",
        )
    return resultado


def _contexto_analitico(db: Session) -> str:
    """Arma el JSON con KPIs + demanda agregada + predicciones ML (regresion lineal,
    una por cada area/pais con suficiente historial) que se le pasa a la IA como
    unica fuente de verdad para responder preguntas del asistente."""
    kpis = calcular_kpis(db)

    filas = (
        db.query(Vacante.area, Vacante.pais, func.count(Postulacion.id))
        .join(Postulacion, Postulacion.vacante_id == Vacante.id)
        .group_by(Vacante.area, Vacante.pais)
        .all()
    )
    demanda_por_area_y_pais = sorted(
        ({"area": a, "pais": p, "total_postulaciones": t} for a, p, t in filas),
        key=lambda r: r["total_postulaciones"],
        reverse=True,
    )

    areas = sorted({a for a, _, _ in filas})
    paises = sorted({p for _, p, _ in filas})
    mejor_mes_por_area_y_pais = []
    for area in areas:
        for pais in paises:
            resultado = predecir_demanda(db, area, pais)
            if resultado:
                mejor_mes_por_area_y_pais.append(
                    {"area": area, "pais": pais, "mes_recomendado": resultado["mes_recomendado"]}
                )

    return json.dumps(
        {
            "kpis_resumen": kpis["resumen"],
            "demanda_total_por_area_y_pais": demanda_por_area_y_pais,
            "mejor_mes_para_publicar_segun_modelo_ml_por_area_y_pais": mejor_mes_por_area_y_pais,
        },
        ensure_ascii=False,
        default=str,
    )


@router.post("/asistente", response_model=AsistenteOut)
def asistente(
    payload: AsistenteIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("institucion", "empresa")),
):
    """Chatbot del panel: responde en base a los KPIs y las predicciones de ML ya calculadas."""
    contexto = _contexto_analitico(db)
    respuesta = responder_asistente_institucion(payload.pregunta, contexto)
    return AsistenteOut(respuesta=respuesta)
