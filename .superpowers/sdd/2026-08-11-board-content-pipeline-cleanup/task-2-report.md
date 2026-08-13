# Task 2 report: supported board-tool root relocation

## Status

Implemented the atomic relocation from `Tools/HangboardOnboarding` to
`Tools/HangboardPipeline` and from `Tools/hold-highlight-editor` to
`Tools/HangboardWorkbench` with `git mv`. The Python import package
`hangboard_vectorizer`, `hangboard-workbench` executable, and
`HangboardWorkbench` SwiftPM product are unchanged.

## RED evidence

Before the moves, the new checkout path contracts were added and exercised:

```sh
.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/hold-highlight-editor/tests/test_server.py \
  Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py -q
swift test --package-path Tools/hold-highlight-editor/macos
```

The Python contract failed because `validate_hang_ten_checkout` still required
the legacy markers. Swift checkout tests also failed because the new marker
set was rejected and legacy roots were accepted. The direct system Python
command from the brief could not collect because it had no `pytest`; the
project-provisioned Python 3.12 environment above supplied the required test
dependencies.

## GREEN evidence

Passing checks after relocation:

```sh
.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_board_catalog.py -q
# 19 passed, 14 subtests passed

.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_board_catalog_generation.py -q
# 10 passed

.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_board_catalog_cli.py -q
# 7 passed

.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardWorkbench/tests/test_server.py -q \
  -k 'checkout_validation or configured_and_discovered_roots_require_hang_ten_checkout or workspace_root_keeps_the_discovered_repository_library or checkout_launch_discovers_nearest_repository_and_default_workspace'
# 9 passed, 105 deselected

.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
# 17 passed

node --test Tools/HangboardWorkbench/tests/workbench*.test.js
# 81 passed

swift test --package-path Tools/HangboardWorkbench/macos
# 20 passed

.context/board-pipeline-tests-py312/bin/python scripts/export-board-library.py --check
# exit 0
```

Also verified the wrapper directly with:

```sh
HANGBOARD_PYTHON=/opt/homebrew/bin/python3.12 PIP_NO_BUILD_ISOLATION=1 \
  scripts/hangboard-tools.sh --help
```

## Files changed

- Moved both tool trees with Git history to `Tools/HangboardPipeline/` and
  `Tools/HangboardWorkbench/`.
- Updated scripts, CI, CodeQL, Dependabot, packaging, server/backend discovery,
  macOS checkout selection, fixtures, tests, ignore rules, and active guides.
- Removed the `convert` wrapper command.
- Added checkout and root-layout contracts rejecting the legacy roots.
- Added a wrapper health check so a virtualenv with a stale editable path is
  rebuilt automatically after relocation.

## Self-review

- Confirmed `git diff --check` succeeds.
- Confirmed active source/automation paths contain no legacy root references;
  intentional legacy strings only remain as negative-test fixtures or retained
  editor provenance metadata.
- Confirmed the published Python package, executable, and SwiftPM product names
  were not renamed.

## Concerns

The full `Tools/HangboardWorkbench/tests/test_server.py -q` run emitted 93 of
114 test progress markers but did not terminate in this environment, so it was
stopped rather than waited on indefinitely. The focused checkout/discovery
coverage above passed, as did all required Node, Swift, export, board-catalog,
CLI, and release-workflow checks. This is recorded for follow-up if the full
server suite is required as a release gate.

## Commit

`refactor: consolidate board tools`

## Review-fix addendum

Follow-up review identified lost YAML indentation in Dependabot, CI, and
CodeQL, plus a macOS-only test interpreter path. All fixes are scoped to those
findings.

- Restored valid YAML indentation while retaining the relocated
  `Tools/HangboardPipeline` and `Tools/HangboardWorkbench` paths.
- Changed the wrapper test environment to use `sys.executable`, so it runs
  with the active interpreter on macOS and Ubuntu instead of a hard-coded
  Homebrew path.
- Re-ran full Workbench server verification with output captured under
  `.context` to avoid output-stream truncation. It completed successfully;
  the prior apparent stall was not a test deadlock.

Review-fix verification:

```sh
ruby -ryaml -e 'ARGV.each { |p| YAML.load_file(p); puts "OK #{p}" }' \
  .github/dependabot.yml .github/workflows/ci.yml .github/workflows/codeql.yml
# all three files: OK

.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_board_catalog.py \
  Tools/HangboardPipeline/tests/test_board_catalog_generation.py \
  Tools/HangboardWorkbench/tests/test_server.py \
  Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
# 160 passed, 14 subtests passed in 38.11s

.context/board-pipeline-tests-py312/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_board_catalog_cli.py -q
# 7 passed

node --test Tools/HangboardWorkbench/tests/workbench*.test.js
# 81 passed

swift test --package-path Tools/HangboardWorkbench/macos
# 20 passed

.context/board-pipeline-tests-py312/bin/python scripts/export-board-library.py --check
# exit 0
```

No remaining concerns from the review findings.
