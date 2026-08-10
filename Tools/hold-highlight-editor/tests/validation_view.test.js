const test = require("node:test");
const assert = require("node:assert/strict");

const {
  renderValidationReport,
  simulatorCommand,
  simulatorCommands,
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

test("validation report renders package, parity, semantic, plan, and promotion checks", () => {
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
  }, { saved: true, revisionId: "revision-1" });

  const text = visibleText(container);
  assert.match(text, /Package integrity.*Passed/);
  assert.match(text, /Hold-ID parity.*Failed/);
  assert.match(text, /Semantic routine resolution.*Stale/);
  assert.match(text, /Plan library freshness.*Not run/);
  assert.match(text, /Promotion status.*Passed/);
  assert.match(text, /stage 3 is missing hold-4/);
});

test("simulator handoff commands require a caller-supplied explicit UUID", () => {
  assert.equal(simulatorCommand("1234-UUID"), "platform=iOS Simulator,id=1234-UUID");
  assert.throws(() => simulatorCommand("booted"), /explicit simulator UUID/);
  assert.throws(() => simulatorCommand("unknown"), /explicit simulator UUID/);
  assert.throws(() => simulatorCommand(""), /explicit simulator UUID/);

  const commands = simulatorCommands("1234-UUID");
  assert.match(commands, /platform=iOS Simulator,id=1234-UUID/);
  assert.match(commands, /xcrun simctl install 1234-UUID/);
  assert.match(commands, /SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1/);
  assert.match(commands, /SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1/);
  assert.match(commands, /xcrun simctl io 1234-UUID screenshot/);
  assert.doesNotMatch(commands, /simctl\s+(?:create|delete|boot|erase)\b/);
});
