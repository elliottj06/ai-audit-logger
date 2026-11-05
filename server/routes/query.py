import csv
import io
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from typing import Optional
from server.db import get_db
from server.models import LogEntry
from server.auth import require_auth

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise HTTPException(400, f"Invalid datetime: {val}")


def _base_query(db, provider, model, user_id, app_name, session_id, since, until):
    q = db.query(LogEntry)
    if provider:    q = q.filter(LogEntry.provider == provider)
    if model:       q = q.filter(LogEntry.model == model)
    if user_id:     q = q.filter(LogEntry.user_id == user_id)
    if app_name:    q = q.filter(LogEntry.app_name == app_name)
    if session_id:  q = q.filter(LogEntry.session_id == session_id)
    if since:       q = q.filter(LogEntry.timestamp >= since)
    if until:       q = q.filter(LogEntry.timestamp <= until)
    return q


def _entry_dict(e) -> dict:
    return {
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
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    q = _base_query(db, provider, model, user_id, app_name, session_id,
                    _parse_dt(since), _parse_dt(until))
    total = q.count()
    entries = q.order_by(desc(LogEntry.timestamp)).offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "limit": limit,
            "entries": [_entry_dict(e) for e in entries]}


@router.get("/logs/stats")
def get_stats(
    db: Session = Depends(get_db),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    user_id: Optional[str] = None,
    app_name: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    q = _base_query(db, provider, model, user_id, app_name, None,
                    _parse_dt(since), _parse_dt(until))

    total_calls    = q.with_entities(func.count(LogEntry.id)).scalar()
    total_cost     = q.with_entities(func.sum(LogEntry.cost_usd)).scalar() or 0
    total_tokens_in  = q.with_entities(func.sum(LogEntry.tokens_in)).scalar() or 0
    total_tokens_out = q.with_entities(func.sum(LogEntry.tokens_out)).scalar() or 0
    avg_latency    = q.with_entities(func.avg(LogEntry.latency_ms)).scalar() or 0

    by_model = (
        q.with_entities(
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


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """List sessions with aggregated stats."""
    q = db.query(
        LogEntry.session_id,
        func.count(LogEntry.id).label("calls"),
        func.sum(LogEntry.cost_usd).label("total_cost"),
        func.sum(LogEntry.tokens_in).label("tokens_in"),
        func.sum(LogEntry.tokens_out).label("tokens_out"),
        func.avg(LogEntry.latency_ms).label("avg_latency"),
        func.min(LogEntry.timestamp).label("first_call"),
        func.max(LogEntry.timestamp).label("last_call"),
        func.count(LogEntry.error).label("errors"),
    ).filter(LogEntry.session_id.isnot(None))

    if since: q = q.filter(LogEntry.timestamp >= _parse_dt(since))
    if until: q = q.filter(LogEntry.timestamp <= _parse_dt(until))

    q = q.group_by(LogEntry.session_id)
    total = q.count()
    rows = q.order_by(desc(func.max(LogEntry.timestamp))).offset(offset).limit(limit).all()

    return {
        "total": total,
        "sessions": [
            {
                "session_id": r.session_id,
                "calls": r.calls,
                "total_cost_usd": round(r.total_cost or 0, 6),
                "tokens_in": r.tokens_in or 0,
                "tokens_out": r.tokens_out or 0,
                "avg_latency_ms": round(r.avg_latency or 0, 1),
                "first_call": r.first_call.isoformat(),
                "last_call": r.last_call.isoformat(),
                "errors": r.errors or 0,
            }
            for r in rows
        ],
    }


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_db)):
    """All calls for a single session, ordered chronologically."""
    entries = (
        db.query(LogEntry)
        .filter(LogEntry.session_id == session_id)
        .order_by(LogEntry.timestamp)
        .all()
    )
    if not entries:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session_id,
        "calls": len(entries),
        "entries": [_entry_dict(e) for e in entries],
    }


@router.get("/logs/timeseries")
def get_timeseries(
    db: Session = Depends(get_db),
    bucket: str = Query("hour", pattern="^(hour|day)$"),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """Returns call counts and cost bucketed by hour or day."""
    q = _base_query(db, provider, model, None, None, None,
                    _parse_dt(since), _parse_dt(until))
    trunc = func.date_trunc(bucket, LogEntry.timestamp)
    rows = (
        q.with_entities(
            trunc.label("bucket"),
            func.count(LogEntry.id).label("calls"),
            func.sum(LogEntry.cost_usd).label("cost"),
            func.sum(LogEntry.tokens_in + LogEntry.tokens_out).label("tokens"),
        )
        .group_by(trunc)
        .order_by(trunc)
        .all()
    )
    return {
        "bucket": bucket,
        "points": [
            {
                "time": r.bucket.isoformat(),
                "calls": r.calls,
                "cost_usd": round(r.cost or 0, 6),
                "tokens": r.tokens or 0,
            }
            for r in rows
        ],
    }


@router.get("/logs/users")
def get_users(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """Top users by call count with aggregated stats."""
    q = db.query(
        LogEntry.user_id,
        func.count(LogEntry.id).label("calls"),
        func.sum(LogEntry.cost_usd).label("total_cost"),
        func.sum(LogEntry.tokens_in).label("tokens_in"),
        func.sum(LogEntry.tokens_out).label("tokens_out"),
        func.avg(LogEntry.latency_ms).label("avg_latency"),
        func.max(LogEntry.timestamp).label("last_call"),
    ).filter(LogEntry.user_id.isnot(None))
    if since: q = q.filter(LogEntry.timestamp >= _parse_dt(since))
    if until: q = q.filter(LogEntry.timestamp <= _parse_dt(until))
    rows = (
        q.group_by(LogEntry.user_id)
        .order_by(desc(func.count(LogEntry.id)))
        .limit(limit)
        .all()
    )
    return {
        "users": [
            {
                "user_id": r.user_id,
                "calls": r.calls,
                "total_cost_usd": round(r.total_cost or 0, 6),
                "tokens_in": r.tokens_in or 0,
                "tokens_out": r.tokens_out or 0,
                "avg_latency_ms": round(r.avg_latency or 0, 1),
                "last_call": r.last_call.isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/logs/apps")
def get_apps(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """Top apps by call count with aggregated stats."""
    q = db.query(
        LogEntry.app_name,
        func.count(LogEntry.id).label("calls"),
        func.sum(LogEntry.cost_usd).label("total_cost"),
        func.sum(LogEntry.tokens_in).label("tokens_in"),
        func.sum(LogEntry.tokens_out).label("tokens_out"),
        func.avg(LogEntry.latency_ms).label("avg_latency"),
        func.max(LogEntry.timestamp).label("last_call"),
    ).filter(LogEntry.app_name.isnot(None))
    if since: q = q.filter(LogEntry.timestamp >= _parse_dt(since))
    if until: q = q.filter(LogEntry.timestamp <= _parse_dt(until))
    rows = (
        q.group_by(LogEntry.app_name)
        .order_by(desc(func.count(LogEntry.id)))
        .limit(limit)
        .all()
    )
    return {
        "apps": [
            {
                "app_name": r.app_name,
                "calls": r.calls,
                "total_cost_usd": round(r.total_cost or 0, 6),
                "tokens_in": r.tokens_in or 0,
                "tokens_out": r.tokens_out or 0,
                "avg_latency_ms": round(r.avg_latency or 0, 1),
                "last_call": r.last_call.isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/budget")
def get_budget(db: Session = Depends(get_db)):
    """Daily and monthly spend vs configured limits."""
    from datetime import date, timedelta
    daily_limit   = float(os.getenv("BUDGET_DAILY_USD",   "0") or 0)
    monthly_limit = float(os.getenv("BUDGET_MONTHLY_USD", "0") or 0)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)

    daily_cost = db.query(func.sum(LogEntry.cost_usd)).filter(
        LogEntry.timestamp >= today
    ).scalar() or 0

    monthly_cost = db.query(func.sum(LogEntry.cost_usd)).filter(
        LogEntry.timestamp >= month_start
    ).scalar() or 0

    return {
        "daily": {
            "cost_usd": round(daily_cost, 6),
            "limit_usd": daily_limit,
            "pct": round(daily_cost / daily_limit * 100, 1) if daily_limit else None,
        },
        "monthly": {
            "cost_usd": round(monthly_cost, 6),
            "limit_usd": monthly_limit,
            "pct": round(monthly_cost / monthly_limit * 100, 1) if monthly_limit else None,
        },
    }


@router.get("/logs/export")
def export_logs(
    db: Session = Depends(get_db),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    user_id: Optional[str] = None,
    app_name: Optional[str] = None,
    session_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    format: str = Query("csv", pattern="^(csv|jsonl)$"),
):
    q = _base_query(db, provider, model, user_id, app_name, session_id,
                    _parse_dt(since), _parse_dt(until))
    entries = q.order_by(desc(LogEntry.timestamp)).all()

    if format == "jsonl":
        import json
        def gen_jsonl():
            for e in entries:
                yield json.dumps(_entry_dict(e)) + "\n"
        return StreamingResponse(gen_jsonl(), media_type="application/x-ndjson",
                                 headers={"Content-Disposition": "attachment; filename=audit_log.jsonl"})

    def gen_csv():
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["id","timestamp","provider","model","app_name","user_id",
                    "session_id","tokens_in","tokens_out","cost_usd","latency_ms","error"])
        yield out.getvalue()
        for e in entries:
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow([str(e.id), e.timestamp.isoformat(), e.provider, e.model,
                        e.app_name, e.user_id, e.session_id, e.tokens_in,
                        e.tokens_out, e.cost_usd, e.latency_ms, e.error])
            yield out.getvalue()

    return StreamingResponse(gen_csv(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=audit_log.csv"})
