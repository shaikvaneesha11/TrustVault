from fastapi import FastAPI

app = FastAPI(title="TrustVault")
from app.auth import router as auth_router
app.include_router(auth_router)


@app.get("/")
def home():
    return {"message": "TrustVault is running"}


@app.get("/health")
def health():
    return {"status": "ok"}