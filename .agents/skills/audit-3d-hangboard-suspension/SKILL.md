---
name: audit-3d-hangboard-suspension
description: Use when a Hang Ten 3D board is missing an expected cord, Apple On-Demand Resources or offline caching is suspected, or suspension evidence, topology, or package metadata needs review.
---

# Audit 3D hangboard suspension

Treat suspension as bundled package metadata rendered as transient RealityKit
geometry. The USDZ is the only On-Demand Resource (ODR); clearing Apple's ODR
cache cannot make a metadata-driven cord appear.

Read [3D suspension and ODR](../../../docs/3D_SUSPENSION_AND_ODR.md) before
diagnosis or edits. Read the board's current source audit and retained evidence;
when an explicit closed cord-audit manifest is supplied, validate it rather
than relying on an older design note. Generated `assets/suspension.json` is not that
audit manifest.
For a cord entering two connected mouths, read
[CAD cord authoring](../../../docs/HANGBOARD_CORD_AUTHORING.md) before choosing
`internalLoop` or changing a winding direction.

## Work from the failing boundary

- A loaded, correct board with no cord points first to `board.json`, position
  selection, suspension parsing, or the transient renderer.
- An unavailable model or hash mismatch points to ODR acquisition, staging,
  lease lifetime, or USDZ validation.
- An older installed/prebuilt app is evidence only when its commit provenance
  includes the suspension renderer and current bundled metadata.

For a board with one flat `Hangboards/<slug>.FCStd`, there is no committed
`board.json`: it is generated from the FCStd's `HangTenBoardManifest`.
If the source carries `HangTenSuspensionAuthoring`, generation also validates
and merges `assets/suspension.json`. A source without that property has no
suspension artifact to find or require. Read the generated board with
`rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug>`. Edit the
document-level `App::PropertyString` `HangTenSuspensionAuthoring` with
`Tools/HangboardCAD/set_cad_authoring.py`; inspect it with
`board_manifest.py --package <slug> --dump-authoring suspension`. Optional
simulation inputs live in `HangTenRopePhysics`. Suspension authoring contains
only topology, dimensions, solver settings, evidence, pose rotations/cameras,
and optional `offsetXZ: [x, z]`. Source/model hashes, settled heights, and
solved routes are generated; never save them into CAD. When suspension
authoring exists, package generation rejects absent/stale artifacts and
mismatches with current authoring inputs.
Never create `board.json` or authored JSON sidecars in the package.

USDZ, model/physics descriptors, and any generated suspension artifact are
ignored files at the existing `Hangboards/<slug>/assets/` paths.
Run `rtk proxy bash scripts/build-board-assets.sh` before package validation;
before an app build use `rtk proxy bash scripts/build-runtime-assets.sh`.
Both use the flat FCStd with its embedded authoring as input. CI consumers download
the producer artifact before validation/staging. Read
[generated artifacts](../../../docs/GENERATED_ARTIFACTS.md) for the boundary.

Do not bake a cord, anchor, or fallback into the USDZ. Do not infer a hidden
route, through-bore, knot, supplied accessory, or safety property.

## Preserve the evidence contract

Discover model packages at execution time. Every represented or excluded
decision needs an independent `sourceFact`, retained exact-revision evidence,
a ruling, and human approval. Current validated evidence outranks superseded
assumptions; in particular, native `yy.baguette-evo` retains source-backed
`cadRoutedCord` alongside orientation metadata. Its descriptor-bound
generated `assets/suspension.json` supplies the current suspension from CAD
authoring with
`ropeSolver.method: "nativeRoutes"`.

For a CAD board (with flat `Hangboards/<slug>.FCStd`), preserve the evidenced
connection graph and use the native solver in
[CAD cord authoring](../../../docs/HANGBOARD_CORD_AUTHORING.md). For evidenced
connected internal mouth pairs, the standard method uses a CAD passage void,
`twoBranchCord` (or the single-loop `threadedLoopCord`) with `internalLoop` in
`HangTenSuspensionAuthoring`, and a CAD-measured channel length. For independent visible
leads, exterior wraps, or mouths whose hidden connection is unknown, use the
documented `cadRoutedCord` / `ropeSolver.method: "nativeRoutes"` contract;
do not invent a connecting channel. Generate every canonical pose against the
actual native solid through the pinned build's `compile_suspension.py` and
retained solvers, then reproduce generated artifacts with
`solve_threaded_rope.py --package <slug> --solid <owned-collision-solid.json> --check`
using the [pinned environment and collider export](../../../Tools/HangboardCAD/README.md#focused-cord-reproduction).
Retain clearance, length, tube and topology checks. Replace
hand-authored `pairedLeadCord` routes when a board moves to CAD, and extend the
solver with evidence and tests instead of hand-placing routes.

For older non-CAD packages, choose the narrowest supported topology: `singleCord` for one attachment,
`pairedLeadCord` for two independent exterior leads, or `twoBranchCord` for
two evidenced ordered passage routes or connected internal mouth pairs.
`internalLoop` additionally requires each branch's two mouths to connect in
the CAD solid and an evidence-backed winding choice at every mouth. Keep
sourced facts distinct from
`displayEstimate` values. A published total rope length is not a per-lead
`restLength`; record any derivation explicitly. A user-approved shorter visual
cord remains a display estimate: adjust its anchor geometry and rest length
coherently, and keep `restLength` at least as long as every required solved
route. Never shorten `restLength` alone to force less visible slack.

For the native Captain Fingerfood DUAL revision, the retained maker title photo
shows both visible leads entering the front cavity's floor openings. Preserve
those front mouth centers and set authoring `mouthAxis: [0, 0, 1]` (runtime
front) for each native lead, then regenerate every pose with the native solver.
A clearance-valid approach through the rear opening contradicts this visible
threading. Do not infer a hidden connection between the two holes. See the
dated DUAL source audit and cord-entry review.

Captain Fingerfood POCKET is already native CAD, with suspension embedded in
its flat FCStd's `HangTenBoardManifest`. Consolidation preserves that existing
CAD-contained setup unchanged. Its retained `pairedLeadCord` and ordered
`contactPointsInModel` are legacy metadata, not proof of a completed native
solver migration. Retaining this pre-existing suspension is an intentional,
POCKET-only legacy exception pending a separate evidence-backed cord revision;
it does not permit `pairedLeadCord` on newly migrated CAD packages.
Any cord revision must follow the evidence-matched native
solver contract above and reproduce every canonical pose; a visible recess
alone does not establish an additional through-bore or hidden connection.
Native UNLEVEL uses its current CAD source audit and `nativeRoutes` metadata.

## Prove the result

Start with a failing parser/audit/runtime regression. Validate any supplied
closed cord audit, package inventory, JSON, and unchanged USDZ/descriptor hash boundary.
Run relevant Python and XCTest suites. Use `validate-hang-ten-ios` for a
current-source isolated Simulator review of every canonical pose: front,
oblique, active contact, clearance, self-intersection, selection, clear/reappear,
orbit/reset, and workout-driven position. The cord must remain non-pickable and
outside accessibility. Retain provenance for screenshots and clean only exact
workspace-owned simulators and artifacts.
