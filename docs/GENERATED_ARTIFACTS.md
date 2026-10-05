# Source and generated resources

The apps ship compiled resources, while Git retains the sources that produce
them. After a fresh checkout or source change, generate the runtime files before
package validation, staging, or an Xcode build:

```sh
rtk git lfs pull
rtk proxy bash scripts/build-runtime-assets.sh
```

The CAD documents must be Git LFS objects, not pointer files.

| Retained source | Generated, ignored output | Compiler |
| --- | --- | --- |
| Flat `Hangboards/<slug>.FCStd` documents, including `HangTenBoardManifest` | Each declared presentation's USDZ and `.model.json` contact descriptor | FreeCAD 1.1.3 and OpenUSD 26.8 |
| Embedded `HangTenSuspensionAuthoring` and its native CAD solid | `Hangboards/<slug>/assets/suspension.json`, including source/model hashes and solved poses/routes | `compile_suspension.py` and pinned native cord solvers |
| CAD manifest and validated generated suspension | `board.json` in staged app resources | Package generator and validator |
| Embedded `HangTenRopePhysics` and its CAD solid | `primary.physics.json` | Native CAD compiler |
| `Art/GripHand/GripHand.blend`, original hand GLB, and license | `HangTen/Resources/GripHand/hand-mesh.json` | Blender 5.2.0 |

Audited plans live in the checked-in canonical
`HangTen/Resources/PlanLibrary.json`, shared by both apps and bundled unchanged.
App decoders validate its definitions against the board catalog. The runtime
asset manifest records its source hash; the catalog does not carry another copy
of the plan JSON. There is no separate Swift plan authoring catalog or exporter.

`primary.model.json` contains compiled contact bindings, mesh measurements, and the model hash; it
is generated alongside its USDZ, without a previously exported descriptor.
The build covers every declared presentation, including Plateau's three depth
configurations. Suspension authoring remains inside the FCStd as topology,
dimensions, solver settings, evidence, pose rotations/cameras, and optional
`offsetXZ: [x, z]`. Generated hashes, settled heights, and routes never become
source metadata. The producer validates source/model/physics/suspension bindings
before installing a complete package and removes superseded generated
configurations. Package generation rejects missing or stale suspension artifacts,
including an artifact whose authoring inputs differ from the current source.

CI materializes the complete catalog and distributes it to package tests,
platform staging, and app builds. Automatic releases download the exact catalog
from the successful triggering main CI run. Manual releases compile the selected
commit through the same workflow before signing and uploading. Both app
platforms stage generated packages; iOS places only the USDZ in On-Demand
Resources, while Android keeps it inline.

Board compilation uses eight stable SHA-256 package shards on Ubuntu 24.04,
up to eight concurrent Linux jobs, and two independent native processes per job.
One Linux job assembles the catalog and exports the hand once. A per-board cache
records the FCStd digest, all compiler inputs (including depth audits and package/model
helpers), pinned dependencies/toolchain, platform, and every generated file's
hash. Cache hits must match current CAD-derived inventory and bindings. Changes,
missing files, malformed descriptors, and corrupt entries rebuild only the
affected boards; compiler changes invalidate all affected cache entries. A full
hit skips native toolchain setup. Generated files remain outside Git.

The assembled `.context/<owner>-runtime-assets/catalog.json` records the exact
revision, CAD and canonical plan source hashes, and complete delivered file hashes. Assembly rejects
missing or overlapping shards, failed builds, mixed revisions, and obsolete
packages. Releases check the manifest again against the tested checkout. Shard
artifact names stay stable within a CI run, so failed-job retries preserve
successful shards. Complete catalogs are immutable and include their producer
attempt. An automatic release uses complete job history to identify the newest
successful assembly execution at or before its successful CI attempt, then
selects its artifact ID. GitHub copies retained jobs into later attempts with new
job IDs and attempt numbers. `scripts/select-runtime-catalog.py` groups copies
by their original execution times and runner, retaining the earliest attempt
for each execution. Release selection is separate from native compilation, so
changes to that script do not invalidate board caches.
Missing or expired artifacts fail release preparation. Test-only retries reuse their retained
catalog, and a later compilation cannot replace an earlier release's tested bytes.

## Local iteration

Use `rtk proxy bash scripts/build-board-assets.sh --package <slug>` for a
board-only rebuild. Edit the canonical plan JSON directly after a source audit,
then validate it with `rtk scripts/validate-plan-work-targets.sh` and the plan tests.
Set `HANGTEN_FREECAD_CMD` or `HANGTEN_BLENDER_CMD` to installed pinned tools, or
let the scripts install checksum-verified toolchains into workspace scratch.
Ubuntu 24.04 needs these runtime and extraction packages before installation:

- FreeCAD: `libegl1 libgl1 libglu1-mesa libopengl0 squashfs-tools`.
- Blender: `libegl1 libgl1 libxi6 libxfixes3 libxrender1 libsm6 libxxf86vm1 libxkbcommon0 xz-utils`.

FreeCAD downloads support Linux x86_64/aarch64 and macOS Apple silicon/Intel.
Linux extracts the AppImage and launches its bundled `freecadcmd` without a
FUSE mount. The hand export automatically downloads Blender on Linux x86_64
and Apple silicon macOS. On Intel macOS or another platform, provide a working
Blender 5.2.0 executable through
`HANGTEN_BLENDER_CMD`; an installed executable at the standard macOS application
path is also accepted.
Temporary tools, mounts, and configuration directories have recorded workspace
ownership and cleanup traps. Compiled resources installed in the ignored app
and package paths remain available for local builds.

## Retained assets and evidence

Reviewed countdown audio, app icons, StoreKit configuration, primary source
evidence, licenses, and source audits are retained inputs. Countdown audio is
generated by a maintainer using a paid external service and reviewed before
commit; CI does not regenerate it.

Keep raw execution logs, test-result bundles, exports, and temporary scripts in
workspace `.context` or CI artifacts. Commit source audits that explain current
physical facts or accepted display estimates, with the primary evidence and
review images needed to assess those decisions. See the
[CAD guide](../Tools/HangboardCAD/README.md),
[package contract](../Tools/HangboardPackages/README.md), and
[ODR guide](IOS_ON_DEMAND_RESOURCES.md) for authoring, validation, and delivery.
