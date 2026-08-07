const test = require("node:test");
const assert = require("node:assert/strict");

function response(payload) {
  return { ok: true, status: 200, async json() { return payload; } };
}

test("a newly accepted job ID is exposed before polling completes", async () => {
  const calls = [];
  let releasePoll;
  global.fetch = async (path) => {
    calls.push(path);
    if (path === "/api/boards") return response({ ok: true, jobId: "job-42", boardId: "board-9" });
    await new Promise((resolve) => { releasePoll = resolve; });
    return response({ ok: true, job: { id: "job-42", state: "succeeded", result: { boardId: "board-9" } } });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");
  const accepted = [];

  const pending = client.createFromUrl("Board", "https://example.test/board.png", {
    onAccepted(job) { accepted.push(job); },
  });
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(accepted, [{ jobId: "job-42", boardId: "board-9" }]);
  releasePoll();
  assert.deepEqual(await pending, { boardId: "board-9" });
  assert.deepEqual(calls, ["/api/boards", "/api/jobs/job-42"]);
});

test("an accepted mutation survives a transient poll failure without being submitted again", async () => {
  const calls = [];
  let pollAttempt = 0;
  const originalSetTimeout = global.setTimeout;
  global.setTimeout = (resolve) => {
    queueMicrotask(resolve);
    return 1;
  };
  global.fetch = async (path) => {
    calls.push(path);
    if (path === "/api/approve") {
      return response({ ok: true, jobId: "job-44", boardId: "board-9" });
    }
    pollAttempt += 1;
    if (pollAttempt === 1) throw new TypeError("connection reset");
    if (pollAttempt === 2) {
      return response({
        ok: true,
        job: { id: "job-44", boardId: "board-9", state: "running", result: null, error: null },
      });
    }
    return response({
      ok: true,
      job: {
        id: "job-44",
        boardId: "board-9",
        state: "succeeded",
        result: { boardId: "board-9", revisionId: "revision-2" },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  try {
    const result = await client.approve({
      boardId: "board-9",
      revisionId: "revision-1",
      stage: 2,
    });

    assert.deepEqual(result, { boardId: "board-9", revisionId: "revision-2" });
    assert.deepEqual(calls, [
      "/api/approve",
      "/api/jobs/job-44",
      "/api/jobs/job-44",
      "/api/jobs/job-44",
    ]);
  } finally {
    global.setTimeout = originalSetTimeout;
  }
});

test("exhausted poll transport failures retain the accepted nonterminal job identity", async () => {
  global.fetch = async () => { throw new TypeError("network unavailable"); };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  await assert.rejects(
    client.pollJob("job-uncertain", { interval: 0, maxTransientFailures: 1 }),
    (error) => {
      assert.equal(error.message, "network unavailable");
      assert.equal(error.jobId, "job-uncertain");
      assert.equal(error.terminal, false);
      return true;
    },
  );
});

test("a server-confirmed failed job reports a terminal error with its accepted identity", async () => {
  global.fetch = async () => response({
    ok: true,
    job: {
      id: "job-failed",
      boardId: "board-9",
      state: "failed",
      result: null,
      error: "Stage 2 region 17: contour is invalid",
    },
  });
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  await assert.rejects(client.pollJob("job-failed", { interval: 0 }), (error) => {
    assert.equal(error.message, "Stage 2 region 17: contour is invalid");
    assert.equal(error.jobId, "job-failed");
    assert.equal(error.terminal, true);
    return true;
  });
});

test("importRun submits an explicit CLI run root to the import endpoint", async () => {
  const calls = [];
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (path === "/api/boards/import") return response({ ok: true, jobId: "job-import" });
    return response({
      ok: true,
      job: { id: "job-import", state: "succeeded", result: { boardId: "board-imported" } },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(await client.importRun("/workspace/cli-run"), { boardId: "board-imported" });
  assert.equal(calls[0][0], "/api/boards/import");
  assert.deepEqual(JSON.parse(calls[0][1].body), { runRoot: "/workspace/cli-run" });
});
