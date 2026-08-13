((root, factory) => {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.HoldEditorErrorReporting = api;
})(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const MAX_MESSAGE_LENGTH = 500;
  const MAX_EXCEPTION_TYPE_LENGTH = 100;
  const MAX_PENDING_ERRORS = 20;

  function redact(value, maximumLength, fallback) {
    return String(value || fallback)
      .replace(/https?:\/\/\S+/gi, "[url]")
      .replace(/file:\/\/[^\r\n]*/gi, "[file]")
      .replace(/\b[A-Za-z]:[\\/][^\r\n]*/g, "[path]")
      .replace(/\\\\[^\r\n]*/g, "[path]")
      .replace(/(?:\/[^/\r\n]+){2,}[^\r\n]*/g, "[path]")
      .slice(0, maximumLength) || fallback;
  }

  function redactMessage(value) {
    return redact(value, MAX_MESSAGE_LENGTH, "Unknown error");
  }

  function redactExceptionType(value) {
    return redact(value || "Error", MAX_EXCEPTION_TYPE_LENGTH, "Error");
  }

  function exceptionProperties(error, { handled = false, mechanism = "onerror" } = {}) {
    const candidate = error && typeof error === "object" ? error : {};
    const type = redactExceptionType(candidate.name);
    const value = redactMessage(candidate.message || error);
    return {
      $exception_list: [{
        type,
        value,
        mechanism: { type: redactExceptionType(mechanism), handled: Boolean(handled) },
      }],
      $exception_type: type,
      $exception_message: value,
      editor_surface: "hold_editor",
    };
  }

  function createReporter({ token, host, distinctId, fetch: send = globalThis.fetch } = {}) {
    let captureHost;
    try {
      const parsedHost = new URL(host);
      if (parsedHost.protocol === "https:" && parsedHost.hostname) captureHost = parsedHost.href.replace(/\/+$/, "");
    } catch (_error) {
      // Invalid configuration disables reporting.
    }
    const enabled = typeof token === "string" && token.startsWith("phc_")
      && Boolean(captureHost)
      && typeof distinctId === "string" && distinctId.length > 0
      && typeof send === "function";
    return {
      enabled,
      capture(error, context) {
        if (!enabled) return Promise.resolve(false);
        return Promise.resolve().then(() => send(`${captureHost}/i/v0/e/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            api_key: token,
            event: "$exception",
            properties: {
              ...exceptionProperties(error, context),
              distinct_id: distinctId,
              $lib: "hang-ten-hold-editor",
            },
          }),
          keepalive: true,
        })).then(() => true, () => false);
      },
    };
  }

  async function install(target = globalThis) {
    let reporter = createReporter();
    const pending = [];
    let configuring = true;
    const capture = (error, context) => {
      if (configuring) {
        if (pending.length < MAX_PENDING_ERRORS) pending.push([error, context]);
      } else {
        reporter.capture(error, context);
      }
    };
    target.addEventListener("error", (event) => {
      capture(event.error || new Error(event.message), { mechanism: "onerror" });
    });
    target.addEventListener("unhandledrejection", (event) => {
      capture(event.reason, { mechanism: "unhandledrejection" });
    });

    let configuration;
    try {
      const response = await target.fetch("/api/telemetry");
      configuration = response.ok ? await response.json() : null;
    } catch (_error) {
      configuring = false;
      pending.length = 0;
      return reporter;
    }
    const storageKey = "hang-ten.posthog-anonymous-id";
    let distinctId;
    try {
      distinctId = target.localStorage?.getItem(storageKey);
    } catch (_error) {
      // Storage can be unavailable in privacy modes; reporting must remain nonfatal.
    }
    if (!distinctId) {
      distinctId = target.crypto?.randomUUID?.() || `editor-${Date.now()}-${Math.random()}`;
      try {
        target.localStorage?.setItem(storageKey, distinctId);
      } catch (_error) {
        // The in-memory ID still identifies events for the lifetime of this page.
      }
    }
    reporter = createReporter({
      ...configuration,
      distinctId,
      fetch: target.fetch.bind(target),
    });
    configuring = false;
    if (reporter.enabled) pending.splice(0).forEach(([error, context]) => reporter.capture(error, context));
    else pending.length = 0;
    return reporter;
  }

  return { createReporter, exceptionProperties, install, redactExceptionType, redactMessage };
});
