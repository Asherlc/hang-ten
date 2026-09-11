# Hangboard 3D Toolkit Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract reusable verification, authoring, suspension, evidence, and staging contracts without changing shipped model geometry or Hang Ten behavior.

**Architecture:** First freeze Beastmaker 1000 and Compact II from their actual exported USDZ packages, with Flash captured only as a non-mutating baseline. Then move repeated actual-export checks behind a fail-closed configuration object, extract Blender helpers through semantic snapshots, and extract suspension solver/rendering through compatibility facades. Manifests and galleries consume verified packages rather than becoming a second geometry source.

**Tech Stack:** Python 3, Blender Python (`bpy`), USDZ, JSON, pytest, Swift, XCTest, SceneKit.

**Spec:** `docs/superpowers/specs/2026-09-10-hangboard-3d-toolkit-extraction-design.md`

## Global Constraints

- Preserve shipped USDZ, descriptor, texture, logical inventory/order, staging-tree, picking, and app behavior unless a separately approved rebuild says otherwise.
- Model packages remain model-only, contain exactly one USDZ and hash-bound descriptor, and never acquire raster paths, fallback media, cached bounds, or hand-authored frames.
- Verify only reimported actual USDZ geometry; no source images, source blend data, name-based identity inference, or render mask may substitute for imported triangles.
- Board adapters may add typed probes but cannot disable inventory, asset, material, role, descriptor, or nearest-triangle checks.
- Do not change Flash generator/package/descriptor/runtime/tests in this extraction. It is baseline-only until its two-branch migration has separately completed and been reviewed.
- Geometry remains direct analytic/evidence-reviewed authoring; only Astra may make final physical-fidelity changes after approved multi-angle evidence.
- All owned generated output is owner-prefixed under `.context`, recorded, and removed/verified by an exit trap. Production staging remains recursive regular-file copying.
- Preserve strict Python/Swift package compatibility: member order, duplicate keys, scalar kinds, explicit-null rejection, finite values, and shared malformed fixtures.
- Luna owns routine tests/tooling/parser/documentation; Terra is used only after a bounded Luna integration failure; Astra is reserved exclusively for final physical geometry/fidelity.

---

### Task 1: Characterize existing actual-export and package behavior

**Files:**
- Create: `Tools/HangboardModels/model_characterization.py`
- Create: `Tools/HangboardModels/test_model_characterization.py`
- Modify: `Tools/HangboardModels/test_model_reports.py`
- Modify: `Tools/HangboardPackages/tests/test_board_package_staging.py`

**Interfaces:**
- Consumes: `compile_model_package.load_logical_hold_ids`, each current verifier report, package paths, and `scripts/stage-board-packages.py` output.
- Produces: `capture_model_baseline(package: Path, board_json: Path) -> dict[str, object]` and `assert_baseline_matches(actual: Mapping[str, object], expected: Mapping[str, object]) -> None`.

- [ ] **Step 1: Write failing pure-Python characterization tests**

```python
def test_capture_model_baseline_records_exact_two_asset_tree_and_hashes(tmp_path):
    baseline = capture_model_baseline(package, board_json)
    assert baseline["assets"] == ["assets/primary.model.json", "assets/primary.usdz"]
    assert baseline["logicalHoldIDs"] == expected_ids
    assert baseline["descriptorSHA256"] == sha256(descriptor)

def test_baseline_comparison_rejects_reordered_inventory():
    with pytest.raises(ValueError, match="logicalHoldIDs"):
        assert_baseline_matches({"logicalHoldIDs": ["b", "a"]}, {"logicalHoldIDs": ["a", "b"]})
```

- [ ] **Step 2: Run the new tests and confirm they fail because the module/functions are absent.**

Run: `pytest -q Tools/HangboardModels/test_model_characterization.py`

- [ ] **Step 3: Implement deterministic, Blender-free package-tree/hash/descriptor/logical-ID capture and strict comparison.**

```python
def capture_model_baseline(package: Path, board_json: Path) -> dict[str, object]:
    assets = _regular_assets(package)
    descriptor = _json_object(package / "assets/primary.model.json")
    return {"assets": sorted(assets), "logicalHoldIDs": _ordered_hold_ids(board_json),
            "modelSHA256": _sha256(package / "assets/primary.usdz"),
            "descriptorSHA256": _sha256(package / "assets/primary.model.json"),
            "descriptor": descriptor}
```

- [ ] **Step 4: Add fixture-driven tests for Beastmaker 1000, Compact II, and Flash baseline capture; Flash tests must only read existing assets. Add a staging characterization that compares every staged regular-file byte to its source.**

- [ ] **Step 5: Run the targeted Python suites, then commit and push.**

Run: `pytest -q Tools/HangboardModels/test_model_characterization.py Tools/HangboardModels/test_model_reports.py Tools/HangboardPackages/tests/test_board_package_staging.py`

Commit: `test: characterize shipped model packages and staging`

### Task 2: Extract fail-closed generic verification core and Beastmaker adapter

**Files:**
- Create: `Tools/HangboardModels/model_verification.py`
- Create: `Tools/HangboardModels/test_model_verification.py`
- Modify: `Tools/HangboardModels/verify_beastmaker_1000.py`
- Modify: `Tools/HangboardModels/test_model_reports.py`

**Interfaces:**
- Consumes: Task 1 baselines and `compile_model_package.validate_tagged_scene`, `_snapshot_scene`, `_imported_source_node_ids`, and `compile_descriptor`.
- Produces: `ModelVerificationConfig`, `MaterialPolicy`, `VerificationReport`, `BoardProbe`, and `verify_model_package(package: Path, config: ModelVerificationConfig, *, render: bool = False) -> VerificationReport`.

- [ ] **Step 1: Write failing unit tests for strict config asset equality, ordered hold IDs, descriptor regeneration, additive probes, material policy, forbidden-mesh tokens, and report serialization without importing `bpy`.**

```python
def test_verify_model_package_rejects_an_unconfigured_regular_asset(tmp_path):
    with pytest.raises(ValueError, match="asset inventory"):
        verify_model_package(tmp_path, config)

def test_board_probe_cannot_turn_off_core_inventory_failure():
    with pytest.raises(ValueError, match="logical inventory"):
        verify_model_package(package_with_reordered_ids, config_with_passing_probe)
```

- [ ] **Step 2: Run and confirm the core tests fail because `model_verification` is unavailable.**

Run: `pytest -q Tools/HangboardModels/test_model_verification.py`

- [ ] **Step 3: Implement dataclass configuration and pure report/package validation with lazy Blender imports; invoke the existing compiler helpers only after core checks pass.**

```python
@dataclass(frozen=True)
class ModelVerificationConfig:
    board_id: str
    board_json: Path
    package_relative_assets: frozenset[str]
    expected_hold_ids: tuple[str, ...]
    expected_position_ids: tuple[str, ...] = ()
    triangle_ceiling: int | None = None
    required_roles: frozenset[str] = frozenset({"body", "hold"})
    forbidden_name_tokens: tuple[str, ...] = ()
    material_policy: MaterialPolicy = field(default_factory=MaterialPolicy.canonical_wood)
    suspension_policy: SuspensionVerificationPolicy | None = None
    board_probes: tuple[BoardProbe, ...] = ()
```

- [ ] **Step 4: Convert Beastmaker’s CLI into a compatibility adapter with its 22-ID inventory, hardware prohibition, canonical material checks, existing authored rim/nearest-hit probe, and unchanged output fields/`--skip-renders` behavior. Compare the adapter report against the Task 1 baseline.**

- [ ] **Step 5: Run core and Beastmaker tests, the existing report test, and the Blender verifier where available; commit and push.**

Run: `pytest -q Tools/HangboardModels/test_model_verification.py Tools/HangboardModels/test_model_reports.py`

Commit: `feat: extract model verification core and Beastmaker adapter`

### Task 3: Adopt Compact II without adding unsupported depth or rendering claims

**Files:**
- Modify: `Tools/HangboardModels/verify_wood_grips_compact_ii.py`
- Modify: `Tools/HangboardModels/test_model_verification.py`
- Modify: `Tools/HangboardModels/test_model_reports.py`

**Interfaces:**
- Consumes: `ModelVerificationConfig` and `verify_model_package` from Task 2.
- Produces: `compact_ii_config() -> ModelVerificationConfig` retaining `triangle_ceiling=150_000` and a `rendersSkipped` compatibility report.

- [ ] **Step 1: Write failing adapter tests that prove 19 ordered IDs, exact two-asset package inventory, descriptor equality after actual reimport, imported image material on every bound mesh, triangle ceiling, and `--skip-renders` are retained.**

- [ ] **Step 2: Run the tests and confirm they fail before the adapter is changed.**

Run: `pytest -q Tools/HangboardModels/test_model_verification.py Tools/HangboardModels/test_model_reports.py`

- [ ] **Step 3: Implement only the Compact config/adapter; do not add a body-depth assertion or a review rig.**

- [ ] **Step 4: Run all Compact and generic verifier tests plus the actual Blender CLI using `--skip-renders`; compare the report to the Task 1 baseline; commit and push.**

Commit: `refactor: route Compact II verification through shared core`

### Task 4: Extract geometry primitives through semantic snapshots

**Files:**
- Create: `Tools/HangboardModels/geometry_primitives.py`
- Create: `Tools/HangboardModels/test_geometry_primitives.py`
- Modify: `Tools/HangboardModels/beastmaker_1000.py`
- Modify: `Tools/HangboardModels/wood_grips_compact_ii.py`
- Modify: `Tools/HangboardModels/tension_flash_board.py`
- Modify: `Tools/HangboardModels/test_compile_model_package_blender.py`

**Interfaces:**
- Consumes: compiler tag properties and Task 1 source/package baseline data.
- Produces: `tag_piece`, `create_rounded_body`, `create_recess`, `create_stepped_edge`, `create_passage`, `split_contact_surface`, and `make_review_rig`, all preserving authored coordinates/topology unless an approved geometry task says otherwise.

- [ ] **Step 1: Write Blender tests that snapshot object names/roles/hold IDs, transforms, vertex/topology hashes, material image bytes, and explicit no-export review objects before calling one primitive.**

- [ ] **Step 2: Run in Blender and confirm each requested primitive is unavailable.**

- [ ] **Step 3: Implement tags/material and one analytic helper family at a time; after every family re-run source-scene snapshots. Use `Path(__file__)` import bootstrap and create disposable boolean/export objects only.**

- [ ] **Step 4: Migrate generator call sites one board at a time, first Beastmaker then Compact. Keep Flash source functionally identical; no Flash compile, package, descriptor, or runtime artifact is replaced.**

- [ ] **Step 5: Compile only owned temporary packages, compare captured semantic snapshots and baseline descriptor geometry/material bytes, run clay/front/oblique/detail review, then commit and push each independently accepted family.**

### Task 5: Characterize and extract single-cord suspension behind a Swift compatibility facade

**Files:**
- Create: `HangTen/Models/SuspensionProfiles.swift`
- Modify: `HangTen/Views/SuspendedBoardPresentation.swift`
- Modify: `HangTen/Views/BoardModelView.swift`
- Modify: `HangTenTests/BoardModelTests.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- Consumes: `BoardModelSingleCordSuspension`, `BoardModelBounds`, and the existing `SuspendedCordSolver` behavior.
- Produces: `SuspensionProfileSolver.solveSingle(pose:profile:bounds:) throws -> SolvedSuspension`, `SolvedSuspension`, and `SolvedCordBranch`; the existing public `SuspendedBoardPresentation` remains a forwarding facade.

- [ ] **Step 1: Add failing XCTest fixtures for existing single-cord samples, tangents, polyline/measured lengths, board transform, framing, taut/slack classification, invalid/nonfinite inputs, missing pose/node, clearance failure, non-pickability, and unavailable state.**

- [ ] **Step 2: Run the focused XCTest selection and confirm it fails because the model-layer solver is missing.**

- [ ] **Step 3: Move pure single-cord calculations without changing constants, bisection tolerance, sample count, endpoint preservation, or error mapping; keep the view-layer facade.**

- [ ] **Step 4: Make SceneKit create only transient, independent non-pickable/no-accessibility tube nodes, atomically replacing its cord layer while retaining wood highlights.**

- [ ] **Step 5: Run focused and full model/package XCTest suites, visual simulator review for the existing single-cord board, then commit and push.**

### Task 6: Add shared manifest validation, gallery bookkeeping, staging parity, and malformed profile fixtures

**Files:**
- Create: `Tools/HangboardModels/migration-manifest.schema.json`
- Create: `Tools/HangboardModels/migration-manifest.example.json`
- Create: `Tools/HangboardModels/migration_manifest.py`
- Create: `Tools/HangboardModels/render_model_gallery.py`
- Create: `Tools/HangboardModels/test_migration_manifest.py`
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py`
- Modify: `Tools/HangboardPackages/tests/test_board_package_staging.py`
- Modify: `scripts/stage-board-packages.py`

**Interfaces:**
- Consumes: verified package output, Task 1 baseline records, model presentation descriptor, and current cross-parser fixtures.
- Produces: `load_migration_manifest(path: Path) -> MigrationManifest`, `render_model_gallery(package: Path, manifest: MigrationManifest, output: Path) -> tuple[ReviewArtifact, ...]`, and exact source-to-stage byte assertions.

- [ ] **Step 1: Write failing tests for closed manifest objects: reject unknown/duplicate/null/wrong-kind/path-escaping members; require one model USDZ/descriptor, exact logical ID order, declared omissions, and no geometry/bounds fields.**

- [ ] **Step 2: Write failing gallery/staging tests that require owner-prefixed `.context` output, stable view/hash/provenance records, package validation before render, exact asset bytes after staging, and cleanup of only the owned output directory.**

- [ ] **Step 3: Implement parser and gallery with lazy Blender imports. Keep existing render scripts as wrappers until output equivalence is characterized; do not place manifests/galleries in compiler packages.**

- [ ] **Step 4: Extend the single shared malformed matrix with ordered discriminator/passage/branch/pose/duplicate-key/member-order/scalar-kind/explicit-null mutations and make both Python and Swift tests consume it.**

- [ ] **Step 5: Backfill Beastmaker and Compact manifests using existing evidence only. Add Flash only after its separately approved migration is complete; do not synthesize Flash evidence or change its files. Run Python, Swift, staging, and gallery tests; commit and push.**

### Task 7: Extract two-branch suspension only after the Flash migration gate

**Files:**
- Modify: `HangTen/Models/SuspensionProfiles.swift`
- Modify: `HangTen/Views/SuspendedBoardPresentation.swift`
- Modify: `HangTen/Views/BoardModelView.swift`
- Modify: `HangTenTests/BoardModelTests.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `Tools/HangboardModels/model_verification.py`
- Modify: `Tools/HangboardModels/test_model_verification.py`

**Interfaces:**
- Consumes: Task 5 solver types and reviewed Flash package/profile inputs.
- Produces: `SuspensionProfileSolver.solveTwoBranch(pose:profile:bounds:) throws -> SolvedSuspension` with each route `anchor -> passage[0] -> passage[1] -> anchor`.

- [ ] **Step 1: Verify the external gate: Flash's own two-branch migration, evidence, package, descriptor, and review are complete and approved. If not, record this task as blocked and do not modify Flash or extract this route.**

- [ ] **Step 2: Add failing parity tests for two ordered branches, shared fixed anchor, taut/slack spans, transformed poses, preserved passage interior, actual-mesh clearance, nearer cord hit, self-intersection, invalid framing, and every unavailable-state error.**

- [ ] **Step 3: Implement the two-branch solver/renderer in the existing typed closed contract; prohibit fallback, visible anchor, partial branches, raster use, and logical-hold attachment.**

- [ ] **Step 4: Run Python/Swift parity fixtures, actual triangle probes, iOS interaction/accessibility/picking checks, then commit and push.**

### Task 8: Document supported workflow and remove only proven compatibility duplication

**Files:**
- Modify: `.codex/skills/migrate-hangboard-to-3d/SKILL.md`
- Modify: `Tools/HangboardModels/README.md`
- Modify: verifier wrappers only after all consumers use shared config.

**Interfaces:**
- Consumes: Tasks 1–7 public interfaces and verified manifests/gallery workflow.
- Produces: documentation that names the shared verifier/config/manifest/gallery entry points and maintains the migration skill’s evidence, Astra, no-image-tracing, no-remote-sync, and Workbench-boundary requirements.

- [ ] **Step 1: Add documentation assertions/README examples that invoke existing CLI wrappers and verify no unsupported remote sync or model editing claim is introduced.**

- [ ] **Step 2: Update the README and migration skill without weakening any evidence gate or geometry rule.**

- [ ] **Step 3: Remove a wrapper only after adapter parity is covered by tests and every caller uses the shared API; otherwise retain the wrapper.**

- [ ] **Step 4: Run full Python package/model suites, full Hang Ten tests, parser fixture suite, staging characterization, and first-migration iOS review route for every newly migrated board. Commit and push.**

## Pre-execution rulings

1. Task 1 makes no geometry/package/runtime changes and is the required first commit.
2. Tasks 2–3 can proceed after Task 1; Task 4 follows their report contract; Task 5 is independent of Flash but retains the current single-cord behavior; Task 6 consumes Tasks 1–3 and may manifest only Beastmaker/Compact.
3. Task 7 has a hard external dependency on Flash’s separate migration approval. It is not a defect in this extraction when that gate is unavailable.
4. Task 8 occurs only for shipped, verified interfaces. Documentation must not claim the blocked two-branch or Flash adoption is shipped.

## Self-review

- Coverage: Tasks 1–3 cover the characterization/verifier rollout; Task 4 covers analytic primitives; Tasks 5 and 7 cover single/two-branch runtime plus parity; Task 6 covers manifest/gallery/staging fixtures; Task 8 covers runtime/skill docs. Flash remains deliberately gated as required by the approved design.
- Placeholder scan: No implementation step relies on unspecified geometry measurements or a generic bypass callback. Existing board data and tests are its input.
- Interface consistency: `ModelVerificationConfig`/`verify_model_package`, manifest functions, and `SuspensionProfileSolver` names remain constant throughout the tasks.
