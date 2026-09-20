# Hangboards Batch 03 Evidence and Model Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the approved Batch 03 evidence, convert eight audited GLBs into hash-bound USDZ assets, and ship six exact-revision schema-v3 model-only hangboard packages with closed source/cord audits, suspension, ODR delivery, and reproducible import/render validation.

**Architecture:** A closed source audit first promotes exactly the 28 already-approved manufacturer captures byte-for-byte. The existing contact-first Blender importer remains the only transport path, extended narrowly for named output assets and an explicit operator-authored correction chain; final package JSON remains the authority for contact identity, positions, suspension, and Plateau configuration. Package, clean-reimport, cord, staging, native SceneKit, and retained human-review gates all validate the same eight USDZ/descriptor pairs.

**Tech Stack:** Python 3.11.4+, pytest, Blender Python (`bpy`), deterministic USDZ compiler, schema-v3 JSON, Swift/SceneKit/XCTest, Apple On-Demand Resources, Xcode project resources, SHA-256.

**Spec:** `docs/superpowers/specs/2026-09-20-hangboards-batch-03-3d-migration-design.md`

## Global Constraints

- This plan owns only evidence retention, model import/authoring, the six packages, source/cord audit data, ODR registration, and package/model validation. Runtime resolution, editor, history, workout, and experience behavior are implemented by their companion plans.
- Use the repository-local `migrate-hangboard-to-3d`, `audit-3d-hangboard-suspension`, `add-hangboard`, and `validate-hang-ten-ios` skills at the steps that name them. Read each named skill and `docs/3D_SUSPENSION_AND_ODR.md` immediately before executing that step.
- Do not begin Tasks 8-13 until Tasks 1, 2, and 6 of `docs/superpowers/plans/2026-09-20-batch-03-configuration-runtime.md` have landed `BoardPosition.effectiveDepths: [String: HoldDepth]?`, multiple original model presentations, presentation-local position/pose validation, full-inventory descriptors, the two-root cord-evidence allowlist, and cord-audit validation of every model presentation.
- Keep schema version `3`. Five packages have exactly one original model presentation named `primary`; Plateau has exactly `depth-18mm`, `depth-15mm`, and `depth-10mm`, with only `depth-18mm` default.
- Promote exactly Appendix A's 28 approved evidence files from `.context/sweet-hamster-batch03-research/evidence/` without downloading, decoding, re-encoding, resizing, minifying, cropping, or otherwise changing bytes.
- Retain all eight accepted source GLBs and verify their exact SHA-256 values before import. A corrected authoring source never replaces or obscures its accepted parent GLB.
- All three Plateau presentations must omit every screw/mounting hole. Task 4 separately retains and approves three operator-authored corrected `.blend` sources through `operatorAuthoredCorrection`; all three compile from those sources and report `sourceGeometryChanged:true`. Deliberately remove and cap each hole while preserving the lower open cord exits/grooves, attachment semantics, oak edge, black body, reversible reducer/blocker, contact identity, and selectable geometry. The cord exits are not mounting holes. No automatic hole detection, extraction, or mesh repair is permitted.
- Never use image-driven hold detection, segmentation, generated masks/contours, source registration/alignment, vectorization, automatic path simplification/cropping, proximity selection, bounds-based face selection, or proposal/refine/promote geometry. Port's side pinch and the standard Nature jug are selected face-by-face by an operator in Blender Edit Mode; both Nature multi-node pinches are deliberately mapped and reviewed by an operator.
- `contacts[]` is the sole physical-contact inventory. Descriptor node bindings may be many-to-one, but every descriptor's complete contact inventory equals the complete package inventory.
- USDZ is the only ODR resource. Descriptors and transient, non-pickable suspension metadata remain bundled. Do not bake cords, anchors, knots, hardware, blockers-as-contacts, or environmental objects into USDZ.
- No raster presentation, `contactGeometry`, PNG, mixed media, or fallback may remain in any of the six packages.
- All attachment coordinates, invisible anchors, cord radii/rest lengths, camera framing, translations, and newly selected pose values are audit-labelled `displayEstimate` unless Appendix A establishes the number. Nature side grooves and Plateau curled ends are open routes, not through-bores.
- Derive the workspace owner from the final path component of `${PASEO_WORKTREE_PATH:-$PWD}`. Put disposable output under `.context/OWNER-batch03-model-packages-*`, record the resolved owner, absolute paths, process IDs, and Simulator UDID in `OWNERSHIP.md`, install an exit trap before Blender/Xcode/Simulator work, and delete only those exact owned resources on every exit. Verify they are gone before completion. The shared `.context/hangboard-packages-venv` is repository-local tooling and is deliberately excluded from task cleanup.
- Preserve unrelated worktree changes. Do not commit `.context`, `.codegraph`, DerivedData, simulator data, or unapproved render candidates. Every task commit is followed immediately by `rtk git push`; stop on either commit or push failure before starting the next task.

## Review Focus

- A source-audit path that is a symlink, ignored, untracked, outside the repository, duplicated, or correct-looking but hash-mismatched must fail before package work; Task 1 tests every case.
- An operator-corrected source that does not hash-bind its accepted parent, correction report, explicit `prohibitedAutomationUsed: false`, and completed approval must fail import; Task 3 tests that chain.
- Require exactly five geometry corrections: Port, Oak, and all three Plateau presentations. Tasks 4, 7, 13, and 14 reject a missing/swapped Plateau source, audit, review image, or actual-time approval. Normal and rear/oblique images require human confirmation of capped screw/mounting holes and intact open cord exits for every corrected source and final shipped model; artifact/hash/node/material checks cannot establish hole absence.
- Plateau's three presentations must never borrow another presentation's descriptor, local position, effective-depth map, pose, or USDZ; Tasks 13, 14, and 16 exercise cross-wiring mutations.
- Multi-node contacts must remain one selectable identity after USDZ reimport: Port must never bind the obsolete bottom band, both Nature packages must bind both exterior pieces to `pinch-60`, and standard Nature's jug must bind only the manually partitioned recess; Tasks 5-7, 10-12, 14, and 17 test these exact node sets.
- A cord may solve numerically yet collide, self-intersect, terminate outside its declared open route, disappear behind the board, become pickable/accessibility-visible, or omit a local pose; Tasks 15 and 17 exercise the production clearance, visibility, picking, and accessibility gates for every presentation/position.

---

## File Structure

### Source-audit boundary

- Create `Tools/HangboardPackages/src/hangboard_packages/source_audit.py` for the closed evidence manifest types, parser, tracked-path/hash checks, and report.
- Create `Tools/HangboardPackages/tests/test_source_audit.py` for structural, filesystem, git-tracking, exact-production-record, and mutation tests.
- Modify `Tools/HangboardPackages/src/hangboard_packages/cli.py:11-151` and `scripts/hangboard-packages.sh:9-42` to expose `audit-sources` without loading the board catalog.
- Create `docs/source-audits/2026-09-20-hangboards-batch-03-source-audit.json` and the 28 exact files below `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/`.

### Import/authoring boundary

- Modify `Tools/HangboardModels/contact_model_package.py:136-219,668-685` and `Tools/HangboardModels/test_contact_model_package.py` for a validated asset stem instead of a hard-coded `primary` stem.
- Modify `Tools/HangboardModels/import_contact_model_source.py:35-109,285-377` and `Tools/HangboardModels/test_import_contact_model_source.py:14-119` for the accepted-parent/operator-correction chain and asset-stem report fields.
- Create `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/` containing the eight accepted GLBs, five corrected Blender sources (Port, Oak, and three Plateau sources), eight source manifests, eight contact mappings, correction/mapping approvals, import/reimport reports, render artifacts, `model-import-audit.json`, and `README.md`.
- Create `Tools/HangboardModels/verify_batch_03_models.py` and `Tools/HangboardModels/test_verify_batch_03_models.py` for exact shipped-asset clean reimport and descriptor reconstruction.

### Package/delivery boundary

- Replace each of `Hangboards/{aelith-cyclops-011,frictitious-nug,frictitious-port-a-board,nature-stone-hanger-mini,nature-stone-hanger-mini-karma8a,plateau-lifting-edge}/board.json` with the final model-only contract and replace their raster assets with eight USDZ/descriptor pairs.
- Create `Tools/HangboardPackages/tests/test_batch_03_model_packages.py` for exact identities, ordered contacts/positions, media, suspension, hashes, and absence of raster fallback.
- Modify `docs/source-audits/2026-09-13-model-hangboard-cord-audit.json` and `.md` with six evidence-backed represented decisions.
- Modify `Tools/HangboardModels/production_cord_clearance.swift:17-527` and `check_production_cord_clearance.rb:9-37`; create `Tools/HangboardModels/test_production_cord_clearance.py` for discovery of every suspended presentation, including `singleCord`.
- Modify `Tools/HangboardPackages/tests/test_board_package_staging.py:311-399,542-620`, `scripts/stage-board-packages.py:216-254` only if its all-presentation behavior fails the new regression, and `HangTen.xcodeproj/project.pbxproj:9-42,186-218,405-431,780-806` for six ODR folders/tags carrying eight USDZ assets.
- Create `HangTenTests/Batch03BoardModelTests.swift` and register it in `HangTen.xcodeproj/project.pbxproj` for exact native model behavior.
- Create `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/ios-native-model-acceptance.md` only after current-source package/model review passes.

## Task 1: Add the closed tracked source-audit validator

**Files:**

- Create: `Tools/HangboardPackages/src/hangboard_packages/source_audit.py`
- Create: `Tools/HangboardPackages/tests/test_source_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py:11-151`
- Modify: `scripts/hangboard-packages.sh:9-42`

**Interfaces:**

- Consumes: a UTF-8 JSON manifest path and repository root; `rtk git -C REPOSITORY_ROOT ls-files -z` is the operator-facing tracked-file authority.
- Produces: `load_source_audit(path: Path) -> SourceAuditManifest`, `validate_source_audit(manifest: SourceAuditManifest, *, manifest_path: Path, repository_root: Path, tracked_paths: frozenset[str] | None = None) -> SourceAuditReport`, and CLI `hangboard-packages audit-sources --repository-root ROOT --manifest FILE`.

- [ ] **Step 1: Bootstrap the shared package-tool virtual environment before the first Python RED run**

If `.context/hangboard-packages-venv/bin/python` is absent, run the exact bootstrap from `Tools/HangboardPackages/TESTING.md`:

```bash
rtk python3 -m venv .context/hangboard-packages-venv
rtk .context/hangboard-packages-venv/bin/python -m pip install -e 'Tools/HangboardPackages[dev]'
```

Confirm the interpreter reports Python 3.11.4 or newer with `rtk .context/hangboard-packages-venv/bin/python --version`. Reuse this environment in every later Python step. It is shared repository-local tooling, not disposable Task 1 output: do not owner-prefix it, add it to `OWNERSHIP.md`, or remove it during Task 14 cleanup.

- [ ] **Step 2: Write closed-schema and filesystem tests**

Define frozen records with exactly these JSON keys:

```python
RECORD_KEYS = {
    "ref", "publisher", "url", "sourceTier", "snapshotSHA256",
    "snapshotPath", "supportClaim", "humanApproval",
}
APPROVAL_KEYS = {"approved", "reviewer", "reviewedAt", "notes"}
```

Use one valid record `AE-1`, URL `https://aelith.eu/products/cyclops-011`, snapshot `docs/source-audits/test-evidence/aelith/product-page.html`, bytes `approved-aelith-byte-fixture`, its lowercase SHA-256, tier `manufacturer`, and a complete 2026-09-20 evidence approval. Parameterize these exact mutations and first diagnostics:

| Fixture mutation | Exact first diagnostic |
| --- | --- |
| Add record key `extra` | `records[0]: unknown keys: extra` |
| Delete `supportClaim` | `records[0]: missing keys: supportClaim` |
| Repeat JSON key `ref` in the source text | `source audit JSON contains duplicate key: ref` |
| Duplicate `ref`, `url`, or `snapshotPath` in record 1 | `records[1].ref duplicates records[0]`, `records[1].url duplicates records[0]`, or `records[1].snapshotPath duplicates records[0]` |
| URL `http://aelith.eu/products/cyclops-011` | `records[0].url must use https` |
| `sourceTier: "retailer"` | `records[0].sourceTier must equal manufacturer` |
| 63-character, uppercase, or non-hex hash | `records[0].snapshotSHA256 must be 64 lowercase hexadecimal characters` |
| Empty `supportClaim`, reviewer, or notes | `records[0].FIELD must be nonempty` with the mutated field path |
| `humanApproval.approved: false` | `records[0].humanApproval.approved must be true` |
| Evidence approval date `2026-09-21` | `records[0].humanApproval.reviewedAt must equal 2026-09-20` |
| Absolute path or `../outside` | `records[0].snapshotPath must be repository-relative and contained` |
| Symlink at the file or parent directory | `records[0].snapshotPath must not traverse a symlink` |
| Directory/FIFO instead of a regular file | `records[0].snapshotPath must name a regular file` |
| Changed snapshot bytes | `records[0].snapshotSHA256 does not match snapshot bytes` |
| Path absent from injected `tracked_paths` | `records[0].snapshotPath is not tracked by git` |

For the real-Git case, initialize a temporary repository, add the valid snapshot, then add the same path to `.gitignore` without staging it; assert the same untracked diagnostic. The successful fixture must equal `SourceAuditReport(record_count=1, snapshot_count=1, source_tiers={"manufacturer": 1})`.

- [ ] **Step 3: Run the focused test and confirm red**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_source_audit.py -q`

Expected: FAIL because `hangboard_packages.source_audit` does not exist.

- [ ] **Step 4: Implement the parser and validator**

Use this algorithm, keeping validation order identical to the table so diagnostics are deterministic:

```python
def load_source_audit(path: Path) -> SourceAuditManifest:
    pairs = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_json_keys)
    return SourceAuditManifest.from_closed_object(pairs)

def validate_source_audit(manifest, *, manifest_path, repository_root, tracked_paths=None):
    root = repository_root.resolve(strict=True)
    tracked = tracked_paths if tracked_paths is not None else git_tracked_paths(root)
    seen_refs, seen_urls, seen_paths = {}, {}, {}
    for index, record in enumerate(manifest.records):
        validate_closed_fields_and_uniqueness(record, index, seen_refs, seen_urls, seen_paths)
        relative = validate_repository_relative_path(record.snapshot_path)
        candidate = root / relative
        reject_symlink_component(root, relative)  # lstat each existing component; never resolve through it
        require_regular_file(candidate)           # stat.S_ISREG(candidate.stat(follow_symlinks=False).st_mode)
        require_tracked(relative.as_posix(), tracked)
        require_streaming_sha256(candidate, record.snapshot_sha256)
    return SourceAuditReport(len(manifest.records), len(seen_paths), Counter(r.source_tier for r in manifest.records))
```

`git_tracked_paths(root)` runs `subprocess.run(["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True)` and decodes the NUL-delimited repository-relative set. Reject a Git LFS/external pointer because its bytes cannot match the approved SHA-256. The production JSON report serializes exactly as:

```python
{"recordCount": 28, "snapshotCount": 28, "sourceTiers": {"manufacturer": 28}}
```

- [ ] **Step 5: Add `audit-sources` without requiring `--root Hangboards`**

Branch on `arguments.command == "audit-sources"` before the existing `discover_board_packages(arguments.root)` call in `cli.main`; add required `--repository-root` and `--manifest` arguments. Add the shell allowlist/help entry. In `test_cli.py`, patch `validate_source_audit` to return the one-record report and assert exit `0` plus stdout `{"recordCount":1,"snapshotCount":1,"sourceTiers":{"manufacturer":1}}`; then use the untracked fixture and assert exit `1`, empty stdout, and stderr beginning `records[0].snapshotPath is not tracked by git`.

- [ ] **Step 6: Run focused and full package-tool tests**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_source_audit.py Tools/HangboardPackages/tests/test_cli.py -q`

Expected: PASS.

- [ ] **Step 7: Commit, push, and obtain a fresh review**

```bash
rtk git add Tools/HangboardPackages/src/hangboard_packages/source_audit.py Tools/HangboardPackages/src/hangboard_packages/cli.py Tools/HangboardPackages/tests/test_source_audit.py Tools/HangboardPackages/tests/test_cli.py scripts/hangboard-packages.sh
rtk git commit -m "feat: validate closed hangboard source audits"
rtk git push
```

Give a fresh reviewer the Task 1 commit, the exact diagnostic table, and `test_source_audit.py`; do not begin Task 2 until the reviewer confirms symlink-component and tracked-byte checks cannot be bypassed.

## Task 2: Promote exactly the 28 approved evidence bytes and close the audit

**Files:**

- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-source-audit.json`
- Create: the exact 28 paths in spec lines 851-880 below `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/`
- Modify: `Tools/HangboardPackages/tests/test_source_audit.py`

**Interfaces:**

- Consumes: the already-approved ignored captures at `.context/sweet-hamster-batch03-research/evidence/` and exact Appendix A rows at spec lines 882-911.
- Produces: 28 unique tracked regular snapshots plus one closed schema-v1 manifest whose records are keyed `AE-1..3`, `NU-1..4`, `PA-1..5`, `NS-1..5`, `NK-1..5`, and `PL-1..6`.

- [ ] **Step 1: Add the production-record regression before copying anything**

In `test_source_audit.py`, assert the production manifest has exactly this ref/path/hash relation (the URL, publisher, and support claim for each row must equal the same Appendix A row, not a shortened paraphrase):

```python
EXPECTED = {
  "AE-1": ("aelith-cyclops-011/product-page.html", "1f802675e64e2f9850542622cef9fb44f34eb7d4ae01ce502e5b610daddd9eb0"),
  "AE-2": ("aelith-cyclops-011/front-back.jpg", "fc40128d4eaf51c260201e84bb1d8fde7d5224c49a42bd1349c93e4ab56cdeff"),
  "AE-3": ("aelith-cyclops-011/in-use.jpg", "0226a85fcc54586b7b12ff09b15154ff6aaf190f47fb16142d2fceed95a7a30c"),
  "NU-1": ("frictitious-nug/product-page.html", "eb44cc7bf24b53b721183cae2c42542863299c4ab193171a8d3be5ea6b9444de"),
  "NU-2": ("frictitious-nug/front.jpg", "7c476ab558d6defdacf4d4105e09cbffe99edaf5455c6ea04e5f00b812f2a384"),
  "NU-3": ("frictitious-nug/reverse.jpg", "c3e36dc47c9e4542321d155c337d91a3511ef6d6f9dfbcd0bd40100ce26f8202"),
  "NU-4": ("frictitious-nug/in-use.jpg", "146cbf91b840b7e6ae2063877c08729ae869bbb07da5e478300f9fdbeffd9ecd"),
  "PA-1": ("frictitious-port-a-board/product-page.html", "71f455b60e3f5f15511c22ca24d17c17d8928ef5bf8f296d3ed9207ca8dcfb55"),
  "PA-2": ("frictitious-port-a-board/front.jpg", "1509f81ed1dcf960a8ee1e91424e538de5aa890698b351a12fe2f1c36e4859e1"),
  "PA-3": ("frictitious-port-a-board/reverse.jpg", "38522abf6ccfa4a0f18dac57e5bbbf9a6290de4cd6a030756248f1a0314f70f4"),
  "PA-4": ("frictitious-port-a-board/side.jpg", "61221d7cb34edf3c5fd13e2300045050a0d7149424be9c5bcf8ded6c021df8e7"),
  "PA-5": ("frictitious-port-a-board/in-use.jpg", "a2cc5ec6e79272241c8f24891d91f89d075c3ebadc69b731d082a20775a43cd3"),
  "NS-1": ("nature-stone-hanger-mini/product-page.html", "782f39e5a7e4a04c61e812e28f581094c95b1d6cbbda7eb9b0bb3a82cca16369"),
  "NS-2": ("nature-stone-hanger-mini/front-original.jpg", "3aae064c37d7eef11e7874acaabbaca0194a1caa357e2bff1bbfb83faf093ff7"),
  "NS-3": ("nature-stone-hanger-mini/reverse-original.jpg", "09a4926269b291354b171fdac6e20365a6c9c66528bb4275b8cb56b20b8f1eae"),
  "NS-4": ("nature-stone-hanger-mini/oblique-original.jpg", "383cdd3665f1e30a0dc8443959d7442e65780dbd27b71bc597efc9a1b924f685"),
  "NS-5": ("nature-stone-hanger-mini/in-use-original.jpg", "f17ceb9007a1f00ad19859c6fdf4bbd0c8a48b5f8d1cdbf169c6de46ffeb076e"),
  "NK-1": ("nature-stone-hanger-mini-karma8a/product-page.html", "b962a7df9b6169c12993aa86b8c7d189941cad4acc373fac4f6064987bc04666"),
  "NK-2": ("nature-stone-hanger-mini-karma8a/front-original.png", "3267c96f30e9576b1b66f769d83722cac6c55322c9ad6491cda82ea3910f7743"),
  "NK-3": ("nature-stone-hanger-mini-karma8a/reverse-original.png", "412059dc91cb4b564d450b4065fdf467618d1d981c9568cb5346983ae7653de0"),
  "NK-4": ("nature-stone-hanger-mini-karma8a/oblique-original.jpg", "95292e0c642c3a3de255e66e0c09cd8b8ddcd6802a724a8bbd429d7647b58cbf"),
  "NK-5": ("nature-stone-hanger-mini-karma8a/in-use-original.png", "a962fc997461aed38bfaee08071681b27b12f671406c216947f7b21ce6bb2df8"),
  "PL-1": ("plateau-lifting-edge/product-page.html", "4c63ca9c62f1dbd686e823ceb2af3366a5f8381daaafe92b024ad7743a8a74b3"),
  "PL-2": ("plateau-lifting-edge/front.png", "7a854f73c876dffdff07251e4ab4cd5128014c3f51a3d31e14ecf00ac36fe7a7"),
  "PL-3": ("plateau-lifting-edge/oblique.png", "bb12d65453f77a917e048eb7ed09582c0ee4d96d6cf265973748f99cfc39191d"),
  "PL-4": ("plateau-lifting-edge/blocker-15.png", "4e666f921ffebdb287f383eb1330d5eb8aafab591cea5cfc488667368ee312b0"),
  "PL-5": ("plateau-lifting-edge/blocker-10.png", "b2a474441847de209fa85307383d0822f462801650f1f188bd0b1d8d8d49e243"),
  "PL-6": ("plateau-lifting-edge/oak-blocker-in-use.jpg", "a4a037eccdd1de212333f3f4482fab309ff385720768bb60c61606a9fb209e75"),
}
```

Prefix each tuple path with `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/`. Also assert `aelith-cyclops-011/oblique.jpg`, both Nature lower-resolution alternates, and `nature-stone-hanger-mini/side.jpg` are absent.

- [ ] **Step 2: Run the production test and confirm red**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_source_audit.py -q`

Expected: FAIL because the production manifest/snapshots do not exist.

- [ ] **Step 3: Copy the exact approved byte set and hash it before staging**

Use this byte-copy algorithm over the literal dictionary, without a glob, directory-wide copy, download, or image/HTML editor:

```python
source_root = Path(".context/sweet-hamster-batch03-research/evidence")
destination_root = Path("docs/source-audits/2026-09-20-hangboards-batch-03-evidence")
for ref, (relative_path, expected_hash) in EXPECTED.items():
    source = source_root / relative_path
    destination = destination_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    actual_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert actual_hash == expected_hash, f"{ref}: expected {expected_hash}, got {actual_hash}"
```

Run the production-record test immediately afterward; its loop rehashes the exact 28 destination paths and asserts `len(EXPECTED) == 28`, `len(set(paths)) == 28`, and that the four rejected alternates are absent.

- [ ] **Step 4: Author all 28 closed records with exact Appendix values**

Transcribe `publisher`, exact `url`, and the complete `supportClaim` from the corresponding ref row in Appendix A's `Publisher and evidence`, `Exact manufacturer URL`, and `What the retained bytes support` columns; the production regression compares all three strings for all refs, not only their non-emptiness. Set every `sourceTier` to `manufacturer`, every `snapshotSHA256`/`snapshotPath` to the literal `EXPECTED` dictionary, and every approval to:

```json
{
  "approved": true,
  "reviewer": "asherlc",
  "reviewedAt": "2026-09-20",
  "notes": "Approved as exact retained bytes for the evidence-specific support claim in this record."
}
```

Use `asherlc`, the identity attached to the already-recorded 2026-09-20 approval, on each record. Preserve one complete approval object per record; a later geometry-review approval does not replace this evidence approval.

- [ ] **Step 5: Stage before invoking the tracked-file gate, then validate**

Run:

```bash
rtk git add docs/source-audits/2026-09-20-hangboards-batch-03-source-audit.json docs/source-audits/2026-09-20-hangboards-batch-03-evidence
rtk scripts/hangboard-packages.sh audit-sources --repository-root . --manifest docs/source-audits/2026-09-20-hangboards-batch-03-source-audit.json
rtk git check-ignore --no-index docs/source-audits/2026-09-20-hangboards-batch-03-evidence/aelith-cyclops-011/product-page.html
```

Expected: JSON exactly reports `{"recordCount":28,"snapshotCount":28,"sourceTiers":{"manufacturer":28}}`. The `rtk git check-ignore --no-index` probe exits `1`, meaning the representative evidence path is not ignored; the production test has already checked all 28 tracked paths.

- [ ] **Step 6: Commit, push, and review the immutable evidence boundary**

```bash
rtk git commit -m "docs: retain approved batch 03 manufacturer evidence"
rtk git push
```

Give a fresh reviewer the Task 2 commit and the Appendix A table. The reviewer must independently count 28 records/files, recompute all 28 hashes, compare publisher/URL/support strings, and confirm the four rejected alternates are absent before Task 3 begins.

## Task 3: Generalize the contact-first importer for named assets and audited corrections

**Files:**

- Modify: `Tools/HangboardModels/contact_model_package.py:136-219,668-685`
- Modify: `Tools/HangboardModels/test_contact_model_package.py`
- Modify: `Tools/HangboardModels/import_contact_model_source.py:35-109,285-377`
- Modify: `Tools/HangboardModels/test_import_contact_model_source.py:14-119`

**Interfaces:**

- Consumes: schema-v1 source manifests bound to a requested `(packageID, presentationID)`, whose existing `auditedModelSource` is always the accepted user-provided parent; optional `operatorAuthoredCorrection` is a closed, hash-bound derived source. The low-level verifier requires `presentation_id` without a default; both public import paths supply their validated `asset_stem` as that expected identity.
- Produces: `compile_model_package(blend_path: Path, board_json_path: Path, output_directory: Path, *, asset_stem: str = "primary") -> ModelDescriptorV1`; `VerifiedSource(package_id: str, presentation_id: str, accepted_path: Path, compile_path: Path, source_geometry_changed: bool, correction_report_path: Path | None)`; `CorrectionReport(package_id: str, presentation_id: str, accepted_source_path: str, corrected_source_path: str, prohibited_automation_used: bool, candidate_generated_at: datetime)`; `load_closed_correction_report(path: Path) -> CorrectionReport`; `verify_source_manifest(manifest_path: Path, package_id: str, presentation_id: str, repository_root: Path, now: datetime | None) -> VerifiedSource`; `import_package(manifest_path: Path, mapping_path: Path, package_id: str, board_json: Path, output_directory: Path, *, asset_stem: str = "primary") -> Mapping[str, object]`; `verify_import_output(manifest_path: Path, mapping_path: Path, package_id: str, asset_stem: str, output_directory: Path, report_path: Path, repository_root: Path, expected_source_geometry_changed: bool, now: datetime | None) -> Mapping[str, object]`; import CLI `--asset-stem`; and ordinary-Python CLI `verify-import --manifest PATH --mapping PATH --package ID --asset-stem STEM --output-directory PATH --report PATH --repository-root PATH --expected-source-geometry-changed {true,false}`.

- [ ] **Step 1: Test named compiler assets first**

Add tests that `asset_stem="depth-15mm"` yields exactly `assets/depth-15mm.usdz` and `assets/depth-15mm.model.json`, while an omitted stem yields `assets/primary.usdz` and `assets/primary.model.json`. Parameterize `""`, `"Primary"`, `"depth/15mm"`, `"."`, `"depth 15mm"`, and `"../escape"`; each must raise `ModelPackageError("asset_stem must match ^[a-z0-9]+(?:-[a-z0-9]+)*$")` before the mocked Blender runner is called. Update mocked expected staged-file sets to use the selected stem.

- [ ] **Step 2: Test the correction chain first**

Add top-level `presentationID` to the closed manifest schema. All eight Batch 03 manifests explicitly require it: `primary` for the five single-presentation sources and the matching `depth-18mm`, `depth-15mm`, or `depth-10mm` for Plateau. Every correction report and every generated import report also requires explicit `presentationID`, including `primary`; unknown, blank, null, malformed, or mismatched values fail. Retain backward compatibility only for an existing schema-v1 **uncorrected** manifest whose `presentationID` key is absent and whose caller explicitly requests `primary`: the loader normalizes that documented legacy primary form and the verifier still requires equality with the requested `primary`. A missing key never authorizes a named presentation or an operator correction. Never derive requested identity from a filename, a correction, declaration order, or the board's default. Public `asset_stem="primary"` defaults remain explicit primary requests; an explicit wrong value never takes the legacy path.

Keep `auditedModelSource.provenanceType == "user-provided"`. Add an optional closed object with exactly:

```json
{
  "retainedPath": "docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/authored-source/frictitious-port-a-board.blend",
  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "parentSHA256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "correctionAuditPath": "docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/frictitious-port-a-board.json",
  "correctionAuditSHA256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
}
```

The base fixture is intentionally unapproved. In the success test, a fake clock starts at `2026-09-20T17:00:00Z`; `render_candidate()` writes that instant as the correction report's `candidateGeneratedAt`, `inspect_candidate()` must be called, the clock advances five minutes, and only then does `complete_approval(reviewed_at=clock.now())` add the approval. This fixed clock is test-only; production captures the real clock after inspection. Test this exact mutation matrix and diagnostics:

| Mutation | Exact diagnostic |
| --- | --- |
| Manifest explicitly declares `depth-15mm` for requested `depth-18mm` | `model source manifest presentationID must equal depth-18mm` |
| Manifest omits `presentationID` for a named presentation or any corrected source | `model source manifest presentationID is required` |
| Manifest explicitly declares a non-primary identity for requested `primary` | `model source manifest presentationID must equal primary` |
| Correction report omits `presentationID` | `correction report presentationID is required` |
| Correction report declares `depth-15mm` for requested `depth-18mm` | `correction report presentationID must equal depth-18mm` |
| Unknown `operatorAuthoredCorrection.extra` | `operatorAuthoredCorrection: unknown keys: extra` |
| Missing `parentSHA256` | `operatorAuthoredCorrection: missing keys: parentSHA256` |
| Parent hash differs from `auditedModelSource.sha256` | `operatorAuthoredCorrection.parentSHA256 must equal auditedModelSource.sha256` |
| Accepted/corrected/report path is a symlink or non-file | `PATH must be a repository-contained regular file without symlinks` |
| Accepted, corrected, or report bytes mismatch its hash | `FIELD does not match retained bytes` |
| Report omits `prohibitedAutomationUsed` or sets it true | `correction report prohibitedAutomationUsed must be false` |
| Approval is absent, false, or blank | `operatorAuthoredCorrection.humanApproval must be completed after inspection` |
| `reviewedAt` is date-only or lacks `Z` | `operatorAuthoredCorrection.humanApproval.reviewedAt must be an RFC3339 UTC instant` |
| `reviewedAt < candidateGeneratedAt` | `operatorAuthoredCorrection.humanApproval.reviewedAt must not predate candidate generation` |
| `reviewedAt > now` | `operatorAuthoredCorrection.humanApproval.reviewedAt must not be in the future` |
| Report `packageID`, `acceptedSourcePath`, or `correctedSourcePath` disagrees | `correction report FIELD does not match source manifest` |

An uncorrected manifest returns the accepted GLB as both `accepted_path` and `compile_path`, `source_geometry_changed == false`, and `correction_report_path is None`; its `VerifiedSource.package_id` and `.presentation_id` must equal the caller's validated request. Test explicit `primary` and the narrowly allowed legacy primary form for identical outputs; a legacy key omission with requested `depth-18mm` must fail, as must omission on a corrected `primary` manifest.

Add `verify_import_output` tests using valid uncorrected and corrected `fixture.board/primary` fixtures. The verifier must derive the expected descriptor bindings directly from every mapping object whose role is `body` or `contact`; attachment objects remain audit evidence but are not descriptor nodes. Mutate one field at a time and require these first diagnostics:

| Mutation | Exact diagnostic |
| --- | --- |
| Manifest `packageID` differs from the CLI package | `model source manifest packageID must equal fixture.board` |
| Manifest `presentationID` differs from CLI `--asset-stem primary` | `model source manifest presentationID must equal primary` |
| Mapping `packageID` differs from the CLI package | `contact mapping packageID must equal fixture.board` |
| Import report `packageID` differs | `import report packageID must equal fixture.board` |
| Import report `presentationID` differs | `import report presentationID must equal primary` |
| CLI expectation or report `sourceGeometryChanged` differs from an uncorrected `VerifiedSource` | `sourceGeometryChanged must equal false` |
| CLI expectation or report `sourceGeometryChanged` differs from a corrected `VerifiedSource` | `sourceGeometryChanged must equal true` |
| Report `acceptedSourceModelPath` differs | `import report acceptedSourceModelPath does not match verified source` |
| Report `acceptedSourceModelSHA256` differs | `import report acceptedSourceModelSHA256 does not match verified source` |
| Report `compiledSourcePath` differs | `import report compiledSourcePath does not match verified source` |
| Report `compiledSourceSHA256` differs | `import report compiledSourceSHA256 does not match verified source` |
| Corrected report omits/misstates `correctionAuditPath`, or an uncorrected report makes it non-null | `import report correctionAuditPath does not match verified source` |
| Report `assetPath` differs from the stem-derived path | `import report assetPath must equal assets/primary.usdz` |
| Report `descriptorPath` differs from the stem-derived path | `import report descriptorPath must equal assets/primary.model.json` |
| Generated USDZ is missing, a symlink, or outside `output_directory` | `generated USDZ must be a contained regular file without symlinks` |
| Generated descriptor is missing, a symlink, or outside `output_directory` | `generated descriptor must be a contained regular file without symlinks` |
| Report `modelSHA256` differs from generated bytes | `import report modelSHA256 does not match generated bytes` |
| Report `descriptorSHA256` differs from generated bytes | `import report descriptorSHA256 does not match generated bytes` |
| Descriptor `modelSHA256` differs from generated USDZ bytes | `descriptor modelSHA256 does not match generated USDZ` |
| Descriptor body/contact node tuples differ from the mapping | `descriptor nodes must equal mapped body/contact nodes` |
| Report `contactMappings` differs from mapped contact nodes | `import report contactMappings must equal mapped contact nodes` |
| Report `logicalContactIDs` or descriptor contact inventory differs from mapping order/set | `generated contact inventory must equal mapping logicalContactIDs` |

The corrected-fixture success case proves the accepted parent, retained correction, hash-bound correction report, parsed `candidateGeneratedAt`, and post-inspection approval are revalidated by this gate. The uncorrected success case proves `correctionAuditPath:null`. Both print only `PASS fixture.board/primary verified import output` on stdout and return exit status `0`.

Include corrected fixtures for each of the three Plateau presentation IDs. The closed report parser must support Task 4's explicit presentation identity, render path/hash list, preserved node/material/contact inventory, and post-inspection verdict fields without allowing arbitrary unknown keys. Revalidate every retained review image and the approval's binding to that exact candidate. Tests must reject mismatched presentation identity or render hashes and missing review views; this verification does not determine whether geometry contains holes.

For both `import_package(..., asset_stem="depth-18mm")` and `verify_import_output(..., asset_stem="depth-18mm", ...)`, supply the complete otherwise-valid `depth-15mm` manifest and correction chain: its accepted source, corrected `.blend`, correction audit, render files/hashes, and completed approval all remain internally consistent. Require the first diagnostic `model source manifest presentationID must equal depth-18mm`. Repeat for all six directed swaps between the three Plateau depths. Spy on the source scene opener and Blender runner: neither may be called, and no corrected geometry may be resolved/opened. Separately change only that valid 15 mm manifest's top-level `presentationID` to `depth-18mm`, retaining its accepted parent and complete 15 mm correction/report chain with valid hashes; require `correction report presentationID must equal depth-18mm` before corrected-path resolution. Keep matching outer identities and mutate each accepted-parent binding, compiled-source binding, retained review-image binding, or approval candidate binding in turn; the full chain must fail verification. Matching package IDs alone never satisfy these tests.

- [ ] **Step 3: Run the model-tool tests and confirm red**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py -q`

Expected: FAIL on missing `asset_stem`, `VerifiedSource`, and `verify-import` behavior.

- [ ] **Step 4: Implement the narrow backward-compatible changes**

Validate stems with `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Implement the verification flow exactly as:

```python
def verify_source_manifest(
    manifest_path: Path,
    package_id: str,
    presentation_id: str,
    repository_root: Path,
    now: datetime | None,
) -> VerifiedSource:
    validate_presentation_identifier(presentation_id)
    manifest = load_closed_manifest(
        manifest_path,
        allow_legacy_uncorrected_primary=(presentation_id == "primary"),
    )
    if manifest.package_id != package_id:
        raise SourceManifestError(f"model source manifest packageID must equal {package_id}")
    if manifest.presentation_id != presentation_id:
        raise SourceManifestError(
            f"model source manifest presentationID must equal {presentation_id}"
        )
    accepted = verify_regular_hash_bound_path(repository_root, manifest.audited_model_source)
    if manifest.operator_authored_correction is None:
        return VerifiedSource(package_id, presentation_id, accepted, accepted, False, None)
    correction = manifest.operator_authored_correction
    require_equal(correction.parent_sha256, manifest.audited_model_source.sha256)
    report_path = verify_regular_hash_bound_path(repository_root, correction.correction_audit)
    correction_report = load_closed_correction_report(report_path)
    if correction_report.presentation_id != presentation_id:
        raise SourceManifestError(
            f"correction report presentationID must equal {presentation_id}"
        )
    validate_correction_report_identity(
        correction_report, manifest, package_id, presentation_id,
    )
    compiled = verify_regular_hash_bound_path(repository_root, correction.retained_source)
    validate_correction_report(
        correction_report, manifest, accepted, compiled, presentation_id=presentation_id,
    )
    verify_review_images_and_candidate_binding(
        correction_report, correction.human_approval, repository_root,
        package_id=package_id, presentation_id=presentation_id,
    )
    validation_now = datetime.now(timezone.utc) if now is None else now
    validate_completed_utc_approval(
        correction.human_approval,
        candidate_generated_at=correction_report.candidate_generated_at,
        now=validation_now,
    )
    return VerifiedSource(package_id, presentation_id, accepted, compiled, True, report_path)
```

`load_closed_manifest` applies the Step 2 legacy rule only for a missing key on an uncorrected schema-v1 manifest; otherwise `presentationID` is required and validated. `load_closed_correction_report` always requires it. `validate_correction_report_identity` checks the report's package/presentation and accepted/corrected source path/hash declarations against the manifest before corrected geometry resolution. The later artifact checks recompute those hashes, verify all retained review images, and require approval of that exact package/presentation/candidate source/render set. The approved report hash binds those records together. All checks complete before opening a source scene or invoking the compiler; a mismatch is not deferred to package promotion or an offline aggregate test.

Have `import_package` validate `asset_stem`, then call `verify_source_manifest(manifest_path, package_id, asset_stem, Path.cwd(), None)` before source-scene opening or any Blender runner call. Require the returned `(package_id,presentation_id)` to equal the request, open only `VerifiedSource.compile_path`, and never mutate the accepted or corrected source. Add exact report fields `presentationID`, `assetPath`, `descriptorPath`, `acceptedSourceModelPath`, `acceptedSourceModelSHA256`, `compiledSourcePath`, `compiledSourceSHA256`, `sourceGeometryChanged`, nullable `correctionAuditPath`, and ordered `logicalContactIDs`; preserve existing model/descriptor/bounds/node/contact/mapping fields. The import CLI passes `--asset-stem` directly into `import_package`; that same validated stem goes to `compile_model_package`, both output paths, and the report's verified presentation ID. Never let the manifest select or overwrite the requested stem.

Implement `verify_import_output` as a non-Blender path in the same script. It first calls `verify_source_manifest(manifest_path, package_id, asset_stem, repository_root, now)`. It loads the closed mapping and import report; requires their package/presentation/source fields to equal the CLI request and `VerifiedSource`; derives `assets/{asset_stem}.usdz` and `assets/{asset_stem}.model.json`; resolves those beneath `output_directory` without symlinks; hashes each once; and compares those hashes with the report plus the descriptor's `modelSHA256`. Build expected descriptor nodes by sorting mapping objects with role `body` or `contact` by `sourceNodeID` and projecting them to `{nodeID,role}` plus `contactID` for contacts. Require byte-for-byte equality with descriptor `nodes`, exact equality between report `contactMappings` and the mapping's contact projection, exact ordered equality between report `logicalContactIDs` and mapping `logicalContactIDs`, and descriptor contact keys equal to the same set. Return the verified paths/hashes mapping and print `PASS {package_id}/{asset_stem} verified import output`. Parse `true`/`false` explicitly for `--expected-source-geometry-changed`; dispatch `verify-import` before importing `bpy`, while the existing no-subcommand Blender invocation remains backward compatible.

- [ ] **Step 5: Run focused tests and a default-primary regression**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py Tools/HangboardModels/test_contact_model_descriptor.py -q`

Expected: PASS; old callers still produce `primary.*` from explicitly validated primary identity, including the narrowly allowed legacy uncorrected manifest form. All six full Plateau-chain swaps and report-only cross-presentation swaps fail before source-scene opening or Blender runner invocation in both entrypoints.

- [ ] **Step 6: Commit, push, and review importer support**

```bash
rtk git add Tools/HangboardModels/contact_model_package.py Tools/HangboardModels/import_contact_model_source.py Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py
rtk git commit -m "feat: import named audited model assets"
rtk git push
```

Give a fresh reviewer the Task 3 commit and require an explicit verdict on path containment, correction-report hash binding, timestamped approval validation, default-`primary` compatibility, and rejection before Blender invocation.

## Task 4: Retain the eight accepted GLBs and approve all three Plateau corrections

Assign this task to a fresh implementation agent and a different reviewer. It owns immutable source retention, six mappings whose node/contact assignments remain unchanged, and deliberate removal/capping of screw/mounting holes in each of the three Plateau sources. It does not approve Port, Oak, or KARMA8A contact semantics.

**Files:**

- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/*.glb` (8 exact files)
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/*.source.json` (8 accepted-parent manifests)
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/{aelith-cyclops-011,frictitious-nug,nature-stone-hanger-mini-karma8a,plateau-lifting-edge-depth-18mm,plateau-lifting-edge-depth-15mm,plateau-lifting-edge-depth-10mm}.contact-map.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/authored-source/plateau-lifting-edge-depth-{18,15,10}mm.blend` (3 separate sources)
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/plateau-lifting-edge-depth-{18,15,10}mm.json` (3 separate correction audits)
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/plateau-lifting-edge-depth-{18,15,10}mm-{normal,rear-oblique}.png` (6 review images)
- Create: `Tools/HangboardModels/test_batch_03_source_contract.py`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/README.md`

**Interfaces:**

- Consumes: eight absolute, user-approved source paths and exact SHA-256 values in `ACCEPTED_SOURCES` below; Task 2 evidence refs.
- Produces: `verify_retained_source(path: Path, expected_sha256: str) -> None`, eight hash-bound accepted-parent manifests, six structurally complete mappings with unchanged node/contact assignments, and `verify_plateau_corrections(root: Path) -> None` requiring all three approved corrections. Each Plateau manifest gains its own Task 3 `operatorAuthoredCorrection` chain and resolves `source_geometry_changed == true`. Tasks 5 and 6 add correction objects to the Port and Oak manifests; Task 7 approves the already-authored KARMA8A mapping.

- [ ] **Step 1: Write the literal source contract and RED tests**

Put this exact dictionary in `test_batch_03_source_contract.py`; keys are also the retained filenames:

```python
ACCEPTED_SOURCES = {
    "aelith-cyclops-011.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/aelith-cyclops-011/aelith-cyclops-011.glb"), "e30bffa8078cd37a9389037146f55fb340d10163d4a7dd50a472cef3fbe46d3a"),
    "frictitious-nug.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/frictitious-nug/frictitious-nug.glb"), "40c328f9bdd3ff10befcd2dde71074876a70379f03ec91187609e3873d4d7c70"),
    "frictitious-port-a-board.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/frictitious-port-a-board/frictitious-port-a-board.glb"), "4314f5c6a129f17ff26139ed945b3d4b1fb32a3d2ee596522a674d3373bf69de"),
    "nature-stone-hanger-mini.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/nature-stone-hanger-mini/nature-stone-hanger-mini.glb"), "d9eedc2407d836bf008087e547fde76d81ecc41f306c7e2ce526c49524be626e"),
    "nature-stone-hanger-mini-karma8a.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/nature-stone-hanger-mini-karma8a/nature-stone-hanger-mini-karma8a.glb"), "3ebe92f518cc66dd03f8256ebd6260a950f01252b74adbeb2b0c3116e775ffb6"),
    "plateau-lifting-edge.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge.glb"), "a71374b13a0629f98971063deacb6fbdddb5171133094c692b6a9841547ff8ce"),
    "plateau-lifting-edge-15mm.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge-15mm.glb"), "4328f58efac235aa69efb4326b3254577d745e1e86881aa454ef79bcca9945ba"),
    "plateau-lifting-edge-10mm.glb": (Path("/Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge-10mm.glb"), "88bb08d316588b270a6b47b40acce467c81ebbcfa630b089fec638277f15e208"),
}
```

`test_retained_sources` requires exactly those eight destination filenames and hashes. `test_accepted_parent_manifests` requires closed base keys `schemaVersion`, `packageID`, `presentationID`, `manufacturerPhysicalAuthority`, `historicalSource`, `auditedModelSource`, and `supersessionRuling`, allowing only Task 3's closed `operatorAuthoredCorrection` extension; `auditedModelSource` has exactly `provenanceType`, `authorization`, `retainedPath`, and `sha256`, with `provenanceType: user-provided`. Require explicit `primary` for the five single-presentation manifests and the matching depth identity for each Plateau manifest; none of these new manifests may use the legacy omission rule. Before retention, both tests fail with `missing retained Batch 03 source: aelith-cyclops-011.glb`. The separate Plateau correction test must fail until all three chains and post-inspection approvals exist; accepted-parent validation alone never authorizes Plateau export.

- [ ] **Step 2: Hash all eight exact absolute paths before any copy**

Run this executable preflight before creating `source-delivery`:

```bash
rtk .context/hangboard-packages-venv/bin/python - <<'PY'
from hashlib import sha256
from pathlib import Path

sources = [
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/aelith-cyclops-011/aelith-cyclops-011.glb"), "e30bffa8078cd37a9389037146f55fb340d10163d4a7dd50a472cef3fbe46d3a"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/frictitious-nug/frictitious-nug.glb"), "40c328f9bdd3ff10befcd2dde71074876a70379f03ec91187609e3873d4d7c70"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/frictitious-port-a-board/frictitious-port-a-board.glb"), "4314f5c6a129f17ff26139ed945b3d4b1fb32a3d2ee596522a674d3373bf69de"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/nature-stone-hanger-mini/nature-stone-hanger-mini.glb"), "d9eedc2407d836bf008087e547fde76d81ecc41f306c7e2ce526c49524be626e"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/nature-stone-hanger-mini-karma8a/nature-stone-hanger-mini-karma8a.glb"), "3ebe92f518cc66dd03f8256ebd6260a950f01252b74adbeb2b0c3116e775ffb6"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge.glb"), "a71374b13a0629f98971063deacb6fbdddb5171133094c692b6a9841547ff8ce"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge-15mm.glb"), "4328f58efac235aa69efb4326b3254577d745e1e86881aa454ef79bcca9945ba"),
    (Path("/Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge-10mm.glb"), "88bb08d316588b270a6b47b40acce467c81ebbcfa630b089fec638277f15e208"),
]
failures = []
for path, expected in sources:
    if path.is_symlink() or not path.is_file():
        failures.append(f"{path}: missing regular file")
        continue
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        failures.append(f"{path}: expected {expected}, got {actual}")
if failures:
    print("\n".join(failures))
    raise SystemExit(1)
print("PASS: 8 exact accepted GLBs")
PY
```

Expected on success: exactly `PASS: 8 exact accepted GLBs`. A missing/nonregular path prints `PATH: missing regular file`; a mismatch prints `PATH: expected HASH, got HASH`. The loop reports every failure across all eight, never rereads a missing file, prints no PASS line when any failure exists, and exits once with status `1`; stop without copying.

- [ ] **Step 3: Copy only the preflighted bytes and rehash destinations**

Create the destination with `rtk mkdir -p docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery`, then run these commands individually:

```bash
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/aelith-cyclops-011/aelith-cyclops-011.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/aelith-cyclops-011.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/frictitious-nug/frictitious-nug.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/frictitious-nug.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/frictitious-port-a-board/frictitious-port-a-board.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/frictitious-port-a-board.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/nature-stone-hanger-mini/nature-stone-hanger-mini.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/nature-stone-hanger-mini.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/nature-stone-hanger-mini-karma8a/nature-stone-hanger-mini-karma8a.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/nature-stone-hanger-mini-karma8a.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/plateau-lifting-edge.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge-15mm.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/plateau-lifting-edge-15mm.glb
rtk cp -p -- /Users/asherlc/Downloads/hangboards-batch-03/plateau-lifting-edge/plateau-lifting-edge-10mm.glb docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/source-delivery/plateau-lifting-edge-10mm.glb
```

Run `test_retained_sources`; expected: eight paths, eight unique SHA-256 values, and PASS. Never alter a retained GLB.

- [ ] **Step 4: Author eight accepted-parent manifests and six node/contact mappings**

For every manifest, use its final package ID, explicit `presentationID` (`primary` or its exact Plateau depth), exact Task 2 manufacturer publisher/evidence packet, `historicalSource: {"status":"missing"}`, the corresponding retained path/hash, and a supersession ruling naming the exact revision. Correction reports added here and in Tasks 5/6 must repeat the same presentation identity. Do not add `operatorAuthoredCorrection` to Port or Oak yet.

Use this complete mapping table; `B` means `{"role":"body"}`, `C:id` means `{"role":"contact","contactID":"id"}`, and each attachment row also has `selectable:false`, the shown order/source position, and evidence-ref metadata. `logicalContactIDs` is the listed ordered array.

| Mapping key | Ordered logical IDs | Exact source-node assignments |
| --- | --- | --- |
| `aelith-cyclops-011` | `mono-20` | `body-blue-aluminum=B`; `edge-20mm=C:mono-20`; `cord-attachment=A1@[0,-0.014,0.0251]` |
| `frictitious-nug` | `edge-25,edge-20,edge-13,edge-8,jug-40,pinch-60` | `body-beech=B`; `front-edge-25mm=C:edge-25`; `front-edge-20mm=C:edge-20`; `reverse-edge-13mm=C:edge-13`; `reverse-edge-8mm=C:edge-8`; `outer-jug=C:jug-40`; `outer-pinch-opposition=C:pinch-60`; `cord-passage-1=A1@[-0.053,-0.02,0]`; `cord-passage-2=A2@[0.053,-0.02,0]` |
| `nature-stone-hanger-mini-karma8a` | `granite-edge-15,wood-edge-15,pinch-60` | `body-smoked-oak=B`; `body-granite-front=B`; `granite-edge-15mm=C:granite-edge-15`; `wood-edge-15mm=C:wood-edge-15`; `outer-pinch-upper=C:pinch-60`; `outer-pinch-lower=C:pinch-60`; `cord-passage-1=A1@[-0.0511,0,0]`; `cord-passage-2=A2@[0.0511,0,0]` |
| `plateau-lifting-edge-depth-18mm` | `edge-18` | `body-black-aluminum=B`; `body-oak=B`; `edge-18mm=C:edge-18`; `cord-passage-1=A1@[-0.05,-0.009,-0.03]`; `cord-passage-2=A2@[0.05,-0.009,-0.03]` |
| `plateau-lifting-edge-depth-15mm` | `edge-18` | same as 18 mm plus `body-reducer-polymer=B` |
| `plateau-lifting-edge-depth-10mm` | `edge-18` | same as 18 mm plus `body-reducer-polymer=B` |

The test feeds the exact GLB object inventories to `validate_mapping`, then repeats validation against each corrected Plateau source after Step 4b. Assert every object is mapped once, body/attachment nodes have no contact ID, each ordered logical inventory matches the table, and reducer nodes are nonselectable body. These are node/contact invariants, not evidence that holes are absent. It does not semantically approve the KARMA8A two-node pinch; that is Task 7.

- [ ] **Step 4a: Add the three-source Plateau correction contract before authoring**

Require these exact pairs; each key also names its own manifest, `.blend`, correction audit, and review-image pair under the paths in Files:

| Presentation source key | Immutable accepted parent |
| --- | --- |
| `plateau-lifting-edge-depth-18mm` | `plateau-lifting-edge.glb` |
| `plateau-lifting-edge-depth-15mm` | `plateau-lifting-edge-15mm.glb` |
| `plateau-lifting-edge-depth-10mm` | `plateau-lifting-edge-10mm.glb` |

Parameterize every mutation over all three keys. Missing `operatorAuthoredCorrection` fails `KEY: Plateau correction is required`. First call Task 3's `verify_source_manifest` with the expected package and presentation from the row, never from the supplied manifest: a whole manifest/chain swap fails `model source manifest presentationID must equal EXPECTED_DEPTH`; a correction report swap fails `correction report presentationID must equal EXPECTED_DEPTH`. After these identity checks, reusing another presentation's parent, corrected path/hash, audit, render pair, or approval fails `KEY: Plateau correction identity mismatch`, even when that other chain is internally valid. Missing or mismatched source/audit/render bytes, absent/false approval, approval predating `candidateGeneratedAt` or after the validation clock, and `prohibitedAutomationUsed:true` must fail the existing Task 3 chain or the closed Plateau report validator. A false import/report flag fails `sourceGeometryChanged must equal true`. Assert all three `.blend` paths are distinct and each hash matches its own retained bytes; merely counting three corrections is insufficient.

Use the closed correction report extension to bind `presentationID`, `sourceGeometryChanged:true`, the exact normal/rear-oblique paths and SHA-256 values, the preserved Step 4 node/contact inventory, and an explicit human verdict on removed/capped screw/mounting holes and preserved lower cord exits. Record each accepted source's exact per-node material identities and assignments before editing, preserve them in the corrected source, and bind both inventories in the audit for exact comparison. Hash-bind that report via `correctionAuditSHA256`. Tests validate this artifact/approval contract and exact inventories; they must not analyze pixels, infer topology, detect holes automatically, or treat node names as a proxy for absence of holes.

- [ ] **Step 4b: Deliberately remove and cap every screw/mounting hole in each source**

Read `migrate-hangboard-to-3d/SKILL.md`. Record an owned/trapped Blender workspace as in Task 5. Import each accepted Plateau GLB into its own empty scene, save a working copy under the owned directory, and preserve the original GLB bytes. Compare PL-1 through PL-6 visually. In Blender Edit Mode an operator deliberately selects and edits the relevant faces to remove and cap every screw/mounting hole, including rear openings; no image-driven selection, scripted repair, automatic hole filling, extraction, or topology inference is permitted. Preserve lower curled open cord exits/grooves and the two attachment markers/semantics, oak edge, black body, the 15/10 reducer and its orientation, materials, `edge-18mm→edge-18`, and all selectable contact surfaces. Do not cap a cord exit or claim the physical product has no mounting holes. Inspect caps, normals, and seams manually. Save each result at its distinct tracked `.blend` path; document deliberate edits and preserved invariants, accepted/corrected paths/hashes, `presentationID`, `sourceGeometryChanged:true`, and `prohibitedAutomationUsed:false` in its audit, with approval absent.

- [ ] **Step 4c: Obtain a separate actual-time human approval for each correction**

For each saved corrected source, render full-frame normal and rear/oblique views that expose all former screw/mounting-hole areas and the retained lower cord exits; retain additional views if these two do not reveal every area. After that candidate set exists, capture `candidateGeneratedAt` using `rtk date -u +%Y-%m-%dT%H:%M:%SZ` and hash every image. Show the images and approved manufacturer evidence to the human reviewer. Require explicit confirmation that every screw/mounting hole is removed and capped, the open cord exits/grooves remain intact, and the oak edge, black body, applicable blocker, and contact geometry remain correct. On rejection, return to Step 4b and invalidate that candidate's approval. Only after explicit approval capture a new actual RFC3339 UTC instant and write reviewer, notes, and all relevant render hashes in `humanApproval`; never prefill/backdate it or reuse the date-only evidence approval. Bind each manifest's `operatorAuthoredCorrection` to that source, its own accepted parent, correction audit, and completed approval. Source/render changes require new generation and review; any missing/mismatched chain blocks all three Plateau exports.

- [ ] **Step 5: Run the Task 4 contract slice**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_batch_03_source_contract.py -q -k 'retained or accepted_parent or unchanged_mapping or plateau_correction'`

Expected: PASS for eight source hashes, eight accepted-parent manifests, six mappings with unchanged node/contact assignments, and all three Plateau correction chains with `sourceGeometryChanged:true`. Exact first failures include `accepted source hash mismatch: NAME`, `unmapped source object: NODE`, `logicalContactIDs mismatch for KEY`, and the Step 4a correction diagnostics. Automated PASS supplements the three required human visual verdicts and never proves hole absence.

- [ ] **Step 6: Commit, push, and obtain an independent immutable-source review**

```bash
rtk git add docs/source-audits/2026-09-20-hangboards-batch-03-model-imports Tools/HangboardModels/test_batch_03_source_contract.py
rtk git commit -m "docs: retain accepted batch 03 model sources"
rtk git push
```

A fresh reviewer reruns the absolute-path preflight, recomputes the eight retained hashes, compares every mapping row, and reviews all three Plateau corrected sources and hash-bound normal/rear-oblique image sets for capped screw/mounting holes and intact cord exits. Confirm each Plateau source has its own completed actual-time approval, Port/Oak have no premature correction object, and KARMA8A has no mapping approval. Stop on any discrepancy.

## Task 5: Manually correct and approve the Port-A-Board side pinch

Assign this task to a fresh implementation agent and a different reviewer. No image-derived or scripted face selection is permitted.

**Files:**

- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/authored-source/frictitious-port-a-board.blend`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/frictitious-port-a-board.contact-map.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/frictitious-port-a-board.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/frictitious-port-a-board-{normal,pinch-body-isolated}.png`
- Modify: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/frictitious-port-a-board.source.json`
- Modify: `Tools/HangboardModels/test_batch_03_source_contract.py`

**Interfaces:**

- Consumes: retained Port GLB hash `4314f5c6a129f17ff26139ed945b3d4b1fb32a3d2ee596522a674d3373bf69de`, evidence refs `PA-1..PA-5`, and Task 3's correction chain.
- Produces: one approved corrected `.blend`, `pinch-body` as the only `pinch-body` contact node, a hash-bound correction report, and `verify_port_correction(report: Mapping[str, object], mapping: ValidatedMapping) -> None`.

- [ ] **Step 1: Add the Port RED contract**

Require ordered IDs `edge-30,edge-25,edge-20,edge-15,edge-12,edge-10,edge-8,jug-outer-rim,pinch-body`. Require exact bindings `front-lower-30mm→edge-30`, `front-upper-25mm→edge-25`, `front-upper-20mm→edge-20`, `reverse-upper-15mm→edge-15`, `reverse-upper-12mm→edge-12`, `reverse-lower-10mm→edge-10`, `reverse-lower-8mm→edge-8`, `outer-jug→jug-outer-rim`, and new `pinch-body→pinch-body`; require `body-beech`, `body-black-eyelet`, and `outer-pinch-opposition` as body plus the two marker rows `[-0.054,-0.024,0]` and `[0.054,-0.024,0]`. Before authoring, fail exactly `Port correction approval is missing`.

- [ ] **Step 2: Create and register the owned Blender workspace**

Read `migrate-hangboard-to-3d/SKILL.md`. Create one owner-named temporary directory beneath `.context`, write its resolved path and Blender PID to its `OWNERSHIP.md`, and install a trap that terminates that PID and deletes only that directory. Import the retained GLB into an empty Blender scene and immediately save a working copy under the owned directory; never edit the retained GLB.

- [ ] **Step 3: Select the side faces manually and save the corrected source**

Display PA-2, PA-4, and PA-5 only for operator comparison. In Blender Edit Mode on `body-beech`, click the narrow side-body faces one by one and separate exactly that operator-selected set as `pinch-body`. Do not use a script, pixel analysis, segmentation, mask, contour, registration, vectorization, automatic simplification/crop, proximity query, bounds query, material selection, or scripted polygon selection. Keep `outer-pinch-opposition` intact and nonselectable as body. Delete only Blender's default camera/light, inspect normals and seams, and save the tracked `.blend`. Record the manually observed original polygon indices, source/result polygon counts, accepted/corrected paths/hashes, evidence refs, and `prohibitedAutomationUsed:false` in the correction report; leave `humanApproval` absent.

- [ ] **Step 4: Stop for human review before writing any approval**

Render the full board normally and render `pinch-body` isolated in a contrasting material without changing its faces. After both candidate files exist, capture `candidateGeneratedAt` with `rtk date -u +%Y-%m-%dT%H:%M:%SZ`; do not create an approval object yet. Show both full-frame images and PA-2/PA-4/PA-5 to the human reviewer. Require an explicit verdict that the isolated region is the narrow side body, does not include the bottom band, and does not overlap the jug/edges. On rejection, keep the candidate unapproved and return to Step 3. On approval only, run `rtk date -u +%Y-%m-%dT%H:%M:%SZ` again and record that actual RFC3339 UTC instant, reviewer identity, notes, and both render SHA-256 values in `humanApproval`; never prefill or backdate it. Then hash-bind the report and corrected source from the manifest. Validation rejects an approval before `candidateGeneratedAt` or after the current clock. The date-only 2026-09-20 evidence approvals are unrelated provenance and are not comparison instants.

- [ ] **Step 5: Run the Port audit cycle**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_batch_03_source_contract.py -q -k port`

Expected: PASS; the accepted parent hash remains unchanged, corrected/report/render hashes match, `reviewedAt` is an RFC3339 UTC instant at or after `candidateGeneratedAt` and not after the validation clock, every source object is mapped once, and `outer-pinch-opposition` is body. Mutating it to a contact fails `Port outer-pinch-opposition must remain body`; deleting `pinch-body` fails `Port pinch-body correction is missing`.

- [ ] **Step 6: Commit, push, and obtain a fresh geometry review**

```bash
rtk git add docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/authored-source/frictitious-port-a-board.blend docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/frictitious-port-a-board.contact-map.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/frictitious-port-a-board.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/frictitious-port-a-board-normal.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/frictitious-port-a-board-pinch-body-isolated.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/frictitious-port-a-board.source.json Tools/HangboardModels/test_batch_03_source_contract.py
rtk git commit -m "docs: approve port side pinch correction"
rtk git push
```

A fresh reviewer verifies the tracked render hashes and `.blend` selection against PA-2/PA-4/PA-5. If that review rejects the boundary, revert only this task through a new corrective commit; do not continue to package conversion.

## Task 6: Manually correct and approve the Nature Oak jug and combined pinch

Assign this task to a fresh implementation agent and a different reviewer. Keep jug geometry approval separate from the two-node pinch mapping approval.

**Files:**

- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/authored-source/nature-stone-hanger-mini.blend`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini.contact-map.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/nature-stone-hanger-mini.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-{normal,internal-jug-isolated,combined-pinch-isolated}.png`
- Modify: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/nature-stone-hanger-mini.source.json`
- Modify: `Tools/HangboardModels/test_batch_03_source_contract.py`

**Interfaces:**

- Consumes: retained Oak GLB hash `d9eedc2407d836bf008087e547fde76d81ecc41f306c7e2ce526c49524be626e`, evidence refs `NS-1..NS-5`, and Task 3 correction chain.
- Produces: `internal-pull-up-jug`, an approved two-node `pinch-60`, one hash-bound correction report with two actual-time approval objects, and `verify_oak_correction(report, mapping) -> None`.

- [ ] **Step 1: Add the Oak RED contract**

Require ordered IDs `granite-edge-15,wood-edge-15-incut,pinch-60,pull-up-jug`. Require `granite-edge-15mm→granite-edge-15`, `wood-edge-15mm→wood-edge-15-incut`, both `outer-jug-pinch-upper→pinch-60` and `outer-pinch-lower→pinch-60`, new `internal-pull-up-jug→pull-up-jug`, `body-oak/body-granite-front` as body, and marker rows `[-0.0486,0,0]`/`[0.0486,0,0]`. Before authoring, fail `Oak internal-jug approval is missing`; after only that approval, fail `Oak combined-pinch approval is missing`.

- [ ] **Step 2: Manually partition only the internal broad recess**

Use an owned/trapped Blender workspace as in Task 5. With NS-2, NS-4, and NS-5 visible for comparison, enter Edit Mode on `body-oak`, click internal broad recess/cavity faces one by one, and separate them as `internal-pull-up-jug`. Use none of the prohibited image/proximity/bounds/scripted selection methods listed in Task 5. Keep both exterior meshes unchanged. Inspect that the jug excludes `outer-jug-pinch-upper`, the exterior pieces contain no jug faces, and the corrected scene contains only retained meshes/markers. Save the tracked `.blend`; record manually observed polygon indices/counts and `prohibitedAutomationUsed:false`, but no approvals.

- [ ] **Step 3: Stop for two independent human approvals**

Render normal, isolated `internal-pull-up-jug`, and combined isolated `outer-jug-pinch-upper + outer-pinch-lower`. After all three candidates exist, capture their shared `candidateGeneratedAt` with `rtk date -u +%Y-%m-%dT%H:%M:%SZ`; create no approval object yet. First require explicit human approval that the jug is the internal broad recess and excludes the upper exterior patch. Only after that inspection, capture the real RFC3339 UTC instant with the same `rtk date` command and write `jugGeometryApproval`. Separately require explicit approval that both exterior pieces form one complete `pinch-60` and contain no jug surface; only after that inspection capture a new real instant and write `pinchMappingApproval`. Each object stores reviewer, notes, and the exact relevant render hash; neither value is prefilled or backdated, and neither may be after the validation clock. If either is rejected, keep both approval objects out of the source manifest and return to Step 2 or the mapping. The date-only evidence approvals are not used for ordering.

- [ ] **Step 4: Complete the correction chain and run the Oak audit**

After both approvals, write the manifest's single `humanApproval` using the later actual review instant and notes referencing both nested approvals; hash-bind the accepted source, corrected source, report, and three renders. Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_batch_03_source_contract.py -q -k oak`

Expected: PASS. `pull-up-jug` has exactly node set `{internal-pull-up-jug}`; `pinch-60` has exactly `{outer-jug-pinch-upper, outer-pinch-lower}`; both approvals are RFC3339 UTC instants at or after `candidateGeneratedAt` and not after the validation clock. Swapping the upper node to the jug fails `Oak pull-up-jug must bind only internal-pull-up-jug`; dropping either pinch node fails `Oak pinch-60 must bind both exterior nodes`.

- [ ] **Step 5: Commit, push, and obtain a fresh two-surface review**

```bash
rtk git add docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/authored-source/nature-stone-hanger-mini.blend docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini.contact-map.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/nature-stone-hanger-mini.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-normal.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-internal-jug-isolated.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-combined-pinch-isolated.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/nature-stone-hanger-mini.source.json Tools/HangboardModels/test_batch_03_source_contract.py
rtk git commit -m "docs: approve nature oak contact corrections"
rtk git push
```

A fresh reviewer independently accepts or rejects the jug and combined pinch. Stop on either rejection.

## Task 7: Deliberately review KARMA8A's multi-node pinch and close all source mappings

Assign this task to a fresh implementation agent and a different reviewer. It changes no KARMA8A geometry.

**Files:**

- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/nature-stone-hanger-mini-karma8a-mapping-review.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-karma8a-{normal,combined-pinch-isolated}.png`
- Modify: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini-karma8a.contact-map.json`
- Modify: `Tools/HangboardModels/test_batch_03_source_contract.py`
- Modify: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/README.md`

**Interfaces:**

- Consumes: retained KARMA8A GLB hash `3ebe92f518cc66dd03f8256ebd6260a950f01252b74adbeb2b0c3116e775ffb6`, evidence refs `NK-1..NK-5`, and the Task 4 structural mapping.
- Produces: an actual-time mapping approval over exact node set `{outer-pinch-upper,outer-pinch-lower}` and `verify_complete_batch_03_source_contract(root: Path) -> SourceContractReport` reporting `acceptedSources:8`, `manifests:8`, `mappings:8`, `geometryCorrections:5`, `mappingReviews:1`.

- [ ] **Step 1: Add the final-mapping RED contract**

Require KARMA8A node sets `granite-edge-15→{granite-edge-15mm}`, `wood-edge-15→{wood-edge-15mm}`, and `pinch-60→{outer-pinch-upper,outer-pinch-lower}`; require `sourceGeometryChanged:false`. Before review, fail `KARMA8A combined-pinch approval is missing`. The complete-contract test requires the exact eight source/manifests/mappings and returns the five counts in the Interfaces block. Require the exact corrected source-key set `{frictitious-port-a-board,nature-stone-hanger-mini,plateau-lifting-edge-depth-18mm,plateau-lifting-edge-depth-15mm,plateau-lifting-edge-depth-10mm}` and rerun Task 4's three-source correction/approval mutations; five arbitrary corrections cannot satisfy this gate.

- [ ] **Step 2: Stop for deliberate human mapping review**

Open a clean, unmodified copy of the retained KARMA8A GLB. Render a normal full-frame view and a combined isolated highlight of the two existing exterior nodes; rendering assigns temporary materials/camera only and must not analyze pixels, select faces, alter geometry, or save over the retained source. After both files exist, capture `candidateGeneratedAt` with `rtk date -u +%Y-%m-%dT%H:%M:%SZ`, with no approval object. Show both renders with NK-2/NK-4/NK-5. Require explicit human confirmation that both nodes together form the complete exterior `pinch-60` and neither edge/body is included. On rejection, correct only the explicit mapping and repeat candidate generation. On approval only, capture a new actual RFC3339 UTC instant with the same `rtk date` command, then write reviewer/notes, both render hashes, exact node IDs, `sourceGeometryChanged:false`, and `prohibitedAutomationUsed:false`. Never prefill/backdate the value; validation requires it at or after candidate generation and not in the future. The date-only evidence approval is not a comparison instant.

- [ ] **Step 3: Run the final source/mapping audit cycle**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_batch_03_source_contract.py -q`

Expected: PASS with `{"acceptedSources":8,"manifests":8,"mappings":8,"geometryCorrections":5,"mappingReviews":1}`. A missing second KARMA node fails `KARMA8A pinch-60 must bind both exterior nodes`; any KARMA8A correction declaration fails `KARMA8A mapping review must not claim geometry changed`; an incomplete Port/Oak chain retains the exact Task 5/6 diagnostic, and a missing/mismatched Plateau chain retains Task 4's exact diagnostic. No package conversion proceeds with any of the three Plateau corrections unapproved.

- [ ] **Step 4: Commit, push, and obtain a fresh final source-contract review**

```bash
rtk git add docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/nature-stone-hanger-mini-karma8a-mapping-review.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-karma8a-normal.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/corrections/review/nature-stone-hanger-mini-karma8a-combined-pinch-isolated.png docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini-karma8a.contact-map.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/README.md Tools/HangboardModels/test_batch_03_source_contract.py
rtk git commit -m "docs: approve batch 03 source mappings"
rtk git push
```

A fresh reviewer reruns the complete source-contract test and visually rechecks the tracked KARMA8A render pair. Tasks 8-18 may consume mappings only after approval.

## Shared package contract for Tasks 8-12

This section is a contract reference, not an implementation task. Each following task owns exactly one package, one RED/GREEN cycle, one commit/push, and one independent review.

**Shared file map:**

- Create: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`
- Modify: `Hangboards/{aelith-cyclops-011,frictitious-nug,frictitious-port-a-board,nature-stone-hanger-mini,nature-stone-hanger-mini-karma8a}/board.json`
- Delete: all raster files below those five package `assets/` directories
- Create: `Hangboards/{aelith-cyclops-011,frictitious-nug,frictitious-port-a-board,nature-stone-hanger-mini,nature-stone-hanger-mini-karma8a}/assets/primary.usdz`
- Create: `Hangboards/{aelith-cyclops-011,frictitious-nug,frictitious-port-a-board,nature-stone-hanger-mini,nature-stone-hanger-mini-karma8a}/assets/primary.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/{aelith-cyclops-011,frictitious-nug,frictitious-port-a-board,nature-stone-hanger-mini,nature-stone-hanger-mini-karma8a}.json`

**Shared interfaces:**

- Consumes: Task 3 importer, Tasks 4-7 approved sources/mappings, and landed runtime-plan Tasks 1, 2, and 6. Suspension marker conversion is fixed source Z-up to descriptor basis `(x,y,z) -> (x,z,-y)`.
- Produces across Tasks 8-12: five packages with presentation ID `primary`, exactly 19 ordered positions, full-inventory descriptors, and presentation-local canonical pose keys.

### Exact production-package matrix

Assert contact arrays and ordered positions exactly equal spec lines 95-102 and 172-192. Assert all five packages contain only `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; media is original model/default `primary`; no contact geometry/PNG exists; every descriptor hash matches USDZ; descriptor contacts equal the package inventory; and every `canonicalPoses` key set exactly equals the package's position IDs.

```python
EXPECTED_CONTACTS = {
    "aelith.cyclops-011": ["mono-20"],
    "frictitious.nug": ["edge-25", "edge-20", "edge-13", "edge-8", "jug-40", "pinch-60"],
    "frictitious.port-a-board": ["edge-30", "edge-25", "edge-20", "edge-15", "edge-12", "edge-10", "edge-8", "jug-outer-rim", "pinch-body"],
    "nature.stone-hanger-mini": ["granite-edge-15", "wood-edge-15-incut", "pinch-60", "pull-up-jug"],
    "nature.stone-hanger-mini-karma8a": ["granite-edge-15", "wood-edge-15", "pinch-60"],
}
EXPECTED_POSITIONS = {
    "aelith.cyclops-011": [("front-cup", ["mono-20"])],
    "frictitious.nug": [
        ("front-25", ["edge-25"]),
        ("front-inverted-20", ["edge-20"]),
        ("reverse-13", ["edge-13"]),
        ("reverse-inverted-8", ["edge-8"]),
        ("outer-upper", ["jug-40"]),
        ("outer-lower", ["pinch-60"]),
    ],
    "frictitious.port-a-board": [
        ("front-upright", ["edge-30", "edge-25"]),
        ("front-inverted", ["edge-20"]),
        ("reverse-upright", ["edge-12", "edge-10"]),
        ("reverse-inverted", ["edge-15", "edge-8"]),
        ("outer-upper", ["jug-outer-rim"]),
        ("pinch-side", ["pinch-body"]),
    ],
    "nature.stone-hanger-mini": [
        ("front-upright", ["pull-up-jug", "granite-edge-15"]),
        ("wood-inverted", ["wood-edge-15-incut"]),
        ("pinch-side", ["pinch-60"]),
    ],
    "nature.stone-hanger-mini-karma8a": [
        ("granite-front", ["granite-edge-15"]),
        ("wood-inverted", ["wood-edge-15"]),
        ("pinch-side", ["pinch-60"]),
    ],
}
assert [(p.id, list(p.contact_ids)) for p in board.positions] == EXPECTED_POSITIONS[board.id]
assert {p.presentation_id for p in board.positions} == {"primary"}
assert [contact.id for contact in board.contacts] == EXPECTED_CONTACTS[board.id]
assert set(package_files) == {"board.json", "assets/primary.usdz", "assets/primary.model.json"}
```

### Exact correction-specific negative matrix

Assert Port has no `pocket-30-two-finger-mono`, blocker ID, `outer-lower` position, or descriptor contact binding from `outer-pinch-opposition`; its `pinch-body` binding is the new corrected node. Assert Oak name explicitly contains `Oak`, product URL is exactly `https://natureclimbing.com/products/stone-hanger-mini-oak`, no new batch-03 audit/package text contains the stale Beech URL/name, `pull-up-jug` binds only `internal-pull-up-jug`, and each Nature descriptor maps both reviewed exterior nodes to `pinch-60`. Use these mutation diagnostics: unexpected Port ID → `frictitious.port-a-board: forbidden contact pocket-30-two-finger-mono`; bottom-band binding → `frictitious.port-a-board: pinch-body nodes must equal ['pinch-body']`; Oak jug swap → `nature.stone-hanger-mini: pull-up-jug nodes must equal ['internal-pull-up-jug']`; either incomplete Nature pinch → `BOARD_ID: pinch-60 must bind both reviewed exterior nodes`; raster/contact geometry → `BOARD_ID: model-only package contains raster fallback`.

### Exact board JSON contract

For each dictionary row above, replace `contacts` and `positions` in that exact order. Omit `effectiveDepths` from every position. Replace presentations with exactly one `primary` item whose media is `{"type":"model","assetPath":"assets/primary.usdz","descriptorPath":"assets/primary.model.json"}`, whose derivation is `{"type":"original"}`, and whose default is true. Remove every orientation block because suspension canonical poses own the complete setup. Retain source-backed contact metadata; leave Port `jug-outer-rim` and `pinch-body` depth absent. Remove every raster asset only after Step 7 succeeds.

### Exact suspension contract

Use `singleCord` for Aelith and `pairedLeadCord` for the other four. Convert marker centers exactly:

```text
Aelith attachment: [0, 0.0251, 0.014]
NUG left/right: [-0.053, 0, 0.02], [0.053, 0, 0.02]
Port left/right: [-0.054, 0, 0.024], [0.054, 0, 0.024]
Nature Oak left/right open grooves: [-0.0486, 0, 0], [0.0486, 0, 0]
Nature KARMA8A left/right open grooves: [-0.0511, 0, 0], [0.0511, 0, 0]
```

Use these exact body node IDs: Aelith `body-blue-aluminum`; NUG `body-beech`; Port `body-beech`; Oak `body-oak`; KARMA8A `body-smoked-oak`. Never use a marker name removed from USDZ. For Nature, use one-point open passages, never entry/exit bore pairs. Begin every presentation with anchor offset `[0,0.15,0]`, `restLength:0.4`, `radius:0.002`, material `matteCord`, and provenance beginning `displayEstimate;`. `validate_suspension_candidate(board, presentation, position, triangles) -> SuspensionCheck` must require `solved`, both length checks, mesh clearance, no self-intersection, open-route termination, and framing; it returns the first exact diagnostic `PACKAGE/PRESENTATION/POSITION: CHECK failed`. If a seed fails, manually choose and record the rejected and replacement numeric values in the import report, then rerun the unchanged validator.

### Exact pose contract

Use translation `[0,0,0]`, camera `viewDirection: [0,0,-1]`, and `fitPadding: 0.1`. The fixed source-to-descriptor quaternion conversion yields these seeds:

```text
front 22°: [0.1908089953765448,0,0,0.981627183447664]
front inverted: [1.1683681271820385e-17,0.1908089953765448,-0.981627183447664,6.010732940826067e-17]
reverse 22°: [1.1683681271820385e-17,0.981627183447664,0.1908089953765448,6.010732940826067e-17]
reverse inverted: [0.981627183447664,0,0,-0.19080899537654475]
upper side: [0.7071067811865475,0,0,0.7071067811865476]
lower side: [-0.7071067811865475,0,0,0.7071067811865476]
```

Apply the seeds exactly as follows: front 22° to Aelith `front-cup`, NUG `front-25`, Port `front-upright`, Oak `front-upright`, and KARMA8A `granite-front`; front inverted to NUG `front-inverted-20`, Port `front-inverted`, Oak `wood-inverted`, and KARMA8A `wood-inverted`; reverse 22° to NUG `reverse-13` and Port `reverse-upright`; reverse inverted to NUG `reverse-inverted-8` and Port `reverse-inverted`; upper side to both `outer-upper` positions; lower side to NUG `outer-lower`. For Port and the two Nature `pinch-side` positions, start from a side-on view, manually adjust the quaternion until the approved complete corrected contact and both cord exits are visible, normalize it, record its four exact numeric components in the import report and package, and require byte-for-byte equality between them. Do not reuse a bottom-band or upper-only batch pose. Record any manually chosen pose-specific exterior `cordContactPoints` as exact triples with `displayEstimate` provenance, then run `validate_suspension_candidate` and the human visibility gate.

Each package task calls `import_package(manifest_path, mapping_path, package_id, board_json, output_directory, asset_stem="primary")` once with a new nonexistent owner-named output directory. That explicit stem supplies `presentation_id="primary"` to source verification; require the manifest and any correction report to declare `primary` and the returned `VerifiedSource.presentation_id` to match. It asserts `assetPath == "assets/primary.usdz"`, `descriptorPath == "assets/primary.model.json"`, and the package-specific `sourceGeometryChanged` value before promoting those two files. Never export over a retained source; remove that package's raster files only after model/descriptor hashes agree.

## Task 8: Build the Aelith Cyclops #011 model-only package

Assign this task to a fresh implementation agent and a different reviewer.

**Files:**

- Create: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`
- Modify: `Hangboards/aelith-cyclops-011/board.json`
- Delete: `Hangboards/aelith-cyclops-011/assets/primary.png`
- Create: `Hangboards/aelith-cyclops-011/assets/primary.usdz`
- Create: `Hangboards/aelith-cyclops-011/assets/primary.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/aelith-cyclops-011.json`

**Interfaces:**

- Consumes: Task 3 importer; Task 4 manifest/mapping; contact node `edge-20mm→mono-20`; attachment marker `[0,-0.014,0.0251]`.
- Produces: `aelith.cyclops-011/primary/front-cup`, one-contact descriptor, `singleCord` suspension, and `sourceGeometryChanged:false`.

- [ ] **Step 1: Add package-specific RED tests**

Add `test_aelith_cyclops_011_model_package` and `test_aelith_cyclops_011_rejects_fallback`. Require contacts `['mono-20']`, position `[('front-cup','primary',['mono-20'])]`, exact files `{board.json,assets/primary.usdz,assets/primary.model.json}`, descriptor node set `{edge-20mm:mono-20}`, and no raster/contact geometry. The existing package fails exactly `aelith.cyclops-011: model-only package contains raster fallback`.

- [ ] **Step 2: Run RED**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k aelith_cyclops_011`

Expected: FAIL only on the raster/model contract.

- [ ] **Step 3: Author exact JSON, suspension, and pose**

Author one original/default `primary` model presentation and `front-cup` without `effectiveDepths`. Use `singleCord`, body node `body-blue-aluminum`, attachment `[0,0.0251,0.014]`, anchor `[0,0.15,0]`, rest length `0.4`, radius `0.002`, material `matteCord`, quaternion `[0.1908089953765448,0,0,0.981627183447664]`, translation `[0,0,0]`, view `[0,0,-1]`, and padding `0.1`; label every non-source suspension number `displayEstimate` and require the shared solver checks.

- [ ] **Step 4: Import, verify, promote, and remove raster**

```bash
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/aelith-cyclops-011.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/aelith-cyclops-011.contact-map.json --package aelith.cyclops-011 --board-json Hangboards/aelith-cyclops-011/board.json --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-aelith --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/aelith-cyclops-011.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/aelith-cyclops-011.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/aelith-cyclops-011.contact-map.json --package aelith.cyclops-011 --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-aelith --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/aelith-cyclops-011.json --repository-root . --expected-source-geometry-changed false
```

Expected gate output is exactly `PASS aelith.cyclops-011/primary verified import output`. Stop on any other output or nonzero status. Only after that successful gate may the implementer run this separate promotion/removal block:

```bash
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-aelith/assets/primary.usdz Hangboards/aelith-cyclops-011/assets/primary.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-aelith/assets/primary.model.json Hangboards/aelith-cyclops-011/assets/primary.model.json
rtk git rm Hangboards/aelith-cyclops-011/assets/primary.png
```

The gate rechecks the Task 4 accepted parent, package/stem paths, exact node/contact mapping, both generated hashes, and `sourceGeometryChanged:false`; promotion and raster removal are forbidden if it does not pass.

- [ ] **Step 5: Run GREEN, commit, push, and review**

```bash
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k aelith_cyclops_011
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk git add Hangboards/aelith-cyclops-011 Tools/HangboardPackages/tests/test_batch_03_model_packages.py docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/aelith-cyclops-011.json
rtk git commit -m "feat: migrate aelith cyclops 011 to 3d"
rtk git push
```

A fresh reviewer checks the one contact, single-cord route, normal/highlight view, pose, hashes, and absence of raster before Task 9.

## Task 9: Build the Frictitious NUG model-only package

Assign this task to a fresh implementation agent and a different reviewer.

**Files:**

- Modify: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`
- Modify: `Hangboards/frictitious-nug/board.json`
- Delete: `Hangboards/frictitious-nug/assets/primary.png`
- Delete: `Hangboards/frictitious-nug/assets/reverse.png`
- Create: `Hangboards/frictitious-nug/assets/primary.usdz`
- Create: `Hangboards/frictitious-nug/assets/primary.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-nug.json`

**Interfaces:**

- Consumes: Task 3 importer and Task 4 NUG manifest/mapping.
- Produces: six ordered contacts/positions on `primary`, paired-lead suspension, full descriptor, and `sourceGeometryChanged:false`.

- [ ] **Step 1: Add and run package-specific RED tests**

Add `test_frictitious_nug_model_package` and `test_frictitious_nug_node_bindings`. Require contacts `edge-25,edge-20,edge-13,edge-8,jug-40,pinch-60`; positions `front-25`, `front-inverted-20`, `reverse-13`, `reverse-inverted-8`, `outer-upper`, `outer-lower` with the shared matrix's contact arrays; exact contact nodes `front-edge-25mm`, `front-edge-20mm`, `reverse-edge-13mm`, `reverse-edge-8mm`, `outer-jug`, `outer-pinch-opposition`; and only three package files. Run `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k frictitious_nug`; expect `frictitious.nug: model-only package contains raster fallback`.

- [ ] **Step 2: Author exact JSON, suspension, and six poses**

Use paired attachments on `body-beech` at `[-0.053,0,0.02]`/`[0.053,0,0.02]`, common anchor/cord/camera values from the shared contract, and pose quaternions in order: front 22°, front inverted, reverse 22°, reverse inverted, upper side, lower side. Canonical pose keys must equal the six position IDs; omit `effectiveDepths` and orientation metadata.

- [ ] **Step 3: Import and promote exact outputs**

```bash
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/frictitious-nug.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/frictitious-nug.contact-map.json --package frictitious.nug --board-json Hangboards/frictitious-nug/board.json --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-nug --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-nug.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/frictitious-nug.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/frictitious-nug.contact-map.json --package frictitious.nug --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-nug --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-nug.json --repository-root . --expected-source-geometry-changed false
```

Expected gate output is exactly `PASS frictitious.nug/primary verified import output`. Stop on any other output or nonzero status. Only after that successful gate may the implementer run this separate promotion/removal block:

```bash
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-nug/assets/primary.usdz Hangboards/frictitious-nug/assets/primary.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-nug/assets/primary.model.json Hangboards/frictitious-nug/assets/primary.model.json
rtk git rm Hangboards/frictitious-nug/assets/primary.png Hangboards/frictitious-nug/assets/reverse.png
```

The gate rechecks the Task 4 accepted parent, package/stem paths, exact six-contact node identities, both generated hashes, and `sourceGeometryChanged:false`; promotion and raster removal are forbidden if it does not pass.

- [ ] **Step 4: Run GREEN, commit, push, and review**

```bash
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k frictitious_nug
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk git add Hangboards/frictitious-nug Tools/HangboardPackages/tests/test_batch_03_model_packages.py docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-nug.json
rtk git commit -m "feat: migrate frictitious nug to 3d"
rtk git push
```

A fresh reviewer checks six exact bindings/poses, paired-cord clearance, hashes, and raster removal before Task 10.

## Task 10: Build the Frictitious Port-A-Board model-only package

Assign this task to a fresh implementation agent and a different reviewer.

**Files:**

- Modify: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`
- Modify: `Hangboards/frictitious-port-a-board/board.json`
- Delete: `Hangboards/frictitious-port-a-board/assets/primary.png`
- Delete: `Hangboards/frictitious-port-a-board/assets/front-inverted.png`
- Delete: `Hangboards/frictitious-port-a-board/assets/back.png`
- Delete: `Hangboards/frictitious-port-a-board/assets/back-inverted.png`
- Delete: `Hangboards/frictitious-port-a-board/assets/side.png`
- Create: `Hangboards/frictitious-port-a-board/assets/primary.usdz`
- Create: `Hangboards/frictitious-port-a-board/assets/primary.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-port-a-board.json`

**Interfaces:**

- Consumes: Task 3 importer and Task 5 approved corrected source/mapping.
- Produces: nine contacts, six positions, corrected `pinch-side`, paired suspension, and `sourceGeometryChanged:true`. Task 10 is the Port package producer consumed by runtime/experience work.

- [ ] **Step 1: Add and run package-specific RED tests**

Add `test_frictitious_port_a_board_model_package` and `test_frictitious_port_a_board_corrected_nodes`. Require the exact nine-contact/six-position rows in the shared matrix, no pocket or `outer-lower`, `pinch-body→pinch-body`, `outer-pinch-opposition→body`, and absent depths for `jug-outer-rim`/`pinch-body`. Run `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k frictitious_port_a_board`; expect `frictitious.port-a-board: forbidden contact pocket-30-two-finger-mono` before conversion.

- [ ] **Step 2: Author exact JSON, suspension, and poses**

Use paired attachments on `body-beech` at `[-0.054,0,0.024]`/`[0.054,0,0.024]`. Assign front 22°, front inverted, reverse 22°, reverse inverted, and upper-side quaternions to the first five positions. For `pinch-side`, manually select a side-on quaternion that shows the approved complete `pinch-body` and both cord exits, normalize it, and write the identical four numeric components to package/report; record the rejected bottom-band pose and run solver plus human visibility review. Omit `effectiveDepths` and orientation.

- [ ] **Step 3: Import and promote exact outputs**

```bash
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/frictitious-port-a-board.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/frictitious-port-a-board.contact-map.json --package frictitious.port-a-board --board-json Hangboards/frictitious-port-a-board/board.json --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-port --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-port-a-board.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/frictitious-port-a-board.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/frictitious-port-a-board.contact-map.json --package frictitious.port-a-board --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-port --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-port-a-board.json --repository-root . --expected-source-geometry-changed true
```

Expected gate output is exactly `PASS frictitious.port-a-board/primary verified import output`. Stop on any other output or nonzero status. Only after that successful gate may the implementer run this separate promotion/removal block:

```bash
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-port/assets/primary.usdz Hangboards/frictitious-port-a-board/assets/primary.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-port/assets/primary.model.json Hangboards/frictitious-port-a-board/assets/primary.model.json
rtk git rm Hangboards/frictitious-port-a-board/assets/primary.png Hangboards/frictitious-port-a-board/assets/front-inverted.png Hangboards/frictitious-port-a-board/assets/back.png Hangboards/frictitious-port-a-board/assets/back-inverted.png Hangboards/frictitious-port-a-board/assets/side.png
```

The gate rechecks the complete Task 5 accepted-parent/correction-report/approval chain, package/stem paths, corrected `pinch-body` and body-node identities, both generated hashes, and `sourceGeometryChanged:true`; promotion and raster removal are forbidden if it does not pass.

- [ ] **Step 4: Run GREEN, commit, push, and review**

```bash
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k frictitious_port_a_board
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk git add Hangboards/frictitious-port-a-board Tools/HangboardPackages/tests/test_batch_03_model_packages.py docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/frictitious-port-a-board.json
rtk git commit -m "feat: migrate port a board to 3d"
rtk git push
```

A fresh reviewer checks corrected side-only highlighting, all nine nodes, exact pose, cord clearance, unmeasured depths, hashes, and no raster before the Oak package task begins.

## Task 11: Build the Nature Stone Hanger Mini Oak model-only package

Assign this task to a fresh implementation agent and a different reviewer.

**Files:**

- Modify: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`
- Modify: `Hangboards/nature-stone-hanger-mini/board.json`
- Delete: `Hangboards/nature-stone-hanger-mini/assets/primary.png`
- Delete: `Hangboards/nature-stone-hanger-mini/assets/side.png`
- Create: `Hangboards/nature-stone-hanger-mini/assets/primary.usdz`
- Create: `Hangboards/nature-stone-hanger-mini/assets/primary.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini.json`

**Interfaces:**

- Consumes: Task 3 importer and Task 6 approved corrected source/mapping.
- Produces: Oak identity, four contacts/three positions, corrected jug, combined pinch, paired open-groove suspension, and `sourceGeometryChanged:true`.

- [ ] **Step 1: Add and run package-specific RED tests**

Add `test_nature_stone_hanger_mini_oak_model_package` and `test_nature_stone_hanger_mini_oak_corrected_nodes`. Require exact Oak name, URL `https://natureclimbing.com/products/stone-hanger-mini-oak`, contacts `granite-edge-15,wood-edge-15-incut,pinch-60,pull-up-jug`, positions from the shared matrix, jug node exactly `{internal-pull-up-jug}`, and pinch nodes exactly `{outer-jug-pinch-upper,outer-pinch-lower}`. Run `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k nature_stone_hanger_mini_oak`; expect the first diagnostic `nature.stone-hanger-mini: product identity must be the approved Oak revision`.

- [ ] **Step 2: Author exact JSON, suspension, and poses**

Use `body-oak`, open-groove points `[-0.0486,0,0]`/`[0.0486,0,0]`, front 22° for `front-upright`, front-inverted for `wood-inverted`, and a manually normalized side-on quaternion for `pinch-side` that shows both approved exterior nodes and grooves. Record the identical chosen quaternion in package/report, run solver/human visibility, and omit `effectiveDepths`/orientation.

- [ ] **Step 3: Import and promote exact outputs**

```bash
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/nature-stone-hanger-mini.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini.contact-map.json --package nature.stone-hanger-mini --board-json Hangboards/nature-stone-hanger-mini/board.json --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-oak --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/nature-stone-hanger-mini.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini.contact-map.json --package nature.stone-hanger-mini --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-oak --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini.json --repository-root . --expected-source-geometry-changed true
```

Expected gate output is exactly `PASS nature.stone-hanger-mini/primary verified import output`. Stop on any other output or nonzero status. Only after that successful gate may the implementer run this separate promotion/removal block:

```bash
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-oak/assets/primary.usdz Hangboards/nature-stone-hanger-mini/assets/primary.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-oak/assets/primary.model.json Hangboards/nature-stone-hanger-mini/assets/primary.model.json
rtk git rm Hangboards/nature-stone-hanger-mini/assets/primary.png Hangboards/nature-stone-hanger-mini/assets/side.png
```

The gate rechecks the complete Task 6 accepted-parent/correction-report/approval chain, package/stem paths, corrected jug and two-node pinch identities, both generated hashes, and `sourceGeometryChanged:true`; promotion and raster removal are forbidden if it does not pass.

- [ ] **Step 4: Run GREEN, commit, push, and review**

```bash
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k nature_stone_hanger_mini_oak
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk git add Hangboards/nature-stone-hanger-mini Tools/HangboardPackages/tests/test_batch_03_model_packages.py docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini.json
rtk git commit -m "feat: migrate nature oak mini to 3d"
rtk git push
```

A fresh reviewer independently checks Oak identity, internal jug, complete two-node pinch, pose, open grooves, hashes, and raster removal before Task 12.

## Task 12: Build the Nature Stone Hanger Mini × KARMA8A model-only package

Assign this task to a fresh implementation agent and a different reviewer.

**Files:**

- Modify: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`
- Modify: `Hangboards/nature-stone-hanger-mini-karma8a/board.json`
- Delete: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png`
- Create: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.usdz`
- Create: `Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini-karma8a.json`

**Interfaces:**

- Consumes: Task 3 importer, Task 4 source/mapping, and Task 7 mapping approval.
- Produces: three contacts/positions, approved two-node pinch, paired open-groove suspension, and `sourceGeometryChanged:false`.

- [ ] **Step 1: Add and run package-specific RED tests**

Add `test_nature_stone_hanger_mini_karma8a_model_package` and `test_nature_stone_hanger_mini_karma8a_combined_pinch`. Require contacts `granite-edge-15,wood-edge-15,pinch-60`, positions `granite-front`, `wood-inverted`, `pinch-side`, no jug, and pinch node set `{outer-pinch-upper,outer-pinch-lower}`. Run `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k nature_stone_hanger_mini_karma8a`; expect `nature.stone-hanger-mini-karma8a: model-only package contains raster fallback`.

- [ ] **Step 2: Author exact JSON, suspension, and poses**

Use `body-smoked-oak`, open-groove points `[-0.0511,0,0]`/`[0.0511,0,0]`, front 22° for `granite-front`, front-inverted for `wood-inverted`, and a manually normalized/reviewed side-on quaternion for `pinch-side` showing both nodes and grooves. Record exact identical components in package/report and run solver/human review.

- [ ] **Step 3: Import and promote exact outputs**

```bash
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/nature-stone-hanger-mini-karma8a.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini-karma8a.contact-map.json --package nature.stone-hanger-mini-karma8a --board-json Hangboards/nature-stone-hanger-mini-karma8a/board.json --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-karma8a --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini-karma8a.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/nature-stone-hanger-mini-karma8a.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/nature-stone-hanger-mini-karma8a.contact-map.json --package nature.stone-hanger-mini-karma8a --asset-stem primary --output-directory .context/sweet-hamster-batch03-model-packages-karma8a --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini-karma8a.json --repository-root . --expected-source-geometry-changed false
```

Expected gate output is exactly `PASS nature.stone-hanger-mini-karma8a/primary verified import output`. Stop on any other output or nonzero status. Only after that successful gate may the implementer run this separate promotion/removal block:

```bash
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-karma8a/assets/primary.usdz Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-karma8a/assets/primary.model.json Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.model.json
rtk git rm Hangboards/nature-stone-hanger-mini-karma8a/assets/primary.png
```

The gate rechecks the Task 7 mapping approval, Task 4 accepted parent, package/stem paths, exact two-node pinch identity, both generated hashes, and `sourceGeometryChanged:false`; promotion and raster removal are forbidden if it does not pass.

- [ ] **Step 4: Run GREEN, commit, push, and review**

```bash
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k nature_stone_hanger_mini_karma8a
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk git add Hangboards/nature-stone-hanger-mini-karma8a Tools/HangboardPackages/tests/test_batch_03_model_packages.py docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/nature-stone-hanger-mini-karma8a.json
rtk git commit -m "feat: migrate nature karma8a mini to 3d"
rtk git push
```

A fresh reviewer checks all three positions, complete two-node pinch, open grooves, exact pose, hashes, and raster removal. Tasks 8-12 are then independently green.

## Task 13: Build Plateau's three-presentation package

**Files:**

- Modify: `Hangboards/plateau-lifting-edge/board.json`
- Delete: `Hangboards/plateau-lifting-edge/assets/primary.png`
- Create: `Hangboards/plateau-lifting-edge/assets/depth-18mm.usdz`
- Create: `Hangboards/plateau-lifting-edge/assets/depth-18mm.model.json`
- Create: `Hangboards/plateau-lifting-edge/assets/depth-15mm.usdz`
- Create: `Hangboards/plateau-lifting-edge/assets/depth-15mm.model.json`
- Create: `Hangboards/plateau-lifting-edge/assets/depth-10mm.usdz`
- Create: `Hangboards/plateau-lifting-edge/assets/depth-10mm.model.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-18mm.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-15mm.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-10mm.json`
- Modify: `Tools/HangboardPackages/tests/test_batch_03_model_packages.py`

**Interfaces:**

- Consumes: runtime-plan Tasks 1, 2, and 6: `BoardPosition.effectiveDepths: [String: HoldDepth]?`, multiple original presentations, presentation-local position/pose validation, full-inventory descriptors, and per-presentation cord checks; Task 3 `asset_stem` importer; Task 4's three separately approved corrected Plateau sources and Task 7's complete five-correction gate.
- Produces: the three exact package position/presentation IDs and assets consumed by runtime/experience plans; all use stable contact `edge-18`, omit every screw/mounting hole, preserve open cord exits, and report `sourceGeometryChanged:true`. Task 13 is the package plan's Plateau producer.

- [ ] **Step 1: Add Plateau's exact contract test**

Assert one contact `edge-18` with base exact depth 18; ordered presentations/positions `depth-18mm`, `depth-15mm`, `depth-10mm`; only 18 is default; each is original model media with same-named unique asset/descriptor; each position contains only `edge-18` and its corresponding exact map—18 uses `{edge-18: range(18,18)}`, 15 uses `{edge-18: range(15,15)}`, and 10 uses `{edge-18: range(10,10)}`; every descriptor has the full one-contact inventory; all six directed distinct-position transitions exist with `setupRequired`; blocker meshes are body/nonselectable; no blocker contacts or raster remain.

```python
depths = {"depth-18mm": 18, "depth-15mm": 15, "depth-10mm": 10}
assert [p.id for p in board.presentations] == list(depths)
assert [p.id for p in board.positions] == list(depths)
for position in board.positions:
    assert position.presentation_id == position.id
    assert position.contact_ids == ("edge-18",)
    value = position.effective_depths["edge-18"].range
    assert (value.minimum, value.maximum) == (depths[position.id], depths[position.id])
assert {(t.from_position_id, t.to_position_id, t.kind.value) for t in board.position_transitions} == {
    (source, target, "setupRequired")
    for source in depths for target in depths if source != target
}
```

- [ ] **Step 2: Add cross-wiring mutations**

Use a valid three-presentation fixture and apply these one-field mutations:

| Mutation | Exact first diagnostic |
| --- | --- |
| `depth-15mm.descriptorPath = assets/depth-18mm.model.json` | `plateau.lifting-edge: duplicate descriptor path assets/depth-18mm.model.json` |
| `depth-15mm.assetPath = assets/depth-18mm.usdz` | `plateau.lifting-edge: duplicate model asset path assets/depth-18mm.usdz` |
| 15 mm position `presentationID = depth-18mm` | `depth-15mm position must reference presentation depth-15mm` |
| 15 mm pose key renamed `depth-18mm` | `depth-15mm canonicalPoses keys must equal local positions ['depth-15mm']` |
| 15 mm effective range changed to 18 | `depth-15mm effective edge-18 depth must equal 15` |
| 10 mm descriptor inventory emptied | `depth-10mm descriptor contacts must equal ['edge-18']` |

Each mutation changes only the named field and must fail before asset loading from a different presentation.

Also parameterize the source/import gate over all three Plateau keys: removing a correction, replacing the compiled source with its accepted GLB or another depth's `.blend`, swapping approval/render bindings, or reporting `sourceGeometryChanged:false` must reject promotion with Task 4/Task 3 diagnostics. Verify exact black-body/oak-edge/reducer material and node/contact invariants against each approved corrected-source inventory. These tests verify the correction contract; human visual review establishes the absence of screw/mounting holes.

- [ ] **Step 3: Run focused tests and confirm red**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k plateau`

Expected first diagnostic: `plateau.lifting-edge: model-only package contains raster fallback`.

- [ ] **Step 4: Author exact Plateau JSON and suspension**

Write one contact `edge-18` with exact base range 18 and the three positions/effective-depth objects in Step 1. Write the six ordered transition objects `(18,15)`, `(15,18)`, `(18,10)`, `(10,18)`, `(15,10)`, `(10,15)`, each with `kind:setupRequired`. For every presentation use `pairedLeadCord`, body node `body-black-aluminum`, local `canonicalPoses` containing only its same-named position, marker points `[-0.05,-0.03,0.009]` and `[0.05,-0.03,0.009]`, and one-point open routes from the lower curled extrusion—never bores. Use quaternion `[-0.21643961393810288,0,0,0.9762960071199334]`, translation `[0,0,0]`, view `[0,0,-1]`, and padding `0.1` for each local pose. Run the shared `validate_suspension_candidate` independently against each model/blocker geometry and label anchor `[0,0.15,0]`, `restLength:0.4`, `radius:0.002`, material, camera, and pose provenance `displayEstimate`.

- [ ] **Step 5: Import all three approved corrected sources independently**

Revalidate all three Task 4 correction/approval chains before the first import. For each command below, the literal CLI `--asset-stem depth-18mm`, `depth-15mm`, or `depth-10mm` is the requested presentation passed by both `import_package` and `verify_import_output` to `verify_source_manifest`; require the manifest, correction report, and returned `VerifiedSource` to match that exact depth before corrected geometry resolution/opening. The manifests retain their immutable accepted GLB parents but resolve `compile_path` to their own corrected `.blend`; no accepted GLB may be used as the compiled Plateau source. A full chain swap must fail Task 3's precise presentation mismatch diagnostic even if it retains the same package ID and valid hashes. Run each exact import and its ordinary-Python verification gate in order:

```bash
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/plateau-lifting-edge-depth-18mm.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/plateau-lifting-edge-depth-18mm.contact-map.json --package plateau.lifting-edge --board-json Hangboards/plateau-lifting-edge/board.json --asset-stem depth-18mm --output-directory .context/sweet-hamster-batch03-model-packages-plateau-18 --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-18mm.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/plateau-lifting-edge-depth-18mm.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/plateau-lifting-edge-depth-18mm.contact-map.json --package plateau.lifting-edge --asset-stem depth-18mm --output-directory .context/sweet-hamster-batch03-model-packages-plateau-18 --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-18mm.json --repository-root . --expected-source-geometry-changed true
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/plateau-lifting-edge-depth-15mm.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/plateau-lifting-edge-depth-15mm.contact-map.json --package plateau.lifting-edge --board-json Hangboards/plateau-lifting-edge/board.json --asset-stem depth-15mm --output-directory .context/sweet-hamster-batch03-model-packages-plateau-15 --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-15mm.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/plateau-lifting-edge-depth-15mm.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/plateau-lifting-edge-depth-15mm.contact-map.json --package plateau.lifting-edge --asset-stem depth-15mm --output-directory .context/sweet-hamster-batch03-model-packages-plateau-15 --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-15mm.json --repository-root . --expected-source-geometry-changed true
rtk proxy blender --background --python Tools/HangboardModels/import_contact_model_source.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/plateau-lifting-edge-depth-10mm.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/plateau-lifting-edge-depth-10mm.contact-map.json --package plateau.lifting-edge --board-json Hangboards/plateau-lifting-edge/board.json --asset-stem depth-10mm --output-directory .context/sweet-hamster-batch03-model-packages-plateau-10 --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-10mm.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python Tools/HangboardModels/import_contact_model_source.py verify-import --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/manifests/plateau-lifting-edge-depth-10mm.source.json --mapping docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/mappings/plateau-lifting-edge-depth-10mm.contact-map.json --package plateau.lifting-edge --asset-stem depth-10mm --output-directory .context/sweet-hamster-batch03-model-packages-plateau-10 --report docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import/plateau-lifting-edge-depth-10mm.json --repository-root . --expected-source-geometry-changed true
```

The three gate lines must be exactly, in order, `PASS plateau.lifting-edge/depth-18mm verified import output`, `PASS plateau.lifting-edge/depth-15mm verified import output`, and `PASS plateau.lifting-edge/depth-10mm verified import output`, each with status `0`. They recheck the three Task 4 accepted parents and their distinct corrected-source/audit/render/actual-time approval chains, package/presentation stems and paths, exact `edge-18mm→edge-18` mapping, preserved node/material inventories and 15/10 reducer body identities, generated USDZ/descriptor hashes, and `sourceGeometryChanged:true`. Stop after the first failure. Only after all three gates pass may the implementer run this separate promotion/removal block:

```bash
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-plateau-18/assets/depth-18mm.usdz Hangboards/plateau-lifting-edge/assets/depth-18mm.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-plateau-18/assets/depth-18mm.model.json Hangboards/plateau-lifting-edge/assets/depth-18mm.model.json
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-plateau-15/assets/depth-15mm.usdz Hangboards/plateau-lifting-edge/assets/depth-15mm.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-plateau-15/assets/depth-15mm.model.json Hangboards/plateau-lifting-edge/assets/depth-15mm.model.json
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-plateau-10/assets/depth-10mm.usdz Hangboards/plateau-lifting-edge/assets/depth-10mm.usdz
rtk cp -p -- .context/sweet-hamster-batch03-model-packages-plateau-10/assets/depth-10mm.model.json Hangboards/plateau-lifting-edge/assets/depth-10mm.model.json
rtk git rm Hangboards/plateau-lifting-edge/assets/primary.png
```

Promotion and raster removal are forbidden unless all three gates pass in the current run and all three source corrections have matching human approvals. Final acceptance additionally requires Task 14's human review of the exact shipped normal/rear-oblique renders; source approval alone is insufficient.

- [ ] **Step 6: Remove raster, validate, and commit**

Run:

```bash
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch_03_model_packages.py -q -k plateau
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: PASS and exact package files are `board.json` plus six model files. Commit:

```bash
rtk git add Hangboards/plateau-lifting-edge docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/import Tools/HangboardPackages/tests/test_batch_03_model_packages.py
rtk git commit -m "feat: add plateau depth model presentations"
rtk git push
```

Give a fresh reviewer the three package assets/descriptors/import reports, their distinct corrected-source chains and normal/rear-oblique approvals, the six-transition set, three local pose maps, effective-depth maps, and solver lanes. Stop on any missing/mismatched correction or approval, screw/mounting hole, capped cord exit, cross-wiring, or blocker-selection finding.

## Task 14: Cleanly reimport, rebuild, render, and close the model-import audit

**Files:**

- Create: `Tools/HangboardModels/verify_batch_03_models.py`
- Create: `Tools/HangboardModels/test_verify_batch_03_models.py`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/model-import-audit.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/reports/reimport/*.json` (8)
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/renders/{aelith-cyclops-011,frictitious-nug,frictitious-port-a-board,nature-stone-hanger-mini,nature-stone-hanger-mini-karma8a,plateau-lifting-edge-depth-18mm,plateau-lifting-edge-depth-15mm,plateau-lifting-edge-depth-10mm}/normal.png`
- Create: per-position `*-highlight.png` files beneath the corresponding eight render directories, with names exactly equal to that presentation's local position IDs.
- Create: `rear-oblique.png` in each of the three `renders/plateau-lifting-edge-depth-{18,15,10}mm/` directories, plus additional retained views if needed to expose every former mounting-hole area and preserved lower cord exit.
- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/render-review.json`
- Modify: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/README.md`

**Interfaces:**

- Consumes: `verify_batch(manifest_path: Path, repository_root: Path, report_directory: Path, render_directory: Path) -> Mapping[str, object]` and CLI arguments `--manifest`, `--repository-root`, `--report-directory`, and `--render-directory`; the final eight shipped pairs from Tasks 8-13.
- Produces: eight deterministic clean-reimport reports, normal/per-position highlight renders plus three Plateau rear/oblique view sets, and a closed audit tying accepted/corrected/imported/reimported hashes and approvals together.

- [ ] **Step 1: Test the pure audit loader and exact eight-entry inventory**

Define entries keyed by the eight presentation keys from Task 4, with package/presentation IDs, accepted/compiled source paths+hashes, mapping/import/reimport paths+hashes, final asset/descriptor paths+hashes, expected ordered contacts, exact `nodeID -> role/contactID` mapping, and render paths. First diagnostics are respectively `entries[KEY]: unknown keys: FIELD`, `duplicate package/presentation pair: PACKAGE/PRESENTATION`, `entries[KEY].FIELD does not exist`, `entries[KEY].FIELD SHA-256 mismatch`, `entries[KEY].FIELD must be a contained regular non-symlink`, `entries[KEY]: descriptor modelSHA256 mismatch`, `entries[KEY]: incomplete correction chain`, and `entries[KEY]: asset is not declared by presentation`.

```python
EXPECTED_PRESENTATIONS = {
    "aelith-cyclops-011": ("aelith.cyclops-011", "primary"),
    "frictitious-nug": ("frictitious.nug", "primary"),
    "frictitious-port-a-board": ("frictitious.port-a-board", "primary"),
    "nature-stone-hanger-mini": ("nature.stone-hanger-mini", "primary"),
    "nature-stone-hanger-mini-karma8a": ("nature.stone-hanger-mini-karma8a", "primary"),
    "plateau-lifting-edge-depth-18mm": ("plateau.lifting-edge", "depth-18mm"),
    "plateau-lifting-edge-depth-15mm": ("plateau.lifting-edge", "depth-15mm"),
    "plateau-lifting-edge-depth-10mm": ("plateau.lifting-edge", "depth-10mm"),
}
assert {(entry.package_id, entry.presentation_id) for entry in audit.entries} == set(EXPECTED_PRESENTATIONS.values())
```

Require exactly Task 7's five corrected source keys, including all three Plateau entries with `sourceGeometryChanged:true` and their own full Task 4 correction chains. Mutate each Plateau entry to omit/swap its corrected source, audit, source approval, normal/rear-oblique render, or final review binding; reject missing or mismatched artifacts even if counts remain eight entries/five corrections. Render-review approval must bind the exact shipped model/descriptor and every relevant render hash for each presentation, with an actual UTC instant at or after candidate generation and not in the future. An absent verdict for any depth prevents final acceptance.

- [ ] **Step 2: Implement clean shipped-USDZ verification**

For each entry: reset Blender to an empty scene; require zero objects/materials/images; import `repository_root / entry.asset_path`; call `validate_tagged_scene(imported_scene, frozenset(entry.expected_contacts), imported=True)` and `_snapshot_scene(imported_scene, imported_nodes, transform_to_board_frame=False, require_imported_materials=True, require_triangles=True)`; rebuild with `compile_descriptor`; require byte-for-byte JSON equality with `repository_root / entry.descriptor_path`; report model/descriptor hashes, bounds, nodes, contact mappings, and `cleanReimport: true`.

- [ ] **Step 3: Add mapping-specific verification**

Require Port `pinch-body` to have one or more triangles and `outer-pinch-opposition` to be body; require Oak `internal-pull-up-jug` only maps `pull-up-jug`; require Oak `{outer-jug-pinch-upper,outer-pinch-lower}` and KARMA8A `{outer-pinch-upper,outer-pinch-lower}` both map to `pinch-60`; require all three Plateau descriptors expose only `edge-18` and classify reducer nodes as body. One-field mutations fail with `Port pinch-body has no triangles`, `Port bottom band must remain body`, `Oak pull-up-jug node set mismatch`, `BOARD pinch-60 node set mismatch`, or `PLATEAU_KEY reducer must remain body`.

- [ ] **Step 4: Render exact shipped assets without geometry analysis**

Render one neutral normal view and one material-isolated highlight per authored position using the final package pose and descriptor bindings. Rendering may assign materials/camera only; it must not select faces, analyze pixels to infer geometry, crop automatically, generate masks/contours, or alter USDZ. Hash and list every full-frame render in the audit.

For each Plateau shipped USDZ also render rear/oblique views revealing every former screw/mounting-hole area and the lower open cord exits/grooves. Hash-bind these views with the normal views; preserve their full frames. Exact node/material/contact invariants and correction hashes are automated checks, while hole absence and intact cord exits require human inspection. Do not add pixel analysis, automated hole detection, topology inference, or node-name proxies.

- [ ] **Step 5: Run the verifier for all eight pairs**

Run:

```bash
rtk proxy blender --background --python Tools/HangboardModels/verify_batch_03_models.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/model-import-audit.json --repository-root . --report-directory .context/sweet-hamster-batch03-model-packages-verification/reports --render-directory .context/sweet-hamster-batch03-model-packages-verification/renders
```

Expected: eight successful clean reimports, exact descriptor reconstructions, and one report for each key in `EXPECTED_PRESENTATIONS`.

- [ ] **Step 6: Mandatory operator gate — review final shipped bytes**

After all normal/highlight and Plateau rear/oblique files exist, record their shared `candidateGeneratedAt` as an actual RFC3339 UTC instant and leave `render-review.json` unapproved. Review the sets against Task 2 manufacturer evidence. Explicitly inspect all positions, Port narrow-side highlight and lack of bottom-band highlight, Oak internal jug, both complete Nature multi-node pinches, Plateau blocker nonselection in all configurations, cord exits, and reset framing. For each of the three Plateau presentations require an explicit verdict from its normal and rear/oblique views that every screw/mounting hole is removed/capped, the lower cord exits/grooves remain open, and oak edge, black body, applicable reversible blocker, and contact geometry are preserved. Only after explicit inspection, capture the actual current RFC3339 UTC instant and record reviewer/notes plus exact shipped model/descriptor/render hashes for every reviewed presentation; do not prefill/backdate it, and reject an instant before candidate generation or after the validation clock. Missing or mismatched approval for any Plateau depth blocks the gate. A rejection returns to Task 4 for Plateau source corrections, Task 5, 6, or 7 for other source/mapping work, or the owning Task 8-13 for pose/suspension work; never patch the verifier or descriptor by hand. Changed candidates require new generation and approval.

- [ ] **Step 7: Promote approved reports/renders and commit**

Copy the approved owned output into the tracked paths, update hashes in `model-import-audit.json`, rerun the verifier against tracked artifacts, then:

```bash
rtk git add Tools/HangboardModels/verify_batch_03_models.py Tools/HangboardModels/test_verify_batch_03_models.py docs/source-audits/2026-09-20-hangboards-batch-03-model-imports
rtk git commit -m "test: retain batch 03 model reimport review"
rtk git push
```

Give a fresh reviewer the verifier code, mutation diagnostics, eight reports, and full render matrix before Task 15.

## Task 15: Close the cord audit and make production clearance discover every presentation

**Files:**

- Modify: `docs/source-audits/2026-09-13-model-hangboard-cord-audit.json`
- Modify: `docs/source-audits/2026-09-13-model-hangboard-cord-audit.md`
- Modify: `Tools/HangboardModels/production_cord_clearance.swift:17-527`
- Modify: `Tools/HangboardModels/check_production_cord_clearance.rb:9-37`
- Create: `Tools/HangboardModels/test_production_cord_clearance.py`
- Modify: `Tools/HangboardPackages/tests/test_cord_audit.py:26-110`

**Interfaces:**

- Consumes: runtime's canonical snapshot-root allowlist containing both `docs/source-audits/2026-09-13-model-cord-snapshots/` and Task 2's evidence root, plus its per-presentation topology check.
- Produces: six represented package decisions; `discover_suspended_lanes(root: URL) throws -> [SuspendedLane]`; and a clearance tool that reports unique `packageSlug/presentationID/positionID` lanes.

- [ ] **Step 1: Add six exact cord decisions**

Add `aelith.cyclops-011 -> singleCord`; the other five board IDs -> `pairedLeadCord`. Every record uses `decision: represented`, `sourceFact: documentedSuspension`, exact revision identity, at least two distinct Appendix A URLs/paths/hashes, and the actual 2026-09-20 approval. Use AE-1/2/3; NU-1/2/4; PA-1/2/4/5; NS-1/2/4/5; NK-1/2/4/5; PL-1/2/3/6 as relevant. Rulings must state visible topology and explicitly decline hidden routes/bores.

- [ ] **Step 2: Write discovery/single-cord tests before changing the checker**

Use fixture package `fixture.multi` with presentations `depth-a`/position `position-a`/`singleCord` and `depth-b`/position `position-b`/`pairedLeadCord`. Assert `discover_suspended_lanes` returns exactly `[fixture-multi/depth-a/position-a, fixture-multi/depth-b/position-b]`, constructs `BoardModelSingleCordSuspension` then `BoardModelPairedLeadCordSuspension`, and never reads `presentations[0]`. Duplicate pose keys fail `fixture-multi/depth-b/position-b: duplicate clearance lane`; a missing local pose fails `fixture-multi/depth-b: canonical poses do not equal local positions`. A source-text guard rejects a hard-coded Batch 03 slug array or literal expected pose count.

- [ ] **Step 3: Update the production checker**

For each parser-approved package directory in sorted slug order, iterate presentations in authored order; skip only `suspension == nil`; derive local positions by equal `presentationID`; require the pose-key set equals those IDs; append one lane per local position. Dispatch `singleCord` to one attachment plus `SuspensionProfileSolver.solveSingle` and `pairedLeadCord` to ordered left/right attachments plus the paired solver. For each lane, run in order: solve, rest-length, triangle clearance through production `BoardModelView.hasClearance`, self-intersection, open-route terminal, and camera visibility; emit `PASS package/presentation/position` only after all six checks.

- [ ] **Step 4: Run audit and clearance lanes**

Run:

```bash
rtk scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_cord_audit.py Tools/HangboardModels/test_production_cord_clearance.py -q
rtk proxy ruby Tools/HangboardModels/check_production_cord_clearance.rb
```

Expected: audit covers the full model inventory with `{"excluded": 25, "represented": 14}`; every Batch 03 presentation/local pose prints PASS for solving, length, mesh clearance, self-intersection, route termination, and visible framing. Task 17 separately proves cord non-picking and accessibility hiding in the real model scene.

- [ ] **Step 5: Commit the cord boundary**

```bash
rtk git add docs/source-audits/2026-09-13-model-hangboard-cord-audit.json docs/source-audits/2026-09-13-model-hangboard-cord-audit.md Tools/HangboardModels/production_cord_clearance.swift Tools/HangboardModels/check_production_cord_clearance.rb Tools/HangboardModels/test_production_cord_clearance.py Tools/HangboardPackages/tests/test_cord_audit.py
rtk git commit -m "feat: audit batch 03 model suspension"
rtk git push
```

Give a fresh reviewer the six cord records, exact evidence refs/hashes, two-root audit output, discovery fixture, and every production clearance lane.

## Task 16: Stage all eight USDZ assets into six ODR packs

**Files:**

- Modify: `Tools/HangboardPackages/tests/test_board_package_staging.py:311-399,542-620`
- Modify if the regression fails: `scripts/stage-board-packages.py:216-254`
- Modify: `HangTen.xcodeproj/project.pbxproj:9-42,186-218,405-431,780-806`

**Interfaces:**

- Consumes: all declared `PresentationMediaModel.assetPath` values, not one presentation/package.
- Produces: tags `hang-ten-model-aelith-cyclops-011`, `hang-ten-model-frictitious-nug`, `hang-ten-model-frictitious-port-a-board`, `hang-ten-model-nature-stone-hanger-mini`, `hang-ten-model-nature-stone-hanger-mini-karma8a`, and `hang-ten-model-plateau-lifting-edge`; Plateau's one pack contains three USDZ files.

- [ ] **Step 1: Replace single-presentation staging assertions**

Iterate all model presentations and assert this exact Batch 03 ODR map:

```python
EXPECTED_ODR = {
    "hang-ten-model-aelith-cyclops-011": {"aelith-cyclops-011/assets/primary.usdz"},
    "hang-ten-model-frictitious-nug": {"frictitious-nug/assets/primary.usdz"},
    "hang-ten-model-frictitious-port-a-board": {"frictitious-port-a-board/assets/primary.usdz"},
    "hang-ten-model-nature-stone-hanger-mini": {"nature-stone-hanger-mini/assets/primary.usdz"},
    "hang-ten-model-nature-stone-hanger-mini-karma8a": {"nature-stone-hanger-mini-karma8a/assets/primary.usdz"},
    "hang-ten-model-plateau-lifting-edge": {
        "plateau-lifting-edge/assets/depth-18mm.usdz",
        "plateau-lifting-edge/assets/depth-15mm.usdz",
        "plateau-lifting-edge/assets/depth-10mm.usdz",
    },
}
```

For each package, base staging contains `board.json` plus every declared descriptor and no USDZ; its one slug ODR root equals its set above and contains no descriptor; every descriptor's `modelSHA256` matches its corresponding ODR bytes. Assert exactly eight unique USDZ paths and six tags. A missing depth fails `hang-ten-model-plateau-lifting-edge: expected 3 USDZ, found 2`; a base USDZ fails `base package must not contain ODR asset: PATH`; an ODR descriptor fails `ODR pack must contain USDZ only: PATH`.

- [ ] **Step 2: Run staging tests and confirm the precise failure**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py -q`

Expected: FAIL at existing `len(model_presentations) == 1`, `primary.usdz`, and missing project registrations—not because the staging loop lost an asset.

- [ ] **Step 3: Preserve generic staging and register six Xcode ODR folders**

If `stage-board-packages.py` already passes the new generic asset test, leave it unchanged. Add one PBX folder reference/build-file/tag for each exact folder: `$(DERIVED_FILE_DIR)/HangTenModelODR/aelith-cyclops-011/Hangboards`, `$(DERIVED_FILE_DIR)/HangTenModelODR/frictitious-nug/Hangboards`, `$(DERIVED_FILE_DIR)/HangTenModelODR/frictitious-port-a-board/Hangboards`, `$(DERIVED_FILE_DIR)/HangTenModelODR/nature-stone-hanger-mini/Hangboards`, `$(DERIVED_FILE_DIR)/HangTenModelODR/nature-stone-hanger-mini-karma8a/Hangboards`, and `$(DERIVED_FILE_DIR)/HangTenModelODR/plateau-lifting-edge/Hangboards`. Use new unique 24-character IDs, add each reference to the ODR group, and each build file to the app Resources phase. Do not make separate Plateau tags per depth.

- [ ] **Step 4: Run staging/project tests and inspect a staged tree**

Run the full staging test, then run:

```bash
rtk env TARGET_BUILD_DIR=.context/sweet-hamster-batch03-model-packages-staging/Build/Products/Debug-iphonesimulator UNLOCALIZED_RESOURCES_FOLDER_PATH=HangTen.app DERIVED_FILE_DIR=.context/sweet-hamster-batch03-model-packages-staging/DerivedFiles scripts/stage-board-packages.py --repository-root . --destination .context/sweet-hamster-batch03-model-packages-staging/Build/Products/Debug-iphonesimulator/HangTen.app/Hangboards
```

Expected: six Batch 03 base package directories have eight descriptors total and zero USDZ; the six `EXPECTED_ODR` roots have eight USDZ total and zero descriptors; no asset path or byte payload is duplicated across roots.

- [ ] **Step 5: Commit ODR registration**

```bash
rtk git add Tools/HangboardPackages/tests/test_board_package_staging.py scripts/stage-board-packages.py HangTen.xcodeproj/project.pbxproj
rtk git commit -m "build: stage batch 03 model resources"
rtk git push
```

Give a fresh reviewer the staging test, staged tree inventory, six PBX tags/folder references/resource entries, and the eight descriptor-to-ODR hash comparisons. Task 16 is the package plan's ODR-readiness producer for the experience plan.

## Task 17: Prove exact native loading, picking, highlighting, switching, and reset

**Files:**

- Create: `HangTenTests/Batch03BoardModelTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` (test file reference/build phase)
- Create after passing review: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/ios-native-model-acceptance.md`

**Interfaces:**

- Consumes: `BoardCatalog.packageStore`, `BoardModelLoader.load(board:presentation:store:resourceAccess:)`, `BoardModelScene.select(positionID:)`, `.highlight(_:mode:)`, `.contactID(for:)`, `.orbit(azimuth:elevation:zoomScale:)`, `.resetCamera(animated:)`, and the six package contracts.
- Produces: `Batch03ModelCase(boardID:presentationID:positionID:expectedContactNodes:forbiddenNodes:)`, `loadAndAssert(_ case: Batch03ModelCase) async throws`, and native evidence that all eight resources behave as declared. Task 17 is the package plan's native-model acceptance producer; it does not own routine editor/workout UI behavior.

- [ ] **Step 1: Register a focused XCTest file and make it red**

Build cases from the exact 19 `(board,primary,position)` rows in the shared Tasks 8-12 matrix plus `(plateau.lifting-edge,depth-18mm,depth-18mm)`, `(plateau.lifting-edge,depth-15mm,depth-15mm)`, and `(plateau.lifting-edge,depth-10mm,depth-10mm)`. For each, load that exact resource/descriptor, select the local position, assert node set from Tasks 4-7, pick at each node's presentation-space bounds center, clear/reapply highlight, orbit by `(azimuth:0.3,elevation:0.2,zoomScale:1.1)`, reset to the canonical camera, and require transient cord nodes return nil from picking and do not occur in accessibility elements. The first failure identifies `boardID/presentationID/positionID` and exact expected/actual node sets.

- [ ] **Step 2: Add the four semantic regressions**

For Port `pinch-side`, require picking/highlighting `pinch-body` and never `outer-pinch-opposition`. For Oak `front-upright`, require only `internal-pull-up-jug` owns `pull-up-jug`; for both Nature `pinch-side` cases, require the exact two reviewed exterior nodes share `pinch-60` and both receive active material. For all Plateau presentations, require blocker hits return no contact while `edge-18` remains pickable.

- [ ] **Step 3: Test Plateau model switching atomically at the package/model boundary**

Load `depth-18mm → depth-15mm → depth-10mm → depth-18mm` using the position's own presentation. Capture tuple `(modelSHA256,descriptorPath,canonicalPose,cordAttachmentPoints,highlightedNodeIDs,resetCamera)` after each load; require the first three model hashes are pairwise distinct and the final tuple equals the initial tuple. Clear the previous scene before accepting the next. Removing `depth-15mm.usdz` must yield `.unavailable(.missingResource)` with no scene; changing one byte must yield `.unavailable(.hashMismatch)` with no scene. In both mutations assert no prior scene and no raster view remain.

- [ ] **Step 4: Run focused XCTest**

Use `validate-hang-ten-ios` to create and record the owner-named isolated Simulator/DerivedData, then run:

```bash
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/sweet-hamster-batch03-model-packages-native -only-testing:HangTenTests/Batch03BoardModelTests
rtk xcodebuild test-without-building -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=sweet-hamster Batch03,OS=latest' -derivedDataPath .context/sweet-hamster-batch03-model-packages-native -only-testing:HangTenTests/Batch03BoardModelTests
```

Expected: all eight USDZ pairs and all 22 local-position cases pass. If the exact owner-named destination cannot boot, record the native lane as blocked; Python validation is not a substitute.

- [ ] **Step 5: Current-source package/model visual checkpoint**

Use `validate-hang-ten-ios` on the isolated simulator for every board/position and all Plateau depths. This checkpoint covers only model/descriptor/suspension/picking/orbit/reset and unavailable behavior; the companion experience plan owns board-detail/editor/workout/Dynamic-Type/VoiceOver workflow acceptance. Record exact commit, simulator/runtime, package hashes, inspected positions, screenshots, and operator verdict in `ios-native-model-acceptance.md`.

At every Plateau depth, inspect normal and rear/oblique app views to confirm screw/mounting holes remain absent/capped, lower open cord exits/grooves remain intact, and the oak contact, black body, and applicable nonselectable blocker match Task 14's approved shipped renders. Record each depth's explicit verdict and screenshot hashes; missing or failed visual review blocks native acceptance.

- [ ] **Step 6: Commit native package validation**

```bash
rtk git add HangTenTests/Batch03BoardModelTests.swift HangTen.xcodeproj/project.pbxproj docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/ios-native-model-acceptance.md
rtk git commit -m "test: validate batch 03 models natively"
rtk git push
```

Give a fresh reviewer the XCTest cases/results and current-source acceptance record. The companion experience plan's final integration task—not this package task—owns final package-backed Port exact-unmeasured requirement acceptance and legacy routine/history/stale-ID runtime acceptance.

## Task 18: Run the complete audit matrix, hand off runtime acceptance, and clean owned resources

**Files:**

- Create: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/final-package-gate.md`
- Modify only if factual final hashes/results changed: `docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/{README.md,model-import-audit.json,ios-native-model-acceptance.md}`

**Interfaces:**

- Consumes: all prior task outputs and the companion runtime/parser changes.
- Produces: a clean, reproducible final branch with no owned external resources or untracked migration output; package handoff producers are Tasks 8-12 (five independent single-board packages), Task 13 (Plateau package), Task 16 (ODR readiness), and Task 17 (native model acceptance). The experience plan's final integration task owns package-backed Port exact-unmeasured requirement acceptance and legacy routine/history/stale-ID runtime acceptance.

- [ ] **Step 1: Re-run immutable source and model provenance**

Run:

```bash
rtk scripts/hangboard-packages.sh audit-sources --repository-root . --manifest docs/source-audits/2026-09-20-hangboards-batch-03-source-audit.json
rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py Tools/HangboardModels/test_batch_03_source_contract.py Tools/HangboardModels/test_verify_batch_03_models.py -q
rtk proxy blender --background --python Tools/HangboardModels/verify_batch_03_models.py -- --manifest docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/model-import-audit.json --repository-root . --report-directory .context/sweet-hamster-batch03-model-packages-final/reports --render-directory .context/sweet-hamster-batch03-model-packages-final/renders
```

Expected: `{"recordCount":28,"snapshotCount":28,"sourceTiers":{"manufacturer":28}}`, eight accepted source hashes, eight exact shipped model hashes, eight exact descriptor reconstructions, and corrected source-key set exactly `{frictitious-port-a-board,nature-stone-hanger-mini,plateau-lifting-edge-depth-18mm,plateau-lifting-edge-depth-15mm,plateau-lifting-edge-depth-10mm}`. The source contract reports `{"acceptedSources":8,"manifests":8,"mappings":8,"geometryCorrections":5,"mappingReviews":1}`; all three Plateau imports require `sourceGeometryChanged:true`, matching source approvals, and Task 14's normal/rear-oblique shipped-render approvals. Automated verification alone cannot satisfy the human hole-removal verdicts.

- [ ] **Step 2: Re-run package/audit/staging suites**

Run:

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests -q
rtk proxy ruby Tools/HangboardModels/check_production_cord_clearance.rb
```

Expected: PASS; Batch 03 contributes six model-only packages, eight USDZ, no PNG, and no draft/unlisted asset.

- [ ] **Step 3: Run affected native suites and build**

Run the Task 17 isolated `build-for-testing`/`test-without-building` commands with `-only-testing` entries `HangTenTests/Batch03BoardModelTests`, `HangTenTests/BoardModelTests`, and `HangTenTests/SuspendedBoardPresentationTests`. Run the runtime plan's Tasks 1/2/6 focused Swift and Python parser commands, then run `rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/sweet-hamster-batch03-model-packages-final-native CODE_SIGNING_ALLOWED=NO build`. Expected: PASS with the staging phase present in the build log.

- [ ] **Step 4: Audit forbidden content and exact identities**

Run these package-scoped searches; every command must exit `1` with no matches:

```bash
rtk rg -n '"type"\s*:\s*"raster"|contactGeometry|\.png' Hangboards/aelith-cyclops-011 Hangboards/frictitious-nug Hangboards/frictitious-port-a-board Hangboards/nature-stone-hanger-mini Hangboards/nature-stone-hanger-mini-karma8a Hangboards/plateau-lifting-edge
rtk rg -n 'pocket-30-two-finger-mono|blocker-edge-15|blocker-edge-10|stone-hanger-mini-beech|Stone Hanger Mini — Beech' Hangboards/frictitious-port-a-board Hangboards/nature-stone-hanger-mini Hangboards/plateau-lifting-edge docs/source-audits/2026-09-20-hangboards-batch-03-model-imports
rtk rg -n '/Users/|cord.*(mesh|geometry)|knot.*(mesh|geometry)' Hangboards/aelith-cyclops-011 Hangboards/frictitious-nug Hangboards/frictitious-port-a-board Hangboards/nature-stone-hanger-mini Hangboards/nature-stone-hanger-mini-karma8a Hangboards/plateau-lifting-edge
```

Do not apply these migration-only assertions to historical audits outside the Batch 03 paths.

- [ ] **Step 5: Verify worktree and diff integrity**

Run `rtk git diff --check`, `rtk git status --short`, `rtk git ls-files docs/source-audits/2026-09-20-hangboards-batch-03-evidence docs/source-audits/2026-09-20-hangboards-batch-03-model-imports Hangboards/aelith-cyclops-011 Hangboards/frictitious-nug Hangboards/frictitious-port-a-board Hangboards/nature-stone-hanger-mini Hangboards/nature-stone-hanger-mini-karma8a Hangboards/plateau-lifting-edge`, and `rtk git diff --stat`. Expected: no whitespace errors, all required artifacts tracked, and no unrelated modifications.

- [ ] **Step 6: Clean and prove resource deletion**

Trigger the installed exit trap; terminate only PIDs listed in the task `OWNERSHIP.md`, shut down/delete only the recorded `sweet-hamster Batch03` Simulator UDID, and delete the exact owner-named verification/staging/DerivedData directories after promoting approved artifacts. The trap iterates the recorded PID values through `rtk ps -p`, recorded absolute directories through the platform file-existence check, and the recorded UDID through `rtk xcrun simctl list devices`; it exits nonzero if any owned item remains. Preserve `.context/hangboard-packages-venv` as shared repository-local tooling, and leave shared/unknown resources untouched.

- [ ] **Step 7: Record, commit, push, and review the final package gate**

Write `final-package-gate.md` with the exact commit under test; the 28/8/8/6 evidence-source-model-package counts; geometry-change set; Tasks 8-13 package test results; Task 14 reimport/render verdict; Task 15 cord result; Task 16 ODR inventory; Task 17 native result or explicit blocker; forbidden-content result; cleanup inventory; and the experience-plan handoff. Include only factual final hash updates to existing audit files.

```bash
rtk git add docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/final-package-gate.md docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/README.md docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/model-import-audit.json docs/source-audits/2026-09-20-hangboards-batch-03-model-imports/ios-native-model-acceptance.md
rtk git commit -m "docs: close batch 03 model migration audit"
rtk git push
```

A fresh reviewer compares every recorded result with the final command output and confirms the runtime/experience handoff. Task 18 is the final package gate.
