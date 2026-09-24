# Metolius Prime Rib: native FreeCAD source audit (2026-09-24)

This file records the provenance of every authored value in
`Hangboards/metolius-prime-rib/metolius-prime-rib.FCStd`. The authoring script is
`Tools/HangboardCAD/migration/author_metolius_prime_rib.py`. `board.json` is
unchanged. The document is a measured, vector-authored approximation of the
approved display mesh. It is not recovered manufacturing geometry, and it does
not support a product-accuracy or load-bearing claim.

## Sources consulted

| Source | Reachable | Used for |
| --- | --- | --- |
| https://www.metoliusclimbing.com/products/prime-rib | yes (HTTP 200, 2026-09-24) | "Specs & Details": *Edges Depth: 38 mm (1.49") 23 mm (0.90") 15 mm (0.59")*; *Size: 20" x 4.2" x 1.5" (50.8 cm x 10.66 cm x 3.8 cm)*; *Can be mounted with four screws (included)* |
| https://www.metoliusclimbing.com/products/prime-rib.json | yes | product id 15386925924425, SKU WOOD006, one image |
| https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Prime-Rib-board.jpg?v=1759459292 | yes | visual cross-check only: three full-width rungs labelled 38 / 23 / 15 mm top to bottom, four screw holes, rounded ends. No dimensions were taken from the photo. |
| Pre-migration reference `Hangboards/metolius-prime-rib/assets/primary.usdz` at commit `6b828e15` (`Tools/HangboardCAD/reference.py`), SHA-256 `ddfb6f8f…8026` | yes (Git LFS) | cross-section primitives, contact runs, end round-over, material |
| `Hangboards/metolius-prime-rib/board.json` | yes | contact ids, names and depths (38 / 23 / 15 mm), `dimensions` "20 × 4.2 × 1.5 in" |

## Field mappings

Native frame: millimetres, +X right, +Z up, front −Y. Sketch local `(u, v)` =
native `(0, −u, v)`.

| Authored field | Value | Source |
| --- | --- | --- |
| Pad `Length` (board width) | 508.0 | manufacturer 20" (board.json) |
| `BoardHeight` | 106.68 | manufacturer 4.2" |
| `BoardThickness` | 38.1 | manufacturer 1.5" |
| `Edge15Depth`, `Edge23Depth` | 15, 23 | manufacturer edge depths (board.json `depth.range`) |
| edge-38 depth | 38.1 (full thickness) | manufacturer 38 mm (1.49") ≈ 1.5" thickness; the reference mesh also spans 38.1. The compiler's published-depth gate allows 0.25 mm. |
| `Edge15LedgeHeight` 18, `Edge15SlotHeight` 21, `MiddleRungThickness` 18, `Edge23SlotHeight` 26 | mm | measured: reference end-cap loop |
| 12 radii (`BackBottomRadius` 2, `FrontBottomRadius` 2, `Edge15LipRadius` 2.2, `Edge15SlotFloor/CeilingFilletRadius` 3.4, `MiddleRungNoseRadius` 2.6, `Edge23LipRadius` 3.5, `Edge23SlotFloor/CeilingFilletRadius` 6, `TopRungNoseRadius` 4, `CrestRadius` 7.5, `BackTopRadius` 2) | mm | measured: reference end-cap loop, exact circle fits |
| Top-surface Beziers: `RearTopHeight` 103, `TopDipJoinDepth` 6, `TopDipJoinHeight` 103, handles 1.1 / 1.5 / 9.0 / 1.5 (drop) / 6.6 | mm | measured: least-squares cubic Bezier fit to the reference top-surface samples (residual 6e-5 mm) |
| `EndRoundover.Radius` | 1.2 | measured: reference end stations x = 252.8…254 follow 1.2·sin θ |
| Contact runs | edge-15: bottom-rung front, lip, ledge, floor fillet. edge-23: middle-rung front, lip, ledge, floor fillet. edge-38: top-rung front, crest, both top Beziers, rear top round | measured: reference contact nodes' (y, z) extents, asserted to 0.01 mm |
| Contact X span | ±252.8 (`Pad.Length − 2·EndRoundover.Radius`) | measured: reference contact nodes |
| `HangTenHoldOutline` | front-plane rectangle of each run's extent | derived from the authored run |
| Node IDs | `body_mesh_001`, `edge_{15,23,38}_mesh_001` | kept from the reference, which `test_approved_board_packages.py` pins |
| Material `prime_rib_neutral_wood`, roughness 0.58, metallic 0, texture `prime-rib-neutral-wood-64199871cb68.png` | — | carried over from the reference USDZ. Base colour `0.72,0.55,0.36` is a stated display choice, as on the pilot. |

## Deliberately not authored

- **The four mounting bores** (x = ±223 mm, z = 28.5 / 70 mm, r = 5.5 mm).
  The repository's hardware-omission policy covers them
  (`Tools/HangboardModels/mounting_bore_repairs.json`). The reference still
  carries their flat cap patches, and the native surface is continuous there.

## Verification evidence

- Reference fit: all 291 reference end-cap profile vertices lie within
  0.00006 mm of the authored sketch (the script's limit is 0.01 mm).
- Native checks (`Tools/HangboardCAD/tests/prime_rib_native_source_checks.py`)
  pass, including an `Edge23Depth` 23 → 26 mm edit that moves only edge-23.
- Compile (`compile_board.py`): published-depth gate 15.0 / 23.0 / 38.1 mm.
  Descriptor `facePlaneAABB` matches the reference to within 4e-8
  (normalized). `modelBounds` are identical.
- `compare_exports` against the reference, two-way sampled, limit 0.5 mm:
  - candidate → reference: worst 0.0782 mm over 336,912 samples.
  - reference → candidate: worst 0.0671 mm over 55,020 samples.
  - p99 is 0.014 mm in both directions.
  - Per contact: edge-15 0.0026 mm, edge-23 0.0046 mm, edge-38 0.078 mm.
  The residual is tessellation chord error at the 0.08 mm deflection. At its
  default `--chunk 2048`, the tool's reverse pass was OOM-killed on this
  56k-triangle mesh, so the same functions were run at a smaller chunk; the
  tool now has a `--chunk` option for that.
- Preview: `docs/pr-screenshots/metolius-prime-rib/native-vs-reference-preview.png`.
  This is a CPU lambert render, not a SceneKit screenshot.
- Not run: in-app simulator validation (no macOS here), the Hydra `usdrecord`
  render (the usd-core wheel has no Storm imaging), and suspension. The board
  has no suspension metadata.
