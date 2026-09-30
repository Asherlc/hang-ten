# Tension Whetstone native CAD source audit — 2026-09-29

The user selected automatic board choice and approved the exact three-image evidence set before authoring. This migration targets the Whetstone shown in Tension Climbing's current product gallery, with two split-depth slot rows, two asymmetric two-finger pockets, a center incut edge, and the continuous ergo-bump jug.

## Retained evidence

`review.json` records the original URLs, publisher, SHA-256 hashes, support mappings, and user approval. Originals are retained adjacent to this audit. The published facts are cross-referenced from [Tension Climbing's product page](https://tensionclimbing.com/products/whetstone), retained as `product-page.html`, and its machine-readable product record `product.json`.

- [Whetstone1.png](Whetstone1.png): Front silhouette, symmetric hold layout, split-depth slot labels, ergo-bump locations. Publisher: Tension Climbing. SHA-256 `e2a130f3ee6d94685e01da1195c54127c47dca51e3558dcdc8b0446640768327`. [Original URL](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Whetstone1.png?v=1726542637).
- [Whetstone5.jpg](Whetstone5.jpg): Right oblique end profile, jug curvature, center-edge incut and pocket relief. Publisher: Tension Climbing. SHA-256 `30122b44592cd3246cecc315c0e64e9455113c267b710dc85550a319e53d4b6a`. [Original URL](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Whetstone5.jpg?v=1726542637).
- [Whetstone6.jpg](Whetstone6.jpg): Left oblique end profile, two-finger cavity relief and stepped slot floors. Publisher: Tension Climbing. SHA-256 `d878a295b61bc2d05e35500d261c21cf76ee746a12c2c45fa8679d6913bbb18d`. [Original URL](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Whetstone6.jpg?v=1726542637).

## Source-to-field mapping

| Field or contacts | Specific source fact | Treatment |
| --- | --- | --- |
| Product identity and productURL | Manufacturer product title Whetstone | Preserved |
| dimensions | Product record: 25 inch wide × 6 inch high × 2 inch deep | Preserved text; CAD envelope 635 × 152.4 × 50.8 mm |
| top-ergo-jug | Manufacturer: custom jug profile with ergo-bumps; front and oblique photos | Existing ID and contact semantics preserved; sculpted display curvature estimated |
| edge-40-center | Manufacturer: 40 mm center edge with 10 degree incut | Preserved depth; authored incut |
| pocket-40-left/right | Manufacturer: 40 mm two-finger pockets | IDs, depth and finger capacity preserved; mouth shape and widths deliberately authored estimates |
| edge-40-left/right | Product key features 40 mm edges; visible 40 labels on front photo | IDs and depths preserved |
| edge-30-left/right | Product key features 30 mm edges; visible 30 labels on front photo | IDs and depths preserved |
| edge-25-left/right | Product key features 25 mm edges; visible 25 labels on front photo | IDs and depths preserved |
| edge-20-left/right | Product key features 20 mm edges; visible 20 labels on front photo | IDs and depths preserved |
| Right slot depth order | Front photo labels both sides left-to-right 40/30 and 25/20 | Corrects legacy raster's mirrored right-side placement; keeps logical IDs |

No routines, grip prescriptions, exercise counts, or coaching claims are introduced. The existing empty gripTypes arrays and twoFingerPocket cues remain source-backed metadata.

## Geometry scope

The CAD is deliberately authored as analytic native geometry from the approved manufacturer evidence. It is an estimated display model, not recovered manufacturing geometry and not a load-bearing design. Unpublished widths, placement, mouth round-overs, silhouette transitions, and jug curvature are display estimates. Published overall dimensions and grip depths are kept separate from these estimates.

Mounting holes, screws, engraved branding, and hardware are deliberately omitted from the display model; this does not imply the physical product lacks them. No materials or textures ship in the USDZ. There is no suspension on this fixed board.

The prior package was raster-only; it provides no genuine prior 3D front/side/top reference. Review must show the new three CAD views adjacent to the prior committed front image and the approved oblique manufacturer references.

## Rendering and regression coverage

The model camera is a display estimate: orthographic framing directed 20 degrees down from a front view, up vector `[0, 1, 0]`, fit padding `0.08`. Both stored aspect ratios use the authored 635 / 152.4 envelope. These are presentation choices, not manufacturer specifications.

Regression checks retain the photographed non-mirrored depth order, full logical contact inventory, native section-edit propagation, unchanged source bytes during validation, and outward surface normals against the actual wood boundary. RealityKit validation loads every Whetstone contact as pickable geometry and checks the renderer's neutral material. Whetstone is included in the existing CI-only simulator asset staging set so those checks do not depend on a simulator ODR download.

## Geometry review

[Prior committed image beside new front, side, and top views](whetstone-before-after.png). [New neutral CAD elevated front view](whetstone-front-elevated.png). Both show the final compiled asset, with no model materials or textures. Side and top are new views because no prior 3D asset existed.

## Validation

The package, CAD, and model Python suites passed: 458 tests, 11 skipped legacy native checks. The Whetstone native check ran and passed, including center-depth and jug-section edits, contact boundary normals, and unchanged saved source bytes. Recompiling with pinned FreeCAD 1.1.3 and OpenUSD 26.08 produced byte-identical USDZ and descriptor files.

[Staging validation](staging-validation.json) confirms identical generated board metadata on Android and iOS, exclusion of the FCStd source from both bundles, the Android inline model hash, and the same iOS ODR model hash. [Delivery validation](delivery-verification.json) records the package inventory and checksum results. [Material validation](material-validation.json) records the absence of material/shader prims, bindings, and texture files.

The iOS unit suite passed on an isolated workspace-owned iPhone 17 Pro, iOS 26.5 simulator: 1,234 tests, three skipped, zero failures. This includes the Whetstone RealityKit load test, all 12 contacts' collision/input targets, neutral renderer materials, the typed media boundary, and catalog/source-boundary checks.

[Runtime validation](runtime-validation.json) records selected IDs confirmed after seven taps on the displayed model. The [inactive board](app-inactive.png), [jug](app-jug.png), [center incut](app-center.png), [right pocket](app-pocket-40-right.png), [left pocket](app-pocket-40-left.png), and right [40 mm](app-edge-40-right.png), [30 mm](app-edge-30-right.png), [25 mm](app-edge-25-right.png), [20 mm](app-edge-20-right.png) regions were visually reviewed. The [landscape view](app-landscape.png) confirms the neutral geometry and selected 20 mm region in the scrollable compact layout. Screenshots use the built and installed Debug app, with no flat image fallback.
