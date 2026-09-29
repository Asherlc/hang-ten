---
name: audit-3d-hangboard-suspension
description: Use when a Hang Ten 3D board is missing an expected cord, Apple On-Demand Resources or offline caching is suspected, or suspension evidence, topology, or package metadata needs review.
---

# Audit 3D hangboard suspension

Treat suspension as bundled package metadata rendered as transient RealityKit
geometry. The USDZ is the only On-Demand Resource (ODR); clearing Apple's ODR
cache cannot make a metadata-driven cord appear.

Read [3D suspension and ODR](../../../docs/3D_SUSPENSION_AND_ODR.md) before
diagnosis or edits. Also read the current cord audit manifest and its retained
evidence rather than relying on an older design note.
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

For a package with a native `<slug>.FCStd`, there is no committed `board.json`:
it is generated from the FCStd's `HangTenBoardManifest` and any adjacent
`suspension.json` at build time (read it with
`python3 Tools/HangboardCAD/board_manifest.py --package <slug>`). Edit the
sidecar when present; otherwise edit suspension in the manifest with
`Tools/HangboardCAD/set_board_manifest.py`. The sidecar must match the model
descriptor's SHA-256. Never create a `board.json` in the package.

Do not bake a cord, anchor, or fallback into the USDZ. Do not infer a hidden
route, through-bore, knot, supplied accessory, or safety property.

## Preserve the evidence contract

Discover model packages at execution time. Every represented or excluded
decision needs an independent `sourceFact`, retained exact-revision evidence,
a ruling, and human approval. Current validated evidence outranks superseded
assumptions; in particular, `yy.baguette-evo` intentionally retains its
source-backed `twoBranchCord` alongside orientation metadata.

For a CAD board (a package with `<slug>.FCStd`), use the standard method in
[CAD cord authoring](../../../docs/HANGBOARD_CORD_AUTHORING.md): the cord
passage is a CAD void, the topology is `twoBranchCord` with `internalLoop` in
`suspension.json`, and `solve_threaded_rope.py` solves the routes. Replace a
hand-authored `pairedLeadCord` when its board moves to CAD, and extend the
solver instead of hand-placing routes when a board does not fit it.

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

For the current Captain Fingerfood DUAL, POCKET, and UNLEVEL revisions, retain
the evidenced upper-lip-to-recess path as ordered paired-lead
`contactPointsInModel`; do not collapse it into a front-floor hole or upgrade it
to an unevidenced through-bore.

## Prove the result

Start with a failing parser/audit/runtime regression. Validate the closed cord
audit, package inventory, JSON, and unchanged USDZ/descriptor hash boundary.
Run relevant Python and XCTest suites. Use `validate-hang-ten-ios` for a
current-source isolated Simulator review of every canonical pose: front,
oblique, active contact, clearance, self-intersection, selection, clear/reappear,
orbit/reset, and workout-driven position. The cord must remain non-pickable and
outside accessibility. Retain provenance for screenshots and clean only exact
workspace-owned simulators and artifacts.
