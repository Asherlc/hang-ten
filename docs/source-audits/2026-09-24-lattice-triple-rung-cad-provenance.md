# lattice-triple-rung CAD authoring provenance

Date: 2026-09-24

This record preserves the provenance carried by the retired one-off migration
script `Tools/HangboardCAD/migration/author_lattice_triple_rung.py`, which authored
`Hangboards/lattice-triple-rung/lattice-triple-rung.FCStd`. The script was never a build input: the
committed FCStd stands alone, and its embedded `HangTenBoardManifest` is now the
source of `board.json` (`Tools/HangboardCAD/board_manifest.py`). The script was
removed because re-running it would recreate the document without that manifest.

Nothing below is new evidence. The module docstring, recorded constants, inline
notes, and pre-save checks are copied from the script so the trail from
published product facts and the measured Git reference to the authored document
survives. Where the script distinguished PUBLISHED values from MEASURED ones, or
recorded a stated deviation, that wording is kept as written.

## Recovering the script

- Last commit that modified the script: `171f5d2efd62dda4e010abafa3ff2c2ce55927eb`
- Last commit containing the script before its removal: `060eba8ebd6d5ba44ae8becd3a538232d483eaa9`

```sh
git show 060eba8ebd6d5ba44ae8becd3a538232d483eaa9:Tools/HangboardCAD/migration/author_lattice_triple_rung.py
```

The script imported the shared helpers `Tools/HangboardCAD/reference.py`
(`load_reference`, which resolves the approved reference USDZ from Git at the
recorded pre-migration commit) and ran under the pinned FreeCAD interpreter
(for example through `Tools/HangboardCAD/run_freecad.py`), reading extra site
directories such as the one providing `pxr` from `HANGTEN_CAD_PYTHONPATH`.

## Module docstring (verbatim)

```text
One-off migration: author Hangboards/lattice-triple-rung/lattice-triple-rung.FCStd natively.

This script is a MIGRATION TOOL, not a build input. The saved FCStd must stand
alone: the shared compiler never runs this file, and nothing here is required to
rebuild the published runtime asset.

Provenance of every number written into the document:

* Overall size 550 x 130 x 50 mm and the three grip depths (45, 20, 10 mm) come
  from ``Hangboards/lattice-triple-rung/board.json`` (``dimensions`` and each
  contact's ``depth.range``). These are PUBLISHED product facts.
* The cross-section outline is MEASURED from the approved model reference
  ``Hangboards/lattice-triple-rung/assets/primary.usdz``: the ordered boundary
  loop of the body's end cap, converted to native FreeCAD millimetres
  ``(x, y, z) = (X, -Z, Y)``. It is a measured approximation of a display mesh,
  not recovered manufacturing data.
* Contact band boundaries are the measured endpoints of each contact node's own
  swept polyline, snapped to the nearest measured profile vertex.
* Reduction from 267 measured points to the authored vertex set keeps every
  vertex whose removal would deviate the outline by more than 0.2 mm. The
  achieved maximum deviation is recorded in the provenance JSON.

The authored sketch is deliberately a closed polyline of measured vertices with
explicit dimensional constraints on the published facts, so that editing a
dimension in the FreeCAD GUI changes the exported surface. Nothing here is
presented as recovered parametric design history.
```

## Recorded constants

```python
PACKAGE = "lattice-triple-rung"
# The approved reference is read from Git at the recorded pre-migration commit,
# never from the live runtime path: the shared compiler overwrites that path
# with this migration's own output, so reading it there would silently make the
# migration compare against itself.
REFERENCE_PATH = f"Hangboards/{PACKAGE}/assets/primary.usdz"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
BODY_PRIM = "/root/LatticeBody/LatticeBody_editable_surface_001"
BAND_PRIMS = {
    "edge-10": "/root/edge_10/edge_10_editable_surface_001",
    "edge-20": "/root/edge_20/edge_20_editable_surface_001",
    "edge-45": "/root/edge_45/edge_45_editable_surface_001",
}
REDUCTION_TOLERANCE_MM = 0.2
# Published facts from board.json; asserted against the measured reference.
PUBLISHED_MM = {"width": 550.0, "height": 130.0, "depth": 50.0}
GRIP_DEPTH_MM = {"edge-45": 45.0, "edge-20": 20.0, "edge-10": 10.0}
MATERIAL_NAME = "neutral_tulipwood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0
```

## Inline authoring notes

- `_reference_texture()`:
  - Docstring: Extract the approved display texture from the reference package.
- `main()`:
  - The approved display material travels with the source: the texture image is embedded in the FCStd so the document is self-contained and the compiler never needs the previous runtime asset.
  - The profile lives on the body YZ plane with an explicit, fully determined frame: sketch-local (u, v) maps to native (0, u, v), i.e. local +X is native +Y (depth) and local +Y is native +Z (height). An explicit placement avoids depending on the body origin's own axis directions. Pinned-build quirk, verified in this script's own assertions: a Sketcher DistanceX/DistanceY between a point and the sketch axis solves to the NEGATED value (x = -value, y = -value) regardless of the initial geometry. The authored outline therefore stores negated local coordinates with positive driving dimensions, and the sketch frame negates them back. The pad's world bounding box is asserted below, so any change in that behaviour fails the build instead of silently mirroring the board.
  - Every authored vertex carries its measured coordinate as an explicit driving dimension against the sketch origin. The profile is therefore fully constrained (no solver freedom) and every vertex stays individually editable.
  - A contact region is the extrusion of its run of profile segments, bound to the sketch's own edges. Sketch edges keep their identity when a driving dimension changes, so the binding survives profile edits. Binding to the pad's FACES instead was tried and rejected: FreeCAD lost the face element map after a profile edit and the unrelated contact regions silently moved to different faces. That failure is covered by the native checks below.
  - The band is the same extrusion as the body, so its length follows the pad through a native expression rather than a copied constant.
  - The CAD document is the source of truth for hold geometry: author the contact band's front-plane (XZ) outline so the compiler emits it as the descriptor region rather than deriving it from the exported mesh.
  - The shared material is declared once, on the body node; the contacts carry the same MaterialName and inherit the embedded texture at build time.

## Checks the script enforced before saving

Each guard below raised `ValueError` and aborted authoring (source lines verbatim).

```python
if len(loop) != len(adjacency):
    raise ValueError("cap outline is not one closed loop")
if len(names) != 1:
    raise ValueError(f"expected exactly one reference texture, found {names}")
if abs(measured[key] - published) > 0.05:
    raise ValueError(f"measured {key} {measured[key]:.3f} disagrees with published {published}")
if any(indices[i + 1] - indices[i] != 1 for i in range(len(indices) - 1)):
    raise ValueError(f"{contact_id} contact band is not a contiguous profile run")
if abs(measured_depth - GRIP_DEPTH_MM[contact_id]) > 0.05:
    raise ValueError( f"{contact_id} measured grip depth {measured_depth:.3f} disagrees with published " f"{GRIP_DEPTH_MM[contact_id]}" )
if min(vertex[2] for vertex in vertices) < -1e-6:
    raise ValueError("profile height must be non-negative for the authored sketch")
if (resolved.multVec(local) - expected).Length > 1e-9:
    raise ValueError("profile sketch frame does not map local (u, v) to native (0, -u - shift, -v)")
if abs(measured_axis - target) > 0.05:
    raise ValueError(f"{label} dimension {measured_axis:.3f} disagrees with published {target}")
if sketch.solve() and not sketch.FullyConstrained:
    raise ValueError("authored profile sketch is not fully constrained")
if not sketch.FullyConstrained:
    raise ValueError("authored profile sketch is not fully constrained")
if not run:
    raise ValueError(f"{contact_id} contact band selected no profile edges")
if any(abs(a - b) > 0.05 for a, b in zip(actual_box, expected_box)):
    raise ValueError(f"authored body frame {actual_box} does not match native frame {expected_box}")
if abs(span - GRIP_DEPTH_MM[contact_id]) > 0.1:
    raise ValueError(f"{contact_id} authored depth {span} disagrees with published {GRIP_DEPTH_MM[contact_id]}")
```
