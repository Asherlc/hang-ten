# Imported model packages source audit

Reviewed 2026-09-10. This audit covers the Task 3 promotion decision for the
four supplied archives recorded by
`.context/import-hangboard-model-packages/source-manifest.json` (SHA-256
`ef6bcffdb875398ab705082a63d91194a76a1f589f72ce9fbb7806b6e360eec9`).
Only YY Vertical Baguette Evo and Nature Climbing Stone Hanger passed the
required conversion boundary and are promoted. The model is display geometry,
not manufacturing CAD or a source for training prescriptions.

## Source archives and disposition

| Candidate | Supplied archive SHA-256 | Disposition |
| --- | --- | --- |
| YY Vertical Baguette Evo | `e74609c64e65030c5a1011dee64e6cc6b4166d99821614929eaf391c97d5e92f` | Promoted over the existing `yy.baguette-evo` raster presentations. |
| Nature Climbing Stone Hanger | `6519f4881f5abadbaa8e86873aaedafece99774444f9c995a396230927b5afb0` | Promoted as the new, distinct `nature.stone-hanger` package selected by the user. |
| Metolius Simulator 3D | `a49df1d76caaad2aa1e5304866b8b8638b9fd048a89a456d6ef080d86bade409` | Blocked; the clean USDZ reimport reports `board_body_001` has no image material. `Hangboards/metolius-simulator-3d` is unchanged. |
| So iLL Training Tiles | `fb61690aebb3b2906ef444f84818893dca68d307a3eca85727cc818d719ef3ee` | Blocked; the explicit mapping leaves `top-jug-left`, `top-jug-right`, `top-pocket-inner-left`, and `top-pocket-inner-right` unmapped. `Hangboards/soill-training-tiles` is unchanged. |

The blocker reports are retained at
`.context/import-hangboard-model-packages/reports/metolius-import.json`
(`9becf3e39163467743d2125bf6467b70f8b94c043c171ae592d191188c260181`)
and `reports/training-tiles-import.json`
(`062275bf9989364e1a13b00c42dba0f112cd695a648c4b7b3520b179145c1dcd`).
No failed candidate asset was copied into a board package.

## YY Vertical Baguette Evo

The exact revision is the round Baguette Evo Turn & Pull version, not the older
rectangular La Baguette or the wall-mounted VerticalBoard Evo. Manufacturer
identity, the 520 × 50 × 50 mm envelope, rubberwood material, paired edge
depths, central edge depths, and rounded option are mapped from the retained
package README and its cited [manufacturer product page](https://www.yyvertical.com/en/products/baguette-evo).
The retained README records that public sources do not establish exact machining
profiles, pocket widths, fillets, or bore dimensions.

Source and conversion evidence:

| Retained path | SHA-256 | Use |
| --- | --- | --- |
| `.context/import-hangboard-model-packages/source-evidence/baguette-evo/YY-Vertical-Baguette-Evo/README.md` | `db31f96b3634ba39c5241b648feb0bc8e8485e4788ffb9ed288e4c9abfac7b73` | Revision identity, physical facts, evidence limits, and manufacturer URL. |
| `.context/import-hangboard-model-packages/source-evidence/baguette-evo/YY-Vertical-Baguette-Evo/hold-mapping.json` | `5004a613a715bbfac910de7bf98df096ad43c56b88152772bdec1e91082e43fb` | Supplied contact inventory and source mesh identities. |
| `.context/import-hangboard-model-packages/source-evidence/baguette-evo/YY-Vertical-Baguette-Evo/validation-report.json` | `b819a543d7d3a057f2a60c7e27999b1e9241308f44bb7d5f6f12e4b4c7f100f3` | Supplied scene validation. |
| `.context/import-hangboard-model-packages/mappings/baguette-evo.json` | `1333f5be7b0cb18ec5e2d3bbc04cfe5e7815a83d8aee8dde105100b949bd329a` | Explicit source-mesh to existing logical-ID mapping. |
| `.context/import-hangboard-model-packages/reports/baguette-evo-verification.json` | `ade279c1f9c5d7080377cbce2fead0b42ecce37591c782fdc9561f9fef3f5aa5` | Actual USDZ clean-reimport, materials, bounds, attachment, and descriptor verification. |

The board retains its pre-migration logical hold order and all logical metadata:
`edge-20-left`, `edge-10-left`, `edge-25-left`, `edge-15-left`,
`edge-15-right`, `edge-25-right`, `edge-10-right`, `edge-20-right`,
`edge-12-left`, `edge-12-right`, `edge-8-left`, `edge-8-right`,
`edge-6-upper`, `edge-6-lower`, `edge-central-30`, `edge-central-25`,
`edge-central-20`, `edge-central-6`, and `rounded-tray`. The explicit mapping
binds the 20 supplied selectable mesh pieces to those 19 logical IDs; the two
rounded pieces intentionally share `rounded-tray`. All five raster presentations
and their PNGs are removed. The sole presentation is the compiled model, with
no `holdGeometry` or raster fallback.

Promoted bytes:

| Path | SHA-256 |
| --- | --- |
| `Hangboards/yy-baguette-evo/assets/primary.usdz` | `e006aad2dfac8e5a3911d1e3e0944830056856d45d757fc76c360e339c76f91b` |
| `Hangboards/yy-baguette-evo/assets/primary.model.json` | `e73f56e2f9ae903583896f88067f03f9f3d9bb1065b8febddd825fcd98b4532c` |

## Nature Climbing Stone Hanger

This is the standard current-gallery Granite Stone Hanger, manufacturer SKU
`STONE_HANGER`, and is distinct from Stoak Board III and both Stone Hanger Mini
packages. The retained package identifies the selected physical facts as
105 × 105 × 35 mm, FSC-certified oak with Norwegian granite, and nominal 20,
15, 10, and 6 mm edges. These facts and the explicit eight-contact technical
drawing inventory map to the retained README and the
[manufacturer product page](https://natureclimbing.com/products/stone-hanger-1).
The manufacturer publishes no numbered revision; `current-gallery-2026-09-11`
is the retained evidence snapshot key, not a claimed product revision date.

Source and conversion evidence:

| Retained path | SHA-256 | Use |
| --- | --- | --- |
| `.context/import-hangboard-model-packages/source-evidence/nature-stone-hanger/nature-stone-hanger/README.md` | `48b908a6eb80bea016c871563ff34d9f5199f59a25caca9170850a4e737f3fae` | Exact product identity, published facts, eight-contact mapping, marker semantics, and fidelity limits. |
| `.context/import-hangboard-model-packages/source-evidence/nature-stone-hanger/nature-stone-hanger/integration.json` | `52302c27055262bc5fb09cfbd5d19010b565f699083e3966c22897fa4c2a721e` | Eight selectable source meshes and two ordered marker records. |
| `.context/import-hangboard-model-packages/source-evidence/nature-stone-hanger/nature-stone-hanger/qa/validation.json` | `7c6e88b1c4c69b078321c5c0076d15445dacd60f0301ce972a14bcf26748bb1a` | Supplied reopened-scene inventory and material validation. |
| `.context/import-hangboard-model-packages/mappings/nature-stone-hanger.json` | `11ae1b516698ee5eec5edd90a1ab96a52b5bbaec23e24c8f55a8cceb4dd4f1a3` | Explicit identity mapping for the eight contacts and two nonselectable attachments. |
| `.context/import-hangboard-model-packages/reports/nature-stone-hanger-verification.json` | `074169d8b936fd79be38c64c3acdaad091e1787e59f51f7b53a517fe430441ee` | Actual USDZ clean-reimport, eight-hold descriptor, materials, and attachment export verification. |

The new logical inventory contains only:
`edge-front-15mm-incut`, `edge-front-15mm-flat`,
`edge-front-20mm-wood-flat`, `edge-front-20mm-granite`,
`edge-reverse-10mm-incut`, `edge-reverse-10mm-flat`,
`edge-reverse-06mm-flat`, and `edge-reverse-06mm-incut`.
No pinch or jug IDs are inferred from product use imagery or promotional prose.

The compiled USDZ preserves `cord-passage-1` and `cord-passage-2` as exported,
ordered, nonselectable attachment markers. The verification report records their
positions, outward axes, sides, and source node IDs. They are evidence for two
visible lateral cord-port mouths only. A runtime suspension declaration is
intentionally omitted because the source does not establish four passage
endpoints, cord length/radius, anchor offset, or canonical poses required by
the closed two-branch schema. Hidden routing, rope geometry, knots, off-board
anchor position, adjustment-notch interaction, and a central attachment are not
invented.

Promoted bytes:

| Path | SHA-256 |
| --- | --- |
| `Hangboards/nature-stone-hanger/assets/primary.usdz` | `366e6833403d8877b62b2403ce98683e4c27f9ce76c1d9e9abaa24e50ba382e4` |
| `Hangboards/nature-stone-hanger/assets/primary.model.json` | `eb2a83c035d1a80e172f196c68210b4b0556a897f367ebd3ddcd27b196237fa8` |

Branding artwork, mounting holes, screw hardware, route geometry, and internal
joinery are omitted. Fine fillets, recess widths, insert dimensions, incut
relief, port diameter/depth, and notch placement remain documented display
approximations rather than board metadata. No capacity, weight, included-item,
country-of-origin, coating, training-position, or coaching claim is added to
`board.json`.

## Validation contract

The promoted package roots must contain exactly `board.json`,
`assets/primary.usdz`, and `assets/primary.model.json`. Validation commands:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk python3 -B Tools/HangboardModels/test_model_reports.py
rtk .context/import-hangboard-model-packages/gray-horse-hangboard-packages-venv/bin/pytest \
  -q Tools/HangboardModels/test_import_model_package.py
```

The exact command results are recorded in the Task 3 handoff report. Byte
comparison against the committed converted outputs is required in addition to
descriptor hash and logical-inventory validation.

## Task 5 final validation

Fresh validation at `70771baabb3e9bf38ab3af8c512c6883dacb2070`
confirmed the 63-package final inventory with no drafts. The focused checks
passed: importer tests 19/19, model-report tests 12/12, and model-first package
tests 93/93. Clean Blender reimports of both shipped USDZ files reproduced the
retained reports byte-for-byte. Those reports verify the exact descriptor
hashes and hold inventories above, bounds and centers, positive triangle
counts, native materials, nearest-triangle picking, and source-node
correspondence. Both promoted roots contain only `board.json`,
`assets/primary.usdz`, and `assets/primary.model.json`; neither has a raster or
2D hold-geometry fallback.

Nature's two nonselectable markers were reproduced in exact order: marker 1 is
`cord-passage-1` at `[-0.05249999836087227, 0, -0.002400000113993883]` with
axis `[-1, 0, 0]`, and marker 2 is `cord-passage-2` at
`[0.05249999836087227, 0, -0.002400000113993883]` with axis `[1, 0, 0]`.
Runtime suspension remains intentionally unavailable because this evidence is
not a complete closed-route profile.

Metolius and Training Tiles are unchanged from their pre-promotion baseline.
Their retained rejection reports remain reproducible: Metolius has a body mesh
without an image material, and Training Tiles has four unmapped logical hold
IDs. The retained Baguette determinism reproduction still records byte-identical
descriptor and USDZ output with cleanup verified.

The first focused iOS run passed `BoardModelTests` 16/16 and
`SuspendedBoardPresentationTests` 29/29. `BoardPackageStoreTests` passed 114/115;
its sole failure is the known Task 1 fixture-order mismatch in
`testStoreRejectsSharedCrossParserMalformedModelFixtureMatrix`, not a model
package runtime failure. The excluded Task 1 fixture/test files were not
changed. A second bounded run reported 45 selected tests with zero failures
before it was interrupted at the user's request; its result-bundle summary and
screenshot phase therefore did not run.

Six fresh package renders are retained under
`.context/import-hangboard-model-packages/final-visual-review`, but the generic
review renderer overexposes and clips/crops several Nature and detail views.
They establish renderability, not physical fidelity. No fresh app screenshot
was captured; the retained Task 4 report provides textual app-review evidence
but no retained screenshot was found. No physical-fidelity claim is made.

Exact simulator UUIDs, command logs, hashes, the interrupted-run status, and
cleanup checks are recorded in
`.context/import-hangboard-model-packages/final-report.json`. Both owned
simulators, their manifest entries, the stale validation process, DerivedData,
and the result bundle were verified absent. No HTTP server or network action
was used. No verifier defect was found, so the verifier was unchanged.
