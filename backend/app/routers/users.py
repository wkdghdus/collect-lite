from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.user import UserResponse
from app.services.users import ensure_demo_annotators

router = APIRouter(tags=["users"])


@router.get("/annotators", response_model=list[UserResponse])
def list_annotators(db: Session = Depends(get_db)):
    annotators = ensure_demo_annotators(db)
    db.commit()
    return [UserResponse.model_validate(u) for u in annotators]
