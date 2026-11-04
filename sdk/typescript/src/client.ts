import { AuditConfig } from "./config";

export interface LogPayload {
  provider: string;
  model: string;
  prompt?: string | null;
  response?: string | null;
  tokens_in?: number | null;
  tokens_out?: number | null;
  latency_ms?: number | null;
  cost_usd?: number | null;
  session_id?: string | null;
  user_id?: string | null;
  app_name?: string | null;
  error?: string | null;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export class AuditClient {
  constructor(private config: AuditConfig) {}

  log(payload: LogPayload): void {
    if (!this.config.enabled) return;
    // Fire-and-forget — never blocks the caller
    fetch(`${this.config.serverUrl}/api/v1/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.config.timeout),
    }).catch(() => {}); // silently drop — logging must never crash the app
  }
}
