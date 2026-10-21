from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from app.models import AuditLog, Document, LoginSession, User
from sqlalchemy.orm import Session

from app.audit import verify_chain, write_audit
from app.db import get_db
from app.deps import require_role
from app.models import AuditLog, Document, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit")
def audit(action: str | None = None, outcome: str | None = None,
          document_id: int | None = None, actor_user_id: int | None = None,
          limit: int = 100, admin: User = Depends(require_role("admin")),
          db: Session = Depends(get_db)):
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if document_id:
        stmt = stmt.where(AuditLog.document_id == document_id)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    rows = db.scalars(stmt.limit(max(1, min(limit, 500)))).all()
    write_audit(db, admin.id, "admin_view_audit", "allowed", None, "")
    return [{"id": r.id, "time": r.created_at, "actor": r.actor_user_id,
             "action": r.action, "outcome": r.outcome,
             "document_id": r.document_id, "detail": r.detail} for r in rows]


@router.get("/permission-changes")
def permission_changes(admin: User = Depends(require_role("admin")),
                       db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).where(
        AuditLog.action.in_(["grant", "revoke"])).order_by(
        AuditLog.id.desc()).limit(200)).all()
    return [{"time": r.created_at, "actor": r.actor_user_id,
             "action": r.action, "outcome": r.outcome,
             "document_id": r.document_id, "detail": r.detail} for r in rows]


@router.get("/verify-chain")
def verify(admin: User = Depends(require_role("admin")),
           db: Session = Depends(get_db)):
    ok, bad_id = verify_chain(db)
    return {"valid": ok, "first_bad_row": bad_id}


@router.get("/alerts")
def alerts(admin: User = Depends(require_role("admin")),
           db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=1)

    def counts(where, minimum):
        return [{"user_id": uid, "count": n} for uid, n in db.execute(
            select(AuditLog.actor_user_id, func.count()).where(
                AuditLog.created_at >= since, *where)
            .group_by(AuditLog.actor_user_id)
            .having(func.count() >= minimum)).all()]

    return {
        "window": "last 1 hour",
        "many_refused_attempts": counts([AuditLog.outcome == "denied"], 3),
        "many_downloads": counts([AuditLog.action == "download",
                                  AuditLog.outcome == "allowed"], 10)}


@router.get("/documents")
def all_documents(admin: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db)):
    # Metadata only. The admin cannot read file contents.
    rows = db.execute(select(Document, User).join(
        User, User.id == Document.owner_id)).all()
    return [{"id": d.id, "title": d.title, "owner": u.email,
             "created_at": d.created_at, "size_bytes": d.size_bytes}
            for d, u in rows]
@router.get("/users")
def list_users(admin: User = Depends(require_role("admin")),
               db: Session = Depends(get_db)):
    rows = db.scalars(select(User).order_by(User.id)).all()
    return [{"id": u.id, "email": u.email, "role": u.role,
             "is_active": u.is_active} for u in rows]


@router.post("/users/{user_id}/deactivate")
def deactivate(user_id: int, admin: User = Depends(require_role("admin")),
               db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(400, "You cannot deactivate yourself")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    target.is_active = False
    # Delete every login this person holds, so they are out immediately.
    db.execute(delete(LoginSession).where(LoginSession.user_id == user_id))
    db.commit()
    write_audit(db, admin.id, "deactivate_user", "allowed", None,
                f"user={user_id}")
    return {"ok": True}


@router.post("/users/{user_id}/activate")
def activate(user_id: int, admin: User = Depends(require_role("admin")),
             db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    target.is_active = True
    db.commit()
    write_audit(db, admin.id, "activate_user", "allowed", None,
                f"user={user_id}")
    return {"ok": True}