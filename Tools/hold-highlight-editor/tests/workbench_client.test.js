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
