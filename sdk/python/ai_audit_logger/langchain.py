"""
LangChain callback handler for AI Audit Logger.

Usage:
    from langchain_openai import ChatOpenAI
    from ai_audit_logger.langchain import AuditCallbackHandler

    handler = AuditCallbackHandler(app_name="my-app", user_id="user-123")
    llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])

    response = llm.invoke("Hello!")
    # Call is automatically logged
"""

import time
import json
from typing import Any, Optional, Union
from uuid import UUID

from .client import AuditClient
from .config import AuditConfig

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    raise ImportError(
        "langchain-core is required for the LangChain integration. "
        "Install it with: pip install langchain-core"
    )


class AuditCallbackHandler(BaseCallbackHandler):
    """LangChain callback that logs every LLM call to AI Audit Logger."""

    def __init__(
        self,
        server_url: str = None,
        app_name: str = None,
        user_id: str = None,
        session_id: str = None,
        redact_prompts: bool = False,
        config: AuditConfig = None,
    ):
        super().__init__()
        self._config = config or AuditConfig(
            server_url=server_url or AuditConfig.__dataclass_fields__["server_url"].default_factory(),
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            redact_prompts=redact_prompts,
        )
        self._audit = AuditClient(self._config)
        self._start_times: dict[str, float] = {}
        self._prompts: dict[str, str] = {}

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._start_times[str(run_id)] = time.time()
        if not self._config.redact_prompts:
            self._prompts[str(run_id)] = json.dumps(prompts)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._start_times[str(run_id)] = time.time()
        if not self._config.redact_prompts:
            self._prompts[str(run_id)] = json.dumps(
                [[m.dict() if hasattr(m, "dict") else str(m) for m in batch] for batch in messages]
            )

    def on_llm_end(self, response: LLMResult, run_id: UUID, **kwargs: Any) -> None:
        run_key = str(run_id)
        start = self._start_times.pop(run_key, None)
        prompt = self._prompts.pop(run_key, None)
        latency_ms = (time.time() - start) * 1000 if start else None

        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
        tokens_in = token_usage.get("prompt_tokens") or token_usage.get("input_tokens")
        tokens_out = token_usage.get("completion_tokens") or token_usage.get("output_tokens")
        model = llm_output.get("model_name") or llm_output.get("model") or "unknown"

        response_text = None
        if response.generations:
            gen = response.generations[0][0] if response.generations[0] else None
            if gen:
                response_text = getattr(gen, "text", None) or str(gen)

        self._audit.log(
            provider=self._detect_provider(model),
            model=model,
            prompt=prompt,
            response=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            session_id=self._config.session_id,
            user_id=self._config.user_id,
            app_name=self._config.app_name,
        )

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], run_id: UUID, **kwargs: Any) -> None:
        run_key = str(run_id)
        start = self._start_times.pop(run_key, None)
        self._prompts.pop(run_key, None)
        latency_ms = (time.time() - start) * 1000 if start else None

        self._audit.log(
            provider="unknown",
            model="unknown",
            latency_ms=latency_ms,
            session_id=self._config.session_id,
            user_id=self._config.user_id,
            app_name=self._config.app_name,
            error=str(error),
        )

    def _detect_provider(self, model: str) -> str:
        model_lower = model.lower()
        if any(x in model_lower for x in ["gpt", "o1", "o3", "text-davinci"]):
            return "openai"
        if any(x in model_lower for x in ["claude", "anthropic"]):
            return "anthropic"
        if "gemini" in model_lower:
            return "google"
        return "unknown"
