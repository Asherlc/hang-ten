# Metolius Simulator 3-D: jagged appearance correction

Scope: only the Simulator native outline and shoulder transitions. Prior source, model and descriptor are frozen from commit `ca5024c3b62f5ecc87e669e1ecab398e650b3890`; hashes are recorded in `frozen-reference.json`.

## Approved primary evidence

- Complete manufacturer photograph: https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Simulator-black-white.jpg?v=1759460469 — retained `docs/source-audits/2026-09-29-remaining-cad/metolius-simulator-3d/sources/product-01.jpg`, SHA-256 `5ac1677d6280dc90242cb1dcef47691647fd3f5a9adc3c465838e930075f58a9`.
- Complete manufacturer numbered depth diagram: https://cdn.shopify.com/s/files/1/0955/0030/4457/files/sim-num-dep_c543622d-e670-4601-8d4d-792cc8e46dea.jpg?v=1762201085 — retained `sources/product-03.jpg` in the same audit directory, SHA-256 `e9561ab3fb6d3a85014097dcbdb0bc3d9c4079f9cb0954bd87965d180329932a`.
- Original manufacturer product page and source audit remain the basis for the published 711 × 222 mm face dimensions, grip inventory and depths.

Both complete images were visually inspected without pixel measurement, tracing, registration, cropping, segmentation or vectorization. The photograph supports a rounded resin outline and continuous shoulder form. It does not establish exact rounding radii, Bezier poles, transition widths or overall thickness.

## Direct native authoring

`authored-design.json` records every revised silhouette control pole and all twelve exact native section stations. The chosen poles, 30 / 36 / 40 mm transition widths and 2 mm end guard spacings are display estimates. The native section profiles come from exact intersections of the existing analytic CAD shell, not a source image or reference mesh. The profiles have consistent rear / roof / floor edges and form local solid lofts; each transition must be a nonempty valid single solid before assembly. The mirrored half uses exact native mirroring. All 140 native sketches are fully constrained.

`BodySolid` retains the original cavity cutters. Two symmetric pocket-4 cutter floors were translated approximately −2.69416 mm to retain their original published depth after the shoulder surface correction; no depth fact changed. Surface contacts were rebuilt from final native faces, original semantic partitions and the published Y = −55 / −65 mm support boundaries. All 30 identifiers and the exact embedded manifest remain unchanged, including separate left/right flat slopers and the shared round-sloper center contact covering both shoulders.

## Dimensions and continuity

The published 711 × 222 mm face dimensions remain exact within native kernel tolerance. Authored overall thickness remains approximately 94 mm, with a measured native optimal bound of 94.1183246 mm. The 0.1183 mm increase is an explicitly audited display estimate, not a manufacturer specification. All 24 cavity and 3 sloper depth checks pass.

All three silhouette sketches have closed G1 joins. The three former roof boundaries at X = ±47, ±148 and ±258 mm no longer have finite height steps. The local roof bridges are positionally continuous, with residual endpoint normal changes up to approximately 6.77° near a sloper lip. Do not describe the complete roof as G1. Independent shrinking-epsilon and interior-Y probes separate grazing support-boundary rays from real positional discontinuities. Final shell mirror distance is below 0.000001 mm.

## Validation and presentation

`root-cause.md` and raw diagnostic logs explain the original geometry defects and CPU preview contribution. The standard 0.28 mm tessellation deflection and analytic surface normals remain unchanged. USDZ material policy and runtime renderer are unchanged. The exact frozen model and final export are compared using identical front, side, top, oblique and raking cameras. CPU previews use triangle-face shading and can exaggerate faceting; fresh actual-app loading, selection and orbit review remains the final appearance/performance check.

Independent native, contact, edit/restore and continuity results live in `../independent-validation/`. Compiler check and published scratch export reports establish byte reproducibility. Human approval for board #8 is not implied by technical validation.
