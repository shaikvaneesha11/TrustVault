import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import AuditLog

PASSWORD = "StrongPass123"


def make_user(role):
    """Each call makes a brand-new user with their own login, like a separate browser."""
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


def test_stranger_cannot_download():
    owner, _, _ = make_user("owner")
    stranger, _, _ = make_user("viewer")
    doc_id = upload(owner)
    assert stranger.get(f"/documents/{doc_id}/download").status_code == 404


def test_stranger_does_not_see_it_in_list():
    owner, _, _ = make_user("owner")
    stranger, _, _ = make_user("viewer")
    doc_id = upload(owner)
    ids = [d["id"] for d in stranger.get("/documents").json()]
    assert doc_id not in ids


def test_grant_then_revoke_is_immediate():
    owner, _, _ = make_user("owner")
    viewer, viewer_email, viewer_id = make_user("viewer")
    doc_id = upload(owner)
    r = owner.post(f"/documents/{doc_id}/permissions",
                   json={"email": viewer_email, "level": "read"})
    assert r.status_code == 200
    assert viewer.get(f"/documents/{doc_id}/download").status_code == 200
    owner.delete(f"/documents/{doc_id}/permissions/{viewer_id}")
    assert viewer.get(f"/documents/{doc_id}/download").status_code == 404


def test_read_access_cannot_edit_delete_or_share():
    owner, _, _ = make_user("owner")
    viewer, viewer_email, _ = make_user("viewer")
    doc_id = upload(owner)
    owner.post(f"/documents/{doc_id}/permissions",
               json={"email": viewer_email, "level": "read"})
    assert viewer.patch(f"/documents/{doc_id}",
                        json={"title": "hacked"}).status_code == 404
    assert viewer.delete(f"/documents/{doc_id}").status_code == 404
    assert viewer.post(f"/documents/{doc_id}/permissions",
                       json={"email": viewer_email, "level": "edit"}).status_code == 404
    assert owner.get(f"/documents/{doc_id}/download").status_code == 200


def test_logged_out_session_stops_working():
    owner, _, _ = make_user("owner")
    doc_id = upload(owner)
    stolen_cookie = owner.cookies.get("session")
    owner.post("/auth/logout")
    thief = TestClient(app)
    thief.cookies.set("session", stolen_cookie)
    assert thief.get(f"/documents/{doc_id}/download").status_code == 401


def test_viewer_role_cannot_upload():
    viewer, _, _ = make_user("viewer")
    r = viewer.post("/documents", data={"title": "x"},
                    files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 403


def test_fake_pdf_is_rejected():
    owner, _, _ = make_user("owner")
    r = owner.post("/documents", data={"title": "x"},
                   files={"file": ("evil.pdf", b"MZ\x90\x00\x03", "application/pdf")})
    assert r.status_code == 400


def test_refused_attempt_is_in_audit_log():
    owner, _, _ = make_user("owner")
    stranger, _, stranger_id = make_user("viewer")
    doc_id = upload(owner)
    stranger.get(f"/documents/{doc_id}/download")
    with SessionLocal() as db:
        rows = db.scalars(select(AuditLog).where(
            AuditLog.document_id == doc_id,
            AuditLog.actor_user_id == stranger_id,
            AuditLog.outcome == "denied")).all()
    assert len(rows) >= 1