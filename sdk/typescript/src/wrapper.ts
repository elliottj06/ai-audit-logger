import { AuditClient } from "./client";
import { AuditConfig } from "./config";

// Cost per 1M tokens (input, output) in USD
const COST_TABLE: Record<string, [number, number]> = {
  "gpt-4o-mini": [0.15, 0.6],
  "gpt-4o": [5.0, 15.0],
  "gpt-4-turbo": [10.0, 30.0],
  "gpt-3.5-turbo": [0.5, 1.5],
  "claude-haiku-4-5": [0.8, 4.0],
  "claude-sonnet-4-6": [3.0, 15.0],
  "claude-opus-4-6": [15.0, 75.0],
  "claude-3-5-sonnet": [3.0, 15.0],
  "claude-3-5-haiku": [0.8, 4.0],
};

function calcCost(model: string, tokensIn: number, tokensOut: number): number | null {
  const lower = model.toLowerCase();
  for (const [key, [costIn, costOut]] of Object.entries(COST_TABLE)) {
    if (lower.includes(key)) {
      return (tokensIn * costIn + tokensOut * costOut) / 1_000_000;
    }
  }
  return null;
}

// ── OpenAI wrapper ────────────────────────────────────────────────────────────

export function wrapOpenAI<T extends object>(client: T, audit: AuditClient, config: AuditConfig): T {
  const original = (client as any).chat.completions.create.bind((client as any).chat.completions);

  const wrappedCreate = async (params: any): Promise<any> => {
    const start = Date.now();
    let error: string | null = null;
    let response: any = null;
    try {
      response = await original(params);
      return response;
    } catch (e: any) {
      error = e?.message ?? String(e);
      throw e;
    } finally {
      const latencyMs = Date.now() - start;
      const tokensIn: number | null = response?.usage?.prompt_tokens ?? null;
      const tokensOut: number | null = response?.usage?.completion_tokens ?? null;
      audit.log({
        provider: "openai",
        model: params.model,
        prompt: config.redactPrompts ? null : JSON.stringify(params.messages ?? []),
        response: response?.choices?.[0]?.message?.content ?? null,
        tokens_in: tokensIn,
        tokens_out: tokensOut,
        latency_ms: latencyMs,
        cost_usd: tokensIn != null && tokensOut != null ? calcCost(params.model, tokensIn, tokensOut) : null,
        session_id: config.sessionId,
        user_id: config.userId,
        app_name: config.appName,
        error,
      });
    }
  };

  return new Proxy(client, {
    get(target, prop) {
      if (prop === "chat") {
        return new Proxy((target as any).chat, {
          get(chatTarget, chatProp) {
            if (chatProp === "completions") {
              return new Proxy(chatTarget.completions, {
                get(compTarget, compProp) {
                  if (compProp === "create") return wrappedCreate;
                  return (compTarget as any)[compProp];
                },
              });
            }
            return (chatTarget as any)[chatProp];
          },
        });
      }
      return (target as any)[prop];
    },
  });
}

// ── Anthropic wrapper ─────────────────────────────────────────────────────────

export function wrapAnthropic<T extends object>(client: T, audit: AuditClient, config: AuditConfig): T {
  const original = (client as any).messages.create.bind((client as any).messages);

  const wrappedCreate = async (params: any): Promise<any> => {
    const start = Date.now();
    let error: string | null = null;
    let response: any = null;
    try {
      response = await original(params);
      return response;
    } catch (e: any) {
      error = e?.message ?? String(e);
      throw e;
    } finally {
      const latencyMs = Date.now() - start;
      const tokensIn: number | null = response?.usage?.input_tokens ?? null;
      const tokensOut: number | null = response?.usage?.output_tokens ?? null;
      audit.log({
        provider: "anthropic",
        model: params.model,
        prompt: config.redactPrompts ? null : JSON.stringify(params.messages ?? []),
        response: response?.content?.[0]?.text ?? null,
        tokens_in: tokensIn,
        tokens_out: tokensOut,
        latency_ms: latencyMs,
        cost_usd: tokensIn != null && tokensOut != null ? calcCost(params.model, tokensIn, tokensOut) : null,
        session_id: config.sessionId,
        user_id: config.userId,
        app_name: config.appName,
        error,
      });
    }
  };

  return new Proxy(client, {
    get(target, prop) {
      if (prop === "messages") {
        return new Proxy((target as any).messages, {
          get(msgTarget, msgProp) {
            if (msgProp === "create") return wrappedCreate;
            return (msgTarget as any)[msgProp];
          },
        });
      }
      return (target as any)[prop];
    },
  });
}
