# AI Audit Logger

A drop-in audit logger for LLM API calls. Records every OpenAI and Anthropic call — prompts, responses, tokens, cost, latency — in a queryable, self-hosted database.

Built for teams that need visibility into their AI usage for debugging, cost control, and compliance (EU AI Act, SOC 2).

## Quickstart

### 1. Start the server

```bash
docker compose up -d
```

This starts Postgres and the ingest/query API on `http://localhost:8000`.

### 2. Wrap your client (one line change)

```python
from openai import OpenAI
from ai_audit_logger import wrap

client = wrap(OpenAI())

# Every call is now logged automatically
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

```python
from anthropic import Anthropic
from ai_audit_logger import wrap

client = wrap(Anthropic())

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 3. Query your logs

```bash
# Install CLI
pip install -r cli/requirements.txt

# Show recent calls
python cli/main.py tail

# Show stats
python cli/main.py stats

# Filter by provider, model, user
python cli/main.py tail --provider openai --model gpt-4o --limit 50
```

---

## Configuration

Set via environment variables or `configure()`:

```python
from ai_audit_logger import configure

configure(
    server_url="http://localhost:8000",
    app_name="my-chatbot",
    user_id="user-123",          # optional: tie logs to a user
    session_id="session-abc",    # optional: group calls into a session
    redact_prompts=False,        # set True to omit prompt text
    enabled=True,
)
```

| Env var | Default | Description |
|---|---|---|
| `AUDIT_SERVER_URL` | `http://localhost:8000` | Ingest server URL |
| `AUDIT_APP_NAME` | (none) | Tag logs with your app name |
| `AUDIT_ENABLED` | `true` | Set `false` to disable logging |
| `AUDIT_REDACT_PROMPTS` | `false` | Omit prompt/response text from logs |

---

## API

| Endpoint | Description |
|---|---|
| `POST /api/v1/log` | Ingest a log entry |
| `GET /api/v1/logs` | Query logs (filter by provider, model, user, app, session) |
| `GET /api/v1/logs/stats` | Aggregated stats (total calls, cost, tokens, latency) |
| `GET /health` | Health check |

---

## Project Structure

```
ai-audit-logger/
├── server/           # FastAPI ingest + query API
├── sdk/python/       # Python SDK (wrap OpenAI/Anthropic)
├── cli/              # CLI for querying logs
├── docker-compose.yml
└── .env.example
```

---

## Roadmap

- [ ] TypeScript SDK
- [ ] LangChain integration
- [ ] Web dashboard
- [ ] Tamper-evident log hashing (compliance tier)
- [ ] Slack/email alerts on cost spikes
- [ ] Export to CSV / JSONL for compliance reports

---

## License

MIT
