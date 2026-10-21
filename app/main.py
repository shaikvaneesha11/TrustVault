from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.admin import router as admin_router
from app.auth import router as auth_router
from app.documents import router as documents_router

app = FastAPI(title="TrustVault")
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(admin_router)

STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

PAGE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


@app.middleware("http")
async def block_cross_site_writes(request: Request, call_next):
    # Extra CSRF defence on top of the SameSite cookie.
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-site request blocked"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "index.html", headers={"Content-Security-Policy": PAGE_CSP})


@app.get("/health")
def health():
    return {"status": "ok"}