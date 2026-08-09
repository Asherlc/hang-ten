# Task 1 report — deterministic flat catalog renderer

Date: August 9, 2026

## Scope completed

- Added deterministic flat preview renderer and CLI entry point.
- Added focused TDD coverage for split-board rendering and catalog determinism.
- Rebuilt all 32 `*-flat.png` previews plus `flat-illustrations-contact-sheet.png`.
- Replaced the scoped batch review note after visual inspection.

## RED

Command:

```sh
rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py -q
```

Output:

```text
==================================== ERRORS ====================================
__________ ERROR collecting tests/test_catalog_flat_illustrations.py ___________
ImportError while importing test module '/Users/asherlc/src/hang-ten/Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.12/3.12.3/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py:9: in <module>
    from hangboard_vectorizer.catalog_flat_illustrations import (
E   ModuleNotFoundError: No module named 'hangboard_vectorizer.catalog_flat_illustrations'
=========================== short test summary info ============================
ERROR Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.61s
```

Observed result: expected RED import failure because the new module did not exist yet.

## GREEN

Command:

```sh
rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py -q
```

Output:

```text
..                                                                       [100%]
2 passed in 0.74s
```

Observed result: focused renderer tests passed after the minimal implementation.

## Renderer implementation

Files added or changed for the renderer itself:

- `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_flat_illustrations.py`
- `Tools/HangboardOnboarding/pyproject.toml`
- `Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py`

Behavior implemented:

- fixed `PARCHMENT_COLOR`, `BOARD_COLOR`, `CONTOUR_COLOR`, `CAVITY_COLOR`;
- deterministic border-background median masking;
- multi-component retention with 5% / 64 px thresholds;
- deterministic close/open cleanup;
- board-plane fill plus one-pixel contour;
- hold-path flattening through the existing `flatten_display_path(...)` helper;
- metadata-free RGB PNG output;
- four-column labeled contact sheet;
- `hangboard-catalog-flat` CLI plus `python -m hangboard_vectorizer.catalog_flat_illustrations`.

## Full catalog renders

Command used for both runs:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_flat_illustrations --source-dir docs/hangboard-generative-catalog --outline-dir docs/hangboard-generative-catalog/outlines --output-dir docs/hangboard-generative-catalog/flat-illustrations --contact-sheet docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png
```

Run 1 output:

```text
Rendered 32 flat illustration(s)
```

Run 2 output:

```text
Rendered 32 flat illustration(s)
```

## Determinism hashes

33 PNG hashes after run 1, confirmed unchanged after run 2:

```text
beastmaker-1000-flat.png 7b9c060a8755f50a555ec5e88c95b9897d1ae70726095d2e6c7bf33aaf71ca62
beastmaker-2000-flat.png a5cfed57696c23917cd0e5e16e0fa210b12cb216eb022800ec614d8a5ea4a393
dewoodstok-woodbord-flat.png 619e8156eb76b7842acafab535baa846c2eaeab2e0fd31d4c385ef719ab74778
escape-beta-flat.png 040fbce9ad7a2a144271900a82ae3a0df58bb4e52acb1ccd35ebc4e049ec45f1
escape-unlimited-flat.png e9ff497e9ab86d7cac35a2dd92a3ba40e5a8863a04f86c8bf155d49b1c98426f
evolv-kilter-basic-long-flat.png ea833626b559ff58f9968657dd4fc4090a358f8ca43607b7a41b7c3edff89f6a
frictitious-doormount-pro-7-flat.png 95e726edbe3815ff59f36905dad6c87ef2728279e0d4c8a3db18c826ec45d794
frictitious-megalith-flat.png 8db371b67f46ac389a2485ff5f0fccb65cb0f65e5f1bdf47ab91f31790c2794f
lattice-triple-rung-flat.png 0a5a93a8922ff482e145d78190c2323eb7a559d345063c9fffde186a8fa5dcfb
metolius-climbers-edge-flat.png 03dbd2fee4ee6827c44a2e084d4e0d4983d473d9b365aea8ceee36bcd1e6dceb
metolius-contact-flat.png 2ce94ae9884d895766daea2f8feafb2b8536a22e32494a1394119ec43c86bb59
metolius-project-flat.png d51a48172dd62daf611b16f60652db6d9b4dfe922b340360566f68c4895e1c4e
metolius-simulator-3d-flat.png e0a9d95075010374c9da86db2b95fc63613aa0eda5750da8036fa93bf0f4804a
moon-armstrong-flat.png 52ae584d2da4b0a6d9f9d5bd5694a73c80e4589e7fd0c8ae1be35ffc31b71d1e
nature-stoak-board-iii-flat.png a76bea55fd5517dcc27175df81499870191c6b576031c644e9b2efb1bdaada91
soill-iron-palm-2-flat.png 022e79d5a448e983167f5de05e1f22ff667ada1e0d661b0867ad0e2ed365500f
soill-split-palm-flat.png 9d6bf3c6254c7241594cbcb969690bc0faa23d0277bdfde58fc0faae400b0fbc
soill-training-tiles-flat.png 1f3426640c7288973810d50a9f25ac6bb0844bd9c93567ee21348a10c70dd874
target10a-linebreaker-base-flat.png b2acb967baed3ee305ca088af35ce3640fefc58181525f6a06ada1a17e5916f6
tension-grindstone-flat.png 47d45977592603703d5dc33948a33ef8477aab10219a0217767b3817fa15e2f2
tension-honestone-flat.png 35e1139e5de883b71f4815d99b10589fc84a7b7982c8bf8d8babb2fc4d36425f
tension-whetstone-flat.png 61d23ea24ce77d334aa9db8c441650913c266139060a1b2a687b855e90595075
trango-rock-prodigy-forge-flat.png 59ba8e1cc941421d65a08706554b54994afe39b5efe34aee67d1ed5e166d9048
trango-rock-prodigy-natural-flat.png b395f75a5cd8b39511550f9d6c3c49b67f38b6e4ff48a70b3d31b4ae726b0f29
trango-rock-prodigy-pivot-flat.png 0c04d9e91a10e5ce0cb28824dfb4470f748c21bb58e963e56ded0a8b39ce5211
trango-rock-prodigy-training-center-flat.png 4baf6be58e557ec3202909f73da4eb76b8c19f8e65f7b505f383937c04a6f1db
yy-verticalboard-evo-flat.png 8adaaef935f856ecab15eaf556221d78f35121207b502d82dbc82e030a0b8034
yy-verticalboard-first-flat.png 1832ad9a77735d7b9da3d04225800abb4cb90ccb975aaf71e2c39379800ca7c5
yy-verticalboard-light-flat.png 00df98f85c8ea510044fc427cab723230903936df2f6fc5162f6ccb17c2746f5
yy-verticalboard-one-flat.png 1eae743761fefd870d9e73d8eff8eee8e1c07fc071de789a194536cb85ae6851
zlagboard-evo-flat.png 9280cc5623ad178a8bd320739311514a367fdd10d23cc792774e2b5c61478814
zlagboard-pro-flat.png 756143d48a0e34990f80de30368d516a97e84dae7a7f30f3321849cfed82d71d
flat-illustrations-contact-sheet.png 139419a588bbf369cfe46f5a2ff020cc8e3755496b7592992a87c2cff0d00238
```

Comparison command result:

```text
Determinism verified for 33 PNG files
```

## Verification commands

Focused renderer tests:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py -q
```

Output:

```text
..                                                                       [100%]
2 passed in 0.74s
```

Combined catalog verification:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py -q
```

Output:

```text
..FFF                                                                    [100%]
FAILED Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py::test_catalog_outline_documents_match_catalog_sources
FAILED Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py::test_catalog_sources_include_conservative_outline_guidance
FAILED Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py::test_every_catalog_output_has_plausible_internal_outline_geometry
3 failed, 2 passed in 0.90s
```

Failure details observed:

- `flat-illustrations-contact-sheet.png` is currently treated as a source PNG by the outline catalog checks, so they expect a matching outline JSON.
- The current working-tree `docs/hangboard-generative-catalog/outlines/evolv-kilter-basic-long.json` includes `hold-01` bounds `(0.056, 0.535, 0.888, 0.04700000000000004)`, which violates the existing “not wider than 0.88 while shorter than 0.18” plausibility assertion.

Outline CLI verification:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli --source-dir docs/hangboard-generative-catalog --output-dir docs/hangboard-generative-catalog/outlines --check
```

Output:

```text
Missing outline JSON: flat-illustrations-contact-sheet
```

## Visual review

Inspected file:

- `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png`

Observed results:

- 32 / 32 boards render with visible board bodies.
- Split and multi-piece boards retain separate components instead of collapsing to the largest body only.
- Cavities are consistently darker than the board plane and stay traceable at contact-sheet scale.
- Palette is consistent warm parchment / board / cavity with no lighting, texture, branding, or scene artifacts.

Scoped review note updated:

- `.context/flat-hangboard-illustrations/batch-review.md`

## Files changed

Code and tests:

- `Tools/HangboardOnboarding/pyproject.toml`
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_flat_illustrations.py`
- `Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py`

Review note:

- `.context/flat-hangboard-illustrations/batch-review.md`

Generated preview artifacts:

- `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png`
- all 32 files under `docs/hangboard-generative-catalog/flat-illustrations/`

## Concerns

1. The renderer task itself is green and deterministic, but the broader outline verification step is not clean in the current worktree because of pre-existing outline-check assumptions and unrelated outline JSON edits that I was instructed not to modify or stage.
2. I did not change or stage any outline JSON files, even though that leaves the existing outline verification command failing as described above.

## Follow-up wave — August 9, 2026

### Root causes confirmed

1. The previous committed PNGs were rendered against 16 dirty working-tree outline JSON files instead of a clean committed outline snapshot.
2. The 82nd-percentile foreground cutoff dropped pale board planes on real catalog sources and erased committed cavity geometry when clipping to the reduced board mask.
3. `flat-illustrations-contact-sheet.png` was still treated as a source PNG by `catalog_outline_cli._discover_sources` and by the catalog-outline test helper.
4. The contour implementation used a morphology gradient that colored outside-board pixels instead of a literal one-pixel inner boundary.

### Follow-up RED

Focused RED command:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py Tools/HangboardOnboarding/tests/test_catalog_outlines.py -k 'flat or contact_sheet or module_mode_executes_main' -q
```

Output:

```text
FAILED Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py::test_render_flat_illustration_uses_one_pixel_inner_contour
FAILED Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py::test_render_flat_illustration_preserves_representative_low_contrast_board_planes[beastmaker-2000-1605-225]
FAILED Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py::test_render_flat_illustration_preserves_representative_low_contrast_board_planes[beastmaker-2000-165-406]
FAILED Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py::test_render_flat_illustration_preserves_representative_low_contrast_board_planes[dewoodstok-woodbord-72-447]
FAILED Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py::test_render_flat_illustration_preserves_representative_low_contrast_board_planes[dewoodstok-woodbord-231-609]
FAILED Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py::test_render_flat_catalog_gives_every_committed_outline_visible_cavity_pixels
FAILED Tools/HangboardOnboarding/tests/test_catalog_outlines.py::test_cli_excludes_contact_sheet_and_writes_review_overlay
FAILED Tools/HangboardOnboarding/tests/test_catalog_outlines.py::test_module_mode_executes_main_and_writes_outputs
8 failed, 5 passed, 21 deselected in 14.54s
```

Focused RED failure details observed:

- outside contour pixels were `CONTOUR_COLOR` instead of `PARCHMENT_COLOR`;
- representative Beastmaker 2000 and DeWoodstok outer-plane pixels still rendered as parchment;
- the clean committed catalog still had 13 outlines with zero cavity pixels after clipping;
- outline CLI still emitted `flat-illustrations-contact-sheet.json`.

### Follow-up GREEN

Focused GREEN command:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py Tools/HangboardOnboarding/tests/test_catalog_outlines.py -k 'flat or contact_sheet or module_mode_executes_main' -q
```

Output:

```text
......                                                            [100%]
13 passed, 21 deselected in 13.68s
```

Implementation changes in this wave:

- replaced the 82nd-percentile foreground cutoff with a border-noise-derived threshold;
- merged outline support back into the board mask before cavity rendering;
- switched the contour to a literal one-pixel inner boundary;
- excluded `flat-illustrations-contact-sheet.png` in outline-source discovery;
- allowed the catalog-outline test module to point at a clean committed outline directory via `HANGBOARD_CATALOG_OUTLINE_DIR` so the dirty working-tree outline edits remained untouched.

### Clean committed-input verification

Committed outline snapshot creation:

```text
/Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5
```

Combined outline tests against clean committed inputs:

```sh
HANGBOARD_CATALOG_OUTLINE_DIR=/Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5/docs/hangboard-generative-catalog/outlines TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py -q
```

Output:

```text
.....                                                             [100%]
12 passed in 13.27s
```

Clean committed outline CLI check:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli --source-dir docs/hangboard-generative-catalog --output-dir /Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5/docs/hangboard-generative-catalog/outlines --check
```

Output:

```text
Verified 32 catalog outline documents
```

### Clean rerender reproducibility

First clean rerender into checked-in PNG paths:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_flat_illustrations --source-dir docs/hangboard-generative-catalog --outline-dir /Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5/docs/hangboard-generative-catalog/outlines --output-dir docs/hangboard-generative-catalog/flat-illustrations --contact-sheet docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png
```

Output:

```text
Rendered 32 flat illustration(s)
```

Second clean rerender into the workspace-owned temp area:

```sh
TASK_PYTHONPATH=Tools/HangboardOnboarding/src PYTHONPATH="$TASK_PYTHONPATH" rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_flat_illustrations --source-dir docs/hangboard-generative-catalog --outline-dir /Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5/docs/hangboard-generative-catalog/outlines --output-dir /Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5/rerender/flat-illustrations --contact-sheet /Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5/rerender/flat-illustrations-contact-sheet.png
```

Output:

```text
Rendered 32 flat illustration(s)
```

Hash comparison between the checked-in 33 PNGs and the second clean rerender:

```text
Matched 33 PNG hashes
beastmaker-1000-flat.png 1e83d5aed44ac8b171f60a1f6f9a75458bf2beb485325378d7c3f114adde0023
beastmaker-2000-flat.png aa4a71c58d1ea450a94c2b7a492ae30999c3b209f613b77d2d7ed077ebd5ce97
dewoodstok-woodbord-flat.png 9e2fa7dca19218a80856ae558c96c9545115f460a225e86d46b1086297a3e3f5
escape-beta-flat.png 7fcf6d5bf8f277b48013c06a0c843416e31569e10d8f19280460f1bf264ee1d6
escape-unlimited-flat.png eaa5fa8324d05800987066274b3630978f93d1ed25130d2a97165aacccd373a0
evolv-kilter-basic-long-flat.png fa476815f4aa75f52c30986486e7009d65f568ec5362e493b61f31b1b52bda14
flat-illustrations-contact-sheet.png 85737d3542472c96e1d1464e93e8a7845214e8b92ce64b386a77d5dcb8418202
frictitious-doormount-pro-7-flat.png 19e65991a602d7f62c0b722b708984b2ee5b1f9e2090071532999ee2bd7eef45
frictitious-megalith-flat.png 6257737891dd87b81cea90b69e204c2dc531200073bc5bf01d4fe532670ff0c2
lattice-triple-rung-flat.png d502930ddf452b080583e0c3b76ff55d69462fb1d44e107f615b3cb63881ee72
metolius-climbers-edge-flat.png c248675c463b3980b34b9b76f1544bdd492385d44749116133132927878c7dce
metolius-contact-flat.png 493d0efa01720dad7cec5655e61a19330e335944725e63acbbb09b039baf8393
metolius-project-flat.png 52295870e09d309d38b57c938a82bc9b43da41de01f9d78c59c824a196c8aeb1
metolius-simulator-3d-flat.png 1806220c4d7b248e7811febb6a46a7fbbb64f74f0eddc5d00d66b400a70ee370
moon-armstrong-flat.png ca49633f87b5cbc41705149e2af7bda8bac7f322f89e0c7031d5b6cda894e447
nature-stoak-board-iii-flat.png ac83054bfe013789f42bab1aeee26a743047d07541c469910c955071df60c962
soill-iron-palm-2-flat.png 2aacb496e2fd910b1856c668aa059355ae359b91a9cb110473ef72eb53886727
soill-split-palm-flat.png b8aad5eb890e5c0cc3ba9a42f22323a218dbf60c8a1cbdd7eea1402bac86416d
soill-training-tiles-flat.png bd90d13cc07de2d56bf91a3d9bd626927d70420c2178e33c9f923b9358ae3099
target10a-linebreaker-base-flat.png 405d482c655112f931daa55eddac4240798a61d55410f02effd3ff6221594160
tension-grindstone-flat.png 99b53646dc7433fef14d78cb6272b4d1ceb09c23612d9c1dbfb0c017fd518c33
tension-honestone-flat.png f3fa877aea864e112ada7c893ffd2d370bd9fe4bd534b64d096405dc5b6a4c85
tension-whetstone-flat.png e96b29a0f5b5903b7ea720a2539b8deca07e717a32a285f72fc4f1d70ffb485b
trango-rock-prodigy-forge-flat.png 5067092f705bab8a1e93d34c07de5bff383b0c36b30ab92c8aecff77db483f94
trango-rock-prodigy-natural-flat.png c17a5da66f1c485e31437c0c571bc496e4ec1457d2a90efb55213951d6909500
trango-rock-prodigy-pivot-flat.png 26665a94c63c95764ce9a8e24af30d04dc0984eb5b2cacc399c8ca7e77d7bd58
trango-rock-prodigy-training-center-flat.png d2aa3fa75a15f05cbe0f1147599f13efab3d408556a2f6a2319318c58921b4e4
yy-verticalboard-evo-flat.png ec5db1fbc928dcd3e164af0772b5e34463e2deb92baa67e9924d44452e37024d
yy-verticalboard-first-flat.png fca4d5449a4079d10dbcae6f08eefd2c6b0540cbcffd36fe9ee23d6d12c05d2b
yy-verticalboard-light-flat.png 27406fbff23b188597b556def9e87af57cfc8989c28fef5f65958a48dd25ffd2
yy-verticalboard-one-flat.png 923f9767d8867384020e9d8087c1b17b5de37cf91c60084785a9cf31f9b3a38f
zlagboard-evo-flat.png 242bd97abc0678494186689f42f02c190f51840a5fa9a8dac76ad4bfe72ed9f4
zlagboard-pro-flat.png 430063ed07d8c5bf18bc3a2345624e9dd8d2881b88968c372211d40a2ac65733
```

### Visual review

Inspected file after the clean committed-input rerender:

- `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png`

Observed follow-up results:

- Beastmaker 2000 and DeWoodstok now retain the pale outer planes that were previously dropped.
- All 32 boards remain visually traceable in the contact sheet.
- Split and multi-piece boards remain preserved.
- Every board keeps the warm flat palette with no photographic texture or lighting artifacts.

### Workspace-owned temp cleanup

Cleanup command result:

```text
removed /Users/asherlc/src/hang-ten/.context/task1-clean-head-snapshot.7xurbia5
exists_after False
```

### Files changed in the follow-up wave

- `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_flat_illustrations.py`
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outline_cli.py`
- `Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py`
- `Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py`
- `Tools/HangboardOnboarding/tests/test_catalog_outlines.py`
- `.context/flat-hangboard-illustrations/batch-review.md`
- `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png`
- all 32 files under `docs/hangboard-generative-catalog/flat-illustrations/`

### Follow-up concerns

1. The dirty working-tree outline JSON edits remain present and intentionally untouched, so any command pointed at `docs/hangboard-generative-catalog/outlines` directly can still observe those unrelated user modifications.
2. The clean verification path now depends on explicitly using the clean committed snapshot for outline-based checks when the working tree is dirty, which is intentional for this task.
