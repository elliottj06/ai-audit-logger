from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from server.db import get_db
from server.models import LogEntry

router = APIRouter(prefix="/api/v1")


@router.get("/logs")
def get_logs(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    user_id: Optional[str] = None,
    app_name: Optional[str] = None,
    session_id: Optional[str] = None,
):
    q = db.query(LogEntry)
    if provider:
        q = q.filter(LogEntry.provider == provider)
    if model:
        q = q.filter(LogEntry.model == model)
    if user_id:
        q = q.filter(LogEntry.user_id == user_id)
    if app_name:
        q = q.filter(LogEntry.app_name == app_name)
    if session_id:
        q = q.filter(LogEntry.session_id == session_id)

    total = q.count()
    entries = q.order_by(desc(LogEntry.timestamp)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "session_id": e.session_id,
                "user_id": e.user_id,
                "app_name": e.app_name,
                "provider": e.provider,
                "model": e.model,
                "prompt": e.prompt,
                "response": e.response,
                "tokens_in": e.tokens_in,
                "tokens_out": e.tokens_out,
                "latency_ms": e.latency_ms,
                "cost_usd": e.cost_usd,
                "tags": e.tags,
                "metadata": e.metadata_,
                "error": e.error,
            }
            for e in entries
        ],
    }


@router.get("/logs/stats")
def get_stats(db: Session = Depends(get_db)):
    total_calls = db.query(func.count(LogEntry.id)).scalar()
    total_cost = db.query(func.sum(LogEntry.cost_usd)).scalar() or 0
    total_tokens_in = db.query(func.sum(LogEntry.tokens_in)).scalar() or 0
    total_tokens_out = db.query(func.sum(LogEntry.tokens_out)).scalar() or 0
    avg_latency = db.query(func.avg(LogEntry.latency_ms)).scalar() or 0

    by_model = (
        db.query(
            LogEntry.model,
            func.count(LogEntry.id).label("calls"),
            func.sum(LogEntry.cost_usd).label("cost"),
        )
        .group_by(LogEntry.model)
        .all()
    )

    return {
        "total_calls": total_calls,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "avg_latency_ms": round(avg_latency, 2),
        "by_model": [
            {"model": r.model, "calls": r.calls, "cost_usd": round(r.cost or 0, 6)}
            for r in by_model
        ],
    }
