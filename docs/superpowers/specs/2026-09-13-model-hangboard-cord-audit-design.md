# 3D model hangboard cord audit and presentation

## Goal

Ensure every shipped 3D hangboard whose exact product revision includes an
integral or supplied cord is represented with that cord in the app. Do not add
decorative ropes for products that merely can be used with a user-provided rope,
elastic, sling, or anchor.

The cord is display-only: it communicates the real product configuration while
remaining outside the selectable hangboard model and never claiming load,
physics, knot details, or safety properties.

## Scope and evidence policy

The audit begins with every model-media package, not a hand-maintained list:

| Result class | Boards | Evidence status |
| --- | --- | --- |
| Already represented | Tension Flash Board | Existing source packet establishes paired end passages and its supplied portable cord. |
| Known supplied cord candidate | Lattice MXEdge Lift Small and Large | Lattice's [product page](https://latticetraining.com/product/mxedge-lift/) and [warnings](https://latticetraining.com/warnings/mxedge-lift/) describe the cord arrangement and supplied cord. |
| Requires a primary-evidence decision | Nature Stone Hanger | The current product listing establishes a portable hanger, but the retained record must establish whether the cord is supplied/integral before promotion. |
| Explicitly not enough evidence today | YY Vertical Baguette Evo | YY says it can be used with rope or bungee, but does not establish that either is supplied or integral. |
| Expected excluded | Beastmaker 1000/2000, Captain Fingerfood DUAL/POCKET/UNLEVEL, Lattice Triple Rung, Metolius Prime Rib/Project/Wood Grips Compact II | Fixed or non-cord product configurations; the audit records primary-source evidence and the exclusion rationale. |

Each decision is recorded in a source audit with exact revision, primary URLs,
retained visual snapshots, source tier, and a yes/no eligibility ruling. A
candidate must have two materially distinct exact-revision views, including an
attachment-region view where available, before geometry or package metadata is
authored. A human approves each candidate's exact evidence set. Cords only
qualify when supplied or an integral physical component; optional ropes,
bands, slings, and mounting environments are excluded.

## Design

The model package remains one USDZ and one descriptor. Its optional
`media.suspension` metadata describes only a proven physical cord topology:

1. `singleCord` binds an attachment point to an importer-visible body or
   attachment node.
2. `twoBranchCord` binds two source-supported passage pairs and routes each
   branch through its declared passages.
3. `pairedLeadCord` binds exactly two source-supported external attachment
   points. It renders one lead from the shared invisible anchor to each point;
   it deliberately renders no segment between those points. This is only for
   a product, such as Stone Hanger, whose evidence establishes two external
   support branches but does not establish a complete interior cord route.

The renderer transforms the selected position's canonical model pose, solves
the declared cord(s) from an invisible world anchor, and adds non-pickable
transient SceneKit geometry. The model remains the sole source for hold
rendering, highlighting, and hit testing. The anchor, length, radius,
material, knot treatment, pose, and camera values are explicit display
estimates unless the retained source proves them.

No cord is baked into a USDZ, exposed to accessibility, or made selectable.
No environment object (wall, hook, carabiner, weight, band, ceiling) is added.
The existing Flash two-branch implementation remains unchanged except for
shared audit coverage.

`pairedLeadCord` is not a permissive fallback for incomplete two-branch
evidence. Its parser rejects a declared interior route, a third lead, duplicate
or unknown attachment IDs, a non-body/non-attachment node, unknown positions,
or a visible anchor. Its label and source audit must explicitly say that the
unrendered interior section is not established by evidence.

## Delivery slices

1. Add a deterministic catalog audit/test that discovers every model package
   and requires a source-backed `represented`, `excluded`, or `pending`
   classification. `pending` fails promotion, so no qualifying board can be
   silently omitted.
2. Gather and retain the primary evidence packets, obtain human approval of
   the multi-angle views, and document topology and attachment facts separately
   from display estimates.
3. For each approved qualifying board, add the narrowest valid suspension
   metadata. If the existing USDZ lacks a source-supported attachment/passage
   feature, refine only that physical model geometry after the evidence gate;
   final shape work is performed by Astra.
4. Add the closed `pairedLeadCord` package/runtime contract before promoting
   Stone Hanger. It reuses the existing deterministic single-span solver for
   each independent lead, shares an invisible anchor, and never reconstructs
   the product's unproven internal route.
5. Add package, solver, native-picking, clearance, and position coverage for
   every promoted package. Render review artifacts in an owner-prefixed
   `.context` directory, visually review them, then clean up the artifacts.

## Failure handling and tests

Any missing evidence ruling, unresolved attachment, invalid pose, unknown
descriptor node, short/unsolved cord, self-intersection, mesh collision, or
cord hit target leaves that presentation unavailable; it never falls back to a
straight line, raster board, or invented attachment.

For `pairedLeadCord`, either lead failing validation makes the entire
presentation unavailable. The two rendered leads must terminate exactly at
their own documented attachment points, share only the invisible anchor, and
remain mutually clear and clear of the model. No rendering result may imply
that the two endpoints are joined inside the product.

Tests first establish the catalog-audit failure for an unclassified model
package. Per promoted board they verify parser acceptance, all canonical poses,
finite curves, declared attachment endpoints, route/mesh clearance, and that
the cord cannot win model picking. The full package validation and the native
iOS model tests run after each promotion. Evidence snapshots and rendered
review views receive human sign-off before release.

## Non-goals

- Rendering user-provided ropes, resistance bands, or generic portable-board
  accessories.
- Simulating load, swinging, knots, carabiners, hardware, or rope dynamics.
- Adding 2D fallbacks, duplicate models, or cord meshes to logical hold IDs.
- Treating estimated display dimensions as manufacturer specifications.
