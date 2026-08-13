((root, factory) => {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.HoldEditorErrorReporting = api;
})(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const MAX_MESSAGE_LENGTH = 500;

  function redactMessage(value) {
    return String(value || "Unknown error")
      .replace(/https?:\/\/\S+/gi, "[url]")
      .replace(/file:\/\/\S+/gi, "[file]")
      .replace(/\b[A-Za-z]:[\\/](?:[^\\/\s]+[\\/])*[^\\/\s]*/g, "[path]")
      .replace(/\\\\[^\\\s]+\\[^\\\s]+(?:\\[^\\\s]+)*/g, "[path]")
      .replace(/(?:\/[\w.@~+-]+){2,}/g, "[path]")
      .slice(0, MAX_MESSAGE_LENGTH);
  }

  function exceptionProperties(error, { handled = false, mechanism = "onerror" } = {}) {
    const candidate = error && typeof error === "object" ? error : {};
    const type = typeof candidate.name === "string" && candidate.name ? candidate.name : "Error";
    const value = redactMessage(candidate.message || error);
    return {
      $exception_list: [{ type, value, mechanism: { type: mechanism, handled } }],
      $exception_type: type,
      $exception_message: value,
      editor_surface: "hold_editor",
    };
  }

  function createReporter({ token, host, distinctId, fetch: send = globalThis.fetch } = {}) {
    const enabled = typeof token === "string" && token.startsWith("phc_")
      && typeof host === "string" && /^https:\/\//.test(host)
      && typeof distinctId === "string" && distinctId.length > 0
      && typeof send === "function";
    return {
      enabled,
      capture(error, context) {
        if (!enabled) return Promise.resolve(false);
        return Promise.resolve().then(() => send(`${host.replace(/\/+$/, "")}/i/v0/e/`, {
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
        pending.push([error, context]);
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

  return { createReporter, exceptionProperties, install, redactMessage };
});
