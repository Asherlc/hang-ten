# CI Ruleset Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure GitHub Actions emits the checks that the active `Main` ruleset requires after normal and automatic pull-request base changes, while keeping the expensive Release-device build post-merge only.

**Architecture:** The repository workflow becomes recoverable and responsive to PR base edits by accepting `edited` and `workflow_dispatch` events. The active repository ruleset is then narrowed to the two jobs that execute on pull requests, preventing auto-merge from waiting for the intentionally post-merge Release-device job.

**Tech Stack:** GitHub Actions YAML, GitHub repository rulesets API, GitHub CLI.

## Global Constraints

- Preserve `Build (Release device)` as a post-merge-only job; do not remove `if: github.event_name != 'pull_request'`.
- Preserve the required check names `Build (Debug simulator)` and `Test (iOS Simulator)` exactly.
- Do not alter application source code, merge methods, review requirements, or unrelated ruleset rules.
- The active ruleset is `Main` (ID `20264425`) and applies to `~DEFAULT_BRANCH`.

---

### Task 1: Make PR CI triggerable after stack/base updates

**Files:**
- Modify: `.github/workflows/ci.yml:4-14`

**Interfaces:**
- Consumes: GitHub `pull_request` actions `opened`, `synchronize`, `reopened`, and `ready_for_review`.
- Produces: CI workflow runs for `pull_request.edited` and manually dispatched runs, publishing the unchanged `Build (Debug simulator)` and `Test (iOS Simulator)` check names.

- [ ] **Step 1: Add the missing PR action and manual event**

  Update the workflow trigger block to include `edited` and `workflow_dispatch`:

  ```yaml
  on:
    pull_request:
      branches:
        - main
      types:
        - opened
        - synchronize
        - reopened
        - ready_for_review
        - edited
    workflow_dispatch:
    push:
      branches:
        - main
    merge_group:
  ```

- [ ] **Step 2: Verify the workflow change is scoped and structurally valid**

  Run:

  ```bash
  git diff --check
  git diff -- .github/workflows/ci.yml
  gh workflow view ci.yml --repo Asherlc/hang-ten
  ```

  Expected: no whitespace errors; the only workflow changes are `edited` and `workflow_dispatch`; GitHub recognizes the `CI` workflow.

- [ ] **Step 3: Commit the workflow change**

  ```bash
  git add .github/workflows/ci.yml
  git commit -m "ci: trigger checks after PR base updates"
  git push origin HEAD
  ```

### Task 2: Align the active Main ruleset with PR-visible checks

**Files:**
- Create: `.context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset.json` (temporary API payload; remove after the successful API update)
- External configuration: GitHub repository ruleset `Asherlc/hang-ten` / `20264425`

**Interfaces:**
- Consumes: ruleset `20264425` with its current deletion, non-fast-forward, pull-request, code-scanning, and code-quality rules.
- Produces: the same active `Main` ruleset, except its `required_status_checks` list contains exactly `Build (Debug simulator)` and `Test (iOS Simulator)` with integration ID `15368`.

- [ ] **Step 1: Read and save the existing ruleset before changing it**

  Run:

  ```bash
  mkdir -p .context
  gh api repos/Asherlc/hang-ten/rulesets/20264425 > .context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset-before.json
  ```

  Expected: the saved document shows the existing rules unchanged except for the stale required status-check list to be corrected.

- [ ] **Step 2: Create the complete replacement payload preserving every unrelated rule**

  Create `.context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset.json` with this exact JSON:

  ```json
  {
    "name": "Main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {
      "ref_name": {
        "include": ["~DEFAULT_BRANCH"],
        "exclude": []
      }
    },
    "rules": [
      {"type": "deletion"},
      {"type": "non_fast_forward"},
      {
        "type": "pull_request",
        "parameters": {
          "required_approving_review_count": 0,
          "dismiss_stale_reviews_on_push": false,
          "required_reviewers": [],
          "require_code_owner_review": false,
          "require_last_push_approval": false,
          "required_review_thread_resolution": true,
          "allowed_merge_methods": ["merge", "squash", "rebase"]
        }
      },
      {
        "type": "code_scanning",
        "parameters": {
          "code_scanning_tools": [
            {
              "tool": "CodeQL",
              "security_alerts_threshold": "high_or_higher",
              "alerts_threshold": "errors"
            }
          ]
        }
      },
      {"type": "code_quality", "parameters": {"severity": "warnings"}},
      {
        "type": "required_status_checks",
        "parameters": {
          "strict_required_status_checks_policy": false,
          "do_not_enforce_on_create": false,
          "required_status_checks": [
            {"context": "Build (Debug simulator)", "integration_id": 15368},
            {"context": "Test (iOS Simulator)", "integration_id": 15368}
          ]
        }
      }
    ],
    "bypass_actors": []
  }
  ```

- [ ] **Step 3: Apply the exact ruleset replacement and verify its shape**

  Run:

  ```bash
  gh api --method PUT repos/Asherlc/hang-ten/rulesets/20264425 --input .context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset.json
  gh api repos/Asherlc/hang-ten/rules/branches/main --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context'
  ```

  Expected output contains exactly:

  ```text
  Build (Debug simulator)
  Test (iOS Simulator)
  ```

- [ ] **Step 4: Remove the workspace-owned API payloads**

  Run:

  ```bash
  rm -f .context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset.json .context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset-before.json
  test ! -e .context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset.json
  test ! -e .context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset-before.json
  ```

  Expected: both exact workspace-owned temporary files are absent; no unrelated `.context` entries are changed.

### Task 3: Verify the end-to-end escape hatch

**Files:**
- Modify: none
- External state: GitHub Actions run for `agent/force-sensor-entralpi` and PR #104 check rollup.

**Interfaces:**
- Consumes: the pushed CI workflow and the aligned active Main ruleset.
- Produces: fresh CI checks on the selected branch and a PR status rollup containing the two required check contexts.

- [ ] **Step 1: Start CI manually for the blocked PR branch**

  Run:

  ```bash
  gh workflow run ci.yml --repo Asherlc/hang-ten --ref agent/force-sensor-entralpi
  gh run list --repo Asherlc/hang-ten --workflow ci.yml --branch agent/force-sensor-entralpi --limit 1
  ```

  Expected: a new CI run appears for `agent/force-sensor-entralpi`.

- [ ] **Step 2: Wait for CI and inspect the required contexts**

  Run:

  ```bash
  gh run watch --repo Asherlc/hang-ten <RUN_ID> --exit-status
  gh pr view 104 --repo Asherlc/hang-ten --json mergeable,mergeStateStatus,statusCheckRollup
  ```

  Expected: the run succeeds and the check rollup contains successful `Build (Debug simulator)` and `Test (iOS Simulator)` entries. `Build (Release device)` is not required for PR #104.

- [ ] **Step 3: Confirm auto-merge progresses or report the remaining independent blocker**

  Run:

  ```bash
  gh pr view 104 --repo Asherlc/hang-ten --json state,mergedAt,mergeStateStatus,autoMergeRequest,url
  ```

  Expected: auto-merge can proceed once the two required checks pass. If the PR remains open, report the precise GitHub field or check that blocks it; do not bypass it silently.

### Task 4: Land the CI recovery trigger on main

**Files:**
- Modify: `.github/workflows/ci.yml:4-15,141`
- External state: a clean, workspace-scoped GitHub branch and pull request targeting `main`

**Interfaces:**
- Consumes: reviewed commits `544a51d` and `d3c5615`, which contain only the CI trigger and Release-device guard changes.
- Produces: the approved CI workflow on `main`, making `workflow_dispatch` available for PR #104 without merging unrelated force-sensor commits.

- [ ] **Step 1: Create an isolated clean branch from the current remote main**

  Use an exact workspace-scoped branch name and temporary worktree:

  ```bash
  git fetch origin
  git worktree add .context/relieved-peacock-climbro-ci-ruleset-recovery \
    -b agent/relieved-peacock-climbro-ci-ruleset-recovery origin/main
  cd .context/relieved-peacock-climbro-ci-ruleset-recovery
  ```

  Expected: the branch starts at `origin/main` and contains no sensor-adapter or planning changes.

- [ ] **Step 2: Cherry-pick only the two reviewed workflow commits**

  ```bash
  git cherry-pick 544a51da383440e84ead2cd1f4f745b454fda931
  git cherry-pick d3c5615c949f6c0e9514949f0fb6def7fd85be25
  git diff --check origin/main...HEAD
  git diff --name-only origin/main...HEAD
  ```

  Expected: no whitespace errors; the only changed file is `.github/workflows/ci.yml`.

- [ ] **Step 3: Push and open a CI-only pull request**

  ```bash
  git push -u origin agent/relieved-peacock-climbro-ci-ruleset-recovery
  gh pr create --repo Asherlc/hang-ten --base main \
    --head agent/relieved-peacock-climbro-ci-ruleset-recovery \
    --title 'ci: recover required checks (relieved-peacock-climbro)' \
    --body 'Adds PR-base-update and manual CI triggers while keeping the Release-device build push-only. This is the minimal deployment of the approved CI ruleset alignment.'
  ```

  Expected: the PR contains only the three workflow-line changes and normal PR CI starts.

- [ ] **Step 4: Verify, merge, and clean up the exact workspace-owned branch/worktree**

  ```bash
  gh pr checks <PR_NUMBER> --repo Asherlc/hang-ten --watch
  gh pr merge <PR_NUMBER> --repo Asherlc/hang-ten --squash --delete-branch
  git worktree remove .context/relieved-peacock-climbro-ci-ruleset-recovery
  test ! -e .context/relieved-peacock-climbro-ci-ruleset-recovery
  git ls-remote --exit-code --heads origin agent/relieved-peacock-climbro-ci-ruleset-recovery && exit 1 || true
  ```

  Expected: the CI-only PR is merged; its remote branch and exact temporary worktree are absent; main contains the new `edited` and `workflow_dispatch` triggers and retains the push-only Release-device guard.
