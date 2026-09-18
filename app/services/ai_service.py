"""Unico modulo del backend que llama a internet (API de Groq).

Si la llamada falla o tarda demasiado (mala señal en la demo), cae a una
respuesta pre-generada guardada en app/fixtures/*.json — "modo demo offline".
"""
import json
from pathlib import Path

import httpx

from app.config import settings

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Mismo vocabulario que Vacante.area (ver app/seed.py) para que el area que la
# IA detecta en un CV se pueda cruzar despues con las vacantes disponibles.
AREAS_CONOCIDAS = [
    "Administracion",
    "Diseno grafico",
    "Marketing digital",
    "Desarrollo web",
    "Atencion al cliente",
    "Otro",
]


def _load_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def call_ai_text(prompt: str) -> str | None:
    """Llama al modelo y devuelve texto plano, o None si falla/no hay API key."""
    if not settings.groq_api_key:
        return None
    try:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.ai_model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def review_cv(modo: str, texto: str) -> dict:
    areas = ", ".join(f"'{a}'" for a in AREAS_CONOCIDAS)
    prompt = (
        f"Actua como coach de empleabilidad juvenil en modo '{modo}'. "
        f"Revisa el siguiente CV/perfil y responde SOLO en JSON con las claves "
        f"'resumen', 'fortalezas' (lista), 'a_mejorar' (lista) y 'datos_extraidos' (objeto). "
        f"'datos_extraidos' debe tener las claves 'edad' (numero o null), 'telefono' (texto o null), "
        f"'ciudad' (texto o null) y 'area_formacion' (una de estas categorias exactas: {areas}, o null). "
        f"Muy importante: en 'datos_extraidos' poné null en cualquier dato que no aparezca explicitamente "
        f"en el texto — nunca inventes datos de contacto.\n\nTexto:\n{texto}"
    )
    raw = call_ai_text(prompt)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"resumen": raw, "fortalezas": [], "a_mejorar": []}

    fallback = _load_fixture("cv_fallback.json")
    return fallback.get(modo, fallback["tradicional"])


def _nombre_idioma(idioma: str) -> str:
    return "ingles" if idioma == "en" else "español"


def start_interview(
    modo: str,
    sector: str | None,
    idioma: str = "es",
    contexto_perfil: str | None = None,
) -> str:
    perfil_txt = f" El candidato/a: {contexto_perfil}." if contexto_perfil else ""
    prompt = (
        f"Actua como entrevistador/a en modo '{modo}' para el sector '{sector or 'general'}'."
        f"{perfil_txt} Responde en {_nombre_idioma(idioma)}. "
        f"Esto es una llamada de voz, no texto: da el primer mensaje de la conversacion en tono natural y breve "
        f"(maximo 2 oraciones cortas), con una sola pregunta, como hablarias en una charla real."
    )
    raw = call_ai_text(prompt)
    if raw:
        return raw

    fallback = _load_fixture("interview_fallback.json")
    return fallback.get(modo, fallback["tradicional"])["mensaje_inicial"]


def finalize_interview(modo: str, historial: list[dict], idioma: str = "es") -> dict:
    """UC-08/08B (cierre). Evalua la simulacion completa y devuelve recomendaciones,
    con la misma forma que review_cv (resumen/fortalezas/a_mejorar) para reusar el
    mismo tipo de pantalla de feedback en el frontend."""
    tipo = "entrevista laboral" if modo == "tradicional" else "negociacion con un cliente freelance"
    contexto = "\n".join(f"{turno['rol']}: {turno['texto']}" for turno in historial)
    prompt = (
        f"Actua como coach de empleabilidad juvenil. A continuacion esta la transcripcion completa de una "
        f"simulacion de {tipo}. Evalua unicamente el desempeño de 'usuario' (no el de 'asistente') y responde "
        f"SOLO en JSON con las claves 'resumen' (parrafo breve), 'fortalezas' (lista) y 'a_mejorar' (lista). "
        f"Responde en {_nombre_idioma(idioma)}.\n\nTranscripcion:\n{contexto}"
    )
    raw = call_ai_text(prompt)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"resumen": raw, "fortalezas": [], "a_mejorar": []}

    fallback = _load_fixture("interview_fallback.json")
    return fallback.get(modo, fallback["tradicional"])["feedback"]


def responder_asistente_institucion(pregunta: str, contexto_json: str) -> str:
    """UC-13 (chatbot de datos): responde preguntas del panel institucion/empresa
    usando SOLO los KPIs y predicciones de ML (regresion lineal) ya calculados,
    para no inventar numeros que no esten respaldados por los datos reales."""
    prompt = (
        "Sos el asistente de datos del panel de Rumbo para instituciones y empresas. "
        "Respondes preguntas sobre cuando conviene publicar una vacante y sobre en que paises "
        "hay mas demanda/postulantes de cierta area, usando UNICAMENTE los datos JSON de abajo "
        "(son KPIs reales y predicciones de un modelo de regresion lineal entrenado sobre el "
        "historial de postulaciones). Nunca inventes numeros que no esten en el JSON. Si la "
        "pregunta no se puede responder con estos datos, decilo con claridad y sugeri que revisen "
        "la seccion 'Demanda y prediccion' del panel. Responde en español, breve y directo "
        "(maximo 4-5 oraciones), citando numeros concretos cuando corresponda.\n\n"
        f"Datos disponibles (JSON):\n{contexto_json}\n\n"
        f"Pregunta: {pregunta}"
    )
    raw = call_ai_text(prompt)
    if raw:
        return raw

    return (
        "No pude conectarme al modelo de IA en este momento (modo sin conexion). "
        "Mientras tanto, podes revisar los mismos datos en las secciones 'KPIs' y "
        "'Demanda y prediccion' del panel."
    )


def continue_interview(modo: str, historial: list[dict], mensaje: str, idioma: str = "es") -> str:
    contexto = "\n".join(f"{turno['rol']}: {turno['texto']}" for turno in historial)
    prompt = (
        f"Continua la simulacion de {'entrevista' if modo == 'tradicional' else 'negociacion con cliente'}. "
        f"Responde en {_nombre_idioma(idioma)}. "
        f"Historial:\n{contexto}\nusuario: {mensaje}\n"
        f"Esto es una llamada de voz, no texto: responde con el siguiente turno de la conversacion en forma breve "
        f"y natural (maximo 2-3 oraciones cortas), una sola intervencion, como hablarias en una charla real."
    )
    raw = call_ai_text(prompt)
    if raw:
        return raw

    fallback = _load_fixture("interview_fallback.json")
    respuestas = fallback.get(modo, fallback["tradicional"])["respuestas"]
    turno_index = min(len([t for t in historial if t["rol"] == "usuario"]), len(respuestas) - 1)
    return respuestas[turno_index]
