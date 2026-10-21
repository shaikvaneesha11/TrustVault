import re
from datetime import date, datetime, time, timedelta, timezone

from fastapi import (APIRouter, Depends, File, Form, HTTPException,
                     Response, UploadFile)
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.access import can_access
from app.audit import write_audit
from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Document, Permission, User

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_BYTES = 5 * 1024 * 1024


def detect_type(data: bytes):
    """Decide the type from the file's content, never from its name."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return None if "\x00" in text else "text/plain"


def clean_filename(name):
    name = (name or "file").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:100] or "file"


def get_allowed_doc(db, user, doc_id, action, label):
    """Load a document, or refuse. Same answer (404) whether it is missing or
    forbidden, so nobody can discover which ids exist. Refusals are audited."""
    doc = db.get(Document, doc_id)
    if doc is None or not can_access(db, user, doc, action):
        write_audit(db, user.id, label, "denied", doc_id, "refused")
        raise HTTPException(404, "Document not found")
    return doc


@router.post("", status_code=201)
def upload(title: str = Form(..., min_length=1, max_length=200),
           category: str = Form("", max_length=100),
           file: UploadFile = File(...),
           user: User = Depends(require_role("owner")),
           db: Session = Depends(get_db)):
    data = file.file.read(MAX_BYTES + 1)
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 5 MB)")
    content_type = detect_type(data)
    if content_type is None:
        raise HTTPException(400, "Only PDF or UTF-8 text files are allowed")
    doc = Document(owner_id=user.id, title=title.strip(),
                   category=category.strip(),
                   filename=clean_filename(file.filename),
                   content_type=content_type, size_bytes=len(data),
                   content=data)
    db.add(doc)
    db.commit()
    write_audit(db, user.id, "upload", "allowed", doc.id,
                f"{doc.filename} {doc.size_bytes} bytes")
    return {"id": doc.id, "title": doc.title}


@router.get("")
def list_documents(q: str | None = None, category: str | None = None,
                   owner: str | None = None,
                   created_from: date | None = None,
                   created_to: date | None = None,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    shared_ids = select(Permission.document_id).where(
        Permission.user_id == user.id)
    stmt = (select(Document, User).join(User, User.id == Document.owner_id)
            .where(or_(Document.owner_id == user.id,
                       Document.id.in_(shared_ids)))
            .order_by(Document.created_at.desc()))
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Document.category.ilike(category))
    if owner:
        stmt = stmt.where(or_(User.name.ilike(f"%{owner}%"),
                              User.email.ilike(f"%{owner}%")))
    if created_from:
        stmt = stmt.where(Document.created_at >= datetime.combine(
            created_from, time.min, tzinfo=timezone.utc))
    if created_to:
        stmt = stmt.where(Document.created_at < datetime.combine(
            created_to + timedelta(days=1), time.min, tzinfo=timezone.utc))
    levels = {p.document_id: p.level for p in db.scalars(
        select(Permission).where(Permission.user_id == user.id))}
    result = []
    for doc, doc_owner in db.execute(stmt).all():
        if not can_access(db, user, doc, "read"):   # the one rule decides
            continue
        result.append({
            "id": doc.id, "title": doc.title, "category": doc.category,
            "filename": doc.filename, "size_bytes": doc.size_bytes,
            "owner": doc_owner.name, "created_at": doc.created_at,
            "your_access": "owner" if doc.owner_id == user.id
            else levels.get(doc.id)})
    return result


@router.get("/{doc_id}/download")
def download(doc_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc = get_allowed_doc(db, user, doc_id, "read", "download")
    write_audit(db, user.id, "download", "allowed", doc.id, doc.filename)
    return Response(
        content=bytes(doc.content), media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"',
                 "X-Content-Type-Options": "nosniff",
                 "Cache-Control": "private, no-store"})


class UpdateIn(BaseModel):
    title: str | None = None
    category: str | None = None


@router.patch("/{doc_id}")
def update(doc_id: int, data: UpdateIn,
           user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc = get_allowed_doc(db, user, doc_id, "edit", "update")
    if data.title is not None:
        if not 1 <= len(data.title.strip()) <= 200:
            raise HTTPException(400, "Title must be 1 to 200 characters")
        doc.title = data.title.strip()
    if data.category is not None:
        doc.category = data.category.strip()[:100]
    db.commit()
    write_audit(db, user.id, "update", "allowed", doc.id, "title/category")
    return {"ok": True}


@router.delete("/{doc_id}")
def delete(doc_id: int, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc = get_allowed_doc(db, user, doc_id, "delete", "delete")
    title = doc.title
    db.delete(doc)
    db.commit()
    write_audit(db, user.id, "delete", "allowed", doc_id, title)
    return {"ok": True}


class ShareIn(BaseModel):
    email: str
    level: str  # read or edit


@router.get("/{doc_id}/permissions")
def list_permissions(doc_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc = get_allowed_doc(db, user, doc_id, "share", "view_permissions")
    rows = db.execute(select(Permission, User).join(
        User, User.id == Permission.user_id).where(
        Permission.document_id == doc.id)).all()
    return [{"user_id": u.id, "email": u.email, "level": p.level}
            for p, u in rows]


@router.post("/{doc_id}/permissions")
def grant(doc_id: int, data: ShareIn,
          user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    if data.level not in ("read", "edit"):
        raise HTTPException(400, "Level must be read or edit")
    doc = get_allowed_doc(db, user, doc_id, "share", "grant")
    target = db.scalar(select(User).where(
        User.email == data.email.strip().lower()))
    if (target is None or not target.is_active or target.id == user.id
            or target.role == "admin"):
        raise HTTPException(404, "User not found")
    perm = db.scalar(select(Permission).where(
        Permission.document_id == doc.id, Permission.user_id == target.id))
    if perm:
        perm.level = data.level
    else:
        db.add(Permission(document_id=doc.id, user_id=target.id,
                          level=data.level, granted_by=user.id))
    db.commit()
    write_audit(db, user.id, "grant", "allowed", doc.id,
                f"user={target.id} level={data.level}")
    return {"ok": True}


@router.delete("/{doc_id}/permissions/{target_user_id}")
def revoke(doc_id: int, target_user_id: int,
           user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc = get_allowed_doc(db, user, doc_id, "share", "revoke")
    perm = db.scalar(select(Permission).where(
        Permission.document_id == doc.id,
        Permission.user_id == target_user_id))
    if perm:
        db.delete(perm)
        db.commit()
    write_audit(db, user.id, "revoke", "allowed", doc.id,
                f"user={target_user_id}")
    return {"ok": True}