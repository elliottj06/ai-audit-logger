from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class AuditConfig:
    server_url: str = field(default_factory=lambda: os.getenv("AUDIT_SERVER_URL", "http://localhost:8000"))
    app_name: Optional[str] = field(default_factory=lambda: os.getenv("AUDIT_APP_NAME"))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    enabled: bool = field(default_factory=lambda: os.getenv("AUDIT_ENABLED", "true").lower() == "true")
    redact_prompts: bool = field(default_factory=lambda: os.getenv("AUDIT_REDACT_PROMPTS", "false").lower() == "true")
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("AUDIT_API_KEY"))
    timeout: float = 2.0
