# Tension Grindstone Pro CAD provenance (2026-09-26)

## Revision and approval

This record covers the discontinued 2017 Tension Grindstone Pro (`tension.grindstone-pro`), not the original Grindstone or current Grindstone Mk2. The user approved the exact two-photo visual evidence set and the CAD migration design in this session. The user also approved retaining `phone-slot` as a no-depth utility contact with estimated display geometry.

## Evidence retained and reviewed

Both approved images are archival Climbing magazine CDN photos, not manufacturer assets. They are retained only in the workspace review scratch directory and are not redistributed in this package.

| Evidence | URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| Climbing 2017 front photo | https://cdn.climbing.com/wp-content/uploads/2017/11/dsc09271.jpg | `929108c3f712a7186711543f705c4855eb95a0cc3dcf11be5c6d545e568c5407` | Pro revision identity and front contact arrangement |
| Climbing 2017 alternate angle | https://cdn.climbing.com/wp-content/uploads/2017/12/hptensionboard.jpg | `39a55492120d84fd6a35780116c6b1a21853e2440d9ace6796b559293f22bea9` | Distinct view of the same Pro revision and stepped body depth |

The archival source set and contact inventory are cross-referenced to [`2026-08-12-soill-tension-board-packages.md`](2026-08-12-soill-tension-board-packages.md), Grindstone Pro section. The 2017 [Power Company interview transcript](https://www.powercompanyclimbing.com/blog/2017/7/5/episode-49-a-better-strip-of-wood-with-tension-climbing) supplies the published 35 mm warm-up edges; paired 20/15/10 mm edges; 30 and 22 mm center edges; 45 mm monos; 25 mm two-finger pockets; and 7 mm 15-degree incut, and identifies the phone slot as a utility feature. [Gear Institute's 2017 coverage](https://gearinstitute.com/sneak-peek-the-climbing-gear-that-wont-be-at-outdoor-retailer/) independently corroborates the pockets, phone slot and edge-focused design.

## Authored geometry and field mapping

The canonical contact inventory is unchanged: `phone-slot`, `edge-35-left/right`, `edge-7-incut`, `edge-20-left/right`, `mono-45-left/right`, `pocket-25-left/right`, `edge-30-center`, `edge-22-center`, `edge-15-left/right`, and `edge-10-left/right` (16 contacts). IDs and published depth facts are mapped from the source audit above and remain exact in the embedded manifest.

The native source is `Hangboards/tension-grindstone-pro/tension-grindstone-pro.FCStd`. Its body envelope (560 × 205 mm), three tier widths (560/550/535 mm), tier heights and depths, rounded corners, all contact centers/opening widths/opening heights/radii, and the utility-slot recess depth are operator-selected display estimates based on the approved photos. They are not manufacturer dimensions. The source authoring script under `.context/` records every numeric input. `dimensions` remains “Not published by manufacturer”; the presentation aspect ratio is the estimated display envelope ratio. The user-approved phone slot has no `depth` metadata; its 7 mm CAD recess is a display-only estimate and is not asserted as a climbing depth.

The 7 mm / 15-degree incut is represented with an authored ruled profile whose maximum recess equals the published 7 mm depth. Published contact depths are validated against the CAD contact regions during compilation. Unsupported engraving, screws, mounting details and other unseen construction features are omitted. No routine or training instruction was changed.

## Build and review

`Tools/HangboardCAD/compile_board.py` reopens and recomputes the FreeCAD source, verifies all published contact depths, and writes the unbound USDZ plus hash-bound contact descriptor. The package contains no raster fallback or materials/textures. `board.json` is generated from the embedded `HangTenBoardManifest` and is ignored/not committed.

The native BREP is valid and contains all authored cuts. The compiler exports 17 nodes (one body and 16 contacts). The direct front review render has limited visual contrast because cavity floors are close in color and align behind the openings; an oblique front review view exposes the stepped depth and pocket floors. The required front/side/top comparison against the previous committed display asset is preserved under `.context/spiky-buffalo-grindstone-pro/previews/grindstone-pro-review-comparison.png`; the review render uses temporary neutral/contrast shading only and does not change the material-free USDZ. App simulator review was not run.

## Limits

The archival photos do not publish overall dimensions or exact cavity proportions. No physical-product accuracy claim is made for estimated body proportions, contact placement, mouth shape, or the utility-slot recess. The display model preserves the source-backed contact identities and published grip depths while explicitly approximating their appearance.
