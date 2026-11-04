"""
Optional bearer token authentication.

Set API_KEY in your environment or .env file to enable auth.
If API_KEY is not set, the server runs open (fine for local use).

Protected routes require:
  Authorization: Bearer <your-api-key>

The dashboard handles this automatically via localStorage.
Proxy routes (/proxy/*) are always protected when API_KEY is set.
The /health endpoint is always public.
"""

import os
import secrets
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer(auto_error=False)

API_KEY = os.getenv("API_KEY", "").strip()


def get_api_key() -> str | None:
    return API_KEY or None


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """FastAPI dependency — call this on any route you want protected."""
    key = get_api_key()
    if not key:
        return  # Auth disabled — open access

    if credentials is None or not secrets.compare_digest(credentials.credentials, key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set Authorization: Bearer <key>",
            headers={"WWW-Authenticate": "Bearer"},
        )
