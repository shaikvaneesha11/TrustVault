import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.db import get_db
from app.deps import get_current_user
from app.models import AuditLog, LoginSession, User
from app.security import hash_password, hash_token, new_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") == "1"
SESSION_HOURS = 8
MAX_FAILS = 5
WINDOW_MINUTES = 15
DUMMY_HASH = hash_password("not-a-real-password")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10, max_length=128)
    role: str = "viewer"


class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    # Anyone can register, but only as owner or viewer. Admins are never self-created.
    if data.role not in ("owner", "viewer"):
        raise HTTPException(400, "Role must be owner or viewer")
    email = data.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, name=data.name.strip(),
                password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    since = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    fails = db.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.action == "login", AuditLog.outcome == "denied",
        AuditLog.detail == f"email={email}", AuditLog.created_at >= since))
    if fails >= MAX_FAILS:
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = db.scalar(select(User).where(User.email == email))
    # Always do the slow password check, even for unknown emails,
    # so response time does not reveal which emails exist.
    ok = verify_password(user.password_hash if user else DUMMY_HASH, data.password)
    if not user or not user.is_active or not ok:
        write_audit(db, user.id if user else None, "login", "denied", None,
                    f"email={email}")
        raise HTTPException(401, "Wrong email or password")
    token = new_token()
    db.add(LoginSession(
        token_hash=hash_token(token), user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)))
    db.commit()
    write_audit(db, user.id, "login", "allowed", None, "")
    response.set_cookie("session", token, httponly=True, secure=COOKIE_SECURE,
                        samesite="lax", max_age=SESSION_HOURS * 3600)
    return {"name": user.name, "role": user.role}


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None),
           db: Session = Depends(get_db)):
    if session:
        row = db.get(LoginSession, hash_token(session))
        if row:
            db.delete(row)
            db.commit()
    response.delete_cookie("session")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}