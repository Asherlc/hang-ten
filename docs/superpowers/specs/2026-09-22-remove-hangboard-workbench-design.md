# Remove Hangboard Workbench

Date: 2026-09-22
Status: approved design, pending implementation plan

## Context

The repository historically shipped the Hangboard Workbench: a locally run and
browser-hosted board-geometry editor with a React/TypeScript front end, a Python
HTTP server, a packaged macOS Swift shell, CNG/CI build and release workflows, a
Render deployment, and a body of Workbench-named audit metadata. The in-app iOS
board editor (`HangTen/Views/BoardEditor`) supersedes it as the review and
editing surface.

The goal is to remove the Workbench tool, its build/CI/release/hosting, the
Workbench-named audit metadata, the shared-code coupling it introduced, and all
live references to it. Git history is not rewritten.

## Scope

In scope:

- Delete the tool, its CI/CD/release pipelines, hosting config, and Workbench-topic docs.
- Relocate the one piece of shared geometry code that other tools depend on.
- Remove Workbench-named audit metadata and update its consumers.
- Reword live documentation and code comments so no live Workbench references remain.

Out of scope:

- Rewriting git history.
- Changing the iOS in-app `BoardEditor` feature; only its Workbench-parity comments change.
- Touching references to Blender's **Workbench render engine**, which is an unrelated product.
- Rewriting dated historical audit narratives and historical `docs/superpowers` plan/spec records wholesale (see Documentation policy).

## Deletions

- `Tools/HangboardWorkbench/` — entire directory (React app, `server.py`, `capture_*`, `github_*`, `board_package.py`, `macos/` Swift package, `packaging/`, `tests/`, `package.json`, `pyproject.toml`, `README.md`, assets).
- `.github/actions/build-hangboard-workbench/`
- `.github/workflows/hangboard-workbench-pr.yml`
- `.github/workflows/hangboard-workbench-pr-comment.yml`
- `.github/workflows/hangboard-workbench-release.yml`
- `render.yaml` (its only service is `hangboard-workbench`; no other deploy targets are declared there).
- Workbench-topic Superpowers docs:
  - `docs/superpowers/plans/2026-08-19-react-workbench-editor.md`
  - `docs/superpowers/plans/2026-08-20-source-only-workbench-bundling.md`
  - `docs/superpowers/plans/2026-08-20-workbench-editor-history-shortcuts.md`
  - `docs/superpowers/plans/2026-08-16-github-oauth.md` (GitHub OAuth for the hosted Workbench)
  - `docs/superpowers/specs/2026-08-19-react-workbench-editor-design.md`
  - `docs/superpowers/specs/2026-08-20-source-only-workbench-bundling-design.md`
  - `docs/superpowers/specs/2026-08-20-workbench-editor-history-shortcuts-design.md`
  - `docs/superpowers/specs/2026-08-16-github-oauth-design.md`

## Relocation: `board_geometry.py`

`Tools/HangboardWorkbench/board_geometry.py` is self-contained geometry code
(no Workbench imports) that is imported by
`Tools/HangboardPackages/src/hangboard_packages/geometry_cleanup.py`. It is the
only production cross-dependency from `HangboardPackages` into the Workbench tree.

- Move `board_geometry.py` to `Tools/HangboardPackages/src/hangboard_packages/board_geometry.py`.
- Update `geometry_cleanup.py` to import it as a package-relative module and remove the `WORKBENCH_ROOT` `sys.path` insertion.
- Update the module docstring to describe the packages-library role rather than the "direct Workbench contact editor".
- Port `Tools/HangboardWorkbench/tests/test_board_geometry.py` to
  `Tools/HangboardPackages/tests/test_board_geometry.py`, adjusting repository-root
  resolution and importing `board_geometry` from `hangboard_packages`. This
  preserves the shared `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
  coverage.
- Rejected alternative: inlining only the functions `geometry_cleanup` uses; it
  loses the fixture suite and duplicates 622 lines.

## Audit metadata removal

`workbenchReview` is a canonical audit field validated by
`Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`.
It is removed entirely (not renamed).

Production code:

- Remove `_WORKBENCH_CHECKS` (`normal`, `allActive`, `individualHolds`).
- Remove `workbench_review` from the `PresentationFinalState` dataclass and from
  `BootstrapReviewChecks`.
- Remove the `workbenchReview` key from the `_closed(...)` allowed-key sets for a
  record's `final` object and for a bootstrap set's `reviewChecks` object, and
  remove the corresponding parsing.
- Remove Workbench branches in validation:
  - `_checks_are_pending` no longer includes `final.workbench_review`.
  - `keep` validation no longer requires pending `normal`/`allActive`/`individualHolds` and the `hitTest` `notRequired` check is dropped.
  - Completed Phase 2 no longer requires four passed Workbench checks.
  - Non-completed Phase 2 no longer blocks prewritten Workbench results.
  - Bootstrap acceptance changes from four checks (`evidence`, `visual`, `workbench`, `package`) to three; the `selected` and `blocked` branches and the `all_four` predicate are updated accordingly.
- Reword `_COHORT_BASELINE_REASON` to drop the "Workbench" token while preserving meaning.

Canonical data:

- Remove the 85 `final.workbenchReview` objects from
  `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`.
  Every record's `bootstrapComparatorSet` is `null`, so no bootstrap `reviewChecks`
  data exists to remove there.

Tests and helpers:

- `presentation_remediation_helpers.py`: remove the `workbenchReview` builder.
- `test_presentation_remediation_audit.py`: update or remove assertions that
  reference `workbenchReview`.
- `test_hard_cut_audit.py`: delete
  `test_workbench_has_no_older_schema_adapter_or_hold_wire_contract`, which scans
  the deleted directory.
- Preserve `_SIMULATOR_FLOW_KEYS` (`normal`, `active`, `individualHold`, `hitTest`);
  those belong to simulator review, not Workbench.

## Reference edits

CI and configuration:

- `.github/ci-paths.yml`: remove the `workbench`, `workbench_web`, and
  `workbench_native` filters, the Workbench paths under `python`, and the
  `Tools/HangboardWorkbench/pyproject.toml` path under `workflow`.
- `.github/workflows/ci.yml`: remove the now-unused `workbench_web` and
  `workbench_native` job outputs.
- `.github/dependabot.yml`: remove the `Tools/HangboardWorkbench` pip entry.
- `.gitignore`: remove the `.workbench.lock` entry and the Workbench packaging/node_modules/`app.js` entries.

Application and tests:

- `HangTen/Models/BoardStorage.swift`: reword the off-canvas geometry comment to drop the Workbench reference.
- `HangTen/Views/BoardEditor/BoardEditorSession.swift`: reword the two "Workbench display-path parity" comments to describe the in-app editor contract.
- `HangTenTests/BoardPackageStoreTests.swift`: reword the "Workbench's directory" comment.
- `HangTenTests/HoldPathEngineTests.swift`: rename `testOutlinePresetGenerationMatchesWorkbenchSerialization` to a Workbench-free name.
- `HangTenTests/BoardSourceBoundaryTests.swift`: remove the `.workbench.lock` allowed-operational-file exception and its dedicated test.

Documentation policy:

- Live process docs are reworded: `README.md`, `AGENTS.md`,
  `docs/ADDING_A_BOARD.md`, `docs/IOS_SIMULATOR_VALIDATION.md`.
  The Workbench authoring/review step is replaced with the in-app board editor
  and direct canonical `board.json` authoring as the review surface.
- `docs/source-audits/2026-08-12-hangboard-batch-template.md` (a reusable
  template, not a dated record) and `docs/source-audits/screenshots/pr-246/README.md`
  are reworded.
- Dated historical audit records under `docs/source-audits/` and historical
  `docs/superpowers` plans/specs are records of what was done; they are left
  unedited except where they are the canonical manifest (data removal above).
- Blender Workbench references (for example in
  `docs/source-audits/2026-09-20-hangboards-batch-05-migration/.../blender-smooth-shading-2026-09-20.html`)
  are explicitly out of scope and must not be changed.

## Verification

- `Tools/HangboardPackages`: full `pytest` suite passes, including the ported
  `test_board_geometry.py`.
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` passes.
- `rg -i workbench` over the working tree yields only allowed residual hits:
  Blender Workbench references and unedited historical records.
- iOS unit tests touching changed files (`BoardPackageStoreTests`,
  `BoardSourceBoundaryTests`, `HoldPathEngineTests`) compile and pass.
- GitHub Actions workflow lint (`actionlint`) passes on the edited workflows.

## Risks

- The audit schema change alters validation semantics for bootstrap acceptance
  and completed Phase 2 actions. Tests must be updated deliberately rather than
  weakened to hide regressions.
- Removing Workbench leaves the in-app `BoardEditor` as the only editing surface;
  authoring guidance must not imply a tool that no longer exists.
- Historical audit narratives that reference specific Workbench runs remain as
  records; no claim may assert a different tool performed that work.
