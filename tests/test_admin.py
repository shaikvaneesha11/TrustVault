import uuid

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security import hash_password

PASSWORD = "StrongPass123"


def login(email):
    client = TestClient(app)
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    return client


def make_admin():
    email = f"admin-{uuid.uuid4().hex[:8]}@test.example"
    with SessionLocal() as db:   # admins cannot self-register, so insert directly
        db.add(User(email=email, name="admin", role="admin",
                    password_hash=hash_password(PASSWORD)))
        db.commit()
    return login(email)


def make_user(role):
    email = f"{role}-{uuid.uuid4().hex[:8]}@test.example"
    client = TestClient(app)
    r = client.post("/auth/register", json={
        "email": email, "name": role, "password": PASSWORD, "role": role})
    assert r.status_code == 201
    client = login(email)
    return client, client.get("/auth/me").json()["id"]


def test_non_admins_get_403_and_anonymous_gets_401():
    viewer, _ = make_user("viewer")
    owner, _ = make_user("owner")
    paths = ["/admin/audit", "/admin/alerts", "/admin/verify-chain",
             "/admin/documents", "/admin/users", "/admin/permission-changes"]
    for path in paths:
        assert viewer.get(path).status_code == 403
        assert owner.get(path).status_code == 403
        assert TestClient(app).get(path).status_code == 401


def test_admin_cannot_download_document_contents():
    admin = make_admin()
    owner, _ = make_user("owner")
    r = owner.post("/documents", data={"title": "Private"},
                   files={"file": ("a.txt", b"secret", "text/plain")})
    doc_id = r.json()["id"]
    assert admin.get(f"/documents/{doc_id}/download").status_code == 404


def test_deactivated_user_is_logged_out_immediately():
    admin = make_admin()
    user, user_id = make_user("viewer")
    email = user.get("/auth/me").json()["email"]
    assert user.get("/auth/me").status_code == 200
    assert admin.post(f"/admin/users/{user_id}/deactivate").status_code == 200
    assert user.get("/auth/me").status_code == 401        # old session is dead
    r = TestClient(app).post("/auth/login", json={
        "email": email, "password": PASSWORD})
    assert r.status_code == 401                           # cannot log in again


def test_admin_cannot_deactivate_self():
    admin = make_admin()
    my_id = admin.get("/auth/me").json()["id"]
    assert admin.post(f"/admin/users/{my_id}/deactivate").status_code == 400


def test_audit_chain_is_valid():
    admin = make_admin()
    assert admin.get("/admin/verify-chain").json()["valid"] is True

def test_non_admins_cannot_deactivate_or_activate():
    viewer, viewer_id = make_user("viewer")
    owner, _ = make_user("owner")
    anon = TestClient(app)
    for path in (f"/admin/users/{viewer_id}/deactivate",
                 f"/admin/users/{viewer_id}/activate"):
        assert viewer.post(path).status_code == 403
        assert owner.post(path).status_code == 403
        assert anon.post(path).status_code == 401
    assert viewer.get("/auth/me").status_code == 200