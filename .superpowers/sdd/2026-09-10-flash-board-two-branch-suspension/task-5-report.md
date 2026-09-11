# Task 5 report — actual-export verifier and two-branch probes

## Scope

Updated only the Flash Board actual-export verifier and its pure-contract
tests. The verifier now requires:

- one body and exactly seven unique selectable hold bindings;
- four passage correspondences to importer-visible body/attachment nodes,
  rejecting passage or ledge meshes with a hold role;
- material/image evidence for every imported board/contact mesh;
- exact model and descriptor hashes, coordinate frame, source-image isolation,
  and explicit triangle evidence;
- front-to-back surface ray results for every active hold in all four poses;
- two branch clearance results per pose, with sampled centerlines, passage
  interfaces, radius-plus-clearance thresholds, nearest-mesh diagnostics, and
  exact sample counts.

The verifier uses the actual imported mesh BVHs. It does not use camera masks,
source-image detection, generated geometry, or physical geometry edits.

## Test-first evidence

The new report-contract and branch-probe tests were written first and failed
because the verifier accepted missing passage/ray/branch fields. After the
minimal implementation:

```text
python3 -m unittest -v Tools.HangboardModels.test_verify_tension_flash_board
```

Result: 11 tests passed.

Additional checks:

```text
python3 -m py_compile Tools/HangboardModels/verify_tension_flash_board.py Tools/HangboardModels/test_verify_tension_flash_board.py
git diff --check
```

Both passed. The requested `pytest` executable is not installed in this
environment, so the equivalent standard-library unittest module was used.

## Actual Blender verification boundary

The requested compile command was attempted exactly through the managed RTK
Blender entrypoint. Blender 5.2.0 terminated with SIGSEGV before Python ran in
the Metal backend (`gpu::MTLBackend::metal_is_supported`); the retained
diagnostic is:

`.context/pretty-crocodile-tension-flash-board/task5-blender-fresh-config/tmp/blender.crash.txt`

Per the brief, one owned fresh-config minimal repro was then run and reproduced
the same pre-Python SIGSEGV. One identical host-context minimal repro reached
Python and exited successfully. This isolates an environment/runtime boundary;
it is not evidence of a geometry defect. Consequently no new actual-export
`export-verification.json` could be produced from this branch's current
single-cord board metadata. The prior owned package was retained at
`package-prior-task5/` and was not treated as a two-branch pass.

No compiler, descriptor, board JSON, geometry, or package-promotion files were
changed.
