from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import LoginIn, RefreshIn, RegisterIn, TokenPair
from ..security import get_current_user
from ..services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    """FR-01: реєстрація за e-mail і паролем."""
    return auth.register(db, data, client_ip(request))


@router.post("/login", response_model=TokenPair)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    return auth.login(db, data, client_ip(request))


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    return auth.refresh(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Відкликає всі токени користувача на всіх пристроях."""
    auth.logout_everywhere(db, user, client_ip(request))
