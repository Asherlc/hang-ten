# trango-rock-prodigy-pivot CAD authoring provenance

Date: 2026-09-25

`Hangboards/trango-rock-prodigy-pivot/trango-rock-prodigy-pivot.FCStd` models
one canonical (left) resin half. The right half is still the `reflection: "x"`
instance in the board manifest. The source was authored by a throwaway script
under `.context/`, which was not committed (see
`docs/freecad-authoring-migration.md`). The committed FCStd stands alone. Its
embedded `HangTenBoardManifest` is the previously hand-authored `board.json`
with one change: the eight instance position translations went from
`±0.102000000` to `±0.132500000` (see [Manifest change](#manifest-change)).

This is **not** a trace of the pre-migration display mesh. That mesh (reference
SHA-256 `1549ef47…`, the committed asset at `7e747c60d`) was a manual
reinterpretation. It is about 20 % too small (188 × 96 mm front against the
≈ 234 × 136 mm measured below) and it differs from Trango's product in
topology: five round scallops instead of two sawtooth teeth, a ridge instead of
a slab wing, and a short 13 mm rail. Its rail and three-finger pocket depth
gradients also run opposite to the depth guide. The front view was therefore
re-authored from manufacturer evidence, and depths come from the manufacturer
depth guide. The old mesh was used only as the comparison baseline.

## Sources

| ID | Source | Use |
| --- | --- | --- |
| G | Trango main image, grey, top-down: <https://trango.com/cdn/shop/products/22840-501_RockProdigyPivotGrey_MainImage.jpg?v=1755037446&width=1946> (retained copy `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840-501_RockProdigyPivotGrey_MainImage.jpg`, SHA-256 `339f743c…`) | Every front-view (X, Z) point, read by eye |
| D | Rock Prodigy Pivot Depth Guide PDF: <https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905> (retrieved 2026-09-25, SHA-256 `29e9c36e…`) | All hold depths; hold identity (items 1–7) |
| Q | Rock Prodigy Pivot Quick Start Guide PDF: <https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507> (retrieved 2026-09-25, SHA-256 `a2bbf721…`) | Page 3 CAD render and pp. 6–15 photos: 3D topology only. Page 3 hardware list: 7/32 in hex, which fits a 3/8 in flat-head bolt |
| P | Trango product photos AltImage2/3/4 (retained copies, SHA-256 `26cf8d59…`, `7aa2556d…`, `e05deb5c…`) | 3D topology only (wing slab, cove, raised rim, bevel) |
| R | Retail listings: GearX <https://www.gearx.com/products/trango-rock-prodigypivot-hm47z-grey> "15.5 x 5 x 2.5in"; Out&Back <https://outandbackoutdoor.com/products/trango-rock-prodigy-pivot-climbing-hold> "25.5 x 5 x 2.5 in." (secondary) | Overall depth 2.5 in. The width figures conflict with each other and are not used |

The product page (<https://trango.com/products/rock-prodigy-pivot>, fetched
2026-09-25) states no dimensions.

## Scale and frame

G is Trango's top-down product shot. Its bolt through-hole and countersink
both image as circles (to within about 1 %), so the view is treated as
orthographic. The scale comes from the bolt seat. Q lists a 7/32 in hex key,
which fits a 3/8 in flat-head cap screw, so the seat is a ≈ 10.3 mm clearance
bore with a ≈ 20.6 mm countersink. G shows a 39.3 px bore and a 78.8 px
countersink; their ratio of 2.0 matches that hardware. The resulting scale is
**3.82 px/mm**, and the half measures **234.3 × 136.1 mm**.

Cross-checks:

- The retail "5 in" height is 127 mm, 7 % below the photo value.
- The quick-start mounted photo (Q p. 5) gives ≈ 245 mm from the bolt head,
  which includes perspective from the protruding wing.
- The same photo's 18 in rail cleats give ≈ 285 mm, but the cleat ends are not
  fully visible.

These are recorded conflicts. The bolt-seat scale was kept because it lies in
the plane of the part.

Points were authored in the photo frame (origin at the countersink centre),
then shifted by (+3.35, +13.55) mm so that the half's front-view bounds are
centred on the native origin. That centre is the rotation pivot the manifest
positions use (`modelBoundsCenter`).

## How the front view was authored

The image was cropped into 1 mm-gridded, contrast-stretched tiles. Points were
read by eye and typed in, with no detection, segmentation, contouring or
registration of any kind. Cubic Béziers and lines were then least-squares
fitted to those hand-typed points, with G1 tangents at smooth joints and
one-sided tangents at kinks. The worst deviation from an authored point is
0.80 mm. Every curve in the FCStd is a blocked Sketcher line, arc or cubic
B-spline (Bézier).

## Depths

The back plane and the rim face are 35.5 mm apart. This spacing is retained
from the approved pre-migration asset; no thickness is published.

| Feature | Value | Source |
| --- | --- | --- |
| Upper sloped crimp (D1) | band 12.5 mm deep, from the rim-face edge back to the silhouette. Region depth gate: 12.50 mm exactly | D |
| Outer sloped crimp (D2) | band 11.5 mm deep. Gate: 11.50 mm exactly | D |
| Variable-depth rail (D3) | floor 16 mm below the rim face at the left end, 31 mm at the right, planar between | D (top photo, read L→R as printed) |
| Medium crimp (D4) | lower rim edge stands 9 mm (left end of the field) to 10 mm (end-stop tab) above the field. The field floor is the plane that produces this | D |
| Large crimp (D5) | Γ ledge 12 mm (left) to 11 mm (right) proud of the field, so it stands up to 2.65 mm proud of the rim face at its left end | D (bottom photo is the half rotated 180°, so L→R is reversed) |
| Two-finger pocket (D6) | the pocket's inclined top wall ends on a vertical plane 28 mm (left) to 32 mm (right) behind the rim face. The through opening continues to the back | D (reversed as for D5) |
| Three-finger pocket (D7) | floor 17 mm (left, at the wing wall) to 28 mm (right, at the end window) below the rim face | D (reversed as for D5) |
| Overall depth 63.5 mm | the wing's outer lip is 28 mm proud of the rim face. The crease is 1.5 mm lower (a display estimate) | R (2.5 in) |

The pre-migration mesh ran the rail and three-finger pocket gradients the other
way round. D is explicit ("16mm - 31mm (L - R)" on the unrotated photo), and
the D7 reversal is physically consistent: the pocket is deepest beside its
through end window. The depth guide was followed in both cases.

## Front-view geometry (authored)

- **Silhouette**: 153 points (table below), fitted to 24 lines and Béziers. It
  has two sawtooth teeth and a notch along the bottom and a rim bulge around
  the rail's right end.
- **Wing** (`outer-wedge-pinch`): a smooth loft through 12 sections at
  X = −124 … −18. The crest (crease) and base lines are authored from G:
  crest (−115, −19.5) … (−18, 22.5), base (−100, −36.2) … (−18, −12.0). The
  front face is nearly planar (G, P and Q p. 3 all show a flat slope), with a
  mild concavity toward the base: a Bézier with control points at 35 % along
  the crease-to-base chord and at (0.20 h, 0.25) from the base, a display
  estimate. The loft is trimmed to the silhouette and ends on
  the field's left wall at X = −20.
- **Field**: the left wall is X = −20. The bottom edge (the medium-crimp band
  edge) is Z = −17.6 from X −20 to 64.8. There the band ends in a pointed
  end-stop caret: it rises vertically to Z = −9 at X 64.8–65.8, slopes down to
  (75, −18.2), and drops vertically into the rail. Right of X 75 the field runs
  down to the rail (to Z = −31, just into the slot). A J lip of the rim wraps
  the rail's right end: X 92.5–100, top Z = −24.5, with a rounded free end
  (R 2.9). The right wall is X = 100. The top follows the two-finger opening,
  up to Z = 37.6. The caret, field-to-rail run and J lip were corrected on
  2026-09-26 from an operator photo of the same corner, then re-read on G.
- **Three-finger pocket**: X −20 … 41, bottom Z = 16.5. Its top lip is
  scalloped, with highs at X −6/11/28 (Z 37.0) and dividers at X −14.5/2.5/19.5
  (Z 34.5–35.0).
- **End window** (attachment): a through opening, X 29–40.8, Z 15.3–31, corner
  radius 4.
- **Two-finger pocket**: the front opening is F2 = (54.2, 16.8)–(54.2, 37.6)–
  (86.7, 33.8)–(86.7, 14.6). The through opening is B2, with top corners at
  32.4 and 29.3; the dark top wall in G is inclined. Corner radius 4. The
  ruled loft F2 → B2 is the pocket; the B2 through prism behind it is the
  `two-finger-opening` attachment.
- **Γ ledge**: top Z 15.2 → 14.05, bottom 6.5 → 5.85, X 9.8 → 95.0 (top) /
  97.8 (bottom), with a hook to a tip at (19.2, −0.8). It ends free with a
  slanted end short of the right wall (G; confirmed by the product owner,
  2026-09-26).
- **Rail**: a stadium, X −82 … 99.5, Z −52.0 … −30.3.
- **Lower-right bevel**: from Z = −55.5 on the rim face back to the bottom
  silhouette at 45°, X 21–96. The bevel is visible in G, D and Q p. 3; its 45°
  angle is a display estimate.
- **Round-overs**: 1.5 mm on every convex edge OCCT can round together (58 of
  102), matching the moulded edges in Trango's CAD render (Q p. 3) and product
  photos. The two gated sloped-crimp bands and the back plane stay sharp, so
  the gated depths are unaffected. The 44 edges OCCT would not round stay
  sharp. Display choice.

Omitted under the hardware/branding policy: the bolt countersink and bore, the
two set-screw holes, the TRANGO plate, and all Quad Cleat and rail hardware.

## Node and slot bindings

The node IDs are unchanged from the pre-migration descriptor:

| Node | Role | Slot |
| --- | --- | --- |
| `pivot_half_body_002` | body | — |
| `upper_sloped_crimp_001` | contact | `upper-sloped-crimp` |
| `outer_sloped_crimp_001` | contact | `outer-sloped-crimp` |
| `variable_edge_001` | contact | `variable-edge` |
| `medium_crimp_001` | contact | `medium-crimp` |
| `large_crimp_001` | contact | `large-crimp` |
| `two_finger_pocket_001` | contact | `two-finger-pocket` |
| `three_finger_pocket_001` | contact | `three-finger-pocket` |
| `outer_wedge_pinch_001` | contact | `outer-wedge-pinch` |
| `lower_sloper_001` | contact | `lower-sloper` |
| `two_finger_opening_001` | attachment | — |
| `three_finger_end_window_001` | attachment | — |

Each contact is a `Part::Feature` copy of the body faces lying on its cutter or
feature. These are static copies, so the published-depth gate is what catches
drift. The sketch edit-propagation suite is not claimed. Every contact carries
a `HangTenHoldOutline`: authored outlines for the rail, pockets, ledge,
medium-crimp strip and wing, and front-view hulls of the faces for the crimp
bands and teeth.

## Manifest change

With a 234 mm half, the old ±102 mm instance translations overlapped the two
halves. All eight translations became ±132.5 mm, which leaves a 30.6 mm gap in
`p1`. The spacing is a display estimate: the Quad Cleats are user-positioned,
and G shows a gap of about 40 mm. Rotations, slot maps, contacts, depths and
all other fields are byte-identical.

## Evidence

- Compile (FreeCAD 1.1.3, OCCT 7.8.1, macOS): 92,547 triangles (the
  round-overs; the USDZ is 2.1 MB);
  `modelBounds` 234.3 × 136.1 × 63.5 mm. Published-depth gates: upper sloped
  crimp 12.500, outer sloped crimp 11.500. Measured region depths for the
  ungated range holds: rail 31.0 (31), 3F 26.5, 2F 32.0,
  medium crimp 8.619 (the round-over on the band edge), large crimp 12.998.
- `verify_reproducible.py --package trango-rock-prodigy-pivot` rebuilds the
  asset byte-identically.
- The compiled mesh is watertight, with consistent winding and positive
  volume, so every node faces outward.
- `compare_exports` (first revision) against the pre-migration mesh reports a two-way sampled
  worst deviation of 36.58 mm (reverse 21.35 mm; limit 0.5 mm; 215,628 /
  84,324 samples). This is **accepted and expected**: the reference was about
  20 % undersized and topologically different (see above). It is evidence, not
  a gate.
- In app (first revision, before the round-over and wing-face pass; node IDs
  and slots are unchanged since): iPhone 17 Pro simulator (iOS 26.5), Debug board-detail route, in a
  workspace-owned simulator that was deleted afterwards. The pair renders
  mirrored with the 30 mm gap. The following selections were confirmed via
  `boardDetail.selectedHold.<id>` and screenshots:
  - `upper-sloped-crimp-left`, the default, highlights the top band;
  - `three-finger-pocket-left`, by deep link, highlights the scalloped pocket;
  - `variable-edge-right`, by hold-map tap on the reflected half, highlights
    the rail.

  Not verified: positions `p2`/`p3`/`p5`, accessibility, and performance.
- Visual review: `Tools/HangboardCAD/photo_grid.py overlay` of the compiled
  front view over G at the bolt-seat scale; side-by-side renders of the compiled asset against G at equal
  mm scale, and against D's photo at a matching viewpoint. `preview.py`
  front/side/top renders of the new asset next to the prior committed asset.
  All images live in workspace scratch, not in the repository.

## Honest limits

This is a measured approximation from photographs and published depths, not
recovered manufacturing geometry. The following are display estimates:

- the wing's cross-section fractions and crease height;
- the bevel angle;
- the rim round-over;
- the retained 35.5 mm body thickness;
- the instance spacing.

The width scale rests on the bolt-seat hardware inference, and the conflicts
with the retail sizes are recorded above.

## Authored point tables

#### Silhouette points (photo frame, mm)

```
(-120.5, -7.5), (-116, -4.5), (-112, -1.6), (-105, 3.1), (-100, 6.6), (-95, 9.8), (-90, 13.2), (-85, 16.8), (-80, 20.2), (-75, 23.7), (-70, 27.2), (-65, 30.6), (-62, 32.8), (-60, 34.6), (-57, 36.3), (-55, 37.2), (-50, 39.1), (-45, 40.3), (-40, 40.8), (-35, 41.1), (-30, 41.1), (-27, 40.8), (-25, 40.7), (-22, 41.5), (-20, 42.3), (-17, 43.5), (-15, 44.2), (-12, 45), (-9, 45.2), (-5, 44.8), (-3, 44.3), (0, 43.3), (2, 42.9), (5, 43), (8, 43.6), (10, 44), (12, 44), (15, 43.6), (18, 42.8), (20, 42.3), (22, 41.5), (24, 40.7), (25, 40.5), (26, 40.8), (28, 41.8), (30, 43), (33, 44.3), (35, 45.2), (37, 46.3), (38.5, 48.3), (40, 49.8), (42, 50.9), (45, 52.2), (50, 53.6), (55, 54.1), (60, 54.4), (65, 54.5), (70, 54.4), (75, 54), (80, 53.4), (85, 52.3), (90, 50.6), (95, 48.4), (100, 45.5), (103, 43), (104.8, 40), (106.5, 36), (108, 32), (109.5, 28), (111, 24), (112.5, 15), (113.4, 8), (113.8, 3.6), (113.8, -5), (113.4, -13.8), (112.5, -17.5), (111.6, -20.8), (110.5, -24.5), (109.9, -27.8), (110.4, -31), (110.8, -34.8), (111.2, -40.9), (110.8, -45), (109.9, -48.7), (107.3, -54.8), (104, -58.5), (100.7, -61.8), (97.5, -65.8), (95.2, -68.9), (93.8, -70.8), (92.5, -71.6), (89.8, -72.4), (80, -72.2), (70, -71.7), (60, -71.3), (50, -70.8), (35, -70.5), (21, -70.3), (20, -69.9), (17, -67.3), (15, -65.4), (14, -64.9), (13.5, -65.2), (12.5, -66.4), (10, -68.6), (5, -72), (0, -74.7), (-3, -76.3), (-5, -77), (-7, -77.2), (-9, -76.9), (-11, -75.6), (-12.7, -74.3), (-15, -72.8), (-16.5, -70.5), (-18, -69.4), (-20, -69.2), (-22, -69.6), (-25, -71.3), (-30, -74.8), (-35, -77.6), (-40, -80.5), (-41.2, -81.3), (-42.5, -81.6), (-43.5, -81), (-45, -78.3), (-48.2, -74.1), (-51.5, -69.8), (-55.2, -65.4), (-56.5, -64.9), (-60, -65), (-70, -65.4), (-75, -65.5), (-78, -65), (-80.5, -64), (-82.6, -62.6), (-85.3, -59.5), (-88.4, -55), (-91.3, -50), (-94.7, -45), (-97.9, -40), (-100, -36.4), (-100.6, -36.1), (-104, -36.4), (-108, -37), (-110, -36.5), (-112.5, -34), (-114.5, -31), (-115.5, -28), (-116, -25), (-117, -20), (-118.5, -15), (-120.3, -10)
```

#### Upper sloped-crimp front edge

```
(38.5, 48.3), (40, 48.4), (45, 49.7), (50, 50.5), (55, 51), (60, 51.3), (65, 51.3), (70, 51.2), (75, 50.8), (80, 50.7), (85, 49.7), (90, 48.2), (95, 45.3), (99, 42), (100.5, 40)
```

#### Outer sloped-crimp front edge

```
(100.5, 40), (101.5, 37), (103, 33), (104, 29), (105, 25), (105.7, 21), (106.4, 17), (107.4, 12), (108.2, 7.1), (108.6, 0), (108.6, -5.1), (108.4, -12), (108.2, -19), (108.6, -24), (109.9, -27.8)
```
