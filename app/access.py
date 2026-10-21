from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Permission, User

LEVELS = {"read": 1, "edit": 2}


def can_access(db: Session, user: User, doc: Document, action: str) -> bool:
    """The only place that decides if a user may touch a document.
    action is one of: read, edit, delete, share."""
    if user is None or doc is None or not user.is_active:
        return False
    if doc.owner_id == user.id:
        return True                      # the owner can do everything
    if action in ("delete", "share"):
        return False                     # only the owner deletes or shares
    perm = db.scalar(select(Permission).where(
        Permission.document_id == doc.id, Permission.user_id == user.id))
    if perm is None:
        return False                     # no grant, no access (deny by default)
    return LEVELS[perm.level] >= LEVELS.get(action, 99)