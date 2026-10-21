from fastapi import FastAPI

app = FastAPI(title="TrustVault")
from app.auth import router as auth_router
app.include_router(auth_router)
from app.documents import router as documents_router
app.include_router(documents_router)
from app.admin import router as admin_router
app.include_router(admin_router)
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/")
def home():
    return {"message": "TrustVault is running"}


@app.get("/health")
def health():
    return {"status": "ok"}