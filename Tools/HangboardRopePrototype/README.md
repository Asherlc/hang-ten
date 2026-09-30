# Mini Bar Bullet rope contact experiment

The separate [sparse contact screen](sparse_contact_screen.py) targets the
current coupled live solver's frozen triangle-contact QP. Its
[30 September audit](../../docs/source-audits/2026-09-30-live-sparse-primal-contact.md)
records a numerical pass and a performance rejection. It uses the corrected
CAD/channel workload and does not reuse the surrogate below.

**Historical experiment (2026-09-27):** These runs used the earlier USDZ
whose body had no local holes; the prototype pinned inferred exterior guide
points. The current CAD body has two connected channels, one per end, and
uses a different model SHA-256. The eight runs below describe a
**solid-bar surrogate**, not the corrected Mini Bar. Their zero-of-eight
outcome does not establish that Bullet would fail on the actual board. See the
[reusable CAD cord authoring guide](../../docs/HANGBOARD_CORD_AUTHORING.md).

This is an offline experiment for the Lattice Mini Bar. It does not change the
app, FreeCAD source, USDZ, descriptor, or suspension sidecar. The cord remains
transient and unselectable in the product. The experiment asks whether a rope
whose anchor, two strand positions, and outside winding are specified can
settle against the board without authored contact coordinates.

## Inputs and provenance

- Historical exterior-loop fixture: `Tools/HangboardRopePrototype/fixtures/exterior-mini-bar-2026-09-26/`.
  Its descriptor and suspension sidecar are preserved from commit `f559563f7`;
  the USDZ is the matching 32,354-byte staged asset with the hash below. This
  fixture is only for reproducing the rejected historical experiment.
- USDZ SHA-256: `5f6744d3aeede10cc2b3c5f6f9dc19df1bb985c94991192ec8f2044c32932c46`.
  `case.py` refuses a mismatch with either the descriptor or suspension sidecar.
- Body collider source: the `mini_bar_body` triangles from the USDZ, with the
  USD importer transform applied. The exported case contains 592 vertices and
  584 triangles. The model is in metres.
- Suspension inputs: the two sidecar branch passage pairs, 2 mm cord radius,
  0.75 m original length estimate per loop, shared bounds-relative anchor, and
  four canonical pose transforms. `wrap_side=opposite-anchor` states the
  approved outside winding. No intermediate contact positions are specified.
- Bullet source: official [Bullet Physics 3.25](https://github.com/bulletphysics/bullet3/tree/3.25),
  resolved commit `2c204c49e56ed15ec5fcfa71d199ab6d6570b3f5`, zlib license
  (`LICENSE.txt`). JSON parser: [nlohmann/json v3.12.0](https://github.com/nlohmann/json/releases/tag/v3.12.0),
  single-header SHA-256 `aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63`.

## Reproduce

From the repository root, with generated files kept under `.context/frantic-kiwi`:

```sh
python3 -m venv .context/frantic-kiwi/rope-venv
.context/frantic-kiwi/rope-venv/bin/pip install -r Tools/HangboardRopePrototype/requirements.txt
git clone --branch 3.25 --depth 1 https://github.com/bulletphysics/bullet3.git .context/frantic-kiwi/bullet3-3.25
curl -L https://github.com/nlohmann/json/releases/download/v3.12.0/json.hpp -o .context/frantic-kiwi/json-v3.12.0.hpp
cmake -S .context/frantic-kiwi/bullet3-3.25 -B .context/frantic-kiwi/bullet-build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_BULLET2_DEMOS=OFF -DBUILD_EXTRAS=OFF -DBUILD_UNIT_TESTS=OFF -DBUILD_SHARED_LIBS=OFF -DUSE_DOUBLE_PRECISION=ON
cmake --build .context/frantic-kiwi/bullet-build --target BulletSoftBody BulletDynamics BulletCollision LinearMath -j 8
cmake -S Tools/HangboardRopePrototype -B .context/frantic-kiwi/rope-build -DBULLET_SOURCE="$PWD/.context/frantic-kiwi/bullet3-3.25" -DBULLET_BUILD="$PWD/.context/frantic-kiwi/bullet-build" -DJSON_HEADER_DIR="$PWD/.context/frantic-kiwi"
cmake --build .context/frantic-kiwi/rope-build -j 8
.context/frantic-kiwi/rope-venv/bin/python Tools/HangboardRopePrototype/case.py Tools/HangboardRopePrototype/fixtures/exterior-mini-bar-2026-09-26 .context/frantic-kiwi/rope-case.json
.context/frantic-kiwi/rope-venv/bin/python Tools/HangboardRopePrototype/run_case.py .context/frantic-kiwi/rope-case.json .context/frantic-kiwi/rope-build/rope_solver .context/frantic-kiwi/rope-results --bullet-revision 2c204c49e56ed15ec5fcfa71d199ab6d6570b3f5
.context/frantic-kiwi/rope-venv/bin/python Tools/HangboardRopePrototype/run_case.py .context/frantic-kiwi/rope-case.json .context/frantic-kiwi/rope-build/rope_solver .context/frantic-kiwi/rope-repeat --bullet-revision 2c204c49e56ed15ec5fcfa71d199ab6d6570b3f5
.context/frantic-kiwi/rope-venv/bin/python Tools/HangboardRopePrototype/evaluate.py .context/frantic-kiwi/rope-case.json .context/frantic-kiwi/rope-results --repeat-results .context/frantic-kiwi/rope-repeat
.context/frantic-kiwi/rope-venv/bin/python -m pytest Tools/HangboardRopePrototype/tests -q
```

The output has `manifest.json`, `report.json`, `findings.md`, and front, side,
and oblique PNGs for every pose and length condition. All eight solver results
remain available even if a condition fails. The `original` condition uses the
unchanged 0.75 m sidecar estimate. The `taut` condition uses the length of a
collision-free seed at one cord radius from the board section; it is an
experimentally derived length and is never written to package metadata.

## Solver and measurement

The board is rigid. Each loop has soft-body chain nodes at no more than 3 mm
seed spacing. The shared overhead point and two declared strand guide points
are pinned. Gravity is `(0,-9.81,0)` m/s². Bullet uses 1 mm sparse signed
distance voxels, a 0.25 mm extra collision margin around the 2 mm cord,
30 position iterations, damping `0.08`, friction `0.5`, a 1/240 s step,
and at most 3000 steps. It stops if the 120-step displacement is under 0.02 mm
after at least 480 steps.

Bullet's soft-body `SDF_RS` path evaluates signed distance only for convex
collision shapes in [its implementation](https://github.com/bulletphysics/bullet3/blob/3.25/src/BulletSoftBody/btSparseSDF.h).
The experiment therefore collides against a convex hull of the exact body
vertices. That hull spans the Mini Bar's recessed grip profile, so a successful
solve against it would still need exact surface validation. The evaluator uses
the original USDZ triangles for its segment and point distances. The mesh has
open, duplicated boundary edges, so local nearest-face orientation supplies
the penetration sign; this is less reliable deep inside the shape than a
closed solid mesh.

## Findings (2026-09-27)

For the provisional solid-bar surrogate, the synthetic round-bar test passed outside winding, tube contact, separate
loops, fixed guides, and repeatability. On the real Mini Bar, all eight fresh
conditions reproduced in an independent second run, but **zero of eight met
the exact mesh acceptance criteria**. Six did not converge within 3000 steps.
The ergonomic jug taut condition settled but its maximum expected contact gap
was 6.1 mm; the limit is 1 mm. The edge 20 taut gap was 11.2 mm and it did
not converge. The original 0.75 m estimate was slack relative to the taut
estimate and gave visibly hanging spans. See the generated side PNGs and
`report.json` for each pose and loop.

These runs cannot support a decision to replace the product cord renderer.
The CAD first needs the actual passage topology represented. The simulator
then needs passage constraints and a collider that handles that geometry.
