"""
Transparent proxy routes — forward requests to AI providers and log them.

Usage (no SDK changes needed):
  OpenAI:    base_url="http://localhost:8000/proxy/openai/v1"
  Anthropic: base_url="http://localhost:8000/proxy/anthropic"
  Gemini:    base_url="http://localhost:8000/proxy/gemini"

Custom headers (optional):
  x-app-name, x-user-id, x-session-id  — tag logs without changing your app logic
"""

import json
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.alerts import check_alerts
from server.auth import require_auth
from server.config_manager import get_provider_key
from server.db import get_db
from server.models import LogEntry

router = APIRouter(prefix="/proxy", dependencies=[Depends(require_auth)])

# Cost per 1M tokens (input, output) in USD
COST_TABLE = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (5.00, 15.00),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1-mini": (3.00, 12.00),
    "o1": (15.00, 60.00),
    "o3-mini": (1.10, 4.40),
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6": (15.00, 75.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (3.50, 10.50),
    "gemini-2.5-pro": (1.25, 10.00),
}


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    lower = model.lower()
    for key, (cost_in, cost_out) in COST_TABLE.items():
        if key in lower:
            return (tokens_in * cost_in + tokens_out * cost_out) / 1_000_000
    return None


def _save_log(db, provider, model, body, response_data, latency_ms, error=None,
              app_name=None, user_id=None, session_id=None):
    tokens_in = tokens_out = None
    response_text = None

    if provider == "openai" and response_data:
        usage = response_data.get("usage", {})
        tokens_in = usage.get("prompt_tokens")
        tokens_out = usage.get("completion_tokens")
        choices = response_data.get("choices", [])
        if choices:
            response_text = choices[0].get("message", {}).get("content")

    elif provider == "anthropic" and response_data:
        usage = response_data.get("usage", {})
        tokens_in = usage.get("input_tokens")
        tokens_out = usage.get("output_tokens")
        content = response_data.get("content", [])
        if content:
            response_text = content[0].get("text")

    elif provider == "gemini" and response_data:
        usage = response_data.get("usageMetadata", {})
        tokens_in = usage.get("promptTokenCount")
        tokens_out = usage.get("candidatesTokenCount")
        candidates = response_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                response_text = parts[0].get("text")

    # Sanitize prompt — never log API keys from headers
    prompt_body = body.get("messages") or body.get("contents") or []

    entry = LogEntry(
        provider=provider,
        model=model,
        prompt=json.dumps(prompt_body),
        response=response_text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        cost_usd=_calc_cost(model, tokens_in or 0, tokens_out or 0) if tokens_in else None,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        error=error,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    check_alerts(db, entry)
    return entry


def _get_meta(request: Request):
    return (
        request.headers.get("x-app-name"),
        request.headers.get("x-user-id"),
        request.headers.get("x-session-id"),
    )


# ── OpenAI ────────────────────────────────────────────────────────────────────

@router.post("/openai/v1/chat/completions")
async def proxy_openai_chat(request: Request, db: Session = Depends(get_db)):
    api_key = get_provider_key("openai") or request.headers.get("x-openai-key")
    if not api_key:
        raise HTTPException(401, detail="No OpenAI API key configured. Add OPENAI_API_KEY to .env or via Settings.")

    body = await request.json()
    model = body.get("model", "unknown")
    app_name, user_id, session_id = _get_meta(request)

    start = time.time()
    response_data = error = None
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            response_data = resp.json()
    except httpx.HTTPStatusError as e:
        error = f"HTTP {e.response.status_code}"
        raise HTTPException(e.response.status_code, detail=e.response.text[:500])
    except Exception as e:
        error = str(e)
        raise HTTPException(502, detail=f"Upstream error: {error}")
    finally:
        _save_log(db, "openai", model, body, response_data, (time.time() - start) * 1000,
                  error, app_name, user_id, session_id)

    return response_data


# ── Anthropic ─────────────────────────────────────────────────────────────────

@router.post("/anthropic/v1/messages")
async def proxy_anthropic(request: Request, db: Session = Depends(get_db)):
    api_key = get_provider_key("anthropic") or request.headers.get("x-anthropic-key")
    if not api_key:
        raise HTTPException(401, detail="No Anthropic API key configured.")

    body = await request.json()
    model = body.get("model", "unknown")
    app_name, user_id, session_id = _get_meta(request)

    start = time.time()
    response_data = error = None
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            response_data = resp.json()
    except httpx.HTTPStatusError as e:
        error = f"HTTP {e.response.status_code}"
        raise HTTPException(e.response.status_code, detail=e.response.text[:500])
    except Exception as e:
        error = str(e)
        raise HTTPException(502, detail=f"Upstream error: {error}")
    finally:
        _save_log(db, "anthropic", model, body, response_data, (time.time() - start) * 1000,
                  error, app_name, user_id, session_id)

    return response_data


# ── Gemini ────────────────────────────────────────────────────────────────────

@router.post("/gemini/v1beta/models/{model_id}:generateContent")
async def proxy_gemini(model_id: str, request: Request, db: Session = Depends(get_db)):
    api_key = get_provider_key("gemini") or request.headers.get("x-gemini-key")
    if not api_key:
        raise HTTPException(401, detail="No Gemini API key configured.")

    body = await request.json()
    app_name, user_id, session_id = _get_meta(request)

    start = time.time()
    response_data = error = None
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
                json=body,
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            response_data = resp.json()
    except httpx.HTTPStatusError as e:
        error = f"HTTP {e.response.status_code}"
        raise HTTPException(e.response.status_code, detail=e.response.text[:500])
    except Exception as e:
        error = str(e)
        raise HTTPException(502, detail=f"Upstream error: {error}")
    finally:
        _save_log(db, "gemini", model_id, body, response_data, (time.time() - start) * 1000,
                  error, app_name, user_id, session_id)

    return response_data
