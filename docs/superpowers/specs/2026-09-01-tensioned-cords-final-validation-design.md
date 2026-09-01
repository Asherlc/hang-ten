# Tensioned Cords Final Validation Design

## Purpose

This project is the final evidence, integration, and visual-validation pass for
the tensioned-cord work already divided among three dependency workspaces. It
does not authorize a new catalog redesign. It accepts only source-supported
cord repairs, preserves every unrelated accepted pixel and package fact, and
updates the existing pull request only after all terminal records and all
accepted assets satisfy the complete acceptance matrix.

## Dependency and integration boundary

The final-validation workspace waits for an explicit acceptance decision that
names the immutable commit or commits accepted from each dependency workspace:

1. `tensioned-cords-foundation` — foundation and evidence
2. `tensioned-cords-compact-dual` — compact and dual boards
3. `tensioned-cords-inverted-routing` — inverted and routed boards

The final workspace does not integrate a branch tip merely because it is
available, green, or newer. Before integration, an independent reviewer reads
the complete accepted-commit diff, its source evidence, its renders, and its
reported tests. The reviewer records the accepted SHA, parent, paths, source
provenance, accepted scope, rejected scope, and acceptance decision. Only the
accepted immutable commits are cherry-picked, in the order above. A whole
branch, an unaccepted fixup, and a candidate outside the recorded acceptance
boundary are not integrated.

Each applied dependency commit is independently reviewed again in the final
workspace before the next cohort proceeds. A conflict, unexpected path, lost
provenance, unsupported visual claim, or rejected candidate stops integration
and returns the work to its owning dependency workspace. It is not silently
repaired in the controller session.

The workspace-owned machine acceptance manifest is
`.context/tensioned-cords-final-validation/dependency-acceptance.json`. For
each cohort it records the named dependency ref, cohort base, non-empty ordered
`acceptedImplementationCommits` sequence, each commit's recorded parent,
accepted and rejected paths/candidates, source provenance, reviewer decision,
and required delivered capabilities. Before any cherry-pick, machine checks
prove parent equality, reachability from the named ref, absence from the
recorded integration base, global SHA uniqueness, and a contiguous ordered
parent chain. Reachability from other refs is neither prohibited nor treated as
an acceptance signal.

The foundation/evidence cohort is ineligible unless its accepted implementation
sequence itself provides and tests Workbench `--all-presentations`, stable
`packageID::presentationID` manifest identities, normal and hold-ID capture
variants, and failure-safe cleanup of its exact capture-server and Chrome child
processes. Its `requiredCapabilities` includes
`failureSafeOwnedChildCleanup`. Final validation consumes that capability; it
does not implement it.

## Source and physics contract

Every cord-bearing presentation must show the cords proved for that exact
product revision and working presentation. A sibling product, adjacent model,
alternate material, or another presentation of the same board cannot establish
cord count, doubled strands, knots, hidden connections, terminals, hardware,
or topology.

Every load-bearing cord must be taut in the source-supported load direction
under canvas-down gravity. A load-bearing segment may not have decorative sag,
float upward, bow against gravity, terminate without evidence, or imply an
unsupported connection. Routing-hole segments and exterior loops are included
when primary evidence proves them. Non-load-bearing slack is allowed only when
the exact source proves that slack and its direction for that presentation.

Unsupported and previously rejected candidates remain rejected. The work must
not infer or cosmetically complete doubled cords, knots, hidden continuity,
connections, terminals, hardware, or topology.

## Preservation contract

The accepted image is the baseline. For an accepted no-op, the entire asset is
byte-identical. For a source-proved repair, changes are bounded to the proved
cord, routing, terminal, or hardware pixels and the minimum antialiased boundary
needed to render those pixels. The following remain exact unless the primary
source specifically proves that the corresponding cord feature was wrong:

- board imagery and complete silhouette;
- hold appearance and overlay geometry;
- material, color, lighting, background, and alpha behavior;
- decoded width, height, and image mode;
- framing, scale, and position; and
- every unrelated pixel.

No automatic detection, segmentation, vectorization, masking, cropping,
registration, simplification, or generated contour workflow is permitted.
Visual review is direct and operator-led.

The already accepted classic YY Vertical La Baguette `stepped-face` and
`reverse-face` presentations are preservation baselines. Both remain present,
and neither may be replaced, reframed, rescaled, recolored, recropped, or have
unrelated pixels altered.

Final-workspace repair authorization is limited to exactly five records:

1. Nature Climbing Stone Hanger Mini `primary`;
2. Nature Climbing Stone Hanger Mini `side`;
3. Nature Climbing Stone Hanger Mini x KARMA8A `primary`;
4. YY Vertical La Baguette `reverse-face`; and
5. YY Vertical TravelBoard `reverse-10`.

Before any repair, each record must have an accepted baseline, exact-revision
source URLs and claims, a permitted cord-pixel region, and an expected terminal
result recorded in the dependency acceptance manifest. A changed and accepted
record ends `FIXED`; an already-correct unchanged baseline ends `PASS`.
Unresolved evidence is returned to its dependency owner. Every other candidate
is rejected or returned to its dependency owner unless the user explicitly
expands this five-record boundary.

La Baguette `stepped-face` and TravelBoard `front-25-15` are preservation/no-op
cross-checks, not additional repair authorization. TravelBoard `front-25-15`
must still remain source-correct and byte-preserved outside any separately
accepted dependency scope.

## Baguette Evo evidence boundary

The following five Baguette Evo presentations remain `BLOCKED`:

- `paired-25-20-15-10`
- `paired-12-8-6`
- `central-30-25`
- `central-20-6`
- `rounded-tray`

The available primary evidence does not resolve the visible cord topology,
hidden continuity, terminals, and hardware for every orientation. The project
must not use siblings, turn the absence of evidence into cord omission, or
invent a plausible route. Their terminal ledger entries stay honest and name
the unresolved evidence. No candidate pixels for these five presentations are
accepted until exact-revision primary evidence resolves all four gaps.

## Mandatory focused revalidation

Regardless of cohort reports, the final workspace directly revalidates these
assets and their package declarations:

- Nature Climbing Stone Hanger Mini `primary` and `side`;
- Nature Climbing Stone Hanger Mini x KARMA8A `primary`;
- YY Vertical La Baguette `reverse-face`, while also confirming the accepted
  `stepped-face` baseline remains unchanged; and
- YY Vertical TravelBoard `reverse-10`, while confirming `front-25-15` remains
  source-correct.

The Nature views must retain every source-proved routing-hole segment and
exterior loop. The TravelBoard reverse must retain its source-proved routing,
and no load-bearing TravelBoard cord may contain decorative sag. These checks
are direct image, source, package, Workbench, and iOS checks; a prior report is
not sufficient.

## Authoritative roster and terminal ledger

The final ledger is
`docs/source-audits/2026-09-01-tensioned-cords-final-validation.json`. Its roster
is discovered from the accepted source audit and the current catalog after the
three dependency cohorts are integrated. Discovery must fail unless there are
exactly 47 unique `(packageID, presentationID)` records. The final-validation
project does not invent names to reach 47 and does not remove a sourced record
to reduce the total.

Each record ends in exactly one terminal state:

- `PASS` — the accepted baseline required no pixel change and passed every
  applicable check;
- `FIXED` — a bounded source-proved correction was accepted and passed every
  applicable check; or
- `BLOCKED` — primary evidence is insufficient, no candidate was accepted, and
  the record states the exact missing evidence.

The five Baguette Evo records are `BLOCKED`. Every other record must be `PASS`
or `FIXED`; any additional blocked record stops pull-request publication until
the user explicitly accepts a revised boundary.

## Complete per-record acceptance matrix

The following matrix applies to all 47 records. A record cannot be marked
`PASS` or `FIXED` unless every applicable row passes with an evidence path or
command result in the ledger.

| Gate | Required result |
| --- | --- |
| Source-ledger terminal status | Exactly one honest `PASS`, `FIXED`, or `BLOCKED`; a blocked record accepts no candidate |
| Dimensions and alpha | Exact decoded width, height, image mode, and alpha behavior preserved |
| Pixel preservation | Background, scale, position, framing, and all unrelated pixels match the accepted baseline |
| Source fidelity | Cord topology, cord color, routing, terminals, and hardware are supported for the exact revision and presentation |
| Physics | Orientation-specific canvas-down gravity is respected and every load-bearing cord is taut in the source-supported direction |
| Silhouette | The complete board and every source-proved exterior cord loop remain visible without crop or accidental damage |
| Workbench overlay | Every visible hold overlay remains aligned with its intended contact surface |
| Workbench evidence | Normal and hold-ID-overlay captures exist for every in-scope presentation through the all-presentations capture path |
| iOS evidence | Normal and active/detail screenshots exist for every app-exposed record on the owned isolated simulator; blocked-record captures document the current baseline without accepting it |
| Package commands | Final-inventory validation and package status both pass |
| Focused tests | Cord, approved-package, and all-presentation capture tests pass |
| Full suite | The complete HangboardPackages suite and relevant Workbench suites pass |
| Diff | `git diff --check`, path review, binary/hash review, and unrelated-pixel review pass |
| Independent code review | A fresh reviewer approves provenance, scope, package data, tests, and diff |
| Independent visual review | A different fresh reviewer approves every source/render pair and capture |
| Owned-resource cleanup | Every exact workspace-owned simulator and generated runtime resource is deleted or cleaned; shared and unknown resources remain untouched |

Workbench capture evidence includes all declared catalog presentations, not
only default surfaces, and the ledger maps each of the 47 identities to its
normal and hold-ID-overlay captures. iOS evidence is captured from an isolated,
explicitly owned simulator UUID and includes normal and active/detail states.

The Workbench capture capability owns loopback ports `4187` and `4188` only for
the duration of capture. It records the exact server and Chrome child PIDs,
installs failure/signal cleanup before launch, terminates and waits for those
exact children on success, failure, interruption, and timeout, and never kills
an unknown process occupying either port. Capture starts only when both ports
are free and ends only after both are verified free.

`.context/hangboard-packages-venv` is an exact workspace-local tool artifact
when the package wrapper creates it. It is recorded as owned, retained through
the last package test, and deleted by the final resource-cleanup gate. Durable
independent-review decisions are written to
`.context/tensioned-cords-final-validation/final-code-review.json` and
`.context/tensioned-cords-final-validation/final-visual-review.json`; final
publication verifies that both approve the exact final HEAD and ledger hash.

## Pull-request publication

Pull request #388 is the only publication target. Publication is allowed only
after the ledger contains exactly 47 terminal records, the five Baguette Evo
records are honestly `BLOCKED`, every remaining record is `PASS` or `FIXED`,
every accepted asset passes every applicable matrix gate, both independent
final reviews approve, and owned-resource cleanup is verified.

The final branch is then pushed to the existing #388 head branch,
`fix-cords-backfill-gaps-nature-climbing-stone-hanger-mini`. The project does
not open a replacement pull request and does not merge #388.
