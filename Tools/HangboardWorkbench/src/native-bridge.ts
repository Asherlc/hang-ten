import type { RequestDiagnostic } from "./types.ts";

interface NativeDiagnosticHandler {
  postMessage(diagnostic: RequestDiagnostic): void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function hasDiagnosticHandler(value: unknown): value is NativeDiagnosticHandler {
  return isRecord(value) && typeof value.postMessage === "function";
}

export function postNativeDiagnostic(browserGlobal: unknown, diagnostic: RequestDiagnostic): void {
  if (!isRecord(browserGlobal)) return;
  const webkit = browserGlobal.webkit;
  if (!isRecord(webkit)) return;
  const messageHandlers = webkit.messageHandlers;
  if (!isRecord(messageHandlers)) return;
  const handler = messageHandlers.workbenchDiagnostics;
  if (!hasDiagnosticHandler(handler)) return;
  handler.postMessage(diagnostic);
}
