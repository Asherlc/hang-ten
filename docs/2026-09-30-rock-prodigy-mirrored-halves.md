# Rock Prodigy single-half model representation

Forge, Natural, and Training Center now store one canonical left half and declare
separate left/right equipment instances. The right instance reflects X through
the corrected renderer path, which reflects normals and reverses winding in an
independent runtime mesh resource. Each instance declares an identity transform for the existing implicit `primary`
position. Selecting or clearing that position preserves the base placement.
Instance translations retain the schema's required nine-decimal precision.
The paired display retains the previous gap,
orientation, camera, and presentation aspect ratio.

This is a representation change to the approved existing geometry. No new hold
shape, depth, dimension, grip cue, or routine content is introduced. Every physical
contact ID and its factual fields is preserved; only equipment ownership changes
from `primary` to `left-half` / `right-half`. Each descriptor slot is the prior
left contact ID without the `-left` suffix. Both instances bind each slot to its
respective unchanged physical contact ID.

Manufacturer references reviewed September 30, 2026:

- [Forge](https://trango.com/products/rock-prodigy-forge): split product identity,
  per-side dimensions, and matching bilateral hold arrangement in product images.
- [Natural](https://trango.com/products/rock-prodigy-natural): split product
  identity and mirrored arrangement. The retained geometry and measurements are
  documented in [Natural CAD provenance](2026-09-29-trango-rock-prodigy-natural-cad-provenance.md).
- [Training Center](https://trango.com/products/rock-prodigy-training-center):
  split product identity and bilateral hold arrangement. Its existing native
  source already generated its right half using `Part::Mirroring`.

Natural's right CAD feature branch and Training Center's right mirror/contacts
are removed. Their body compounds now contain only the existing left solid;
left feature history, native authored hold outlines, and contact regions remain.
Their sources use reusable descriptor version 2 and `ContactSlotID` bindings.
The manifest changes are embedded with `set_board_manifest.py`; no `board.json`
is committed for either CAD package.

Forge has no native CAD source. Its existing USD layer is reduced by removing
only the right branches. Every left mesh retains its vertices, triangles, normals,
and transforms. The reusable descriptor carries the retained authored outlines
through the single-half normalization. Body-surface pinch nodes remain body nodes.
All three USDZ assets remain unbound and contain no materials or textures.

The canonical half retains its original negative-X coordinates. With its
bounds center `cx`, the left translation is zero and the right translation is
`-2*cx`; reflection about the descriptor center therefore reconstructs `x -> -x`
in the paired board space. This preserves the previous physical gap without
shifting any authored CAD sketch or hold outline.

Workspace-owned validation artifacts live under `.context/mirrored-trango`:
front/side/top prior/canonical/runtime-pair comparisons, independent left/right
app selection screenshots, CAD compiler reports, package checks, and iOS tests.

Validation completed: full catalog validation, Android staging, 468 Python tests
(with 24 subtests), and 35 iOS board-model tests. All 58 physical hold IDs remain
selectable through distinct left/right entities. The five reflected boards are
covered by lighting-normal regressions. The retained Forge mesh has 60 small
pre-existing triangle/normal disagreements; its mirrored half has exactly the
same count and triangle inventory. The other four models have zero disagreements.
The conversion does not repair those original thin-facet normals.

The final iOS app screenshots were reviewed with left and right holds selected
independently on each board. Both complete front surfaces render correctly.
The workspace-owned simulator and DerivedData were deleted and deletion verified.

Independent pinned-toolchain rebuilds reproduced both CAD assets and their entire
descriptors exactly: Natural `8177ca86217b281e62a72ee2d27a5312b6f447b91974d4e1b08d08fd236539c9`
and Training Center `7b1988e9fd280a26c4c8d086355f36d1e825e045a2f3265632760ca9f5f2c92e`.
Every retained Forge node's decoded points, triangles, normals, and transforms
matches its prior committed asset exactly. The retained native shapes' areas,
volumes, and bounds also match (Natural exactly; Training Center maximum native
numeric difference `1.46e-11`).

Merge review also verified map and workout frames for reusable halves. Physical
contact frames now include the owning instance's reflection and nominal placement
before normalization across the pair. The regression first reproduced overlapping
left/right frames and failed bilateral selection, then passed for all three boards.
The reusable Training Center verifier now rebuilds and compares the full descriptor
from native authored bindings/outlines and exported USDZ points; mutations to model
bounds or slot frames are rejected. Final checks passed 100 selected iOS tests and
469 Python tests with 26 subtests. The review simulator and DerivedData were deleted
and deletion verified.
