# Task 2 report: presentation-complete capture and generic DEBUG route

## Status

Implemented and verified.

## Delivered behavior

- Workbench reads the live board and per-presentation API documents, validates the exact selected presentation asset and ordered presentation-scoped region keys, and captures pair-safe evidence.
- `--all-presentations` expands every completed package into all API-declared presentations. The default preserves the legacy one-default-presentation-per-board behavior.
- Manifest entries, PNG names and labels, and contact-sheet metadata identify both package and presentation. Manifest entries also expose stable `capture_id` and `variant` fields.
- Capture-owned server and Chrome process groups are terminated on success, failure, `SIGINT`, and `SIGTERM`; Chrome profiles are workspace-local temporary directories.
- DEBUG launches can opt into the normal board-detail/map renderer with `HANGTEN_REVIEW_BOARD_PRESENTATION=1`, `HANGTEN_REVIEW_BOARD_ID`, and `HANGTEN_REVIEW_PRESENTATION_ID`.
- Missing or unknown route identifiers produce a visible typed error and never fall back. Without the opt-in variable, routing is unchanged. The parser and route remain compiled out of Release behavior with `#if DEBUG`.

## Files changed

- `Tools/HangboardWorkbench/capture_catalog.py`
- `Tools/HangboardWorkbench/tests/test_capture_catalog.py`
- `Tools/HangboardWorkbench/README.md`
- `HangTen/Views/RootView.swift`
- `HangTen/Views/TrainView.swift`
- `HangTen/Views/BoardMapView.swift`
- `HangTenTests/TelemetryTests.swift`
- `docs/IOS_SIMULATOR_VALIDATION.md`

No `Hangboards/` package, geometry, asset, or tensioned-cord ledger file was changed by Task 2.

## TDD evidence

### Workbench RED to GREEN

- The brief's exact `rtk python -m pytest ...` command could not run because this machine has no `python` executable; `rtk python3 ...` then reported that system Python had no `pytest`.
- The workspace-owned venv command `rtk .context/tensioned-cords-foundation-foundation-venv/bin/python -m pytest Tools/HangboardWorkbench/tests/test_capture_catalog.py -q` initially produced `5 failed, 13 passed` for missing presentation enumeration, readiness, filenames, manifest, and contact-sheet behavior.
- The same focused command passed after implementation.
- Smoke debugging produced two additional reproducible RED cases: an unbounded readiness image probe and a board click accepted while the Workbench control was still disabled. Their focused tests failed before each fix and passed afterward.
- A later stale-asset starvation trace showed the DOM still on `lattice.mini-bar/end` while waiting for `lattice.mxedge-lift-large/primary`; the new stale-asset probe regression failed before the expected-URL gate and passed afterward.

Seven additive acceptance tests appeared externally during implementation. They were preserved exactly and not claimed as this agent's authorship. Their first focused-suite observation was `7 failed, 19 passed`; after implementing their generic pair identity, compatibility flag, manifest fields, process-group, and signal-unwind requirements, the fresh selection command reported `7 passed, 19 deselected`.

### Swift RED to GREEN

- The first bounded exact-class build failed at compile time on the intentionally missing board catalog argument and route/error cases.
- Final split validation used an owned iOS 26.3 simulator: `xcodebuild build-for-testing`, followed by bounded `xcodebuild test-without-building -only-testing:HangTenTests/TelemetryTests`.
- Result: `14 tests`, `0 failures`, `** TEST EXECUTE SUCCEEDED **`. The five new cases cover exact valid resolution through `BoardDetailHoldMap`, unknown board, unknown presentation, missing identifiers, and absent opt-in.

## Acceptance evidence

- Focused capture suite: `26 passed in 0.63s`.
- Full Workbench Python suite: `468 passed in 55.76s`.
- Workspace-owned full capture smoke with `all_presentations=True`: `61` packages, `94` presentations, `94` distinct pairs, `94` manifest PNGs present, and contact sheet present.
- DEBUG simulator build: `** BUILD SUCCEEDED **`; installed app container resolved for the exact owned simulator UUID.
- Valid visual route: Owl Climb Poker opened directly with Face B selected; the normal image, numbered overlays, selected Face B hold card, and nine Face B map entries were visible.
- Invalid visual route: the screen visibly showed `Board presentation unavailable` and `Board package unknown.board was not found.`
- `git diff --check` passed.

## Resource lifecycle

Every simulator was registered before use and deleted by exact UUID/name through the workspace archive cleanup. Capture output, Chrome profile, capture server, Chrome process group, DerivedData, screenshots, generated Workbench `node_modules`/`app.js`, local validation scripts, UUID evidence, and the workspace venv were registered for exact cleanup. Final cleanup verification is recorded in the commit handoff.

An unrelated `Tools/HangboardPackages/uv.lock` appeared during concurrent workspace activity. This agent did not run `uv` or create it, did not delete it, and did not stage it. Later concurrent Task 3 changes also appeared under `Tools/HangboardPackages/` and `scripts/hangboard-packages.sh`; Task 2 does not stage them.

## Concerns

None in Task 2 scope. The full catalog is larger than the 20-package/47-presentation tensioned-cord audit scope by design; the smoke validates the complete live Workbench catalog independently.

## Fix round 1

Review found that a present but non-opt-in `HANGTEN_REVIEW_BOARD_PRESENTATION` value silently fell through, and that the route wiring was covered only by a separately constructed hold map rather than through `RootView` and the rendered UI.

### RED

- Parser command: `rtk zsh .context/tensioned-cords-foundation-fix1-ios-session.zsh unit-red`
- Result: exit `65`; compile failed with `Type 'RootReviewBoardPresentationError' has no member 'invalidEnableValue'` and `** TEST FAILED **`.
- UI mutation command: `rtk zsh .context/tensioned-cords-foundation-fix1-ios-session.zsh ui-red`
- Result: exit `65`; `2 tests`, `5 failures`, `0 unexpected`, `** TEST FAILED **`. The invalid value did not produce `boardPresentationReview.error`, and Face B was not selected after intentionally dropping `selectedPresentationID` at the `RootView`/`BoardDetailView` boundary.

### GREEN

- Parser command: `rtk zsh .context/tensioned-cords-foundation-fix1-ios-session.zsh unit-green`
- Result: exit `0`; `15 tests`, `0 failures`, `** TEST SUCCEEDED **`. The new table-driven test covers `""`, `"true"`, `"yes"`, and `"typo"` as present invalid activation values.
- UI command: `rtk zsh .context/tensioned-cords-foundation-fix1-ios-session.zsh ui-green`
- Result: exit `0`; `2 tests`, `0 failures`, `0 unexpected`, `** TEST SUCCEEDED **`. XCUITest verified the visible typed error and Face B selection through the real DEBUG launch route and normal renderer.
