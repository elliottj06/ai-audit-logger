"""
Slack webhook alerts for cost spikes.

Configure via environment variables:
  SLACK_WEBHOOK_URL     - Slack incoming webhook URL
  ALERT_COST_PER_CALL   - Alert if a single call costs more than this (default: 0.50)
  ALERT_HOURLY_COST     - Alert if hourly spend exceeds this (default: 5.00)
"""

import os
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ALERT_COST_PER_CALL = float(os.getenv("ALERT_COST_PER_CALL", "0.50"))
ALERT_HOURLY_COST = float(os.getenv("ALERT_HOURLY_COST", "5.00"))


def _send_slack(message: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    try:
        httpx.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=3)
    except Exception:
        pass


def check_alerts(db: Session, entry) -> None:
    """Called after each log entry is saved. Fires Slack alerts if thresholds exceeded."""
    if not SLACK_WEBHOOK_URL:
        return

    # Single call cost spike
    if entry.cost_usd and entry.cost_usd >= ALERT_COST_PER_CALL:
        _send_slack(
            f":rotating_light: *AI Audit Alert — High Cost Call*\n"
            f"> Provider: `{entry.provider}` | Model: `{entry.model}`\n"
            f"> Cost: `${entry.cost_usd:.4f}` | Tokens: {entry.tokens_in}→{entry.tokens_out}\n"
            f"> App: `{entry.app_name or 'unknown'}` | User: `{entry.user_id or 'unknown'}`"
        )

    # Hourly spend threshold
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    from server.models import LogEntry
    hourly_cost = (
        db.query(func.sum(LogEntry.cost_usd))
        .filter(LogEntry.timestamp >= one_hour_ago)
        .scalar() or 0
    )
    if hourly_cost >= ALERT_HOURLY_COST:
        _send_slack(
            f":money_with_wings: *AI Audit Alert — Hourly Spend Threshold*\n"
            f"> Spent `${hourly_cost:.4f}` in the last hour (threshold: `${ALERT_HOURLY_COST:.2f}`)"
        )
