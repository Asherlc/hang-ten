# Workbench CI fast-fix report

## Root cause

`Tools/HangboardWorkbench/tests/test_dewoodstok_woodbord_board_package.py` retained
an old presentation canvas assertion (`1774 × 887`) and pixel-coordinate frame
constants. The audited `assets/primary.png` is now cropped to `1685 × 465`, while
the board package's normalized geometry, inventory, metadata, path signatures,
and mirror relationships remain the behavior under test.

The Workbench duplicate now derives the image aspect ratio from the asset,
validates normalized frame bounds, and checks a common computed symmetry axis
for mirrored pairs. No production or package data changed, and no cropped asset
dimensions were hardcoded.

## Verification

- Focused test: `rtk python -m pytest -q Tools/HangboardWorkbench/tests/test_dewoodstok_woodbord_board_package.py::test_dewoodstok_woodbord_inventory_geometry_and_symmetry` — 1 passed.
- Full Workbench suite: `rtk python -m pytest -q Tools/HangboardWorkbench/tests` — 173 passed in 24.69s.
- `rtk git diff --check` — passed.

An initial `rtk pytest` wrapper run reported unrelated server-test failures; the
project-supported `python -m pytest` command above passed the complete suite.
