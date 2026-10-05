# Metolius Simulator 3-D — Opus geometry corrections

This scratch candidate corrects the two source-supported shape regressions identified in `../metolius-simulator-3d-plastic-review/opus-first-review.md`. It is not human acceptance of board #8.

## Retained approved manufacturer evidence

The complete manufacturer photo `product-01.jpg` and complete numbered diagram `product-03.jpg` under `docs/source-audits/2026-09-29-remaining-cad/metolius-simulator-3d/sources/` were reviewed by eye. No pixels were measured, traced, cropped, aligned, segmented or vectorized.

- Photo: https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Simulator-black-white.jpg?v=1759460469 — SHA-256 `5ac1677d6280dc90242cb1dcef47691647fd3f5a9adc3c465838e930075f58a9`.
- Numbered diagram: https://cdn.shopify.com/s/files/1/0955/0030/4457/files/sim-num-dep_c543622d-e670-4601-8d4d-792cc8e46dea.jpg?v=1762201085 — SHA-256 `e9561ab3fb6d3a85014097dcbdb0bc3d9c4079f9cb0954bd87965d180329932a`.

Both sources support the rounded, full-width center jug dome, the continuous upper roof and the molded outer saddles. Published face dimensions and hold depths remain the existing manufacturer facts. Hardware remains omitted from this display model.

## Diagnosed regressions and native correction

The rejected 8fa dome silhouette changed the first cubic Bezier from the original control points `(0,222), (24,222), (42,211), (47,188)` to a narrow tent; its bridge influence began at X = 35 mm, climbing the sides. The corrected source restores the original cubic in all three silhouette sketches and its exact mirror. Center bridge influence is limited to |X| = 46.5–61 mm above Z = 145 mm, with section stations 46.5, 46.9, 59.5 and 61 mm. This retains the original dome core and confines the estimated concave transition to the base.

The rejected round/flat section builder classified only the first rear-wall edge as the rear line. On the round side the straight rear wall was split at Z = 145 mm. The resulting loft therefore paired a spurious Z = 145 mm roof start with the true flat-side roof top, producing the unsupported back-edge V notch. The correction merges the entire straight rear-wall run, including native straight B-splines whose poles lie on the rear plane. Roof, rear and floor correspond consistently across all sections. The round/flat blend spans |X| = 110–185 mm above Z = 135 mm, with stations 110, 112, 183 and 185 mm. Its support depths remain 65 mm round and 55 mm flat.

All blend widths, control points, floor planes and overall thickness are operator-selected display estimates, not measured manufacturer dimensions. Native sections come from the existing analytic CAD shell. The outer saddle construction at |X| = 238–278 mm and the rounded lower/outer silhouette are retained. No whole-roof G1 claim is made.

## Frozen inputs and metadata

`freeze.json` records the exact original 9449 source/assets, rejected 8fa source/assets and plastic-tagged 3c source/assets. The final candidate starts from the plastic-tagged source. Its raw `HangTenBoardManifest` is byte-exact, preserving all 30 IDs/facts including `surfaceFinish: plastic`. The UV-node normals opt-in and analytic normals remain enabled, at the unchanged 0.28 mm tessellation setting. No renderer, compiler, material policy or other package is changed by this author.

`probe-design.json` records deliberate native section stations and rear-wall topology. `authored-design.json` records the frozen contact-complete source and zero additional cavity floor corrections. `source-freeze.json` binds the exact candidate hash. Fresh native bounds measure approximately 711 × 94.030457 × 222 mm: 711 × 222 mm are published dimensions; about 94 mm thickness is a display estimate (previous rejected geometry measured 94.118325 mm).

## Visual gate and verification

The five whole-image three-column views in `review/` compare the original committed 9449 asset, rejected 8fa asset, and corrected native body. Root and Opus approved this native shape gate before full export. The retained review is `../metolius-simulator-3d-plastic-review/opus-native-review.md`. Faint dashed roof shading and small dark specks remain cosmetic watch items for exact export and actual colored app review; no claim is made that CPU triangle-face previews establish runtime shading quality.

The contact rebuild only sets native OCCT checked flags and reserializes body floating-point values by at most 1.12e-16; no cavity floor change was needed. Native preview provenance records that distinction rather than claiming byte-identical BReps. `final-normal-comparison.json` checks 186 actual triangle corners (heavy-face interior and boundary, plus legacy fallbacks) against the original analytic normal path, with exact positions and maximum angular difference 0.0000298 degrees.

Final independent source/edit checks, export reproducibility, exact exported previews and actual app review remain separately reported. Human approval remains pending.
