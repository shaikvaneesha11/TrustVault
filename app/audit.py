import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AuditLog

GENESIS = "0" * 64


def _hash(prev_hash, actor, action, outcome, document_id, detail, created_at):
    when = created_at.astimezone(timezone.utc).isoformat()
    payload = json.dumps(
        [prev_hash, actor, action, outcome, document_id, detail, when])
    return hashlib.sha256(payload.encode()).hexdigest()


def write_audit(db: Session, actor_user_id, action, outcome,
                document_id=None, detail=""):
    # One writer at a time, so two requests cannot extend the chain from the same row.
    db.execute(text("SELECT pg_advisory_xact_lock(7001)"))
    last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev = last.row_hash if last else GENESIS
    now = datetime.now(timezone.utc)
    db.add(AuditLog(
        created_at=now, actor_user_id=actor_user_id, action=action,
        outcome=outcome, document_id=document_id, detail=detail,
        prev_hash=prev,
        row_hash=_hash(prev, actor_user_id, action, outcome,
                       document_id, detail, now)))
    db.commit()


def verify_chain(db: Session):
    prev = GENESIS
    for row in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        expected = _hash(prev, row.actor_user_id, row.action, row.outcome,
                         row.document_id, row.detail, row.created_at)
        if row.prev_hash != prev or row.row_hash != expected:
            return False, row.id
        prev = row.row_hash
    return True, None