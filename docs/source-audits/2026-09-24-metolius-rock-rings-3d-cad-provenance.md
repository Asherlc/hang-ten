# metolius-rock-rings-3d CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_metolius_rock_rings_3d.py`, which authored
`Hangboards/metolius-rock-rings-3d/metolius-rock-rings-3d.FCStd`. The script was never a build input: the
committed FCStd stands alone, and its embedded `HangTenBoardManifest` is now the
source of `board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was
removed because re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written.

## Recovering the script

- Last commit that modified the script: `08ba107fc30f9eb3109ed15e4feb551c830ee38a`
- Last commit containing the script before its removal: `060eba8ebd6d5ba44ae8becd3a538232d483eaa9`

```sh
git show 060eba8ebd6d5ba44ae8becd3a538232d483eaa9:Tools/HangboardCAD/migration/author_metolius_rock_rings_3d.py
```

The script imported the shared helpers `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under the pinned FreeCAD interpreter
(for example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/metolius-rock-rings-3d/metolius-rock-rings-3d.FCStd.

This script is a MIGRATION TOOL, not a build input. The saved FCStd must stand
alone: the shared compiler never runs this file, and nothing here is required to
rebuild the published runtime asset.

Provenance of every number written into the document:

* Overall size 146 x 57 x 184 mm (x, depth, height) and the three grip depths
  (40, 32, 25 mm) come from ``Hangboards/metolius-rock-rings-3d/board.json``
  (``dimensions`` and each contact's ``depth.range``). These are PUBLISHED
  product facts.
* The mid-depth outline, the three pocket openings/floors, the jug band and the
  two cord apertures are MEASURED from the approved model reference
  ``Hangboards/metolius-rock-rings-3d/assets/primary.usdz`` resolved from Git.
  They are measured approximations of a display mesh, not recovered
  manufacturing data.
* The measured mid-depth outline is reduced to the authored vertex set with a
  stated tolerance; the achieved maximum deviation is printed and recorded.

The authored document is a real native feature tree: a fully constrained
Sketcher profile padded along the depth axis, a native fillet for the 6 mm
perimeter round, native ruled lofts for each pocket (opening and floor both
measured, so the published grip depth is the loft's extent), a native common for
the jug band, and native extruded cuts for the cord apertures. Nothing here is
presented as recovered parametric design history.
```

## Recorded constants

```python
PACKAGE = "metolius-rock-rings-3d"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
BODY_PRIM = "/root/ring_body/ring_body_001"
SLOT_PRIMS = {
    "jug": "/root/unit_jug/unit_jug_001",
    "pocket-25": "/root/unit_pocket_25/unit_pocket_25_001",
    "pocket-32": "/root/unit_pocket_32/unit_pocket_32_001",
    "pocket-40": "/root/unit_pocket_40/unit_pocket_40_001",
}
ATTACHMENT_PRIMS = {
    "lateral_window_001": "/root/lateral_window/lateral_window_001",
    "roof_exit_001": "/root/roof_exit/roof_exit_001",
}
MID_TOLERANCE_MM = 0.15
PROFILE_TOLERANCE_MM = 0.1
PERIMETER_ROUND_MM = 6.0
LATERAL_DEPTH_MM = 9.0
ROOF_DEPTH_MM = 10.0
PUBLISHED_MM = {"width": 146.0, "height": 184.0}
MATERIAL_NAME = "neutral_resin"
MATERIAL_BASE_COLOR = "0.82,0.80,0.76"
MATERIAL_ROUGHNESS = 0.45
MATERIAL_METALLIC = 0.0
# The pinned-build Sketcher axis distances solve to the negated value, so each
# authored local coordinate is the negated, shifted native coordinate and the
# sketch placement un-negates it. Frames map local (u, v) onto the sketch plane.
OUTLINE_FRAME = _matrix(
    [
        (-1.0, 0.0, 0.0, -73.0),
        (0.0, 0.0, -1.0, 0.0),
        (0.0, -1.0, 0.0, -92.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
LATERAL_RIGHT_FRAME = _matrix(
    [
        (0.0, 0.0, 1.0, 74.0),
        (-1.0, 0.0, 0.0, -14.0),
        (0.0, -1.0, 0.0, 38.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
LATERAL_LEFT_FRAME = _matrix(
    [
        (0.0, 0.0, 1.0, -74.0),
        (-1.0, 0.0, 0.0, -14.0),
        (0.0, -1.0, 0.0, 38.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
ROOF_FRAME = _matrix(
    [
        (-1.0, 0.0, 0.0, 57.5),
        (0.0, -1.0, 0.0, -4.5),
        (0.0, 0.0, 1.0, 94.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
```

## Inline authoring notes

- `_mid_outline()`:
  - Docstring: Measured mid-depth outline from the vertical side wall of the slab.
  - The descriptor derives modelBounds from the exported vertices, and the package contract pins the published envelope. Merging and reduction can pull an extreme in by a fraction of a millimetre, so snap the four extreme vertices back onto the published 146 x 184 mm envelope.
- `_resample_closed()`:
  - Docstring: Resample a closed polygon to ``count`` points by arc length. A ruled loft needs matching vertex order between its sections or it twists into a wedge. Both pocket sections are therefore resampled from the same start (the topmost vertex) in the same direction.
- `_project_outline()`:
  - Docstring: Ordered front-plane outline of a set of (x, z) points (star-shaped).
- `_smooth_top_notch()`:
  - Docstring: Bow the straight top-center chord into a shallow arc. The measured silhouette has no vertices between the ears, so the pad's top is one straight horizontal chord spanning the depth: its side wall faces straight up for the full 57 mm and renders as a single over-lit facet. Bowing the chord into a shallow arc gives that wall depth-varying normals, so the top reads as a rounded notch (the design intent) without modelling the sculpted lip.
- `_bind()`:
  - The CAD document is the source of truth for hold geometry: the compiler reads this front-plane polygon (native XZ millimetres) and emits it as the descriptor's hold region.
- `main()`:
  - The exported hold region is the pocket's cap-free CAD surface: the loft's lateral surface (Solid=False) plus its floor face. The solid is only the boolean tool, so the opening cap never becomes a hold.
  - Lofting from floor to opening reverses the lateral surface normals so the cavity-facing side is front-facing in the rendered highlight.
  - The pocket's cap-free lateral surface and floor are already inside the body; clipping them with Part::Common against the body boundary would be a degenerate boolean and fragments the surface. The raw surface is reversed during binding so the cavity-facing side is front-facing.
  - The jug is a sub-region of the flat front face. A flat patch z-fights the face and a centroid partition of that face is ragged, so author it as a shallow recess exactly like a pocket: the body takes a clean cut, the partition claims that cut's surface, and the region mesh matches it. Keep the band on the flat front face: above ~z84 the face has curved back into the top fillet, so a straight recess there would poke off the body.
  - The cut needs a solid; the exported hold surface is cap-free.
  - The attachment surfaces start outside the body envelope and must be clipped to it, but only the cap-free surfaces (not their solids) are exported as nodes.
  - Pockets export their cap-free surface directly; attachments are clipped to the body; the jug is already a clean proud patch.
  - Reverse the cap-free shell so its cavity-facing side (floor toward the camera, walls inward) is front-facing in the highlight. Part::Reverse is parametric, so the region still follows edits.
  - The jug mesh is the front-facing patch bounded by the box footprint; keep the outline coincident with that patch.

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if len(selected) < 3:
    raise ValueError(f"no rim vertices at y={y}")
if abs(measured - PUBLISHED_MM[key]) > 0.5:
    raise ValueError(f"measured {key} {measured:.3f} disagrees with published")
if slot in depths and abs(depths[slot] - low) > 1e-6:
    raise ValueError(f"slot {slot} declares conflicting depths")
if not sketch.FullyConstrained:
    raise ValueError(f"{name} is not fully constrained")
if not perimeter:
    raise ValueError("no front/back perimeter edges found to round")
if depth is None:
    raise ValueError(f"no published depth for slot {slot}")
if abs(measured_depth - depth) > 0.5:
    raise ValueError( f"{slot} measured depth {measured_depth:.2f} disagrees with published {depth}" )
if stale:
    raise ValueError("document did not recompute cleanly: " + "; ".join(stale))
```
