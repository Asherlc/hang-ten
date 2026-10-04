# CodeRabbit comment resolution report

Date: 2026-08-24

Branch: `add-changeable-editor-backgrounds`

Implementation commit: `910d3f9575382272a90e54cd7d1f44526105481a`

## Red evidence

Before the production changes, the focused regressions failed as intended:

```text
FAILED test_wrapper_reinstalls_when_pyproject_is_newer_than_entry_point
  FileNotFoundError: pip.log
FAILED test_process_png_preserves_primary_file_mode
  assert 0o600 == 0o640
FAILED test_main_rejects_seed_packages_missing_from_the_invocation
  AssertionError: seed coverage must be checked before model initialization
3 failed in 8.18s
```

These failures demonstrated that the wrapper skipped a stale editable install,
atomic PNG replacement discarded the original mode, and the CLI initialized
the model without first ensuring every configured seed package was in scope.

## Green evidence

The same focused regressions passed after the implementation:

```text
3 passed in 3.22s
```

The local backdrop dependency was updated from `rembg 2.0.67` to the exact
`rembg[cpu]==2.0.75` project pin. Full verification then produced:

```text
python -m pytest Tools/HangboardPackages/tests -q
146 passed in 14.54s

scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
44 boards; 0 drafts; exit 0

scripts/hangboard-packages.sh status --root Hangboards
44 boards; 0 drafts; exit 0

bash -n scripts/hangboard-packages.sh
exit 0

python -m py_compile Tools/HangboardPackages/scripts/remove_primary_backdrops.py
exit 0

git diff --check
exit 0
```

The ONNX session sidecar created by a direct version-import check was removed,
and its absence was verified before committing.

## Round 1 follow-up

Implementation commit: `ddd5b2030866245fe3465cc56e8e1e0a9a4a2c21`

The focused queue instrumentation regression ran against the prior
implementation and observed duplicate enqueue counts:

```text
FAILED test_enclosed_background_fill_enqueues_each_coordinate_once
  assert {1, 2} == {1}
1 failed, 1 passed in 1.09s
```

After introducing an enqueue-time `discovered` set, the same regression, all
19 configured-seed cases, and both wrapper freshness boundaries passed:

```text
22 passed in 6.15s
```

Full verification for the follow-up produced:

```text
python -m pytest Tools/HangboardPackages/tests -q
148 passed in 29.77s

scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
44 boards; 0 drafts; exit 0

scripts/hangboard-packages.sh status --root Hangboards
44 boards; 0 drafts; exit 0

bash -n scripts/hangboard-packages.sh
exit 0

python -m py_compile Tools/HangboardPackages/scripts/remove_primary_backdrops.py
exit 0

git diff --check
exit 0
```
