"""
Manages provider API key configuration.

Priority order (highest to lowest):
  1. Environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY)
  2. server_config.json (set via dashboard)

Keys are NEVER stored in the database or logged.
"""

import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "server_config.json"

ENV_MAP = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

PROVIDERS = ["openai", "anthropic", "gemini"]


def _load() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def _save(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_provider_key(provider: str) -> str | None:
    """Return API key for provider. Env vars take precedence."""
    env_key = ENV_MAP.get(provider)
    if env_key:
        val = os.getenv(env_key)
        if val:
            return val
    config = _load()
    key = config.get("keys", {}).get(provider, "")
    return key or None


def set_provider_key(provider: str, key: str) -> None:
    """Save provider key to config file. Pass empty string to remove."""
    config = _load()
    config.setdefault("keys", {})[provider] = key
    _save(config)


def delete_provider_key(provider: str) -> None:
    config = _load()
    config.get("keys", {}).pop(provider, None)
    _save(config)


def get_all_status() -> dict:
    result = {}
    config = _load()
    for p in PROVIDERS:
        env_key = ENV_MAP.get(p, "")
        from_env = bool(os.getenv(env_key))
        from_file = bool(config.get("keys", {}).get(p))
        key = get_provider_key(p)
        result[p] = {
            "configured": bool(key),
            "source": "env" if from_env else ("config" if from_file else None),
            "masked": f"...{key[-4:]}" if key and len(key) >= 4 else None,
        }
    return result
