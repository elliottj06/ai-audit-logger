export interface AuditConfig {
  serverUrl: string;
  appName?: string;
  userId?: string;
  sessionId?: string;
  enabled: boolean;
  redactPrompts: boolean;
  timeout: number;
}

export function defaultConfig(overrides: Partial<AuditConfig> = {}): AuditConfig {
  return {
    serverUrl: process.env.AUDIT_SERVER_URL ?? "http://localhost:8000",
    appName: process.env.AUDIT_APP_NAME,
    enabled: process.env.AUDIT_ENABLED !== "false",
    redactPrompts: process.env.AUDIT_REDACT_PROMPTS === "true",
    timeout: 2000,
    ...overrides,
  };
}

let _config = defaultConfig();

export function configure(overrides: Partial<AuditConfig>): void {
  _config = defaultConfig(overrides);
}

export function getConfig(): AuditConfig {
  return _config;
}
