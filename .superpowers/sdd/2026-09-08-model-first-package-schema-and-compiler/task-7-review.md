# Task 7 independent review

**Range:** `dc17f79b..ea1587ef`  
**Verdict:** **REQUEST CHANGES**

## Finding

### P1 — README retains an incompatible raster-only package contract

`README.md:7-10` still says that every supported board is a flat package with a
presentation PNG and canonical hold paths. `README.md:41-44` likewise says that
packages live alongside `assets/primary.png` and that their geometry is the
sole runtime geometry. This contradicts the same change's model-media contract
at `README.md:220-228`: model packages own a USDZ and hash-bound descriptor,
and their mesh/descriptor rather than raster paths supplies presentation,
highlighting, and picking data.

Update or qualify the two earlier paragraphs so the README consistently
describes schema-v2 raster *and* model packages. Until then, the requested
README documentation is internally inconsistent and incorrectly tells future
board migrations to retain a PNG/path representation for every board.

## Confirmed

- `scripts/stage-board-packages.py` has no diff in the reviewed commit. Its
  production sequence calls `discover_board_packages` before creating the
  staging directory (`scripts/stage-board-packages.py:157-167`), and then uses
  `_copy_regular_tree` / `shutil.copyfile` to recursively copy only regular,
  non-symlinked entries (`:105-123`, `:169-172`). The existing malformed-package
  regression also proves no destination is created after parser rejection
  (`test_board_package_staging.py:260-274`).
- The new self-contained fixture is valid to the checked-in schema-v2 parser:
  it declares model media, a `.usdz`, a hash-bound descriptor, matching body
  and hold node inventory, and the two logical holds (`:70-137`). It stages by
  calling the actual production staging entry point under the configured Xcode
  resource environment, with the catalog source copied into the temporary test
  repository (`:140-154`).
- The regression checks exact source-versus-staged USDZ and descriptor bytes
  plus the complete staged regular-file set (`:238-257`). It does not mock or
  reimplement copying, so it would fail on byte transformation, omission,
  addition, or app-side asset substitution.
- The characterization first-run PASS ruling is explicitly and adequately
  recorded in `task-7-report.md`: no production behavior was added, and an
  artificial missing-helper failure would not demonstrate staging behavior.
  The test exercises real code rather than asserting fixture internals, so it
  is not tautological.
- Temporary model source and Xcode-style output are created through pytest's
  `tmp_path`; no persistent server, simulator, tunnel, or generated workspace
  resource is introduced by the change.

## Fresh verification

```text
rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
  Tools/HangboardPackages/tests/test_board_package_staging.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py -q
40 passed in 0.33s

rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
  Tools/HangboardPackages/tests/test_board_package_staging.py::test_staging_copies_model_and_hash_bound_descriptor_byte_for_byte \
  Tools/HangboardPackages/tests/test_board_package_staging.py::test_staging_fails_closed_for_a_malformed_completed_package -q -vv
2 passed in 0.11s

rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
exit 0; 61 boards; drafts: []

rtk git diff --check dc17f79b ea1587ef
exit 0

rtk git diff --exit-code dc17f79b ea1587ef -- scripts/stage-board-packages.py
exit 0
```
