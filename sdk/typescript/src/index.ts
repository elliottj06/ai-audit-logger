export { AuditConfig, configure, getConfig } from "./config";
export { AuditClient, LogPayload } from "./client";

import { AuditClient } from "./client";
import { AuditConfig, defaultConfig, getConfig } from "./config";
import { wrapOpenAI, wrapAnthropic } from "./wrapper";

/**
 * Wrap an OpenAI or Anthropic client to automatically log all LLM calls.
 *
 * @example
 * import OpenAI from 'openai';
 * import { wrap } from 'ai-audit-logger';
 *
 * const client = wrap(new OpenAI());
 * // All calls now logged automatically
 */
export function wrap<T extends object>(client: T, config?: Partial<AuditConfig>): T {
  const cfg = config ? defaultConfig(config) : getConfig();
  const audit = new AuditClient(cfg);
  const className = client.constructor?.name ?? "";

  if (className.includes("OpenAI")) return wrapOpenAI(client, audit, cfg);
  if (className.includes("Anthropic")) return wrapAnthropic(client, audit, cfg);

  throw new Error(`Unsupported client type: ${className}. Expected OpenAI or Anthropic.`);
}
