# Hold-region review and promotion toolkit

## Goal

Make the solo hold-region workflow fast to inspect, safe to accept, and
repeatable to promote into Hang Ten without turning the existing editor into a
large all-in-one application.

The toolkit covers the gap between the local hold-region editor and the
repository's existing Xcode/CI/TestFlight delivery path. It communicates
through explicit JSON artifacts and keeps visual editing, validation,
acceptance, promotion, and release checks as separate responsibilities.

## Scope and assumptions

The first version is for a solo developer reviewing one or more local
onboarding runs. The hold-region editor remains the only interactive geometry
editor. The existing staged onboarding pipeline remains responsible for
source registration, generated regions, deterministic previews, and hash
validation.

For this design, “production” means reviewed board data integrated into the
app and shipped through the existing `main` → CI → TestFlight flow. Direct
App Store Connect upload is not added to the local review tools; the existing
release workflow remains the delivery authority.

The toolkit must not infer physical hold semantics, invent missing metadata,
or replace the runtime's deterministic Swift geometry with a raster overlay.
When a board still needs manual Swift integration, promotion produces an
explicit handoff package and reports `handoff-required` rather than claiming
the board is production-ready.

## Design principles

- Each command has one clear responsibility and can be run independently.
- Commands exchange versioned JSON documents and exit with useful non-zero
  statuses on invalid input or blocked promotion.
- Generated Stage 1 and Stage 2 artifacts are immutable. Human-edited regions,
  correction deltas, acceptance records, reports, and promotion packages are
  separate files.
- Mutating commands are atomic and default to a dry run or preview.
- All promotion outputs include SHA-256 hashes for their source inputs and
  generated outputs.
- Visual inspection remains easy without requiring a third-party frontend
  framework or a network connection.
- Product-specific knowledge lives in board data and runtime integration, not
  in generic review commands.

## Command surface

The existing `scripts/hangboard-tools.sh` wrapper gains narrow subcommands.
Each subcommand delegates to an independently testable Python module or local
browser page under the onboarding/tooling area.

### `inspect`

`inspect --run <path>` reports the run's discovered stages, artifact paths,
schema versions, source and artifact hashes, current review state, and the
next valid action. It is read-only and suitable for shell scripts.

It distinguishes automatic proposal, edited artifact, correction delta,
acceptance record, and promotion report. It never treats the presence of an
edited file alone as approval.

### `compare`

`compare --run <path>` opens or emits a dependency-free visual comparison of
the automatic and edited regions. The view supports:

- opacity slider and side-by-side comparison;
- image-only, automatic-only, edited-only, and difference modes;
- selected-region focus and region metadata;
- added, modified, and deleted correction summaries;
- fit, zoom, and the same normalized coordinate display used by the editor.

The comparison tool reads artifacts and does not save edits. If no edited
artifact exists, it clearly reports that there is nothing to compare.

### `lint`

`lint --run <path>` validates the edited artifact and its correction delta
without changing them. Checks include:

- valid schema, canvas dimensions, finite coordinates, and closed contours;
- unique stable region IDs and non-empty keys;
- non-degenerate area and points within the declared canvas;
- valid grip type, interaction mode, path style, and curve metadata;
- correction entries that agree with the automatic baseline;
- no deleted, added, or modified entry that cannot be reconciled to the
  baseline;
- required semantic metadata for any configured board promotion target.

The command emits both human-readable diagnostics and a machine-readable
lint report. Warnings do not silently become passes; promotion declares which
warnings are allowed for the selected board profile.

### `preview`

`preview --run <path>` generates deterministic review images and an optional
static HTML gallery for normal, all-highlighted, per-type, selected-region,
and symmetry views. It reuses the existing pipeline renderers where possible
and records the edited artifact hash beside each preview.

This is a review aid, not runtime interaction geometry. A generated preview
cannot by itself make a board eligible for app integration.

### `accept`

`accept --run <path>` records an explicit human review decision after linting
and preview generation. It writes an acceptance document beside the edited
artifact, for example:

```json
{
  "schemaVersion": 1,
  "decision": "accepted",
  "reviewer": "local-user",
  "reviewedAt": "2026-08-09T00:00:00Z",
  "source": {
    "stage1Sha256": "...",
    "stage2Sha256": "...",
    "editedSha256": "...",
    "correctionsSha256": "..."
  },
  "toolVersion": "...",
  "notes": "..."
}
```

Acceptance is invalidated when any referenced input changes. Rejecting a run
is represented explicitly and leaves all generated and edited artifacts
untouched. Re-acceptance creates a new record after the changed artifact has
been reviewed again.

### `promote`

`promote --run <path>` performs a safe promotion preflight. It requires a
current acceptance record and then:

1. verifies the Stage 1 → Stage 2 → edited/corrections hash relationship;
2. reruns linting using the selected board profile;
3. generates the canonical manifest, preview bundle, and provenance report;
4. checks that every runtime hold ID has reviewed geometry and that every
   reviewed geometry has an intentional runtime mapping;
5. reports whether the result is `ready`, `handoff-required`, or `blocked`.

The default is `--dry-run`. `--apply` may copy or update only explicitly
configured canonical inputs, using atomic replacement and a complete file list
shown before mutation. It must never overwrite the original generated Stage 1
or Stage 2 artifacts.

For boards without a configured runtime integration profile, `--apply` writes
an auditable promotion package under `.context` and returns
`handoff-required`. It does not generate Swift geometry from pixels or assume
that a visual region has a particular depth, finger count, or semantic type.

### `release-check`

`release-check --run <path>` validates the repository-facing side of the
promotion. It checks the canonical artifact set, board catalog coverage,
routine compatibility, plan-library export consistency, and the relevant
local XCTest/build commands. It produces a release checklist and exits
non-zero when a required check fails.

It does not commit, push, upload, or publish. The developer reviews the
result, commits intentionally, and lets the existing GitHub Actions workflow
promote a successful `main` build to TestFlight.

## Artifact layout

The existing run remains the source of truth for review inputs. New files are
kept beside the relevant Stage 2 proposal or under the run's owned `.context`
directory:

```text
stage-2-regions.json                 automatic proposal, immutable
stage-2-regions.edited.json         human-edited geometry
stage-2-human-corrections.json      added/modified/deleted delta
stage-2-review-acceptance.json      explicit review decision and hashes
board-promotion-report.json         preflight result and output hashes
promotion/                          generated handoff/canonical package
```

The exact destination for canonical app inputs is supplied by a board
integration profile rather than hard-coded into generic review commands.

## Promotion state model

```text
automatic
  → edited
  → lint-passed
  → accepted
  → ready | handoff-required | blocked
  → release-checked
  → committed and pushed
  → CI/TestFlight
```

State is derived from artifact presence, hashes, and reports; it is not kept
in a mutable database. Any source or edited-artifact change moves the run back
to the appropriate earlier state.

## Error handling and safety

- Missing or ambiguous artifacts stop the command with a path-specific error.
- Hash mismatches invalidate acceptance and promotion rather than producing a
  best-effort package.
- Invalid geometry reports all independent failures where practical.
- `--apply` requires an explicit destination profile and prints the planned
  changes before writing.
- Writes use temporary files in the destination directory followed by atomic
  replacement.
- No command follows symlinks outside the configured run or repository-owned
  destination.
- Browser comparison and preview pages remain local-only and do not upload
  source images.

## Verification

Unit tests cover artifact discovery, hash invalidation, schema and geometry
linting, correction reconciliation, acceptance records, promotion states,
destination confinement, and atomic writes.

Browser tests cover comparison modes, selected-region focus, missing-edited
artifact handling, and preview gallery generation against representative
Compact II, Beastmaker 1000, and Simulator 3D runs.

End-to-end verification runs the complete solo path on a fixture run:

```text
edit/save → inspect → compare → lint → preview → accept
→ promote --dry-run → release-check
```

The fixture must prove that changing the source or edited JSON after
acceptance blocks promotion, that generated proposals remain unchanged, and
that a board without runtime integration produces `handoff-required` rather
than a false success.

## Non-goals for the first version

- No replacement of the existing hold editor.
- No live collaboration, accounts, or hosted review service.
- No automatic product recognition or model-generated contours.
- No automatic invention of hold semantics or Swift runtime geometry.
- No direct App Store Connect or public App Store publishing command.
- No automatic git commit or push.

