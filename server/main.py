from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.routes import ingest, query, proxy, settings
from server.db import init_db
from server.auth import get_api_key
import os

app = FastAPI(title="AI Audit Logger", version="0.1.0")

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/auth/status")
def auth_status():
    """Public endpoint — tells the dashboard whether auth is enabled."""
    return {"auth_required": bool(get_api_key())}


@app.get("/")
def dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))


app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(proxy.router)
app.include_router(settings.router)
