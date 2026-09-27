# Escape Beta Board — native CAD provenance

Date: 2026-09-26. Package `escape-beta-22`, revision
`2026-09-contact-first`. The FreeCAD source is
`Hangboards/escape-beta-22/escape-beta-22.FCStd`. Its embedded
`HangTenBoardManifest` replaces the committed `board.json`; the generated
metadata preserves the 22 stable physical contact IDs. The one-off authoring
script lives only in workspace scratch at
`.context/wasteful-scorpion/author_escape_beta.py`. The saved document reopens
and recompiles without that script.

This is a deliberately simplified **display model**, not recovered
manufacturing geometry or a load-bearing CAD plan. The manufacturer photos
establish the outline, open slots, side shape, and hold inventory; unpublished
coordinates and radii below are labeled display estimates. The operator
reviewed and approved the exact four-source set in the 2026-09-26 conversation
before geometry authoring.

## Approved primary sources

| Retained file | Publisher and URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `2026-09-26-escape-beta-cad-sources/front.jpg` | Escape Climbing, <https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_01-02.jpg?v=1700454580&width=1445> | `c318ed1539a205ee7923bebaab00faac0bdb2ba9bf23a7b7009e0747544b94b6` | Symmetric front silhouette, open slot arrangement, continuous upper centre opening |
| `2026-09-26-escape-beta-cad-sources/side.jpg` | Escape Climbing, <https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_03-02.jpg?v=1700454580&width=1445> | `7c6fbbc0a49dd452d828889d1d5443786277ad669072acb1ac3971ea600ecddf` | Published 6 in height and 2 in depth; end wing recedes toward the lower edge |
| `2026-09-26-escape-beta-cad-sources/oblique.jpg` | Escape Climbing, <https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_05-02.jpg?v=1700454580&width=1445> | `668d6b7ba05ea5fc157f4be1018713c47691a328d756332f3b2f3b207270858c` | Open slot mouths, rounded lips, raised end wing |
| `2026-09-26-escape-beta-cad-sources/numbered.png` | Escape Climbing, <https://escapeclimbing.com/cdn/shop/products/2020_Website_Editorials_EscapeClimbing_Breakdown.png?v=1700454580&width=1445> | `89c97e90e6c073d2ec2c98f7b272fc9544188237201ae71001b4212a3678e1d0` | Official numbers 1–11 on both sides, grip type names and published depths |

The [manufacturer product page](https://escapeclimbing.com/products/ec72100)
cross-checks product identity, 26 × 6 × 2 in overall dimensions, and dual
texture. The approved front and numbered images determine which physical
surface belongs to each numbered contact. No training prescription was
inferred from the model.

The superseded Git asset at `db4da303b132d580bfd2df4d6f5638787fc1b8b9`
is a visual cross-check, never a compiler input: USDZ SHA-256
`95c41baa291c134358fa47eb8a9981acabd35bfb2231e14fd7951a9d9a0b0be4`,
descriptor `e26a0258f84d958b6a345c16fdbc5bff1a426d980b1cb1ab8203447c0e4cffb6`,
and retired board metadata
`76ea1f68bca5c753ea09e48cd1209cd7a96d09d46bb621026ca8596a7c215fe3`.

## CAD construction and field mapping

Native coordinates are millimetres, +X right, +Z up, front −Y. The rear plane
is Y = 0. The published 26 × 6 × 2 in dimensions give 660.4 × 152.4 × 50.8 mm.
An XZ `Sketcher::SketchObject` describes a symmetric, manually selected outer
loop; a `PartDesign::Pad` places its front at Y = −50.8. Four depth groups use
rounded Sketcher loops, `PartDesign::Pocket`, and a second Pocket to continue
the opening through to the rear. The pocket seam leaves an exact front section
for each published grip depth. A native `PartDesign::Fillet` rounds the slot
mouths. Separate side-plane Sketcher/Pocket features taper the two end wings.
Each contact is bound to an exact analytic face copy from this native body.
These static copies preserve the reviewed surfaces but are not expression-linked
to later Sketcher edits; reselect them after changing a pocket or wing.

| Number / IDs | Source fact | Authored region / estimated display choices |
| --- | --- | --- |
| 1, `hold-01-left/right` | Thin pinch, bilateral (numbered diagram) | Upper end-wing taper face, Z 0–35 mm |
| 2, `hold-02-left/right` | Wide pinch, bilateral | Lower end-wing taper face, Z −60 to −30 mm |
| 3, `hold-03-left/right` | 38 mm mini-jug, bilateral | Outer upper openings, 38 mm front wall section |
| 4, `hold-04-left/right` | 29 mm incut jug, bilateral | Outer middle openings, 29 mm front wall section |
| 5, `hold-05-left/right` | 12 mm incut edge, bilateral | Outer lower openings, 12 mm front wall section |
| 6, `hold-06-left/right` | 38 mm flat edge, bilateral | Inner upper openings, 38 mm front wall section |
| 7, `hold-07-left/right` | 29 mm flat edge, bilateral | Inner middle openings, 29 mm front wall section |
| 8, `hold-08-left/right` | 12 mm flat edge, bilateral | Inner lower openings, 12 mm front wall section |
| 9, `hold-09-left/right` | 50 mm sloper edge, bilateral | Two halves of the central crown, X −90–0 / 0–90 mm; the full published 2 in body thickness is 50.8 mm, a documented 0.8 mm display difference from the nominal 50 mm grip depth |
| 10, `hold-10-left/right` | 31 mm sloper edge, bilateral | One continuous central upper opening, partitioned into left/right 31 mm contact surfaces at X = 0 without a physical divider |
| 11, `hold-11-left/right` | 12 mm sloper edge, bilateral | Two lower central openings, 12 mm front wall section |

Slot X/Z positions and 7–9 mm plan radii were manually authored as display
estimates against the approved front and numbered images. The lip fillet radius
is a 2 mm display estimate. The wing front profile is piecewise planar at
Y = −50.8, −48, −43, −35, −29, and −25 mm from top to bottom, a deliberate
approximation of the side/oblique photos. No image was segmented, traced, or
used as an automatic geometry input.

The orthographic camera looks 20° down to reveal the slot walls; it is a
presentation choice, not a product fact. Fastener holes, screws, and mounting
hardware shown in the photos are deliberately omitted from the display model.
The USDZ ships with unbound meshes and no material or texture.

## Verification and limits

The compiler checks the 22 exact contact IDs, source reopen/recompute, the
published-depth gate, analytic surface partition, USDZ reimport, and the
hash-bound descriptor. All 38/29/12/31 mm sections are exact. Its 50 mm crown
check accepts the 50.8 mm overall dimension within the source's 1.8 mm
tessellation tolerance. The FreeCAD features are native and editable, while the
contact face copies require manual rebind after a geometry edit.

The previews were compared with the superseded asset from front, side, and
top. The model intentionally has simpler planar bands and end-wing facets than
the manufacturer's molded, rounded surface. The individual slot shapes and
wing transitions are display estimates; no manufacturing tolerances are known.

| Review view | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/escape-beta-22/previous-front.png) | [CAD](../pr-screenshots/escape-beta-22/cad-front.png) |
| Side | [previous](../pr-screenshots/escape-beta-22/previous-side.png) | [CAD](../pr-screenshots/escape-beta-22/cad-side.png) |
| Top | [previous](../pr-screenshots/escape-beta-22/previous-top.png) | [CAD](../pr-screenshots/escape-beta-22/cad-top.png) |

The [iOS hold-map screenshot](../pr-screenshots/escape-beta-22/app-hold-03-left.png)
records the non-default contact selection and highlight.

Final source SHA-256:
`2d3c4755a1868a83cde82c25f9b4a2965086f3a24ed5e613e66c802fd054912c`.
Compiled USDZ SHA-256:
`014497a1d2a399d4aec12e7d0b97dcec22c0c6cf4cf43aa5d6cfba28cc407c23`.
Descriptor SHA-256:
`2797e436006385608aa7fb11bc8ec2a3786ecf8d29e00182b5e64f4e66658d2e`.
`compile_board.py --check` passed the native-source and 22-contact gates;
`verify_reproducible.py --package escape-beta-22` rebuilt the USDZ and
descriptor byte-identically on the pinned macOS toolchain. The package
validator accepted all 64 discovered boards, and the 47-package model-delivery
lock verified with this FCStd as the Beta Board authority. An iPhone 17 Pro
simulator running iOS 26.5 loaded the model on the DEBUG board-detail route and
selected the default left thin pinch. After a full first-boot migration, a
fresh iPhone 17 Pro simulator loaded the same route; tapping the hold-map row
`boardDetail.holdLegend.hold-03-left` selected
`boardDetail.selectedHold.hold-03-left`. Its screenshot shows the upper-left
pocket highlighted and the Left 38mm Mini-Jug card with 38 mm depth. Both owned
simulators were deleted after their runs.
