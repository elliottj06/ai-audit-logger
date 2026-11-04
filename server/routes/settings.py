from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from server.config_manager import get_all_status, set_provider_key, delete_provider_key
from server.auth import require_auth

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])

ALLOWED_PROVIDERS = {"openai", "anthropic", "gemini"}


class KeyUpdate(BaseModel):
    provider: str
    key: str


@router.get("/settings/providers")
def get_providers():
    """Return masked status of all configured provider keys."""
    return get_all_status()


@router.post("/settings/providers")
def upsert_provider_key(update: KeyUpdate):
    if update.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(400, f"Unknown provider. Must be one of: {', '.join(ALLOWED_PROVIDERS)}")
    if not update.key.strip():
        raise HTTPException(400, "Key cannot be empty.")
    set_provider_key(update.provider, update.key.strip())
    return {"status": "ok", "provider": update.provider}


@router.delete("/settings/providers/{provider}")
def remove_provider_key(provider: str):
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(400, "Unknown provider.")
    delete_provider_key(provider)
    return {"status": "ok"}
