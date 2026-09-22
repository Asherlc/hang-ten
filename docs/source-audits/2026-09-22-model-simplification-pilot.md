# Model simplification pilot — 2026-09-22

## Scope

Authorized in chat after the simplification assessment: compare conservative and leaner versions of Metolius Simulator 3D, Metolius Wood Grips II Deluxe, and Lattice MXEdge Lift Small. Use the committed PR #457 model bytes at `ef07a5fb04104d5f0a5ed3accc4c6ae918e02529`. Do not change the other 37 model packages, any board metadata, logical contact IDs, suspension metadata, or material/texture image bytes. These are review candidates, not a global visual redesign or native-app approval.

## Selected geometry

| Model | Before triangles | Selected triangles |
|---|---:|---:|
| Simulator 3D | 512024 | 90386 |
| Wood Grips II Deluxe | 63522 | 18082 |
| MXEdge Lift Small | 378232 | 19456 |

The selected meshes use 127924 triangles instead of 953778 (86.6% reduction). They keep the same node identities and geometrically exact per-node boundary edge positions. Attribute-aware meshoptimizer v1.0 simplification chooses existing vertices only. No hole detection, image tracing, geometric feature inference, or contact remapping occurs. Body and contact extrema are locked; the descriptor is recompiled from reopened referenced triangles.

Constant texture sampling is collapsed to one UV coordinate only after confirming every referenced embedded image is constant and the st graph uses supported repeat/clamp UV readers. This removes redundant per-triangle UV islands without changing image bytes or sampled color. Other UV seams remain protected. The existing one-pixel black Wood Grips texture is intentionally retained; neutral review shading does not simulate that native material.

The generic 35-degree normal-smoothing candidate for the machined wood board was rejected after rendered review. The selected wood version preserves source normal attributes, permits attribute-aware collapses across redundant normal seams only for its verified constant-texture graph, and gives genuinely axis-aligned planar faces flat normals. The Simulator preserves its existing organic normal field, with a tighter body-specific error limit after a looser version showed approximately 1 mm sampled deviation. The Lattice uses crease-aware normal treatment. An initial Lattice reduction was rejected for nine new nonmanifold edges. The topology guard locks the original one-ring of a rejected collapse and retries from the untouched source; two retries kept all source topology invariants with the same triangle budget. No blanket smoothing or all-quad conversion is claimed.

## Verification contract

- Reopen actual USDZs and recompile their descriptors; preserve contact dictionaries, bounds, nodes and all board.json bytes.
- Compare all boundary edge coordinates, connected component counts, Euler characteristics, nonmanifold-edge counts and degenerate-face counts per node.
- Sample 1800 points per mesh node in each direction; find actual nearest triangle distances within the corresponding logical node, not a different nearby/back surface. The maximum sampled distance must be at most 0.5 mm. This is a sampled check, not an exact Hausdorff bound.
- Recheck former mounting holes on Simulator and Wood Grips using five rays at every audited mounting location. Keep actual finger and suspension apertures.
- Review matched front, rear and oblique neutral CPU renders. These are not native SceneKit screenshots, and do not certify native picking or performance.
- Verify the full root-layer text fingerprint against the locally reviewed candidate before publishing; preserve all embedded secondary resource bytes.

## Delivery identity

Binary USDC serialization is not guaranteed byte-deterministic across separate processes, even with identical exported layer text. Therefore the publication workflow must commit its final USDZs, update the exact-file lock, and build the delivery by COPYING those committed files. Never rerun authoring to make the download. Previews must be bound to these same binaries by SHA-256. The reviewed layer fingerprints in `simplification_pilot.json` guard against publishing a different mesh implementation or geometry.

## Dependencies and limits

The native dependency is the official meshoptimizer v1.0 archive, SHA-256 `30d1c3651986b2074e847b17223a7269c9612ab7f148b944250f81214fed4993`, MIT licensed: https://github.com/zeux/meshoptimizer/releases/tag/v1.0 . USD mesh/normals semantics: https://openusd.org/release/api/class_usd_geom_mesh.html . Python package versions are pinned in `simplification_requirements.txt`.

No native iOS, SceneKit, Workbench or Blender checks are claimed. This pilot does not fix inherited shape inaccuracies, guarantee globally watertight boards, or establish production visual approval. Do not merge automatically.
