from fastapi import FastAPI
from server.routes import ingest, query
from server.db import init_db

app = FastAPI(title="AI Audit Logger", version="0.1.0")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(ingest.router)
app.include_router(query.router)
