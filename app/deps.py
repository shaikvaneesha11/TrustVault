from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LoginSession, User
from app.security import hash_token


def get_current_user(session: str | None = Cookie(default=None),
                     db: Session = Depends(get_db)) -> User:
    if not session:
        raise HTTPException(401, "Not logged in")
    row = db.get(LoginSession, hash_token(session))
    if row is None or row.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(401, "Not logged in")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Not logged in")
    return user


def require_role(*roles):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Not allowed")
        return user
    return checker
