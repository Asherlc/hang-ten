const test = require("node:test");
const assert = require("node:assert/strict");

function response(payload) {
  return { ok: true, status: 200, async json() { return payload; } };
}

test("board reads recover when the local backend briefly rejects connections", async () => {
  const calls = [];
  const originalSetTimeout = global.setTimeout;
  global.setTimeout = (resolve) => {
    queueMicrotask(resolve);
    return 1;
  };
  global.fetch = async (path) => {
    calls.push(path);
    if (calls.length < 3) throw new TypeError("Load failed");
    return response({ ok: true, boards: [{ boardId: "recovered-board", location: "repository" }] });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  try {
    assert.deepEqual(await client.listBoards(), {
      repositoryBoards: [{ boardId: "recovered-board", location: "repository" }],
      inProgressBoards: [],
      diagnostics: [],
    });
    assert.deepEqual(calls, ["/api/boards", "/api/boards", "/api/boards"]);
  } finally {
    global.setTimeout = originalSetTimeout;
  }
});

test("mutations are not retried when the local backend rejects a connection", async () => {
  const calls = [];
  global.fetch = async (path) => {
    calls.push(path);
    throw new TypeError("Load failed");
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  await assert.rejects(
    client.createFromUrl("Board", "https://example.test/board.png"),
    /Load failed/,
  );
  assert.deepEqual(calls, ["/api/boards"]);
});

test("transport errors identify the failing endpoint and attempt count", async () => {
  const originalSetTimeout = global.setTimeout;
  global.setTimeout = (resolve) => {
    queueMicrotask(resolve);
    return 1;
  };
  global.fetch = async () => {
    throw new TypeError("connection refused");
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  try {
    await assert.rejects(
      client.listBoards(),
      /backend for \/api\/boards after 3 attempts: connection refused/,
    );
  } finally {
    global.setTimeout = originalSetTimeout;
  }
});

test("request failures are reported to the native diagnostic bridge", async () => {
  const diagnostics = [];
  global.webkit = {
    messageHandlers: {
      workbenchDiagnostics: { postMessage(value) { diagnostics.push(value); } },
    },
  };
  global.fetch = async (path) => {
    if (path === "/api/boards") return { ok: false, status: 503, async json() { return { ok: false }; } };
    return { ok: true, status: 200, async json() { throw new SyntaxError("bad json"); } };
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  try {
    await assert.rejects(client.listBoards(), /\/api\/boards failed \(503\)/);
    assert.deepEqual(diagnostics, [
      {
        path: "/api/boards",
        category: "server",
        message: "Workbench request for /api/boards failed (503)",
        status: 503,
      },
    ]);
  } finally {
    delete global.webkit;
  }
});

test("expected client errors do not trigger native recovery diagnostics", async () => {
  const diagnostics = [];
  global.webkit = {
    messageHandlers: {
      workbenchDiagnostics: { postMessage(value) { diagnostics.push(value); } },
    },
  };
  global.fetch = async () => ({
    ok: false,
    status: 422,
    async json() { return { ok: false, error: "Board name is required" }; },
  });
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  try {
    await assert.rejects(client.createFromUrl("", ""), /Board name is required/);
    assert.deepEqual(diagnostics, []);
  } finally {
    delete global.webkit;
  }
});

test("native diagnostics are bounded before crossing the bridge", async () => {
  const diagnostics = [];
  global.webkit = {
    messageHandlers: {
      workbenchDiagnostics: { postMessage(value) { diagnostics.push(value); } },
    },
  };
  global.fetch = async () => ({
    ok: false,
    status: 503,
    async json() { return { ok: false, error: "x".repeat(4096) }; },
  });
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  try {
    await assert.rejects(client.listBoards());
    assert.equal(diagnostics.length, 1);
    assert.equal(diagnostics[0].message.length, 1024);
    assert.deepEqual(Object.keys(diagnostics[0]).sort(), ["category", "message", "path", "status"]);
  } finally {
    delete global.webkit;
  }
});

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
    if (path.startsWith("/api/boards?")) {
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
  assert.equal(calls[0][0], "/api/boards?type=upload&productName=Board+%26+Rail");
  assert.deepEqual(calls[0][1].headers, { "Content-Type": "image/webp" });
  assert.equal(calls[0][1].body, image);
});

test("an accepted mutation survives a transient poll failure without being submitted again", async () => {
  const calls = [];
  let pollAttempt = 0;
  const originalSetTimeout = global.setTimeout;
  global.setTimeout = (resolve, delay) => {
    if (delay > 1_000) return originalSetTimeout(resolve, delay);
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

test("a polling deadline retains the active job as nonterminal uncertainty", async () => {
  global.fetch = async () => response({
    ok: true,
    job: {
      id: "job-running",
      boardId: "board-9",
      state: "running",
      result: null,
      error: null,
    },
  });
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  await assert.rejects(
    client.pollJob("job-running", { interval: 0, maxDuration: 0 }),
    (error) => {
      assert.match(error.message, /deadline/i);
      assert.equal(error.jobId, "job-running");
      assert.equal(error.terminal, false);
      return true;
    },
  );
});

test("a polling deadline bounds a stalled job request", async () => {
  let releaseRequest;
  global.fetch = async () => new Promise((resolve) => {
    releaseRequest = () => resolve(response({
      ok: true,
      job: {
        id: "job-stalled",
        boardId: "board-9",
        state: "running",
        result: null,
        error: null,
      },
    }));
  });
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");
  const polling = client.pollJob("job-stalled", { interval: 0, maxDuration: 0 });

  try {
    const outcome = await Promise.race([
      polling.then(() => "resolved", () => "rejected"),
      new Promise((resolve) => setTimeout(() => resolve("still-pending"), 20)),
    ]);
    assert.equal(outcome, "rejected");
    await assert.rejects(polling, (error) => {
      assert.match(error.message, /deadline/i);
      assert.equal(error.jobId, "job-stalled");
      assert.equal(error.terminal, false);
      return true;
    });
  } finally {
    releaseRequest?.();
    await polling.catch(() => {});
  }
});

test("job polling does not start transport retries that outlive its deadline", async () => {
  let calls = 0;
  const originalSetTimeout = global.setTimeout;
  global.fetch = async () => {
    calls += 1;
    throw new TypeError("connection refused");
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  await assert.rejects(
    client.pollJob("job-deadline", { interval: 100, maxDuration: 0 }),
    (error) => {
      assert.match(error.message, /deadline/i);
      assert.equal(error.jobId, "job-deadline");
      return true;
    },
  );
  await new Promise((resolve) => originalSetTimeout(resolve, 250));
  assert.equal(calls, 1);
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
    if (path === "/api/boards") return response({ ok: true, jobId: "job-import" });
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
  assert.equal(calls[0][0], "/api/boards");
  assert.deepEqual(JSON.parse(calls[0][1].body), { type: "import", runRoot: "/workspace/cli-run" });
});

test("listBoards returns repository boards and diagnostics", async () => {
  const calls = [];
  global.fetch = async (path) => {
    calls.push(path);
    return response({
      ok: true,
      boards: [{ boardId: "example-board", location: "repository" }],
      diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(
    await client.listBoards(),
    {
      repositoryBoards: [{ boardId: "example-board", location: "repository" }],
      inProgressBoards: [],
      diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
    },
  );
  assert.deepEqual(calls, ["/api/boards"]);
});

test("openRepositoryBoard creates a workspace board from a repository board", async () => {
  const calls = [];
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (path === "/api/boards") {
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

  assert.deepEqual(await client.openRepositoryBoard("example board"), { boardId: "board-0001" });
  assert.deepEqual(calls.map(([path]) => path), [
    "/api/boards",
    "/api/jobs/job-library",
  ]);
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    type: "repository",
    boardId: "example board",
  });
});

test("finalSave patches the encoded board resource", async () => {
  const calls = [];
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (path === "/api/boards/board%209") {
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
  assert.equal(calls[0][0], "/api/boards/board%209");
  assert.equal(calls[0][1].method, "PATCH");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    boardId: "board 9",
    expectedRevisionId: "revision-1",
  });
});

test("validation reads encode the board and active revision", async () => {
  const calls = [];
  global.fetch = async (path) => {
    calls.push(path);
    return response({
      ok: true,
      boardId: "board 9",
      revisionId: "revision & 1",
      report: {
        boardId: "board 9",
        revisionId: "revision & 1",
        overallStatus: "passed",
        checks: [],
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.deepEqual(await client.getValidationReport("board 9", "revision & 1"), {
    boardId: "board 9",
    revisionId: "revision & 1",
    overallStatus: "passed",
    checks: [],
  });
  assert.deepEqual(calls, ["/api/boards/board%209/validation?revisionId=revision+%26+1"]);
});

test("validation run uses a revision-bound job", async () => {
  const calls = [];
  global.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    if (!path.startsWith("/api/jobs/")) {
      return response({ ok: true, jobId: "job-1", boardId: "board 9" });
    }
    const jobId = path.split("/").at(-1);
    return response({
      ok: true,
      job: {
        id: jobId,
        boardId: "board 9",
        state: "succeeded",
        result: {
          boardId: "board 9",
          revisionId: "revision-2",
          overallStatus: "passed",
          checks: [],
        },
        error: null,
      },
    });
  };
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");
  assert.deepEqual(
    await client.runValidation("board 9", "revision-2"),
    {
      boardId: "board 9",
      revisionId: "revision-2",
      overallStatus: "passed",
      checks: [],
    },
  );
  assert.equal(calls[0][0], "/api/boards/board%209/validation");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    boardId: "board 9",
    expectedRevisionId: "revision-2",
  });
});

test("the suite client has no commit, remote sync, or simulator lifecycle API", () => {
  const source = require("node:fs").readFileSync(require.resolve("../workbench-client.js"), "utf8");

  assert.doesNotMatch(source, /\/api\/[^"'`]*(?:commit|push|remote|simctl)\b/i);
  assert.doesNotMatch(
    source,
    /\b(?:async\s+function|function)\s+(?:commit|push|remote|simctl)\w*\s*\(/i,
  );
  assert.match(source, /\/api\/boards\//);
});

test("the suite client exposes no generated-app promotion API", () => {
  delete require.cache[require.resolve("../workbench-client.js")];
  const client = require("../workbench-client.js");

  assert.equal(client.getPromotionPreview, undefined);
  assert.equal(client.previewPromotion, undefined);
  assert.equal(client.savePromotion, undefined);
});
