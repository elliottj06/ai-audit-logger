# AI Audit Logger

![CI](https://github.com/elliottj06/ai-audit-logger/actions/workflows/ci.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/ai-audit-logger)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![npm](https://img.shields.io/npm/v/ai-audit-logger)
![License](https://img.shields.io/github/license/elliottj06/ai-audit-logger)

A self-hosted audit logger for LLM API calls. Capture every **OpenAI, Anthropic and Gemini** call — prompts, responses, tokens, cost, latency — in a Postgres database you own. Wrap your client in one line (Python or Node.js), or point your `base_url` at the built-in proxy and change **zero code**.

Built for teams that need visibility into their AI usage for **debugging**, **cost control**, and **governance** — the kind of audit trail that EU AI Act and SOC 2 reviews ask for. Your data never leaves your infrastructure.

**Features:** Python + TypeScript SDKs · transparent proxy · LangChain callback · web dashboard · CLI · CSV/JSONL export · prompt redaction · Slack cost-spike alerts · daily/monthly budgets · optional API-key auth

![AI Audit Logger web dashboard showing total calls, cost, latency, token usage, per-model charts and a filterable table of recent calls](docs/images/dashboard.png)

---

## How it works

```
Your App ─┬─ SDK (wrap your client) ──→ Ingest API ─┐
          └─ Proxy (change base_url) ──→ Provider  ─┴→  Postgres
                                                            ↓
                                               CLI / Dashboard / Export
```

Two ways to capture calls:

- **SDK** — a thin wrapper around your existing OpenAI, Anthropic or Gemini client. It intercepts every call, records it asynchronously (never blocks your app), and ships it to the server.
- **Proxy** — the server forwards your requests to the provider and logs them on the way through. No SDK, no code changes, works from any language.

---

## Quickstart

### 1. Start the server

```bash
git clone https://github.com/elliottj06/ai-audit-logger
cd ai-audit-logger
docker compose up -d
```

### 2. Capture your calls

#### Option A — Wrap your client (one line)

```bash
pip install ai-audit-logger      # Python
npm install ai-audit-logger      # Node.js / TypeScript
```

**OpenAI:**
```python
from openai import OpenAI
from ai_audit_logger import wrap

client = wrap(OpenAI())

# Every call now logged automatically — no other changes needed
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

**Anthropic:**
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

**TypeScript / Node.js:**
```ts
import OpenAI from "openai";
import { wrap } from "ai-audit-logger";

const client = wrap(new OpenAI());

const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello" }],
});
```

**LangChain:**
```python
from langchain_openai import ChatOpenAI
from ai_audit_logger.langchain import AuditCallbackHandler

llm = ChatOpenAI(model="gpt-4o", callbacks=[AuditCallbackHandler(app_name="my-app")])
llm.invoke("Hello!")
```

#### Option B — Proxy mode (zero code changes)

Point your existing client at the server instead of the provider. Requests are forwarded and logged automatically.

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/proxy/openai/v1")
```

| Provider | Proxy base URL |
|---|---|
| OpenAI | `http://localhost:8000/proxy/openai/v1` |
| Anthropic | `http://localhost:8000/proxy/anthropic` |
| Gemini | `http://localhost:8000/proxy/gemini` |

Provider keys are read from `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` on the server, or set in the dashboard. Tag requests with optional `x-app-name`, `x-user-id` and `x-session-id` headers.

### 3. Query your logs

```bash
pip install -r cli/requirements.txt

python cli/main.py tail        # recent calls
python cli/main.py stats       # cost + usage summary
```

**`tail` output:**
```
Showing 3 of 3 entries

 Timestamp           Provider    Model                        Tokens        Cost          Latency
 ------------------- ----------- ---------------------------- ------------ ------------- ---------
 2026-11-04 14:23:01 openai      gpt-4o                       18→32         $0.00057      843ms
 2026-11-04 14:23:02 anthropic   claude-sonnet-4-6            20→41         $0.00068      1204ms
 2026-11-04 14:23:03 openai      gpt-4o-mini                  0→0           n/a           120ms    ERROR
```

**`stats` output:**

![Output of the stats command: total calls, total cost, tokens in and out, average latency, and a per-model breakdown of calls and cost](docs/images/cli-stats.png)

### 4. Open the dashboard

With the server running, open **http://localhost:8000** for the web dashboard: summary cards, calls and cost by model, and a filterable table of recent calls (click any row for full detail).

---

## Try it without API keys

Run the included example to send simulated log entries and see the CLI in action:

```bash
python examples/basic_usage.py
python cli/main.py tail
python cli/main.py stats
```

---

## Configuration

```python
from ai_audit_logger import configure

configure(
    server_url="http://localhost:8000",  # your server
    app_name="my-chatbot",              # tag logs by app
    user_id="user-123",                 # tie logs to a user
    session_id="session-abc",           # group calls into sessions
    redact_prompts=False,               # True = omit prompt text from logs
    enabled=True,
)
```

| Env var | Default | Description |
|---|---|---|
| `AUDIT_SERVER_URL` | `http://localhost:8000` | Ingest server URL |
| `AUDIT_APP_NAME` | (none) | Tag logs with your app name |
| `AUDIT_ENABLED` | `true` | Set `false` to disable without code changes |
| `AUDIT_REDACT_PROMPTS` | `false` | Omit prompt/response text (privacy mode) |
| `AUDIT_API_KEY` | (none) | Bearer token sent to the server when auth is on |

### Server

| Env var | Default | Description |
|---|---|---|
| `API_KEY` | (none) | Set to require `Authorization: Bearer <key>` on the API, dashboard and proxy. Leave blank for open local use. |
| `DATABASE_URL` | local Postgres | SQLAlchemy connection string |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | (none) | Provider keys used by proxy mode |
| `SLACK_WEBHOOK_URL` | (none) | Enable Slack cost-spike alerts |
| `ALERT_COST_PER_CALL` | `0.50` | Alert when one call costs more than this (USD) |
| `ALERT_HOURLY_COST` | `5.00` | Alert when hourly spend exceeds this (USD) |
| `BUDGET_DAILY_USD` / `BUDGET_MONTHLY_USD` | `0` | Spend budgets shown in the dashboard (`0` = no limit) |

See [`.env.example`](.env.example) for a full template.

> **Securing a shared deployment:** set `API_KEY` before exposing the server beyond localhost — it stores full prompts and responses unless redaction is on.

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/log` | POST | Ingest a log entry |
| `/api/v1/logs` | GET | Query logs (filter by provider, model, user, app, session) |
| `/api/v1/logs/stats` | GET | Aggregated stats — total calls, cost, tokens, latency |
| `/api/v1/logs/timeseries` | GET | Calls and cost over time |
| `/api/v1/logs/users` · `/api/v1/logs/apps` | GET | Usage broken down by user or app |
| `/api/v1/sessions` · `/api/v1/sessions/{id}` | GET | Calls grouped into sessions |
| `/api/v1/logs/export` | GET | Export as CSV or JSONL (`?format=jsonl`) |
| `/api/v1/budget` | GET | Spend vs. daily/monthly budget |
| `/api/v1/settings/providers` | GET/POST/DELETE | Manage provider keys for proxy mode |
| `/proxy/{openai,anthropic,gemini}/...` | POST | Transparent logging proxy |
| `/health` | GET | Health check (always public) |

---

## Project structure

```
ai-audit-logger/
├── server/                  # FastAPI server
│   ├── main.py
│   ├── models.py            # SQLAlchemy LogEntry model
│   ├── db.py                # Postgres connection
│   ├── auth.py              # Optional bearer-token auth
│   ├── alerts.py            # Slack cost-spike alerts
│   ├── config_manager.py    # Provider key storage
│   ├── routes/
│   │   ├── ingest.py        # POST /api/v1/log
│   │   ├── query.py         # Logs, stats, sessions, budget, export
│   │   ├── proxy.py         # /proxy/* transparent logging proxy
│   │   └── settings.py      # Provider key management
│   ├── static/index.html    # Web dashboard (served at /)
│   └── Dockerfile
├── sdk/
│   ├── python/ai_audit_logger/
│   │   ├── __init__.py      # wrap() + configure()
│   │   ├── wrapper.py       # OpenAI, Anthropic, Gemini wrappers
│   │   ├── langchain.py     # LangChain callback handler
│   │   ├── client.py        # Fire-and-forget HTTP sender
│   │   └── config.py        # AuditConfig dataclass
│   └── typescript/src/      # Node.js / TypeScript SDK
├── cli/
│   └── main.py              # tail / stats / get commands
├── examples/
│   └── basic_usage.py       # Try it without API keys
└── docker-compose.yml
```

---

## Roadmap

### Core (open source)
- [x] Python SDK — OpenAI, Anthropic, Gemini
- [x] Web dashboard with cost charts
- [x] Proxy mode — zero code changes required
- [x] Publish to PyPI (`pip install ai-audit-logger`)
- [x] CSV / JSONL compliance export
- [x] Slack cost spike alerts
- [x] TypeScript / Node.js SDK (`npm install ai-audit-logger`)
- [x] LangChain integration
- [x] Optional API-key auth + spend budgets
- [ ] Tamper-evident log hashing for compliance exports
- [ ] Gemini support in the TypeScript SDK

### Managed / Team tier (future paid product)
The self-hosted version stays free forever. The managed tier is where the business lives —
teams with 10+ engineers, compliance requirements, and a CTO asking "how much are we spending on AI?"

- [ ] User auth (email/password + Google SSO)
- [ ] Organisations and workspaces
- [ ] Role-based access (admin, developer, viewer)
- [ ] Per-user API key management
- [ ] Usage limits and budgets per user
- [ ] Stripe billing integration
- [ ] Cloud-hosted, managed infrastructure

> **Model inspiration:** Grafana, Metabase, PostHog — open core, free self-hosted, paid managed cloud.

---

## Contributing

Issues and pull requests are welcome. If you're looking for a place to start, check the open issues or the unchecked roadmap items above.

---

## License

[MIT](LICENSE) © Elliott Jones
