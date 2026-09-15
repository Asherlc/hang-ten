---
name: audit-3d-hangboard-suspension
description: Use when a Hang Ten 3D board is missing an expected cord, Apple On-Demand Resources or offline caching is suspected, or suspension evidence, topology, or package metadata needs review.
---

# Audit 3D hangboard suspension

Treat suspension as bundled package metadata rendered as transient SceneKit
geometry. The USDZ is the only On-Demand Resource (ODR); clearing Apple's ODR
cache cannot make a metadata-driven cord appear.

Read [3D suspension and ODR](../../../docs/3D_SUSPENSION_AND_ODR.md) before
diagnosis or edits. Also read the current cord audit manifest and its retained
evidence rather than relying on an older design note.

## Work from the failing boundary

- A loaded, correct board with no cord points first to `board.json`, position
  selection, suspension parsing, or the transient renderer.
- An unavailable model or hash mismatch points to ODR acquisition, staging,
  lease lifetime, or USDZ validation.
- An older installed/prebuilt app is evidence only when its commit provenance
  includes the suspension renderer and current bundled metadata.

Do not bake a cord, anchor, or fallback into the USDZ. Do not infer a hidden
route, through-bore, knot, supplied accessory, or safety property.

## Preserve the evidence contract

Discover model packages at execution time. Every represented or excluded
decision needs an independent `sourceFact`, retained exact-revision evidence,
a ruling, and human approval. Current validated evidence outranks superseded
assumptions; in particular, `yy.baguette-evo` intentionally retains its
source-backed `twoBranchCord` alongside orientation metadata.

Choose the narrowest supported topology: `singleCord` for one attachment,
`pairedLeadCord` for two independent exterior leads, or `twoBranchCord` only
for two evidenced ordered passage routes. Keep sourced facts distinct from
`displayEstimate` values. A published total rope length is not a per-lead
`restLength`; record any derivation explicitly. A user-approved shorter visual
cord remains a display estimate: adjust its anchor geometry and rest length
coherently, and keep `restLength` at least as long as every required solved
route. Never shorten `restLength` alone to force less visible slack.

## Prove the result

Start with a failing parser/audit/runtime regression. Validate the closed cord
audit, package inventory, JSON, and unchanged USDZ/descriptor hash boundary.
Run relevant Python and XCTest suites. Use `validate-hang-ten-ios` for a
current-source isolated Simulator review of every canonical pose: front,
oblique, active hold, clearance, self-intersection, selection, clear/reappear,
orbit/reset, and workout-driven position. The cord must remain non-pickable and
outside accessibility. Retain provenance for screenshots and clean only exact
workspace-owned simulators and artifacts.
