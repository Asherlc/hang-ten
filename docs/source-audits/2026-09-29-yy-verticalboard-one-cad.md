# YY VerticalBoard One — native CAD source audit

Date: 2026-09-29. Package `yy-verticalboard-one`; board ID `yy.verticalboard-one`.
The operator approved the exact two-image manufacturer evidence set with “y” before geometry work. This is an estimated interactive display model, not manufacturing or load-bearing CAD.

## Evidence and published facts

Publisher for both photographs: YY Vertical. Product page: <https://www.yyvertical.com/en/products/verticalboard-one> (cross-checked 2026-09-29).

| Retained evidence | Original URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `.context/supreme-zebra-cad-evidence/one-0.webp` | <https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY-VBO-1gris.webp?v=1770713584> | `2d8c253bc59989604d3d668fbbde13794470b161426c8910729f91363092f635` | Complete front inventory, symmetric stepped shell, through handle, printed edge/pocket depths, sloper positions. |
| `.context/supreme-zebra-cad-evidence/one-3.webp` | <https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY-VBO-7gris.webp?v=1770127412> | `6497f51e6bba81e283bd5565522b2654966c253a2d388d932ee5c77ccbcd87c8` | Distinct left oblique detail, cavity walls/floors, rounded mouths, stepped lower shelf, printed depths and 35° sloper. |

The product page confirms 620 × 130 × 55 mm, 20° and 35° slopers, 30/50 mm two-finger pockets, and inclined 25 mm edges at 30°. The photo's lower outer edges are marked 20 mm and inner edges 18 mm. The page's generic list instead says 18/25/30/35/45 mm and omits the 20 mm pair, while claiming an unmatched 35 mm edge. The approved photographs and existing contact inventory govern that conflict: all 20 contact records, depths, names, kinds, finger capacities, grip types and order remain unchanged. No training content was introduced.

## Field mapping and construction

`HangTenBoardManifest` contains the prior schema-v3 metadata with model-only `assets/primary.usdz` and `assets/primary.model.json` media in place of raster geometry. Presentation aspect ratio is now 620/130; the legacy top-level aspect ratio remains 2.0. Canonical raster paths are removed with the raster asset. The FCStd source is self-contained: constrained native Sketcher profiles, Part extrusions/lofts/fusions/cuts, and native semantic face binders; there is no Python feature or external geometry dependency. The throwaway authoring script is `.context/supreme-zebra-one-cad/author.py`, not a committed build input. The document follows the native feature/semantic contact structure used for the Trango Rock Prodigy Pivot precedent.

Native millimetres: +X right, +Z up, front −Y; wall plane Y=0. Upper shelf front is Y=−55; the lower shelf front Y=−32 is an estimated 23 mm setback. Full published envelope is 620 × 130 × 55 mm. The two halves use deliberately authored exact symmetric values; no image tracing, detection, cropping, vectorization, registration, mesh inference or automatic simplification was used.

The following are **display estimates**, except the depth column (photo-backed) and the 30° inclined-pair angle (product-page-backed). Each ±X row is two contacts. Width and height are the inner capsule section before the mouth round-over. All capsules use semicircular ends with radius height/2. A ruled three-station mouth uses an estimated 2.5 mm quarter-round with (inward Y, outward section offset) stations (0,2.5), (0.732233047,0.732233047), (2.5,0) mm. The remaining cavity is a native extrusion to an actual floor at the stated depth; the 25 mm inclined pair rises through the body at 30°.

| Contact IDs | X | Z center | Width | Height | Front Y | Published depth | Inclination |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `edge-25-left/right` | ±254 | 100 | 82 | 24 | -55 | 25 | 0° |
| `edge-45-left/right` | ±254 | 64 | 82 | 24 | -55 | 45 | 0° |
| `pocket-50-left/right` | ±178 | 64 | 39 | 25 | -55 | 50 | 0° |
| `edge-inclined-25-left/right` | ±105 | 64 | 85 | 20 | -55 | 25 | 30° |
| `pocket-30-left/right` | ±66 | 99 | 41 | 22 | -55 | 30 | 0° |
| `edge-20-left/right` | ±231 | 22 | 83 | 24 | -32 | 20 | 0° |
| `edge-18-left/right` | ±138 | 22 | 83 | 24 | -32 | 18 | 0° |

Center handle: estimated inner capsule centered X=0/Z=39 mm, 110 × 25 mm, cut through the full 55 mm thickness. Its front mouth has the same estimated 2.5 mm round-over as the cavities, so the outer mouth is 115 × 30 mm. Its actual internal wall is the selectable contact; the mouth has no cap.

Top contacts: outer jug spans start at X=±195 mm. Each jug has a 14 mm front crest radius with analytic cross-section from Y=−55/Z=116 to Y=−41/Z=130, followed by the top flat. The symmetric 35° slopers span X=98…195 mm and −195…−98 mm; their active slope runs 40 mm inward from front Y=−55 to Y=−15, ending at Z=128. The 20° center sloper spans X=−98…98 mm with a 30 mm inward slope ending at Y=−25/Z=128. Remaining rear ledges lie at Z=128. Sloper angles are published, while all run lengths, spans, crest radius and rear ledge height are display estimates.

The upper front silhouette is a deliberately authored analytic rounded polygon. Each shelf has an additional native 2 mm front-perimeter fillet. The lower shelf has small symmetric scallops between the paired edge stations, as supported qualitatively by both approved photos. The complete estimated unrounded stations and corner radii are retained here for reproducibility; the rounding consists of tangent circular arcs, not pixel-derived polylines:

```json
{
  "upperOutlineXZ": [
    [
      -310,
      130
    ],
    [
      310,
      130
    ],
    [
      310,
      44
    ],
    [
      212,
      44
    ],
    [
      204,
      48
    ],
    [
      194,
      44
    ],
    [
      163,
      44
    ],
    [
      152,
      48
    ],
    [
      141,
      44
    ],
    [
      88,
      44
    ],
    [
      67,
      0
    ],
    [
      -67,
      0
    ],
    [
      -88,
      44
    ],
    [
      -141,
      44
    ],
    [
      -152,
      48
    ],
    [
      -163,
      44
    ],
    [
      -194,
      44
    ],
    [
      -204,
      48
    ],
    [
      -212,
      44
    ],
    [
      -310,
      44
    ]
  ],
  "upperCornerRadii": [
    20,
    20,
    19,
    5,
    3,
    5,
    5,
    3,
    5,
    9,
    15,
    15,
    9,
    5,
    3,
    5,
    5,
    3,
    5,
    19
  ],
  "lowerOutlineXZ": [
    [
      -287,
      57
    ],
    [
      287,
      57
    ],
    [
      281,
      0
    ],
    [
      193,
      0
    ],
    [
      185,
      4
    ],
    [
      177,
      0
    ],
    [
      90,
      0
    ],
    [
      80,
      4
    ],
    [
      -80,
      4
    ],
    [
      -90,
      0
    ],
    [
      -177,
      0
    ],
    [
      -185,
      4
    ],
    [
      -193,
      0
    ],
    [
      -281,
      0
    ]
  ],
  "lowerCornerRadii": [
    12,
    12,
    23,
    4,
    3,
    4,
    4,
    3,
    3,
    4,
    4,
    3,
    4,
    23
  ]
}
```

Every exported cavity contact is a native binder to physical cut-boundary walls and floors of the final solid. There are no disconnected front caps or artificial highlight surfaces. `GripDepth` on each named depth extrusion drives its depth expression, so saved native edits rebuild the cutter, body and contact together. This is native editable CAD, with explicitly pinned display estimates rather than a recovered manufacturer drawing.

Mounting bores, screws, logos, printed markings, finish and removable magnetic inserts in their side storage positions are omitted from the display. Those omissions do not assert their absence on the product. This wall-mounted package needs no suspension metadata. The USDZ uses only unbound meshes, without materials, textures or color adornments.

## Prior asset and validation

There was no prior 3D model. The previous committed `assets/primary.png` is retained only in workspace review output (`prior-raster.png`), so no prior side/top view can be supplied. It is a comparison reference, never geometry input.

Prior raster SHA-256: `68cb5d5023d6ef440c9de4629becb96004337b51f2d5cf6952db7283a2b1821a`.

The final standalone source passed 77 native checks after reopening: valid closed single solid, exact 620 × 130 × 55 mm optimal envelope, all Sketcher profiles constrained, all 20 contact identities, exact scalar depths, contact surfaces on the actual solid, absent mouth caps and actual recessed floors. Native edits changed the left 25 mm depth to 28 mm and the inclined right 25 mm depth to 27 mm; each rebuilt its cavity and contact while every unrelated contact retained its depth. The checks restored the in-memory dimensions and verified the saved FCStd bytes were unchanged. The checks use the optimal B-rep envelope because conservative control-point bounds of rounded surfaces can exceed the physical surface.


Final pinned FreeCAD compile: **57,372 triangles**, 20 contacts, 21 nodes, USDZ 1,377,400 bytes. All 14 scalar cavity depths were exact. The exported USDZ reimported successfully, contains only `stage.usdc`, and inspection found no Material/Shader prim, material-binding relationship or texture entry. The descriptor binds the actual imported meshes and matches the USDZ hash. Pure manifest generation again confirmed byte-for-byte parsed equality of all 20 contact records and all other factual fields.

- FCStd SHA-256: `5e6b0ab9d7a0d7a7336e4634f601e5bc4440cef482d5aa47729b1373ab50ad73`
- USDZ SHA-256: `57e63588b4671fc4ac0e6556dd8c499b131575dce096c380f0a5d3e54d7c93c5`
- Descriptor SHA-256: `a2f6ccff8286c3bf0ea048394a1bef4e47179a0c9c461615042aef0e1f8522ea`

Final exact-asset Storm renders were visually reviewed in front, side, top and oblique views. They show open cavities with physical floors, the inclined edge pair, layered shelf and through center handle. The comparison with the complete prior committed raster is `.context/supreme-zebra-one-cad/comparison.png`; individual exact-asset views are `front.png`, `side.png`, `top.png` and `threequarter.png` in that directory. Prior side/top angles are unavailable because no prior 3D asset existed.

Workspace reports are `compile-final.json`, `native-check.json` and `final-verification.json`. Temporary FreeCAD wrappers were created only inside `.context/supreme-zebra-one-cad/tmp` and removed automatically; no server, simulator or other external resource was started by this package author. Repository-wide tests, staging, delivery-lock refresh and app acceptance are handled by the parent migration task.

The primary model display uses an orthographic camera tilted 15° down with 8% fit padding. This is a presentation estimate to make pocket walls and floors visible, not a manufacturer geometry fact.

Final independent delivery results are recorded in [the batch delivery audit](2026-09-29-yy-verticalboards-delivery.md). The pinned rebuild reproduced both the USDZ and descriptor byte-identically.


## Current committed source provenance after finish integration

The standalone compile/rebuild evidence above refers to the source before main's runtime finish metadata integration: `5e6b0ab9d7a0d7a7336e4634f601e5bc4440cef482d5aa47729b1373ab50ad73`. The current committed `yy-verticalboard-one.FCStd` SHA-256 (and Git LFS object ID) is `eee7a5194769cbca5d8f15041b2252f4b6635101ba884a9e089eaac0929bb728`.

Merge commit `79373106a` added only `presentations[0].media.display.surfaceFinish = "neutral"` using the supported manifest authoring tool. Comparing both source archives confirms identical member inventories and byte-identical geometry members; only `Document.xml` changed. Parsed manifests differ only by that finish field, with every contact and factual field unchanged. The delivered USDZ and descriptor hashes remain those recorded above. This is metadata provenance reconciliation, not a new geometry build or a claim that the new source hash was the earlier reproducibility input.
