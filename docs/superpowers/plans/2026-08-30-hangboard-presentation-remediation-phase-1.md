# Hangboard Presentation Remediation Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a machine-validated provenance manifest and use fresh live-web evidence to reclassify all 61 hangboard packages and all 85 declared presentation PNGs without changing a PNG or `board.json`.

**Architecture:** A closed-schema JSON manifest records current immutable asset facts, exact-revision web evidence, seven visual findings, a material/form-factor comparator, and one remediation decision for every declared presentation. A standard-library Python domain module cross-checks that ledger against package discovery, PNG dimensions, and SHA-256 hashes; an `audit-presentations` CLI supports both lane-level review and fail-closed full-catalog validation. Phase 1 records only source classification: kept assets may identify their current bytes as accepted, while any presentation needing a Phase 2 mutation must retain empty candidate data, null accepted output, and pending final validation.

**Tech Stack:** Python 3.11.4+ standard library, pytest 9, Pillow test fixtures, existing `hangboard_packages` discovery/CLI, JSON, Markdown, live official manufacturer pages/manuals/catalogues/archives, and live independent retailer/review/owner pages.

**Spec:** `docs/superpowers/specs/2026-08-30-hangboard-presentation-remediation-design.md`

## Global Constraints

- Preserve Hang Ten's simplified, unbranded illustration style; manufacturer and independent photographs are evidence, never shipped assets.
- Revalidate all 61 packages and all 85 declared PNG presentation assets, including assets previously judged compliant.
- Use fresh live-web evidence for every package. Local documentation, current `board.json`, generated output, and model assumptions are not product proof.
- Record direct HTTPS source URLs, publisher, source kind, review date `2026-08-30`, exact revision applicability, image role, and the precise supported claim.
- Require first-party evidence and independent corroboration when available. When a class of source genuinely cannot be found after direct web searching, record the exact searches and a concrete evidence-gap reason; never invent a substitute claim.
- Keep every sourced usable surface, and judge each presentation orthographically head-on to its own working surface.
- Preserve material-specific cues while using the common off-white studio background, centered composition, neutral lighting, restrained contact shadows, clean antialiasing, and cohort-consistent scale required by the spec.
- Use only the decision enum `keep`, `regenerate`, `edit`, `removeUnsupportedPresentation`, or `splitPhysicalRevision`.
- Do not change, regenerate, crop, post-process, or otherwise rewrite any PNG in Phase 1.
- Do not change any `Hangboards/*/board.json` in Phase 1, including presentations, product metadata, or canonical geometry.
- Do not use image-driven hold detection, segmentation, masks, contours, alignment, registration, vectorization, automatic path simplification, automatic cropping, or proposal/refine/promote geometry workflows.
- Every implementation task is executed by a fresh subagent under `superpowers:subagent-driven-development`. After each task, the controller performs the required spec-compliance review and then a separate code/data-quality review before dispatching the next task, as required by `AGENTS.md`.
- Use `rtk` for shell commands. Run package tests with `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest` and inventory validation with `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`.
- Commit and push each completed, reviewed task to the current remote branch. Never combine lanes in one commit.
- Put any transient web notes or captures under `.context/sincere-otter-remediation-phase-1-*`, record `sincere-otter` ownership immediately, install an exit trap for each exact external resource, delete owned resources, and verify deletion. Do not save or commit source photographs during Phase 1.

## File structure

- `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py` owns the closed manifest schema, SHA-256/dimension cross-checks, phase-aware invariants, lane filtering, and deterministic coverage report.
- `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py` owns parser, inventory, evidence, hash/dimension, decision, comparator, and Phase 1 truthfulness tests.
- `Tools/HangboardPackages/src/hangboard_packages/cli.py`, `scripts/hangboard-packages.sh`, `Tools/HangboardPackages/tests/test_cli.py`, and `Tools/HangboardPackages/README.md` expose and document `audit-presentations` without changing existing commands.
- `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json` is the only machine-readable catalog ledger.
- `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md` explains evidence policy, lane completion, conflicts, revision resolutions, unsupported surfaces, and classification totals without duplicating all 85 JSON records.

---

### Task 1: Add the presentation-remediation manifest domain, validator, and CLI

**Files:**
- Create: `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`
- Create: `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `scripts/hangboard-packages.sh`
- Modify: `Tools/HangboardPackages/README.md`

**Interfaces:**
- Consumes: `BoardInventory`, `BoardPackage`, and `BoardPresentation` from `hangboard_packages.board_catalog`; a manifest JSON path; the `Hangboards` root; and an optional exact set of board IDs for lane validation.
- Produces: `PresentationRemediationAuditError(ValueError)`, `load_presentation_remediation_manifest(path: Path) -> PresentationRemediationManifest`, and `validate_presentation_remediation_manifest(manifest: PresentationRemediationManifest, inventory: BoardInventory, *, hangboards_root: Path, selected_package_ids: frozenset[str] = frozenset()) -> PresentationRemediationReport`.
- `PresentationRemediationReport.to_json() -> dict[str, object]` returns sorted `packageIDs`, integer `packageCount`, integer `presentationCount`, decision counts under `decisions`, and sorted `evidenceBlockedAssets`.
- CLI: `scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json [--package-id BOARD_ID ...]` prints sorted JSON and returns `1` with one `error:` line for malformed or incomplete data.

The manifest root is a closed object with exactly these keys:

```json
{
  "schemaVersion": 1,
  "phase": "sourceReclassification",
  "reviewDate": "2026-08-30",
  "packageIDs": [],
  "records": [],
  "phase1Checks": {
    "manifestValidation": {"status": "pending", "command": null},
    "packageValidation": {"status": "pending", "command": null},
    "packageTestSuite": {"status": "pending", "command": null},
    "hangboardsDiff": {"status": "pending", "command": null}
  }
}
```

Every presentation record is a closed object with these exact fields and nested names:

```json
{
  "packageID": "fixture.board",
  "productName": "Fixture Board",
  "presentationID": "front",
  "assetPath": "Hangboards/fixture-board/assets/primary.png",
  "workingSurface": "Published front working face",
  "physicalRevision": "Revision named by the cited first-party page",
  "manufacturer": "Fixture Maker",
  "materials": ["wood"],
  "formFactor": "fullWidthFixedBoard",
  "currentAsset": {
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "widthPixels": 1200,
    "heightPixels": 600
  },
  "decision": "keep",
  "findings": {
    "productLikeness": {"outcome": "conforms", "explanation": "The cited views establish the same silhouette and contact layout."},
    "material": {"outcome": "conforms", "explanation": "The cited specification and real-world view establish wood."},
    "topology": {"outcome": "conforms", "explanation": "All published contacts and identity-bearing parts are represented."},
    "headOnPerspective": {"outcome": "conforms", "explanation": "The working face is orthographic rather than foreshortened."},
    "smoothing": {"outcome": "conforms", "explanation": "Transitions follow the material-specific restrained studio treatment."},
    "framing": {"outcome": "conforms", "explanation": "The complete product is centered and uncropped at cohort-consistent scale."},
    "crossCatalogConsistency": {"outcome": "conforms", "explanation": "Lighting, background, texture frequency, and edge treatment match the selected baseline."}
  },
  "evidence": {
    "official": [{
      "url": "https://manufacturer.example/fixture-board",
      "publisher": "Fixture Maker",
      "sourceKind": "officialProductPage",
      "reviewedAt": "2026-08-30",
      "revisionApplicability": "Exact named revision",
      "imageRole": "Straight-on view establishes silhouette and contact layout; oblique gallery view establishes material and depth transitions.",
      "supportedClaim": "The exact revision is a wood fixed board with the shown front working face."
    }],
    "independent": [{
      "url": "https://retailer.example/fixture-board",
      "publisher": "Independent Retailer",
      "sourceKind": "retailer",
      "reviewedAt": "2026-08-30",
      "revisionApplicability": "Exact named revision",
      "imageRole": "Real-world oblique product view corroborates finish and construction.",
      "supportedClaim": "The production finish and component inventory match the official revision."
    }],
    "officialEvidenceGap": null,
    "independentEvidenceGap": null
  },
  "comparator": {
    "assetPath": "Hangboards/accepted-wood-baseline/assets/primary.png",
    "materialMatch": "Warm diffuse wood with bounded face-grain detail",
    "formFactorMatch": "Full-width fixed board",
    "reason": "The baseline governs framing, neutral lighting, texture frequency, and edge treatment only.",
    "baselineGap": null
  },
  "generation": {
    "prompt": null,
    "sourceImages": [],
    "currentAssetRole": null,
    "candidates": []
  },
  "final": {
    "acceptedAssetSHA256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "finalDimensions": {"widthPixels": 1200, "heightPixels": 600},
    "visualReviewerDecision": "acceptedCurrentAsset",
    "workbenchReview": {
      "normal": {"status": "pending", "evidence": null},
      "allActive": {"status": "pending", "evidence": null},
      "individualHolds": {"status": "pending", "evidence": null}
    },
    "validation": {
      "packageValidation": {"status": "pending", "evidence": null},
      "focusedTests": {"status": "pending", "evidence": null},
      "fullPackageSuite": {"status": "pending", "evidence": null},
      "buildForTesting": {"status": "pending", "evidence": null},
      "simulatorReview": {"status": "pending", "evidence": null}
    }
  }
}
```

Schema rules are exact:

- `materials` is a nonempty unique array whose values are from `wood`, `moldedPlastic`, `resin`, `urethane`, `metal`, `stoneMineralComposite`, `ropeCord`, or `mixedOther`.
- `formFactor` is one of `fullWidthFixedBoard`, `splitFixedBoard`, `compactFixedBoard`, `liftingEdge`, `suspendedPortable`, `reversiblePortable`, or `multiOrientationDevice`.
- Every finding key shown above is required exactly once. `outcome` is `conforms`, `nonconforming`, `uncertain`, or `notApplicable`, and `explanation` is nonempty and evidence-specific.
- Official source kinds are `officialProductPage`, `officialManual`, `officialCatalog`, `archivedFirstParty`, and `officialImage`; independent source kinds are `retailer`, `review`, and `ownerPhoto`. URLs must be direct HTTPS pages, not search-result URLs. Each evidence array must be nonempty or its paired evidence-gap field must be a nonempty account of the exact searches and missing proof, never both.
- `comparator` supports exactly one of two closed modes. Ready-baseline mode requires nonempty `assetPath`, `materialMatch`, `formFactorMatch`, and `reason`, plus null `baselineGap`; the path must identify another ready accepted `keep` record in this manifest, or the same record only when the reason explicitly names it as the accepted cohort baseline. Gap mode requires null `assetPath`, `materialMatch`, `formFactorMatch`, and `reason`, plus a nonempty `baselineGap` explaining why no current accepted comparator exists for the material/form-factor cohort. Gap mode is allowed only for an evidence-blocked `keep` or a Phase 2 decision (`regenerate`, `edit`, `removeUnsupportedPresentation`, or `splitPhysicalRevision`), never for an accepted `keep`. A ready comparator must match at least one declared material and have a compatible form factor; its reason may govern style but must not claim geometry evidence.
- For `keep`, `generation.prompt` and `generation.currentAssetRole` are null and `generation.sourceImages` and `generation.candidates` are empty. A source-supported accepted keep sets `final.acceptedAssetSHA256` equal to `currentAsset.sha256`, copies the current dimensions, and uses `acceptedCurrentAsset`. An evidence-blocked keep instead has at least one `uncertain` finding, null accepted hash/dimensions, and `visualReviewerDecision: "blockedEvidence"`.
- For `regenerate`, `edit`, `removeUnsupportedPresentation`, and `splitPhysicalRevision`, all generation arrays remain empty in Phase 1, the prompt/current-asset role remain null, the accepted hash/dimensions remain null, the reviewer decision is `pendingPhase2`, and all per-presentation Workbench/validation statuses remain `pending`. This is the invariant that prevents Phase 1 from claiming a generated output or final validation that does not exist.
- `removeUnsupportedPresentation` requires sourced findings showing that the declared surface is not usable. `splitPhysicalRevision` requires conflicting sources tied to two named physical revisions. Neither changes package inventory in Phase 1.
- `phase1Checks` reports only ledger/tool verification and never counts as final per-presentation validation.

- [ ] **Step 1: Write failing domain tests before production code.**

  Use `write_board_package` and `write_multi_presentation_board_package` from `tests/conftest.py`. Write `_record(boards: Path, package_slug: str, package_id: str, presentation_id: str, asset_path: str) -> dict[str, object]` to emit the exact closed structure above with hashes and dimensions read from the fixture asset. Add `_single_board_fixture(tmp_path: Path) -> tuple[Path, BoardInventory, dict[str, object]]` and `_validate_document(tmp_path: Path, boards: Path, inventory: BoardInventory, records: list[dict[str, object]]) -> PresentationRemediationReport` so every mutation test goes through the public loader and validator. Add tests for exact inventory coverage, duplicate/unknown/missing presentation keys, package ID and product-name mismatch, direct asset-path mismatch, SHA-256 mismatch, width/height mismatch, invalid decision, missing finding, invalid evidence kind/HTTP/search URL, missing official and independent evidence without a gap, comparator not present/not kept/material-incompatible, comparator fields mixed across ready/gap modes, an accepted keep attempting gap mode, a Phase 2 repair validly using gap mode, nonempty keep generation arrays, keep accepted-hash mismatch, repair accepted-hash claim, and repair validation status other than pending.

  ```python
  def test_manifest_inventory_must_equal_every_declared_presentation(tmp_path: Path) -> None:
      boards = tmp_path / "Hangboards"
      write_multi_presentation_board_package(boards / "fixture-board")
      inventory = discover_board_packages(boards, require_complete_inventory=True)
      document = _manifest(package_ids=["fixture.board"], records=[
          _record(boards, "fixture-board", "fixture.board", "front", "assets/primary.png")
      ])
      manifest_path = _write_manifest(tmp_path, document)

      with pytest.raises(
          PresentationRemediationAuditError,
          match=r"missing presentation record: fixture\.board/back",
      ):
          validate_presentation_remediation_manifest(
              load_presentation_remediation_manifest(manifest_path),
              inventory,
              hangboards_root=boards,
          )


  def test_repair_record_cannot_claim_phase_2_output_or_validation(tmp_path: Path) -> None:
      boards, inventory, record = _single_board_fixture(tmp_path)
      record["decision"] = "regenerate"
      record["final"]["acceptedAssetSHA256"] = record["currentAsset"]["sha256"]
      record["final"]["finalDimensions"] = {
          "widthPixels": record["currentAsset"]["widthPixels"],
          "heightPixels": record["currentAsset"]["heightPixels"],
      }
      record["final"]["visualReviewerDecision"] = "acceptedCurrentAsset"
      record["final"]["validation"]["packageValidation"] = {
          "status": "passed", "evidence": "fixture"
      }

      with pytest.raises(
          PresentationRemediationAuditError,
          match="regenerate must not claim accepted output or final validation in Phase 1",
      ):
          _validate_document(tmp_path, boards, inventory, [record])


  def test_accepted_keep_cannot_claim_a_comparator_baseline_gap(tmp_path: Path) -> None:
      boards, inventory, record = _single_board_fixture(tmp_path)
      record["comparator"] = {
          "assetPath": None,
          "materialMatch": None,
          "formFactorMatch": None,
          "reason": None,
          "baselineGap": "No accepted metal portable baseline exists in the current catalog.",
      }

      with pytest.raises(
          PresentationRemediationAuditError,
          match="accepted keep requires a ready comparator",
      ):
          _validate_document(tmp_path, boards, inventory, [record])


  def test_phase_2_repair_may_record_an_exact_comparator_gap(tmp_path: Path) -> None:
      boards, inventory, record = _single_board_fixture(tmp_path)
      record["decision"] = "regenerate"
      record["findings"]["productLikeness"] = {
          "outcome": "nonconforming",
          "explanation": "The cited views establish a different silhouette.",
      }
      record["comparator"] = {
          "assetPath": None,
          "materialMatch": None,
          "formFactorMatch": None,
          "reason": None,
          "baselineGap": "Every current metal portable asset needs Phase 2 repair, so none is an accepted baseline.",
      }
      record["final"]["acceptedAssetSHA256"] = None
      record["final"]["finalDimensions"] = None
      record["final"]["visualReviewerDecision"] = "pendingPhase2"

      report = _validate_document(tmp_path, boards, inventory, [record])

      assert report.to_json()["decisions"] == {"regenerate": 1}
  ```

- [ ] **Step 2: Write failing CLI tests.**

  Extend `_run_cli` coverage with one full fixture and a two-presentation fixture validated through `--package-id`. Assert deterministic JSON on success and the domain error's first line on failure.

  ```python
  result = _run_cli(
      "audit-presentations",
      "--root", str(boards),
      "--manifest", str(manifest),
      "--package-id", "fixture.board",
  )

  assert result.returncode == 0, result.stderr
  assert _json_output(result.stdout) == {
      "decisions": {"keep": 2},
      "evidenceBlockedAssets": [],
      "packageCount": 1,
      "packageIDs": ["fixture.board"],
      "presentationCount": 2,
  }
  ```

- [ ] **Step 3: Run focused tests and verify RED.**

  Run:

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py -k 'presentation_remediation or audit_presentations'
  ```

  Expected: FAIL during collection because `hangboard_packages.presentation_remediation_audit` and the `audit-presentations` command do not exist.

- [ ] **Step 4: Implement the closed parser and fail-closed validator.**

  Use frozen dataclasses for the manifest, source, finding, comparator, current asset, final state, and report. Reuse the strict helper style in `metadata_audit.py`: reject unknown and missing keys; reject booleans as integers; parse `2026-08-30` with `date.fromisoformat`; use `urlsplit` for HTTPS validation; preserve manifest ordering only for diagnostics and sort report output.

  Build the inventory comparison from the real package objects, not directory guesses:

  ```python
  expected = {
      (package.board.id, presentation.id): (
          package,
          presentation,
          (
              Path(hangboards_root).name
              + "/"
              + package.root.name
              + "/"
              + presentation.asset_path
          ),
      )
      for package in inventory.packages
      for presentation in package.board.presentations
  }
  actual = {(record.package_id, record.presentation_id): record for record in manifest.records}
  if len(actual) != len(manifest.records):
      raise PresentationRemediationAuditError("duplicate presentation record")
  ```

  Read hashes and dimensions from the current bytes. Package discovery has already validated PNG structure, but dimensions still come from the PNG IHDR rather than Pillow:

  ```python
  def _current_png_facts(path: Path) -> tuple[str, int, int]:
      data = path.read_bytes()
      if data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
          raise PresentationRemediationAuditError(f"asset is not a PNG: {path}")
      width, height = struct.unpack(">II", data[16:24])
      return hashlib.sha256(data).hexdigest(), width, height
  ```

  A nonempty `selected_package_ids` filters only the required record-coverage and returned counts; the root `packageIDs` must still exactly equal all inventory board IDs, all present records must still name real assets, and every selected board must exist. This lets three independently committed lanes pass without weakening final full-catalog validation.

- [ ] **Step 5: Add the CLI and wrapper command without changing existing command behavior.**

  Add an `audit-presentations` subparser with required `--root` and `--manifest`, plus repeatable `--package-id` using `action="append"`, `default=[]`. Discover with `require_complete_inventory=True`, load/validate, and print `json.dumps(report.to_json(), indent=2, sort_keys=True)`. Add the command to the wrapper's usage and allowlist and document the complete invocation and lane-filter semantics in the README.

- [ ] **Step 6: Run focused tests and verify GREEN.**

  Run:

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py
  ```

  Expected: PASS, including all phase-truthfulness, exact-inventory, hash/dimension, source, comparator, and CLI tests.

- [ ] **Step 7: Commit and push the validator slice.**

  ```bash
  rtk git add \
    Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/src/hangboard_packages/cli.py \
    Tools/HangboardPackages/tests/test_cli.py \
    scripts/hangboard-packages.sh \
    Tools/HangboardPackages/README.md
  rtk git commit -m "Add presentation remediation manifest validator"
  rtk git push
  ```

---

### Task 2: Create the complete inventory skeleton and source-audit narrative

**Files:**
- Create: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Create: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the validator from Task 1 and the current `discover_board_packages(Hangboards, require_complete_inventory=True)` inventory.
- Produces: a valid JSON root with all 61 sorted board IDs in `packageIDs`, empty `records` ready for lane commits, pending `phase1Checks`, and a narrative defining evidence/decision/conflict reporting. Lane tasks append only their exact records.

- [ ] **Step 1: Generate the exact package-ID inventory from package discovery and verify the count.**

  Run the existing status command and inspect IDs from its JSON; do not hand-infer IDs from directory names:

  ```bash
  rtk scripts/hangboard-packages.sh status --root Hangboards --final-inventory
  ```

  Expected: 61 boards and no drafts. The sorted `packageIDs` array in the manifest must contain exactly:

  ```json
  [
    "aelith.cyclops-011",
    "beastmaker-1000",
    "beastmaker-2000",
    "captain-fingerfood.dual",
    "captain-fingerfood.pocket",
    "captain-fingerfood.unlevel",
    "crimptonite.helium-mobile",
    "dewoodstok-woodbord",
    "escape-beta-22",
    "escape.unlimited",
    "evolv-kilter-basic-long",
    "frictitious.doormount-pro-7",
    "frictitious.megalith",
    "frictitious.nug",
    "frictitious.port-a-board",
    "lattice-triple-rung",
    "lattice.mini-bar",
    "lattice.mxedge-lift-large",
    "lattice.mxedge-lift-small",
    "mammut.diamond-finger",
    "metolius.climbers-edge",
    "metolius.contact",
    "metolius.foundry",
    "metolius.light-rail-2",
    "metolius.prime-rib",
    "metolius.project",
    "metolius.rock-rings-3d",
    "metolius.simulator-3d",
    "metolius.wood-grips-compact-ii",
    "metolius.wood-grips-deluxe-ii",
    "moon.armstrong",
    "nature.stoak-board-iii",
    "nature.stone-hanger-mini-karma8a",
    "nature.stone-hanger-mini",
    "owl-climb.poker",
    "plateau.lifting-edge",
    "soill.iron-palm-2",
    "soill.split-palm",
    "soill.training-tiles",
    "target10a.linebreaker-base",
    "tension.flash-board",
    "tension.grindstone-original",
    "tension.grindstone-pro",
    "tension.grindstone",
    "tension.honestone",
    "tension.whetstone",
    "the-hangboard.the-hangboard",
    "trango.rock-prodigy-forge",
    "trango.rock-prodigy-natural",
    "trango.rock-prodigy-pivot",
    "trango.rock-prodigy-training-center",
    "yy.baguette-evo",
    "yy.baguette",
    "yy.penta-evo",
    "yy.travelboard",
    "yy.verticalboard-evo",
    "yy.verticalboard-first",
    "yy.verticalboard-light",
    "yy.verticalboard-one",
    "zlagboard.evo",
    "zlagboard.pro"
  ]
  ```

- [ ] **Step 2: Create the machine-readable skeleton without fake research records.**

  Write the exact Task 1 root object with the 61 IDs above, `records: []`, and all four `phase1Checks` pending. Do not seed record fields with guessed materials, revisions, decisions, evidence-gap claims, or current-package text; the lane agents create a record only after opening live sources.

- [ ] **Step 3: Create the narrative header and operating sections.**

  The Markdown file must contain these concrete sections:

  ```markdown
  # Hangboard Presentation Remediation Phase 1 Source Audit

  ## Scope and result contract
  This audit covers the 61 current packages and 85 declared presentation PNGs. Phase 1 records live-web evidence and a remediation decision only; it changes no PNG and no board.json.

  ## Evidence method
  Search each exact manufacturer/product/revision independently. Open and cite direct official and independent HTTPS pages, inspect straight-on and oblique published pictures, and record only claims those pages establish. Local documentation and current package metadata are navigation aids, not evidence.

  ## Decision legend
  - `keep`: current bytes conform, or remain explicitly evidence-blocked without a final acceptance claim.
  - `edit`: verified topology is suitable for a bounded Phase 2 material, perspective, or treatment correction.
  - `regenerate`: verified silhouette, revision, or working-surface topology requires a new Phase 2 render.
  - `removeUnsupportedPresentation`: sources establish that a declared presentation is not a usable surface; removal waits for Phase 2.
  - `splitPhysicalRevision`: sources establish distinct physical revisions that cannot truthfully share one package; splitting waits for Phase 2.

  ## Lane completion
  | Lane | Packages | Assets | Status |
  | --- | ---: | ---: | --- |
  | A — Aelith through Mammut | 20 | 27 | Not started |
  | B — Metolius through So iLL | 19 | 24 | Not started |
  | C — target10a through Zlagboard | 22 | 34 | Not started |

  ## Revision, source-conflict, and unsupported-surface resolutions
  Resolutions are added only when direct live sources establish the named revisions or surface use.

  ## Final classification totals
  Totals are written from the validated manifest report after all three lanes reconcile.
  ```

- [ ] **Step 4: Verify parseability and the honest expected coverage failure.**

  Run:

  ```bash
  rtk python3 -m json.tool \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  ```

  Expected: JSON formatting succeeds; the validator returns `1` with `error: missing presentation record:` because no live-web lane has been researched yet. This failure is intentional and must not be weakened with fabricated skeleton records.

- [ ] **Step 5: Commit and push the inventory skeleton.**

  ```bash
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Create presentation remediation source ledger"
  rtk git push
  ```

---

### Task 3: Live-web reclassification lane A — Aelith through Mammut

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the Task 1 record schema and validator, plus fresh direct official and independent web pages opened during this task.
- Produces: complete source/material/revision/working-surface/finding/comparator/decision records for exactly 20 packages and 27 assets; no record from lanes B or C.

The exact lane is:

- `aelith-cyclops-011` (`aelith.cyclops-011`): `primary` → `assets/primary.png`
- `beastmaker-1000` (`beastmaker-1000`): `primary` → `assets/primary.png`
- `beastmaker-2000` (`beastmaker-2000`): `primary` → `assets/primary.png`
- `captain-fingerfood-dual` (`captain-fingerfood.dual`): `primary` → `assets/primary.png`; `reverse` → `assets/reverse.png`
- `captain-fingerfood-pocket` (`captain-fingerfood.pocket`): `primary` → `assets/primary.png`
- `captain-fingerfood-unlevel` (`captain-fingerfood.unlevel`): `primary` → `assets/primary.png`; `reverse` → `assets/reverse.png`
- `crimptonite-helium-mobile` (`crimptonite.helium-mobile`): `primary` → `assets/primary.png`; `reverse` → `assets/reverse.png`
- `dewoodstok-woodbord` (`dewoodstok-woodbord`): `primary` → `assets/primary.png`
- `escape-beta-22` (`escape-beta-22`): `primary` → `assets/primary.png`
- `escape-unlimited` (`escape.unlimited`): `primary` → `assets/primary.png`
- `evolv-kilter-basic-long` (`evolv-kilter-basic-long`): `primary` → `assets/primary.png`
- `frictitious-doormount-pro-7` (`frictitious.doormount-pro-7`): `primary` → `assets/primary.png`
- `frictitious-megalith` (`frictitious.megalith`): `primary` → `assets/primary.png`
- `frictitious-nug` (`frictitious.nug`): `primary` → `assets/primary.png`; `reverse` → `assets/reverse.png`
- `frictitious-port-a-board` (`frictitious.port-a-board`): `primary` → `assets/primary.png`; `back` → `assets/back.png`; `side` → `assets/side.png`
- `lattice-triple-rung` (`lattice-triple-rung`): `primary` → `assets/primary.png`
- `lattice-mini-bar` (`lattice.mini-bar`): `primary` → `assets/primary.png`; `end` → `assets/end.png`
- `lattice-mxedge-lift-large` (`lattice.mxedge-lift-large`): `primary` → `assets/primary.png`
- `lattice-mxedge-lift-small` (`lattice.mxedge-lift-small`): `primary` → `assets/primary.png`
- `mammut-diamond-finger` (`mammut.diamond-finger`): `primary` → `assets/primary.png`

- [ ] **Step 1: Search and open live evidence for every exact product and revision.**

  For each of the 20 entries, issue a fresh web search for the exact manufacturer plus product name, then separate searches for `official`, `manual` or `catalog`, and `review`, `retailer`, or `owner`. Open the direct pages. Inspect at least one first-party straight-on or hold-layout view, one first-party oblique/material view, and one independent real-world view when available. For discontinued items, search the manufacturer domain and a web archive for the exact revision before recording an official evidence gap. Do not cite search-result pages or reuse claims from local source-audit Markdown.

- [ ] **Step 2: Write all 27 records from the opened sources.**

  For each presentation, compute `currentAsset` from its untouched file, identify its working surface independently, and enter every Task 1 record field. A multi-surface product gets presentation-specific findings and evidence roles: a source proving the front does not automatically prove the reverse, side, back, or end is usable. Record component materials separately in `materials`; do not flatten sourced ropes, fasteners, pins, or plates into the main body material. Use `uncertain` plus an exact evidence-gap account where a detail remains unproved.

- [ ] **Step 3: Select only evidence-qualified catalog comparators and finalize decisions.**

  Compare wood to a ready wood/form-factor keep, molded resin/plastic/urethane to a ready manufactured-surface keep, metal to a ready metal/form-factor keep, and portable/multi-surface equipment to a ready compatible keep. The reason must name composition, lighting, texture frequency, and edge treatment, while stating that the comparator supplies no product geometry. If lane A contains no accepted keep for a material/form-factor cohort, use the exact comparator gap mode only on an evidence-blocked keep or Phase 2 repair record; do not force an accepted keep or point at a noncompliant asset. Use `edit` only for a bounded correction that preserves verified topology; use `regenerate` when silhouette/topology/revision is wrong; reserve removal or split decisions for direct source proof.

- [ ] **Step 4: Validate lane A and update its narrative status.**

  Run the exact filtered command:

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --package-id aelith.cyclops-011 \
    --package-id beastmaker-1000 \
    --package-id beastmaker-2000 \
    --package-id captain-fingerfood.dual \
    --package-id captain-fingerfood.pocket \
    --package-id captain-fingerfood.unlevel \
    --package-id crimptonite.helium-mobile \
    --package-id dewoodstok-woodbord \
    --package-id escape-beta-22 \
    --package-id escape.unlimited \
    --package-id evolv-kilter-basic-long \
    --package-id frictitious.doormount-pro-7 \
    --package-id frictitious.megalith \
    --package-id frictitious.nug \
    --package-id frictitious.port-a-board \
    --package-id lattice-triple-rung \
    --package-id lattice.mini-bar \
    --package-id lattice.mxedge-lift-large \
    --package-id lattice.mxedge-lift-small \
    --package-id mammut.diamond-finger
  ```

  Expected: PASS with `packageCount: 20` and `presentationCount: 27`. Change only lane A's narrative status to `Complete — 20 packages / 27 assets`; record any exact revision conflict or evidence-blocked presentation under the resolution section.

- [ ] **Step 5: Confirm Phase 1 changed no package input, then commit and push.**

  ```bash
  rtk git diff --name-only -- Hangboards
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Reclassify presentation assets in lane A"
  rtk git push
  ```

  Expected: the diff command prints nothing before the commit.

---

### Task 4: Live-web reclassification lane B — Metolius through So iLL

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the Task 1 record schema and validator, plus fresh direct official and independent web pages opened during this task.
- Produces: complete source/material/revision/working-surface/finding/comparator/decision records for exactly 19 packages and 24 assets; lane A records remain unchanged except a comparator reference may point to an accepted lane B baseline after Task 6 reconciliation.

The exact lane is:

- `metolius-climbers-edge` (`metolius.climbers-edge`): `primary` → `assets/primary.png`
- `metolius-contact` (`metolius.contact`): `primary` → `assets/primary.png`
- `metolius-foundry` (`metolius.foundry`): `front` → `assets/primary.png`
- `metolius-light-rail-2` (`metolius.light-rail-2`): `20mm-side` → `assets/primary.png`; `15mm-side` → `assets/15mm-surface.png`
- `metolius-prime-rib` (`metolius.prime-rib`): `front` → `assets/primary.png`
- `metolius-project` (`metolius.project`): `primary` → `assets/primary.png`
- `metolius-rock-rings-3d` (`metolius.rock-rings-3d`): `front-pair` → `assets/primary.png`
- `metolius-simulator-3d` (`metolius.simulator-3d`): `primary` → `assets/primary.png`
- `metolius-wood-grips-compact-ii` (`metolius.wood-grips-compact-ii`): `primary` → `assets/primary.png`
- `metolius-wood-grips-deluxe-ii` (`metolius.wood-grips-deluxe-ii`): `front` → `assets/primary.png`
- `moon-armstrong` (`moon.armstrong`): `primary` → `assets/primary.png`
- `nature-stoak-board-iii` (`nature.stoak-board-iii`): `primary` → `assets/primary.png`
- `nature-stone-hanger-mini-karma8a` (`nature.stone-hanger-mini-karma8a`): `primary` → `assets/primary.png`
- `nature-stone-hanger-mini` (`nature.stone-hanger-mini`): `primary` → `assets/primary.png`; `side` → `assets/side.png`
- `owl-climb-poker` (`owl-climb.poker`): `face-a` → `assets/face-a.png`; `face-b` → `assets/face-b.png`; `face-c` → `assets/face-c.png`; `face-d` → `assets/face-d.png`
- `plateau-lifting-edge` (`plateau.lifting-edge`): `primary` → `assets/primary.png`
- `soill-iron-palm-2` (`soill.iron-palm-2`): `primary` → `assets/primary.png`
- `soill-split-palm` (`soill.split-palm`): `primary` → `assets/primary.png`
- `soill-training-tiles` (`soill.training-tiles`): `primary` → `assets/primary.png`

- [ ] **Step 1: Search and open live evidence for every exact product and revision.**

  Search each of the 19 exact products independently, including version suffixes such as `3D`, `II`, `2.0`, and the named collaboration edition. Open direct manufacturer product/manual/catalog pages and direct independent retailer/review/owner pages. Inspect straight-on imagery for silhouette/contact layout, oblique imagery for depth/material, and multi-face imagery for every declared side or face. Search historical first-party catalogues or archived manufacturer pages before declaring a discontinued model's evidence unavailable.

- [ ] **Step 2: Write all 24 records from the opened sources.**

  Enter the full closed schema for each asset and current byte facts from disk. Keep Metolius material variants and exact named revisions separate; do not let a current product page silently prove an older `II`, `3-D`, or Foundry revision. Treat Nature stone/mineral products as their sourced composite rather than wood or molded plastic. For the Poker, prove and classify each of four working faces independently. Every unavailable independent or official class needs its own exact search account.

- [ ] **Step 3: Select qualified comparators and make evidence-specific decisions.**

  Prefer a ready keep in the same material and form-factor cohort. If none exists among the records available so far, use comparator gap mode only for an evidence-blocked keep or Phase 2 repair decision and describe the missing accepted cohort; an accepted keep still requires a ready comparator. Mixed or mineral products retain their identity-bearing finish instead of borrowing another cohort's texture. Apply the strict orthographic test to each Light Rail side, Stone Hanger side, and Poker face. Record all seven findings even when one failure already determines a repair decision.

- [ ] **Step 4: Validate lane B and update its narrative status.**

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --package-id metolius.climbers-edge \
    --package-id metolius.contact \
    --package-id metolius.foundry \
    --package-id metolius.light-rail-2 \
    --package-id metolius.prime-rib \
    --package-id metolius.project \
    --package-id metolius.rock-rings-3d \
    --package-id metolius.simulator-3d \
    --package-id metolius.wood-grips-compact-ii \
    --package-id metolius.wood-grips-deluxe-ii \
    --package-id moon.armstrong \
    --package-id nature.stoak-board-iii \
    --package-id nature.stone-hanger-mini-karma8a \
    --package-id nature.stone-hanger-mini \
    --package-id owl-climb.poker \
    --package-id plateau.lifting-edge \
    --package-id soill.iron-palm-2 \
    --package-id soill.split-palm \
    --package-id soill.training-tiles
  ```

  Expected: PASS with `packageCount: 19` and `presentationCount: 24`. Change only lane B's narrative status to `Complete — 19 packages / 24 assets`; add exact revision/source conflicts to the resolution section.

- [ ] **Step 5: Confirm no package input changed, then commit and push.**

  ```bash
  rtk git diff --name-only -- Hangboards
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Reclassify presentation assets in lane B"
  rtk git push
  ```

  Expected: the diff command prints nothing before the commit.

---

### Task 5: Live-web reclassification lane C — target10a through Zlagboard

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the Task 1 record schema and validator, plus fresh direct official and independent web pages opened during this task.
- Produces: complete source/material/revision/working-surface/finding/comparator/decision records for exactly 22 packages and 34 assets.

The exact lane is:

- `target10a-linebreaker-base` (`target10a.linebreaker-base`): `primary` → `assets/primary.png`
- `tension-flash-board` (`tension.flash-board`): `three-edge-upright` → `assets/primary.png`; `three-edge-inverted` → `assets/three-edge-inverted.png`; `two-edge-upright` → `assets/two-edge-surface.png`; `two-edge-inverted` → `assets/two-edge-inverted.png`
- `tension-grindstone-original` (`tension.grindstone-original`): `primary` → `assets/primary.png`
- `tension-grindstone-pro` (`tension.grindstone-pro`): `primary` → `assets/primary.png`
- `tension-grindstone` (`tension.grindstone`): `primary` → `assets/primary.png`
- `tension-honestone` (`tension.honestone`): `primary` → `assets/primary.png`
- `tension-whetstone` (`tension.whetstone`): `primary` → `assets/primary.png`
- `the-hangboard` (`the-hangboard.the-hangboard`): `front` → `assets/primary.png`
- `trango-rock-prodigy-forge` (`trango.rock-prodigy-forge`): `primary` → `assets/primary.png`
- `trango-rock-prodigy-natural` (`trango.rock-prodigy-natural`): `primary` → `assets/primary.png`
- `trango-rock-prodigy-pivot` (`trango.rock-prodigy-pivot`): `orientation-1` → `assets/primary.png`; `orientation-2` → `assets/orientation-2.png`; `orientation-3` → `assets/orientation-3.png`; `orientation-4` → `assets/orientation-4.png`
- `trango-rock-prodigy-training-center` (`trango.rock-prodigy-training-center`): `primary` → `assets/primary.png`
- `yy-baguette-evo` (`yy.baguette-evo`): `paired-25-20-15-10` → `assets/primary.png`; `paired-12-8-6` → `assets/shallow-pairs.png`; `central-30-25` → `assets/central-30-25.png`; `central-20-6` → `assets/central-20-6.png`; `rounded-tray` → `assets/tray.png`
- `yy-baguette` (`yy.baguette`): `stepped-face` → `assets/primary.png`; `reverse-face` → `assets/reverse.png`
- `yy-penta-evo` (`yy.penta-evo`): `front-pair` → `assets/primary.png`
- `yy-travelboard` (`yy.travelboard`): `front-25-15` → `assets/primary.png`; `reverse-10` → `assets/reverse.png`
- `yy-verticalboard-evo` (`yy.verticalboard-evo`): `primary` → `assets/primary.png`
- `yy-verticalboard-first` (`yy.verticalboard-first`): `primary` → `assets/primary.png`
- `yy-verticalboard-light` (`yy.verticalboard-light`): `primary` → `assets/primary.png`
- `yy-verticalboard-one` (`yy.verticalboard-one`): `primary` → `assets/primary.png`
- `zlagboard-evo` (`zlagboard.evo`): `primary` → `assets/primary.png`
- `zlagboard-pro` (`zlagboard.pro`): `primary` → `assets/primary.png`

- [ ] **Step 1: Search and open live evidence for every exact product and revision.**

  Search all 22 exact products independently. Distinguish Grindstone original, Mk2, and Pro; distinguish every Rock Prodigy construction; distinguish Baguette from Baguette Evo and all VerticalBoard models; distinguish Zlagboard Evo from Pro 2.0. Open official straight-on/layout and oblique/material evidence plus direct independent real-world corroboration. For alternate orientations and faces, require a direct source showing that the surface or inversion is intended for use.

- [ ] **Step 2: Write all 34 records from the opened sources.**

  Enter every Task 1 field and current hash/dimensions. Treat four Flash Board orientations, four Pivot orientations, five Baguette Evo presentations, two Baguette faces, and two TravelBoard faces as independent working-surface claims. Do not use one orientation's published picture to assert another orientation's topology. Preserve documented mixed-material components on Zlagboard and exact sourced material differences among Rock Prodigy models.

- [ ] **Step 3: Select qualified comparators and make decisions under the shared style contract.**

  Compare within material and form-factor cohorts and apply the head-on rule to each presentation's usable surface, not to the conventional front of the product. When no accepted current comparator exists, use the closed gap mode only for evidence-blocked keeps or Phase 2 repair decisions; never use it to accept a keep. Record a repair whenever recess depth is conveyed through camera tilt instead of controlled shading. A multi-orientation asset is not nonconforming solely because it depicts a side/end of the whole object; it fails only if that selected working surface itself is oblique.

- [ ] **Step 4: Validate lane C and update its narrative status.**

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --package-id target10a.linebreaker-base \
    --package-id tension.flash-board \
    --package-id tension.grindstone-original \
    --package-id tension.grindstone-pro \
    --package-id tension.grindstone \
    --package-id tension.honestone \
    --package-id tension.whetstone \
    --package-id the-hangboard.the-hangboard \
    --package-id trango.rock-prodigy-forge \
    --package-id trango.rock-prodigy-natural \
    --package-id trango.rock-prodigy-pivot \
    --package-id trango.rock-prodigy-training-center \
    --package-id yy.baguette-evo \
    --package-id yy.baguette \
    --package-id yy.penta-evo \
    --package-id yy.travelboard \
    --package-id yy.verticalboard-evo \
    --package-id yy.verticalboard-first \
    --package-id yy.verticalboard-light \
    --package-id yy.verticalboard-one \
    --package-id zlagboard.evo \
    --package-id zlagboard.pro
  ```

  Expected: PASS with `packageCount: 22` and `presentationCount: 34`. Change only lane C's narrative status to `Complete — 22 packages / 34 assets`; add exact revision/source conflicts to the resolution section.

- [ ] **Step 5: Confirm no package input changed, then commit and push.**

  ```bash
  rtk git diff --name-only -- Hangboards
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Reclassify presentation assets in lane C"
  rtk git push
  ```

  Expected: the diff command prints nothing before the commit.

---

### Task 6: Reconcile source conflicts, decisions, and cross-catalog comparators

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: all 85 lane records and their direct live URLs.
- Produces: a full-catalog manifest with every source conflict resolved to named revisions or explicitly evidence-blocked, every record assigned a valid decision, and every comparator either pointing to a ready kept baseline or carrying a permitted exact cohort-baseline gap; narrative classification totals come from the validator report.

- [ ] **Step 1: Run full validation and collect every cross-lane failure.**

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  ```

  Expected on the first reconciliation run: FAIL only for unresolved cross-lane comparator mode/readiness/material compatibility, contradictory decisions, or incomplete exact-inventory evidence; no lane may be silently excluded.

- [ ] **Step 2: Re-open conflicting live sources and resolve each to a physical revision.**

  For every official/independent disagreement, revisit the direct pages and search revision-specific model names, catalogue years, manuals, color/material editions, and component layouts. Record separate evidence entries for each revision. Set `physicalRevision` to the revision actually represented by the current package; do not merge details. If the package combines distinct constructions/materials/usable surfaces/topologies, use `splitPhysicalRevision`. If a declared surface is proved non-usable, use `removeUnsupportedPresentation`. If proof remains absent, retain an evidence-blocked `keep` with null accepted output and explain the exact missing evidence in both the record and narrative.

- [ ] **Step 3: Re-evaluate all 85 decisions and all seven findings.**

  Apply these consistency rules record by record:

  - accepted `keep`: no `nonconforming` or `uncertain` finding, current hash/dimensions copied into final acceptance, and no generation data;
  - evidence-blocked `keep`: at least one `uncertain` finding, null final acceptance, `blockedEvidence`, and exact evidence-gap text;
  - `edit`: likeness/topology are source-confirmed but one or more material, perspective, smoothing, framing, or consistency findings require a bounded correction;
  - `regenerate`: source-confirmed silhouette, topology, revision, component inventory, or working-surface representation is wrong;
  - removal/split: only the direct-source conditions from Task 1, with mutations deferred to Phase 2.

  Re-check that genuine side/end/reverse faces remain when sourced and are judged head-on to themselves.

- [ ] **Step 4: Establish ready baseline records and repair every comparator reference.**

  Seek at least one accepted kept baseline for each material/form-factor cohort actually present. A baseline must itself have complete evidence and conforming findings. In ready-baseline mode, update the comparator to that ready keep and explain both material and form-factor applicability; a baseline may not supply absent product geometry. If no current asset qualifies for a cohort, set all four ready-baseline fields to null and write the exact reason in `baselineGap` for each affected evidence-blocked keep or Phase 2 repair record. Never point to a noncompliant asset, mix ready/gap fields, or allow an accepted keep to use gap mode.

- [ ] **Step 5: Run the validator to GREEN and write deterministic totals.**

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  ```

  Expected: PASS with `packageCount: 61`, `presentationCount: 85`, decision counts summing to 85, and only explicitly evidenced blocked assets in `evidenceBlockedAssets`. Copy those exact decision counts and blocked asset paths into `## Final classification totals`; summarize each removal/split/conflict resolution without copying source prose.

- [ ] **Step 6: Confirm no package input changed, then commit and push.**

  ```bash
  rtk git diff --name-only -- Hangboards
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Reconcile presentation remediation classifications"
  rtk git push
  ```

  Expected: the diff command prints nothing before the commit.

---

### Task 7: Verify Phase 1 integrity and record its checks

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the complete reconciled manifest and all package-tool tests.
- Produces: passing full validation, passing full package tests, explicit Phase 1 check records, and proof that the phase changed no PNG or `board.json` since approved-spec commit `2e74fc8`.

- [ ] **Step 1: Run focused validator and CLI tests.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py
  ```

  Expected: PASS.

- [ ] **Step 2: Run the full package-tool suite and final package inventory validation.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  ```

  Expected: all package-tool tests PASS; package validation returns `0` with all 61 packages valid and no draft inventory.

- [ ] **Step 3: Prove manifest completeness and Phase 1 package immutability.**

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  rtk git diff --name-only 2e74fc8..HEAD -- Hangboards
  rtk git diff --name-only -- Hangboards
  ```

  Expected: manifest validation passes with exactly 61 packages/85 presentations; both `Hangboards` diff commands print nothing. If either diff prints a PNG or `board.json`, stop and restore Phase 1 scope through a new corrective commit without discarding unrelated user changes.

- [ ] **Step 4: Record only the checks actually run.**

  Set the four root `phase1Checks` entries to `status: "passed"` and their exact command strings from Steps 2–3. Do not change any per-presentation `final.validation` or Workbench status: those are Phase 2 completion claims. Add a `## Phase 1 verification` narrative section listing the same commands, their pass result, and the no-`Hangboards` diff result.

- [ ] **Step 5: Re-run JSON parsing, full manifest validation, and the truthfulness tests.**

  ```bash
  rtk python3 -m json.tool \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  rtk scripts/hangboard-packages.sh audit-presentations \
    --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py
  ```

  Expected: JSON parses; the report remains 61/85; all truthfulness tests PASS, including the prohibition on accepted hashes and final validation for every non-keep repair record.

- [ ] **Step 6: Commit and push the verified Phase 1 deliverable.**

  ```bash
  rtk git add \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Verify hangboard remediation phase one"
  rtk git push
  ```

  The controller then performs the final spec-compliance review and separate data/code-quality review. Phase 2 image generation, image editing, package mutation, Workbench geometry review, build-for-testing, and simulator QA begin only after this Phase 1 manifest is accepted.
