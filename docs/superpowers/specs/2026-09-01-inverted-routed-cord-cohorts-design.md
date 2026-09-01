# Inverted and Routed Cord Cohorts Design

## Status and objective

This specification governs the cord-only remediation cohort for Crimptonite,
Tension Flash, Frictitious Port-A-Board, both Lattice MXEdge Lift variants,
and every associated alias, rotated presentation, and inverted presentation
identified by the accepted source ledger.

The objective is physical correctness without collateral image change. Every
real cord proved by primary evidence must appear. Every load-bearing segment
must be taut in the source-supported direction for the presentation being
shown, with gravity acting toward the bottom of that presentation's canvas.
The implementation changes only source-proved cord pixels and preserves the
rest of each accepted presentation exactly.

This work does not change training-plan content, hold inventory, product
revision identity, unrelated board metadata, or app behavior. It does not
update or merge PR #388.

## Hard dependency and authority

Workspace 1, “Cord tension — foundation & evidence,” owns the source ledger,
its validator, the presentation-complete Workbench capture, the DEBUG review
route, and the feasibility gate. Cohort implementation must not begin until
all of the following are true:

1. Workspace 1 has named an exact foundation commit as explicitly accepted.
2. Its feasibility gate is accepted, not merely run or partially passing.
3. This workspace has merged that exact accepted commit.
4. The merged ledger, validator, Workbench capture, DEBUG route, and gate are
   present and usable in this workspace.

A branch name, latest Workspace 1 commit, unreviewed commit, green subset of
checks, or locally copied foundation file is not a substitute for the explicit
acceptance. This design document may be committed before the dependency lands,
but no cohort package, asset, ledger, validator, Workbench, or app change may
be implemented before the accepted foundation commit is merged.

After that merge, the accepted ledger is the enumeration and evidence
authority. Existing package declarations and older audits are useful context,
but they cannot add a presentation, cord, route, attachment, or physical claim
that the accepted ledger does not support. This specification deliberately
does not guess the filenames, schemas, or commands that Workspace 1 will land.

## Architecture

The implementation has five bounded stages:

1. **Foundation intake.** Merge the explicitly accepted Workspace 1 commit,
   run its feasibility gate, and verify that its ledger and validation surfaces
   are available locally.
2. **Ledger expansion.** Select all records belonging to Crimptonite, Flash,
   Port-A-Board, MXEdge Lift Large, and MXEdge Lift Small. Expand the selection
   to every ledger-declared alias and every rotated or inverted presentation.
3. **Per-asset edit.** Across all cohorts, deduplicate by ledger-declared asset
   identity. Every unique supported asset receives exactly one source-grounded
   attempt with the built-in image-editing capability; unsupported assets
   receive zero attempts. The edit replaces or corrects only the cord pixels
   needed for that presentation.
4. **Per-record review.** Validate every unique presentation and every alias
   in both Workbench and the isolated iOS app, even when two records share one
   accepted asset.
5. **Cohort closeout.** Commit and push only terminal, source-supported cohort
   work, retain explicit blocker records for unresolved routing, and send the
   accepted commit hash and blocker list to Workspace 4 through Paseo.

The ledger record is the unit of evidence and review. The unique ledger-
declared asset identity is the unit of image editing and byte-preservation
validation. The cohort is the unit of commit acceptance. These boundaries
prevent an alias from escaping review, prevent one shared asset from receiving
more than one attempt anywhere in these cohorts, and prevent a partially
supported cohort from being presented as complete.

## Data flow

For each cohort, data moves through this sequence:

1. The accepted ledger identifies the package, exact physical revision,
   presentation, alias relationships, asset identity, orientation, cord
   inventory, visible routing, supported attachment facts, primary sources,
   and any blocker.
2. Ledger relationships are expanded into a review matrix containing every
   unique presentation and alias. Records that share bytes remain separate
   review rows.
3. A supported record yields an edit brief containing only facts traceable to
   the ledger's primary evidence: visible cords, routing, load-bearing
   direction, orientation, and canvas-down gravity.
4. Every unique supported ledger-declared asset receives one built-in image
   edit attempt. The existing local asset is the edit target, and the ledger-
   cited source material is the physical authority. Unsupported records and
   assets receive no image edit. No generated output is itself evidence.
5. The foundation validator compares the candidate with the original asset and
   enforces the cord-only mutation boundary and all preservation invariants.
6. A human compares the candidate with the primary evidence and reviews each
   ledger row in the presentation-complete Workbench capture and the app's
   DEBUG review route on an isolated simulator.
7. Accepted bytes are promoted to the declared package asset only after every
   applicable automated and visual gate passes. Rejected bytes are never
   promoted. The ledger records the terminal accepted or blocked disposition.
8. Once every record in a cohort is terminal, the supported package changes
   and explicit blocker records are committed, pushed, and communicated.

An alias may share an asset only when the accepted ledger establishes that it
is the same physical presentation, orientation, gravity, and routing. If an
alias changes any of those properties, it requires its own presentation-
specific asset and its own single attempt. When multiple records resolve to
one asset, the first supported record schedules the sole attempt and all other
records consume that candidate; the shared path is never edited again in
another cohort. Asset sharing is never a reason to copy, rotate, or reuse
physically incorrect cord pixels.

## Cohort and gate rules

The primary cohort selection comprises:

- every accepted-ledger Crimptonite record;
- every accepted-ledger Tension Flash record;
- every accepted-ledger Frictitious Port-A-Board record;
- every accepted-ledger Lattice MXEdge Lift Large record;
- every accepted-ledger Lattice MXEdge Lift Small record; and
- every alias, rotated presentation, and inverted presentation associated with
  those records by the ledger.

The names above select product families; they are not a hand-maintained asset
list. The merged ledger supplies the final inventory. This avoids silently
omitting a presentation added or corrected by Workspace 1.

A cohort is complete only when every enumerated record has a terminal outcome:
accepted or explicitly blocked. Accepted means the evidence, image,
preservation, Workbench, package, and isolated-iOS gates all pass. Blocked
means no unsupported pixel or metadata change was promoted and the record
states the exact missing or conflicting primary evidence. A blocked record
does not authorize guessing and does not become accepted because a related
presentation passes.

Commits may contain supported asset changes and their explicit terminal
blocker records, but never a partially edited asset, an unreviewed alias, an
unsupported route, or a record left in an indeterminate state. A cohort with
an unresolved nonterminal row is not commit-ready.

## Cord physics and presentation-specific pixels

Cord correctness is evaluated in the coordinate system of the final
presentation, not in the orientation of a source photo or another package
asset. The bottom edge of the final canvas is down. For each presentation:

- include every cord that exact-revision primary evidence proves is real;
- preserve the proved visible cord count and topology;
- make each load-bearing segment taut along the source-supported load path;
- make unloaded portions, if primary evidence proves them, respond plausibly
  to canvas-down gravity without changing their proved attachment or route;
- preserve complete cord and board silhouettes, including visible entry,
  exit, perimeter, and terminal regions established by the source; and
- omit any continuity or component that the source does not establish.

An inverted or rotated board is not produced by rotating completed cord
pixels. Rotating a finished raster rotates gravity and tension with it, which
can make a visually tidy result physically false. Board pixels may already be
presentation-related through package metadata, but cord pixels must be edited
for the final presentation's own orientation. The one edit for that asset must
render the source-supported taut direction and canvas-down gravity directly.

Every alias is checked under the same rule. A visual alias that resolves to a
shared file is acceptable only when its final on-screen orientation preserves
the same correct cord physics. Otherwise it is not a valid alias relationship
for cord pixels and remains blocked until the ledger and package representation
can express a source-supported presentation-specific asset.

## Routing and evidence constraints

Only exact-revision primary manufacturer evidence can authorize cord routing,
attachment, and hidden structure. Older revisions, diagrams for another
revision, sibling products, retailer inference, and another orientation cannot
fill a gap.

MXEdge manufacturer evidence establishes perimeter or groove routing. Its
cords must follow that supported perimeter/groove path. They must not pass
through invented side holes, and the edit must not create side holes,
grommets, terminals, or other hardware to explain the route. This applies
independently to both MXEdge Lift variants and to each of their ledger-declared
presentations.

Port-A-Board cord option 4 remains explicitly blocked and receives zero image
edit attempts unless exact,
current-revision primary evidence establishes its routing. Evidence from an
older Port-A-Board revision, a generic option diagram, a sibling product, or a
different orientation does not clear the blocker. A shared asset path or
existing package declaration also does not clear it.

Across all cohorts, do not invent hidden continuity, knots, terminals,
grommets, doubled cords, attachment hardware, concealed holes, or off-canvas
connections. When primary evidence establishes only visible segments, depict
only the supported visible topology. When evidence is insufficient to create
a physically coherent final presentation without invention, block the record.

## Single-edit image contract

Across the complete multi-cohort run, every unique supported ledger-declared
asset receives exactly one source-grounded built-in image edit attempt. Shared
paths are globally deduplicated before any invocation, so aliases, products,
or cohort boundaries cannot trigger another attempt against the same asset.
Unsupported records and assets receive zero attempts. The edit is classified
as a precise object edit: change only the source-proved cords and keep every
invariant unchanged. It uses the current asset as the edit target and the
minimum ledger-cited primary source set needed to establish that presentation's
cords, orientation, and route.

There is no second edit attempt for a failed asset anywhere in these cohorts.
If the single candidate violates evidence, physics, topology, preservation,
or validation, reject it and mark the affected record or records blocked with
the specific failure. This ensures “one edit per asset” cannot quietly become
an iterative product-specific pipeline.

The workflow must not use resizing, pixel postprocessing, masks, manual
coordinates, segmentation, detection, source registration or alignment,
vectorization, automatic cropping, automatic contour or silhouette work,
product-specific pipelines, templates, or per-board tuning. It must not use a
generated cord mask, deterministic cord overlay, or manual raster repair after
the built-in edit. The source prompt may name evidence-backed facts and
preservation constraints, but it may not encode hand-measured pixel positions.

## Absolute preservation invariants

The accepted output must retain the original asset's exact:

- pixel dimensions;
- alpha channel and alpha values;
- canvas and aspect ratio;
- framing and scale;
- board position;
- background;
- board pixels and hold pixels;
- colors and materials; and
- all unrelated pixels.

The only permitted changed pixels are those necessary to replace or correct
source-proved cord pixels. Existing non-cord pixels revealed by removing a
wrong cord remain subject to the foundation feasibility and preservation
contract; if the one edit cannot resolve that region without inventing or
altering unrelated content, the asset is blocked. A candidate that improves
cords while changing any invariant is rejected, even if the visual difference
seems harmless or attractive.

The foundation validator is the mechanical authority for exact preservation,
but passing it is not proof of source correctness. Human evidence review is
also mandatory. Conversely, visual similarity is not a substitute for exact
validator results.

## Package and overlay integrity

The existing package remains the product identity boundary. Supported
orientation changes stay presentations of the same physical product. This
cohort does not create new revisions, holds, training semantics, or accessory
copy.

Saved canonical paths in `board.json` remain the sole source for normal
rendering, active highlighting, and hit testing. Image generation neither
proposes nor validates geometry. This cord-only cohort must preserve every
`board.json` file, including all canonical paths and geometry metadata, byte-
for-byte without exception. A discovered geometry or overlay defect blocks
the affected surface here and becomes a separately scoped future task; it is
never corrected in this cohort.

Do not use image-driven hold detection, segmentation, generated masks or
contours, source registration or alignment, vectorization, automatic path
simplification, automatic cropping, or proposal/refine/promote geometry
workflows. Do not create proposed geometry for later cleanup or infer a shape
constraint from pixels.

Every previously accepted repair is an immutable regression baseline,
including repairs within the enumerated cord records. No cohort change may
overwrite, restyle, or indirectly undo any accepted repair.

## Validation

Validation is presentation-complete, not asset-sampled. Every unique
presentation and every alias must receive a recorded Workbench review and an
isolated-iOS review disposition, including records that share one ledger-
declared asset. A blocker never excuses a missing visual-review record. If a
surface cannot be rendered or reviewed, record that inability as the blocker
for that surface in each review system that could not produce a disposition.

### Automated gates

The implementation must pass the accepted foundation feasibility gate and
validator, final-inventory package validation, package status checks, focused
tests for the changed packages and ledger behavior, and the full relevant
package test suite. These checks must establish at least:

- complete ledger enumeration with no skipped alias or orientation;
- exactly one built-in edit-attempt record per supported unique ledger-declared
  asset across all cohorts, zero for every unsupported asset, and no duplicate
  attempt for a shared path;
- dimensions, alpha, canvas, and all non-cord preservation invariants;
- byte-for-byte preservation of every `board.json` file;
- valid package declarations and asset inventory;
- terminal disposition for every cohort row; and
- no promotion of a blocked or rejected candidate.

No command is prescribed here for a foundation artifact that has not landed;
the merged accepted foundation defines those interfaces. Existing repository
package commands continue to apply through the `add-hangboard` contract.

### Workbench review

Use Workspace 1's presentation-complete capture to inspect every unique
presentation and alias in its actual final orientation. For each row, record
human confirmation of:

- complete cord topology and silhouettes;
- correct source-supported routing;
- presentation-specific taut direction and canvas-down gravity;
- exact preservation of board, holds, material, background, framing, scale,
  and unrelated pixels;
- normal overlay alignment;
- all-active overlay alignment;
- each individual hold overlay; and
- hit-testing alignment.

Aliases are opened and reviewed as aliases; reviewing only the shared source
presentation is insufficient. Every row records either a completed Workbench
review result or the exact reason Workbench could not render or review that
surface. The latter is the row's Workbench blocker, not permission to omit the
row.

### Isolated iOS review

Use the accepted DEBUG review route on a dedicated workspace-owned simulator.
The simulator is addressed by its explicit UUID for creation, boot, build,
install, launch, capture, and cleanup; `booted` and shared device names are
forbidden. Use workspace-specific Derived Data and confirm the installed app
comes from this workspace before reviewing it.

For every unique presentation and alias, inspect the normal board, all-active
state, representative individual holds, and hit testing. Confirm the app does
not crop cords or board silhouettes, that the selected presentation has the
same correct routing and gravity as Workbench, and that overlay alignment did
not drift. Every row records either a completed isolated-iOS review result or
the exact reason the app could not render or review that surface. The latter is
the row's isolated-iOS blocker, not permission to omit the row. A successful
build is not visual acceptance.

## Regression boundary

Rejected commit `0ae9fc84fdcfc0aaf06e152169841a3776d8f995` and its exact
revert `90b85ce2fd0e0328aa65756cbbbc0a3f3705750b` are the principal
regression example. That rejected change modified many assets and geometry
records together and was fully reverted. Neither its raster outputs nor its
geometry adjustments are accepted evidence, reusable candidates, or a basis
for this cohort.

Reviewers must compare the proposed diff against this failure mode: broad
cross-package changes, topology or overlay drift, generated non-cord changes,
and apparently corrected cord physics without presentation-complete proof are
grounds for rejection. The exact revert is the clean baseline until the
accepted Workspace 1 foundation commit is merged.

## Error and blocking semantics

Failures are local to the narrowest evidence-backed unit, but acceptance is at
cohort scope:

- **Dependency unavailable:** wait. Do not implement, cherry-pick an
  unaccepted approximation, or recreate foundation-owned tooling.
- **Feasibility gate rejected:** stop cohort editing. Preserve the gate output
  and report the dependency failure; do not attempt a manual workaround.
- **Missing or conflicting primary evidence:** mark the record blocked with
  the exact missing route, orientation, revision, or attachment fact.
- **Port-A-Board option 4 unresolved:** keep it blocked; do not reuse its
  current shared asset as proof, and do not invoke an image edit for it.
- **Single edit violates an invariant:** reject the candidate and block the
  affected asset records. Do not resize, mask, retouch, crop, or retry.
- **Cord topology or physics is uncertain:** block rather than invent hidden
  continuity, hardware, or force direction.
- **Workbench or iOS review fails:** do not promote or commit the affected
  asset. Record the failed presentation and alias explicitly. If a surface
  cannot be rendered or reviewed, record that inability as its blocker and
  still record a disposition for both Workbench and isolated iOS.
- **Geometry or overlay defect discovered:** block the surface and open a
  separately scoped future task; preserve every `board.json` byte here.
- **Package or test failure:** the cohort is not commit-ready even if its image
  review passed.
- **Cleanup failure:** retain ownership records for safe retry and do not
  report completion until exact owned-resource deletion is verified.

Blocked records remain visible in the ledger and final blocker list. They are
not silently omitted, converted to passes, or described as deferred without a
specific evidence or validation reason.

## Owned-resource lifecycle

All temporary inputs, built-in edit outputs, review matrices, captures, logs,
Derived Data, and other generated artifacts belong under a workspace-owned
`.context` path. Derive the owner from the final component of
`${PASEO_WORKTREE_PATH:-$PWD}` and include that owner in every external
resource name. Record ownership immediately.

Before invoking the built-in image generation or editing capability, install
the cleanup traps and write a pending ownership record for that invocation.
No image call may begin first. Because the built-in image tool initially saves
outside the repository, move the exact output immediately into the owned
`.context` area, update the ownership record, and verify that the exact copy at
the tool's default location no longer exists before any review or promotion.
Promote only an accepted output to the declared package path.

Before creating a simulator or any other external resource, install exit,
interrupt, and termination traps that shut down and delete only the exact
owned resource. Simulator ownership uses both pending and owned manifests so
an interruption between creation and registration remains recoverable.
Cleanup runs on success, failure, and interruption. Verify deletion before
reporting completion. Leave shared, standard, unknown, and other workspaces'
resources untouched. If cleanup cannot be verified, keep the ownership
records and report the failure instead of claiming success.

Rejected candidates and source copies are removed after their required hashes,
source roles, and rejection reasons have been recorded in the accepted ledger.
No `.context` artifact is committed.

## Commit and communication boundaries

The implementation uses a fresh delegated agent for each implementation or
configuration task, with review checkpoints between tasks, as required by
`AGENTS.md`. The controller does not make implementation changes directly.

Each cohort commit must be focused and must contain only complete supported
asset/package work plus the explicit terminal blocker records necessary to
account for that cohort. Before committing, verify all automated, Workbench,
isolated-iOS, preservation, and cleanup gates. Push every new commit to the
current remote branch automatically.

Do not update, retarget, force-push, comment on, or merge PR #388 as part of
this work. A normal push to this cohort's own branch is the only remote source
change authorized by this specification.

After the final accepted cohort commit is pushed, send Workspace 4 a Paseo
message containing:

- the full accepted commit hash;
- the pushed branch name;
- the complete blocker list, including Port-A-Board option 4 unless exact
  current-revision primary evidence cleared it before editing;
- the terminal reason for each blocker; and
- confirmation that PR #388 was not updated or merged.

Do not send an unaccepted, unpushed, documentation-only, or intermediate hash
as the cohort handoff.

## Acceptance criteria

The cohort is accepted only when:

1. The explicitly accepted Workspace 1 foundation commit was merged before
   any cohort implementation.
2. The accepted ledger enumerates every target family record, both MXEdge
   variants, all associated aliases, and all rotated/inverted presentations.
3. Every real source-proved cord appears, and every load-bearing segment is
   taut in the correct presentation-specific direction under canvas-down
   gravity.
4. No presentation was created by rotating completed cord pixels into a
   physically incorrect orientation.
5. MXEdge uses only source-supported perimeter/groove routing and no invented
   side holes.
6. Port-A-Board option 4 remains explicitly blocked with zero image edit
   attempts unless exact current-revision primary evidence resolved its route
   before editing.
7. No hidden continuity, knot, terminal, grommet, doubled cord, hole, or
   attachment hardware was invented.
8. Every supported unique ledger-declared asset received exactly one source-
   grounded built-in edit attempt globally across these cohorts, every
   unsupported asset received zero attempts, and no shared path received a
   duplicate attempt or prohibited postprocessing/product-specific handling.
9. Every preservation invariant passes exactly.
10. Every unique presentation and alias has recorded Workbench and isolated-
    iOS dispositions. Accepted rows pass topology, route, gravity, silhouettes,
    image preservation, and overlay/hit-test alignment; blocked rows retain
    both review dispositions, and any inability to render or review is the
    explicit blocker for that surface rather than an omitted review.
11. Every `board.json` file and every previously accepted repair remain byte-
    for-byte intact, and the `0ae9fc84` failure is not reintroduced.
12. All owned resources and temporary artifacts were cleaned up and deletion
    was verified.
13. Only complete, source-supported cohort work was committed and pushed.
14. Workspace 4 received the pushed accepted hash and complete blocker list
    through Paseo.
15. PR #388 was neither updated nor merged.
