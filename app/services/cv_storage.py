"""Persistencia en disco de los archivos de CV subidos (UC-07).

El nombre en disco es siempre `{cv_review_id}.{ext}` (nunca el nombre que
mando el usuario), asi que no hay riesgo de path traversal ni de colisiones.
El nombre original se guarda aparte en CVReview.archivo_nombre para mostrarlo
al descargar.
"""
import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "cv"

MIME_POR_EXTENSION = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def guardar_cv(review_id: uuid.UUID, ext: str, contenido: bytes) -> str:
    """Guarda los bytes del CV y devuelve el nombre de archivo (no la ruta completa)
    para guardar en CVReview.archivo_path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"{review_id}.{ext}"
    (UPLOAD_DIR / nombre_archivo).write_bytes(contenido)
    return nombre_archivo


def ruta_cv(nombre_archivo: str) -> Path:
    return UPLOAD_DIR / nombre_archivo
