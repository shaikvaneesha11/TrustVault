from fastapi import FastAPI

app = FastAPI(title="TrustVault")


@app.get("/")
def home():
    return {"message": "TrustVault is running"}


@app.get("/health")
def health():
    return {"status": "ok"}