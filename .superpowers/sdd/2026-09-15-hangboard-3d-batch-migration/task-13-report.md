# Task 13 — target10a Linebreaker BASE implementation report

## Scope

Only `target10a-linebreaker-base` was migrated. No other Task 13 board was
regenerated, copied, or changed.

## Input verification

- Retained GLB: `target10a-linebreaker-base.glb`
  - SHA-256: `0ba7ffbdf52579194429b47bbc997954102ef952e425d76ce12dcb10e5a1e9f3`
  - This matches `hold-map.json`.
- The current board inventory contains 23 unique factual contacts. Its order
  exactly matches `contact-mapping.json`'s `logicalContactIDs`.
- `sloper-22-center` is absent from the board, mapping, descriptor, and its
  stale target-specific metadata-ledger records were removed. No contact was
  invented.

## Source-blend investigation and repair

The reported pre-Python sandbox Metal crash did not reproduce in this
workspace. This probe exited 0 and printed `PYTHON_REACHED 24`:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  .context/migration/target10a-linebreaker-base/source.blend \
  --python-expr "import bpy; print('PYTHON_REACHED', len(bpy.context.scene.objects))"
```

The retained GLB was nevertheless imported again with the reproducible
conversion command:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/target10a-linebreaker-base/target10a-linebreaker-base.glb \
  .context/migration/target10a-linebreaker-base/source.blend
```

It produced all 24 named meshes (one `body`, 23 named `hold-*` meshes) with
the original `neutral-product-material` assignment. The first exact import
pipeline invocation then failed with exit 1 at
`ValueError: imported mesh body_001 has no image material`. The regenerated
GLB material had a Principled/output node pair but no `TEX_IMAGE`, while the
compiler requires a usable image texture after USDZ round-trip.

I added a packed 1×1 color image to that same material, connected it to the
existing Principled base-color input, and retained the original geometry,
object names, material name, and assignments. The source blend then has a
usable packed `CompilerCompatibleImage` node. Its bytes changed, so the only
manifest field updated was `auditedModelSource.sha256`.

- Regenerated source blend SHA-256:
  `73f7412b56713bb0626ba2f3b1a6e06a5e3a46f3724f89e3559735e855c99821`
- Previous manifest SHA-256:
  `bf23a8cb192892ac5c7288e5ac06261719a5b63a908644d096b8ee6fbf5a66f0`

## Import command and output

The final invocation used the Task 13 target10a command exactly:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/target10a-linebreaker-base/source-manifest.json \
  --mapping .context/migration/target10a-linebreaker-base/contact-mapping.json \
  --package target10a-linebreaker-base \
  --board-json Hangboards/target10a-linebreaker-base/board.json \
  --output-directory .context/migration/target10a-linebreaker-base/compiled \
  --report .context/migration/target10a-linebreaker-base/migration-report.json
```

It exited 0. `migration-report.json` reports `status: converted`,
`nodeCount: 24`, `contactCount: 23`, and `sourceGeometryChanged: false`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Compiled/package `primary.usdz` | 4,427,378 | `270b3c7a8ce9a994f3c8a7edf71bf5d9464c924110cdeb5b264e385ff52d84bb` |
| Compiled/package `primary.model.json` | 11,264 | `cf6f0688b50958d4545f1e2e145d79583c1f79af2ef6c3e1f70465c0126f4ac5` |

`primary.model.json`'s `modelSHA256` equals the actual USDZ SHA-256.

## Binding and package verification

- Board contacts: 23; unique IDs: 23.
- Descriptor contact nodes: 23; all node IDs unique.
- Every board contact is represented exactly once in the descriptor.
- The target package now declares only `assets/primary.usdz` and
  `assets/primary.model.json`, with the established orthographic model camera;
  `assets/primary.png` was removed.

Successful checks:

```sh
rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk proxy .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_approved_board_packages.py::test_every_approved_board_uses_schema_v3_typed_presentations \
  Tools/HangboardPackages/tests/test_approved_board_packages.py::test_approved_packages_declare_their_complete_presentation_asset_set \
  Tools/HangboardPackages/tests/test_metadata_audit.py -q
rtk proxy git diff --check
```

Results: catalog validation exit 0; pytest exit 0 (`46 passed`); diff check
exit 0. A broader approved-package test run also exposed two pre-existing,
out-of-scope failures for the concurrently modified Metolius Deluxe package;
no Deluxe files were changed here.

## Changed paths

- `.context/migration/target10a-linebreaker-base/source.blend`
- `.context/migration/target10a-linebreaker-base/source-manifest.json`
- `.context/migration/target10a-linebreaker-base/compiled/assets/primary.usdz`
- `.context/migration/target10a-linebreaker-base/compiled/assets/primary.model.json`
- `.context/migration/target10a-linebreaker-base/migration-report.json`
- `Hangboards/target10a-linebreaker-base/board.json`
- `Hangboards/target10a-linebreaker-base/assets/primary.usdz`
- `Hangboards/target10a-linebreaker-base/assets/primary.model.json`
- `Hangboards/target10a-linebreaker-base/assets/primary.png` (removed)
- `Tools/HangboardPackages/tests/test_metadata_audit.py`
- `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`

## Remaining concern

The previously reported sandbox Metal failure could not be reproduced; both
the direct source probe and the import pipeline completed under this workspace's
Blender 5.2.0 LTS. The source material repair was required independently by the
compiler's image-material invariant.
