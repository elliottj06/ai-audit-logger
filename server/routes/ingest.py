from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Any
from server.db import get_db
from server.models import LogEntry

router = APIRouter(prefix="/api/v1")


class LogEntryCreate(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    app_name: Optional[str] = None
    provider: str
    model: str
    prompt: Optional[str] = None
    response: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/log", status_code=201)
def create_log(entry: LogEntryCreate, db: Session = Depends(get_db)):
    db_entry = LogEntry(
        session_id=entry.session_id,
        user_id=entry.user_id,
        app_name=entry.app_name,
        provider=entry.provider,
        model=entry.model,
        prompt=entry.prompt,
        response=entry.response,
        tokens_in=entry.tokens_in,
        tokens_out=entry.tokens_out,
        latency_ms=entry.latency_ms,
        cost_usd=entry.cost_usd,
        tags=entry.tags,
        metadata_=entry.metadata,
        error=entry.error,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return {"id": str(db_entry.id)}
