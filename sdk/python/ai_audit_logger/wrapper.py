import time
import json
from typing import Optional
from .config import AuditConfig
from .client import AuditClient

# Cost per 1M tokens (input, output) in USD
COST_TABLE = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (5.00, 15.00),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6": (15.00, 75.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
}


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> Optional[float]:
    model_lower = model.lower()
    for key, (cost_in, cost_out) in COST_TABLE.items():
        if key in model_lower:
            return (tokens_in * cost_in + tokens_out * cost_out) / 1_000_000
    return None


# ── OpenAI wrappers ───────────────────────────────────────────────────────────

class WrappedOpenAI:
    def __init__(self, client, audit: AuditClient, config: AuditConfig):
        self._client = client
        self.chat = WrappedChat(client.chat, audit, config)

    def __getattr__(self, name):
        return getattr(self._client, name)


class WrappedChat:
    def __init__(self, chat, audit: AuditClient, config: AuditConfig):
        self._chat = chat
        self.completions = WrappedCompletions(chat.completions, audit, config)

    def __getattr__(self, name):
        return getattr(self._chat, name)


class WrappedCompletions:
    def __init__(self, completions, audit: AuditClient, config: AuditConfig):
        self._completions = completions
        self._audit = audit
        self._config = config

    def create(self, **kwargs):
        start = time.time()
        error = None
        response = None
        try:
            response = self._completions.create(**kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            latency_ms = (time.time() - start) * 1000
            model = kwargs.get("model", "unknown")
            tokens_in = tokens_out = None
            response_text = None

            if response:
                if hasattr(response, "usage") and response.usage:
                    tokens_in = response.usage.prompt_tokens
                    tokens_out = response.usage.completion_tokens
                if hasattr(response, "choices") and response.choices:
                    response_text = response.choices[0].message.content

            self._audit.log(
                provider="openai",
                model=model,
                prompt=None if self._config.redact_prompts else json.dumps(kwargs.get("messages", [])),
                response=response_text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_usd=_calc_cost(model, tokens_in or 0, tokens_out or 0) if tokens_in else None,
                session_id=self._config.session_id,
                user_id=self._config.user_id,
                app_name=self._config.app_name,
                error=error,
            )

    def __getattr__(self, name):
        return getattr(self._completions, name)


# ── Anthropic wrappers ────────────────────────────────────────────────────────

class WrappedAnthropic:
    def __init__(self, client, audit: AuditClient, config: AuditConfig):
        self._client = client
        self.messages = WrappedAnthropicMessages(client.messages, audit, config)

    def __getattr__(self, name):
        return getattr(self._client, name)


class WrappedAnthropicMessages:
    def __init__(self, messages, audit: AuditClient, config: AuditConfig):
        self._messages = messages
        self._audit = audit
        self._config = config

    def create(self, **kwargs):
        start = time.time()
        error = None
        response = None
        try:
            response = self._messages.create(**kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            latency_ms = (time.time() - start) * 1000
            model = kwargs.get("model", "unknown")
            tokens_in = tokens_out = None
            response_text = None

            if response:
                if hasattr(response, "usage"):
                    tokens_in = response.usage.input_tokens
                    tokens_out = response.usage.output_tokens
                if hasattr(response, "content") and response.content:
                    response_text = response.content[0].text

            self._audit.log(
                provider="anthropic",
                model=model,
                prompt=None if self._config.redact_prompts else json.dumps(kwargs.get("messages", [])),
                response=response_text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_usd=_calc_cost(model, tokens_in or 0, tokens_out or 0) if tokens_in else None,
                session_id=self._config.session_id,
                user_id=self._config.user_id,
                app_name=self._config.app_name,
                error=error,
            )

    def __getattr__(self, name):
        return getattr(self._messages, name)
