# Task 2 report

## Summary

Added a Blender-free-friendly, fail-closed model package verification core and
a Beastmaker 1000 compatibility configuration/probe adapter. Core checks run
before any Blender import and enforce regular package assets, ordered logical
hold IDs, USDZ/descriptor hashes, descriptor regeneration from imported
vertices, role/unbound-mesh checks, forbidden mesh-name tokens, triangle
ceilings, material policy, and additive board probes. Existing Flash files and
shipped model bytes were not changed.

## Changed files

- `Tools/HangboardModels/model_verification.py`
- `Tools/HangboardModels/test_model_verification.py`
- `Tools/HangboardModels/verify_beastmaker_1000.py`
- This report

## RED/GREEN/final evidence

RED command:

    rtk pytest -q Tools/HangboardModels/test_model_verification.py

Output: `rtk: Failed to run pytest: Failed to spawn process: No such file or directory (os error 2)`.
With the test module attempted directly before production implementation,
the executable failure was `ModuleNotFoundError: No module named
'model_verification'`.

GREEN/final commands:

    rtk env PYTHONPATH=Tools/HangboardModels python3 -m unittest -v test_model_verification
    rtk python3 -m py_compile Tools/HangboardModels/model_verification.py Tools/HangboardModels/test_model_verification.py Tools/HangboardModels/verify_beastmaker_1000.py
    rtk env PYTHONPATH=Tools/HangboardModels python3 -m unittest -q test_model_verification test_model_reports
    rtk git diff --check

Final output: `Ran 19 tests in 0.054s` / `OK`; `git diff --check` was clean.

## Tests

The focused tests cover strict asset equality, ordered inventory, probes not
overriding core failures, report JSON serialization without `bpy`, and the
canonical wood material policy. Existing model report tests remain green.
The Blender verifier was not run because Blender is unavailable in this
environment.

## Review fix round 1 evidence

The Beastmaker CLI now invokes `verify_model_package(beastmaker_config())`
before its legacy report path, then compares the package using
`capture_model_baseline`/`assert_baseline_matches` against the checked-in Task
1 descriptor baseline. The shared core now rejects empty nested asset
directories, requires the canonical texture filename and exact PNG bytes for
canonical wood, counts triangles/enforces the configured ceiling, rejects all
unbound or forbidden meshes, and sets validated legacy role/hold aliases plus
the board-axis transform before additive probes run.

Fix-round verification:

    rtk env PYTHONPATH=Tools/HangboardModels python3 -m unittest -q test_model_verification test_model_reports
    rtk python3 -m py_compile Tools/HangboardModels/model_verification.py Tools/HangboardModels/verify_beastmaker_1000.py
    rtk git diff --check

Output: `Ran 20 tests in 0.055s` / `OK`; compilation succeeded and diff check
was clean. Blender execution remains unavailable, so the integrated USDZ
adapter path is pending the Blender validation gate.

## Self-review and concerns

The adapter keeps the existing Beastmaker CLI/report path intact and exposes a
fixed 22-ID `beastmaker_config()` with canonical material policy, hardware
name prohibitions, and the authored nearest-hit/rim probe. Full imported-scene
execution still requires Blender and should be run in the Blender validation
gate. No package assets or Flash baseline files were modified.
