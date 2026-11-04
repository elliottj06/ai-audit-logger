"""
Basic usage example for AI Audit Logger.

This script simulates LLM calls without needing real API keys,
so you can see the logger working immediately.

To run:
    1. Start the server:  docker compose up -d
    2. Install the SDK:   pip install httpx
    3. Run this script:   python examples/basic_usage.py
    4. Check the logs:    python cli/main.py tail
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sdk", "python"))

from ai_audit_logger import configure
from ai_audit_logger.client import AuditClient
from ai_audit_logger.config import AuditConfig

# Configure the logger
config = AuditConfig(
    server_url="http://localhost:8000",
    app_name="example-app",
    user_id="demo-user",
)
client = AuditClient(config)

print("Sending example log entries to AI Audit Logger...\n")

# Simulate an OpenAI GPT-4o call
client._send(
    provider="openai",
    model="gpt-4o",
    prompt='[{"role": "user", "content": "Summarize the key benefits of audit logging for AI systems."}]',
    response="Audit logging for AI systems provides traceability, cost visibility, compliance evidence, and the ability to debug unexpected model behavior after the fact.",
    tokens_in=18,
    tokens_out=32,
    latency_ms=843.2,
    cost_usd=0.000570,
    app_name="example-app",
    user_id="demo-user",
    session_id="session-001",
)
print("✓ Logged: openai / gpt-4o")

# Simulate an Anthropic Claude call
client._send(
    provider="anthropic",
    model="claude-sonnet-4-6",
    prompt='[{"role": "user", "content": "What is the EU AI Act and who does it affect?"}]',
    response="The EU AI Act is a regulation that classifies AI systems by risk level and imposes obligations on developers and deployers. It affects any company placing AI systems on the EU market.",
    tokens_in=20,
    tokens_out=41,
    latency_ms=1204.7,
    cost_usd=0.000675,
    app_name="example-app",
    user_id="demo-user",
    session_id="session-001",
)
print("✓ Logged: anthropic / claude-sonnet-4-6")

# Simulate a failed call
client._send(
    provider="openai",
    model="gpt-4o-mini",
    prompt='[{"role": "user", "content": "Generate a report."}]',
    response=None,
    tokens_in=None,
    tokens_out=None,
    latency_ms=120.0,
    cost_usd=None,
    app_name="example-app",
    user_id="demo-user",
    error="RateLimitError: You have exceeded your rate limit.",
)
print("✓ Logged: openai / gpt-4o-mini (with error)\n")

import time
time.sleep(1)  # give the background threads a moment to send

print("Done! Now run:\n")
print("  python cli/main.py tail")
print("  python cli/main.py stats\n")
