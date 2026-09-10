# Hangboard 3D Toolkit Extraction Design

**Date:** 2026-09-10  
**Status:** Approved design; implementation follows characterization gates  
**Scope:** Reusable tooling and contracts for model-first hangboard migrations

## Decision summary

Extract a deliberately small toolkit around the contracts that are already
proven by the Beastmaker 1000, Metolius Wood Grips Compact II, and Tension
Flash Board migrations:

1. a configuration-driven actual-export verifier;
2. Blender geometry and review primitives;
3. one typed suspension profile contract with single-cord and two-branch
   implementations;
4. shared evidence fixtures, galleries, and a package migration manifest; and
5. an explicit characterization-first migration sequence.

The toolkit owns invariant checks and deterministic math. A board integration
owns only source evidence, logical inventory/order, board-specific geometry,
position mappings, and any evidence-backed probes that cannot be generalized.
The first extraction must not change the active Flash Board source, package,
descriptor, runtime, or tests. Those files are inputs to characterization and
later adopters, not cleanup targets for this design task.

## Existing baseline and constraints

The following existing code is the baseline to preserve:

| Area | Current implementation | Extraction implication |
| --- | --- | --- |
| USDZ compilation | `Tools/HangboardModels/compile_model_package.py` and `model_descriptor.py` validate tagged meshes, export temporary triangulated copies, reimport the actual USDZ, and derive a hash-bound descriptor | Move reusable validation behind stable functions; keep the current CLI and descriptor bytes compatible |
| Actual-export checks | `verify_beastmaker_1000.py`, `verify_wood_grips_compact_ii.py`, and `verify_tension_flash_board.py` repeat package paths, JSON checks, materials, node correspondence, triangle checks, and reports | Centralize invariants; retain board-specific configuration/hooks for rim, position, and suspension probes |
| Blender authoring | `beastmaker_1000.py`, `wood_grips_compact_ii.py`, and `tension_flash_board.py` each define mesh, material, recess, body, tagging, camera, and render helpers | Introduce primitives without changing authored shapes; generated geometry remains evidence-reviewed and board-owned |
| Suspension parsing | `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` already has immutable single- and two-branch types and strict parsing; `HangTen/Models/BoardPackageStore.swift` mirrors the package contract | Treat the closed JSON shape, member order, scalar kinds, and explicit-null rejection as an existing compatibility contract |
| Suspension solving/rendering | `HangTen/Views/SuspendedBoardPresentation.swift` contains deterministic catenary solving, two-branch route construction, framing, and error types; `BoardModelView.swift` creates transient SceneKit cord nodes | Extract shared pure solving/rendering contracts while preserving outputs, tolerances, and unavailable-state behavior |
| Runtime/package bridge | `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`, and `HangTen/Views/BoardModelView.swift` load one model plus descriptor and bind only descriptor hold nodes | Keep model-only packages, exact descriptor bindings, nearest-triangle picking, accessibility, and explicit failure state unchanged |
| Evidence/review | `evidence_packet.py`, `validate_evidence_packet.py`, board generators, `render_hold_highlights.py`, and `render_canonical_wood_review.py` produce retained evidence and review images | Add common manifest/gallery bookkeeping; never replace the multi-angle human evidence gate |
| Staging | `scripts/stage-board-packages.py` recursively copies validated regular files; `rebuild_all_wood_models.py` discovers model packages and checks exact package trees | Add characterization assertions first; change production staging only if a test proves its current behavior insufficient |

The migration skill remains authoritative for evidence tiers, direct analytic
geometry authoring, omission of mounting hardware, canonical materials,
actual-export verification, Blender bootstrap/sandbox boundaries, SceneKit
picking, cleanup, and Astra ownership of final physical-shape judgment. The
toolkit cannot loosen those rules.

## Goals and non-goals

### Goals

- Make a new model migration mostly declarative: board identity, hold IDs,
  source/evidence paths, geometry generator, positions, and board-specific
  probes.
- Make actual USDZ verification independent of authored `.blend` files and
  source images.
- Make the Python verifier and Swift runtime consume the same suspension
  semantics and fixed numerical parameters.
- Produce repeatable reports, review galleries, and package/hash evidence with
  workspace-owned output and cleanup records.
- Preserve byte, descriptor, inventory, picking, and visual behavior for
  shipped models during extraction.

### Non-goals

- A generic CAD system, image tracer, segmentation/vectorization tool, or
  manufacturing modeler.
- Runtime rope dynamics, stretch, knots, loads, or safety claims.
- Automatic hold discovery or geometry refinement.
- A raster compatibility layer for model packages.
- Replacing board-specific evidence judgment or silently inventing dimensions.
- Remote model synchronization or Workbench model editing.

## Target architecture

The extraction is organized as four layers. Dependencies point downward;
board adapters are the only layer allowed to know a board's physical layout.

```text
board migration adapter
  ├── evidence + logical inventory
  ├── Blender geometry recipe using primitives
  ├── verification configuration + board-specific probes
  └── package migration manifest
        ↓
shared model verification / geometry primitives / suspension profiles
        ↓
existing package compiler, board catalog, Swift package loader, SceneKit
```

### 1. Generic USDZ verification framework

Create `Tools/HangboardModels/model_verification.py` as a Blender-importable
and Blender-free-friendly module. Keep Blender imports lazy so report and
fixture tests can run without `bpy`.

The public configuration is intentionally explicit:

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
    material_policy: MaterialPolicy = MaterialPolicy.canonical_wood()
    suspension_policy: SuspensionVerificationPolicy | None = None
    board_probes: tuple[BoardProbe, ...] = ()
    review_policy: ReviewPolicy = ReviewPolicy()

def verify_model_package(
    package: Path,
    config: ModelVerificationConfig,
    *,
    render: bool = False,
) -> VerificationReport: ...
```

The verifier pipeline is fixed and ordered:

1. Resolve a regular, non-symlinked package and require exactly the configured
   asset inventory (`board.json` is outside the compiler-owned two-asset tree;
   model packages still require one USDZ and one descriptor).
2. Read logical IDs from the board document and compare them to the ordered
   configuration. Reject missing, duplicate, unknown, or reordered IDs.
3. Clear Blender's source materials/images, import only the actual USDZ, and
   require explicit triangles, non-empty mesh geometry, and importer-visible
   node bindings.
4. Verify body/hold/attachment roles, source-piece correspondence, exact
   descriptor hash, descriptor bytes derived from imported vertices, bounds,
   normalized hold frames, and logical inventory. Never infer a role from a
   renamed importer node.
5. Verify every used material has a usable image where the configured policy
   requires it, including positive dimensions and the canonical embedded PNG
   bytes/profile. Keep canonical wood policy as one implementation, not a
   hard-coded requirement for every future material.
6. Reject baked cord/anchor/mounting environment and unbound mesh geometry;
   run actual triangle nearest-hit probes for every configured position/hold.
7. If configured, solve and probe suspension clearance against actual imported
   triangles, allowing only the declared attachment/passage interface.
8. Run review renders/gallery hooks, then write a stable JSON report containing
   command/options, hashes, imported bindings, material checks, triangle count,
   probes, review artifacts, and cleanup verification.

The framework exposes narrow extension points rather than a board callback
that can bypass invariants:

```python
class BoardProbe(Protocol):
    id: str
    def run(self, imported: ImportedModel, config: ModelVerificationConfig) -> ProbeResult: ...

class ReviewPolicy(Protocol):
    def render(self, imported: ImportedModel, output: Path) -> tuple[ReviewArtifact, ...]: ...
```

Board-specific checks may add assertions (for example Compact II's absence
of an overall-depth claim or Beastmaker's complete outer-rim ligament probes)
but cannot disable core package, material, role, descriptor, inventory, or
nearest-hit validation. The current CLIs become thin adapters that construct a
config and print/write the same report shape, preserving existing command
names and `--skip-renders` behavior during a deprecation window.

### 2. Blender geometry primitives

Create `Tools/HangboardModels/geometry_primitives.py` with pure specifications
and Blender-facing constructors. The module must bootstrap sibling imports from
`__file__`, as the compiler does, and must not rely on caller `cwd` or
`PYTHONPATH`.

Proposed primitives:

```python
@dataclass(frozen=True)
class RoundedBodySpec: ...
@dataclass(frozen=True)
class RecessSpec: ...
@dataclass(frozen=True)
class SteppedEdgeSpec: ...
@dataclass(frozen=True)
class PassageSpec: ...

def create_rounded_body(spec: RoundedBodySpec) -> bpy.types.Object: ...
def create_recess(body: bpy.types.Object, spec: RecessSpec) -> bpy.types.Object: ...
def create_stepped_edge(body: bpy.types.Object, spec: SteppedEdgeSpec) -> bpy.types.Object: ...
def create_passage(body: bpy.types.Object, spec: PassageSpec) -> bpy.types.Object: ...
def split_contact_surface(body: bpy.types.Object, hold_id: str, spec: SurfaceSplitSpec) -> bpy.types.Object: ...
def tag_piece(obj: bpy.types.Object, *, role: Literal["body", "hold", "attachment"], hold_id: str | None = None) -> None: ...
def make_review_rig(policy: ReviewRigPolicy) -> ReviewRig: ...
```

Requirements for all primitives:

- analytic sections/fillets and deliberate tessellation; no pixel-derived
  contours, automatic masks, or inferred constraints;
- Boolean cutters and temporary export triangulation are disposable and never
  change editable source topology unexpectedly;
- one canonical light-neutral material source can be assigned consistently;
- contact splits preserve disconnected pieces and stable logical IDs;
- passage/notch/decorative surfaces are explicitly non-hold and cannot become
  selectable through a name convention; and
- review rigs produce matched front, opposite/oblique, clay-detail, and close
  pocket/passage views without adding render-only objects to the export.

Existing generators migrate one function family at a time. The primitive
module must not normalize dimensions or “repair” a board to satisfy a probe;
shape changes remain an evidence-reviewed geometry task and, where physical
fidelity is involved, an Astra task.

### 3. Suspension profiles: shared solver and rendering contract

Keep the closed package discriminator and member names already implemented:
`singleCord` and `twoBranchCord`. Add a shared conceptual contract consumed by
Python verification and Swift runtime; the first implementation may use
language-native types with parity fixtures rather than introducing a new
runtime dependency.

#### Typed profile shape

```text
SuspensionProfile
  ├── SingleCordProfile
  │     attachment(nodeID, pointInModel, provenance)
  │     anchor(offsetFromBoardBounds, invisible, provenance)
  │     cord(restLength, radius, material, provenance)
  │     canonicalPoses[positionID]
  └── TwoBranchCordProfile
        passages.left[2], passages.right[2]
        branches[2](ordered passageIDs, restLength, radius, material)
        one shared invisible anchor
        canonicalPoses[positionID]
```

Each passage/attachment node is importer-visible and descriptor-bound, but is
not a logical hold. Pose keys are exactly the package's supported position IDs.
No pose is created for an unknown position. Camera data is presentation data;
it does not rotate the board independently.

#### Deterministic solver API

The Swift extraction should introduce a focused `SuspensionProfiles.swift`
(or an equivalently named model-layer file) and leave a compatibility facade
in `SuspendedBoardPresentation.swift` until all callers migrate:

```swift
enum SuspensionProfileSolver {
    static func solveSingle(
        pose: BoardModelCanonicalPose,
        profile: BoardModelSingleCordSuspension,
        bounds: BoardModelBounds
    ) throws -> SolvedSuspension

    static func solveTwoBranch(
        pose: BoardModelCanonicalPose,
        profile: BoardModelTwoBranchSuspension,
        bounds: BoardModelBounds
    ) throws -> SolvedSuspension
}

struct SolvedSuspension {
    let boardTransform: simd_float4x4
    let fixedAnchor: SIMD3<Float>
    let branches: [SolvedCordBranch]
    let cameraFraming: SuspendedCameraFraming
    let requiredClearance: Float
}
```

`SolvedCordBranch` contains stable branch ID, ordered passage IDs, exact
endpoint/interior spans, fixed sample count, tangents, measured/polyline
lengths, and taut/slack state. Both languages use the same declared gravity
plane, sample count, bisection/taut tolerances, endpoint preservation, and
finite/self-intersection rules. A taut span is straight only when rest length
equals endpoint separation within the declared tolerance.

The two-branch route is explicitly `anchor -> passage[0] -> passage[1] ->
anchor`: free anchor spans use the catenary solver and the modeled passage
interior is preserved as a continuous ordered segment. Both branches share one
fixed world-space anchor. The cord renderer creates transient, independent
SceneKit tube nodes with a non-pickable category and no accessibility element;
the anchor has no node or visible stand-in. `BoardModelScene` remains
responsible for replacing the transient layer atomically and restoring wood
highlight state.

All invalid conditions route to the existing explicit model-unavailable/error
state: missing node/pose, invalid/nonfinite pose or cord values, too-short
rest length, unsolved/nonfinite/discontinuous/self-intersecting curve,
out-of-bounds passage, actual-mesh collision away from the approved interface,
nearer cord hit, or invalid camera framing. There is no straight, raster,
alternate-orientation, visible-anchor, or partial-branch fallback.

### 4. Evidence fixtures, gallery, and package migration manifest

Add a declarative manifest format under
`Tools/HangboardModels/migration-manifest.schema.json` and one checked-in
example at `Tools/HangboardModels/migration-manifest.example.json`. A board's
manifest records:

```json
{
  "schemaVersion": 1,
  "boardID": "...",
  "revision": "exact manufacturer revision",
  "boardJSON": "Hangboards/.../board.json",
  "evidencePacket": ".../evidence-packet.json",
  "sourceBlend": {"path": "...", "sha256": "..."},
  "logicalHoldIDs": ["..."],
  "presentation": {"id": "primary", "type": "model", "assetPath": "assets/primary.usdz", "descriptorPath": "assets/primary.model.json"},
  "positions": [{"id": "...", "activeHoldIDs": ["..."]}],
  "suspensionProfile": "singleCord | twoBranchCord | none",
  "deliberateOmissions": ["screw holes", "mounting hardware"],
  "verification": {"triangleCeiling": 150000, "probeIDs": ["..."]},
  "reviewViews": ["front", "three-quarter", "clay-detail", "active-hold"],
  "artifacts": {"packageSHA256": "...", "descriptorSHA256": "..."}
}
```

Unknown members, duplicate keys, wrong scalar kinds, explicit nulls, and
invalid paths are rejected. The manifest is evidence/bookkeeping, not a
second source of hold geometry or physical measurements. Sourced facts and
display estimates remain separate and retain provenance.

Add `Tools/HangboardModels/render_model_gallery.py`. It consumes a verified
package plus manifest and emits deterministic, owner-prefixed output under
`.context/<owner>-<board>-3d-review/`: front, opposite/three-quarter, clay
detail, all-holds, each canonical position, and active-highlight views. Each
artifact records camera, renderer, source/package/descriptor hashes, and
whether it is Blender-side or actual-app evidence. Existing render scripts
remain wrappers until gallery output is characterized equivalent.

Extend the existing shared malformed fixture matrix
`HangTenTests/Fixtures/BoardPackageValidationFixtures.json` with model-profile
cases, or add a sibling fixture only if the current matrix cannot represent
the case. Python package tests and Swift package-store tests consume the same
base documents and ordered mutations for discriminator, passage, branch,
pose, duplicate-key, order, scalar-kind, and explicit-null rejection.

The manifest runner stages only parser-approved regular files. It proves
staged USDZ/descriptor bytes and declared assets equal their sources, records
the exact command and output owner, and cleans owned temporary directories.
`scripts/stage-board-packages.py` stays recursive and production-compatible;
the first change is a characterization test, not a rewrite.

## Staged rollout and review gates

Each stage is independently testable and must land separately. A failed gate
stops the extraction; it does not justify changing board geometry, estimates,
camera, or package data to make a shared check pass.

### Stage 0 — characterize before extracting

- Capture current reports, descriptor JSON, USDZ/descriptor/texture hashes,
  package trees, logical ID/order, imported node correspondence, triangle
  budgets, materials, and position/probe results for Beastmaker and Compact.
- Capture the active Flash work as a baseline only; do not edit or rebuild its
  source/package during extraction. Keep its existing dirty files untouched.
- Add no source changes except isolated characterization tests/fixtures in the
  eventual implementation. Record exact CLI commands and owner cleanup.
- Review gate: repeated verification produces the same report and descriptors;
  every current shipped assertion has a named future config field or hook.

### Stage 1 — extract verifier core with compatibility adapters

- Implement `model_verification.py` and unit-test configs/reports without
  Blender.
- Port Beastmaker first because its verifier has no suspension route; compare
  report semantics and actual imported results byte-for-byte where applicable.
- Port Compact second, preserving its deliberate lack of an overall body-depth
  assertion and its `--skip-renders` behavior.
- Leave Flash verifier and active Flash files unchanged until the current
  two-branch migration has its own approved implementation and report.
- Review gate: old and new CLIs agree on package tree, hash, inventory,
  bindings, materials, triangles, and failure categories.

### Stage 2 — introduce geometry primitives without geometry redesign

- Extract one helper family at a time from the three generators: materials and
  tags, analytic rounded sections, recess/stepped edges, surface splitting,
  then review rigs.
- Use source-scene semantic snapshots (piece names/roles/hold IDs, vertex and
  topology hashes, transforms) before and after each extraction.
- Recompile only in an owned temporary directory; do not replace shipped model
  bytes until a deliberate rebuild is approved. Any physical-shape discrepancy
  goes to evidence review/Astra, not to a primitive “fix.”
- Review gate: no inventory, topology, descriptor geometry, material bytes, or
  reviewed visual behavior changes for migrated boards.

### Stage 3 — extract suspension profiles and rendering

- Characterize `SuspendedCordSolver` and `SuspendedBoardPresentation` outputs
  (samples, tangents, lengths, transforms, framing, and errors) as Swift test
  fixtures.
- Extract single-cord solving/rendering first behind the existing facade;
  prove existing single-cord behavior and all unavailable-state failures.
- Extract two-branch route solving/rendering next, using the already-approved
  strict package contract and the Flash design/plan as input. This step begins
  only after the active Flash changes are complete and reviewed; it must not
  mutate them as part of toolkit extraction.
- Add cross-language fixtures for a taut span, slack span, transformed pose,
  passage order, shared anchor, clearance, self-intersection, and all failure
  outcomes. Keep Python verification math within the declared tolerance and
  never use a screen mask as collision evidence.
- Review gate: bitwise/repeatability or declared numerical tolerance matches,
  actual triangle probes pass, cords remain non-pickable/inaccessible, and
  SceneKit/iOS behavior is unchanged for the characterized board.

### Stage 4 — manifests, fixtures, galleries, and staging

- Add manifest validation and backfill the two shipped model packages plus the
  completed Flash package when available.
- Move repeated report-writing and gallery layout to shared code; retain board
  IDs, position mappings, and evidence paths in manifests.
- Add exact staged-byte/hash assertions and shared malformed-package fixtures.
- Review gate: package validation, both language suites, actual-export verifier,
  gallery partition, and cleanup audit all pass; no unsupported remote sync or
  model editing is implied.

### Stage 5 — runtime and skill documentation

- Move shared pure suspension types/solver/render-layer construction to the
  model layer; leave compatibility wrappers and board-specific adapter code
  until call sites are migrated.
- Keep `BoardModelView`'s cache identity, scene/camera rebinding, accessibility,
  nearest-triangle picking, on-demand rendering, highlight semantics, and
  explicit unavailable state.
- Update `migrate-hangboard-to-3d/SKILL.md` and
  `Tools/HangboardModels/README.md` with the toolkit entry points, config
  contract, manifest/gallery workflow, and characterization gates. Preserve
  evidence and Astra routing language verbatim in intent.
- Review gate: run the first-migration iOS review route for each newly migrated
  board, including every hold/position, orbit/reset, active/clear/reappear,
  workout-driven position, cord continuity, and unavailable state.

## Compatibility contract

- **Package schema:** retain model-only v2 packages, exactly one USDZ and
  descriptor, hash-bound descriptor v1, `hang-ten-board-v1`, sorted IDs, and no
  raster fallback or hand-authored bounds.
- **Existing commands:** preserve compiler and verifier entrypoints and flags;
  wrappers may emit the shared report internally during a deprecation window.
- **Python/Swift parity:** retain closed-schema member order, duplicate-key
  detection, scalar-kind distinctions, explicit-null rejection, and shared
  fixture mutations.
- **Runtime:** retain `BoardModelScene` public behavior and error routing;
  typed enum switching is required for new profile consumers, with no silent
  single-to-two-branch widening.
- **Assets/staging:** recursive regular-file copying remains the production
  behavior; staged bytes and declared inventory must be exact. Do not add
  generated manifests or galleries inside the two-asset compiler package.
- **Geometry:** stable logical hold IDs and descriptor-derived frames remain
  the only rendering/highlighting/picking source of truth. Primitive extraction
  is not permission to retain raster paths or add compatibility bounds.

## Cost, risk, and mitigations

| Risk | Impact | Mitigation and owner |
| --- | --- | --- |
| Verifier extraction changes a failure category or silently weakens a check | Shipped invalid asset or misleading report | Stage 0 snapshots, adapter parity tests, fail-closed core framework; Luna owns routine tooling, Terra only after a bounded unresolved integration failure |
| Blender importer renames nodes or changes evaluated topology | Wrong descriptor bindings or missed geometry | Preserve source-piece correspondence on temporary export copies; compare actual imported nodes and vertices; never infer from names |
| Boolean/primitive refactor changes curvature or ligaments | Visual/physical fidelity regression | Semantic mesh snapshots plus clay/front/oblique/detail review; Astra owns final shape corrections |
| Python and Swift catenary math diverges | Cord discontinuity, collision, or different unavailable state | One declared constants/tolerance contract, shared mutation fixtures, repeated solve tests, actual-mesh clearance probes |
| Two-branch route is over-generalized | Wrong passage order or invented physical routing | Keep explicit two pairs/two branches/shared anchor and ordered passage IDs; board config supplies evidence-backed passage points |
| Shared config becomes a generic escape hatch | Board-specific exceptions bypass invariants | Core checks cannot be disabled; extension points are additive and typed |
| Canonical texture/material changes invalidate every model | Large rebuild and visual risk | Keep canonical source hash in manifests; use `rebuild_all_wood_models.py` with exact descriptor-geometry checks and controlled app-renderer review |
| Staging/galleries leak resources or overwrite user output | Workspace pollution or lost evidence | Owner-prefixed `.context` directories, exit traps, exact deletion verification, atomic staging, no shared-resource cleanup |
| Runtime compatibility facade lingers indefinitely | Duplicate implementations and drift | Track facade removal as a final Stage 5 gate after all callers use the shared types |

The expected cost is modest for configuration, fixtures, report, and parser
work (Luna). Blender/SceneKit integration is medium complexity and should be
escalated to Terra only when a bounded Luna attempt demonstrates non-routine
integration failure. Final physical geometry and fidelity judgments remain
exclusive to Astra after the approved evidence gate. No geometry worker may
change shape or cord estimates to mask a tooling failure.

## Acceptance checklist

The extraction is complete only when all of the following are true:

- Beastmaker, Compact, and the completed Flash migration each have a manifest,
  verifier config, retained evidence, and deterministic gallery/report output.
- Existing shipped model package bytes, descriptors, logical inventories,
  material payloads, and staging trees remain characterized and unchanged
  unless a separate approved rebuild explicitly changes them.
- Generic verification catches missing/malformed/hash-wrong/materialless/
  wrong-inventory/unbound/baked-hardware/nearest-hit defects after actual
  USDZ reimport.
- Single- and two-branch profiles share the typed contract and deterministic
  solver/rendering semantics, with all listed invalid states entering the
  explicit unavailable state.
- Python and Swift consume one malformed fixture matrix for parser/profile
  parity, including order, scalar-kind, duplicate-key, and explicit-null
  cases.
- Galleries contain the required front, oblique/opposite, clay/detail,
  active-hold, and canonical-position views with hashes and provenance.
- Package staging proves exact source-to-destination bytes and cleans all
  owned temporary resources.
- The migration skill and model tooling README describe this workflow without
  reintroducing image-driven geometry or unsupported remote/model-editing
  claims.

