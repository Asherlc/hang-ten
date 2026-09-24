# Mounting-bore removal — 2026-09-22

## Status: historical record (retired 2026-09-24)

This one-time repair was applied in commit
`e89ad99` (`fix(models): remove 106 mounting bores from 13 shipped models`).
Its reviewed repair regions are retained unchanged in
[`2026-09-22-mounting-bore-repairs.json`](2026-09-22-mounting-bore-repairs.json)
(formerly `Tools/HangboardModels/mounting_bore_repairs.json`). The repair-time
verifier, `Tools/HangboardModels/verify_mounting_bores.py`, was removed on
2026-09-24 because it can no longer describe the committed catalogue: its
inventory is a snapshot of the 40 models at source commit `c9daec6`, and since
then six models were added (`frictitious-doormount-pro-7`,
`frictitious-megalith`, `trango-rock-prodigy-forge`,
`trango-rock-prodigy-natural`, `zlagboard-evo`, `zlagboard-pro`) and the five
FreeCAD-backed packages (`lattice-triple-rung`, `captain-fingerfood-pocket`,
`lattice-mxedge-lift-large`, `lattice-mxedge-lift-small`,
`metolius-rock-rings-3d`) were rebuilt from their CAD sources, which changed
their model and descriptor bytes (and, for three of them, the generated
`board.json` bytes).
`lattice-triple-rung` was one of the 13 repaired models; its current asset is
compiled from the FCStd, not derived from the repaired mesh, so the repair
region no longer applies to it. The other 12 repaired models still passed the
verifier's per-model checks (descriptor rebuilt from the reopened USDZ,
five closure rays per bore) at `db04185`. Refreshing the inventory
would record hashes this audit never reviewed, so it was retired instead.
Committed model bytes are now governed by the model delivery lock
(`scripts/verify-model-delivery.py`, enforced in CI by
`Tools/HangboardModels/tests/test_model_delivery_alignment.py`) and, for
CAD-backed packages, by the CAD reproducibility check.

Read the retired verifier with
`git show db04185b4541ef469d0a2e8ca9b5eb87bfa53253:Tools/HangboardModels/verify_mounting_bores.py`.
The repair program, `Tools/HangboardModels/remove_mounting_bores.py`, is still
in the repository (other model tools share its mesh helpers); it only accepts
the hash-bound source revision, so it runs only against a checkout of
`c9daec6`.

## Scope and source boundary

Reviewed all 40 shipped USDZ models at commit
`c9daec6a0d1e5c517960daba5e9b3e9f9f28b074`. Thirteen models contain
mounting bores or ineffective mounting-hole caps. Repair 106 explicitly
identified mounting locations. Leave the other 27 models and their descriptors
byte-for-byte unchanged. Retain every `board.json` byte, logical contact ID,
contact-node binding, and embedded texture image. Archived delivery/evidence
models are immutable provenance, not alternate runtime assets, and are unchanged.

These are display-only omissions. The physical boards still have mounting holes.
The cylinder centres and radii in `2026-09-22-mounting-bore-repairs.json`
are reviewed repair regions in the existing mesh frame, not manufacturer CAD
measurements. The operation does not trace or infer geometry from images.

## Repaired models

| Package | Mounting locations |
| --- | ---: |
| `metolius-simulator-3d` | 8 |
| `beastmaker-2000` | 6 |
| `lattice-triple-rung` | 6 |
| `metolius-prime-rib` | 4 |
| `metolius-project` | 8 |
| `metolius-wood-grips-deluxe-ii` | 6 |
| `moon-armstrong` | 8 |
| `target10a-linebreaker-base` | 6 |
| `the-hangboard` | 8 |
| `trango-rock-prodigy-training-center` | 8 |
| `metolius-climbers-edge` | 8 |
| `metolius-contact` | 10 |
| `soill-training-tiles` | 20 |

## What was repaired

The Simulator's eight omission discs sat in front of the board instead of
closing its bore walls. Remove the `mounting_hardware_omission_caps_001` mesh,
excise the bore-wall triangles inside each explicit region, and triangulate
both mouths at the existing surrounding surface. Apply equivalent repairs to
the other listed models. Remove obsolete cap objects from the Simulator,
Climber's Edge, Contact, and The Hangboard. On Training Tiles, remove only the
20 disc components from the combined omission mesh; retain its two pre-existing
wordmark covers. Never bind a new hardware/contact identity.

The local patch uses the actual 3D rim, retains its vertices, copies adjacent
material/UV data, and refreshes obsolete bore-wall normals locally. Training
Tiles' thin, folded junctions use an explicitly enabled 3D minimum-area
triangulation. Contact's pre-existing overlapping rear stencils require an
explicit planar rear patch at its original rear plane. Neither operation is a
runtime importer repair or an automatic hole detector. The package compiler
remains transport-only.

## Openings deliberately retained

Preserve finger pockets, open-backed finger windows, and cord/attachment
passages. In particular, the four large lower pocket windows on the Rock
Prodigy Training Center are not mounting bores: the [manufacturer photograph](https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750&width=1946)
shows them separately from its eight mounting locations, and the
[manufacturer mounting guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Mounting_Instructions_no_screws_v2.pdf?v=1587749856)
requires eight board screws. Both were rechecked on 2026-09-22. Preserve the
larger finger openings on Beastmaker, Moon, Mammut, Training Tiles and Pivot,
and the portable boards' suspension passages. Existing evidence and product
identities are retained in `2026-09-15-hangboard-collection-model-imports.md`
and `2026-09-13-model-hangboard-cord-audit.md`.

## Reproduction and verification

As run at repair time (historical; see the status note above), in an isolated
Python 3.13 environment:

```sh
python -m pip install -r Tools/HangboardModels/mounting_bore_requirements.txt
python Tools/HangboardModels/remove_mounting_bores.py \
  --root SOURCE_CHECKOUT \
  --manifest docs/source-audits/2026-09-22-mounting-bore-repairs.json \
  --output REPAIR_OUTPUT
```

The source hashes intentionally reject already-repaired or changed input.
Never overwrite the retained inputs. Promote only reviewed exports and their
recompiled descriptors. The promoted catalogue was verified with the
since-retired `verify_mounting_bores.py` (read it at `db04185`, above):

```sh
OPENBLAS_NUM_THREADS=1 python Tools/HangboardModels/verify_mounting_bores.py \
  --root REPAIRED_CHECKOUT --source-root SOURCE_CHECKOUT \
  --manifest Tools/HangboardModels/mounting_bore_repairs.json \
  --report verification.json
```

Verification reopens the actual USDZ, reconstructs the descriptor using the
existing compiler, checks uncompressed 64-byte-aligned USDZ members, and tests
five rays per mounting location (530 rays). Rays require front and rear
surfaces and respect each USD mesh's existing handedness and double-sided
setting. A source comparison proves retained triangles outside the explicitly
removed regions, contact-node bindings, and embedded image bytes remain
unchanged. The inventory gate also checks untouched models and every board
metadata hash. Update the two legacy cap verifiers and three package-inventory
assertions to require the repaired body rather than floating cap nodes.

Neutral diagnostic front, rear and oblique renders were made directly from
USD triangles with a CPU depth-buffer renderer; no Blender or generated imagery
was used. These are geometry review renders, not native iOS screenshots.
The exported assets still carry their original materials and texture images.
The local model-tool suite passed (34 tests, 24 subtests; two existing
Blender-dependent tests skipped). The committed machine-readable verification
report records the promoted hashes and catalogue checks. Native application
build/picking tests are separate CI gates; CPU inspection does not claim to
replace those tests. This audit is not a claim that entire original meshes
are globally watertight: real openings and existing contact/body partitions
are retained.
