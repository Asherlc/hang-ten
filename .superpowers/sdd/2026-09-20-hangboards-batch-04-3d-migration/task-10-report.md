# Task 10 — Metolius Rock Rings reusable 3D

Base: `fb1a048961a61e83dc200513c3bc2d27992cb0d4`.
Implementation and geometry owner: Astra. Combined integration is owned by the
controller's disjoint lower-cost worker. Fresh independent Astra combined
review passed with no findings. The controller released the complete atomic
Task 10 commit and automatic push after that review.

## Package and source contract

The package contains only `board.json`, one `assets/primary.usdz`, and its
hash-bound descriptor-v2 `assets/primary.model.json`. The legacy PNG and all
raster/contactGeometry/derivation geometry are removed. The eight canonical
contact IDs, factual names, kinds, depths, finger counts and equipment ownership
are preserved. One generic four-slot unit is rendered twice, identical and
unreflected, with complete maps to `left-ring` and `right-ring`:

| Slot | Left contact | Right contact |
| --- | --- | --- |
| jug | jug-left | jug-right |
| pocket-40 | pocket-40-four-left | pocket-40-four-right |
| pocket-32 | pocket-32-three-left | pocket-32-three-right |
| pocket-25 | pocket-25-two-left | pocket-25-two-right |

The approved manufacturer black/white image and retained owner front/rear and
lateral originals were inspected before authoring. Source URLs/hashes and
approval remain in the closed Batch 04 source register. Three regular-file
copies promote the same bytes into the canonical cord snapshot directory.
The canonical cord audit now records:
`two independent pairedLeadCord systems; no inter-unit connection or central through-bore.`
The retained delivered GLB remains audited source material only; no delivered
geometry or image pixels enter the manually authored final model.

The manufacturer envelope is 146 mm across X, 184 mm high and 57 mm deep;
nominal pocket depths are 40/32/25 mm. Analytic perimeter, rounding, mouth
dimensions, rear and jug cross-section, shallow aperture clipping, resin color,
cord and camera values are `authored-display-estimate`. Exact polymer chemistry
is not asserted and source swirl textures are not used.

## Geometry acceptance

The imported asset has seven mesh nodes: one `ring_body_001`, four
`unit_jug_001` / `unit_pocket_40_001` / `unit_pocket_32_001` /
`unit_pocket_25_001` contact-slot nodes, and two attachment nodes
`roof_exit_001` / `lateral_window_001`. Each attachment node includes its two
physical mouths. The side mouths are non-route geometry only. No mounting/screw
holes, fasteners, cleats, brackets, cords, anchors or hardware are baked in.

Actual imported triangle checks: 8,742 triangles; one welded connected component;
Euler characteristic 2; all 13,113 undirected edges incident to exactly two
faces; positive signed volume; zero degenerate triangles, opposing normals or
image textures. Ray checks strike the solid 40 mm pocket floor and intact rear,
both clipped roof mouths and both clipped side windows. No central through-bore
exists. Two tiny symmetric roof-mouth intersection triangles use deliberately
authored face normals across their roof/wall tangent discontinuity.

Source-unit and assembled-pair captures cover front, reverse, roof, lateral and
oblique views. All four unit slots and all eight independent instance contact
highlights were rendered. Thirteen additional views show the actual production
solver's four cord spans, including each highlighted contact. The top jug is
usable, pocket order and depth appearance match the approved evidence, rear
surfaces stay solid, and pair spacing/roof entry alignment remain clear.
Subtle facet shading around the side-window and jug tangent transitions is
visible in close studio lighting; there are no reversed normals or open seams.
Current-source iOS visual acceptance remains Task 14, with the current task's
native integration regression recorded by the integration worker.

## Suspension and placement ruling

Both instances have identity bases and the sole `primary` suspension pose with
translations X = ±0.105 m, identity rotation. Each owns unique lead IDs and an
independent world-space invisible anchor at X = ±0.105 m, Y = 0.282 m, Z = 0.
Local roof endpoints are (±0.062, 0.091, 0) in descriptor/importer coordinates.
Every lead has 0.202 m available rest length and 2 mm radius. The production
taut renderer displays about 0.20081086 m per lead; it does not display unused
slack. No hidden route, side-window routing or inter-unit connection is claimed.

The controller approved pose-owned placement after verifying the runtime:
`solveInstance` preserves authored paired-lead world anchors; the package parser
validates suspension poses without instance-base context. Base placement would
misvalidate the correct short cord against an unplaced endpoint. Canonical-pose
placement uses the existing supported transform path and avoids an unrelated
runtime change. The integration worker owns a native regression for selected
primary separation, camera union and visibility before scene presentation.

Both real Rock Rings instances pass the exact production solver, mesh/tube
clearance gate, visible hanging-span, endpoint, sampled-length and disjoint
horizontal-interval checks. The unchanged global clearance suite passes all
27 existing poses.

## Verification

- Strict RED: four Rock Rings tests failed for the legacy raster presentation
  and missing canonical audit before production changes (`red-rock-rings.log`).
- Focused Rock Rings package/source tests: 4 passed.
- Final inventory and package status: pass, no drafts.
- Retained descriptor/compiler/importer/YY model-tool lane: 21 passed in host
  context. Managed sandbox Blender crashed before Python; its one failing
  `test_constant_principled_pbr_survives_blender_usdz_round_trip` passed unchanged
  in the working host context with Task 10-owned config/cache/temp paths.
- Exact Rock Rings production clearance: 2 instances passed; global existing
  production clearance: 27 poses passed.
- First broader package lane: 120 passed, two cord-audit discovery failures
  (`test_current_four_documented_suspension_packages_use_compact_visual_cords`,
  `test_production_manifest_excludes_new_model_only_packages_without_suspension`).
  Both exposed the audit's missing per-instance topology discovery. The disjoint
  integration worker owns that focused fix and its RED/GREEN tests.
- Final combined focused package/orientation/cord lanes: 126 passed.
- Global cord audit: pass, 36 exact model records (25 excluded, 11 represented).
- Native selected-primary separation/camera-union regression: 1 passed on
  iPhone 17 Pro iOS 26.5, as recorded in `task-10-integration-report.md`.
  Four pre-existing Xcode warnings were emitted; no infrastructure limitation.
- Safe ODR staging: 4 passed; PBX: 397 definitions, 397 unique IDs, lint passed.
- Full package suite: 666 passed in 123.31 seconds.
- Python compileall and `git diff --check`: pass.

## Assets, evidence and cleanup

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| primary.usdz | 396,093 | `4af718e4c5f1177dce1e440372af6975c0da0c3263e8cc3ea275b9173e956218` |
| primary.model.json | 2,269 | `6ba1c181b107cbdba6284651a2f2e4219158a6c2bbb6417ea8e4e4faa938727d` |

Retained task evidence and authoring/verification scripts:
`.context/learned-giraffe-task10-evidence`.
Temporary authoring/config/cache/export path:
`.context/learned-giraffe-task10-work`.
No HTTP server, tunnel, Simulator or external resource was started by the
geometry owner. Final exact-path EXIT/INT/TERM trap cleanup removed the 2.8 MB
temporary directory, including Blender source/config/cache/tmp, disposable
exports, diagnostic generated Swift and retired PNG backup. A separate absence
check passed. The 35 final captures and concise review evidence remain under
the controller's approved lifecycle. The removed raster remains recoverable
from git.

The integration worker also removed and verified absence of its two exact
Task 10-owned native test artifacts, leaving shared DerivedData and Simulator
resources untouched. Final asset hashes and `git diff --check` were rechecked
after review and remain unchanged/clean. No staging, commit or push preceded
the controller's independent-review release.
