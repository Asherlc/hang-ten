# 2026-09-11 model-package promotion audit

## Scope and decision

This audit promotes the supplied Metolius Simulator 3D and So iLL Training
Tiles Blender sources to model-only schema-v2 packages. It does not derive or
trace geometry from a raster image. Tagged source copies, mapping manifests,
compiler outputs, and ownership metadata are under
`.context/replace-rasters-with-3d-models/` for workspace `merciful-mayfly`.

The supplied Training Tiles source has exactly sixteen selectable contacts: one
pocket, two slopers, two middle edges, and three bottom edges per tile. The
active package has only those sixteen logical holds. `top-pocket-inner-left`,
`top-pocket-inner-right`, `top-jug-left`, and `top-jug-right` have no source
mesh, are excluded from active metadata, and have no placeholder geometry.
A repository scan of runtime and saved-data surfaces (`HangTen`, `HangTenTests`,
and non-test/non-audit package data) found no workout/history record using
them. They are not added as deprecated schema records. The historical 2026-08
20-contact ledger remains historical; this source-backed audit supersedes it
for the active model package.

Metolius retains its old logical holds and appends only source-backed
`flat-sloper-2-left` and `flat-sloper-2-right`: both are 55 mm flat slopers.

## Evidence inputs

| Package | Artifact | SHA-256 |
| --- | --- | --- |
| Metolius | `Metolius-Simulator-3D.blend` | `a589f9202fe528b090a27b1047e89893f6c5376a015431846d8c39ce7e94701e` |
| Metolius | `README.md` | `c6b075666b6aa56480da5dba214de98b1a9ef7780f2158e453e8cbd3bfeb099a` |
| Metolius | `hold-map.json` | `09296c63be94826443ea1ec81c853ad29ebbd0ffeaf9acbcb55f971a6b14adbe` |
| Metolius | `validation.json` | `ef3bcf90d8a568525ef8540233446eb17496bc32a6effab9c1c7848643ce3cc6` |
| Training Tiles | `Training-Tiles.blend` | `c7f252c8c1833c09a85b6d4f0164ecf1ab23d2e2783eaefafeffbcf6b4f014bf` |
| Training Tiles | `README.md` | `10c6c6494a28a05f26b8539ffe35b91b46581439ff63ba75a12fd9911b49b20e` |
| Training Tiles | `hold-map.json` | `fe71fb8bf0046f7aea4dd14cadb532519cffa03f3733434913872fdcd4347fd0` |
| Training Tiles | `qa/validation.json` | `2c4ea08493c7e9119a376c03335bc7623194600bee1ecbf16b38b7cf58bf1866` |

Both sources are in metres, Z-up, X across, with front toward negative Y. The
compiler emits right-handed `hang-ten-board-v1` (X right, Y up, positive Z
toward the climber). The sources have Principled materials without image
textures; the compiler now permits this renderer-visible material contract,
while still rejecting any unusable image texture node.

## Explicit object mappings

No source object was renamed or joined. Importer-visible USDZ node names are
shown after the second arrow. Descriptor `body` nodes never have a `holdID` and
are nonselectable.

### Metolius Simulator 3D

`board_body -> board_body_001` (body).

```text
hold_01_left->jug-1-left->hold_01_left_001; hold_01_right->jug-1-right->hold_01_right_001
hold_02_left->flat-sloper-2-left->hold_02_left_001; hold_02_right->flat-sloper-2-right->hold_02_right_001
hold_03_left->round-sloper-3-left->hold_03_left_001; hold_03_right->round-sloper-3-right->hold_03_right_001
hold_04_left->pocket-4-left->hold_04_left_001; hold_04_right->pocket-4-right->hold_04_right_001
hold_05_left->edge-5-left->hold_05_left_001; hold_05_right->edge-5-right->hold_05_right_001
hold_06_left->edge-6-left->hold_06_left_001; hold_06_right->edge-6-right->hold_06_right_001
hold_07_left->edge-7-left->hold_07_left_001; hold_07_right->edge-7-right->hold_07_right_001
hold_08_left->pocket-8-left->hold_08_left_001; hold_08_right->pocket-8-right->hold_08_right_001
hold_09_left->pocket-9-left->hold_09_left_001; hold_09_right->pocket-9-right->hold_09_right_001
hold_10_left->pocket-10-left->hold_10_left_001; hold_10_right->pocket-10-right->hold_10_right_001
hold_11_left->edge-11-left->hold_11_left_001; hold_11_right->edge-11-right->hold_11_right_001
hold_12_left->pocket-12-left->hold_12_left_001; hold_12_right->pocket-12-right->hold_12_right_001
hold_13_left->pocket-13-left->hold_13_left_001; hold_13_right->pocket-13-right->hold_13_right_001
hold_14_center->jug-14-center->hold_14_center_001; hold_15_center->pocket-15-center->hold_15_center_001
hold_16_center->pocket-16-center->hold_16_center_001; hold_17_center->pocket-17-center->hold_17_center_001
hold_18_center->pocket-18-center->hold_18_center_001
```

### So iLL Training Tiles

`body-L -> body_L_001` and `body-R -> body_R_001` are bodies.

```text
hold-L-pocket->top-pocket-outer-left->hold_L_pocket_001; hold-R-pocket->top-pocket-outer-right->hold_R_pocket_001
hold-L-sloper-outer->upper-sloper-outer-left->hold_L_sloper_outer_001; hold-R-sloper-outer->upper-sloper-outer-right->hold_R_sloper_outer_001
hold-L-sloper-inner->upper-sloper-inner-left->hold_L_sloper_inner_001; hold-R-sloper-inner->upper-sloper-inner-right->hold_R_sloper_inner_001
hold-L-edge-middle-outer->middle-edge-outer-left->hold_L_edge_middle_outer_001; hold-R-edge-middle-outer->middle-edge-outer-right->hold_R_edge_middle_outer_001
hold-L-edge-middle-inner->middle-edge-inner-left->hold_L_edge_middle_inner_001; hold-R-edge-middle-inner->middle-edge-inner-right->hold_R_edge_middle_inner_001
hold-L-edge-bottom-center->bottom-edge-center-left->hold_L_edge_bottom_center_001; hold-R-edge-bottom-center->bottom-edge-center-right->hold_R_edge_bottom_center_001
hold-L-edge-bottom-inner->bottom-edge-inner-left->hold_L_edge_bottom_inner_001; hold-R-edge-bottom-inner->bottom-edge-inner-right->hold_R_edge_bottom_inner_001
hold-L-edge-bottom-outer->bottom-edge-outer-left->hold_L_edge_bottom_outer_001; hold-R-edge-bottom-outer->bottom-edge-outer-right->hold_R_edge_bottom_outer_001
```

## Shipped outputs

| Package | USDZ SHA-256 | Descriptor SHA-256 | Inventory |
| --- | --- | --- | --- |
| `metolius-simulator-3d` | `49582fb19be8c5b4c857e728bd2e669acd80925d1ecc3ea438cd099d74448c56` | `1ab3704c43b9337a05fed6614444a703af3085e20c5c4321d54567405d028485` | 1 body, 31 holds |
| `soill-training-tiles` | `e0fa41d40d4ec4f8c0925ed31f34a716d11203f51dcd753fe12814022973c062` | `e48d46f88157025244b5f41e6f4bf68e8dd4fb59fb25e4740dde0bf6f5951acb` | 2 bodies, 16 holds |

Each package root has only `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`. Descriptor hashes bind the exact shipped USDZ
bytes. Both documents use orthographic model media with no `holdGeometry`, PNG,
image URL, or raster fallback.

## Validation record

The first multi-body compiler test failed before the production change with
`scene requires exactly one body mesh`, then passed after all contract layers
accepted one-or-more bodies. The Blender compiler test similarly failed before
the material change for an untextured Principled material, then passed.

| Command | Result |
| --- | --- |
| `rtk python3 -m unittest Tools/HangboardModels/test_multiple_body_meshes_unittest.py` | pass: 2 tests |
| `rtk python3 -m unittest discover -s Tools/HangboardModels -p 'test_*_unittest.py'` | pass: 2 tests |
| `PYTHONPATH=Tools/HangboardPackages/src rtk python3 -m hangboard_packages.cli validate --root Hangboards --final-inventory` | pass: 61 complete packages, 0 drafts |
| `rtk proxy blender --background --factory-startup --python Tools/HangboardModels/test_compile_model_package_blender.py` | pass: tag, deterministic export/reimport, and untextured Principled-material regressions |
| `rtk proxy blender … compile_model_package.py …` for each owned tagged source, then four `cmp` calls | pass: both regenerated USDZ and descriptors byte-match shipped assets |
| `rtk python3 -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -q` | unavailable: `No module named pytest` |
| `xcrun swiftc -parse HangTen/Models/BoardPackageStore.swift HangTenTests/BoardModelTests.swift HangTenTests/BoardPackageStoreTests.swift` | pass |
| saved-data scan for the four excluded IDs in `HangTen` and `HangTenTests` | pass: no references |

The focused simulator XCTest invocation resolved packages but then left both
its `xcodebuild` client and private `SWBBuildService` idle in Mach-message waits
for more than twelve minutes, before a build action, test result, app install,
or screenshot. The exact owned simulator was then terminated through the
validation script's cleanup trap: the UUID was absent from `simctl`, both owned
manifests were empty, and `.context/DerivedData` was removed. Full simulator
XCTest and visual review are therefore unavailable in this host run; no shared
device was used. A sandbox Blender probe also crashes before startup, so the
host-context Blender commands above performed the actual exports and native
compiler checks.
