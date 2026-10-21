from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
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