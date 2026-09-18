"""Prediccion de demanda de postulaciones via regresion lineal (sklearn).

Se entrena "al vuelo" sobre el historial agregado por mes/area/pais que hay
en la base (dataset chico, no justifica persistir/cachear el modelo).
"""
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models import Postulacion, Vacante

MESES = list(range(1, 13))
MINIMO_FILAS_HISTORIAL = 6


def _historial_por_mes(db: Session) -> list[tuple[int, str, str, int]]:
    filas = (
        db.query(
            extract("month", Postulacion.fecha),
            Vacante.area,
            Vacante.pais,
            func.count(Postulacion.id),
        )
        .join(Vacante, Postulacion.vacante_id == Vacante.id)
        .group_by(extract("month", Postulacion.fecha), Vacante.area, Vacante.pais)
        .all()
    )
    return [(int(mes), area, pais, total) for mes, area, pais, total in filas]


def predecir_demanda(db: Session, area: str, pais: str) -> dict | None:
    historial = _historial_por_mes(db)
    # Se entrena solo con el historial del area pedida: cada area tiene su propia
    # estacionalidad, y mezclarlas con las demas en el mismo modelo diluye el pico
    # de cada una (el efecto de "mes" terminaba siendo un promedio entre areas).
    historial_area = [fila for fila in historial if fila[1] == area]
    if len(historial_area) < MINIMO_FILAS_HISTORIAL:
        return None

    paises = sorted({p for _, _, p, _ in historial_area})
    if pais not in paises:
        return None

    encoder = OneHotEncoder(categories=[MESES, paises])
    X = encoder.fit_transform([[mes, p] for mes, _, p, _ in historial_area])
    y = [total for _, _, _, total in historial_area]

    modelo = LinearRegression()
    modelo.fit(X, y)

    X_pred = encoder.transform([[mes, pais] for mes in MESES])
    predicciones = modelo.predict(X_pred)

    prediccion_por_mes = [
        {"mes": mes, "postulaciones_esperadas": round(max(0.0, float(valor)), 1)}
        for mes, valor in zip(MESES, predicciones)
    ]
    mejor = max(prediccion_por_mes, key=lambda r: r["postulaciones_esperadas"])

    return {
        "area": area,
        "pais": pais,
        "prediccion_por_mes": prediccion_por_mes,
        "mes_recomendado": mejor["mes"],
        "mensaje": (
            f"Segun el historial de postulaciones, el mejor momento para publicar una vacante "
            f"de '{area}' en {pais} es el mes {mejor['mes']}."
        ),
    }
