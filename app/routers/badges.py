from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Badge, User
from app.schemas import BadgeOut

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("", response_model=list[BadgeOut])
def listar_badges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Badge).filter(Badge.user_id == current_user.id).all()
