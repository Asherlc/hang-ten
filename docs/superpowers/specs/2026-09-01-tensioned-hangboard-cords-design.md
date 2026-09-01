# Tensioned Hangboard Cords Foundation Design

## Authority and scope

This design records the foundation-and-evidence phase requested on 2026-09-01
from safe baseline `90b85ce2fd0e0328aa65756cbbbc0a3f3705750b`. The separately named design
and plan commits were unavailable locally and from `origin`, so this document
preserves the user-approved requirements without filling evidence gaps.

The phase delivers no catalog-wide raster repair. It establishes the evidence
ledger and generic gates that every later repair cohort must pass. The rejected
bulk commit `0ae9fc84` and its exact revert `90b85ce2` are the principal
regression pair.

## Source-complete cord ledger

A checked-in JSON ledger has exactly one record for every presentation of every
real product revision in the catalog that bears visible load-bearing cord. The
closed inventory is 20 packages and 47 presentations, including aliases and
rotated or inverted presentations.

Every record identifies the package and presentation, direct source evidence
and URL, presentation orientation, canvas-down gravity, visible cord topology,
load/tension direction, routing, evidence-supported terminals/knots/hardware,
current status, and either an accepted output or an explicit blocker. The
validator cross-checks package identity, presentation identity, asset path,
asset bytes, and the exact 20/47 totals against the live catalog so omissions,
extras, stale assets, duplicate records, and unknown enum values fail closed.

Known blockers remain explicit:

- Frictitious Port-A-Board option 4 has no exact current-revision routing proof.
- All five YY Baguette Evo presentations show visible side strands, while
  hidden continuity, terminals, and hardware are unresolved.

No record may imply hidden topology, knots, terminals, grommets, doubled
strands, colors, routing, or attachment hardware that its cited evidence does
not establish.

## Preservation and cord-physics validation

One generic validator consumes a baseline asset, candidate asset, ledger
record, and method-run evidence. It rejects changed canvas dimensions, lost or
incompatible alpha, background/framing drift, board rescaling or translation,
board/hold/color/material changes, unrelated-pixel changes, unaccounted cord
topology, non-taut load-bearing segments, and a tension direction inconsistent
with that presentation's orientation and canvas-down gravity. Rotated and
inverted aliases are independent physics cases; a source presentation may not
serve as proof that mechanically rotated cord pixels are physically valid.

The validator is generic and data-driven. It contains no product IDs, masks,
coordinates, templates, segmentation, vectorization, registration, cropping,
or per-board thresholds. Failures identify the invariant and presentation.

## Review surfaces

Workbench catalog capture enumerates every declared presentation, not merely
one image per package. Capture filenames and the manifest include both package
and presentation identity, readiness is tied to the selected presentation's
asset and geometry, and the contact sheet contains all requested
presentations.

A DEBUG-only iOS route accepts generic package and presentation identifiers
from launch environment and opens the normal app rendering for that exact
presentation. Invalid or missing identifiers fail visibly. Release builds do
not expose the route and no product-specific branches are permitted.

## Feasibility gate

Before any editing method is promoted, one method identity and one normalized
configuration must be replayed without product-specific changes against the
Aelith, Captain Dual, and MXEdge Large feasibility assets. The gate requires
all three run records, proves that method/config identity is identical, invokes
the generic preservation/physics validator for each, and fails the cohort if
any asset is missing, blocked, or nonconforming. Outputs and diff evidence live
under a workspace-owned `.context` path and are not catalog assets.

The gate protects the exact regression classes demonstrated by `0ae9fc84`:
alpha loss, rescale/reposition, unsupported topology, and overlay
misalignment. It does not promote an editor merely because a candidate looks
plausible.

## Acceptance

Foundation acceptance requires focused red-green tests, full Python package
tests, package validation/status, relevant Swift tests and a simulator build,
fresh Workbench presentation-complete capture evidence, a DEBUG-route smoke
review, and a three-asset feasibility replay. All resources created by the
workspace are named with owner `tensioned-cords-foundation`, recorded on
creation, shut down, deleted, and verified absent before completion.

