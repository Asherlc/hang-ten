# Simulator 3-D jagged appearance: frozen reproduction

The before package is frozen from commit `ca5024c3b62f5ecc87e669e1ecab398e650b3890`; exact source/model/descriptor hashes are in `frozen-reference.json`. Manufacturer evidence remains the approved complete `product-01.jpg` photograph and `product-03.jpg` numbered depth diagram in the original source audit. Both were viewed in full. No pixels were measured, traced, segmented, aligned, vectorized or cropped.

## Native geometry is the primary cause

The native source reopens as a valid solid, but validity does not guarantee a smoothly joined exterior. Exact curve-tangent measurements in `diagnosis-native.json` show a 72.97° direction discontinuity at the center-jug shoulder, 33.74° at the outermost corner and 43.92° at the lower corner, mirrored left/right. Separate roof solids stop at X = ±47, ±148 and ±258 mm and leave actual vertical step faces. Two roof sections separated by only 0.02 mm in X differ by 17.05 mm in height at X = 47 / Y = −65 and 18.23 mm at X = 258 / Y = −65; the round/flat seam differs by up to 3.74 mm in the sampled stations. These are geometric edges and steps, not tessellation error. The existing actual-app capture shows the same angular outline and strip seams.

The minimal reproduction only opens and recomputes the frozen source, reads its original silhouette tangents, intersects exact native vertical lines around the roof boundaries, and renders the frozen USDZ. It does not alter source bytes.

## Export and preview contributions

The document already enables analytic surface normals at its existing 0.28 mm tessellation deflection. `diagnosis-export-normals.json` reads the frozen USDZ and confirms varying vertex normals on 30,229 of 34,634 triangles. Missing smooth normals are therefore not the general cause. The shared CPU preview uses one triangle-face normal per polygon and ignores the shipped analytic vertex normals, so it exaggerates faceting. Front/side/top/oblique CPU images remain useful for shape comparisons, but actual app rendering is required for the final appearance judgment. The exporter, renderer, material policy and standard tessellation setting remain unchanged.

## Targeted correction

Deliberately adjust only the silhouette Bezier control poles needed to make adjacent native tangents agree while retaining the original extrema. Replace the three abrupt shoulder boundary bands with native loft transitions, using exact analytic sections of the existing CAD and short end-guard sections. This is a local correction of the established native shoulder forms; the cavity inventory, opening construction and published depth parameters are retained. No reference mesh or source-image geometry is generated or inferred.

All selected transition widths, guard spacings and silhouette rounding poles are display estimates. They are not manufacturer measurements. Preserve the original raw embedded manifest, 30 IDs, 24 cavity depth facts, 55 mm flat and 65 mm round support depths, and the published 711 × 222 mm face envelope. The authored display thickness remains approximately 94 mm; the final exact native optimal bound is 94.1183246 mm, an audited 0.1183 mm estimate change accepted for this correction. It is not a manufacturer measurement.

## Native verification and limits

The frozen candidate source is `40e42ed072a72946d11756cd6f92047fd0d5acd79eb33946cb2188441babbbde`. Independent native checks preserve all 30 IDs and the exact raw embedded manifest, all 27 published cavity/sloper depth checks, disjoint final-shell contacts, and a 14 → 16 → 14 mm depth edit with the intended contact changing and all contacts restoring. All three silhouette sketches have closed G1 joins; mirrored shell deviation is below 0.000001 mm. The original finite shoulder steps are removed. Roof bridges are positionally continuous, with residual directional creases at some endpoints: the largest measured interior normal difference is approximately 6.77° near a sloper lip. No full G1 roof claim is made. Exact Y = −55 and −65 mm samples touch semantic support-depth boundaries; shrinking-epsilon and nearby interior probes distinguish grazing tangent-ray behavior from a finite step. See the retained independent continuity reports.

The standard 0.28 mm tessellation setting and analytic surface normals are unchanged. Increased final mesh complexity must be evaluated through actual app loading and orbit review.
