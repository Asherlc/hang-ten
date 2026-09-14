import assert from "node:assert/strict";
import test from "node:test";

import { WorkbenchApp } from "../src/WorkbenchApp.tsx";
import * as pathEditor from "../src/path-editor.ts";
import type {
  AuthStatus,
  Board,
  BoardSummary,
  BrowserRuntime,
  CommitResult,
  EditorDocument,
  GitStatus,
  PullRequestResult,
  PushResult,
  WorkbenchClient,
  WorkbenchDependencies,
} from "../src/types.ts";
import * as controller from "../src/workbench-controller.ts";
import { renderReact } from "./react-harness.tsx";

function documentFixture(): EditorDocument {
  return {
    presentationID: "primary",
    contacts: [{
      id: "edge-left",
      equipmentObjectID: "primary",
      name: "Left edge",
      kind: "edge",
      features: ["largeEdge"],
      gripTypes: ["openHand"],
      depthRangeMillimeters: { lowerBound: 18, upperBound: 20 },
    }],
    canvas: { width: 100, height: 60 },
    regions: [{
      id: 1,
      key: "edge-left-piece-0",
      displayPath: "M 10 10 L 40 10 L 40 40 L 10 40 Z",
      metadata: {
        contactID: "edge-left",
        pieceIndex: 0,
        presentationID: "primary",
      },
      treatment: { type: "surface" },
    }],
  };
}

function boardFixture(document = documentFixture()): Board {
  return {
    boardId: "fixture.board",
    displayName: "Fixture Board",
    contactCount: document.contacts.length,
    imageUrl: "/api/boards/fixture.board/image",
    document,
  };
}

function gitStatus(): GitStatus {
  return { ok: true, currentBranch: "main", branches: ["main"], dirty: false, statusLines: [] };
}

function runtimeFixture(): { runtime: BrowserRuntime; succeedImage(): void } {
  const pending: HTMLImageElement[] = [];
  const runtime: BrowserRuntime = {
    async fetch() { throw new Error("fetch is not used by app tests"); },
    location: { assign() {} },
    confirm: () => true,
    prompt: () => null,
    createImage() {
      const image = document.createElement("img");
      Object.defineProperty(image, "src", {
        configurable: true,
        set() { pending.push(image); },
      });
      return image;
    },
  };
  return {
    runtime,
    succeedImage() {
      const image = pending.shift();
      if (!image) throw new Error("No pending board image");
      image.onload?.(new Event("load"));
    },
  };
}

function clientFixture(overrides: Partial<WorkbenchClient> = {}): WorkbenchClient {
  const board = boardFixture();
  const summary: BoardSummary = {
    boardId: board.boardId,
    displayName: board.displayName,
    contactCount: board.contactCount,
    imageUrl: board.imageUrl,
    needsAttention: false,
  };
  return {
    async listBoards() { return [summary]; },
    async getBoard() { return board; },
    async saveBoard(_boardID, document) { return boardFixture(document); },
    async deletePresentation() { return board; },
    async getGitStatus() { return gitStatus(); },
    async getAuthStatus(): Promise<AuthStatus> { return { ok: true, authenticated: false }; },
    async listBranches() { return gitStatus(); },
    async switchBranch(branchName) { return branchName; },
    async createBranch(branchName) { return branchName; },
    async commitBoardChanges(message): Promise<CommitResult> {
      return { ok: true, commit: "abcdef0123456789", branch: "main", message };
    },
    async pushBranch(): Promise<PushResult> { return { ok: true, branch: "main", remote: "origin" }; },
    async openPullRequest(): Promise<PullRequestResult> {
      return { ok: true, branch: "main", url: "https://example.com/pr/1" };
    },
    ...overrides,
  };
}

function dependencies(client: WorkbenchClient, runtime: BrowserRuntime): WorkbenchDependencies {
  return {
    client,
    runtime,
    controller,
    pathEditor,
    dialogs: { confirm: () => true, prompt: () => null },
  };
}

async function openFirstBoard(harness: Awaited<ReturnType<typeof renderReact>>, succeedImage: () => void) {
  await harness.flush();
  assert.equal(harness.text("#board-list"), "Fixture Board1 contacts");
  await harness.click("#board-list button");
  succeedImage();
  await harness.flush();
  assert.equal(harness.text("#board-name"), "Fixture Board");
}

test("WorkbenchApp edits contact facts and saves a native contact document", async () => {
  let savedDocument: EditorDocument | undefined;
  const client = clientFixture({
    async saveBoard(_boardID, document) {
      savedDocument = document;
      return boardFixture(document);
    },
  });
  const image = runtimeFixture();
  const harness = await renderReact(
    <WorkbenchApp dependencies={dependencies(client, image.runtime)} />,
  );
  try {
    await openFirstBoard(harness, image.succeedImage);
    await harness.click("[data-contact-key='edge-left-piece-0']");
    await harness.input("#contact-name", "Source-backed edge");
    assert.equal(harness.text("#save-state"), "Unsaved changes");
    await harness.click("#save-button");
    await harness.flush();

    assert.equal(savedDocument?.contacts[0]?.name, "Source-backed edge");
    assert.equal(savedDocument?.regions[0]?.metadata.contactID, "edge-left");
    assert.equal("name" in (savedDocument?.regions[0] ?? {}), false);
    assert.equal(harness.text("#save-state"), "Saved");
  } finally {
    await harness.cleanup();
  }
});

test("WorkbenchApp keeps contact edits dirty and reports a failed save", async () => {
  const client = clientFixture({
    async saveBoard() { throw new Error("write conflict"); },
  });
  const image = runtimeFixture();
  const harness = await renderReact(
    <WorkbenchApp dependencies={dependencies(client, image.runtime)} />,
  );
  try {
    await openFirstBoard(harness, image.succeedImage);
    await harness.click("[data-contact-key='edge-left-piece-0']");
    await harness.input("#contact-name", "Edited edge");
    await harness.click("#save-button");
    await harness.flush();

    assert.equal(harness.text("#save-state"), "Unsaved changes");
    assert.match(harness.container.textContent ?? "", /write conflict/u);
    assert.equal(harness.documentValue("#contact-name"), "Edited edge");
  } finally {
    await harness.cleanup();
  }
});
