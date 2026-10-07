# Metolius Simulator 3D — selectable app asset

Photo-referenced reconstruction of the Simulator 3D reference family. It does not claim an exact production revision or scan accuracy.

## Contents and coordinates

The main `.blend`, authored with Blender 4.2.0, contains 32 mesh objects: `board_body` and 31 selectable holds. The editable, higher-resolution Blender source is in `source/`. Four separate preview renders show the front, back, oblique view, and jug close-up.

The main mesh uses 521,340 triangles; the editable source uses 1,699,938. `hold-map.json` supplies machine-readable IDs and dimensions. `validation.json` and `glb-validation.json` record the geometry and export checks. Both object names and mesh datablock names use the IDs below.

- Coordinates: Z up, X across the width, front toward negative Y, back plane at Y = 0.
- Units: meters, with unit scale 1. Overall width 0.711 m and height 0.222 m; reconstructed maximum depth approximately 0.09628 m.
- Object transforms: zero location and rotation, unit scale. Geometry is stored in the shared board coordinate system.
- Saved app scene: meshes only, with no cords, markers, separate hardware, lights, cameras, or environment objects.

GLB export uses the standard glTF conversion from Blender's Z-up coordinates to Y-up. The same hold IDs identify exported meshes and nodes; select by name rather than numeric node index.

## Selection and highlighting

Find a hold mesh by its exact name below and replace that mesh's material to highlight it. Each ID represents one usable hold surface, including its assigned rim, rather than a solid hold volume. `board_body` is not selectable.

The meshes are disjoint surface patches partitioned from one casting. The assembled shell is closed; individual hold patches are open, and `board_body` alone has gaps where they fit. Keep all 32 meshes together for normal display. These surface patches are intended for display, picking, and highlighting; use separate collision geometry if the app needs solid colliders. Custom normals are copied across shared boundaries to retain smooth shading; preserve imported normals when supported.

Left and right are defined while facing the front of the board. Numbers follow the manufacturer's diagram. The 31 objects comprise 24 front recesses (16 finger pockets and 8 edges), 3 jugs, and 4 slopers.

| Number | Exact mesh names | Grip | Manufacturer dimension |
|---|---|---|---|
| 1 | `hold_01_left`, `hold_01_right` | Outer jug | Unspecified |
| 2 | `hold_02_left`, `hold_02_right` | Flat sloper | 55 mm |
| 3 | `hold_03_left`, `hold_03_right` | Round sloper | 65 mm |
| 4 | `hold_04_left`, `hold_04_right` | Three-finger pocket | 30 mm |
| 5 | `hold_05_left`, `hold_05_right` | Edge | 25 mm |
| 6 | `hold_06_left`, `hold_06_right` | Edge | 19 mm |
| 7 | `hold_07_left`, `hold_07_right` | Edge | 36 mm |
| 8 | `hold_08_left`, `hold_08_right` | Three-finger pocket | 15 mm |
| 9 | `hold_09_left`, `hold_09_right` | Three-finger pocket | 35 mm |
| 10 | `hold_10_left`, `hold_10_right` | Three-finger pocket | 17 mm |
| 11 | `hold_11_left`, `hold_11_right` | Edge | 14 mm |
| 12 | `hold_12_left`, `hold_12_right` | Two-finger pocket | 30 mm |
| 13 | `hold_13_left`, `hold_13_right` | Two-finger pocket | 14 mm |
| 14 | `hold_14_center` | Center jug | Unspecified |
| 15 | `hold_15_center` | Three-finger pocket | 50 mm |
| 16 | `hold_16_center` | Three-finger pocket | 37 mm |
| 17 | `hold_17_center` | Two-finger pocket | 28 mm |
| 18 | `hold_18_center` | Two-finger pocket | 32 mm |

Sloper dimensions are nominal manufacturer grip dimensions, not perpendicular recess depths. Jug depths are not published and remain unset in descriptive metadata. The shallow numbered holds, including 11 and 13, are selectable. Incidental grooves, ledges, and mounting bores have no separate hold IDs.

## Materials and fidelity

A simple PBR material uses original, generated per-vertex resin color. The cobalt/ivory pour is a stylized finish, not a match to one particular physical unit. No external textures or reference photographs are embedded. Logos and decals are omitted from the reconstruction. Retain the vertex-color material input during import to preserve the default finish. The original generated color data is dedicated to the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

Published overall size and grip dimensions guide this reconstruction. Hidden jug scoop dimensions, local fillets, mounting-bore positions and diameters, rear relief, maximum casting depth, and selectable patch boundaries are estimates derived from photographs or modeling judgment. The asset is for visual app use, not a manufacturing or load-bearing specification.

## References

- [Metolius Simulator Training Board](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board) — product identity, overall size, and manufacturer diagram.
- [Metolius numbered hold and depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/sim-num-dep_c543622d-e670-4601-8d4d-792cc8e46dea.jpg?v=1762201085&width=1600) — hold numbering, grip types, and dimensions.
- [Geartrade reference listing](https://geartrade.com/products/metolius-simulator-3d-training-board-1594396) — supplemental product photographs.
- [Ricardo reference listing](https://www.ricardo.ch/de/a/metolius-simulator-3d-hangboard-1242445644/) — supplemental product photographs.
- [Dicks Climbing reference listing](https://www.dicksclimbing.com/products/metolius-simulator-3d-board) — supplemental product photographs.

Reference photographs are linked only and are not redistributed. Metolius trademarks and reference photographs remain the property of their respective owners; the CC0 dedication above covers only the original generated color data.
