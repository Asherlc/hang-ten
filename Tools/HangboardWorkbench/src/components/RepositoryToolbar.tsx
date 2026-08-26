import React from "react";

import type { WorkbenchActions, WorkbenchState } from "../types.ts";

export interface RepositoryToolbarProps {
  state: WorkbenchState;
  actions: WorkbenchActions;
}

export function RepositoryToolbar({ state, actions }: RepositoryToolbarProps) {
  const busy = state.busyBoard || state.busyGit;
  const branches = [...state.branches].sort();
  return (
    <div className="toolbar git-toolbar" aria-label="Repository tools">
      <span className="eyebrow" id="git-auth-status">
        {state.authenticated && state.username
          ? `Logged in as ${state.username}`
          : <a href="/auth/login">Log in with GitHub</a>}
      </span>
      <span className="eyebrow" id="git-status">
        {!state.initialized && !state.gitStatusKnown
          ? "Repository status"
          : state.currentBranch
          ? `${state.currentBranch}${state.hasUncommittedChanges ? " (uncommitted changes)" : ""}`
          : state.gitStatusKnown
            ? `Detached HEAD${state.hasUncommittedChanges ? " (uncommitted changes)" : ""}`
            : "Repository status unavailable"}
      </span>
      <select
        className="tool-select"
        id="git-branch-select"
        aria-label="Repository branch"
        value={state.selectedBranch}
        disabled={busy || branches.length === 0}
        onChange={(event) => actions.setSelectedBranch(event.currentTarget.value)}
      >
        {branches.length === 0
          ? <option value="">No branches detected</option>
          : branches.map((branch) => <option key={branch} value={branch}>{branch}</option>)}
      </select>
      <button className="tool-button" id="git-refresh-button" type="button" disabled={busy} onClick={() => void actions.refreshGit()}>Refresh</button>
      <button
        className="tool-button"
        id="git-switch-button"
        type="button"
        disabled={busy || !state.currentBranch || !state.selectedBranch || state.selectedBranch === state.currentBranch}
        onClick={() => void actions.switchBranch()}
      >Switch</button>
      <input
        className="tool-input"
        id="git-new-branch-name"
        type="text"
        aria-label="New branch name"
        placeholder="New branch name"
        value={state.newBranchName}
        disabled={busy}
        onInput={(event) => actions.setNewBranchName(event.currentTarget.value)}
      />
      <button
        className="tool-button"
        id="git-new-branch-button"
        type="button"
        disabled={busy || !state.newBranchName.trim()}
        onClick={() => void actions.createBranch()}
      >New Branch</button>
      {!state.hostedStorage && <>
        <input
          className="tool-input"
          id="git-commit-message"
          type="text"
          aria-label="Commit message"
          placeholder="Commit message"
          value={state.commitMessage}
          disabled={busy}
          onInput={(event) => actions.setCommitMessage(event.currentTarget.value)}
        />
        <button className="tool-button" id="git-commit-button" type="button" disabled={busy || !state.currentBranch} onClick={() => void actions.commitChanges()}>Commit</button>
        <button className="tool-button" id="git-push-button" type="button" disabled={busy || !state.currentBranch} onClick={() => void actions.pushBranch()}>Push</button>
      </>}
      <button className="tool-button accent" id="git-open-pr-button" type="button" disabled={busy || !state.currentBranch} onClick={() => void actions.openPullRequest()}>Open PR</button>
    </div>
  );
}
