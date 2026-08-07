const test = require("node:test");
const assert = require("node:assert/strict");

const { timelineFor, canApprove, openingSections } = require("../workbench-model.js");

test("timeline marks current, complete, upcoming, and stale stages", () => {
  const rows = timelineFor({ stage: 3, state: "awaiting_review", staleFromStage: 2 });
  assert.deepEqual(rows.map((row) => row.state), ["complete", "complete", "stale", "current", "upcoming", "upcoming", "upcoming"]);
});

test("timeline completes the final stage after a completed workflow", () => {
  const rows = timelineFor({ stage: 6, state: "complete" });
  assert.deepEqual(rows.map((row) => row.state), ["complete", "complete", "complete", "complete", "complete", "complete", "complete"]);
});

test("stale stages take precedence in a completed workflow", () => {
  const rows = timelineFor({ stage: 6, state: "complete", staleFromStage: 2 });
  assert.deepEqual(rows.map((row) => row.state), ["complete", "complete", "stale", "stale", "stale", "stale", "stale"]);
});

test("canApprove permits an unchanged generated checkpoint and rejects invalid drafts", () => {
  assert.equal(canApprove({ state: "awaiting_review" }), true);
  assert.equal(canApprove({ state: "awaiting_review" }, { valid: false }), false);
  assert.equal(canApprove({ state: "awaiting_review" }, { saving: true }), false);
  assert.equal(canApprove({ state: "awaiting_review" }, { errors: ["missing contour"] }), false);
  assert.equal(canApprove({ state: "processing" }, { valid: true }), false);
});

test("openingSections separates repository boards from unfinished runtime work", () => {
  assert.deepEqual(openingSections(
    [{ boardId: "alpha", displayName: "Alpha", currentVersionId: "revision-0001" }],
    [
      { boardId: "board-0001", productName: "Alpha", repositoryBoardId: "alpha", repositoryVersionId: "revision-0001", saved: true },
      { boardId: "board-0002", productName: "Beta", repositoryBoardId: null, repositoryVersionId: null, saved: false },
      { boardId: "board-0003", productName: "Alpha edit", repositoryBoardId: "alpha", repositoryVersionId: "revision-0001", saved: false },
    ],
  ), {
    library: [{ boardId: "alpha", displayName: "Alpha", currentVersionId: "revision-0001" }],
    inProgress: [
      { boardId: "board-0003", productName: "Alpha edit", repositoryBoardId: "alpha", repositoryVersionId: "revision-0001", saved: false },
      { boardId: "board-0002", productName: "Beta", repositoryBoardId: null, repositoryVersionId: null, saved: false },
    ],
  });
});

test("openingSections sorts copied sections by case-insensitive labels and stable IDs", () => {
  const libraryBoards = [
    { boardId: "charlie", displayName: "charlie", currentVersionId: "revision-0001" },
    { boardId: "alpha-2", displayName: "Alpha", currentVersionId: "revision-0002" },
    { boardId: "alpha-1", displayName: "alpha", currentVersionId: "revision-0001" },
  ];
  const runtimeBoards = [
    { boardId: "bravo-2", productName: "Bravo", saved: false },
    { boardId: "bravo-1", productName: "bravo", saved: false },
  ];

  const sections = openingSections(libraryBoards, runtimeBoards);

  assert.deepEqual(sections.library.map(({ boardId }) => boardId), ["alpha-1", "alpha-2", "charlie"]);
  assert.deepEqual(sections.inProgress.map(({ boardId }) => boardId), ["bravo-1", "bravo-2"]);
  assert.notEqual(sections.library, libraryBoards);
  assert.notEqual(sections.inProgress, runtimeBoards);
});
