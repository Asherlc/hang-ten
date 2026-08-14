const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function response(payload, { ok = true, status = 200 } = {}) {
  return { ok, status, async json() { return payload; } };
}

function freshClient() {
  delete require.cache[require.resolve("../workbench-client.js")];
  return require("../workbench-client.js");
}

test("the browser client lists and opens direct boards", async () => {
  const calls = [];
  global.fetch = async (request) => {
    calls.push(request);
    if (request === "/api/boards") {
      return response({ ok: true, boards: [{ boardId: "compact", displayName: "Compact", holdCount: 10 }] });
    }
    return response({
      ok: true,
      board: {
        boardId: "compact",
        imageUrl: "/api/boards/compact/image",
        document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] },
      },
    });
  };
  const client = freshClient();

  assert.deepEqual(await client.listBoards(), [{ boardId: "compact", displayName: "Compact", holdCount: 10 }]);
  assert.equal((await client.getBoard("compact")).boardId, "compact");
  assert.deepEqual(calls, ["/api/boards", "/api/boards/compact"]);
});

test("the browser client saves one direct editor document with PUT", async () => {
  const calls = [];
  global.fetch = async (request, options) => {
    calls.push([request, options]);
    return response({ ok: true, board: { boardId: "compact", document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] } } });
  };
  const client = freshClient();
  const document = { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] };

  await client.saveBoard("compact", document);

  assert.equal(calls[0][0], "/api/boards/compact");
  assert.equal(calls[0][1].method, "PUT");
  assert.deepEqual(JSON.parse(calls[0][1].body), document);
});

test("direct board loading commits image and holds together and preserves the prior editor on failure", async () => {
  const { loadBoardAtomically } = require("../workbench-controller.js");
  const prior = { boardId: "prior", image: { href: "prior.png" }, document: { regions: [{ key: "prior" }] } };
  const candidate = {
    boardId: "compact",
    imageUrl: "/api/boards/compact/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [{ key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" }] },
  };
  const committed = [];
  const success = await loadBoardAtomically({
    boardId: "compact",
    getBoard: async () => candidate,
    loadImage: async (href) => ({ href, naturalWidth: 100, naturalHeight: 50 }),
    commit: (value) => committed.push(value),
  });
  assert.equal(success.board.boardId, "compact");
  assert.equal(committed.length, 1);

  await assert.rejects(
    loadBoardAtomically({
      boardId: "broken",
      getBoard: async () => ({ ...candidate, boardId: "broken" }),
      loadImage: async () => { throw new Error("Image unavailable"); },
      commit: (value) => committed.push(value),
    }),
    /Image unavailable/,
  );
  assert.deepEqual(committed, [success]);
  assert.equal(prior.boardId, "prior");
});

test("the direct editor model rejects duplicate and open hold paths before saving", () => {
  const { validateEditorDocument } = require("../workbench-controller.js");
  const base = { schemaVersion: 1, canvas: { width: 100, height: 50 } };
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" },
    { key: "hold-1", displayPath: "M 30 1 L 40 1 L 40 20 Z" },
  ] }), /unique hold key/);
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20" },
  ] }), /one closed contour/);
});

test("a rejected save keeps the editor document untouched", async () => {
  const { saveBoardAtomically } = require("../workbench-controller.js");
  const document = {
    schemaVersion: 1,
    canvas: { width: 100, height: 50 },
    regions: [{ key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" }],
  };
  let commits = 0;
  await assert.rejects(
    saveBoardAtomically({
      boardId: "compact",
      document,
      save: async () => { throw new Error("Hold path crosses itself"); },
      commit: () => { commits += 1; },
    }),
    /Hold path crosses itself/,
  );
  assert.equal(commits, 0);
  assert.equal(document.regions[0].displayPath, "M 1 1 L 20 1 L 20 20 Z");
});

test("browser source contains only direct board vocabulary", () => {
  const root = path.join(__dirname, "..");
  const files = ["app.js", "index.html", "workbench-client.js", "workbench-controller.js"];
  const forbidden = /recent runs|in progress|checkpoint|approval|promotion|static mode|\bpipeline\b|\bstage\b|\brevision\b|\bretry\b|final-save/iu;
  for (const file of files) {
    assert.doesNotMatch(fs.readFileSync(path.join(root, file), "utf8"), forbidden, file);
  }
});
