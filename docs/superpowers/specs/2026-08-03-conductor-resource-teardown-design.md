# Conductor Resource Teardown Design

## Goal

Make Hang Ten Conductor workspaces self-cleaning so an agent removes every
resource it owns when work finishes, while preserving unrelated machine data.
The one-time cleanup must reclaim only Hang Ten workspace-owned resources.

## Scope and non-goals

In scope:

- Dedicated iOS Simulator devices created for Hang Ten workspace validation.
- Workspace-local build products, screenshots, logs, and review data under
  `.context`.
- Git worktrees and branches after Conductor archives a finished workspace.
- Agent instructions and validation guidance that make ownership and deletion
  explicit.
- A one-time cleanup path for existing shutdown Hang Ten review simulators.
- A one-time operator purge of the current Xcode DerivedData cache, including
  project build and index artifacts across projects.

Out of scope:

- Global Conductor, Codex, Claude, or Cursor history, databases, caches, and
  indexes. They remain outside recurring cleanup and outside the one-time
  Xcode cache purge.
- Shared or standard Apple simulator devices.
- Booted simulators during the one-time cleanup, because they may still belong
  to active work.
- Automatic deletion of a workspace before its diff has been reviewed or
  merged.

## Considered approaches

### Instructions only

Extend `AGENTS.md` and the simulator guide with cleanup rules. This is simple
and portable, but it depends on every agent remembering to follow the rules and
has no protection when an agent crashes or stops early.

### Repository Conductor settings plus ownership-aware cleanup

Add a shared `.conductor/settings.toml` archive hook, durable pending and owned
manifests for simulator UUIDs, and mandatory cleanup instructions. Validation
creates devices with a workspace marker, appends each exact UUID to the pending
manifest before writing the owned manifest or doing any boot/build work, and
deletes the exact UUID in an exit trap. The archive hook consumes both manifests
as an idempotent last line of defense before Conductor archives the worktree.
This is the recommended approach because it covers normal completion,
interrupted work, and Conductor archive without touching global state.

### Machine-wide cache pruning

Configure a user-level cleanup job that removes provider and Conductor data by
path or age. This could reclaim more space, but those stores are shared across
repositories and sessions, so ownership cannot be proven from this repository.
It is intentionally rejected for this change.

## Design

### Ownership contract

Every validation-created simulator must:

1. Include the exact `CONDUCTOR_WORKSPACE_NAME` in its name.
2. Append its exact UUID to `.context/conductor-pending-simulators` immediately
   after creation, before writing `.context/conductor-owned-simulators` and
   before any boot or build operation.
3. Use the UUID for every boot, install, launch, screenshot, and shutdown
   operation.
4. Register an exit trap that archives the exact UUID and tolerates an
   already-deleted device. Pending state remains durable for archive retry until
   shutdown and deletion both succeed. If pending registration itself fails,
   direct in-memory deletion of the validated UUID is the last-resort fallback;
   before deleting, re-query that exact UUID, parse its exact device-name field,
   and require the exact `Hang Ten Conductor ${CONDUCTOR_WORKSPACE_NAME} ` marker.
   If lookup or ownership verification fails, do not delete and return failure;
   the pending and owned manifests remain for archive retry.

Derived data, screenshots, logs, and temporary review artifacts remain under
`.context`, which is workspace-local and is removed with the archived
worktree. Agents must not use the shared default DerivedData location for
workspace validation.

### Conductor lifecycle

`.conductor/settings.toml` will register `scripts/conductor-archive.sh` as the
archive script. The same shared settings will enable automatic archive after a
merged pull request and delete the archived workspace branch. The archive
script will:

- Consume UUIDs from both `.context/conductor-pending-simulators` and
  `.context/conductor-owned-simulators` in the current workspace, deduplicating
  UUIDs before processing them.
- Validate each UUID format and confirm the simulator name begins with the
  exact ownership marker `Hang Ten Conductor ${CONDUCTOR_WORKSPACE_NAME} ` before
  deleting it.
- Shut down a matching booted simulator, delete it, and treat a missing UUID as
  already clean.
- Skip and report unknown or mismatched devices instead of guessing.
- Preserve pending entries for any UUID whose shutdown or deletion does not
  succeed, so a later archive invocation can retry; remove pending state only
  after cleanup succeeds.
- Leave global agent stores, unrelated simulators, and shared devices alone.

The archive script will be idempotent and safe to run more than once. Cleanup
failures will be visible to Conductor so an archive cannot silently claim to
have completed while an owned external resource remains.

`AGENTS.md` and the repository Conductor prompt will require agents to perform
the same cleanup before reporting completion. The iOS validation skill and
`docs/IOS_SIMULATOR_VALIDATION.md` will use the manifest-and-delete workflow so
the operational guidance matches the hook.

### One-time cleanup

Add a dry-run-first script for the existing machine state. It will enumerate
only shutdown simulator devices whose names identify them as Hang Ten review
devices, print exact UUIDs and names, and require an explicit deletion mode.
It will never delete booted devices, standard device types, or any provider and
Conductor history/index store. The deletion run will be preceded by a
read-only inventory and followed by a fresh simulator listing and disk-usage
measurement.

### One-time Xcode cache purge

The current host's large project-data footprint is Xcode's
`~/Library/Developer/Xcode/DerivedData` directory, which contains build output,
module caches, and `Index.noindex` data. After checking that no Xcode or
`xcodebuild` process is active, the operator may delete the immediate child
project caches and indexes from that directory once. This purge is not part of
the Conductor archive hook and must never be added to recurring agent cleanup.

The purge leaves Xcode `iOS DeviceSupport`, Archives, UserData, simulator
runtimes/devices, Conductor state, provider state, credentials, and agent
session history intact. It must record the child-directory inventory before
deletion and fresh disk-usage evidence afterward.

### Error handling and safety

- Missing `CONDUCTOR_WORKSPACE_NAME` or workspace path is an error for archive
  cleanup; the script must not fall back to broad matching.
- Malformed UUIDs and devices whose names do not prove ownership are skipped
  with an error, not deleted.
- `simctl` operations are scoped to explicit UUIDs only.
- Cleanup commands are safe when resources were already removed by an agent's
-  exit trap; duplicate UUIDs across either manifest are processed once.
- Direct in-memory deletion is permitted only as a last resort when appending
  the UUID to the pending manifest fails, and only after re-querying the exact
  UUID and parsing/verifying the exact ownership marker; failed lookup or
  verification must return failure without deletion. Preserve both manifests
  for archive retry.
- The one-time script defaults to reporting targets; destructive deletion
  requires an explicit flag.

## Verification

The implementation will be verified with:

- Shell syntax checks for every new or modified script.
- Settings/TOML validation and `git diff --check`.
- Unit-like shell tests using mocked `simctl` output to cover matching,
  mismatched, booted, malformed, and already-missing devices.
- A live dry run against the current host followed by deletion of only the
  approved shutdown Hang Ten devices.
- A one-time, explicitly operator-run purge of Xcode DerivedData after a
  read-only child inventory and active-process check.
- Fresh simulator inventory and disk-usage measurements after cleanup.
- A focused review of the final diff confirming no global store or unrelated
  simulator path is referenced.
