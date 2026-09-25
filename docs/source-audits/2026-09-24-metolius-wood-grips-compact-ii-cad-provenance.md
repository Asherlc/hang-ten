# metolius-wood-grips-compact-ii CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_metolius_wood_grips_compact_ii.py`, which authored
`Hangboards/metolius-wood-grips-compact-ii/metolius-wood-grips-compact-ii.FCStd`. The script was never a build input: the
committed FCStd stands alone, and its embedded `HangTenBoardManifest` is now the
source of `board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was
removed because re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from retained
estimates, or recorded a stated deviation, that wording is kept as written. The
"Sourced versus approximated fields" summary restates the script's own
classification against the existing source audits; it adds no new fact.

## Recovering the script

- Last commit that modified the script: `645ba8a1305a9cc016563c2276382e33020a8756`
- Last commit containing the script before its removal: `eed5c974e6f7843ad242a1ae9eb1091a3b4f1c33`

```sh
git show eed5c974e6f7843ad242a1ae9eb1091a3b4f1c33:Tools/HangboardCAD/migration/author_metolius_wood_grips_compact_ii.py
```

The script imported the shared helper `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under the pinned FreeCAD interpreter
(for example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`. Its
numbers were ported from the pre-migration Blender authoring script
`Tools/HangboardModels/wood_grips_compact_ii.py`, readable with
`git show d7ca9c5c9^:Tools/HangboardModels/wood_grips_compact_ii.py`.

## Sourced versus approximated fields

| Field | Status | Evidence |
| --- | --- | --- |
| Face 610 × 157 mm (24 × 6.2 in); `board.json` `dimensions` `24" × 6.2"` | Published | <https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards>; `docs/source-audits/2026-08-12-metolius-board-packages.md` |
| 19-contact inventory (#1 outer jugs, #2 56 mm flat slopers, #3 29 mm edges, #4/#5 29 mm three/two-finger pockets, #6 19 mm edges, #7/#8 19 mm three/two-finger pockets, #9 56 mm round sloper, #10/#11 29/19 mm four-finger pockets) | Published | official numbered diagram <https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg>; mapping in `2026-08-12-metolius-board-packages.md` |
| 29 / 19 mm contact depths (edges and pockets; the compiler's published-depth gate) | Published | same diagram |
| 56 mm sloper depth callouts (#2, #9) | Published hold-depth label only | same diagram; used only as the top-profile sloper span, not as a body thickness |
| Relative placement (two rows of five pockets between side-open edges; jugs at both top ends; flat slopers either side of the central round sloper) | Published (qualitative) | manufacturer front photograph <https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg> |
| Silhouette cubic spans, pocket and edge centres and sizes, corner and fillet radii, front/back roll radii, depth-dependent top profile | Approximated: retained display estimates | drawn by hand from the manufacturer photograph in `wood_grips_compact_ii.py` at `d7ca9c5c9^`, which labels them estimates |
| 64 mm body depth | Approximated: retained display estimate | same script ("64 mm is an independent display estimate"); Metolius publishes no body thickness |
| Mounting holes and engraved logos | Deliberately omitted | repository screw-hole/hardware omission policy |
| Node IDs `Wood_Grips_Compact_II_020`..`039`, material `canonical_neutral_wood` | Carried from the approved pre-migration asset | reference USDZ resolved from Git (`reference.py` commit `6b828e15`, SHA-256 `addf2cd2ddd34f18f311ccc1413ca94644df0d2f3d56020b68edf25625bc664a`) |

The script checked only the envelope against the reference (610 × 64 × 157 mm,
±0.2 mm); it did not re-measure the reference mesh. Recorded evidence from the
authoring branch: `compare_exports` two-way sampled worst deviation 0.39 mm
(limit 0.5 mm; evidence, not a gate), node IDs and `modelBounds` identical to the
reference, descriptor `facePlaneAABB` within 0.6 mm.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/metolius-wood-grips-compact-ii/*.FCStd.

Migration tool only -- not a build input. The saved FCStd stands alone.

Acceptance bar (declared up front): the approved asset is a sculpted display
shell (rolled front/back edges, a depth-varying top with a rolled jug, pitched
flat slopers and a convex round sloper), so the native source is a *measured
approximation*. ``compare_exports`` is evidence, not a gate. The node/role
inventory, published 29 / 19 mm region depths, the 610 x 157 mm face, and
descriptor ``facePlaneAABB`` agreement with the reference are the acceptance
signals.

Provenance (native mm, +X right, +Z up, front -Y):

Published (manufacturer):
* Face 610 x 157 mm (24 x 6.2 in) -- Metolius Wood Grips II product page,
  https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards
  (also ``board.json`` ``dimensions``).
* Hold inventory and grip depths -- the official numbered Wood Grips Compact
  diagram on the same page
  (https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg):
  #1 outer jugs, #2 56 mm flat slopers, #3 29 mm edges, #4 29 mm three-finger
  pockets, #5 29 mm two-finger pockets, #6 19 mm edges, #7 19 mm three-finger
  pockets, #8 19 mm two-finger pockets, #9 56 mm round sloper, #10 29 mm
  four-finger pocket, #11 19 mm four-finger pocket. The 29 / 19 mm values are
  the region depths the compiler gates on.
* Relative placement: the manufacturer front photograph
  (https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg)
  shows two rows of five pockets between side-open edges, jugs at both ends of
  the top, flat slopers either side of a central round sloper.

Retained authored estimates (not manufacturer dimensions):
* Every numeric silhouette control point, pocket centre/width/height, edge
  recess size, fillet radius, top-profile drop, and the 64 mm body depth below
  is carried verbatim from the approved pre-migration model's authoring script
  (``Tools/HangboardModels/wood_grips_compact_ii.py``, last present at
  ``d7ca9c5c9^``). That script states the values were drawn by hand from the
  manufacturer photograph and are display estimates; Metolius publishes no
  body thickness, pocket aperture, radius, or back profile for this board. The
  reference USDZ is resolved from Git only to confirm the envelope.
* Six physical mounting holes and the engraved logos are deliberately omitted
  (repository screw-hole/hardware omission policy).

Construction: the body is a closed polyhedral solid built from the silhouette
at a series of depth stations (each station is the silhouette offset along its
inward normal by the front/back roll inset, with the top lowered by the
depth-dependent jug/sloper profile). Every face is a planar quad or triangle so
contact partitioning by the compiler is exact. Each pocket and side-open edge
is a planar-faced ruled cutter (capsule / rounded rectangle stations with a
back fillet and a flared mouth fillet). One ``Part::Cut`` removes all cutters;
the result is baked into the exported ``BodySolid``. Contacts are faces of the
cut body: a pocket/edge region is every body face lying on that hold's cutter,
and the top regions (jugs, flat slopers, round sloper) are the up-facing top
faces partitioned at the same x boundaries the reference used.
```

## Recorded constants

```python
PACKAGE = "metolius-wood-grips-compact-ii"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get(
        "HANGTEN_CAD_SCRATCH",
        str(REPOSITORY / ".context" / f"freecad-{PACKAGE}"),
    )
)

# Published face (manufacturer): 610 x 157 mm.
FACE_WIDTH = 610.0
FACE_HEIGHT = 157.0
# Retained display estimate (no published thickness).
BODY_DEPTH = 64.0

# Retained silhouette: cubic spans in left-origin (x, h) mm, left half only,
# mirrored about x = 305. Drawn by hand from the manufacturer photograph in the
# pre-migration model; display estimates, not manufacturer dimensions.
SPANS = [
    ((305, 151), (268, 151), (228, 151), (204, 151)),
    ((204, 151), (197, 151), (198, 146), (190, 146)),
    ((190, 146), (163, 146), (133, 146), (111, 146)),
    ((111, 146), (103, 146), (103, 157), (94, 157)),
    ((94, 157), (72, 157), (44, 157), (29, 155)),
    ((29, 155), (10, 153), (0, 148), (0, 139)),
    ((0, 139), (0, 128), (14, 110), (16, 88)),
    ((16, 88), (18, 76), (13, 75), (16, 68)),
    ((16, 68), (20, 62), (23, 52), (24, 40)),
    ((24, 40), (26, 25), (26, 20), (25, 15)),
    ((25, 15), (23, 6), (34, 0), (48, 0)),
    ((48, 0), (112, 0), (222, 0), (305, 0)),
]
SPAN_STEPS = 8

# Top-region x boundaries (left-origin), identical to the reference partition.
JUG_LIMIT = 106.0
FLAT_SLOPER_LIMIT = 196.0
TOP_REGION_MIN_H = 126.0
TOP_REGION_MIN_NORMAL_Z = 0.12

# Retained pocket layout (depth, centre h, outer-pocket x, inner-pocket x,
# three-finger width, two-finger width); all pockets are 25 mm tall capsules,
# the centre four-finger pocket is 96 mm wide.
POCKET_LAYOUT = [
    (29.0, 88.0, 151.0, 221.0, 66.0, 46.0),
    (19.0, 29.0, 161.0, 224.5, 62.0, 39.0),
]
POCKET_HEIGHT = 25.0
CENTER_POCKET_WIDTH = 96.0
POCKET_BACK_FILLET = 4.5
POCKET_MOUTH_FILLET = 3.5

# Retained side-open edge recesses (depth, centre h, width, height, centre x),
# corner radius 8 mm, 6 mm back and mouth fillets.
EDGE_LAYOUT = [
    (29.0, 98.0, 119.0, 48.0, 39.0),
    (19.0, 34.0, 131.0, 43.0, 43.0),
]
EDGE_RADIUS = 8.0
EDGE_FILLET = 6.0

FILLET_STEPS = 6
ARC_STEPS = 8
MOUTH_OVERSHOOT = 20.0

NODE_IDS = {
    "edge-19-left": "Wood_Grips_Compact_II_020",
    "edge-19-right": "Wood_Grips_Compact_II_021",
    "edge-29-left": "Wood_Grips_Compact_II_022",
    "edge-29-right": "Wood_Grips_Compact_II_023",
    "jug-left": "Wood_Grips_Compact_II_024",
    "jug-right": "Wood_Grips_Compact_II_025",
    "pocket-19-four-center": "Wood_Grips_Compact_II_026",
    "pocket-19-three-left": "Wood_Grips_Compact_II_027",
    "pocket-19-three-right": "Wood_Grips_Compact_II_028",
    "pocket-19-two-left": "Wood_Grips_Compact_II_029",
    "pocket-19-two-right": "Wood_Grips_Compact_II_030",
    "pocket-29-four-center": "Wood_Grips_Compact_II_031",
    "pocket-29-three-left": "Wood_Grips_Compact_II_032",
    "pocket-29-three-right": "Wood_Grips_Compact_II_033",
    "pocket-29-two-left": "Wood_Grips_Compact_II_034",
    "pocket-29-two-right": "Wood_Grips_Compact_II_035",
    "sloper-flat-left": "Wood_Grips_Compact_II_036",
    "sloper-flat-right": "Wood_Grips_Compact_II_037",
    "sloper-round-center": "Wood_Grips_Compact_II_038",
    "body": "Wood_Grips_Compact_II_039",
}

MATERIAL_NAME = "canonical_neutral_wood"
MATERIAL_BASE_COLOR = "0.69,0.49,0.28"
MATERIAL_ROUGHNESS = 0.62
MATERIAL_METALLIC = 0.0

PLANAR_TOLERANCE = 1e-7
```

## Inline authoring notes

- `native()`:
  - Docstring: Left-origin width, bottom-origin height, depth-from-back -> native mm.
- `_split_at_x()`:
  - Docstring: Insert a vertex wherever a top segment crosses a region boundary.
- `top_profile()`:
  - Docstring: Retained depth-dependent top: rolled jugs, pitched flat, convex round.
- `roll_inset()`:
  - Docstring: 2 mm back roll; 7 mm (bottom rail) to 2 mm (top) front roll.
- `_ring_polygons()`:
  - Docstring: Side quads (or triangle pairs where non-planar) plus the two end caps.
  - Reflected diagonal so mirrored halves facet identically.
- `body_solid()`:
  - Merge coplanar neighbours (the constant-section lower body between the rolls); top-region faces are checked against the partition boundaries in classify_faces so a merge can never straddle two holds.
- `recess_stations()`:
  - Docstring: (depth-from-back, inset) stations: floor fillet, wall, flared mouth.
- `mouth_outline()`:
  - Docstring: Front-plane opening of a recess (native [x, z]), the tap target.
- `hold_cutters()`:
  - Docstring: {contact id: (cutter solid, outline or None)} in left-origin layout.
  - Side-open: the outline is the face-plane region, clipped later to the body's own extent by the region bounding box.
- `_face_sample()`:
  - Docstring: A point on the face and the outward normal there.
- `main()`:
  - Document properties: `HangTenSchemaVersion` 1, `HangTenSourceKind` `native-parametric-measured-profile`, `HangTenCoordinateFrame` `freecad-mm-z-up-front-negative-y`, `HangTenTessellationDeflection` 0.05. The manifest (`HangTenBoardManifest`) was embedded afterwards with `set_board_manifest.py`; only `Document.xml` changed.
  - One `Part::Cut` of the envelope by a compound of every cutter; the result is copied into the exported `BodySolid`. Each contact is a `Part::Feature` holding the cut-body faces that lie on its cutter (pockets, edges) or the up-facing top faces between the fixed x boundaries (jugs, slopers).
  - `HangTenHoldOutline` is the mouth capsule for pockets and the region bounding rectangle for edges, jugs, and slopers.
  - The reference's single embedded texture is extracted and embedded on the body as `TextureFile`; contacts share `MaterialName` and inherit it.

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if not shell.isClosed():
    raise ValueError("polyhedral shell is not closed")
if solid.Volume <= 0 or not solid.isValid():
    raise ValueError(f"invalid polyhedral solid (volume {solid.Volume})")
if not refined.isValid() or abs(refined.Volume - solid.Volume) > 1e-3:
    raise ValueError("refining the envelope changed its volume")
if len(counts) != 1:
    raise ValueError(f"recess stations disagree on vertex count: {counts}")
if not triangles:
    raise ValueError("face has no tessellation")
if box.XMin < edge - 1.0 and box.XMax > edge + 1.0:
    raise ValueError(f"top face straddles region boundary x={edge}: {box}")
if len(names) != 1:
    raise ValueError(f"expected exactly one reference texture, found {names}")
if abs((highs[axis] - lows[axis]) - target) > 0.2:
    raise ValueError(f"reference axis {axis} extent {highs[axis] - lows[axis]:.3f} != {target}")
if body_cut.Shape.isNull() or not body_cut.Shape.isValid():
    raise ValueError("hold boolean cut failed")
if len(body_cut.Shape.Solids) != 1:
    raise ValueError(f"cut body has {len(body_cut.Shape.Solids)} solids")
if not faces:
    raise ValueError(f"{contact_id} matched no body faces")
if published is not None and abs(box.YLength - published) > 0.25:
    raise ValueError(f"{contact_id} region depth {box.YLength:.3f} != published {published}")
if stale:
    raise ValueError(f"document failed recompute: {stale}")
```
