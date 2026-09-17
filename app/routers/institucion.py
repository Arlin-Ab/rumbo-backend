import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.deps import require_role

router = APIRouter(prefix="/institucion", tags=["institucion"])

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@router.get("/kpis")
def kpis(current_user=Depends(require_role("institucion", "empresa"))):
    """UC-13: devuelve datos de ejemplo con la misma forma que tendrian los datos reales."""
    with open(FIXTURES_DIR / "kpis_mock.json", encoding="utf-8") as f:
        return json.load(f)
