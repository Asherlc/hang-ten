# Task 3 implementation report

Implemented the single-board Workbench suite shell:

- Added browser suite state and a cancellation-aware tool controller.
- Added Onboard, Inspect, Promote to iOS, and Validate tool navigation with a persistent active-board/revision card.
- Kept the existing onboarding editor intact under Onboard.
- Added Inspect board preview, Stage 4 artifact links, hold inventory summary, approval/revision status, readiness, and next action.
- Added promotion and validation workbench client calls with optimistic revision payloads and existing job polling semantics.
- Left Promote and Validate as stable placeholders for Tasks 4 and 5.

Verification run:

```sh
rtk node --test Tools/hold-highlight-editor/tests/workbench_suite_model.test.js \
  Tools/hold-highlight-editor/tests/workbench_suite_controller.test.js \
  Tools/hold-highlight-editor/tests/workbench_app.test.js \
  Tools/hold-highlight-editor/tests/workbench_client.test.js
```

Result: 28 passing tests, 0 failures.

Warnings: `getValidationReport` is wired as an integration point; the current server read route can return no persisted report, while `runValidation` returns the authoritative job result. No Task 4 promotion view or Task 5 validation view was implemented.

## Important Task 3 review fixes

- Completed views now expose only the hash-bound Stage 4 normal artifact and accepted region count for their selected revision; Inspect uses those values while editable-stage images remain unchanged.
- Promotion previews returned by the browser client carry their requested `revisionId`, and suite state rejects unbound or stale results.
- Successful validation jobs populate an in-memory, active-revision cache in `WorkbenchService`; `GET /validation` returns `{ report: ... }` or `null` without running validation.
- Promote and Validate remain placeholders; no Task 4 or Task 5 visual work was added.

Verification:

```sh
rtk node --test Tools/hold-highlight-editor/tests/workbench_suite_model.test.js \
  Tools/hold-highlight-editor/tests/workbench_suite_controller.test.js \
  Tools/hold-highlight-editor/tests/workbench_app.test.js \
  Tools/hold-highlight-editor/tests/workbench_client.test.js
rtk proxy uv run --isolated --project Tools/HangboardOnboarding --extra dev pytest \
  Tools/HangboardOnboarding/tests/test_workbench.py \
  Tools/HangboardOnboarding/tests/test_workbench_validation.py \
  Tools/hold-highlight-editor/tests/test_server.py -q
rtk python3 -m py_compile Tools/hold-highlight-editor/server.py \
  Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py
rtk git diff --check
```
