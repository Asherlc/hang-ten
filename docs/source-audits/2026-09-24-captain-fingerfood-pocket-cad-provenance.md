# captain-fingerfood-pocket CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_captain_fingerfood_pocket.py`, which authored
`Hangboards/captain-fingerfood-pocket/captain-fingerfood-pocket.FCStd`. The script was never a build input: the
committed FCStd stands alone, and its embedded `HangTenBoardManifest` is now the
source of `board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was
removed because re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written.

## Recovering the script

- Last commit that modified the script: `98d6c828423d4ec757275021de32d7b4a976e3bc`
- Last commit containing the script before its removal: `060eba8ebd6d5ba44ae8becd3a538232d483eaa9`

```sh
git show 060eba8ebd6d5ba44ae8becd3a538232d483eaa9:Tools/HangboardCAD/migration/author_captain_fingerfood_pocket.py
```

The script imported the shared helpers `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under the pinned FreeCAD interpreter
(for example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/captain-fingerfood-pocket/*.FCStd.

Migration tool only — not a build input. The saved FCStd stands alone.

Acceptance bar (declared up front): sculpted display shell → measured
approximation. compare_exports is evidence, not a gate. Visually coherent
holds, published grip depths on edge-15/edge-20, node inventory, and envelope
match are the acceptance signals.

Measured facts (Git reference, native mm, +X right +Z up front -Y):

* Envelope 110 × 29 × 66 (x × y × z). Catalogue "110 × 66 × 29 mm" agrees;
  descriptor ±55/±33/±14.5 m matches the mesh.
* One continuous front cavity (rounded-rect trough with ~15 mm corners and a
  6.5 mm entry lip), not four separate pockets. Contacts partition that cavity
  plus the outer rim.
* Outer envelope corners ~10 mm (measured); perimeter roll ~3.5 mm.
* edge-15 / edge-20: opposing long lips with a **stepped floor** (15 mm on +Z,
  20 mm on −Z) per manufacturer “15 sowie 20 mm tiefe Griffleiste” and the
  reference floor (~y 0.7 / 5.3). Published depths 15 / 20 mm.
* pocket-end-wall-15-20: left short end of the same cavity (no fixed depth gate).
* jug-outer-rim: continuous top exterior band (U), full body depth — one contact,
  not a separate pinch.
* Cord through-holes at x=±22, z=0: ~3 mm radius n-gon, floor through back.

Construction: rolled rounded-rect envelope (~10 mm corners), one rounded-rect
cavity with a 6.5 mm entry lip and stepped 15/20 mm floors, through-hole n-gon
cord bores cut last, contacts as faces of the cut body.
```

## Recorded constants

```python
PACKAGE = "captain-fingerfood-pocket"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get(
        "HANGTEN_CAD_SCRATCH",
        str(REPOSITORY / ".context" / "freecad-captain-fingerfood-pocket"),
    )
)
# Mesh envelope (native mm).
HALF_X = 55.0
HALF_Z = 33.0
Y_FRONT = -14.5
Y_BACK = 14.5
BODY_X = 110.0
BODY_Y = 29.0
BODY_Z = 66.0
CORNER_R = 11.0  # manufacturer photos: heavily rounded outer corners
CORNER_CENTER_X = HALF_X - CORNER_R
CORNER_CENTER_Z = HALF_Z - CORNER_R
CORNER_SEGMENTS = 10
EDGE_ROLL_R = 4.0  # soft outer roll-over visible in product shots
EDGE_ROLL_SEGMENTS = 8
# Cavity is a rounded rectangle (not a full-end stadium). Measured opening
# ≈ ±41.8 × ±22.8 with ~15 mm corners; manufacturer lip radius 6.5 mm.
OPEN_HALF_X = 41.8
OPEN_HALF_Z = 22.8
OPEN_CORNER_R = 15.0  # LINESGriffe / mesh: generous cavity corners
OPEN_SEGMENTS = 10
TROUGH_Z_CENTER = 0.0
DEPTH_15 = 15.0
DEPTH_20 = 20.0
FLOOR_Y = Y_FRONT + DEPTH_20
LIP_15_Y = Y_FRONT + DEPTH_15
LIP_R = 6.5  # published Griffkante radius
LIP_SEGMENTS = 8
FLOOR_INSET = 1.6  # slight shrink from opening to floor after the lip
# Cord through-holes at x=±22, z=0 (n-gon loft, no Cylinder). Visible on the
# cavity floor and the back face.
CORD_X = 22.0
CORD_R = 3.0
CORD_SIDES = 16
GRIP_DEPTH_MM = {"edge-15": DEPTH_15, "edge-20": DEPTH_20}
NODE_IDS = {
    "body": "body_skin_001",
    "edge-15": "edge_15_skin_001",
    "edge-20": "edge_20_skin_001",
    "jug-outer-rim": "jug_outer_rim_skin_001",
    "pocket-end-wall-15-20": "pocket_end_wall_15_20_skin_001",
}
MATERIAL_NAME = "lines_blue_charcoal"
MATERIAL_BASE_COLOR = "0.22,0.35,0.55"
MATERIAL_ROUGHNESS = 0.68
MATERIAL_METALLIC = 0.0
BODY_PRIM = "/root/body_main/body_skin_001"
```

## Inline authoring notes

- `_reference_texture()`:
  - Prefer the lines body texture; fall back to first PNG.
- `_opening_xz()`:
  - Docstring: CCW (x, z) rounded-rect cavity outline centred on the origin.
- `_lip_stations()`:
  - Docstring: (depth_from_front, radial_inset) — 6.5 mm entry lip, then floors. A station lands on DEPTH_15 so the upper (+Z) contact can own a published 15 mm wall band before the lower half continues to 20 mm.
  - Explicit (0, 0) keeps the measured opening at Y_FRONT; (-0.05, 0) alone sits outside the body and would shrink the front face via interpolation.
  - Convex entry lip: inset grows with depth (cutter shrinks into the body).
  - Floor insets begin after the full lip radius so the cavity stays monotonic.
  - Keep stations strictly deepening.
- `_station_ring()`:
  - Docstring: Opening ring at Y_FRONT + depth, inset from the measured opening.
- `_cap_fan()`:
  - Docstring: Planar triangle fan closing a ring (flat floor).
- `_half_opening_points()`:
  - Docstring: Closed half rounded-rect at depth y, diameter along z=0.
- `_floor_insets()`:
  - Docstring: DEPTH_15 / DEPTH_20 radial insets from the trough station list.
- `_upper_floor_filler()`:
  - Docstring: Fill the +Z half between 15 mm and 20 mm so that half reads as a 15 mm edge. Section insets come from the trough's DEPTH_15 / DEPTH_20 stations with a small radial overlap so the fuse bonds into the cavity wall.
- `_trough_cutter()`:
  - Docstring: Rounded-rect cavity to 20 mm with a 6.5 mm entry lip (triangle soup).
- `_cord_mouth()`:
  - Docstring: Through-hole n-gon from the cavity floors through the back face. Opens on both the 15 mm and 20 mm floor levels (z≈0 sits on the step), so the start plane is slightly proud of the shallower floor.
- `_in_trough()`:
  - Docstring: True if (x, z) lies inside the opening rounded-rect (plus slack).
- `_edge_15_filter()`:
  - Docstring: Upper (+Z) lip and 15 mm floor — manufacturer 15 mm Griffleiste.
- `_edge_20_filter()`:
  - Docstring: Lower (−Z) lip and 20 mm floor — manufacturer 20 mm Griffleiste.
- `_pocket_end_filter()`:
  - Docstring: Left short end of the cavity (whole-face extent on −X).
- `_jug_filter()`:
  - Docstring: Continuous top exterior band (source-backed U), not the cavity.
  - Tall side face that only grazes the top — skip unless it's the top rim.
  - Prefer the rolled top lip: high Z, not the flat back.
- `main()`:
  - Deep cavity first, then raise the +Z floor to 15 mm, then punch cords through the finished body so the filler cannot plug the holes.
  - Unlink only after validation so a failed author leaves the prior FCStd.

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if not names:
    raise ValueError("no reference texture found")
if not shell.isClosed():
    raise ValueError("triangulated cutter shell is not closed")
if solid.Volume <= 0.0:
    raise ValueError(f"triangulated cutter volume {solid.Volume}")
if len(matches) != 1:
    raise ValueError(f"missing unique trough station at depth {target}")
if not faces:
    raise ValueError("no body faces matched the contact predicate")
if abs(measured[key] - target) > 0.2:
    raise ValueError(f"reference {key} {measured[key]:.3f} mm != target {target}")
if body_cut.Shape.isNull() or body_cut.Shape.Volume < 1.0:
    raise ValueError("boolean cut failed")
if body_fused.Shape.isNull() or body_fused.Shape.Volume < 1.0:
    raise ValueError("upper floor filler fuse failed")
if body_holed.Shape.isNull() or body_holed.Shape.Volume < 1.0:
    raise ValueError("cord through-hole cut failed")
if stale:
    raise ValueError(f"document failed recompute: {stale}")
if abs(measured_depth - published) > 0.25:
    raise ValueError( f"{contact_id} region depth {measured_depth} mm != published {published} mm" )
```
