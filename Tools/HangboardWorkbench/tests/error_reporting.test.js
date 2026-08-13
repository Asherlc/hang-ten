const test = require("node:test");
const assert = require("node:assert/strict");
const { createReporter, exceptionProperties, install, redactMessage } = require("../error-reporting.js");

test("reporting is disabled without a valid public token", async () => {
  let calls = 0;
  const reporter = createReporter({ host: "https://us.i.posthog.com", fetch: async () => { calls += 1; } });
  assert.equal(reporter.enabled, false);
  assert.equal(await reporter.capture(new Error("broken")), false);
  assert.equal(calls, 0);
});

test("reporting remains nonfatal when the transport throws synchronously", async () => {
  const reporter = createReporter({
    token: "phc_public-token",
    host: "https://us.i.posthog.com",
    distinctId: "anonymous-test-editor",
    fetch: () => { throw new Error("transport unavailable"); },
  });
  assert.equal(await reporter.capture(new Error("broken")), false);
});

test("exceptions use PostHog's exception event and redact sensitive locations", async () => {
  const calls = [];
  const reporter = createReporter({
    token: "phc_public-token",
    host: "https://us.i.posthog.com/",
    distinctId: "anonymous-test-editor",
    fetch: async (...args) => { calls.push(args); },
  });
  assert.equal(await reporter.capture(new TypeError("Failed at /Users/alice/private/board.json https://example.com/a?q=secret")), true);
  assert.equal(calls[0][0], "https://us.i.posthog.com/i/v0/e/");
  const payload = JSON.parse(calls[0][1].body);
  assert.equal(payload.event, "$exception");
  assert.equal(payload.api_key, "phc_public-token");
  assert.equal(payload.properties.$exception_type, "TypeError");
  assert.equal(payload.properties.distinct_id, "anonymous-test-editor");
  assert.equal(payload.properties.$exception_list[0].mechanism.handled, false);
  assert.doesNotMatch(payload.properties.$exception_message, /alice|secret|example\.com/);
});

test("redaction and exception properties remain bounded", () => {
  assert.equal(redactMessage("open file:///tmp/private.json"), "open [file]");
  assert.equal(redactMessage("open C:\\Users\\alice\\private\\board.json"), "open [path]");
  assert.equal(redactMessage("open \\\\fileserver\\alice\\private\\board.json"), "open [path]");
  const properties = exceptionProperties(new Error("x".repeat(800)));
  assert.equal(properties.$exception_message.length, 500);
  assert.deepEqual(Object.keys(properties).sort(), [
    "$exception_list", "$exception_message", "$exception_type", "editor_surface",
  ]);
});

test("installation buffers errors while telemetry configuration loads", async () => {
  const listeners = {};
  const calls = [];
  let resolveConfiguration;
  const configuration = new Promise((resolve) => { resolveConfiguration = resolve; });
  const target = {
    addEventListener(type, listener) { listeners[type] = listener; },
    crypto: { randomUUID: () => "startup-editor-id" },
    fetch: async (...args) => {
      if (args[0] === "/api/telemetry") return configuration;
      calls.push(args);
    },
    localStorage: { getItem: () => null, setItem() {} },
  };

  const installed = install(target);
  assert.equal(typeof listeners.error, "function");
  assert.equal(typeof listeners.unhandledrejection, "function");
  listeners.error({ error: new Error("startup failure") });
  listeners.unhandledrejection({ reason: new TypeError("startup rejection") });
  assert.equal(calls.length, 0);

  resolveConfiguration({
    ok: true,
    json: async () => ({ token: "phc_public-token", host: "https://us.i.posthog.com" }),
  });
  const reporter = await installed;
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(reporter.enabled, true);
  assert.equal(calls.length, 2);
  assert.deepEqual(calls.map((call) => JSON.parse(call[1].body).properties.$exception_list[0].mechanism.type), [
    "onerror", "unhandledrejection",
  ]);
});

test("installation uses an in-memory ID when localStorage throws", async () => {
  const calls = [];
  const target = {
    addEventListener() {},
    crypto: { randomUUID: () => "fallback-editor-id" },
    fetch: async (...args) => {
      if (args[0] === "/api/telemetry") {
        return { ok: true, json: async () => ({ token: "phc_public-token", host: "https://us.i.posthog.com" }) };
      }
      calls.push(args);
    },
    localStorage: {
      getItem() { throw new Error("storage blocked"); },
      setItem() { throw new Error("storage blocked"); },
    },
  };

  const reporter = await install(target);
  assert.equal(reporter.enabled, true);
  assert.equal(await reporter.capture(new Error("test")), true);
  assert.equal(JSON.parse(calls[0][1].body).properties.distinct_id, "fallback-editor-id");
});
