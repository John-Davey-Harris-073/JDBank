from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import User


class RedirectToLogin(Exception):
    pass


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise RedirectToLogin()
    return user