# Task 5 independent review — `af02ad95`

## Verdict

**CHANGES REQUESTED.** The promoted Baguette Evo bytes and retained evidence are
internally consistent: the package is model-only, its 19 factual contacts map
exactly to 20 contact meshes plus one body, the installed/retained hashes match,
and the bounded-orbit caveat is explicit. Approval is blocked because the
implementation and audit repeatedly assert that a historical ZIP is
“unrecoverable,” contrary to the review contract. Three review findings should
also be closed before the Task 5 report is treated as complete.

## Critical findings

1. **The forbidden “unrecoverable historical ZIP” claim is both published and
   enforced by code.** The tracked source audit says the archive “remains
   unrecoverable” (`docs/source-audits/2026-09-10-imported-model-packages.md:186-195`),
   the Task 5 report repeats it
   (`.superpowers/sdd/2026-09-12-contact-first-hangboard-domain/task-5-report.md:14-23`),
   and the retained manifest/evidence repeat it
   (`.context/strong-blowfish-task-5-promotion/model-source-manifest.json:10-22`,
   `.context/strong-blowfish-task-5-evidence-repair/evidence-packet.json:319-321`).
   More seriously, the new importer rejects any manifest that does not make
   that assertion (`Tools/HangboardModels/import_contact_model_source.py:83-85`),
   and its unit fixture canonizes the claim
   (`Tools/HangboardModels/test_import_contact_model_source.py:60-81`). The
   retained recovery record supports only “missing / not found in the recorded
   searches” (`.context/strong-blowfish-task-5-evidence-repair/archive-recovery.json:5-25`),
   not the stronger unrecoverability claim. Preserve the positive provenance:
   the explicitly authorized blend and its verified hash; remove the historical
   ZIP assertion and the code path that requires it.

## Important findings

1. **The actual-export verifier does not prove the approved per-mesh contact
   mapping.** It validates the mapping document, then independently checks only
   that the imported USDZ contains the expected set of 21 source IDs
   (`Tools/HangboardModels/verify_yy_baguette_evo.py:187-214`;
   `require_source_correspondence` at `:84-90`). It never compares each imported
   binding's `(role, contactID)` with `validated.roles_by_node` and
   `validated.contact_ids_by_node`. A USDZ/descriptor with two source meshes'
   contact IDs swapped could therefore pass descriptor regeneration at
   `:215-229`. The focused unit test checks only a missing source ID
   (`Tools/HangboardModels/test_verify_yy_baguette_evo.py:56-62`). The retained
   current report is correct—an independent join found zero mapping/report and
   evidence/descriptor mismatches—but the claimed automated gate at
   `task-5-report.md:129-134` is weaker than stated. Add an exact per-source
   role/contact comparison and a swapped-binding rejection test.

2. **The required promotion regression does not distinguish the promoted asset
   from Task 5 BASE.** The report acknowledges that `board.json` was already v3
   and model-only (`task-5-report.md:103-117`), and `board.json` is byte-unchanged
   across `39b757ef..af02ad95`. The BASE descriptor already has the same 19
   contacts, 20 contact nodes, one body, and the same derived bounds; the test at
   `HangTenTests/BoardModelTests.swift:413-440` checks only those facts and file
   names. It does not assert the promoted model SHA, descriptor digest, or source
   correspondence, so it would pass before promotion rather than provide the
   Task 5 RED described by the brief. The retained Blender report establishes
   the current bytes, but the native promotion test should be bound to the
   audited artifact, and the report's TDD account at `task-5-report.md:136-144`
   should state the actual boundary.

3. **The manufacturer-source count is not coherent across retained records.**
   The Task 5 report says the validated primary packet contains 20 sources
   (`task-5-report.md:32-54`), while the validated `evidence-packet.json` has 12
   `primarySources` (`.context/strong-blowfish-task-5-evidence-repair/evidence-packet.json:5-77`).
   A separate `source-register.json` contains 20 entries (beginning at
   `.context/strong-blowfish-task-5-evidence-repair/source-register.json:7`),
   and all retained file hashes checked out. Clarify “20 registered sources / 12
   packet sources,” or make the packet/register inventories identical. This does
   not invalidate the multi-angle gate: the eight approved manufacturer views
   are explicitly recorded at `evidence-packet.json:438-450`, are materially
   distinct on inspection, and their bytes match their recorded hashes.

## Evidence and limitations

- Commit boundary: `af02ad95` is a direct child of Task 5 BASE `39b757ef` and
  changes 13 paths: only the Baguette descriptor/USDZ, Baguette-focused native
  tests, contact-model import/verification tooling and tests, and the tooling
  README and source-audit document. No production Swift renderer, other board package, plan,
  persistence path, or `yy-baguette-evo/board.json` changed. No canonical 2D
  geometry, raster fallback, or runtime compatibility adapter was added.
- Package audit: `Hangboards/yy-baguette-evo/board.json:24-27` declares one
  model presentation. Its 19 contacts begin at `:134` and contain no spatial
  paths. The descriptor has 19 contact records, 20 bound contact nodes and one
  body (`Hangboards/yy-baguette-evo/assets/primary.model.json:2`, `:380-483`);
  `rounded-tray` alone owns two nodes (`:345-364`). The USDZ contains only
  `primary.usda` and one texture; direct USDA inspection found the same 21 mesh
  bindings and no attachment mesh. Runtime bodies are category-mask zero and
  contacts alone are pickable (`HangTen/Views/BoardModelView.swift:304-325`,
  `:364-370`).
- Provenance/hash audit: the external and retained user-provided blend both hash
  to `43ad5ab...b9131`; installed and retained compiled USDZ both hash to
  `c984434e...e088`; installed and retained descriptor both hash to
  `f1d44e9f...148d`. The retained actual-export report hash is
  `8e66e4c6...b889`, and its contents report clean reimport, exact descriptor
  regeneration, 19 contacts, 20 contact meshes, one body, positive triangles,
  image materials and all 21 source IDs
  (`.context/strong-blowfish-task-5-promotion/reports/actual-export-finalization.json`).
  An independent structured join found no differences among the approved
  mapping, report, descriptor, and factual evidence inventory.
- Picking/review: the retained finalization XCTest result contains exactly the
  two named tests, both passed. The native test uses actual triangle hits,
  contact-only category filtering and closest-hit mode
  (`HangTenTests/BoardModelTests.swift:442-495`). The accepted nested-contact
  limitation is plainly hash-bound and documented in
  `.context/strong-blowfish-task-5-promotion/human-model-review-approval.json:11-12,75-79`.
- Cheap independent checks rerun for this review: 10 contact-tool unit tests
  passed; package `validate --final-inventory` and `status` each reported 63
  packages / 0 drafts; the evidence-packet validator passed; `git diff --check`
  passed and the worktree remained clean. I did not rerun Blender export/render
  or iOS tests; those costly claims were checked against retained reports,
  hashes, images, and the `.xcresult` contents.
