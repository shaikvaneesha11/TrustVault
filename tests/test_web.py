from fastapi.testclient import TestClient

from app.main import app


def test_home_page_has_csp_and_no_inline_script():
    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert "<script>" not in r.text


def test_cross_site_write_is_blocked():
    r = TestClient(app).post("/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_same_site_write_is_allowed():
    r = TestClient(app).post("/auth/logout", headers={"Origin": "http://testserver"})
    assert r.status_code == 200