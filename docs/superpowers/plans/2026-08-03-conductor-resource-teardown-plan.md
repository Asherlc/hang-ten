# Conductor Resource Teardown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Hang Ten Conductor workspaces delete their owned simulators and workspace artifacts when work finishes, with a Conductor archive failsafe, a stale-simulator purge, and one explicit operator purge of the current Xcode DerivedData cache.

**Architecture:** A zsh cleanup CLI owns simulator discovery, ownership validation, archive cleanup, and explicit one-time prune behavior. A thin Conductor archive wrapper invokes its archive mode. Shared repository settings enable the wrapper, automatic archive after merge, branch deletion on archive, and a cleanup prompt. Agent instructions and the iOS validation guide use the same manifest-and-delete contract. The Xcode cache purge remains operator-only and is never placed in recurring hooks.

**Tech Stack:** zsh, `xcrun simctl`, Conductor repository TOML settings, Markdown instructions, shell-based mocked tests, and Python 3.12 `tomllib` validation.

## Global Constraints

- Never delete global Conductor, Codex, Claude, Cursor, or other provider history, databases, caches, indexes, credentials, or session records in recurring cleanup.
- Archive cleanup may delete only UUIDs listed in the current workspace's `.context/conductor-owned-simulators` manifest.
- An archive UUID is deletable only when its simulator name contains both the Hang Ten marker and the exact `CONDUCTOR_WORKSPACE_NAME` value.
- Simulator operations must use explicit UUIDs; no `booted`, broad process kill, runtime-wide delete, or name-only delete is allowed for archive cleanup.
- The one-time simulator prune defaults to dry-run and may delete only shutdown devices whose names identify them as Hang Ten review devices; booted, standard, and unrelated devices remain untouched.
- Missing resources are already-clean; malformed UUIDs, missing ownership context, and ownership mismatches are reported as errors and never guessed through.
- Validation build products, logs, screenshots, and temporary review artifacts stay under `.context`; documented local builds must not use the shared default DerivedData location.
- Every newly created validation simulator is named with `Hang Ten Conductor ${CONDUCTOR_WORKSPACE_NAME}`, recorded immediately in `.context/conductor-owned-simulators`, and deleted from an exit trap.
- Shared Conductor settings use `scripts.archive = "./scripts/conductor-archive.sh"`, `git.archive_on_merge = true`, and `git.delete_branch_on_archive = true`.
- The one-time Xcode purge may remove only immediate children of `/Users/asherlc/Library/Developer/Xcode/DerivedData` after inventory and process checks; it must not touch DeviceSupport, Archives, UserData, simulators, provider state, or histories.
- No new runtime or package dependency is introduced.

---

## Files and ownership

- Create `scripts/conductor-resource-cleanup.sh`: ownership-aware CLI with `archive` and `prune [--delete]` modes.
- Create `scripts/tests/conductor-resource-cleanup-test.zsh`: mocked `xcrun simctl` tests.
- Create `scripts/conductor-archive.sh`: Conductor archive entry point.
- Create `.conductor/settings.toml`: shared archive, Git lifecycle, and agent prompt configuration.
- Modify `.gitignore`, `AGENTS.md`, `.codex/skills/validate-hang-ten-ios/SKILL.md`, `docs/IOS_SIMULATOR_VALIDATION.md`, and `README.md`.

## Task 1: Build and test the ownership-aware cleanup CLI

**Files:**
- Create: `scripts/conductor-resource-cleanup.sh`
- Create: `scripts/tests/conductor-resource-cleanup-test.zsh`

**Interfaces:**
- `archive` consumes `CONDUCTOR_WORKSPACE_PATH`, `CONDUCTOR_WORKSPACE_NAME`, and the optional manifest at `$CONDUCTOR_WORKSPACE_PATH/.context/conductor-owned-simulators`; it returns 0 only when every listed resource is deleted or already absent.
- `prune` prints only shutdown Hang Ten review devices and performs no deletion.
- `prune --delete` deletes only those shutdown Hang Ten devices and returns nonzero if a deletion fails.
- Tests put a fake `xcrun` first in `PATH`; no real simulator is modified.

- [ ] **Step 1: Write the mocked test harness first**

Make the fake `xcrun simctl list devices` return:

```text
== Devices ==
-- iOS 26.5 --
    Hang Ten Conductor alpha Review (11111111-1111-1111-1111-111111111111) (Shutdown)
    Hang Ten Conductor alpha Running (22222222-2222-2222-2222-222222222222) (Booted)
    Hang Ten Conductor beta Review (33333333-3333-3333-3333-333333333333) (Shutdown)
    iPhone 17 Pro (44444444-4444-4444-4444-444444444444) (Shutdown)
```

Record explicit `shutdown` and `delete` calls. Assert archive deletes alpha's shutdown UUID, shuts down alpha's booted UUID before deleting it, never deletes beta or the standard device, treats a missing UUID as clean, and rejects malformed or mismatched manifest entries. Assert dry-run prune performs no delete and delete-mode prune deletes only shutdown Hang Ten UUIDs. Run this before implementation and expect failure because the CLI is absent:

```sh
zsh scripts/tests/conductor-resource-cleanup-test.zsh
```

- [ ] **Step 2: Implement the CLI**

Use `/bin/zsh` with `set -euo pipefail`, explicit mode parsing, and quoted paths/UUIDs:

```zsh
case "${1:-}" in
  archive) run_archive_cleanup ;;
  prune) run_prune "${2:-}" ;;
  *) usage >&2; exit 2 ;;
esac
```

Archive mode must require both environment variables before invoking `xcrun`, treat a missing manifest as empty, validate UUIDs against `^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$`, locate each exact UUID in `simctl list devices`, and skip missing UUIDs as already clean. Before deletion, require the parsed device name to contain `Hang Ten Conductor ` and the exact workspace name. Shutdown booted matches, delete matching UUIDs, continue through the manifest, and return 1 if any malformed/mismatched/failed entry remains.

Prune mode must accept no option or exactly `--delete`, select only names beginning `HangTen` or `Hang Ten` with state `Shutdown`, print a concrete line such as `Would delete Hang Ten Conductor alpha Review (11111111-1111-1111-1111-111111111111)` in dry-run mode, and invoke `simctl delete` only in explicit delete mode. Never select booted, standard, or unmarked devices.

- [ ] **Step 3: Run tests and checks**

```sh
zsh scripts/tests/conductor-resource-cleanup-test.zsh
zsh -n scripts/conductor-resource-cleanup.sh
git diff --check
```

Expected result: every mock assertion passes, syntax exits 0, and no whitespace errors are reported.

- [ ] **Step 4: Commit Task 1**

```sh
git add scripts/conductor-resource-cleanup.sh scripts/tests/conductor-resource-cleanup-test.zsh
git commit -m "build: add ownership-aware simulator cleanup"
```

## Task 2: Wire cleanup into Conductor and agent policy

**Files:**
- Create: .conductor/settings.toml
- Create: scripts/conductor-archive.sh
- Modify: .gitignore
- Modify: AGENTS.md

**Interfaces:**
- Conductor runs scripts/conductor-archive.sh from the workspace directory before archive; the wrapper delegates to Task 1's archive mode and preserves its exit status.
- Repository settings enable git.archive_on_merge and git.delete_branch_on_archive for this repository's workspaces.
- AGENTS.md and the Conductor prompt express the same ownership contract without referencing global provider paths.

- [ ] **Step 1: Add the archive wrapper**

Create an executable /bin/zsh wrapper:

~~~
#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
exec "$script_dir/conductor-resource-cleanup.sh" archive
~~~

Run chmod +x scripts/conductor-archive.sh and zsh -n scripts/conductor-archive.sh.

- [ ] **Step 2: Add shared Conductor settings**

Create .conductor/settings.toml with:

~~~
"$schema" = "https://conductor.build/schemas/settings.repo.schema.json"

[scripts]
archive = "./scripts/conductor-archive.sh"

[prompts]
general = """
Resource lifecycle is part of every task. Keep derived data, logs, screenshots, and temporary review files under .context. Give every external resource an exact workspace owner, record that ownership immediately, and install an exit cleanup trap. Before reporting completion, shut down and delete every resource owned by this workspace. Never delete shared or unknown resources; if cleanup fails, report the failure and keep working until it is resolved or explicitly blocked.
"""

[git]
archive_on_merge = true
delete_branch_on_archive = true
~~~

Validate it with:

~~~
python3 - <<'PY'
import pathlib
import tomllib

settings = tomllib.loads(pathlib.Path('.conductor/settings.toml').read_text())
assert settings['scripts']['archive'] == './scripts/conductor-archive.sh'
assert settings['git'] == {'archive_on_merge': True, 'delete_branch_on_archive': True}
assert 'delete every resource owned by this workspace' in settings['prompts']['general']
PY
~~~

- [ ] **Step 3: Update .gitignore and AGENTS.md**

Add without removing existing entries:

~~~
# Conductor workspace-local state
.context/
~~~

Add a Resource lifecycle section to AGENTS.md requiring every agent to put generated output under .context or another explicitly workspace-owned path, include CONDUCTOR_WORKSPACE_NAME in external resource names, record ownership immediately, install an exit trap that shuts down and deletes exact owned resources, verify deletion before reporting completion, and leave shared/standard/unknown resources alone. State that the archive hook is a failsafe, not permission to skip the agent's own cleanup. Preserve the existing delegation instructions verbatim.

- [ ] **Step 4: Validate Task 2**

~~~
zsh -n scripts/conductor-archive.sh scripts/conductor-resource-cleanup.sh
python3 - <<'PY'
import pathlib
import tomllib

settings = tomllib.loads(pathlib.Path('.conductor/settings.toml').read_text())
assert settings['scripts']['archive'] == './scripts/conductor-archive.sh'
assert settings['git'] == {'archive_on_merge': True, 'delete_branch_on_archive': True}
PY
mkdir -p .context
touch .context/conductor-owned-simulators
git check-ignore -q .context/conductor-owned-simulators
rm .context/conductor-owned-simulators
git diff --check
~~~

Expected result: every command exits 0 and no generated file is staged.

- [ ] **Step 5: Commit Task 2**

~~~
git add .conductor/settings.toml scripts/conductor-archive.sh .gitignore AGENTS.md
git commit -m "build: enforce Conductor workspace teardown"
~~~

## Task 3: Align documented workflows with deletion and workspace-local DerivedData

**Files:**
- Modify: .codex/skills/validate-hang-ten-ios/SKILL.md
- Modify: docs/IOS_SIMULATOR_VALIDATION.md
- Modify: README.md

**Interfaces:**
- The skill and guide use Task 1's CLI and .context/conductor-owned-simulators manifest.
- Validation keeps explicit UUID targeting and workspace-specific DerivedData while adding immediate registration and deletion.
- The README's copyable local build command writes DerivedData under .context/DerivedData.

- [ ] **Step 1: Update the validation skill**

Require a simulator name beginning with Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME, immediate append of the created UUID to .context/conductor-owned-simulators before boot/build, an exit trap running scripts/conductor-resource-cleanup.sh archive on success/failure/interruption, and deletion of the exact UUID after validation. Keep the DEBUG review-route, landscape, spoken countdown, and HealthKit requirements unchanged.

- [ ] **Step 2: Update the simulator guide**

Replace the creation example with:

~~~
workspace_path="$PWD"
workspace_name="$CONDUCTOR_WORKSPACE_NAME"
test -n "$workspace_name"
mkdir -p "$workspace_path/.context"
simulator_name="Hang Ten Conductor $workspace_name Review"

cleanup() {
  CONDUCTOR_WORKSPACE_PATH="$workspace_path" \
  CONDUCTOR_WORKSPACE_NAME="$workspace_name" \
  "$workspace_path/scripts/conductor-resource-cleanup.sh" archive
}
signal_exit() {
  trap - INT TERM
  exit "$1"
}
trap cleanup EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM

simulator_uuid="$(xcrun simctl create "$simulator_name" "$device_type_id" "$runtime_id")"
printf '%s\n' "$simulator_uuid" >> "$workspace_path/.context/conductor-owned-simulators"
~~~

Keep every readiness, build, install, launch, screenshot, and runtime-service operation UUID-based. Replace shutdown-only cleanup with scripts/conductor-resource-cleanup.sh archive, explain that the trap is idempotent, and retain the warning against deleting unknown/shared simulators.

- [ ] **Step 3: Update the README build command**

Add this exact flag to the documented local xcodebuild command:

~~~
-derivedDataPath .context/DerivedData
~~~

Add one sentence stating that all Conductor/local-agent builds must use a workspace-local DerivedData path so indexes and build output disappear with the workspace.

- [ ] **Step 4: Validate the documentation contract**

~~~
rg -n 'conductor-owned-simulators|simctl delete|Hang Ten Conductor|DerivedData' .codex/skills/validate-hang-ten-ios/SKILL.md docs/IOS_SIMULATOR_VALIDATION.md README.md
if rg -n 'shutdown only|Shutdown only the dedicated' .codex/skills/validate-hang-ten-ios/SKILL.md docs/IOS_SIMULATOR_VALIDATION.md; then
  exit 1
fi
git diff --check
~~~

Expected result: the first command finds new ownership/deletion guidance; the second finds no shutdown-only instruction; git diff --check exits 0.

- [ ] **Step 5: Commit Task 3**

~~~
git add .codex/skills/validate-hang-ten-ios/SKILL.md docs/IOS_SIMULATOR_VALIDATION.md README.md
git commit -m "docs: require simulator deletion and local DerivedData"
~~~

## Controller-only operation after implementation review: reclaim existing disk space

This operation is authorized by the user's one-time cache request but is not recurring repository behavior. Run it only after Tasks 1–3 pass their task reviews and the final diff has been checked for scope.

- [ ] **Step 1: Check active Xcode work and snapshot exact cache children**

~~~zsh
set -euo pipefail

derived_data_root=/Users/asherlc/Library/Developer/Xcode/DerivedData
if pgrep -x Xcode >/dev/null || pgrep -x xcodebuild >/dev/null; then
  echo "Xcode or xcodebuild is active; stop before purging DerivedData." >&2
  exit 1
fi
mkdir -p .context
find "$derived_data_root" -mindepth 1 -maxdepth 1 -print0 > .context/derived-data-before.bin
du -sh "$derived_data_root"
scripts/conductor-resource-cleanup.sh prune
~~~

This block is zsh-specific because the deletion step uses zsh path modifiers.
Review the dry-run list and the NUL-delimited `.context/derived-data-before.bin`
inventory before deletion. Every simulator target must be a shutdown Hang Ten
review device. Every DerivedData target must be an immediate child of the
explicit DerivedData path.

- [ ] **Step 2: Delete stale Hang Ten simulators**

~~~
scripts/conductor-resource-cleanup.sh prune --delete
~~~

If a device became booted after the dry run, stop and leave it untouched.

- [ ] **Step 3: Delete inventoried Xcode DerivedData children**

Use the already-written inventory, validate every line against the exact root, and delete each child—not the root itself:

~~~zsh
set -euo pipefail

derived_data_root=/Users/asherlc/Library/Developer/Xcode/DerivedData
while IFS= read -r -d '' child; do
  parent="${child:h}"
  name="${child:t}"
  if [[ "$parent" != "$derived_data_root" || -z "$name" || "$name" == "." || "$name" == ".." ]]; then
    echo "Unexpected DerivedData target: $child" >&2
    exit 1
  fi
  rm -rf -- "$child"
done < .context/derived-data-before.bin
~~~

Do not remove /Users/asherlc/Library/Developer/Xcode/iOS DeviceSupport, Xcode Archives/UserData, simulator runtimes/devices, Conductor state, provider state, credentials, or session history.

- [ ] **Step 4: Verify reclaimed space and simulator state**

~~~
du -sh /Users/asherlc/Library/Developer/Xcode/DerivedData
xcrun simctl list devices > .context/simulators-after.txt
scripts/conductor-resource-cleanup.sh prune
df -h /
~~~

Expected result: DerivedData is absent or empty, the second prune reports no shutdown Hang Ten review devices, booted and standard devices remain, and the disk report records recovered capacity.

## Final verification checklist

- [ ] zsh scripts/tests/conductor-resource-cleanup-test.zsh passes ownership, booted, missing, mismatch, dry-run, and delete-mode cases.
- [ ] All new shell scripts pass zsh -n.
- [ ] .conductor/settings.toml parses and contains exact archive and Git lifecycle values.
- [ ] .context/ is ignored and no generated review artifacts are staged.
- [ ] AGENTS.md, the validation skill, README, and simulator guide agree on deletion, manifest, and local DerivedData paths.
- [ ] The final diff contains no global provider path or broad filesystem deletion.
- [ ] The one-time prune removes only approved shutdown Hang Ten simulators.
- [ ] The one-time DerivedData purge records before/after evidence and leaves DeviceSupport, user data, simulator runtimes, and agent history intact.
