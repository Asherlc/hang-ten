# trango-rock-prodigy-natural CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_trango_rock_prodigy_natural.py`,
which authored
`Hangboards/trango-rock-prodigy-natural/trango-rock-prodigy-natural.FCStd`. The
script was never a build input: the committed FCStd stands alone, and its
embedded `HangTenBoardManifest` is now the source of `board.json`
(`Tools/HangboardCAD/board_manifest.py`). The script was removed because
re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written.

## Recovering the script

- Last commit that modified the script: `367b8e1fc` (3-finger pocket as three
  overlapping bores)
- Last commit containing the script before its removal: `6666ccde3` (merge of
  `origin/main`, which retired the per-board author scripts)

```sh
git show 6666ccde3:Tools/HangboardCAD/migration/author_trango_rock_prodigy_natural.py
```

The script imported the shared helper `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved pre-migration reference USDZ from
Git at the recorded commit) and ran under the pinned FreeCAD interpreter (for
example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/trango-rock-prodigy-natural/*.FCStd.

Migration tool only — not a build input. The saved FCStd stands alone.

Acceptance bar: the reference mesh is a genuinely sculpted shell (16,842 body
points per half). A native pad/loft model cannot match every scooped wall
exactly. This is a native *measured approximation* driven from each reference
hold prim's own mesh:

* Constant-depth holds (closed-crimp, upper-pocket, center-lower-pocket, jug)
  extrude a mesh-derived XZ footprint at the published / measured depth.
* Variable-depth holds (top/bottom rails, outer-supported-pocket) loft
  measured YZ cross-sections along X so depth tapers with the reference
  (and with the manufacturer 20–33 / 10–24 mm rail ranges).

Holds whose measured footprint is genuinely a regular shape are authored as a
clean primitive built from the measured opening bounds — a stadium (the two
variable rails, the center-lower pocket, the 3-finger upper pocket) or an
ellipse (the outer-supported-pocket). This is a deliberate, labeled visual
adaptation for fidelity of form, not a traced measurement. The measured
envelope is kept only where the shape is genuinely irregular — the closed-crimp
sloper/wedge and the elongated top jug. Rail depth still follows the measured
profile, so the variable rails keep their taper.

Irregular measured footprints are vectorized: each closed XZ ring is
Chaikin-smoothed and fit with a low-degree `Part.BSplineCurve.approximate` (C2,
DegMax=5, ``OUTLINE_FIT_TOLERANCE_MM``), then discretized at
``OUTLINE_DEFLECTION_MM`` and resampled to ``OUTLINE_SAMPLES`` evenly spaced
points. A low-degree *approximation* keeps the fit from chasing measured noise
into tens of poles: too many poles both wiggles the silhouette and makes OCCT
mesh the extruded surface into hundreds of thousands of triangles per hold
(measured: a 168-pole VDegree=1 BSplineSurface meshes into 1.66M triangles /
89 s at 0.02 mm, and still 266k at 0.5 mm). Rail depth/z profiles are densely
sampled then linearly resampled so the taper reads smooth rather than
stair-stepped. Still mesh-derived — not photo-traced.

`compare_exports` is evidence, not a gate — see docs/freecad-authoring-migration.md
"Accepted deviation for a sculpted board".

Shape revision (mesh-derived pass): prior passes used AABB boxes, invented
hook/ribbon paths, and constant rail depths. User visual review rejected those;
measurements against the 5.7 MB pre-migration reference confirmed rails taper
20.9→32.7 and 10.9→23.7 mm, and closed-crimp is a floor-envelope wedge+tab
(not a Nike swoosh). This script derives those facts from the reference prims.
```

## Recorded constants

```python
PACKAGE = "trango-rock-prodigy-natural"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
REFERENCE_COMMIT = "de267c7ff2483d5cf91f197d3cbbec5415214a05"

# Native frame, one half of the two-piece board.
HALF_X = 95.25
HALF_Z = 76.2
Y_FRONT = -38.1
Y_BACK = 0.0
BODY_X = 190.5
BODY_Y = 38.1
BODY_Z = 152.4
LEFT_CENTER_X = -145.25
RIGHT_CENTER_X = 145.25

CORNER_R = 10.0
CORNER_SEGMENTS = 10
EDGE_ROLL_R = 3.0
EDGE_ROLL_SEGMENTS = 6

OUTLINE_DEFLECTION_MM = 0.05
OUTLINE_SAMPLES = 120
OUTLINE_FIT_TOLERANCE_MM = 0.8
TOP_JUG_EDGE_INSET = 1.0

NOTCH_LEFT = {"x0": -100.0, "x1": -49.0, "z0": -77.0, "z1": -44.0}
NOTCH_MARGIN_Y = 2.0
TOP_BEVEL_RUN_Y = 6.0
TOP_BEVEL_RUN_Z = 4.0

MATERIAL_NAME = "beech_substrate"
MATERIAL_BASE_COLOR = "0.78,0.65,0.45"
MATERIAL_ROUGHNESS = 0.78
MATERIAL_METALLIC = 0.0

HOLD_KIND = {
    "closed-crimp": ("extrude", "recess"),
    "center-lower-pocket": ("extrude", "recess"),
    "upper-pocket": ("extrude", "recess"),
    "outer-supported-pocket": ("taper", "recess"),
    "bottom-variable-rail": ("taper", "recess"),
    "top-variable-rail": ("taper", "recess"),
    "top-jug": ("extrude", "protrusion"),
}
GRIP_DEPTH_MM = {"top-jug": 40.0, "upper-pocket": 38.0}

PRIMITIVE_SHAPE = {
    "top-variable-rail": "stadium",
    "bottom-variable-rail": "stadium",
    "center-lower-pocket": "stadium",
    "upper-pocket": "lobes3",
    "outer-supported-pocket": "ellipse",
}
LOBE_SPACING_FACTOR = 1.55

NODE_SUFFIX = {
    "closed-crimp": "closed_crimp_001",
    "center-lower-pocket": "pocket_2finger_001",
    "upper-pocket": "pocket_3finger_001",
    "outer-supported-pocket": "pocket_supported_001",
    "bottom-variable-rail": "rail_lower_001",
    "top-variable-rail": "rail_upper_001",
    "top-jug": "jug_001",
}
LEFT_HOLD_PATHS = {
    "closed-crimp": "/root/hold__left_closed_crimp/hold__left_closed_crimp_002",
    "center-lower-pocket": "/root/hold__left_pocket_2finger/hold__left_pocket_2finger_002",
    "upper-pocket": "/root/hold__left_pocket_3finger/hold__left_pocket_3finger_002",
    "outer-supported-pocket": "/root/hold__left_pocket_supported/hold__left_pocket_supported_002",
    "bottom-variable-rail": "/root/hold__left_rail_lower/hold__left_rail_lower_002",
    "top-variable-rail": "/root/hold__left_rail_upper/hold__left_rail_upper_002",
    "top-jug": "/root/hold__left_jug/hold__left_jug_002",
}
```

## Inline authoring notes

- **Primitive holds (labeled visual adaptation, not measured).** The two
  variable rails and the center-lower pocket are stadiums, the
  outer-supported-pocket an ellipse, and the 3-finger upper pocket the union of
  three overlapping circular bores (`LOBE_SPACING_FACTOR` < 2 gives the
  scalloped 3-lobe opening the manufacturer top-down photo shows). The
  `TRANG0` manufacturer photos in
  `.context/trango-natural-cad/trango-rock-prodigy-natural/manufacturer-photos/`
  (`top-down.jpg`, `pockets.jpg`, `rails.jpg`, `side.jpg`) are the form source.
  Primitive bounds come from the front-plane opening rim
  (`_opening_bounds`, a 1 mm band at the front), not the prim's full wall extent.
- **Irregular holds keep the measured envelope.** The closed-crimp sloper/wedge
  uses a floor-band min/max-z envelope; the elongated top jug uses a full
  min/max-z envelope (a radius-from-centroid outline degenerates into a bowtie
  on a 185 × 12 mm strip) and is inset `TOP_JUG_EDGE_INSET` from the board's top
  rim so the body/region partition seam does not tear on the shared edge.
- **Vectorized measured footprints.** Chaikin-smooth, then low-degree
  `Part.BSplineCurve.approximate` (C2, DegMax 5, `OUTLINE_FIT_TOLERANCE_MM`),
  discretize at `OUTLINE_DEFLECTION_MM`, and resample to `OUTLINE_SAMPLES`
  equally spaced points. Interpolating every reduced point chased noise into
  tens of poles, which both wiggled the silhouette and exploded the OCCT mesh.
- **Rail depth.** Taper holds loft measured YZ cross-sections along X; primitive
  rails generate those cross-sections from the stadium/ellipse outline with the
  depth from the measured profile (`_depth_at`).
- **Regions face the front.** Recess regions are reoriented from the recess
  floor normal (`_orient_region`); mirroring the outline had flipped one half's
  winding, and the single-sided material culled it (white holes in the app that
  the double-sided offline renderer hid).
- **Flat back.** Protrusions carry no back-plane floor face, so the board back
  stays a single flat surface (the jug floor would otherwise be coplanar with
  the body back and z-fight).
- **Native frame.** One half per side; body 190.5 × 38.1 × 152.4 mm, front at
  `Y_FRONT = -38.1`, board top `HALF_Z = 76.2`, bottom-inner L-notch
  `NOTCH_LEFT`, gentle top-front bevel `TOP_BEVEL_RUN_Y/Z` (approximation of
  `side.jpg`; the top-jug fuse restores material over its own footprint).
- **Published vs measured.** Published grip depths (`GRIP_DEPTH_MM`) are product
  facts validated against the region extent; all other hold geometry is a
  measured approximation of the pre-migration display mesh, not recovered
  manufacturing geometry.

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines
verbatim).

```python
if reference.stat().st_size < 1_000_000:
    raise ValueError(
        f"reference looks like an LFS pointer stub ({reference.stat().st_size} bytes); "
        "set HANGTEN_REFERENCE_DIR to the resolved 5.7 MB USDZ directory"
    )
body_mesh_targets = {"width": BODY_X, "depth": BODY_Y, "height": 146.4}
for key, target in body_mesh_targets.items():
    if abs(measured_body[key] - target) > 0.2:
        raise ValueError(
            f"reference {key} {measured_body[key]:.3f} mm != target {target}"
        )
if len(outline) < 4:
    raise ValueError(f"{base}: outline too small ({len(outline)})")
if notch_cut.Shape.isNull() or notch_cut.Shape.Volume < 1.0:
    raise ValueError(f"{side} outline notch cut failed")
if bevel_cut.Shape.isNull() or bevel_cut.Shape.Volume < 1.0:
    raise ValueError(f"{side} top-edge bevel cut failed")
if cut_obj.Shape.isNull() or cut_obj.Shape.Volume < 1.0:
    raise ValueError(f"{contact_id} cut failed")
if fuse_obj.Shape.isNull() or fuse_obj.Shape.Volume < 1.0:
    raise ValueError(f"{side} jug fuse failed")
if stale:
    raise ValueError(f"document failed recompute: {stale}")
for base, published in GRIP_DEPTH_MM.items():
    for side_name in ("left", "right"):
        contact_id = f"{base}-{side_name}"
        measured_depth = regions[contact_id]["depth"]
        if abs(measured_depth - published) > 0.25:
            raise ValueError(
                f"{contact_id} region depth {measured_depth} mm != published {published} mm"
            )
```
