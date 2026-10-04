# Simulator 3-D jagged appearance: frozen reproduction

The before package is frozen from commit `ca5024c3b62f5ecc87e669e1ecab398e650b3890`; exact source/model/descriptor hashes are in `frozen-reference.json`. Manufacturer evidence remains the approved complete `product-01.jpg` photograph and `product-03.jpg` numbered depth diagram in the original source audit. Both were viewed in full. No pixels were measured, traced, segmented, aligned, vectorized or cropped.

## Native geometry is the primary cause

The native source reopens as a valid solid, but validity does not guarantee a smoothly joined exterior. Exact curve-tangent measurements in `diagnosis-native.json` show a 72.97° direction discontinuity at the center-jug shoulder, 33.74° at the outermost corner and 43.92° at the lower corner, mirrored left/right. Separate roof solids stop at X = ±47, ±148 and ±258 mm and leave actual vertical step faces. Two roof sections separated by only 0.02 mm in X differ by 17.05 mm in height at X = 47 / Y = −65 and 18.23 mm at X = 258 / Y = −65; the round/flat seam differs by up to 3.74 mm in the sampled stations. These are geometric edges and steps, not tessellation error. The existing actual-app capture shows the same angular outline and strip seams.

The minimal reproduction only opens and recomputes the frozen source, reads its original silhouette tangents, intersects exact native vertical lines around the roof boundaries, and renders the frozen USDZ. It does not alter source bytes.

## Export and preview contributions

The document already enables analytic surface normals at its existing 0.28 mm tessellation deflection. `diagnosis-export-normals.json` reads the frozen USDZ and confirms varying vertex normals on 30,229 of 34,634 triangles. Missing smooth normals are therefore not the general cause. The shared CPU preview uses one triangle-face normal per polygon and ignores the shipped analytic vertex normals, so it exaggerates faceting. Front/side/top/oblique CPU images remain useful for shape comparisons, but actual app rendering is required for the final appearance judgment. The renderer, material policy and standard tessellation setting remain unchanged. The final export uses a narrowly scoped, source-opted native UV normal acceleration with the prior inverse evaluator retained for uncertain cases.

## Targeted correction

Deliberately adjust only the silhouette Bezier control poles needed to make adjacent native tangents agree while retaining the original extrema. Replace the three abrupt shoulder boundary bands with native loft transitions, using exact analytic sections of the existing CAD and short end-guard sections. This is a local correction of the established native shoulder forms; the cavity inventory, opening construction and published depth parameters are retained. No reference mesh or source-image geometry is generated or inferred.

All selected transition widths, guard spacings and silhouette rounding poles are display estimates. They are not manufacturer measurements. Preserve the original raw embedded manifest, 30 IDs, 24 cavity depth facts, 55 mm flat and 65 mm round support depths, and the published 711 × 222 mm face envelope. The authored display thickness remains approximately 94 mm; the final exact native optimal bound is 94.1183246 mm, an audited 0.1183 mm estimate change accepted for this correction. It is not a manufacturer measurement.

## Native verification and limits

The frozen candidate source is `40e42ed072a72946d11756cd6f92047fd0d5acd79eb33946cb2188441babbbde`. Independent native checks preserve all 30 IDs and the exact raw embedded manifest, all 27 published cavity/sloper depth checks, disjoint final-shell contacts, and a 14 → 16 → 14 mm depth edit with the intended contact changing and all contacts restoring. All three silhouette sketches have closed G1 joins; mirrored shell deviation is below 0.000001 mm. The original finite shoulder steps are removed. Roof bridges are positionally continuous, with residual directional creases at some endpoints: the largest measured interior normal difference is approximately 6.77° near a sloper lip. No full G1 roof claim is made. Exact Y = −55 and −65 mm samples touch semantic support-depth boundaries; shrinking-epsilon and nearby interior probes distinguish grazing tangent-ray behavior from a finite step. See the retained independent continuity reports.

The standard 0.28 mm tessellation setting and analytic surface normals are unchanged. Increased final mesh complexity must be evaluated through actual app loading and orbit review.

## Compiler performance diagnosis and rejected representation probes

The six roof faces use degree 8 × 3 B-spline surfaces with 245–486 poles in U and 4 poles in V. They dominate the approximately 254,650-triangle native mesh. A retained process sample and `face-cost.json` identify inverse UV searches (`Surface.parameter`) as the long-running analytic-normal operation. Original check/export jobs were stopped under parent coordination; exact process timing and cleanup are retained in `superseded-compile-timing.json` and `superseded-compile-cleanup.json`. Those interrupted runs are not successful compiler proofs.

Local curve compaction was tested at a maximum authorized display tolerance of 0.02 mm. A parameter-preserving degree-5 approximation had sampled equal-parameter and bidirectional polyline deviations below 0.0041 mm, but its native final assembly failed. Independently lofting exact section sectors also failed equivalence and the single-solid requirement because section correspondence changed. All such probes are rejected and remain diagnostic scratch; they did not modify the frozen 40e42ed0 candidate.

`getUVNodes()` exposes the existing native tessellation UV coordinates. A read-only probe shows that evaluating analytic normals from those coordinates is much faster than inverse parameter searches. Node order differs from `tessellate()`; spatial matching and fallback must be validated before any use. No compiler implementation or policy change has been made by this author.

The selected completion path retains the validated 40e42ed0 native geometry and adds only an opt-in `HangTenUVNodeSurfaceNormals` document flag after the narrow compiler acceleration is ready. The acceleration retains native analytic normals and the 0.28 mm quality setting, and uses the prior evaluator for unmatched or ambiguous triangles. It is enabled only for this package. The scratch benchmark (`uv-normal-benchmark.json`) found unique native UV owners for 251,419 of 254,770 triangles; its 60 heavy-face normal comparisons differed by at most 0.000000854°. This benchmark is feasibility evidence, not the final regression or package result.


The expanded comparison covers 213 corners across 71 real triangles, including spatial extrema and legacy fallback boundaries. It exposed ten normal-side ambiguities on internal degree-8 / multiplicity-8 U knots; equal positions can have distinct one-sided normals there. The compiler worker added a conservative exclusion so every incident triangle retains the original inverse evaluator. The rejected UV prototype and stopped compiler attempts are retained under `superseded-uv-boundary/`; no asset from them is eligible for handoff. The old default-false package already reproduced its exact model and descriptor bytes, as recorded in `baseline-default-false-reproducibility.json`.


## Final handoff evidence

Final source `8fa07c203943d849101ba80926fb6c1d69c2ace7dff982a68f6e8a6476f618f7` preserves all native geometry from the independently checked 40e42ed0 source. Final compiler `f4c0d4c2a9c79c02d349be2f71a14962fde3c5c2fa13b24b0b34d425272fc50d` passes the same 71-triangle / 213-corner comparison, including all ten prior boundary failures: positions exact, maximum normal difference 0.000000854°. The sharp-knot and ambiguous-witness cases retain the legacy evaluator.

Check-only and two independent normal exports pass under the pinned toolchain in approximately 6.3–6.4 minutes each. The two model and descriptor files are byte-identical. The final model has 254,961 triangles, 31 mesh nodes and 30 contacts, and is 5,705,584 bytes. It contains no materials, shaders or bindings. The unchanged baseline also reproduces its exact original model and descriptor under the final compiler with the opt-in disabled. See `reproducibility.json`, `baseline-default-false-reproducibility.json`, the four compiler logs/reports and `final-normal-comparison.json`.

All five exact-asset comparison panels were inspected in full. `visual-review.json` binds them to the exact before/after model hashes and records remaining CPU shading limits. Independent final-source and export checks are in `../independent-validation/`. Actual app appearance, loading/orbits and human acceptance remain with the parent review; this handoff does not approve board #8 or advance the review sequence.
