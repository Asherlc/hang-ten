# Foundation Integration P1 Fix Report — 2026-08-09

## Rationale

`ios_promotion.py` intentionally refuses a default preview when any promotion
target differs from `main`. The authorized historical workbench merge included
changes to three promotion-owned iOS targets, so the generator stopped before
rendering its preview. The workbench foundation does not require those changes;
promotion must begin from the clean `main` contract it owns.

The conflict guard is unchanged. No Task 2 promotion/validation service or UI
scope was changed.

## Files changed

- `HangTen/Models/TrainingModels.swift` — restored byte-for-byte from
  `git show main:HangTen/Models/TrainingModels.swift`.
- `HangTen/Models/PlanStorage.swift` — restored byte-for-byte from
  `git show main:HangTen/Models/PlanStorage.swift`.
- `HangTen/Resources/PlanLibrary.json` — restored byte-for-byte from
  `git show main:HangTen/Resources/PlanLibrary.json`, including its deliberate
  lack of a terminal newline.
- `Tools/HangboardOnboarding/tests/test_ios_promotion.py` — uses the
  foundation's canonical `boards/metolius-wood-grips-compact-ii` package and
  adds a real-worktree default-preview regression test. It calls
  `build_promotion_preview` with the default `main` base and therefore fails
  whenever any promotion target is changed from `main`.

## Test evidence

Red regression run before restoration:

```text
Tools/HangboardOnboarding/tests/test_ios_promotion.py::test_default_preview_accepts_the_worktree_main_baseline
ValueError: target changed relative to main: HangTen/Models/TrainingModels.swift
1 failed in 0.46s
```

Green focused promotion run:

```text
.context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_ios_promotion.py -q
..........                                                               [100%]
10 passed in 7.41s
```

Foundation boundary run:

```text
.context/hangboard-suite-venv/bin/python -m pytest \
  Tools/HangboardOnboarding/tests/test_workbench.py \
  Tools/HangboardOnboarding/tests/test_workbench_store.py \
  Tools/hold-highlight-editor/tests/test_server.py -q
exit status 0
```

Final baseline check:

```text
git diff --quiet main -- HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift HangTen/Resources/PlanLibrary.json
exit status 0
```
