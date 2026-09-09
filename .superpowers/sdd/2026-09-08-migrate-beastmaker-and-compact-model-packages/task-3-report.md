# Task 3 — actual-export verifier tooling

Date: 2026-09-09

## Scope

This task changed only the two actual-export verifiers, their Blender-free
report coverage, and their documentation. It did not change Beastmaker
geometry, either Blender source, USDZ/package resources, package descriptors,
or live board packages. A concurrently modified Compact geometry generator was
left untouched and unstaged.

## RED/GREEN evidence

The report suite initially passed its six pre-existing checks. The new
Beastmaker report fixture coverage was added first. It then failed as expected:

```text
FAIL test_beastmaker_report_rejects_hardware_meshes
AssertionError: ValueError not raised
```

The smallest production addition was the Blender-free
`verify_report(report, expected_ids=...)` check in
`verify_beastmaker_1000.py`. It requires the fixed 22-ID inventory and zero
hardware meshes before the actual export report can be written. The test
exercises a JSON fixture through the production loader and validator, and also
registers compiler-package paths for the Compact verifier.

Fresh GREEN verification:

```text
rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py
9 tests: OK

rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
  Tools/HangboardModels/test_model_descriptor.py -q
33 passed

rtk proxy git diff --check
exit 0
```

## Beastmaker actual export

The task brief's literal editable-source compiler command was tried first:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/compile_model_package.py -- \
  --blend .context/shaky-rat-beastmaker-1000/beastmaker-1000.blend \
  --board-json Hangboards/beastmaker-1000/board.json \
  --output-directory .context/shaky-rat-beastmaker-1000/package
```

The compiler itself exited 0, but the standalone verifier correctly rejected
the result: its imported board-frame bounds had `max=[0.58,0.058,0]` and
`min=[0,0,-0.150]`. In other words, the direct input was 580 × 58 × 150 mm
after the compiler's expected native-axis conversion, not the required
580 × 150 × 58 mm. That generated package was deleted immediately; its exact
compiler scratch directory was also confirmed absent.

The approved source report already records a dedicated compiler input and a
rigid board-to-storage matrix. Before using it, a fresh read-only Blender audit
opened both source files without saving either. It compared all 23 meshes and
confirmed identical mesh names, roles, hold IDs, material slots, vertex counts,
polygon counts, SHA-256 hashes of local vertex bytes, and SHA-256 hashes of
face topology/material-index bytes. Every transport scene matrix exactly
equaled the documented rigid matrix times the editable-source matrix:

```text
[[1,0,0,0], [0,0,-1,0], [0,1,0,0], [0,0,0,1]]
```

The retained audit is
`.context/shaky-rat-beastmaker-1000/task3-transport-audit.json`. It proves the
transport copy is coordinate-frame only and not a physical geometry, naming,
material, or topology substitution.

The audited compiler input was then compiled and verified:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/compile_model_package.py -- \
  --blend .context/shaky-rat-beastmaker-1000/beastmaker-1000-compiler-input.blend \
  --board-json Hangboards/beastmaker-1000/board.json \
  --output-directory .context/shaky-rat-beastmaker-1000/package

rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_beastmaker_1000.py -- \
  --output .context/shaky-rat-beastmaker-1000/package
```

Both exited 0. The actual USDZ/report hashes are respectively
`e15bae1d9664b834ee68853cecba47076617bdd382458b26700d18e321e146e3` and
`2c392869087b6729870010d7606dd3a500eb659d48f80fe851115ff62b71984b`.
The actual export report records:

- bounds `min=[0, 0.000000000226, -0.000000011325]`,
  `max=[0.579999983311, 0.150000005960, 0.057999994606]` metres;
- 22 preserved logical hold IDs, zero hardware meshes, and exactly 23 bound
  textured meshes;
- 112,064 explicit triangles, below the recorded 200,000 ceiling;
- exact descriptor node inventory and source-piece correspondence; and
- actual `usdz-front.png`, `usdz-three-quarter.png`, and
  `usdz-clay-detail.png` review renders.

The direct editable-source command in the brief is therefore a specification
concern, not silently substituted behavior: the current compiler expects the
Blender-native transport frame, while the editable source uses the canonical
board frame. The README documents the evidence and the mismatch. No source
geometry was changed to accommodate it.

Sandboxed Blender crashed before Python/USD tooling started (signal 11); each
successful Blender invocation used the approved host command. No server,
tunnel, simulator, or other external resource was created.

## Compact II preparation only

`verify_wood_grips_compact_ii.py` now accepts only the generic compiler
package layout (`assets/primary.usdz` plus `assets/primary.model.json`). It
reimports into an empty scene, requires explicit imported body/hold tags and
the exact 19-ID inventory, rechecks image materials and explicit triangles,
and regenerates the descriptor in memory to require exact USDZ-byte agreement.
It no longer accepts GLB or root-level legacy exports, falls back from object
names to IDs, or asserts a 56 mm whole-body depth. Any report is written beside
the compiler package so the package still contains exactly its two generated
assets.

Compact compilation and runtime verification were intentionally not run.
The approved evidence does not establish a whole-board depth, and the required
reviewed, explicitly tagged Compact source `.blend` was not available to this
task. This remains a pending dependency, not a failed execution. No Compact
shape, source tags, generated asset, descriptor, or board package was altered.

## Resource ownership and cleanup

Task 3 added the owned Beastmaker compiler output path to the existing
`.context/shaky-rat-beastmaker-1000/ownership.json`. The durable package,
report, renders, and transport audit remain under that owner. The temporary
read-only audit script and both exact compiler scratch directories were
deleted and their absence was checked. No assets were promoted.

## Completion addendum — compiler-input ruling and Compact II

### Beastmaker literal-command ruling

The Task 3 plan and tracked brief now explicitly authorize the
generator-emitted, audited
`.context/shaky-rat-beastmaker-1000/beastmaker-1000-compiler-input.blend` as
the compiler input. This resolves the review's **SPEC FAIL / QUALITY PASS**:
the literal editable-scene command had produced a 580 x 58 x 150 mm board-frame
result and was correctly rejected, whereas the documented transport input
produces the verified 580 x 150 x 58 mm export.

The editable Blender scene uses X-width/Y-depth/Z-height; the package board
frame is X-right/Y-up/Z-toward-climber. The accepted compiler input is only the
audited rigid coordinate-frame transport. The retained audit proves that all
23 mesh names, roles, hold IDs, materials, local vertices, and topology are
unchanged; only the documented rigid transform differs. Neither Beastmaker
geometry nor compiler behavior changed. The migration skill already permits
the temporary export copies used by the compiler, so no reusable-rule change
was warranted.

### Compact compiler-source repair (non-geometry only)

Starting from Astra's physical correction `b8596eae`, the Compact generator
now assigns one explicit `role="body"` and every contact explicit
`role="hold"` plus its exact stable `hold_id`. The generator's existing report
continues to distinguish the 64 mm **estimated body depth** from the source
limited 56 mm #2/#9 sloper callouts; no validation treats 56 mm as whole-board
depth. Before writing the editable compiler source it removes only its
review-only wall, camera, and lamps. That prevents render staging objects from
becoming untagged compiler meshes. It does not change body/hold dimensions,
sections, positions, radii, vertices, topology, or material appearance.

RED/GREEN evidence is retained in the focused report suite:

- RED: missing `tag_model_piece` failed `test_compact_source_tags_body_and_exact_hold_id`.
- GREEN: the source tag regression passed after adding the explicit body/hold
  properties.
- RED: the first generic compile correctly rejected the saved `Studio wall —
  render only` mesh because it had no role.
- GREEN: `test_compact_compiler_source_discards_render_only_objects` passed
  after restricting the saved `.blend` to the 20 model meshes.
- RED: a synthetic `assets/primary.png` was accepted by the Compact package
  path helper.
- GREEN: the verifier now rejects any asset inventory other than
  `assets/primary.usdz` and `assets/primary.model.json`.

### Generated source and actual-export evidence

The final source was regenerated from committed generator revision `fd67968a`
under the owned durable path
`.context/shaky-rat-metolius-wood-grips-compact-ii/task3-compiler-ready-source/`.
The generic compiler produced only
`task3-compiler-ready-package/assets/primary.usdz` and
`assets/primary.model.json`; no live package resource was changed or promoted.

The actual compiler USDZ verifier and the separate read-only physical checker
agree on these results:

- USDZ SHA-256: `220c68ea5519b0bed80cd2aac08b35f5f2c2a7d2200596f62c3a84996efb94a3`.
- Descriptor SHA-256: `300a26886362dd0c510c729e1a9fd4e6a35f47497aed5e7f12d33a2fdb7068fe`;
  it exactly describes the actual USDZ bytes in `hang-ten-board-v1`.
- Exact inventory: 19 hold IDs, one body plus 19 hold meshes, 20 imported
  textured meshes, no unbound/hardware mesh, 65,424 explicit triangles (under
  the 150,000 ceiling), and imported 2048 x 2048 image material data on every
  mesh.
- Bounds: 610.000014 x 64.000003 x 157.000005 mm. The 64 mm depth remains the
  Astra display/body estimate only; it is not promoted to a source claim.
- Actual exported mesh rays: all 1,320 exterior-rim probes and all 1,952
  bilateral-section probes pass, with zero failures.
- The verifier clears source images before import, validates exact imported
  tags and materials, and rejects raster or any other extra package asset.

Focused fresh verification completed with 12 report tests, 33 descriptor
tests, and the real-Blender compiler regression suite. No HTTP server, tunnel,
simulator, live package promotion, or native SceneKit validation was created
or claimed by this completion. Durable task output ownership is recorded in
the Compact evidence packet's `ownership.json`.
