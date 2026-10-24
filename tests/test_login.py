import uuid

from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "StrongPass123"


def new_email():
    return f"user-{uuid.uuid4().hex[:8]}@test.example"


def register(client, email, role="viewer"):
    return client.post("/auth/register", json={
        "email": email, "name": "T", "password": PASSWORD, "role": role})


def test_login_works_and_me_returns_user():
    client, email = TestClient(app), new_email()
    assert register(client, email).status_code == 201
    assert client.post("/auth/login", json={
        "email": email, "password": PASSWORD}).status_code == 200
    assert client.get("/auth/me").json()["email"] == email


def test_wrong_password_and_unknown_email_look_the_same():
    client, email = TestClient(app), new_email()
    register(client, email)
    wrong_pw = client.post("/auth/login", json={
        "email": email, "password": "WrongPass999"})
    unknown = client.post("/auth/login", json={
        "email": new_email(), "password": PASSWORD})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_cannot_register_as_admin():
    assert register(TestClient(app), new_email(), "admin").status_code == 400


def test_short_password_rejected():
    r = TestClient(app).post("/auth/register", json={
        "email": new_email(), "name": "T", "password": "short",
        "role": "viewer"})
    assert r.status_code == 422


def test_no_cookie_means_not_logged_in():
    assert TestClient(app).get("/auth/me").status_code == 401


def test_session_dies_after_logout():
    client, email = TestClient(app), new_email()
    register(client, email)
    client.post("/auth/login", json={"email": email, "password": PASSWORD})
    old_cookie = client.cookies.get("session")
    client.post("/auth/logout")
    replay = TestClient(app)
    replay.cookies.set("session", old_cookie)
    assert replay.get("/auth/me").status_code == 401


def test_login_locks_after_repeated_failures():
    client, email = TestClient(app), new_email()
    register(client, email)
    for _ in range(5):
        r = client.post("/auth/login", json={
            "email": email, "password": "WrongPass999"})
        assert r.status_code == 401
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 429

def test_invalid_email_format_rejected():
    for bad in ("notanemail", "a@b", "two@@x.com", "with space@x.com"):
        r = TestClient(app).post("/auth/register", json={
            "email": bad, "name": "T", "password": PASSWORD, "role": "viewer"})
        assert r.status_code in (400, 422)