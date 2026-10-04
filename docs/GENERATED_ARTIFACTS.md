# Source and generated resources

The apps ship compiled resources, while Git retains the sources that produce
them. Run `scripts/build-runtime-assets.sh` after a fresh checkout or a source
change, before package validation, staging, or an Xcode build. Run `git lfs pull`
first so the CAD documents are actual files rather than LFS pointers.

| Retained source | Generated, ignored output | Compiler |
| --- | --- | --- |
| 66 flat `Hangboards/<slug>.FCStd` documents, including `HangTenBoardManifest` | 68 USDZ models and 68 `.model.json` contact descriptors | FreeCAD 1.1.3 and OpenUSD 26.8 |
| Embedded `HangTenSuspensionAuthoring` and its native CAD solid | `Hangboards/<slug>/assets/suspension.json`, including source/model hashes and solved poses/routes | `compile_suspension.py` and pinned native cord solvers |
| CAD manifest and validated generated suspension | `board.json` in staged app resources | Package generator and validator |
| Embedded `HangTenRopePhysics` and its CAD solid | `primary.physics.json` | Native CAD compiler |
| `Art/GripHand/GripHand.blend`, original hand GLB, and license | `HangTen/Resources/GripHand/hand-mesh.json` | Blender 5.2.0 |
| Source-audited Swift plan definitions and board metadata | `HangTen/Resources/PlanLibrary.json` | Swift exporter |

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

CI generates these resources once and distributes them to package tests,
platform staging, and app builds. Release compilation runs against the tested
commit before signing and uploading. Both app platforms keep their existing
package paths; iOS still places only the USDZ in On-Demand Resources.

Use `scripts/build-board-assets.sh --package <slug>` for a board-only rebuild.
Set `HANGTEN_FREECAD_CMD` or `HANGTEN_BLENDER_CMD` to installed pinned tools, or
let the scripts install checksum-verified toolchains into workspace scratch.
Temporary tools, mounts, and configuration directories have recorded workspace
ownership and cleanup traps. Compiled resources installed in the ignored app
and package paths remain available for local builds.

## Retired code and archives

The October 2026 audit traced imports, dynamic loading, CLI entrypoints, CI,
tests, and current documentation across all 1,156 original Python files. It
removed 1,043 obsolete Python scripts: archived one-off authors and diagnostics,
the Blender board import/export chain, mesh rewriting, raster segmentation and
shape inference, old exterior mesh rope authoring, and the rejected Bullet
prototype. Their tests and configuration were removed with them. The obsolete
SceneKit clearance helper and its Ruby launcher were also retired.

Maintained native CAD and cord solvers, descriptor generation, package
validation/staging, geometry review, hand authoring, and source-fidelity tests
remain. Read-only metadata, cord, and presentation audits remain supported.

Another 3,690 archived output files totaling 1,333,207,020 bytes were removed:
compiled model copies, test-result bundles, execution logs, bytecode/editor
caches, frozen Swift copies, and generated patches. Reports, reviewed
screenshots, primary manufacturer evidence, authoring snapshots, and evidence
JSON used by current tests remain. The 119 evidence files formerly tracked
under `.context/` moved unchanged to
[`source-audits/retired-migrations`](source-audits/retired-migrations/README.md).
Git no longer tracks workspace scratch.

Removed programs and raw proof files remain available at Git commit
`769817bcc`, for example `git show 769817bcc:<original-path>`. Old reports may
name those historical paths. Future raw execution output belongs in `.context`
or CI artifacts, with only reviewed findings and necessary evidence retained
in source audits.

## Other files reviewed

Smaller app-icon renditions could be generated from the retained 1024-pixel
artwork. They remain checked in with their asset-catalog metadata. The large
historical image and evidence archives remain because they include primary
sources and human review; they are not inputs to the runtime build.

Reviewed countdown audio remains a source asset. Its paid external speech
generation is not deterministic or available from a clean checkout, so it is
not regenerated in CI. StoreKit documents, training facts, licenses, and
suspension authoring metadata are also retained inputs.

## Reproduction checks

The source-only cleanup before CAD consolidation rebuilt all 66 boards from
their native sources: all 137 board runtime files
reproduced byte for byte, and every retained CAD source remained unchanged.
The hand mesh and all 31 plans also reproduced byte for byte. Package/CAD/script
tests, the retained Models suite, CI gate regressions, workflow lint, and the
iOS Debug build passed. The reviewed Beastmaker 1000 metadata-only
depth correction is documented in
[`source-audits/2026-10-01-beastmaker-spec-corrections.md`](source-audits/2026-10-01-beastmaker-spec-corrections.md).
Its display-depth exception is bound to that exact CAD hash and those exact
published labels in `Tools/HangboardCAD/display_depth_audits.json`; new geometry
or label changes require a new audit. Other depth checks retain their existing
strict behavior.

CAD consolidation retains one flat FCStd per board and embeds the 18 cord
configurations and the physics configuration. All geometry archive members and
native object data remain unchanged. All 18 suspension artifacts regenerate
from native CAD; delivered board facts and cord curves match the prior runtime
data within native numerical precision. Fresh source-only Clavellium and
Beastmaker 1000 builds preserve their USDZ and model-descriptor bytes; the
physics descriptor changes only its source hash. The consolidated host suite
passes 1,027 tests with 14 environment-specific native skips and seven subtests.
All 66 packages validate and stage for both platforms, and the iOS test targets
build successfully. Generated suspension stays outside the app bundle; the 68
USDZs retain their existing ODR placement.
