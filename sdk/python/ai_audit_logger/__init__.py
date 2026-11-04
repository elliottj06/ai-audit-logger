from .config import AuditConfig
from .client import AuditClient
from .wrapper import WrappedOpenAI, WrappedAnthropic

_default_config = AuditConfig()
_default_client = AuditClient(_default_config)


def configure(
    server_url: str = None,
    app_name: str = None,
    user_id: str = None,
    session_id: str = None,
    redact_prompts: bool = False,
    enabled: bool = True,
):
    """Configure global defaults for the audit logger."""
    global _default_config, _default_client
    _default_config = AuditConfig(
        server_url=server_url or _default_config.server_url,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        redact_prompts=redact_prompts,
        enabled=enabled,
    )
    _default_client = AuditClient(_default_config)


def wrap(client, config: AuditConfig = None):
    """
    Wrap an OpenAI or Anthropic client to automatically log all LLM calls.

    Usage:
        from openai import OpenAI
        from ai_audit_logger import wrap

        client = wrap(OpenAI())
        # All calls now logged automatically
    """
    cfg = config or _default_config
    audit = AuditClient(cfg)
    class_name = type(client).__name__

    if "OpenAI" in class_name:
        return WrappedOpenAI(client, audit, cfg)
    elif "Anthropic" in class_name:
        return WrappedAnthropic(client, audit, cfg)
    else:
        raise ValueError(f"Unsupported client type: {class_name}. Expected OpenAI or Anthropic.")


__all__ = ["wrap", "configure", "AuditConfig", "AuditClient"]
