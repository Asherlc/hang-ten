# Task 9 — Metolius Light Rail 2.0

Base: `06ee7f6b5242386999b92d8674b02c2751e253ee`. Worktree and upstream
were clean and identical before work. Implementation and disjoint integration
remain one atomic Task 9 change; no intermediate integration commit was made.

## Delivered package

`Hangboards/metolius-light-rail-2` contains only `board.json`,
`assets/primary.usdz`, and `assets/primary.model.json`. It is schema v3 with
one original/default `primary` presentation and descriptor v1. Both retired
PNGs and all raster geometry/fallback state are removed. All four factual
contacts, canonical IDs, names, depths and equipment-object ownership remain
unchanged. Positions preserve the exact 40/20 and inverted 40/15 groupings.

| Source patch | Canonical contact | Imported mesh |
| --- | --- | --- |
| `lr-top-jug-40` | `jug-40-20mm-side` | `lr_top_jug_40_001` |
| `lr-recess-lower-20` | `edge-20` | `lr_recess_lower_20_001` |
| `lr-bottom-jug-40` | `jug-40-15mm-side` | `lr_bottom_jug_40_001` |
| `lr-recess-upper-15` | `edge-15` | `lr_recess_upper_15_001` |

Final USDZ: **117,652 bytes**, SHA-256
`e217c2268fe3ef1ff4fb6ecce464223b5958cec3a34afcdd217994b13558dcd5`.
Final descriptor: **2,334 bytes**, SHA-256
`bd2608738ed632b346203a368a8a681abe7346dc9e89602db2f6c7ef37363aa2`.
The descriptor's model hash equals the final USDZ. Its archive has one member,
`primary.usdc`, with zero image textures.

## Source, shape and suspension review

Astra inspected the exact retained manufacturer `Light-Rail-2-PT.jpg`
(`7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272`)
and exact archived Treeline field image
(`93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a`).
The delivered GLB `dbd8c47af8d9b1a7f36fc0f8634e4c6afda484d97988729570b685adf7cbb99e`
was not promoted or used as geometry. Direct analytic authoring created the
457 × 76 × 38 mm reversible rail, rounded perimeter, one continuous channel,
15/20 mm opposing channel lips, and two outer nominal 40 mm jug surfaces.
No pixel reading, tracing, segmentation, registration, crop, detection,
contour/vector generation, or proposal/promote geometry pipeline was used.

The reviewed constant-PBR compiler transported deliberately tagged geometry,
reimported the actual USDZ from an empty scene, and rebuilt the descriptor.
Astra authored final triangle topology before explicit planar normals so the
transport triangulator would not re-normalize large face ngons. This removed
the initial front-face shading seams without a compiler change.

The final imported mesh has 2,492 triangles, 3,738 welded edges (all incidence
2), Euler characteristic 2, positive signed volume, zero degenerate triangles,
and zero normal/winding disagreements. It has exactly one body, four contacts,
and two attachment meshes. Rays from underneath both entry coordinates meet
solid surfaces at source Z = -0.038 m; top rays meet clipped entry surfaces at
Z = 0.035 m. These checks establish zero through-holes/handles and no unsupported
underside mouth. No mounting holes, screws, brackets, cleats or hardware exist.
The 3 mm entry clipping depth is a display estimate, not a physical blind-hole
claim. Unsurveyed radii, channel returns, rear, wood color and other geometric
display values are labeled `authored-display-estimate`.

`pairedLeadCord` binds only source upper markers 1/2, transformed as `(x,z,-y)`:
`[-0.213,0.038,0]` / `[0.213,0.038,0]`. Saved Y is clamped inward by 1 nm to
`0.037999999`, the importer-visible upper bound. Point-only passage records
duplicate these entries; no lower marker, hidden route or lead connection is
present. Inverted rotation `[0,0,1,0]` preserves those same physical entries.
Controller-approved exterior `cordContactPoints` guide the inverted leads
around the outer ends to the original rotated entries; there are no attachment
overrides or new mouths. Their exact bends are explicitly display estimates.

Both leads use estimated rest length 0.431878843 m, radius 2 mm and matte
material. The anchor is 0.24 m above the untransformed upper bound. Upright
translation `[0,-0.133053677,0]` and inverted zero translation reconcile the
fixed lead length with extra exterior routing in inversion. Both complete
routes require about 0.430378843 m, with 1.5 mm slack allowance. Inverted guides
follow the existing 6 mm end-rounding profile at a 3.4 mm centerline offset
(3 mm required clearance), with maximum X = ±0.2319 m. The upright route adds
a 6 mm exterior approach to center the tube in its existing entry. All are
display estimates. The approximately 0.133 m displayed height change is
deliberate and automatically reframed; it is not physical metrology.

Astra accepted final imported front/inverted/reverse/end/oblique views and all
four highlights. Eight additional captures show both production-solved poses
from front/reverse/front-oblique/rear-oblique. Highlights coincide with the
actual selected lips/jugs; inverted geometry has no backside or winding defect.
Cord guides stay outside the mesh and clear both contact families. These are
actual USDZ plus production-solver review renders, not current-source iOS app
screenshots; final native interaction, picking/accessibility and appearance
review remains the approved Task 14 lane.

## Integration and audit

The canonical cord audit adds exactly Light Rail with its two distinct retained
regular-file snapshots, Astra approval, and the exact upper-entry-only ruling.
Closed inventory is now 35 model packages: 10 represented and 25 excluded.
No later Batch 04 package was added. The integration subtask registered the
model inventory and orientation audit, added the dedicated ODR folder/tag
`hang-ten-model-metolius-light-rail-2`, and added the narrow `independent`
evidence tier for truthful Treeline provenance with RED/GREEN unknown-tier
rejection. PBX object IDs remain unique. Presentation-remediation conversion
remains Task 14 under the approved controller ruling.

## Verification

- Initial board/audit RED: three expected failures (two raster presentations,
  raster media, missing Light Rail audit record).
- Inversion RED: missing two canonical positions, before metadata authoring.
- Final focused approved-package/cord-audit/source-tier lane: **78 passed**,
  including the guide-envelope regression added in the fix round.
- Retained descriptor/compiler/importer/Baguette model-tool lane: **21 passed**.
- Final-inventory validation, package status and global closed cord audit: pass.
- Light Rail native production solver/clearance: **both poses pass** against the
  exact final USDZ; original global harness: **all 27 poses pass**.
- Python compileall, PBX plist validation and diff whitespace validation: pass.
- Final full package suite: **659 passed in 139.39 seconds**, including static model
  inventory, orientation, closed audit, staging and safe per-model ODR seams.

The first sandbox Blender authoring attempt and constant-PBR round-trip test
crashed with signal 11 before Python. Equivalent host-context commands passed;
all config/cache/temp outputs for subsequent host runs were confined to the
task-owned work directory. The failed sandbox model-tool lane is retained by
name (`test_constant_principled_pbr_survives_blender_usdz_round_trip`); the final
host run has no remaining failures. A mistaken focused test filename produced
one collection error, then the correct lane passed. Initial native checks
reported out-of-bounds attachments and too-short leads; the final importer
clamp and complete-route length estimates resolve both with two-pose evidence.

## Ownership and cleanup

Retained evidence is `.context/learned-giraffe-task9-evidence`, including direct
authoring script, source/hash mappings, final structure, RED/GREEN/full logs,
final imported-model and solved-cord captures. Exact temporary work is
`.context/learned-giraffe-task9-work`, containing authoring blend, disposable
exports, config/cache/temp and retired rasters. No HTTP server, tunnel, owned
Simulator, app build or other external resource was started. Temporary cleanup
ran after independent review. The exact 1.4 MB work directory was deleted by
the task-owned EXIT/INT/TERM trap, and a separate absence check passed. All
task command sessions completed. This evidence directory is intentionally
retained through later whole-branch review under the controller-approved
lifecycle. Old PNGs are recoverable from git.

## Final checkpoint

Independent re-review: **PASS, no findings**. The prior P2 is resolved; the
controller released the one atomic Task 9 commit and push. Final diff/status,
asset hashes and exact owned-resource cleanup checks pass. No current-source
iOS app screenshots are claimed by this task; Task 14 owns that final lane.

### Review fix round 1

The independent reviewer requested a P2 visual correction: the initial
inverted route had rigid 88 mm vertical sections 16.5 mm beyond the rail ends.
Those floating hooks passed minimum clearance but did not read as flexible
cord following the existing silhouette. A new guide-envelope regression was
observed RED at 16.5 mm before metadata changes, then GREEN with rounded
guides only 3.4 mm beyond the surface. Both native Light Rail poses pass after
the guide change. Shared rest length and upright translation were recalculated
from the shorter route; the original 0.477 m/-0.184 m values are superseded.
Model and descriptor bytes are unchanged. All eight solved-cord captures were
regenerated and Astra-reviewed. Both native poses, all 27 global native poses,
78 focused tests, 659 full package tests, final-inventory validation, the
closed cord audit and diff whitespace checks pass. The same reviewer returned
PASS with no findings, and the progress-ledger fix-round entry is closed.
