from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import CVReview, User
from app.schemas import CVReviewIn, CVReviewOut
from app.services.ai_service import review_cv
from app.services.badges_service import check_and_award_badges

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/review", response_model=CVReviewOut)
def cv_review(
    payload: CVReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = review_cv(payload.modo, payload.texto)

    review = CVReview(user_id=current_user.id, modo=payload.modo, feedback_json=feedback)
    db.add(review)
    db.commit()
    db.refresh(review)

    check_and_award_badges(db, current_user.id)
    return review
