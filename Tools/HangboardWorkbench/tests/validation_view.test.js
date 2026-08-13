const test = require("node:test");
const assert = require("node:assert/strict");

const {
  renderValidationReport,
  simulatorCommand,
  simulatorCommands,
  createValidationController,
} = require("../validation-view.js");

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = tagName;
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.className = "";
    this.textContent = "";
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  replaceChildren(...children) {
    this.children = children;
    this.textContent = "";
  }
}

function fakeContainer() {
  const document = {
    createElement(tagName) { return new FakeElement(tagName, document); },
  };
  return new FakeElement("div", document);
}

function visibleText(node) {
  return [node.textContent, ...node.children.map(visibleText)].filter(Boolean).join(" ");
}

test("validation report renders package, parity, semantic, and plan checks", () => {
  const container = fakeContainer();

  renderValidationReport(container, {
    boardId: "board-7",
    revisionId: "revision-1",
    overallStatus: "failed",
    checks: [
      { checkId: "package-readiness", status: "passed", message: "package is ready", details: [] },
      { checkId: "hold-id-parity", status: "failed", message: "hold IDs differ", details: ["stage 3 is missing hold-4"] },
      { checkId: "semantic-routine-resolution", status: "stale", message: "routine targets changed", details: [] },
      { checkId: "plan-library", status: "not_run", message: "not run", details: [] },
    ],
  });

  const text = visibleText(container);
  assert.match(text, /Package integrity.*Passed/);
  assert.match(text, /Hold-ID parity.*Failed/);
  assert.match(text, /Semantic routine resolution.*Stale/);
  assert.match(text, /Plan library freshness.*Not run/);
  assert.doesNotMatch(text, /Promotion status/);
  assert.match(text, /stage 3 is missing hold-4/);
});

test("validation statuses reject inherited object property names", () => {
  for (const status of ["constructor", "toString", "valueOf"]) {
    const container = fakeContainer();
    renderValidationReport(container, { checks: [{ checkId: "package-readiness", status }] });
    assert.match(visibleText(container), /Package integrity Not run/);
  }
});

test("a late report after a board switch cannot repopulate validation", async () => {
  let resolveReport;
  let suite = { activeBoard: { boardId: "board-7", revisionId: "revision-1" }, activeRevision: "revision-1" };
  const controller = createValidationController({
    client: {
      getValidationReport: () => new Promise((resolve) => { resolveReport = resolve; }),
      async runValidation() { return null; },
    },
    getSuiteState: () => suite,
  });
  const pending = controller.loadCachedReport();
  suite = { activeBoard: { boardId: "board-8", revisionId: "revision-1" }, activeRevision: "revision-1" };
  resolveReport({ overallStatus: "passed" });
  await pending;
  assert.equal(controller.getState().report, null);
});

test("a superseded validation report cannot replace the newer report", async () => {
  const resolves = [];
  const suite = { activeBoard: { boardId: "board-7", revisionId: "revision-1" }, activeRevision: "revision-1" };
  const controller = createValidationController({
    client: {
      getValidationReport: () => new Promise((resolve) => resolves.push(resolve)),
      async runValidation() { return null; },
    },
    getSuiteState: () => suite,
  });
  const older = controller.loadCachedReport();
  const newer = controller.loadCachedReport();
  resolves[1]({ overallStatus: "passed", checks: [] });
  await newer;
  resolves[0]({ overallStatus: "failed", checks: [] });
  await older;
  assert.equal(controller.getState().report.overallStatus, "passed");
});

test("simulator handoff commands require a caller-supplied canonical UUID", () => {
  const simulatorUUID = "12345678-1234-ABCD-1234-123456789ABC";
  assert.equal(simulatorCommand(simulatorUUID), `platform=iOS Simulator,id=${simulatorUUID}`);
  assert.equal(
    simulatorCommand(simulatorUUID.toLowerCase()),
    `platform=iOS Simulator,id=${simulatorUUID.toLowerCase()}`,
  );
  assert.throws(() => simulatorCommand("booted"), /explicit simulator UUID/);
  assert.throws(() => simulatorCommand("unknown"), /explicit simulator UUID/);
  assert.throws(() => simulatorCommand(""), /explicit simulator UUID/);
  assert.throws(() => simulatorCommand("not-a-uuid"), /explicit simulator UUID/);
  assert.throws(() => simulatorCommand("12345678-1234-1234-1234-123456789ABC; rm -rf /"), /explicit simulator UUID/);
  assert.throws(() => simulatorCommands("not-a-uuid"), /explicit simulator UUID/);

  const commands = simulatorCommands(simulatorUUID);
  assert.match(commands, new RegExp(`platform=iOS Simulator,id=${simulatorUUID}`));
  assert.match(commands, new RegExp(`xcrun simctl install ${simulatorUUID}`));
  assert.match(commands, /SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1/);
  assert.match(commands, /SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1/);
  assert.match(commands, new RegExp(`xcrun simctl io ${simulatorUUID} screenshot`));
  assert.doesNotMatch(commands, /simctl\s+(?:create|delete|boot|erase)\b/);
});
