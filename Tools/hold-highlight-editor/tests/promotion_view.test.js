const test = require("node:test");
const assert = require("node:assert/strict");

const {
  groupPromotionFiles,
  promotionStatus,
  saveActionState,
  createPromotionController,
} = require("../promotion-view.js");

const profile = Object.freeze({
  schemaVersion: 1,
  boardID: "metolius.wood-grips.compact-ii",
  manufacturer: "Metolius",
  name: "Wood Grips Compact II",
  subtitle: "A compact wood board.",
  dimensions: "24\" × 6.2\"",
  aspectRatio: 3.88,
  productURL: "https://example.test/compact-ii",
});

function preview(overrides = {}) {
  return {
    boardId: "metolius.wood-grips.compact-ii",
    revisionId: "revision-1",
    revisionToken: "native-revision-token",
    baseRef: "main",
    previewToken: "preview-token-1",
    files: [
      { path: "HangTen/Models/TrainingModels.swift", unifiedDiff: "- old metadata\n+ new metadata" },
      { path: "HangTen/Views/MetoliusCompactIIDesign.swift", unifiedDiff: "- old path\n+ new path" },
      { path: "HangTen/Models/PlanStorage.swift", unifiedDiff: "- old store\n+ new store" },
      { path: "HangTen/Resources/PlanLibrary.json", unifiedDiff: "- old plan\n+ new plan" },
    ],
    issues: [],
    ...overrides,
  };
}

function suite(board = { state: "complete", boardId: "board-7", revisionId: "revision-1" }) {
  return { activeBoard: board, activeRevision: board.revisionId };
}

function controllerHarness({ board, client = {}, onPromotion = () => {} } = {}) {
  let currentSuite = suite(board);
  const renders = [];
  const controller = createPromotionController({
    client: {
      async getPromotionPreview() { return null; },
      async previewPromotion() { return preview(); },
      async savePromotion() { return { saved: true, paths: [] }; },
      ...client,
    },
    getSuiteState: () => currentSuite,
    onPromotion,
    render: () => renders.push(controller.getState()),
  });
  return {
    controller,
    renders,
    setSuite(next) { currentSuite = next; },
  };
}

test("promotion files are grouped by metadata, geometry, and plans with path-bound issues", () => {
  const groups = groupPromotionFiles(preview().files, [
    { path: "HangTen/Views/MetoliusCompactIIDesign.swift", code: "target_changed", message: "Local geometry changed." },
    { path: "", code: "package_invalid", message: "Stage 4 approval is incomplete." },
  ]);

  assert.deepEqual(groups.map((group) => group.heading), ["Metadata", "Geometry", "Plans"]);
  assert.deepEqual(groups[0].files.map((file) => file.path), ["HangTen/Models/TrainingModels.swift"]);
  assert.deepEqual(groups[1].files[0].issues, [{ path: "HangTen/Views/MetoliusCompactIIDesign.swift", code: "target_changed", message: "Local geometry changed." }]);
  assert.deepEqual(groups[2].files.map((file) => file.path), [
    "HangTen/Models/PlanStorage.swift",
    "HangTen/Resources/PlanLibrary.json",
  ]);
  assert.deepEqual(groups.unassignedIssues, [{ path: "", code: "package_invalid", message: "Stage 4 approval is incomplete." }]);
});

test("promotion status and save action block issues and stale preview tokens", () => {
  assert.equal(promotionStatus(preview()).label, "Ready to save locally");
  assert.equal(promotionStatus(preview({ issues: [{ path: "HangTen/Models/TrainingModels.swift", message: "Dirty target" }] })).label, "Blocked by issues");
  assert.equal(promotionStatus(preview({ previewToken: "", revisionId: "revision-1" }), { expectedRevisionId: "revision-1" }).label, "Preview is stale");
  assert.equal(saveActionState({ preview: preview({ issues: [{ message: "Dirty target" }] }), busy: false }).disabled, true);
  assert.equal(saveActionState({ preview: preview(), busy: false, expectedRevisionId: "revision-2" }).disabled, true);
  assert.equal(saveActionState({ preview: preview(), busy: false, expectedRevisionId: "revision-1" }).disabled, false);
});

test("the promotion module never uses innerHTML for server-provided unified diffs", () => {
  const source = require("node:fs").readFileSync(require.resolve("../promotion-view.js"), "utf8");
  assert.doesNotMatch(source, /innerHTML/);
});

test("preview generation blocks an incomplete board before a job is started", async () => {
  let calls = 0;
  const { controller } = controllerHarness({
    board: { state: "awaiting_review", boardId: "board-7", revisionId: "revision-1" },
    client: { async previewPromotion() { calls += 1; return preview(); } },
  });
  controller.setProfile(profile);

  await controller.generatePreview();

  assert.equal(calls, 0);
  assert.match(controller.getState().error, /complete and approved/i);
});

test("preview generation blocks a missing explicit profile before a job is started", async () => {
  let calls = 0;
  const { controller } = controllerHarness({
    client: { async previewPromotion() { calls += 1; return preview(); } },
  });

  await controller.generatePreview();

  assert.equal(calls, 0);
  assert.match(controller.getState().error, /explicit iOS promotion profile/i);
});

test("preview result from a stale board context is discarded without repopulating state", async () => {
  let resolvePreview;
  const { controller, setSuite } = controllerHarness({
    client: { previewPromotion: () => new Promise((resolve) => { resolvePreview = resolve; }) },
  });
  controller.setProfile(profile);
  const pending = controller.generatePreview();
  setSuite(suite({ state: "complete", boardId: "board-8", revisionId: "revision-1" }));
  resolvePreview(preview());
  await pending;

  assert.equal(controller.getState().preview, null);
  assert.equal(controller.getState().saved, false);
  assert.equal(controller.getState().error, "");
  assert.equal(controller.getState().profile.boardID, "");
});

test("switching boards after a local save clears the saved promotion state", () => {
  const { controller, setSuite } = controllerHarness();
  controller.setProfile(profile);
  controller.replacePreview(preview({ saved: true }));

  setSuite(suite({ state: "complete", boardId: "board-8", revisionId: "revision-1" }));
  const state = controller.getState();

  assert.equal(state.preview, null);
  assert.equal(state.saved, false);
  assert.equal(state.error, "");
});

test("switching boards resets the explicit promotion profile", () => {
  const { controller, setSuite } = controllerHarness();
  controller.setProfile(profile);

  setSuite(suite({ state: "complete", boardId: "board-8", revisionId: "revision-1" }));
  const state = controller.getState();

  assert.deepEqual(state.profile, {
    schemaVersion: 1,
    boardID: "",
    manufacturer: "",
    name: "",
    subtitle: "",
    dimensions: "",
    aspectRatio: "",
    productURL: "",
  });
});

test("a dirty target returned by preview keeps save disabled", async () => {
  const dirty = preview({ issues: [{ path: "HangTen/Models/TrainingModels.swift", code: "target_changed", message: "Target changed since main." }] });
  const { controller } = controllerHarness({ client: { async previewPromotion() { return dirty; } } });
  controller.setProfile(profile);

  await controller.generatePreview();

  assert.equal(controller.saveState().disabled, true);
  assert.match(controller.saveState().reason, /issue/i);
});

test("successful preview and save mark promotion saved only after saved true", async () => {
  const promotions = [];
  let saveStarted = false;
  let resolveSave;
  const fresh = preview();
  const { controller } = controllerHarness({
    client: {
      async previewPromotion() { return fresh; },
      async getPromotionPreview() { return fresh; },
      savePromotion() {
        saveStarted = true;
        return new Promise((resolve) => { resolveSave = resolve; });
      },
    },
    onPromotion: (result) => promotions.push(result),
  });
  controller.setProfile(profile);
  await controller.generatePreview();
  const pending = controller.saveLocally();
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(saveStarted, true);
  assert.equal(controller.getState().saved, false);
  assert.equal(promotions.at(-1)?.saved, undefined);
  resolveSave({ saved: true, paths: fresh.files.map((file) => file.path) });
  await pending;

  assert.equal(controller.getState().saved, true);
  assert.equal(promotions.at(-1)?.saved, true);
});

test("save re-fetches the preview token and keeps the visible diff after an accepted job fails", async () => {
  const initial = preview({ previewToken: "preview-token" });
  const fresh = preview({ previewToken: "preview-token" });
  const saveCalls = [];
  const { controller } = controllerHarness({
    client: {
      async getPromotionPreview() { return fresh; },
      async savePromotion(...args) {
        saveCalls.push(args);
        const error = new Error("Promotion preview is stale");
        error.terminal = true;
        throw error;
      },
    },
  });
  controller.setProfile(profile);
  controller.replacePreview(initial);

  await controller.saveLocally();

  assert.equal(saveCalls.length, 1);
  assert.equal(saveCalls[0][3], "preview-token");
  assert.equal(controller.getState().preview.previewToken, "preview-token");
  assert.equal(controller.getState().saved, false);
  assert.match(controller.getState().error, /preview is stale/i);
});

test("save stops for review when the re-fetched preview token changed", async () => {
  const initial = preview({ previewToken: "old-token" });
  const refreshed = preview({ previewToken: "new-token" });
  let saveCalls = 0;
  const { controller } = controllerHarness({
    client: {
      async getPromotionPreview() { return refreshed; },
      async savePromotion() { saveCalls += 1; return { saved: true }; },
    },
  });
  controller.setProfile(profile);
  controller.replacePreview(initial);

  await controller.saveLocally();

  assert.equal(saveCalls, 0);
  assert.equal(controller.getState().preview.previewToken, "new-token");
  assert.match(controller.getState().error, /preview changed/i);
  assert.equal(controller.getState().saved, false);
});
