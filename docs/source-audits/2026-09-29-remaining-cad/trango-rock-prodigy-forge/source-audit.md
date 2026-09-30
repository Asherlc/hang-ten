# trango-rock-prodigy-forge source audit

Current Forge split unit revision. Manufacturer photo angles show tapered long wing, broad upper sloper with elevated block, distinct drafted pockets and narrow crimp ledges. Official depth guide and grip chart establish numeric depths and names; overall per-side dimensions are 5.25 x 12.75 in. Both left/right contact sets remain as currently modeled.

Source-set approval: asherlc, 2026-09-29, direct conversation: “those are fine, feel free to use more searches for individual boards as needed”. Consolidated snapshot: `.context/placid-badger/source-review.json`.

## Sources

- [product-01.jpg](https://cdn.shopify.com/s/files/1/0282/7557/2841/products/22820_Rock_Prodigy_Forge_Main_Image.jpg?v=1582662057) — Trango; SHA-256 `838e2a95316508157a6f85c12c665511e797ae5bfb21e9917e3ed67c92ed80c4`. Manufacturer product gallery.
- [product-03.png](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/22820_RockProdigyForge_AltImage1_6974b648-94cf-464a-8ea9-f0a14eb8958b.png?v=1755037539) — Trango; SHA-256 `a2a4e18e3fe3c716c171f2726fe0b3d9ef653cc77ad7c30b56e304476cec1914`. Manufacturer product gallery.
- [product-04.png](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/22820_RockProdigyForge_AltImage2_3a6173b2-1121-4285-a59a-42f178be5aa7.png?v=1755037539) — Trango; SHA-256 `678688bbf11a66fc5d77961e80d5af6b5a35548548c69bbd25588389f6fba136`. Manufacturer product gallery.
- [product-05.png](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/22820_RockProdigyForge_AltIMage3_6794e534-75a5-4109-8a9e-0eb213f5a0e0.png?v=1755037540) — Trango; SHA-256 `ce64d24741944997302ad503882eeaee958cca57a5cf4f80b23a6436bad6487f`. Manufacturer product gallery.
- [product-06.png](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/22820_RockProdigyForge_AltImage4_07218e65-ff06-4c5e-9590-f694e7d67b70.png?v=1755037540) — Trango; SHA-256 `de38abd8ebf79dda10a2f3e9f7f0a77a34f81a314d3e3afa02b69eb7e6bc80c2`. Manufacturer product gallery.
- [depth-guide.pdf](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887) — Trango; SHA-256 `9d56bd2fa27908a2a96ded090f3cacf0278e4be0ea659191eea7c582ae6efff3`. Published hold depths.
- [hold-chart.pdf](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/forge-grip-identification-chart.pdf?v=1588609203) — Trango; SHA-256 `1603ceaf2f4bedbf2698235eea075b90a78c8115020f23248e1a8bf0466ddf5b`. Hold identities and locations.

## Immutable pre-migration reference

Git commit `d0e4e95191e4a76822815bb4eeef3a32caa6fea0`; USDZ SHA-256 `b660392fce1b7289e1d0b0dd07a6644ba3824fd1a777fdb25d4c3319bbdae783`; descriptor SHA-256 `b082e9a64c46707b659937c3cecdfc4dbae214c26391af764d1c581720633898`. Bytes resolved through Git LFS and checked against the pointer. These are review/measurement references only.

## Retained primary visual comparison

![Manufacturer evidence](sources/product-01.jpg)

![Manufacturer evidence](sources/hold-chart-page-1.png)

## Native construction and verification

The canonical source is `Hangboards/trango-rock-prodigy-forge/trango-rock-prodigy-forge.FCStd`. It contains 29 fully constrained Sketcher profiles with three native wing sections, a deliberately drawn curved perimeter, a separate curved crimper ridge and five pocket lofts for the right unit, with native mirrored left-unit solids and semantic surfaces. The source embeds the original board metadata exactly and reopens/recomputes without authoring scripts, Python callbacks or an external mesh dependency. Named depth parameters drive the physical cavity floors. The obsolete on-disk `board.json` was removed only after an exact metadata roundtrip.

Each unit follows the manufacturer nominal 323.85 x 133.35 mm face envelope. The 30 and 40 degree top planes, 7.5 mm closed crimps, 25/15 mm MR pockets and nominal 7–20 mm variable rails follow the official diagrams. The IMR pocket is one continuous native cavity per unit; its nominal 19–31 mm floor is split into the existing shallow/deep semantic halves, preserving the original absence of structured IM depth fields. Native checks enforce the deeper outer half and shallower inner half. The diagonal variable rail and deliberately drawn stepped closed-crimp mouth follow the distinct source shapes; their angle and detailed contour, unit spacing, opening sizes, ridge profile and unspecified blends are operator-selected display estimates. Native mirroring makes the paired shape and depth edit exact. Unrefined native boolean seams pass through each IMR cavity at its semantic boundary and delimit the narrow flat-edge pressure strip, so physical and contact tessellation share the same boundaries. Mount holes, screws and the visible fastener inside the IMR pocket are deliberately omitted under repository policy.

Native checking passed validity for 2 solid(s), all 20 stable contact IDs, body-surface membership, absence of contact sheets on the rear plane and pairwise contact-surface non-overlap. Editing `Depth_closed_crimp_right` from 7.5 to 9.5 mm changed the physical body and only closed-crimp-right, closed-crimp-left; restoring the parameter restored every contact bound and left the saved source bytes unchanged. The pinned compiler passed all ten source/archive, geometry, binding, depth, reimport, descriptor and staged-package stages. The final runtime contains 21 nodes and 19,504 triangles with no material/shader prims or material bindings. Hashes, dimensions, native checks, original source mappings and compiler evidence are retained beside this record.

| View | Prior and native CAD |
| --- | --- |
| Front | [Comparison](review/comparison-front.png) |
| Side | [Comparison](review/comparison-side.png) |
| Top | [Comparison](review/comparison-top.png) |

All three final comparisons were visually inspected alongside the retained manufacturer imagery. The exact prior asset comes from commit `d0e4e95191e4a76822815bb4eeef3a32caa6fea0`. Renders use the shared `preview.py` renderer, including its corrected positive-X side and positive-Z top painter order. The CPU previews shade triangle face normals while runtime exports retain native CAD surface normals. Native-app appearance, selection and performance acceptance remain root integration work.
