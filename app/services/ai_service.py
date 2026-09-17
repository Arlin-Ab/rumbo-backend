"""Unico modulo del backend que llama a internet (API de Anthropic).

Si la llamada falla o tarda demasiado (mala señal en la demo), cae a una
respuesta pre-generada guardada en app/fixtures/*.json — "modo demo offline".
"""
import json
from pathlib import Path

from anthropic import Anthropic, APIError, APITimeoutError

from app.config import settings

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

_client: Anthropic | None = None


def _get_client() -> Anthropic | None:
    global _client
    if not settings.anthropic_api_key:
        return None
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key, timeout=15.0)
    return _client


def _load_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def call_ai_text(prompt: str) -> str | None:
    """Llama al modelo y devuelve texto plano, o None si falla/no hay API key."""
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=settings.ai_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except (APIError, APITimeoutError, Exception):
        return None


def review_cv(modo: str, texto: str) -> dict:
    prompt = (
        f"Actua como coach de empleabilidad juvenil en modo '{modo}'. "
        f"Revisa el siguiente CV/perfil y responde SOLO en JSON con las claves "
        f"'resumen', 'fortalezas' (lista), 'a_mejorar' (lista).\n\nTexto:\n{texto}"
    )
    raw = call_ai_text(prompt)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"resumen": raw, "fortalezas": [], "a_mejorar": []}

    fallback = _load_fixture("cv_fallback.json")
    return fallback.get(modo, fallback["tradicional"])


def start_interview(modo: str, sector: str | None) -> str:
    prompt = (
        f"Actua como entrevistador/a en modo '{modo}' para el sector '{sector or 'general'}'. "
        f"Da el primer mensaje de la conversacion, en tono natural, una sola pregunta."
    )
    raw = call_ai_text(prompt)
    if raw:
        return raw

    fallback = _load_fixture("interview_fallback.json")
    return fallback.get(modo, fallback["tradicional"])["mensaje_inicial"]


def continue_interview(modo: str, historial: list[dict], mensaje: str) -> str:
    contexto = "\n".join(f"{turno['rol']}: {turno['texto']}" for turno in historial)
    prompt = (
        f"Continua la simulacion de {'entrevista' if modo == 'tradicional' else 'negociacion con cliente'}. "
        f"Historial:\n{contexto}\nusuario: {mensaje}\n"
        f"Responde con el siguiente turno de la conversacion, una sola intervencion."
    )
    raw = call_ai_text(prompt)
    if raw:
        return raw

    fallback = _load_fixture("interview_fallback.json")
    respuestas = fallback.get(modo, fallback["tradicional"])["respuestas"]
    turno_index = min(len([t for t in historial if t["rol"] == "usuario"]), len(respuestas) - 1)
    return respuestas[turno_index]
