from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, UserInterest
from ..repositories import TagRepository
from ..schemas import InterestOut, InterestsIn, UserOut
from ..security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/me/interests", response_model=list[InterestOut])
def get_interests(user: User = Depends(get_current_user)):
    return [InterestOut(tag=i.tag.name, weight=i.weight) for i in user.interests]


@router.put("/me/interests", response_model=list[InterestOut])
def put_interests(data: InterestsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """FR-02: анкета інтересів замінює профіль повністю (PUT)."""
    tags = TagRepository(db)
    weights: dict[int, float] = {}
    for item in data.interests:
        weights[tags.get_or_create(item.tag).tag_id] = item.weight
    user.interests.clear()
    db.flush()
    user.interests.extend(UserInterest(user_id=user.user_id, tag_id=t, weight=w) for t, w in weights.items())
    db.commit()
    db.refresh(user)
    return [InterestOut(tag=i.tag.name, weight=i.weight) for i in user.interests]


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """NFR-05: видалення облікового запису; персональні дані видаляються каскадно."""
    db.delete(user)
    db.commit()
