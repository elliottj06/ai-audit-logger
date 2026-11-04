import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from server.db import get_db
from server.models import LogEntry
from server.auth import require_auth

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])


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


@router.get("/logs/export")
def export_logs(
    db: Session = Depends(get_db),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    user_id: Optional[str] = None,
    app_name: Optional[str] = None,
    session_id: Optional[str] = None,
    format: str = Query("csv", pattern="^(csv|jsonl)$"),
):
    """Export logs as CSV or JSONL for compliance reporting."""
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

    entries = q.order_by(desc(LogEntry.timestamp)).all()

    if format == "jsonl":
        import json

        def generate_jsonl():
            for e in entries:
                yield json.dumps({
                    "id": str(e.id),
                    "timestamp": e.timestamp.isoformat(),
                    "provider": e.provider,
                    "model": e.model,
                    "app_name": e.app_name,
                    "user_id": e.user_id,
                    "session_id": e.session_id,
                    "tokens_in": e.tokens_in,
                    "tokens_out": e.tokens_out,
                    "cost_usd": e.cost_usd,
                    "latency_ms": e.latency_ms,
                    "error": e.error,
                }) + "\n"

        return StreamingResponse(
            generate_jsonl(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=audit_log.jsonl"},
        )

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "provider", "model", "app_name", "user_id",
                         "session_id", "tokens_in", "tokens_out", "cost_usd", "latency_ms", "error"])
        yield output.getvalue()
        for e in entries:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([str(e.id), e.timestamp.isoformat(), e.provider, e.model,
                             e.app_name, e.user_id, e.session_id, e.tokens_in, e.tokens_out,
                             e.cost_usd, e.latency_ms, e.error])
            yield output.getvalue()

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
