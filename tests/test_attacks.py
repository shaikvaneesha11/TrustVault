import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import AuditLog

PASSWORD = "StrongPass123"


def make_user(role):
    client = TestClient(app)
    email = f"{role}-{uuid.uuid4().hex[:8]}@test.example"
    r = client.post("/auth/register", json={
        "email": email, "name": role, "password": PASSWORD, "role": role})
    assert r.status_code == 201
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    return client, email, client.get("/auth/me").json()["id"]


def upload(client, content=b"secret text", filename="a.txt"):
    r = client.post("/documents", data={"title": "Secret"},
                    files={"file": (filename, content, "text/plain")})
    assert r.status_code == 201
    return r.json()["id"]


def test_missing_and_forbidden_documents_look_identical():
    owner, _, _ = make_user("owner")
    stranger, _, _ = make_user("viewer")
    doc_id = upload(owner)
    real = stranger.get(f"/documents/{doc_id}/download")
    fake = stranger.get("/documents/99999999/download")
    assert real.status_code == fake.status_code == 404
    assert real.json() == fake.json()


def test_forged_cookie_is_rejected():
    client = TestClient(app)
    client.cookies.set("session", "not-a-real-token")
    assert client.get("/documents").status_code == 401


def test_anonymous_user_gets_401_everywhere():
    client = TestClient(app)
    assert client.get("/documents").status_code == 401
    assert client.get("/documents/1/download").status_code == 401
    assert client.delete("/documents/1").status_code == 401
    assert client.get("/documents/1/permissions").status_code == 401


def test_edit_grant_can_rename_but_not_delete_or_share():
    owner, _, _ = make_user("owner")
    editor, editor_email, _ = make_user("viewer")
    doc_id = upload(owner)
    owner.post(f"/documents/{doc_id}/permissions",
               json={"email": editor_email, "level": "edit"})
    assert editor.patch(f"/documents/{doc_id}",
                        json={"title": "renamed"}).status_code == 200
    assert editor.delete(f"/documents/{doc_id}").status_code == 404
    assert editor.post(f"/documents/{doc_id}/permissions",
                       json={"email": editor_email, "level": "edit"}).status_code == 404


def test_owner_cannot_grant_to_self():
    owner, owner_email, _ = make_user("owner")
    doc_id = upload(owner)
    r = owner.post(f"/documents/{doc_id}/permissions",
                   json={"email": owner_email, "level": "read"})
    assert r.status_code == 404


def test_oversize_and_empty_uploads_are_rejected():
    owner, _, _ = make_user("owner")
    big = owner.post("/documents", data={"title": "big"}, files={
        "file": ("big.txt", b"a" * (5 * 1024 * 1024 + 1), "text/plain")})
    assert big.status_code == 413
    empty = owner.post("/documents", data={"title": "empty"}, files={
        "file": ("empty.txt", b"", "text/plain")})
    assert empty.status_code == 400


def test_filename_cannot_escape():
    owner, _, _ = make_user("owner")
    doc_id = upload(owner, filename="../../evil.txt")
    r = owner.get(f"/documents/{doc_id}/download")
    assert 'filename="evil.txt"' in r.headers["content-disposition"]


def test_search_cannot_widen_access():
    owner, _, _ = make_user("owner")
    stranger, _, _ = make_user("viewer")
    doc_id = upload(owner)
    for query in ("?q=Secret", "?q=%25", "?owner=owner", "?category="):
        ids = [d["id"] for d in stranger.get("/documents" + query).json()]
        assert doc_id not in ids


def test_revoke_with_nothing_to_revoke_is_logged_as_noop():
    owner, _, _ = make_user("owner")
    _, _, viewer_id = make_user("viewer")
    doc_id = upload(owner)
    assert owner.delete(
        f"/documents/{doc_id}/permissions/{viewer_id}").status_code == 200
    with SessionLocal() as db:
        rows = db.scalars(select(AuditLog).where(
            AuditLog.document_id == doc_id, AuditLog.action == "revoke",
            AuditLog.outcome == "noop")).all()
    assert len(rows) == 1