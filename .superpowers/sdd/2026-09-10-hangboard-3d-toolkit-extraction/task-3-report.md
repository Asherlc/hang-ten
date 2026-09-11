# Task 3 — Compact II shared-verifier adapter

## Status

Implemented and locally verified. The Compact II verifier now exposes
`compact_ii_config()` and delegates package validation to
`verify_model_package` from Task 2.

## TDD evidence

### RED

Added adapter tests for the ordered 19-ID inventory, exact two-asset package
set, 150,000 triangle ceiling, shared-verifier identity, skip-render report
compatibility, and the absence of body-depth/review-rig claims. Before the
adapter change, the tests failed because the old module imported unavailable
`bpy`, had no `compact_ii_config`, and did not route through the shared core.
The requested `pytest` command could not run because pytest is not installed.

### GREEN

Replaced the standalone Blender checks with a thin `ModelVerificationConfig`
adapter. The shared verifier now performs exact inventory/order validation,
USDZ archive/material checks, fresh import, imported image materials,
descriptor regeneration/equality, source correspondence, and triangle ceiling
enforcement. The adapter flattens the core report and retains `rendersSkipped`,
`explicitTriangles`, `texturedMeshCount`, `hold_ids_preserved`, and exact asset
report fields. No body-depth assertion or review rig was added.

## Files changed

- `Tools/HangboardModels/verify_wood_grips_compact_ii.py`
- `Tools/HangboardModels/test_model_verification.py`
- `Tools/HangboardModels/test_model_reports.py`

## Tests and checks

- `PYTHONPATH=Tools/HangboardModels rtk proxy python3 -m unittest test_model_verification test_model_reports` — **25 passed**
- `rtk proxy python3 -m py_compile` on all three changed Python files — passed
- `rtk git diff --check` — passed
- Blender CLI verification — unavailable (Blender not installed)

## Concerns / limitations

The environment lacks both pytest and Blender, so actual USDZ reimport and
descriptor regeneration could not be executed here; those checks remain in the
shared verifier and are exercised by the Blender CLI in the target environment.
The adapter intentionally requires `--skip-renders` because Compact II has no
reviewed source render rig.
