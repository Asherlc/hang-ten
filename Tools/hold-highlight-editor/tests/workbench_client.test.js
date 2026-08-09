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
    if (path === "/api/boards") return response({ ok: true, jobId: "job-42" });
    await new Promise((resolve) => { releasePoll = resolve; });
    return response({
      ok: true,
      job: {
        id: "job-42",
        boardId: "workbench-board-reservation-42",
        state: "succeeded",
        result: { boardId: "board-9" },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");
  const accepted = [];

  const pending = client.createFromUrl("Board", "https://example.test/board.png", {
    onAccepted(job) { accepted.push(job); },
  });
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(accepted, [{ jobId: "job-42", boardId: null }]);
  releasePoll();
  assert.deepEqual(await pending, { boardId: "board-9" });
  assert.deepEqual(calls, ["/api/boards", "/api/jobs/job-42"]);
});

test("createFromUpload sends the raw image with its media type and encoded product name", async () => {
  const calls = [];
  const image = { type: "image/webp", bytes: new Uint8Array([1, 2, 3]) };
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (path.startsWith("/api/boards/upload?")) {
      return response({ ok: true, jobId: "job-upload", boardId: "board-upload" });
    }
    return response({
      ok: true,
      job: {
        id: "job-upload",
        boardId: "board-upload",
        state: "succeeded",
        result: { boardId: "board-upload" },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(await client.createFromUpload("Board & Rail", image), { boardId: "board-upload" });
  assert.equal(calls[0][0], "/api/boards/upload?productName=Board+%26+Rail");
  assert.deepEqual(calls[0][1].headers, { "Content-Type": "image/webp" });
  assert.equal(calls[0][1].body, image);
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

test("draft and approval mutations bind the immutable checkpoint token", async () => {
  const submissions = [];
  let accepted = 0;
  global.fetch = async (path, options = {}) => {
    if (path === "/api/drafts" || path === "/api/approve") {
      accepted += 1;
      const jobId = `job-token-${String(accepted)}`;
      submissions.push([path, JSON.parse(options.body)]);
      return response({ ok: true, jobId, boardId: "board-9" });
    }
    const jobId = path.split("/").at(-1);
    return response({
      ok: true,
      job: {
        id: jobId,
        boardId: "board-9",
        state: "succeeded",
        result: { boardId: "board-9" },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");
  const view = {
    boardId: "board-9",
    revisionId: "revision-1",
    stage: 2,
    checkpointToken: "checkpoint-attempt-7",
  };

  await client.saveDraft(view, { regions: [] });
  await client.approve(view);

  assert.deepEqual(submissions, [
    ["/api/drafts", {
      boardId: "board-9",
      expectedRevisionId: "revision-1",
      expectedStage: 2,
      expectedCheckpointToken: "checkpoint-attempt-7",
      document: { regions: [] },
    }],
    ["/api/approve", {
      boardId: "board-9",
      expectedRevisionId: "revision-1",
      expectedStage: 2,
      expectedCheckpointToken: "checkpoint-attempt-7",
    }],
  ]);
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

test("an unknown server job state remains nonterminal uncertainty", async () => {
  global.fetch = async () => response({
    ok: true,
    job: {
      id: "job-future",
      boardId: "board-9",
      state: "paused",
      result: null,
      error: null,
    },
  });
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  await assert.rejects(client.pollJob("job-future", { interval: 0 }), (error) => {
    assert.equal(error.jobId, "job-future");
    assert.equal(error.terminal, false);
    return true;
  });
});

test("missing malformed and mismatched job payloads remain nonterminal uncertainty", async () => {
  const cases = [
    { ok: true },
    { ok: true, job: { id: "job-payload", boardId: "board-9", state: null, result: null, error: null } },
    { ok: true, job: { id: "job-other", boardId: "board-9", state: "failed", result: null, error: "job failed" } },
    { ok: true, job: { id: "job-payload", boardId: "board-9", state: "failed", result: null, error: null } },
    { ok: true, job: { id: "job-payload", boardId: "board-9", state: "failed", result: { stale: true }, error: "job failed" } },
    { ok: true, job: { id: "job-payload", boardId: "board-9", state: "succeeded", error: null } },
  ];
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  for (const payload of cases) {
    global.fetch = async () => response(payload);
    await assert.rejects(client.pollJob("job-payload", { interval: 0 }), (error) => {
      assert.equal(error.jobId, "job-payload");
      assert.equal(error.terminal, false);
      return true;
    });
  }
});

test("importRun submits an explicit CLI run root to the import endpoint", async () => {
  const calls = [];
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (path === "/api/boards/import") return response({ ok: true, jobId: "job-import" });
    return response({
      ok: true,
      job: {
        id: "job-import",
        boardId: "board-imported",
        state: "succeeded",
        result: { boardId: "board-imported" },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(await client.importRun("/workspace/cli-run"), { boardId: "board-imported" });
  assert.equal(calls[0][0], "/api/boards/import");
  assert.deepEqual(JSON.parse(calls[0][1].body), { runRoot: "/workspace/cli-run" });
});

test("listLibraryBoards returns repository boards and diagnostics", async () => {
  const calls = [];
  global.fetch = async (path) => {
    calls.push(path);
    return response({
      ok: true,
      boards: [{ boardId: "example-board" }],
      diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(
    await client.listLibraryBoards(),
    {
      boards: [{ boardId: "example-board" }],
      diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
    },
  );
  assert.deepEqual(calls, ["/api/library"]);
});

test("openLibraryBoard posts to the encoded repository route", async () => {
  const calls = [];
  global.fetch = async (path) => {
    calls.push(path);
    if (path === "/api/library/example%20board/open") {
      return response({ ok: true, jobId: "job-library" });
    }
    return response({
      ok: true,
      job: {
        id: "job-library",
        boardId: "workbench-board-reservation-1",
        state: "succeeded",
        result: { boardId: "board-0001" },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(await client.openLibraryBoard("example board"), { boardId: "board-0001" });
  assert.deepEqual(calls, [
    "/api/library/example%20board/open",
    "/api/jobs/job-library",
  ]);
});

test("finalSave posts to the encoded board-scoped save route", async () => {
  const calls = [];
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (path === "/api/boards/board%209/save") {
      return response({ ok: true, jobId: "job-save", boardId: "board 9" });
    }
    return response({
      ok: true,
      job: {
        id: "job-save",
        boardId: "board 9",
        state: "succeeded",
        result: { boardId: "board 9", saved: true },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(
    await client.finalSave({ boardId: "board 9", revisionId: "revision-1" }),
    { boardId: "board 9", saved: true },
  );
  assert.equal(calls[0][0], "/api/boards/board%209/save");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    boardId: "board 9",
    expectedRevisionId: "revision-1",
  });
});
