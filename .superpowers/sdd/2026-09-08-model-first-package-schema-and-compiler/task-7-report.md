# Task 7: typed board-media staging characterization

## Scope and ruling

Task 7 adds a self-contained v2 model fixture and a characterization test to
`Tools/HangboardPackages/tests/test_board_package_staging.py`; production
staging code remains unchanged. The recorded Task 7 ruling applies the TDD
characterization exception: the fixture and assertion were added together and
the first executable focused run was expected to pass because the existing
stager already implemented the behavior. An artificial missing-helper
`NameError` would not have characterized staging behavior, so no artificial
RED was created.

## Characterized behavior

`make_v2_model_package` creates a parser-valid model-only schema-v2 package
with a hash-bound `assets/primary.usdz` and
`assets/primary.model.json`. `stage_with_xcode_environment` copies the current
catalog package source into the test repository, configures the Xcode resource
environment, and calls the production stager. The test proves:

- staged USDZ bytes exactly equal the source USDZ bytes;
- staged descriptor bytes exactly equal the source descriptor bytes; and
- the staged package's complete regular-file inventory is exactly
  `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`.

Inspection of unchanged `scripts/stage-board-packages.py` confirms the
mechanism: `stage_board_packages` first calls
`discover_board_packages(Hangboards)` and then invokes `_copy_regular_tree` for
each validated package. `_copy_regular_tree` visits children recursively in
sorted order, accepts only regular directories and files, copies file bytes via
`shutil.copyfile`, and rejects every other entry including symlinks. README now
documents this parser-approved recursive, byte-preserving behavior and the
absence of an app-side model-resource substitution.

## Verification evidence

The literal brief command using the system `python3` could not collect tests
because `/opt/homebrew/opt/python@3.12/bin/python3.12` has no `pytest` module.
The existing workspace-local validator environment recorded in this plan's
progress file has pytest 9.1.1, so it was used without installing or changing
dependencies:

```text
rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
  Tools/HangboardPackages/tests/test_board_package_staging.py -q
9 passed in 0.90s

rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
  Tools/HangboardPackages/tests/test_board_package_staging.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py -q
40 passed in 0.98s

rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
exit 0; 61 boards; drafts: []
```

`git diff --check` passed, and the production staging script has no diff.

## Resource lifecycle and cleanup

This task created no persistent resource, server, simulator, tunnel, or
workspace-owned generated directory. Pytest's `tmp_path` fixture created the
model source and Xcode-style destination under its ephemeral test directory
and cleaned them when the run ended. The pre-existing
`.context/hangboard-packages-venv` is an earlier workspace-owned validator
environment, reused read-only for test execution and left untouched.

## Skill candidates

- `migrate-hangboard-to-3d` for typed-media package/staging contract work.
- `superpowers:test-driven-development` for ordinary production behavior
  changes; this task used its characterization exception documented above.
- `superpowers:verification-before-completion` for fresh focused, model-first,
  inventory, and diff checks before commit.
