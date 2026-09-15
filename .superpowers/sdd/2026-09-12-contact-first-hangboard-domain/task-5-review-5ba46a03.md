# Task 5 independent re-review — `5ba46a03`

## Verdict

**PASS.** No critical or important findings. All four findings from
`task-5-review-af02ad95.md` are corrected at
`5ba46a03317b02553cea525ecacceb4058bb5ca5`.

## Finding closure

1. **Historical ZIP wording — closed.** The importer now accepts only the
   evidence-supported `missing` status
   (`Tools/HangboardModels/import_contact_model_source.py:83-85`), and the
   retained manifest says only that the ZIP was absent from the recorded path
   and not found by the retained searches
   (`.context/strong-blowfish-task-5-promotion/model-source-manifest.json:10-22`).
   The tracked audit uses the same bounded wording and preserves the authorized
   blend provenance (`docs/source-audits/2026-09-10-imported-model-packages.md:186-197`).
   A scoped tracked/retained search found no current `unrecoverable` claim or
   enforcement; the only tracked occurrences are historical quotations in the
   original review itself.

2. **Actual-export role/contact proof — closed.** After enforcing one-to-one
   coverage of the 21 approved source mesh IDs, the verifier joins each
   importer-visible node through its stable source ID and compares its exact
   `(role, contactID)` against the validated mapping before regenerating the
   descriptor (`Tools/HangboardModels/verify_yy_baguette_evo.py:84-108,205-254`).
   The negative test swaps the left/right 20 mm bindings while retaining the
   inventory and is rejected
   (`Tools/HangboardModels/test_verify_yy_baguette_evo.py:65-101`). An
   independent structured join found exact equality across all 21 mapping,
   retained-report, and descriptor bindings; the retained report records the
   installed hashes and correspondence
   (`.context/strong-blowfish-task-5-promotion/reports/actual-export-finalization.json:434-435,659-681`).

3. **Promotion regression — closed.** The current test asserts the approved
   model hash, descriptor-file hash, and the exact ordered 21-node role/contact
   list (`HangTenTests/BoardModelTests.swift:414-470`). This is bound to actual
   USDZ bytes because package loading computes and checks the asset hash before
   exposing the descriptor (`HangTen/Models/BoardPackageStore.swift:1001-1027`).
   The retained BASE run overlays this exact test on `39b757ef` and reports one
   failure at the old model hash
   (`.context/strong-blowfish-task-5-review-fixes/run_base_promotion_regression.sh:37-80`;
   `base-promotion-regression-summary.json:14-16,25-41`); the target-tree run
   reports one pass and no failures
   (`current-promotion-regression-summary.json:14-16,25-41`).

4. **Manufacturer-source accounting — closed.** The tracked audit and Task 5
   report now explicitly distinguish 20 manufacturer records in
   `source-register.json` from the 12 intentionally retained as packet
   `primarySources`, leaving eight register-only snapshots visible rather than
   conflating the inventories
   (`docs/source-audits/2026-09-10-imported-model-packages.md:199-203`;
   `task-5-report.md:318-322`). Independent comparison confirmed the 12 packet
   paths are an exact subset of the 20 registered paths and identified eight
   register-only paths; the packet's 12 entries are explicit
   (`.context/strong-blowfish-task-5-evidence-repair/evidence-packet.json:5-78`;
   `source-register.json:7-188`).

## Scope and evidence

`git diff e4ebfb8..5ba46a03` changes six intended paths: review tooling/tests,
the focused native test, and the tracked source audit (112 insertions, 8
deletions; `git diff --check` passes). It changes no hangboard package asset,
`board.json`, production renderer/loader, canonical contact data, 2D geometry,
raster fallback, or legacy compatibility path. The current package remains
schema v3 with one model presentation
(`Hangboards/yy-baguette-evo/board.json:2,15-80`), exactly the three model-only
files, 19 metadata-only contacts, 21 descriptor nodes (one body plus 20 contact
meshes), and no `holds`, `holdID`, raster member, PNG, or contact path. Installed
USDZ and descriptor SHA-256 values remain `c984434e…e088` and
`f1d44e9f…148d`.

The accepted bounded-orbit caveat and its prohibition on geometry, camera-bound,
or correspondence changes remain explicit and hash-bound
(`.context/strong-blowfish-task-5-promotion/human-model-review-approval.json:10-12,75-79`).

Fresh cheap checks for this review passed: 11 focused Python tests, evidence
packet validation, package `validate --final-inventory`, package `status` (62
packages, 0 drafts), and `git diff --check`. The retained actual-export report
hash recomputes to `8e66e4c6…b889`; retained final native evidence reports two
passes, while the focused review-fix BASE/current summaries show the required
RED/GREEN boundary. Blender and iOS were not rerun because the unchanged model
assets, recomputed hashes, retained reports, and focused current checks were
sufficient for this re-review.
