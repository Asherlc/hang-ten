# Rock Prodigy Training Center approved-package audit

Checked 2026-08-10 and packaged 2026-08-12. This audit migrates the already
reviewed runtime board into the canonical approved-package schema. It does not
add facts, holds, semantic targets, geometry, training instructions, or a
presentation asset.

## Approved sources

Only the four sources already named in
`docs/TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md` are used:

- Product page: <https://trango.com/products/rock-prodigy-training-center>
- Use instructions: <https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155>
- Depth guide: <https://www.mountainexperience.it/risorse/Rock_Prodigy_Training_Center_Depth_Guide.pdf>
- Main product image: <https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750&width=1946>

The imported generated-catalog PNGs and approximate outline remain below
`review/unreviewed-generated-catalog/`. They are not package assets, evidence,
physical metadata, semantic input, or runtime artwork.

## Field mapping

| Canonical field | Preserved value | Evidence |
| --- | --- | --- |
| ID | `trango.rock-prodigy-training-center` | Existing reviewed runtime identity; product page |
| Manufacturer / name / URL | Trango / Rock Prodigy Training Center / product URL | Product page |
| Dimensions | 18.2 × 12.1 inches assembled; two 9.1 × 12.1 inch pieces | Product page |
| Aspect ratio | `18.2 / 12.1` | Reviewed normalization of product-page dimensions |
| Presentation | absent | Preserves existing runtime behavior; no new asset introduced |

## Physical-hold mapping

The package preserves the existing 13 logical contacts per side (26 stable
hold IDs). The product image supports the two-piece silhouette and contact
placement; the depth guide supports the manufacturer sizes and contact types.

| Paired ID suffix | Preserved source fact |
| --- | --- |
| `top-jug` | paired top jugs |
| `large-open-rail` | 20–33 mm variable rail |
| `small-crimp-rail` | 10–24 mm variable rail |
| `three-finger-slot` | 38 mm three-finger slot |
| `thin-crimp` | 7.5 mm thin crimp |
| `deep-mr-pocket` / `shallow-mr-pocket` | 29 mm / 19 mm MR pockets |
| `medium-im-pocket` / `shallow-im-pocket` | 26–36 mm / 19–24 mm IM pockets |
| `wide-pinch` / `medium-pinch` / `small-pinch` | 87 mm / 44 mm / 18 mm contacts on the outer angled block |
| `sloper` | existing logical sloper contact on the outer angled surface |

As documented in the 2026-08-10 audit, the depth guide describes the three
pinch sizes on one physical outer block rather than separate cavities. The
three pinch IDs therefore preserve one shared path per side. The logical
sloper target preserves that same source-limited outer-surface path. This is a
migration of the reviewed runtime behavior, not a new geometry claim.

## Semantic mapping

The use instructions and depth guide support the seven preserved routine
targets: `warmup-jug`, `large-open-hand-rail`, `deep-two-finger-pocket`,
`thin-crimp`, `shallow-three-finger-slot`, `wide-pinch`, and `sloper`. Each
maps to its existing left/right namespaced hold IDs exactly as recorded in the
2026-08-10 training-plan audit and current plan library.

## Artwork mapping

`artwork.json` is a literal expansion of the existing reviewed normalized
Swift design. It preserves the canvas frame, paired-path silhouette, 11 layer
frames/shapes, 26 hold-piece IDs, normalized path commands, and surface/shelf/
deep-recess/shallow-recess treatments. Mirrored runtime geometry is expanded
into explicit right-side frames and path coordinates without changing the
result. The product image supports silhouette and placement; the depth guide
supports the contact identities represented by the hold paths. Artwork is a
reviewed human-authored normalization and does not use the quarantined catalog
outline.
