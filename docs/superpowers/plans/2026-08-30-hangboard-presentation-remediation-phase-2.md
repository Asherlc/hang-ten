# Hangboard Presentation Remediation Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair or remove all 66 Phase 1 non-keep presentation records while preserving all 19 keep assets byte-for-byte, then prove the resulting 61-package/84-presentation catalog in Workbench and on isolated iOS Simulators.

**Architecture:** Extend the Phase 1 manifest validator into a schema-version-2, phase-aware state machine that distinguishes original bytes, transient generated candidates, promoted assets, removed presentations, sequential batch completion, and final catalog truth. Fifteen non-overlapping repair sub-batches run strictly in order, each under a fresh implementation subagent: every target is re-sourced live, generated or edited only with the built-in image-generation tool, manually reviewed, directly geometry-reviewed in Workbench, validated, committed, and pushed before the next batch. Final read-only gates review the entire catalog for shared rendering consistency, exercise representative phone and tablet flows with the `validate-hang-ten-ios` skill, and require complete cleanup.

**Tech Stack:** Python 3.11.4+ standard library, pytest 9, existing `hangboard_packages` discovery and CLI, JSON, PNG IHDR/SHA-256 byte inspection, built-in `image_gen` and `view_image` tools, Hangboard Workbench, Swift/Xcode, `xcrun simctl`, and Markdown.

**Spec:** `docs/superpowers/specs/2026-08-30-hangboard-presentation-remediation-design.md`

## Global Constraints

- Execute this plan sequentially with `superpowers:subagent-driven-development`. `AGENTS.md` requires a fresh implementation subagent for every task or configuration change, followed by controller spec-compliance and quality reviews before the next task. Do not parallelize any repair because all tasks mutate the same manifest.
- Use `rtk` for shell commands. Commit and push every completed task and every rejected-candidate provenance checkpoint to the current remote branch.
- Preserve all 19 records whose Phase 1 decision is `keep`; their package PNG bytes and `board.json` files must remain unchanged. This includes the accepted `lattice.mini-bar/primary` self-baseline and the two evidence-blocked keeps.
- Implement exactly 17 `edit`, 48 `regenerate`, and one `removeUnsupportedPresentation` record. The 15 exclusive sub-batches below partition those 66 records by immutable `packageID/presentationID` key; a final review may send a defect back to that record's owning batch but may not create a second asset owner.
- Preserve Phase 1 package identity semantics: `packageIDs` remains a literal unique array whose set is validated against inventory; do not add a sorted-order requirement or silently rewrite its order. Reports may remain deterministically sorted.
- Preserve Phase 1 comparator semantics across all comparator fields. A ready comparator must remain a ready accepted keep with compatible material and form factor, and its reason must start with `Accepted cohort baseline; style-only: `, end with `.`, and contain a unique comma-separated subset of the literal terms `framing`, `lighting`, `background`, `texture`, `smoothing`, and `edge treatment`. A comparator never supplies product geometry. Preserve Mini Bar primary as an allowed accepted self-baseline.
- Before each target is generated, freshly reopen every nonempty official and independent URL routed from that record's `evidence` object, repeat any recorded evidence-gap searches, inspect straight-on and oblique evidence, and record the actual Phase 2 review date and result. Local docs, `board.json`, current assets, manifest prose, comparators, and generated outputs are routing or visual-comparison inputs, never product proof.
- Use only the built-in `image_gen` capability. Never use the imagegen CLI/API fallback, `scripts/image_gen.py`, `OPENAI_API_KEY`, a destination-path argument, or a batch generation command. Issue one built-in call per candidate. For edits, inspect every local edit target and reference with `view_image` before calling `image_gen`; pass the exact local paths through `referenced_image_paths`. For regenerations, pass only the minimum locally saved official/independent evidence images and the declared style comparator, each with an explicit role.
- The built-in tool schema has no explicit size argument. Put the required existing width, height, and aspect ratio in the prompt and accept only untouched model output whose PNG IHDR exactly matches those values. Do not crop, resize, rotate, pad, register, align, mask, composite, recolor, sharpen, smooth, vectorize, simplify, trace, detect, segment, or otherwise post-process any candidate. A byte-preserving `mv`/`cp` is permitted only to place an untouched output or restore an exact backup.
- Never ship a source photograph. The accepted asset must be an original simplified, unbranded render with an off-white studio background, orthographic head-on view of the selected working surface, neutral lighting, restrained contact shadow, clean antialiasing, cohort-consistent framing, and the material-specific cues in the binding design. Omit every detail the reopened evidence does not establish.
- An `edit` uses the current PNG as the built-in edit target and as a topology/likeness invariant; change only the bounded failures identified by that record's findings. A `regenerate` treats the current PNG as human comparison only, not evidence and not an imagegen input; construct only source-proved topology. The removal task performs no generation.
- Store copied web inputs, exact current-byte backups, candidates, side-by-side review captures, Workbench captures, logs, Derived Data, and simulator screenshots only below an exact `.context/sincere-otter-*` directory. Create an `OWNER-sincere-otter` marker immediately, record every exact returned built-in output path and simulator UUID, and install `EXIT`, `INT`, and `TERM` cleanup traps before creating external resources.
- Hash each untouched source input and candidate immediately. A rejected candidate's role, hash, dimensions, built-in provenance, disposition, and evidence-specific reason must be added to the manifest, transiently byte-verified, committed, and pushed before its exact bytes are deleted. Durable final validation checks hash format, provenance, disposition, and verification evidence without requiring rejected bytes to remain. An accepted output ends only at its one declared package asset path.
- Permit at most three prompt-only imagegen attempts per asset. If an attempt changes a proved contact, component, silhouette, material, working-surface orientation, or required canvas, reject it. If no acceptable untouched output exists after three attempts, mark the record and owning batch blocked with the exact reason, commit and push that truth, clean owned resources, and stop later batches; never authorize CLI fallback, post-processing, schema/aspect changes, or approximate likeness.
- For every changed presentation, manually inspect the current target, source images, chosen comparator (or recorded comparator gap), and each candidate side by side. Then use Workbench to inspect normal, all-active, every individual logical hold and every piece, and hit testing against primary evidence. Directly redraw canonical paths only when they are wrong. Use exact mirroring only when the reopened sources prove physical symmetry; select a shape constraint only by operator judgment for a genuinely regular hold. Never derive geometry from raster pixels.
- After each sub-batch, run final-inventory package validation, the focused package/manifest tests, and the complete `Tools/HangboardPackages/tests` suite. Record exact commands/results in the manifest and narrative. If a promoted asset or geometry change fails, move its untouched bytes back to the rejected-candidate context path, restore the exact backed-up current bytes, record the rejection, commit the provenance, and continue only after validation is green.
- Do not add or modify training plans, timer behavior, unrelated metadata, product claims, or app navigation. Do not infer material, color, finish, hardware, dimensions, hold names, hold sizes, usable surfaces, grip guidance, or coaching claims.

## File structure and phase interfaces

- `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py` owns schema-version-2 parsing, original/promoted/removed byte semantics, candidate provenance, batch ordering, transient candidate verification, partial validation, and final validation.
- `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py` owns TDD coverage for Phase 2 lifecycle truth, keep preservation, candidate/promoted hashes, batch partition/order, removal, Workbench/validation states, and partial/final operation.
- `Tools/HangboardPackages/src/hangboard_packages/cli.py`, `Tools/HangboardPackages/tests/test_cli.py`, and `Tools/HangboardPackages/README.md` expose `--phase2-partial`, `--batch-id`, `--candidate-file SHA256 PATH`, and `--phase2-final` while retaining Phase 1 validation compatibility.
- `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json` remains the only machine-readable audit ledger. Record order and original `currentAsset` facts stay immutable so every record keeps its Phase 1 identity.
- `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md` records batch status, source conflicts/gaps, candidate decisions, direct geometry changes, validation, cross-catalog review, and simulator results without becoming product proof.
- `Hangboards/*/assets/*.png` changes only in its exclusive sub-batch below. A package's `board.json` changes only when manual evidence review proves its saved path wrong, except the explicitly sourced Mini Bar removal.

The Phase 2 manifest root is a closed schema-version-2 object. Retain all Phase 1 root fields and add exactly:

```json
{
  "schemaVersion": 2,
  "phase": "assetRemediation",
  "phase2": {
    "batches": [],
    "finalChecks": {
      "crossCatalogReview": {"status": "pending", "evidence": null},
      "manifestValidation": {"status": "pending", "evidence": null},
      "finalInventory": {"status": "pending", "evidence": null},
      "packageTestSuite": {"status": "pending", "evidence": null},
      "buildForTesting": {"status": "pending", "evidence": null},
      "simulatorReview": {"status": "pending", "evidence": null},
      "contextCleanup": {"status": "pending", "evidence": null}
    }
  }
}
```

Each batch is closed over `id`, `order`, `kind`, `recordKeys`, `status`, `blockedReason`, and `checks`. `recordKeys` uses exact `packageID/presentationID` strings and partitions every non-keep record once; keep records appear in no batch. `status` is `pending`, `inProgress`, `passed`, or `blocked`; statuses must form a sequential prefix, and `passed` requires every owned record terminal plus passed `packageValidation`, `focusedTests`, and `fullPackageSuite` checks. Each non-keep record adds `repairBatchID` and a closed `phase2EvidenceReview` object with actual `reviewedAt`, literal reopened URL arrays, repeated evidence-gap searches, `result` (`pending`, `confirmed`, or `blocked`), and notes. Keep records use null `repairBatchID` and a `notRequired` Phase 2 evidence result.

Replace the Phase 1 string arrays under `generation` with these exact structured concepts: `mode` (`none`, `builtInGenerate`, or `builtInEdit`), exact committed `prompt`, `requiredCanvas`, `sourceImages` entries containing `sourceType`, `reference`, `sha256`, `role`, and `suppliedToImagegen`, the exact `currentAssetRole`, and `candidates`. A candidate contains `attempt`, lowercase `sha256`, positive PNG dimensions, `disposition` (`accepted` or `rejected`), concrete `reason`, and provenance fixed to built-in imagegen, untouched model output, and no post-processing, plus a passed transient byte-hash check with actual date and command. There is exactly one accepted candidate for a completed edit/regeneration, and its hash/dimensions equal the on-disk final asset and `final` state.

Add `hitTest` to `final.workbenchReview`. Check status is `pending`, `passed`, `failed`, or `notRequired`, with null evidence only for `pending`; `notRequired` requires a concrete reason. Completed changed presentations require passed normal, all-active, individual-hold, hit-test, package-validation, focused-test, and full-suite checks. Build/simulator checks remain pending until final QA. Removed presentations use `removedUnsupportedPresentation`, null accepted hash/dimensions, no generation candidates, absent package presentation/hold/asset inventory, and truthful `notRequired` visual states.

The public Phase 2 interfaces are:

```python
class PresentationValidationMode(str, Enum):
    SOURCE_RECLASSIFICATION = "sourceReclassification"
    PHASE2_PARTIAL = "phase2Partial"
    PHASE2_FINAL = "phase2Final"


def verify_transient_candidate_files(
    manifest: PresentationRemediationManifest,
    candidate_files: Mapping[str, Path],
) -> tuple[str, ...]:
    """Verify each supplied SHA-256 key against untouched PNG bytes and declared dimensions."""


def validate_presentation_remediation_manifest(
    manifest: PresentationRemediationManifest,
    inventory: BoardInventory,
    *,
    hangboards_root: Path,
    selected_package_ids: frozenset[str] = frozenset(),
    final_validation: bool = False,
    validation_mode: PresentationValidationMode = PresentationValidationMode.SOURCE_RECLASSIFICATION,
    selected_batch_id: str | None = None,
    transient_candidate_files: Mapping[str, Path] | None = None,
) -> PresentationRemediationReport:
    """Validate Phase 1 compatibility or Phase 2 partial/final catalog truth."""
```

The report retains Phase 1 fields and adds `phase`, `batchID`, `batchStatus`, `originalPresentationCount`, `inventoryPresentationCount`, `keptPresentationCount`, `completedRepairCount`, `pendingRepairCount`, and `removedPresentationCount`. Final success is exactly 61 packages, 85 historical records, 19 keeps, 65 completed image repairs, one completed removal, zero pending repairs, and 84 current inventory presentations.

Use these exact ordered `phase2.batches` identities and record keys. This is the machine-validated execution partition; each table in Tasks 2–16 supplies the one exact package asset path for each key.

| Order | Batch ID | Kind | Exact `recordKeys` |
| ---: | --- | --- | --- |
| 1 | `capability-pilot-forge` | `pilot` | `trango.rock-prodigy-forge/primary` |
| 2 | `nonwood-fixed-resin` | `repair` | `escape-beta-22/primary`, `evolv-kilter-basic-long/primary`, `metolius.contact/primary`, `metolius.foundry/front`, `metolius.project/primary`, `metolius.simulator-3d/primary` |
| 3 | `nonwood-fixed-urethane` | `repair` | `soill.iron-palm-2/primary`, `soill.split-palm/primary`, `soill.training-tiles/primary`, `trango.rock-prodigy-training-center/primary` |
| 4 | `mixed-fixed-assemblies` | `repair` | `escape.unlimited/primary`, `frictitious.doormount-pro-7/primary`, `mammut.diamond-finger/primary`, `nature.stoak-board-iii/primary`, `zlagboard.evo/primary`, `zlagboard.pro/primary` |
| 5 | `wood-fixed-classic` | `repair` | `beastmaker-1000/primary`, `metolius.climbers-edge/primary`, `metolius.wood-grips-compact-ii/primary`, `moon.armstrong/primary`, `tension.grindstone-original/primary`, `tension.grindstone-pro/primary`, `trango.rock-prodigy-natural/primary` |
| 6 | `wood-fixed-verticalboard` | `repair` | `yy.verticalboard-evo/primary`, `yy.verticalboard-first/primary`, `yy.verticalboard-light/primary`, `yy.verticalboard-one/primary` |
| 7 | `portable-captain-fingerfood` | `repair` | `captain-fingerfood.dual/primary`, `captain-fingerfood.dual/reverse`, `captain-fingerfood.pocket/primary`, `captain-fingerfood.unlevel/primary`, `captain-fingerfood.unlevel/reverse` |
| 8 | `portable-reversible-edges` | `repair` | `crimptonite.helium-mobile/primary`, `crimptonite.helium-mobile/reverse`, `frictitious.nug/primary`, `frictitious.nug/reverse`, `metolius.light-rail-2/20mm-side`, `metolius.light-rail-2/15mm-side` |
| 9 | `portable-lifting-suspended` | `repair` | `lattice.mxedge-lift-large/primary`, `lattice.mxedge-lift-small/primary`, `metolius.rock-rings-3d/front-pair`, `plateau.lifting-edge/primary` |
| 10 | `multi-port-a-board-flash` | `repair` | `frictitious.port-a-board/primary`, `frictitious.port-a-board/back`, `frictitious.port-a-board/side`, `tension.flash-board/three-edge-upright`, `tension.flash-board/three-edge-inverted`, `tension.flash-board/two-edge-upright`, `tension.flash-board/two-edge-inverted` |
| 11 | `multi-poker` | `repair` | `owl-climb.poker/face-a`, `owl-climb.poker/face-b`, `owl-climb.poker/face-c`, `owl-climb.poker/face-d` |
| 12 | `multi-rock-prodigy-pivot` | `repair` | `trango.rock-prodigy-pivot/orientation-1`, `trango.rock-prodigy-pivot/orientation-2`, `trango.rock-prodigy-pivot/orientation-3`, `trango.rock-prodigy-pivot/orientation-4` |
| 13 | `multi-baguette-evo` | `repair` | `yy.baguette-evo/paired-25-20-15-10`, `yy.baguette-evo/paired-12-8-6`, `yy.baguette-evo/central-30-25`, `yy.baguette-evo/central-20-6` |
| 14 | `multi-yy-penta-travel` | `repair` | `yy.penta-evo/front-pair`, `yy.travelboard/front-25-15`, `yy.travelboard/reverse-10` |
| 15 | `lattice-mini-bar-removal` | `removal` | `lattice.mini-bar/end` |

Every `/records/N/evidence` entry in a repair table is an exact JSON-pointer route into the committed manifest. It means: reopen every literal `official[*].url` and `independent[*].url` below that object, preserve each entry's `publisher`, `sourceKind`, `revisionApplicability`, `imageRole`, and `supportedClaim`, and repeat each non-null evidence-gap search. Likewise, material/render prompts resolve the named record's exact `/materials`, `/formFactor`, `/physicalRevision`, `/workingSurface`, `/findings`, `/currentAsset`, and `/comparator` fields; executors commit the fully expanded prompt and source roles, never pointer text, before calling imagegen.

---

### Task 1: Extend the manifest validator for Phase 2 lifecycle truth

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `Tools/HangboardPackages/README.md`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the existing Phase 1 dataclasses and validator, immutable `currentAsset` facts, literal/set-validated package identities, canonical style-only comparator rule, ready accepted self-baselines, `BoardInventory`, PNG IHDR bytes, and the exact 15-batch key partition declared in this plan.
- Produces: `PresentationValidationMode`, structured Phase 2 records/batches, `verify_transient_candidate_files(...)`, the extended `validate_presentation_remediation_manifest(...)` signature above, and CLI modes `--phase2-partial [--batch-id ID] [--candidate-file SHA256 PATH ...]` and `--phase2-final`.
- Does not consume or produce visual truth: tests may create tiny PNG fixtures and inspect bytes/IHDR only. Do not add Pillow-based image comparison, pixel sampling, similarity, detection, masks, contours, or any other image-analysis helper.

- [ ] **Step 1: Write failing schema and lifecycle tests before production code.**

  Extend fixture builders with `_phase2_manifest(...)`, `_mark_candidate(...)`, `_pass_batch(...)`, and `_remove_presentation(...)`. Add tests that prove the exact schema, enums, and invariants above, including this promoted-byte transition:

  ```python
  def test_phase2_partial_accepts_promoted_bytes_and_preserves_original_facts(tmp_path: Path) -> None:
      boards, inventory, record = _single_board_fixture(tmp_path)
      original_sha = record["currentAsset"]["sha256"]
      candidate_path = tmp_path / "candidate.png"
      candidate_path.write_bytes(_png_bytes(width=1200, height=600, color=(8, 9, 10)))
      candidate_sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
      _mark_completed_generated_record(record, candidate_sha, 1200, 600)
      (boards / "fixture-board/assets/primary.png").write_bytes(candidate_path.read_bytes())
      document = _phase2_manifest(records=[record], batches=[_passed_batch("fixture", record)])

      report = _validate_phase2_document(tmp_path, boards, inventory, document, batch_id="fixture")

      assert record["currentAsset"]["sha256"] == original_sha
      assert report.completed_repair_count == 1
  ```

  Add explicit tests for: schema 2 closed keys; literal package order accepted but duplicate/set mismatch rejected; all 66 non-keeps assigned once and keeps assigned zero times; duplicate/missing/unknown batch keys; product-coupled records resolving through one batch; non-sequential passed/in-progress/blocked states; partial validation with earlier promoted assets and later original assets; wrong on-disk state for pending/promoted/keep; 19 keep hashes immutable; structured source roles; exact prompt/canvas; one accepted candidate; candidate hash format; provenance fixed to built-in/untouched/no-postprocessing; transient candidate bytes/hash/dimensions; rejected-byte absence allowed only after passed transient verification; accepted candidate hash equals final/on-disk hash; Workbench `hitTest`; invalid status/evidence pairs; passed batch completion; blocked batch truth; and final 61/85-history/19/65/1/84 totals.

- [ ] **Step 2: Write failing removal and CLI tests.**

  Test that the historical removal record remains in the manifest while its presentation, `mini-pinch` hold, and `assets/end.png` are absent from inventory; reject a removed record when any of those three remains. Test that other Mini Bar presentation/hold/asset bytes remain unchanged. Add CLI tests for mutually exclusive lifecycle flags, required `--batch-id` relationships, repeated two-argument `--candidate-file`, unknown candidate SHA, hash mismatch, Phase 2 partial JSON, final rejection with pending batches, and final 84-presentation success.

- [ ] **Step 3: Run the new focused tests and confirm RED.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py
  ```

  Expected: FAIL because Phase 2 schema, candidate verification, removal semantics, and CLI flags do not exist.

- [ ] **Step 4: Implement the minimal Phase 2 parser and validator.**

  Add the exact interfaces above. Keep `_current_png_facts` limited to PNG signature/IHDR and SHA-256. In Phase 2 partial mode, compare each keep or pending record to `currentAsset`, each completed repair to its accepted candidate/final hash, and the historical removal record to deliberate absence. Validate all manifest records even when `selected_batch_id` narrows completion reporting. Validate candidate bytes before cleanup only when `transient_candidate_files` is supplied; final durable validation checks the committed verification fields without expecting rejected paths to exist.

- [ ] **Step 5: Implement CLI parsing and documentation.**

  Retain `--final-validation` for the Phase 1 gate. Make `--phase2-partial` and `--phase2-final` mutually exclusive with it and each other. Parse every `--candidate-file SHA256 PATH` pair into a collision-rejecting mapping. `--batch-id` is legal only with partial mode; candidate files are legal only with partial mode. Document the exact transient-versus-durable hash contract and state that no CLI performs generation or image processing.

- [ ] **Step 6: Migrate the manifest to schema 2 without changing package input.**

  Preserve record and `packageIDs` order, every Phase 1 field/value, all original hashes/dimensions, all decisions, and all comparator fields. Add the 15 ordered batch IDs and exact record-key partition from Tasks 2–16, initialize Phase 2 evidence/generation/final state truthfully, add `hitTest`, and set all Phase 2 final checks pending. Add a narrative `## Phase 2 lifecycle` section with 19/17/48/1 input totals and the transient candidate deletion rule. Confirm no `Hangboards` path changed.

- [ ] **Step 7: Run focused tests, full package tests, and initial partial validation.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk git diff --name-only -- Hangboards
  ```

  Expected: tests PASS; partial report is 61 packages, 85 inventory presentations, 19 keeps, 0 completed repairs, 66 pending actions, and 0 removals; package validation passes; the final diff command prints nothing.

- [ ] **Step 8: Commit and push the validator gate.**

  ```bash
  rtk git add \
    Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/src/hangboard_packages/cli.py \
    Tools/HangboardPackages/tests/test_cli.py \
    Tools/HangboardPackages/README.md \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Validate hangboard remediation phase two"
  rtk git push
  ```

---

### Task 2: Prove built-in imagegen canvas fidelity and repair Rock Prodigy Forge

**Files:**
- Modify: `Hangboards/trango-rock-prodigy-forge/assets/primary.png`
- Inspect and modify only if primary evidence proves it wrong: `Hangboards/trango-rock-prodigy-forge/board.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: record `/records/62`, batch `capability-pilot-forge`, built-in `view_image`/`image_gen`, `verify_transient_candidate_files`, and the global source/render/geometry contract.
- Produces: the first completed `regenerate` record and proof that prompt-only built-in output can preserve a required 1536×1024 canvas; or a committed blocked pilot that stops Tasks 3–19.

**Exclusive repair sub-batch (one-asset pilot exception):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/62` `trango.rock-prodigy-forge/primary` | `Hangboards/trango-rock-prodigy-forge/assets/primary.png` | `regenerate` | `urethane`, `splitFixedBoard`; render exact sourced matte molded finish and relief, no wood grain; current image is human comparison only and is not supplied | explicit gap at `/records/62/comparator/baselineGap` | every URL and recorded gap under `/records/62/evidence` |

- [ ] **Step 1: Create and own the pilot workspace before gathering inputs.**

  Create `.context/sincere-otter-phase2-capability-pilot`, immediately create `OWNER-sincere-otter`, and install exit traps that delete only that exact directory plus every exact built-in output path recorded after each call. Copy the current asset byte-for-byte into the directory as a rollback/reference backup and hash it; do not alter it.

- [ ] **Step 2: Reopen and inspect the exact live evidence.**

  Reopen every official and independent URL under `/records/62/evidence`; repeat any gap search; save only the minimum unmodified official/independent images needed to establish the two-piece silhouette, every contact, urethane material, relief, and mounting context. Inspect those local files, the current asset, and the comparator-gap context manually with `view_image`. Update `/records/62/phase2EvidenceReview` with literal reopened URL arrays, actual date, repeated searches, and either `confirmed` or a concrete block.

- [ ] **Step 3: Commit the exact generation prompt before calling the tool.**

  Set `generation.mode` to `builtInGenerate`, `currentAssetRole` to human comparison only/not evidence/not supplied, and `requiredCanvas` to 1536×1024. Populate the prompt fields with literal values from `/records/62/{physicalRevision,workingSurface,materials,formFactor,findings,evidence}`:

  ```text
  Use case: product-mockup
  Asset type: Hang Ten package presentation PNG
  Primary request: create an original simplified unbranded render of the exact cited Rock Prodigy Forge revision and its two-piece advanced front working face
  Input images: identify each supplied official or independent image by its committed source role; identify the accepted style comparator gap explicitly
  Scene/backdrop: common off-white studio background, no wall or mounting scenery
  Subject: only the source-proved product silhouette, contacts, and identity-bearing components
  Style/medium: restrained catalog product render, not a photograph
  Composition/framing: orthographic head-on to the working surface, centered, complete uncropped product, required untouched output canvas exactly 1536 by 1024 pixels
  Lighting/mood: neutral direction, restrained contact shadow, controlled relief shading
  Materials/textures: source-proved matte urethane with no wood grain
  Constraints: preserve every source-proved contact and component; no inferred details; output PNG dimensions and aspect must already be exact from the model
  Avoid: branding, text, labels, logos, watermarks, transparent background, camera tilt, post-processing, invented hardware, invented contacts
  ```

- [ ] **Step 4: Run at most three one-candidate built-in attempts.**

  For each attempt, call built-in `image_gen` once with the committed prompt and exact local source/comparator reference paths through `referenced_image_paths`; do not pass a size or output-path argument. Immediately move the returned file byte-for-byte into the owned context directory, hash it, parse only PNG IHDR, and invoke partial validation with `--candidate-file SHA256 PATH`. Reject any output that is not exactly 1536×1024 before visual promotion. Narrow only the prompt between attempts.

- [ ] **Step 5: Resolve the pilot gate truthfully.**

  If all three attempts miss the exact canvas or fail product/material/topology review, set the record and batch `blocked`, commit each candidate hash/dimensions/reason and the exact capability failure, push, delete rejected bytes only after their transient checks are committed, clean the exact owned directory, and stop the plan. Do not continue to Task 3 and do not use CLI fallback, resize, crop, padding, or a schema/aspect change.

  If a candidate has the exact untouched canvas and passes side-by-side evidence/current review, mark exactly that candidate accepted, promote it byte-for-byte to the declared asset path, and retain other candidates only until their committed rejection provenance is pushed.

- [ ] **Step 6: Deliberately review geometry and visual states.**

  Open Forge in Workbench. Compare primary evidence and the accepted render; inspect normal, all-active, each individual logical hold and every piece, and hit testing. Directly edit `board.json` only for a proved mismatch, use mirroring only if proved, capture review evidence under the owned directory, hash the captures, and record the hashes/results in all four Workbench checks.

- [ ] **Step 7: Validate the pilot batch.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py \
    Tools/HangboardPackages/tests/test_trango_rock_prodigy_training_center_board_package.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id capability-pilot-forge
  ```

  Record exact commands and results; mark the batch passed only after all succeed.

- [ ] **Step 8: Commit, push, and clean the pilot.**

  ```bash
  rtk git add \
    Hangboards/trango-rock-prodigy-forge/assets/primary.png \
    Hangboards/trango-rock-prodigy-forge/board.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Pilot exact-canvas hangboard generation"
  rtk git push
  ```

  Remove copied inputs, rejected outputs, review captures, and the exact owned directory through the installed trap; verify it and every recorded external output path are absent before reporting completion.

---

### Task 3: Repair non-wood fixed resin and molded boards

**Files:**
- Inspect and conditionally modify: `Hangboards/escape-beta-22/board.json`, `Hangboards/evolv-kilter-basic-long/board.json`, `Hangboards/metolius-contact/board.json`, `Hangboards/metolius-foundry/board.json`, `Hangboards/metolius-project/board.json`, `Hangboards/metolius-simulator-3d/board.json`
- Modify: the six exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: passed `capability-pilot-forge`; records 11, 13, 28, 29, 33, and 35; batch `nonwood-fixed-resin`; built-in-only candidate workflow and Phase 2 partial validator.
- Produces: two bounded edits and four exact-revision regenerations with passed manual/Workbench/package validation.

**Exclusive repair sub-batch (6 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/11` `escape-beta-22/primary` | `Hangboards/escape-beta-22/assets/primary.png` | `edit` | `moldedPlastic`, full-width; current is edit target/topology lock; correct only cited treatment defects, retain sourced dual texture | gap `/records/11/comparator/baselineGap` | `/records/11/evidence` |
| `/records/13` `evolv-kilter-basic-long/primary` | `Hangboards/evolv-kilter-basic-long/assets/primary.png` | `edit` | `resin`, full-width; current is edit target/topology lock; retain sourced jug/three-edge layout and real finish | gap `/records/13/comparator/baselineGap` | `/records/13/evidence` |
| `/records/28` `metolius.contact/primary` | `Hangboards/metolius-contact/assets/primary.png` | `regenerate` | `resin`, full-width; matte manufactured surface and exact 11-pocket/four-edge/sloper/jug/pinch topology; current comparison only | gap `/records/28/comparator/baselineGap` | `/records/28/evidence` |
| `/records/29` `metolius.foundry/front` | `Hangboards/metolius-foundry/assets/primary.png` | `regenerate` | `resin`, full-width; source-proved arched pinch/edge/pocket/jug/sloper topology; current comparison only | gap `/records/29/comparator/baselineGap` | `/records/29/evidence` |
| `/records/33` `metolius.project/primary` | `Hangboards/metolius-project/assets/primary.png` | `regenerate` | `resin`, full-width; source-proved compact edge/pocket/jug/sloper topology; current comparison only | gap `/records/33/comparator/baselineGap` | `/records/33/evidence` |
| `/records/35` `metolius.simulator-3d/primary` | `Hangboards/metolius-simulator-3d/assets/primary.png` | `regenerate` | `resin`, full-width; exact seventh-generation topology and controlled depth shading; current comparison only | gap `/records/35/comparator/baselineGap` | `/records/35/evidence` |

- [ ] **Step 1: Establish exact ownership and rollback bytes.**

  Create `.context/sincere-otter-phase2-nonwood-fixed-resin`, add `OWNER-sincere-otter`, install exact cleanup traps, record every returned built-in path, and copy all six current assets byte-for-byte as rollback/current-review inputs.

- [ ] **Step 2: Freshly reopen evidence for all six records.**

  For each exact `/records/N/evidence`, reopen every official and independent URL and repeat recorded gaps. Save the minimum unmodified straight-on/oblique images, hash them, inspect source/current/comparator-gap evidence with `view_image`, and fill each `phase2EvidenceReview`. Stop only the affected record if material, exact revision, topology, or usable face remains unproved; do not borrow facts between Metolius revisions.

- [ ] **Step 3: Commit one exact prompt per record and generate one candidate per call.**

  Use `precise-object-edit` for records 11 and 13, supplying the local target first and locking likeness/topology; use `product-mockup` for records 28, 29, 33, and 35 without supplying current assets. Populate subject/revision/surface/material/form-factor/failure fields from each exact record; include the global studio treatment, literal existing canvas dimensions, no-brand/no-text constraints, source-image roles, comparator gap, and a prohibition on inferred details. Use `view_image` on every local reference, then one `image_gen` call per candidate with `referenced_image_paths`; maximum three candidates per record.

- [ ] **Step 4: Hash, review, record, and promote candidates without post-processing.**

  Immediately byte-hash and IHDR-check every output. Review official/independent/current/candidate/comparator-gap evidence side by side. Before deleting any rejection, record and transiently verify its exact bytes, commit and push with message `Record rejected nonwood fixed resin candidates`. Promote only the accepted untouched output to its one declared path and set all accepted/final fields truthfully.

- [ ] **Step 5: Review every changed presentation in Workbench.**

  Inspect normal, all-active, each individual logical hold/piece, and hit testing for all six presentations. Directly correct a canonical path only if primary evidence proves it wrong; do not infer symmetry or constraints. Hash owned review captures and record all four Workbench results plus any deliberate `board.json` edits.

- [ ] **Step 6: Run package, focused, full-suite, and batch validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_escape_beta_22_board_package.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id nonwood-fixed-resin
  ```

- [ ] **Step 7: Commit, push, and verify cleanup.**

  ```bash
  rtk git add Hangboards/escape-beta-22 Hangboards/evolv-kilter-basic-long \
    Hangboards/metolius-contact Hangboards/metolius-foundry Hangboards/metolius-project \
    Hangboards/metolius-simulator-3d \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair resin and molded fixed presentations"
  rtk git push
  ```

  Trigger and verify exact owned cleanup; accepted PNGs must exist only at declared package paths.

---

### Task 4: Repair non-wood fixed urethane boards

**Files:**
- Inspect and conditionally modify: `Hangboards/soill-iron-palm-2/board.json`, `Hangboards/soill-split-palm/board.json`, `Hangboards/soill-training-tiles/board.json`, `Hangboards/trango-rock-prodigy-training-center/board.json`
- Modify: the four exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 48, 49, 50, and 68 and passed earlier batches.
- Produces: batch `nonwood-fixed-urethane` with four completed regenerations.

**Exclusive repair sub-batch (4 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/48` `soill.iron-palm-2/primary` | `Hangboards/soill-iron-palm-2/assets/primary.png` | `regenerate` | `urethane`, full-width; exact cited sloper/pinch/jug-rail/crimp-rail revision, matte manufactured finish; current comparison only | gap `/records/48/comparator/baselineGap` | `/records/48/evidence`, including the recorded depth conflict |
| `/records/49` `soill.split-palm/primary` | `Hangboards/soill-split-palm/assets/primary.png` | `regenerate` | `urethane`, split fixed; preserve only source-proved mirrored two-piece topology and mounting points; current comparison only | gap `/records/49/comparator/baselineGap` | `/records/49/evidence` |
| `/records/50` `soill.training-tiles/primary` | `Hangboards/soill-training-tiles/assets/primary.png` | `regenerate` | `urethane`, split fixed; exact two-tile pocket/sloper/progressive-edge topology and sourced hardware context; current comparison only | gap `/records/50/comparator/baselineGap` | `/records/50/evidence` |
| `/records/68` `trango.rock-prodigy-training-center/primary` | `Hangboards/trango-rock-prodigy-training-center/assets/primary.png` | `regenerate` | `urethane`, split fixed; controlled recess relief and source-proved body mounting context without depicting excluded screws as supplied; current comparison only | gap `/records/68/comparator/baselineGap` | `/records/68/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-nonwood-fixed-urethane`, record ownership, install exact cleanup traps, and byte-copy/hash all four current assets for rollback and comparison.**

- [ ] **Step 2: Reopen every URL under records 48, 49, 50, and 68 evidence, repeat gaps/conflicts, save and hash only minimum unmodified references, inspect all local images with `view_image`, and commit truthful Phase 2 evidence reviews.**

- [ ] **Step 3: Populate four `product-mockup` prompts from each record's literal revision, working surface, material, form factor, findings, source roles, comparator gap, and canvas. Require the shared studio contract, exact source topology, exact untouched dimensions, matte urethane, no wood grain, no branding/text, and no inferred mounting hardware. Call built-in `image_gen` once per candidate with exact `referenced_image_paths`, at most three per asset.**

- [ ] **Step 4: Hash/IHDR-check untouched output, manually compare source/current/candidate/gap side by side, transiently validate candidate bytes, and commit/push all rejection provenance with message `Record rejected urethane fixed candidates` before deletion. Promote only exact-canvas accepted outputs.**

- [ ] **Step 5: In Workbench, review normal, all-active, every individual hold/piece, and hit testing for all four presentations. Edit paths directly only for proved mismatches, prove any mirroring, hash captures, and record truthful geometry/check results.**

- [ ] **Step 6: Run and record validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_trango_rock_prodigy_training_center_board_package.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id nonwood-fixed-urethane
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/soill-iron-palm-2 Hangboards/soill-split-palm \
    Hangboards/soill-training-tiles Hangboards/trango-rock-prodigy-training-center \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair urethane fixed presentations"
  rtk git push
  ```

  Verify the exact owned directory and every recorded external output are gone.

---

### Task 5: Repair mixed-material fixed assemblies

**Files:**
- Inspect and conditionally modify: `Hangboards/escape-unlimited/board.json`, `Hangboards/frictitious-doormount-pro-7/board.json`, `Hangboards/mammut-diamond-finger/board.json`, `Hangboards/nature-stoak-board-iii/board.json`, `Hangboards/zlagboard-evo/board.json`, `Hangboards/zlagboard-pro/board.json`
- Modify: the six exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 12, 14, 26, 39, 83, and 84.
- Produces: batch `mixed-fixed-assemblies` with six completed regenerations preserving every separately sourced component material.

**Exclusive repair sub-batch (6 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/12` `escape.unlimited/primary` | `Hangboards/escape-unlimited/assets/primary.png` | `regenerate` | `wood+metal`, full-width; restore four sourced mounting positions/hardware without inventing geometry; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/12/evidence` |
| `/records/14` `frictitious.doormount-pro-7/primary` | `Hangboards/frictitious-doormount-pro-7/assets/primary.png` | `regenerate` | `wood+metal+mixedOther`, full-width; complete source-proved metal/rubber clamp assembly; current comparison only | gap `/records/14/comparator/baselineGap` | `/records/14/evidence` |
| `/records/26` `mammut.diamond-finger/primary` | `Hangboards/mammut-diamond-finger/assets/primary.png` | `regenerate` | `wood+metal+mixedOther`, full-width; restore mounting plate, sourced phone mount, and complete topology; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/26/evidence` |
| `/records/39` `nature.stoak-board-iii/primary` | `Hangboards/nature-stoak-board-iii/assets/primary.png` | `regenerate` | `wood+stoneMineralComposite+metal`, full-width; FSC oak, visibly real recycled Norwegian granite, and sourced magnetic/mounting parts stay materially distinct; current comparison only | `Hangboards/metolius-wood-grips-deluxe-ii/assets/primary.png` | `/records/39/evidence` |
| `/records/83` `zlagboard.evo/primary` | `Hangboards/zlagboard-evo/assets/primary.png` | `regenerate` | `wood+metal+mixedOther`, full-width; compact Evo electronic/steel/plate/phone-interface/fastener assembly, without choosing unresolved species; current comparison only | gap `/records/83/comparator/baselineGap` | `/records/83/evidence`, preserving species conflict |
| `/records/84` `zlagboard.pro/primary` | `Hangboards/zlagboard-pro/assets/primary.png` | `regenerate` | `wood+metal+mixedOther`, full-width; exact Pro 2.0 electronic/steel/plate/phone-interface/fastener assembly; current comparison only | gap `/records/84/comparator/baselineGap` | `/records/84/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-mixed-fixed-assemblies`, record ownership, install exact traps, and byte-copy/hash all six originals.**

- [ ] **Step 2: Freshly reopen every routed official/independent URL and gap/conflict for all six exact revisions. Save/hash only minimum unmodified straight-on, oblique, and component references; inspect sources, current assets, and actual comparator or explicit gap with `view_image`; record literal reopened URLs and results.**

- [ ] **Step 3: Write one `product-mockup` prompt per record from literal manifest fields. Name every supplied image role and each separately sourced material/component, require exact original canvas and head-on working face, apply style comparators only to framing/lighting/background/texture/smoothing/edge treatment, and prohibit inferred hardware/species. Call built-in `image_gen` once per candidate, maximum three per asset.**

- [ ] **Step 4: Hash and IHDR-check every untouched output, compare source/current/candidate/comparator side by side, transiently validate bytes, commit/push rejections with message `Record rejected mixed fixed candidates`, then delete only committed rejected bytes. Promote one exact accepted candidate per record.**

- [ ] **Step 5: Review all six accepted presentations in Workbench normal/all-active/individual/hit-test states. Directly correct only proved canonical-path errors, never derive paths from the new raster, hash captures, and record checks/geometry changes.**

- [ ] **Step 6: Run and record batch gates.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id mixed-fixed-assemblies
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/escape-unlimited Hangboards/frictitious-doormount-pro-7 \
    Hangboards/mammut-diamond-finger Hangboards/nature-stoak-board-iii \
    Hangboards/zlagboard-evo Hangboards/zlagboard-pro \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair mixed-material fixed presentations"
  rtk git push
  ```

  Verify exact context/external cleanup and that no source image entered a package.

---

### Task 6: Repair classic wood fixed boards

**Files:**
- Inspect and conditionally modify: `Hangboards/beastmaker-1000/board.json`, `Hangboards/metolius-climbers-edge/board.json`, `Hangboards/metolius-wood-grips-compact-ii/board.json`, `Hangboards/moon-armstrong/board.json`, `Hangboards/tension-grindstone-original/board.json`, `Hangboards/tension-grindstone-pro/board.json`, `Hangboards/trango-rock-prodigy-natural/board.json`
- Modify: the seven exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 1, 27, 36, 38, 56, 57, and 63.
- Produces: batch `wood-fixed-classic` with four regenerations and three bounded edits preserving source-proved grain, finish, topology, and revision identity.

**Exclusive repair sub-batch (7 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/1` `beastmaker-1000/primary` | `Hangboards/beastmaker-1000/assets/primary.png` | `edit` | `wood`, full-width; current is edit target/topology lock; remove transparent/photo-like treatment while preserving exact pockets/slopers | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/1/evidence` |
| `/records/27` `metolius.climbers-edge/primary` | `Hangboards/metolius-climbers-edge/assets/primary.png` | `regenerate` | `wood`, full-width; exact three-rail edge/sloper/jug face and source-proved mounting holes; current comparison only | `Hangboards/metolius-prime-rib/assets/primary.png` | `/records/27/evidence` |
| `/records/36` `metolius.wood-grips-compact-ii/primary` | `Hangboards/metolius-wood-grips-compact-ii/assets/primary.png` | `regenerate` | `wood`, full-width; exact two-row Compact II face and production mounting points; current comparison only | `Hangboards/metolius-prime-rib/assets/primary.png` | `/records/36/evidence` |
| `/records/38` `moon.armstrong/primary` | `Hangboards/moon-armstrong/assets/primary.png` | `edit` | `wood`, full-width; current is edit target/topology lock; convert branded/depth-labeled underscaled photo to unbranded studio treatment without changing hardwood geometry | `Hangboards/metolius-wood-grips-deluxe-ii/assets/primary.png` | `/records/38/evidence` |
| `/records/56` `tension.grindstone-original/primary` | `Hangboards/tension-grindstone-original/assets/primary.png` | `regenerate` | `wood`, full-width; 2017 base revision with jugs and source-cited edge inventory, not Pro pockets; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/56/evidence`, repeating the first-party gap search |
| `/records/57` `tension.grindstone-pro/primary` | `Hangboards/tension-grindstone-pro/assets/primary.png` | `edit` | `wood`, full-width; current is edit target/topology lock; remove transparent cutout while preserving Pro pocket/mono/jug/edge face | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/57/evidence`, repeating the first-party gap search |
| `/records/63` `trango.rock-prodigy-natural/primary` | `Hangboards/trango-rock-prodigy-natural/assets/primary.png` | `regenerate` | `wood`, split fixed; exact beech two-piece face plus complete source-proved cleat/fastener assembly; current comparison only | gap `/records/63/comparator/baselineGap` | `/records/63/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-wood-fixed-classic`, mark ownership, install exact output/context traps, and byte-copy/hash all seven current assets.**

- [ ] **Step 2: Reopen every URL and repeat every gap under records 1, 27, 36, 38, 56, 57, and 63. Save/hash minimum unmodified evidence, distinguish Grindstone 2017 from Pro and each Metolius revision, inspect source/current/comparator with `view_image`, and record actual Phase 2 evidence results.**

- [ ] **Step 3: Populate exact prompts from each record. Use `precise-object-edit` with the current local target for records 1, 38, and 57, locking topology; use `product-mockup` for records 27, 36, 56, and 63 without current as input. Require exact existing canvas, orthographic working face, sourced wood species/finish/grain/lamination only, warm diffuse response without plastic gloss, and no invented mounting parts. Use one built-in call per candidate, maximum three.**

- [ ] **Step 4: Hash/IHDR-check outputs, review evidence/current/candidate/comparator side by side, transiently verify candidates, and commit/push rejected provenance with message `Record rejected classic wood candidates` before deletion. Promote only one accepted untouched output per record.**

- [ ] **Step 5: Review all seven in Workbench normal/all-active/every individual hold or piece/hit-test states. Edit canonical paths directly only if evidence proves them wrong; do not treat visible grain or raster shading as geometry. Hash review captures and record exact results.**

- [ ] **Step 6: Run and record validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_moon_armstrong_geometry_repair.py \
    Tools/HangboardPackages/tests/test_tension_grindstone_legacy_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id wood-fixed-classic
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/beastmaker-1000 Hangboards/metolius-climbers-edge \
    Hangboards/metolius-wood-grips-compact-ii Hangboards/moon-armstrong \
    Hangboards/tension-grindstone-original Hangboards/tension-grindstone-pro \
    Hangboards/trango-rock-prodigy-natural \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair classic wood fixed presentations"
  rtk git push
  ```

  Verify removal of only the exact owned context and built-in output paths.

---

### Task 7: Repair the VerticalBoard wood fixed family

**Files:**
- Inspect and conditionally modify: `Hangboards/yy-verticalboard-evo/board.json`, `Hangboards/yy-verticalboard-first/board.json`, `Hangboards/yy-verticalboard-light/board.json`, `Hangboards/yy-verticalboard-one/board.json`
- Modify: the four exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 79–82 as four distinct physical revisions.
- Produces: batch `wood-fixed-verticalboard` with four completed regenerations; no model borrows component topology from another VerticalBoard revision.

**Exclusive repair sub-batch (4 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/79` `yy.verticalboard-evo/primary` | `Hangboards/yy-verticalboard-evo/assets/primary.png` | `regenerate` | `wood`, full-width; exact expert face, two included -10 mm magnetic wedges, integrated storage, hidden inserts/six-screw mounting without invented front holes; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/79/evidence` |
| `/records/80` `yy.verticalboard-first/primary` | `Hangboards/yy-verticalboard-first/assets/primary.png` | `regenerate` | `wood`, full-width; exact intermediate progressive-contact face and four included wall screws; optional magnetic inserts are not included; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/80/evidence` |
| `/records/81` `yy.verticalboard-light/primary` | `Hangboards/yy-verticalboard-light/assets/primary.png` | `regenerate` | `wood`, full-width; exact beginner deep-contact face and source-proved four-point installation only; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/81/evidence`, preserving the raw-page limitation |
| `/records/82` `yy.verticalboard-one/primary` | `Hangboards/yy-verticalboard-one/assets/primary.png` | `regenerate` | `wood`, full-width; exact all-level progressive face, two included wedges, integrated storage, hidden inserts/four-screw system; current comparison only | `Hangboards/beastmaker-2000/assets/primary.png` | `/records/82/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-wood-fixed-verticalboard`, mark ownership, trap exact resources, and byte-copy/hash all four originals.**

- [ ] **Step 2: Reopen each record's complete evidence independently, repeat the Light limitation search, save/hash minimum unmodified references, and manually inspect sources/current/comparator with `view_image`. Record exact reopened URLs and do not let family resemblance substitute for revision proof.**

- [ ] **Step 3: Write four separate `product-mockup` prompts populated from the exact record fields and explicit component rules in the table. Require existing untouched canvas, source-proved timber treatment, orthographic complete framing, and the Beastmaker comparator for style only. Call built-in `image_gen` once per candidate with local evidence/comparator paths, maximum three candidates per asset.**

- [ ] **Step 4: Hash/IHDR-check and manually review all candidates; transiently validate bytes; commit/push rejection provenance with message `Record rejected VerticalBoard candidates` before deleting exact rejected files. Promote one accepted untouched output per revision.**

- [ ] **Step 5: Inspect all four packages in Workbench normal/all-active/individual/hit-test states against their own primary evidence. Directly edit only proved paths, hash captures, and record truthful checks.**

- [ ] **Step 6: Run package validation, the common focused tests, full package tests, and `--phase2-partial --batch-id wood-fixed-verticalboard`; all must pass.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id wood-fixed-verticalboard
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/yy-verticalboard-evo Hangboards/yy-verticalboard-first \
    Hangboards/yy-verticalboard-light Hangboards/yy-verticalboard-one \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair VerticalBoard presentations"
  rtk git push
  ```

  Verify all exact owned temporary and external outputs are absent.

---

### Task 8: Repair Captain Fingerfood portable boards

**Files:**
- Inspect and conditionally modify: `Hangboards/captain-fingerfood-dual/board.json`, `Hangboards/captain-fingerfood-pocket/board.json`, `Hangboards/captain-fingerfood-unlevel/board.json`
- Modify: the five exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 3–7 and keeps each product's coupled presentations together.
- Produces: batch `portable-captain-fingerfood` with five completed regenerations and complete source-proved suspension components.

**Exclusive repair sub-batch (5 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/3` `captain-fingerfood.dual/primary` | `Hangboards/captain-fingerfood-dual/assets/primary.png` | `regenerate` | `wood+ropeCord`, reversible portable; straight 20 mm face, complete sourced cord/hardware; current comparison only | gap `/records/3/comparator/baselineGap` | `/records/3/evidence` |
| `/records/4` `captain-fingerfood.dual/reverse` | `Hangboards/captain-fingerfood-dual/assets/reverse.png` | `regenerate` | `wood+ropeCord`; curved 20 mm face head-on to itself with same physical assembly; current comparison only | gap `/records/4/comparator/baselineGap` | `/records/4/evidence` |
| `/records/5` `captain-fingerfood.pocket/primary` | `Hangboards/captain-fingerfood-pocket/assets/primary.png` | `regenerate` | `wood+ropeCord`; exact 15/20 mm face and outer contacts plus suspension topology; current comparison only | gap `/records/5/comparator/baselineGap` | `/records/5/evidence` |
| `/records/6` `captain-fingerfood.unlevel/primary` | `Hangboards/captain-fingerfood-unlevel/assets/primary.png` | `regenerate` | `wood+ropeCord`; curved 20 mm face and complete suspension assembly; current comparison only | gap `/records/6/comparator/baselineGap` | `/records/6/evidence` |
| `/records/7` `captain-fingerfood.unlevel/reverse` | `Hangboards/captain-fingerfood-unlevel/assets/reverse.png` | `regenerate` | `wood+ropeCord`; curved 25 mm face head-on to itself and same sourced assembly; current comparison only | gap `/records/7/comparator/baselineGap` | `/records/7/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-portable-captain-fingerfood`, mark ownership, trap exact resources, and byte-copy/hash all five current assets.**

- [ ] **Step 2: Reopen all official/independent URLs for records 3–7, repeat gaps, save/hash minimum unmodified face and suspension references, inspect every source/current/gap image manually with `view_image`, and record actual reviews. Verify reverse faces as separately usable surfaces rather than inferring them from fronts.**

- [ ] **Step 3: Populate five `product-mockup` prompts from literal manifest fields. Require complete source-proved ropes/knots/hardware, exact wood finish, each selected face orthographic to itself, exact existing canvas, uncropped hardware, and no inferred depths/components. Call built-in imagegen once per candidate through exact local paths, maximum three per asset.**

- [ ] **Step 4: Hash/IHDR-check untouched candidates; manually compare sources/current/candidate/gap; transiently verify bytes; commit/push rejected provenance with message `Record rejected Captain Fingerfood candidates`; then delete only recorded rejection/input bytes and promote one accepted output per record.**

- [ ] **Step 5: Review all five presentations in Workbench normal/all-active/every individual hold and piece/hit-test states. Directly edit only source-proved errors and keep coupled physical geometry coherent without raster-derived alignment. Hash captures and record all checks.**

- [ ] **Step 6: Run and record gates.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id portable-captain-fingerfood
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/captain-fingerfood-dual Hangboards/captain-fingerfood-pocket \
    Hangboards/captain-fingerfood-unlevel \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair Captain Fingerfood presentations"
  rtk git push
  ```

  Verify exact owned cleanup.

---

### Task 9: Repair Helium Mobile, NUG, and Light Rail reversible boards

**Files:**
- Inspect and conditionally modify: `Hangboards/crimptonite-helium-mobile/board.json`, `Hangboards/frictitious-nug/board.json`, `Hangboards/metolius-light-rail-2/board.json`
- Modify: the six exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 8, 9, 16, 17, 30, and 31; preserves every coupled face in one task.
- Produces: batch `portable-reversible-edges` with three edits and three regenerations.

**Exclusive repair sub-batch (6 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/8` `crimptonite.helium-mobile/primary` | `Hangboards/crimptonite-helium-mobile/assets/primary.png` | `edit` | `wood+ropeCord`; current edit target/topology lock for updated front edge/jug face; preserve three recesses and cited rough-side/smooth-contact constraint without universalizing owner measurements | gap `/records/8/comparator/baselineGap` | `/records/8/evidence` |
| `/records/9` `crimptonite.helium-mobile/reverse` | `Hangboards/crimptonite-helium-mobile/assets/reverse.png` | `edit` | `wood+ropeCord`; current edit target/topology lock; make back jug/sloper head-on while retaining exact product | gap `/records/9/comparator/baselineGap` | `/records/9/evidence` |
| `/records/16` `frictitious.nug/primary` | `Hangboards/frictitious-nug/assets/primary.png` | `regenerate` | `wood+ropeCord`; exact 20/25 mm face and source-proved cord; current comparison only; current official beech governs species | gap `/records/16/comparator/baselineGap` | `/records/16/evidence`, preserving poplar/beech conflict roles |
| `/records/17` `frictitious.nug/reverse` | `Hangboards/frictitious-nug/assets/reverse.png` | `regenerate` | `wood+ropeCord`; exact 8/13 mm face and same sourced cord assembly; current comparison only | gap `/records/17/comparator/baselineGap` | `/records/17/evidence` |
| `/records/30` `metolius.light-rail-2/20mm-side` | `Hangboards/metolius-light-rail-2/assets/primary.png` | `regenerate` | `wood+ropeCord`; exact reversible face only if reopened evidence resolves/contains the recorded nominal 20 vs 19/26 mm conflict; current comparison only | gap `/records/30/comparator/baselineGap` | `/records/30/evidence` |
| `/records/31` `metolius.light-rail-2/15mm-side` | `Hangboards/metolius-light-rail-2/assets/15mm-surface.png` | `edit` | `wood+ropeCord`; current edit target/topology lock; restore uncropped complete suspension cord only, keep orthographic 15 mm face | gap `/records/31/comparator/baselineGap` | `/records/31/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-portable-reversible-edges`, mark ownership, install exact traps, and byte-copy/hash all six originals.**

- [ ] **Step 2: Independently reopen and inspect every routed URL/gap/conflict. Save/hash only minimum unmodified references; inspect all source/current/gap images with `view_image`; record actual review. Do not average NUG species evidence or Light Rail depth conflicts. If the 20 mm face cannot be tied to an exact revision, block that record instead of inventing topology.**

- [ ] **Step 3: Populate `precise-object-edit` prompts for records 8, 9, and 31 with current targets and invariant topology; populate `product-mockup` prompts for 16, 17, and 30 without current inputs. Route exact record material/surface/revision/findings/source roles/canvas, require complete uncropped cord/hardware and face-head-on composition, and apply no post-processing. One built-in call per candidate, maximum three.**

- [ ] **Step 4: Hash/IHDR-check, manually review, transiently verify, and record all candidate dispositions. Commit/push rejections with message `Record rejected reversible edge candidates` before deleting exact bytes. Promote only accepted original outputs.**

- [ ] **Step 5: Review all six presentations in Workbench normal/all-active/individual/hit-test states against primary evidence. Correct paths directly only when proved and never infer one face's geometry from another. Hash captures and record truth.**

- [ ] **Step 6: Run package, focused, full-suite, and partial batch validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id portable-reversible-edges
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/crimptonite-helium-mobile Hangboards/frictitious-nug \
    Hangboards/metolius-light-rail-2 \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair reversible edge presentations"
  rtk git push
  ```

  Verify exact cleanup and accepted-output placement.

---

### Task 10: Repair portable lifting and suspended products

**Files:**
- Inspect and conditionally modify: `Hangboards/lattice-mxedge-lift-large/board.json`, `Hangboards/lattice-mxedge-lift-small/board.json`, `Hangboards/metolius-rock-rings-3d/board.json`, `Hangboards/plateau-lifting-edge/board.json`
- Modify: the four exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 24, 25, 34, and 47.
- Produces: batch `portable-lifting-suspended` with two edits and two regenerations.

**Exclusive repair sub-batch (4 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/24` `lattice.mxedge-lift-large/primary` | `Hangboards/lattice-mxedge-lift-large/assets/primary.png` | `edit` | `wood+ropeCord`, lifting edge; current edit target/topology lock; remove label/photo/crop treatment and retain complete MXLarge multi-edge assembly | gap `/records/24/comparator/baselineGap` | `/records/24/evidence` |
| `/records/25` `lattice.mxedge-lift-small/primary` | `Hangboards/lattice-mxedge-lift-small/assets/primary.png` | `edit` | `wood+ropeCord`, lifting edge; current edit target/topology lock; remove label/photo/crop treatment and retain complete MXSmall assembly | gap `/records/25/comparator/baselineGap` | `/records/25/evidence` |
| `/records/34` `metolius.rock-rings-3d/front-pair` | `Hangboards/metolius-rock-rings-3d/assets/primary.png` | `regenerate` | `resin+ropeCord`, suspended portable; complete two-unit cords/knots and exact jug/deep-pocket/flat-edge/lower-pocket topology, no false wood; current comparison only | gap `/records/34/comparator/baselineGap` | `/records/34/evidence` |
| `/records/47` `plateau.lifting-edge/primary` | `Hangboards/plateau-lifting-edge/assets/primary.png` | `regenerate` | `metal+wood+ropeCord+mixedOther`, lifting edge; exact aluminum body, oak insert, 15/10 mm blocker, complete 6 mm Edelrid PES cord; current comparison only | gap `/records/47/comparator/baselineGap` | `/records/47/evidence`, repeating independent gap search |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-portable-lifting-suspended`, mark ownership, trap exact resources, and byte-copy/hash all four originals.**

- [ ] **Step 2: Reopen all evidence URLs/gaps, save/hash minimum unmodified full-assembly and material views, inspect sources/current/comparator gaps with `view_image`, and record actual review. Do not infer missing Plateau independent facts.**

- [ ] **Step 3: Use `precise-object-edit` for records 24 and 25 with target topology locked; use `product-mockup` for 34 and 47. Populate literal record revision/surface/material/component/findings/source-role/canvas fields, require complete uncropped ropes/knots/blockers, separate material cues, orthographic surface view, and no branding/text. Use one built-in call per candidate, maximum three.**

- [ ] **Step 4: Hash/IHDR-check and manually compare all candidates; transiently verify; commit/push rejection provenance with message `Record rejected lifting and suspended candidates` before exact deletion; promote one accepted untouched candidate per record.**

- [ ] **Step 5: Workbench-review normal/all-active/every hold or piece/hit testing for all four presentations. Directly correct only primary-evidence mismatches, hash captures, and record all results.**

- [ ] **Step 6: Run and record validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id portable-lifting-suspended
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/lattice-mxedge-lift-large Hangboards/lattice-mxedge-lift-small \
    Hangboards/metolius-rock-rings-3d Hangboards/plateau-lifting-edge \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair lifting and suspended presentations"
  rtk git push
  ```

  Verify exact owned context and external output cleanup.

---

### Task 11: Repair Port-A-Board and Flash Board multi-orientation products

**Files:**
- Inspect and conditionally modify: `Hangboards/frictitious-port-a-board/board.json`, `Hangboards/tension-flash-board/board.json`
- Modify: the seven exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 18–20 and 52–55; preserves all coupled presentations for each physical product.
- Produces: batch `multi-port-a-board-flash` with three edits and four regenerations.

**Exclusive repair sub-batch (7 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/18` `frictitious.port-a-board/primary` | `Hangboards/frictitious-port-a-board/assets/primary.png` | `edit` | `wood+ropeCord`, multi-orientation; current edit target/topology lock for front edge/pocket face; remove branded/photo-like treatment, retain complete hardware | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/18/evidence` |
| `/records/19` `frictitious.port-a-board/back` | `Hangboards/frictitious-port-a-board/assets/back.png` | `edit` | `wood+ropeCord`; current edit target/topology lock for back edge/jug face head-on to itself | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/19/evidence` |
| `/records/20` `frictitious.port-a-board/side` | `Hangboards/frictitious-port-a-board/assets/side.png` | `edit` | `wood+ropeCord`; current edit target/topology lock for narrow side pinch, with the side working surface orthographic | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/20/evidence` |
| `/records/52` `tension.flash-board/three-edge-upright` | `Hangboards/tension-flash-board/assets/primary.png` | `regenerate` | `wood+ropeCord`; complete adjustable cord/knots and upright three-edge cylinder surface; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/52/evidence` |
| `/records/53` `tension.flash-board/three-edge-inverted` | `Hangboards/tension-flash-board/assets/three-edge-inverted.png` | `regenerate` | `wood+ropeCord`; complete adjustable cord/knots, inverted three-edge surface, no transparent cutout; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/53/evidence` |
| `/records/54` `tension.flash-board/two-edge-upright` | `Hangboards/tension-flash-board/assets/two-edge-surface.png` | `regenerate` | `wood+ropeCord`; complete adjustable cord/knots and upright two-edge cylinder surface; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/54/evidence` |
| `/records/55` `tension.flash-board/two-edge-inverted` | `Hangboards/tension-flash-board/assets/two-edge-inverted.png` | `regenerate` | `wood+ropeCord`; complete adjustable cord/knots and inverted two-edge surface; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/55/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-multi-port-a-board-flash`, mark ownership, install exact traps, and byte-copy/hash all seven current assets.**

- [ ] **Step 2: Freshly reopen every routed URL/gap for all seven records, including direct proof that every back/side/inversion is intended for use. Save/hash minimum unmodified surface and full-cord references, inspect sources/current/Mini Bar comparator with `view_image`, and record literal review results. Preserve Tension's 8/10/15/20 mm naming and do not reintroduce 6 mm.**

- [ ] **Step 3: Use `precise-object-edit` for Port-A-Board records with current targets as topology locks; use `product-mockup` for Flash Board records without current inputs. Populate every literal revision/surface/material/source-role/finding/canvas field, require selected surface head-on, whole product/cords uncropped, and use Mini Bar only for style. Call built-in `image_gen` separately for each candidate, at most three per asset.**

- [ ] **Step 4: Hash/IHDR-check and manually review each candidate; transiently verify; commit/push rejection provenance with message `Record rejected Port-A-Board and Flash Board candidates` before deletion; promote only one exact accepted output per record.**

- [ ] **Step 5: Workbench-review all seven normal/all-active/every individual hold or piece/hit-test states. Verify presentation switching scopes the correct holds. Directly edit paths only when primary evidence proves them wrong; never register one orientation to another. Hash captures and record results.**

- [ ] **Step 6: Run and record validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id multi-port-a-board-flash
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/frictitious-port-a-board Hangboards/tension-flash-board \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair Port-A-Board and Flash Board presentations"
  rtk git push
  ```

  Verify exact owned cleanup and no comparator/source bytes in packages.

---

### Task 12: Edit all four Poker working faces

**Files:**
- Inspect and conditionally modify: `Hangboards/owl-climb-poker/board.json`
- Modify: the four exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 43–46 and the Phase 1 ruling that local face IDs A–D are analyst mappings, not manufacturer numeric labels.
- Produces: batch `multi-poker` with four bounded brand-removal edits and no topology/depth reassignment.

**Exclusive repair sub-batch (4 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/43` `owl-climb.poker/face-a` | `Hangboards/owl-climb-poker/assets/face-a.png` | `edit` | `wood+mixedOther`; current edit target/topology lock for flat-center face; remove only engraved Owl mark | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/43/evidence`, including fresh first-party route attempt |
| `/records/44` `owl-climb.poker/face-b` | `Hangboards/owl-climb-poker/assets/face-b.png` | `edit` | `wood+mixedOther`; current edit target/topology lock for deep-sloper face; remove only mark | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/44/evidence` |
| `/records/45` `owl-climb.poker/face-c` | `Hangboards/owl-climb-poker/assets/face-c.png` | `edit` | `wood+mixedOther`; current edit target/topology lock for shallow half-round face; remove only mark | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/45/evidence` |
| `/records/46` `owl-climb.poker/face-d` | `Hangboards/owl-climb-poker/assets/face-d.png` | `edit` | `wood+mixedOther`; current edit target/topology lock for deep rounded-recess face; remove only mark | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/46/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-multi-poker`, record ownership, trap exact resources, and byte-copy/hash all four originals.**

- [ ] **Step 2: Reopen all record evidence and the direct first-party route for each face. Save/hash minimum unmodified four-face references, inspect sources/current/Mini Bar style comparator with `view_image`, and record actual result. Preserve published board-level depth sequences as board-level facts; do not assign them to analyst face IDs without direct proof.**

- [ ] **Step 3: Populate four `precise-object-edit` prompts with each current asset first, exact 1980×300 canvas, invariants locking the whole bar/support/contact geometry/material/framing, and one bounded request: remove the engraved brand mark into the same source-proved wood surface. No other change is permitted. Make one built-in call per candidate, maximum three per face.**

- [ ] **Step 4: Hash/IHDR-check and compare source/current/candidate/comparator for each face. Reject any topology, shading, framing, support, or material drift. Transiently verify and commit/push rejections with message `Record rejected Poker edit candidates` before deletion; promote one accepted output per face.**

- [ ] **Step 5: Workbench-review all four faces in normal/all-active/every hold or piece/hit-test states and presentation switching. Direct geometry changes are expected only if fresh primary evidence proves an existing path wrong; do not use candidate pixels. Hash captures and record checks.**

- [ ] **Step 6: Run package validation, common focused tests, full package tests, and partial validation for `multi-poker`.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id multi-poker
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/owl-climb-poker \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Remove branding from Poker presentations"
  rtk git push
  ```

  Verify exact owned cleanup.

---

### Task 13: Regenerate all four Rock Prodigy Pivot orientations

**Files:**
- Inspect and conditionally modify: `Hangboards/trango-rock-prodigy-pivot/board.json`
- Modify: the four exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 64–67, the Pivot quick-start guide, and the Pivot package as the repository's direct-geometry structural/path-style precedent only.
- Produces: batch `multi-rock-prodigy-pivot` with four complete source-proved orientations and quad-cleat assembly.

**Exclusive repair sub-batch (4 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/64` `trango.rock-prodigy-pivot/orientation-1` | `Hangboards/trango-rock-prodigy-pivot/assets/primary.png` | `regenerate` | `urethane`; exact orientation-1 jug/sloper/pinch/supported-crimp face and quad-cleat assembly, controlled molded relief; current comparison only | gap `/records/64/comparator/baselineGap` | `/records/64/evidence` |
| `/records/65` `trango.rock-prodigy-pivot/orientation-2` | `Hangboards/trango-rock-prodigy-pivot/assets/orientation-2.png` | `regenerate` | `urethane`; exact orientation-2 mono/gaston/small-crimp face and same sourced assembly; current comparison only | gap `/records/65/comparator/baselineGap` | `/records/65/evidence` |
| `/records/66` `trango.rock-prodigy-pivot/orientation-3` | `Hangboards/trango-rock-prodigy-pivot/assets/orientation-3.png` | `regenerate` | `urethane`; exact orientation-3 pocket/supported-crimp/sloper face; current comparison only | gap `/records/66/comparator/baselineGap` | `/records/66/evidence` |
| `/records/67` `trango.rock-prodigy-pivot/orientation-4` | `Hangboards/trango-rock-prodigy-pivot/assets/orientation-4.png` | `regenerate` | `urethane`; exact orientation-4 compression-pinch/mono face; current comparison only | gap `/records/67/comparator/baselineGap` | `/records/67/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-multi-rock-prodigy-pivot`, mark ownership, install exact traps, and byte-copy/hash all four originals.**

- [ ] **Step 2: Reopen every official/independent URL and quick-start evidence per orientation. Save/hash minimum unmodified orientation and cleat references, inspect source/current/gap images with `view_image`, and record exact reviews. A picture of one rotation may establish the shared assembly but cannot prove another face's contacts.**

- [ ] **Step 3: Write four separate `product-mockup` prompts from each record's literal fields, with exact 1774×887 untouched canvas, selected surface orthographic, complete quad-cleat assembly, matte urethane and controlled relief, and no inferred contacts/hardware. Use one built-in call per candidate, maximum three per orientation.**

- [ ] **Step 4: Hash/IHDR-check and side-by-side review all candidates; transiently verify; commit/push rejections with message `Record rejected Rock Prodigy Pivot candidates` before deletion; promote exactly one accepted output per orientation.**

- [ ] **Step 5: Workbench-review normal/all-active/every individual hold/piece/hit testing for each orientation and presentation switching. Directly redraw any proved path; exact left/right mirroring is permitted only where the primary guide proves physical symmetry. Hash captures and record checks.**

- [ ] **Step 6: Run and record validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_coderabbit_mirrored_geometry.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id multi-rock-prodigy-pivot
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/trango-rock-prodigy-pivot \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair Rock Prodigy Pivot presentations"
  rtk git push
  ```

  Verify exact context/output cleanup.

---

### Task 14: Regenerate the four non-kept Baguette Evo surfaces

**Files:**
- Inspect and conditionally modify: `Hangboards/yy-baguette-evo/board.json`
- Modify: the four exclusive assets declared below
- Preserve byte-for-byte: the `rounded-tray` keep presentation in the same package
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 69–72; record 73 remains an immutable keep in the same product.
- Produces: batch `multi-baguette-evo` with four regenerations while proving the accepted tray bytes remain unchanged.

**Exclusive repair sub-batch (4 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/69` `yy.baguette-evo/paired-25-20-15-10` | `Hangboards/yy-baguette-evo/assets/primary.png` | `regenerate` | `wood+ropeCord`; paired 25/20/15/10 surface with complete source-proved cords; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/69/evidence` |
| `/records/70` `yy.baguette-evo/paired-12-8-6` | `Hangboards/yy-baguette-evo/assets/shallow-pairs.png` | `regenerate` | `wood+ropeCord`; paired 12/8/6 surface and complete cords; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/70/evidence` |
| `/records/71` `yy.baguette-evo/central-30-25` | `Hangboards/yy-baguette-evo/assets/central-30-25.png` | `regenerate` | `wood+ropeCord`; central 30/25 surface and complete cords; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/71/evidence` |
| `/records/72` `yy.baguette-evo/central-20-6` | `Hangboards/yy-baguette-evo/assets/central-20-6.png` | `regenerate` | `wood+ropeCord`; central 20/6 surface and complete cords; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/72/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-multi-baguette-evo`, mark ownership, install exact traps, byte-copy/hash the four targets, and separately record the keep tray hash as a no-change assertion.**

- [ ] **Step 2: Reopen every record's official/independent evidence and conflicts. Save/hash minimum unmodified surface/cord references, inspect sources/current/Mini Bar comparator plus the accepted tray with `view_image`, and record review. Use exact current Evo evidence (6–30 mm, 52 cm, 550 g) and do not import the earlier 5 mm/12–5 mm/415 g configuration.**

- [ ] **Step 3: Populate four `product-mockup` prompts with exact record surfaces/materials/canvas/source roles, full uncropped polyester cord, selected surface head-on, and Mini Bar style-only treatment. Do not infer a different cord chemistry. Call built-in imagegen once per candidate, maximum three per surface.**

- [ ] **Step 4: Hash/IHDR-check and manually review; transiently verify; commit/push rejection provenance with message `Record rejected Baguette Evo candidates` before exact deletion; promote one accepted untouched output per changed surface. Re-hash the tray and fail if it changed.**

- [ ] **Step 5: Workbench-review all four changed surfaces normal/all-active/individual/hit-test plus presentation switching, and visually re-check the kept tray without modifying it. Directly edit only source-proved canonical-path errors. Hash captures and record checks.**

- [ ] **Step 6: Run package validation, common focused tests, full package tests, and partial batch validation; assert the keep tray hash still equals `/records/73/currentAsset/sha256`.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id multi-baguette-evo
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/yy-baguette-evo \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair Baguette Evo presentations"
  rtk git push
  ```

  Verify exact owned cleanup and immutable tray bytes.

---

### Task 15: Regenerate Penta Evo and both TravelBoard faces

**Files:**
- Inspect and conditionally modify: `Hangboards/yy-penta-evo/board.json`, `Hangboards/yy-travelboard/board.json`
- Modify: the three exclusive assets declared below
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: records 76–78 and keeps both TravelBoard faces coupled.
- Produces: batch `multi-yy-penta-travel` with three completed regenerations.

**Exclusive repair sub-batch (3 presentations):**

| Record | Asset path | Mode | Material/render and current role | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/76` `yy.penta-evo/front-pair` | `Hangboards/yy-penta-evo/assets/primary.png` | `regenerate` | `wood+ropeCord`; paired front orientation, ring jug, distributed contacts, and complete source-proved cords; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/76/evidence`, preserving seven/eight grip count conflict |
| `/records/77` `yy.travelboard/front-25-15` | `Hangboards/yy-travelboard/assets/primary.png` | `regenerate` | `wood+ropeCord`; front 25/15 rails with jug/monos and complete cords; current comparison only; do not resolve species by averaging | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/77/evidence`, preserving beech/rubberwood conflict |
| `/records/78` `yy.travelboard/reverse-10` | `Hangboards/yy-travelboard/assets/reverse.png` | `regenerate` | `wood+ropeCord`; reverse 10 mm rail working face head-on to itself and same complete physical assembly; current comparison only | `Hangboards/lattice-mini-bar/assets/primary.png` | `/records/78/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-multi-yy-penta-travel`, mark ownership, trap exact resources, and byte-copy/hash all three originals.**

- [ ] **Step 2: Reopen all routed evidence URLs/gaps/conflicts, save/hash minimum unmodified orientation/cord references, inspect source/current/Mini Bar comparator with `view_image`, and record actual review. Preserve unresolved Penta count and TravelBoard species conflicts; omit details not established for the depicted revision.**

- [ ] **Step 3: Populate three `product-mockup` prompts from literal record fields with complete polyester cords, selected face orthographic, existing exact canvas, material facts only where source-resolved, and Mini Bar style only. Call built-in imagegen once per candidate, maximum three per asset.**

- [ ] **Step 4: Hash/IHDR-check and manually review; transiently verify; commit/push rejection provenance with message `Record rejected Penta and TravelBoard candidates` before deletion; promote only accepted untouched outputs.**

- [ ] **Step 5: Workbench-review normal/all-active/every individual hold or piece/hit testing for all three and presentation switching for TravelBoard. Directly edit only proved paths, hash captures, and record checks.**

- [ ] **Step 6: Run and record package, focused, full-suite, and partial validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id multi-yy-penta-travel
  ```

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/yy-penta-evo Hangboards/yy-travelboard \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Repair Penta Evo and TravelBoard presentations"
  rtk git push
  ```

  Verify exact owned cleanup.

---

### Task 16: Remove the unsupported Lattice Mini Bar end presentation

**Files:**
- Modify: `Hangboards/lattice-mini-bar/board.json`
- Delete: the one exclusive asset declared below
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py`
- Modify if removal lifecycle coverage needs a real-catalog assertion: `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: record 23's canonical sourced unusability proof and the package's current inventory.
- Produces: batch `lattice-mini-bar-removal`, a historical removal record, and a valid one-presentation Mini Bar package without `mini-pinch`.

**Exclusive repair sub-batch (1 sourced removal):**

| Record | Asset path | Mode | Inventory/geometry action | Comparator | Evidence to reopen |
| --- | --- | --- | --- | --- | --- |
| `/records/23` `lattice.mini-bar/end` | `Hangboards/lattice-mini-bar/assets/end.png` | `removeUnsupportedPresentation` | remove presentation ID `end`, hold ID `mini-pinch`, and only this PNG; preserve `primary`, `ergonomic-jug`, `edge-10`, `edge-20`, all their geometry, and primary bytes | `Hangboards/lattice-mini-bar/assets/primary.png` remains the accepted self-baseline | every URL under `/records/23/evidence` |

- [ ] **Step 1: Create `.context/sincere-otter-phase2-lattice-mini-bar-removal`, add the owner marker/trap, and hash/copy the complete pre-removal `board.json`, `primary.png`, and end PNG for exact audit/rollback. No imagegen call is permitted.**

- [ ] **Step 2: Freshly reopen every official and independent URL under `/records/23/evidence`. Confirm the four lengthwise grips are selected by flipping the bar and the declared end cap is not a usable working surface. Record literal reopened URLs and the actual date; if canonical unusability proof no longer holds, block instead of deleting.**

- [ ] **Step 3: Write a failing real-catalog inventory test before mutation.**

  Assert Mini Bar has exactly one `primary` presentation, exactly the three hold IDs `ergonomic-jug`, `edge-10`, and `edge-20`, no hold with `presentationID == "end"`, and an asset set of exactly `{"primary.png"}`. Also assert record 23 remains historical and authorizes the absent presentation/hold/asset.

- [ ] **Step 4: Run the focused tests and confirm RED.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py
  ```

  Expected: FAIL because `end`, `mini-pinch`, and the end PNG still exist.

- [ ] **Step 5: Perform the narrow inventory/geometry removal.**

  Use `apply_patch` to remove only the `end` presentation object and `mini-pinch` hold object from `board.json`, then delete only the exact end PNG. Do not change package identity, primary presentation, primary asset bytes, the remaining three holds, their canonical paths, or any unrelated package field. Set record 23 final decision to removed, generation to none/empty, Workbench visual checks to `notRequired` with the sourced-removal reason, and validation truth to actual results.

- [ ] **Step 6: Prove narrowness and validate.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id lattice-mini-bar-removal
  rtk git diff -- Hangboards/lattice-mini-bar/board.json
  ```

  Expected: package/tests/batch PASS; current inventory becomes 61 packages/84 presentations; diff shows only the `end` presentation and `mini-pinch` hold removed; re-hashed primary bytes equal `/records/22/currentAsset/sha256`.

- [ ] **Step 7: Commit, push, and clean.**

  ```bash
  rtk git add Hangboards/lattice-mini-bar/board.json \
    Hangboards/lattice-mini-bar/assets/end.png \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Remove unsupported Mini Bar end presentation"
  rtk git push
  ```

  Remove and verify the exact owned audit/rollback directory only after the committed removal passes.

---

### Task 17: Perform the complete cross-catalog smoothing and framing review

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`
- Reopen for rework only through its existing exclusive owner: a failed record's package asset and conditionally its `board.json`

**Interfaces:**
- Consumes: all 15 passed repair batches, 84 current presentation PNGs, 85 historical records, 19 immutable keeps, accepted candidate hashes, comparators, and material/form-factor cohorts.
- Produces: a passed `crossCatalogReview` final check or a failure routed back to the one existing owning batch; this task does not create a new asset assignment.

- [ ] **Step 1: Create `.context/sincere-otter-phase2-cross-catalog-review`, immediately mark ownership, and install exact cleanup traps for captures and any review processes.**

- [ ] **Step 2: Generate a deterministic review inventory without analyzing pixels.**

  Use the Phase 2 validator report and manifest records to list the 84 current asset paths by material and form factor. Do not use image similarity, pixel statistics, automatic cropping, detection, masks, contours, or a generated contact-sheet pipeline. Manually open the original-sized files and their declared comparators with `view_image` or Workbench; captures may document what the human saw but may not decide pass/fail automatically.

- [ ] **Step 3: Review every current presentation across and within cohorts.**

  For each of the 84 presentations, confirm off-white background, neutral lighting direction, restrained shadow, clean antialiasing, complete uncropped product, cohort-consistent scale, and continuous material-appropriate smoothing. Recheck wood grain/laminations, molded/resin/urethane matte response, metal finish, stone/mineral density, and mixed components independently. For every repaired record, compare official evidence, independent evidence or recorded gap, Phase 1 current role, accepted output, and comparator/gap. For each keep, compare its immutable current bytes but do not replace it merely for uniformity.

- [ ] **Step 4: Route any defect back to its exclusive repair owner.**

  If a repaired asset fails, mark its existing batch check failed, preserve review capture hash/reason, and have the controller dispatch a fresh rework subagent for that same batch/record. The rework repeats live evidence, built-in-only one-call-per-candidate generation, transient hash/provenance, Workbench review, validation, commit, push, and cleanup. Do not repair the asset inside Task 17 and do not assign it to another batch. If an immutable keep appears genuinely nonconforming, stop for spec clarification rather than silently changing its Phase 1 decision.

- [ ] **Step 5: Record the passed manual review.**

  After all 84 pass, hash the owned review captures/log, set root `crossCatalogReview` to passed with actual date, reviewer decision, reviewed counts by material/form factor, capture hashes, and explicit confirmation that all 19 keeps retained original hashes. Update every completed record's `crossCatalogConsistency` explanation only when the review yields new evidence-specific wording; never turn the comparator into geometry proof.

- [ ] **Step 6: Re-run full package and partial manifest validation.**

  ```bash
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial
  ```

  Expected: 61 packages, 84 inventory presentations, 19 keeps, 65 completed image repairs, one completed removal, and zero pending/blocked records.

- [ ] **Step 7: Commit, push, and clean review artifacts.**

  ```bash
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Review hangboard catalog presentation consistency"
  rtk git push
  ```

  Trigger the exact cleanup trap and verify the owned review directory/resources are absent.

---

### Task 18: Build, install, and visually validate on isolated iOS Simulators

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`
- Create temporarily and delete before completion: `.context/sincere-otter-phase2-ios-validation/*`, `.context/DerivedData`, `.context/paseo-pending-simulators`, `.context/paseo-owned-simulators`

**Interfaces:**
- Consumes: passed cross-catalog review, `validate-hang-ten-ios`, `docs/IOS_SIMULATOR_VALIDATION.md`, `docs/IOS_RUNTIME_SERVICES.md`, 61 valid packages/84 presentations, and exact simulator ownership `sincere-otter`.
- Produces: a signed bounded `build-for-testing`, phone and tablet catalog/runtime review, exact capture hashes/results, passed build/simulator checks, and verified deletion of owned simulators/artifacts.

- [ ] **Step 1: Invoke the required validation skill and read its dependencies completely.**

  Use `validate-hang-ten-ios` for this task. Read `.codex/skills/validate-hang-ten-ios/SKILL.md`, `docs/IOS_SIMULATOR_VALIDATION.md`, and `docs/IOS_RUNTIME_SERVICES.md` completely in the execution session before any simulator operation. Do not substitute a generic simulator recipe.

- [ ] **Step 2: Establish exact workspace ownership and traps before `simctl create`.**

  Set `workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"`, verify its final component is exactly `sincere-otter`, create `.context/sincere-otter-phase2-ios-validation/OWNER-sincere-otter`, and install the skill's `EXIT`/`INT`/`TERM` archive trap. The trap calls `scripts/paseo-resource-cleanup.sh archive` with the exact workspace path and deletes only `.context/DerivedData` plus exact Phase 2 iOS captures/logs. It must preserve pending/owned manifests if archive cleanup fails.

- [ ] **Step 3: Create and register representative phone and tablet devices safely.**

  Run `rtk xcrun simctl list devicetypes` and `rtk xcrun simctl list runtimes`; choose one available current iPhone device type and one available current iPad device type on an available iOS runtime, and record their literal IDs. Create `Hang Ten Paseo sincere-otter Review` and `Hang Ten Paseo sincere-otter Tablet Review`. Validate each returned UUID; append each UUID to `.context/paseo-pending-simulators` before any owned-manifest write/boot/build, then append it to `.context/paseo-owned-simulators`. Use the two exact UUIDs for every command; never use `booted`.

- [ ] **Step 4: Boot both devices with bounded readiness checks and build for testing.**

  Follow the skill's 40-attempt/4-second-command/3-second-interval launch-services poll for each UUID. Keep signing enabled. Run the bounded build against the phone UUID and workspace-owned Derived Data:

  ```bash
  rtk xcodebuild build-for-testing \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$phone_simulator_uuid" \
    -derivedDataPath .context/DerivedData
  ```

  Record the literal expanded command, UUID, Xcode/runtime/device versions, exit status, and app path. Inspect the generated `HangTen.app-Simulated.xcent` for `com.apple.developer.healthkit = true`; do not disable signing.

- [ ] **Step 5: Install and prove app provenance on both exact UUIDs.**

  Terminate only `com.hangten.training` on each owned UUID, install `.context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app`, launch by exact UUID, and run `xcrun simctl get_app_container UUID com.hangten.training app`. Compare the built and installed binary hash so another workspace's build cannot be mistaken for this one.

- [ ] **Step 6: Validate catalog, plans, presentations, and hold hit testing on phone and tablet.**

  Use `SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_PICKER=1` to inspect catalog thumbnails for every repaired product family and preserved baselines: no crop, transparency, labels, source photos, wrong material, or missing components. Select at least one board from every repair batch on both device classes through the accessibility identifier formed by `boardPicker.board.` followed by that selected board's literal `TrainingBoard.id`; open the identifier formed by `boardPicker.holdSpecs.` followed by the same literal ID, and inspect the normal board map. Use each visible presentation picker for representative coupled products (Port-A-Board, Flash Board, Poker, Pivot, Baguette Evo, and TravelBoard), tap representative contacts across every visible presentation, and confirm the intended individual hold highlights and hold card; taps outside paths must not select a hold. Exercise all-active/multi-hold states through compatible plan/workout previews, and use `HANGTEN_REVIEW_PLAN=1`, `HANGTEN_REVIEW_WORKOUT=1`, and literal `HANGTEN_REVIEW_STEP` values to confirm the plan view, selected board, active highlight, presentation auto-selection, and hit-test alignment. Repeat representative states in iPhone portrait/landscape and iPad portrait/landscape.

- [ ] **Step 7: Capture and manually inspect exact visual evidence.**

  Save phone/tablet catalog, plan, normal, active, individual-hold, hit-test, and presentation-selector screenshots only under `.context/sincere-otter-phase2-ios-validation`. If the runtime emits landscape UI in portrait pixels, follow the skill's inspect-then-rotate rule for review copies; do not modify package assets. Hash every capture, manually inspect geometry/highlight alignment, text clipping, framing, and selector correctness, and record hashes plus the exact board/presentation/hold/device/state in the manifest/narrative.

- [ ] **Step 8: Record build/simulator truth and handle failure narrowly.**

  Mark per-record/global build and simulator checks passed only for states actually exercised. Use `notRequired` with a concrete global-representative reason where a removed presentation cannot be shown. If any visual fails, mark the check failed, preserve the capture hash/reason, route asset/geometry rework back to its owning batch, and rerun Task 17 plus this task after the new commit; do not accept compile success as visual validation.

- [ ] **Step 9: Archive and verify exact simulator/resource cleanup.**

  On success, failure, or interruption, run the installed archive trap. It must verify each exact UUID has the `Hang Ten Paseo sincere-otter ` name prefix before shutdown/deletion, consume pending/owned records only after successful cleanup, remove exact Derived Data and capture paths, and leave shared/unknown simulators alone. Re-query both exact UUIDs and verify they no longer exist before marking simulator cleanup passed.

- [ ] **Step 10: Commit and push durable QA results only.**

  ```bash
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Validate remediated hangboards on iOS"
  rtk git push
  ```

  Expected: no simulator, capture, Derived Data, or other `.context` artifact is staged.

---

### Task 19: Run the final 61-package/84-presentation gate and clean all owned state

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: all passed batches, passed cross-catalog and iOS checks, complete package tests, and cleaned workspace-owned resources.
- Produces: the final schema-version-2 report: 61 packages, 85 historical records, 84 current presentations, 19 unchanged keeps, 17 completed edits, 48 completed regenerations, one completed removal, zero pending/blocked records, and no owned context artifacts.

- [ ] **Step 1: Recompute exact inventory and immutable keep facts.**

  Use the validator, not hand counts, to prove 61 package IDs and 84 declared PNGs. Re-hash every keep and require equality with its original `currentAsset.sha256`; require all accepted repair PNGs to equal their accepted candidate/final hashes and exact original dimensions; require Mini Bar end/pinch/asset absence and Mini Bar primary self-baseline preservation. Reject duplicate/unknown asset records or extra package files.

- [ ] **Step 2: Run all focused and complete tests.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk scripts/hangboard-packages.sh status --root Hangboards
  ```

  Expected: every test passes; final inventory reports exactly 61 complete packages, zero drafts, and 84 declared presentation PNGs.

- [ ] **Step 3: Validate final manifest truth before setting its own check.**

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial
  ```

  Expected: 15 passed batches; 19 keeps; 65 completed repairs split as 17 edits/48 regenerations; one removal; zero pending/blocked; 84 inventory presentations. Confirm every rejected candidate has lowercase hash, built-in/untouched/no-postprocessing provenance, concrete disposition/reason, and passed transient byte verification even though its bytes are gone.

- [ ] **Step 4: Prove no owned resources or forbidden artifacts remain.**

  Inspect `.context` and simulator lists. There must be no `sincere-otter-phase2-*` directory, candidate, copied web image, comparison board, Workbench capture, simulator capture, Derived Data, pending/owned simulator UUID, or built-in generated output owned by this workspace. Confirm no source photograph, sidecar, candidate, review directory, or undeclared asset exists under `Hangboards`. Leave shared/standard/unknown resources untouched.

- [ ] **Step 5: Record only checks that actually passed.**

  Set `phase2.finalChecks.manifestValidation`, `finalInventory`, `packageTestSuite`, and `contextCleanup` to passed with literal commands/results and actual date; retain the already passed cross-catalog, build, and simulator evidence. Update the narrative final table from validator output, including exact 61/85-history/84-current/19/17/48/1 totals and any source gaps that remained explicitly resolved or blocked before acceptance.

- [ ] **Step 6: Run the final closed gate.**

  ```bash
  rtk python3 -m json.tool \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-final
  rtk git status --short
  ```

  Expected: JSON parses; final validation passes with the exact counts above; status contains only the two audit documents intended for this task.

- [ ] **Step 7: Commit and push the final verified ledger.**

  ```bash
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Verify hangboard remediation phase two"
  rtk git push
  ```

  The controller performs the final spec-compliance review and separate code/data-quality review after this push. Completion is not claimed until the remote branch contains every reviewed task commit and `rtk git status --short` is clean.
