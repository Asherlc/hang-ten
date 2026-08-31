# Hangboard Presentation Remediation Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair 65 Phase 1 presentation assets, remove only the unsupported Mini Bar end presentation while retaining all four physical grips, preserve 19 keep assets byte-for-byte, and prove the resulting 61-package/84-presentation catalog.

**Architecture:** A schema-version-2 manifest separates historical Phase 1 evidence from Phase 2 action state, a disposable 20-class canvas-capability preflight, transient input/output byte verification, acyclic production singular-baseline or cohort-bootstrap style comparison, product-scoped repair, direct Workbench geometry review, and per-presentation simulator evidence. Seven preflight tasks use only pre-Task-9 accepted keep assets plus live evidence to prove untouched output-canvas behavior without creating any production candidate or baseline; 45 product-scoped repair tasks then run sequentially inside four material/form-factor batches, followed by the sourced Mini Bar inventory/geometry change and complete catalog/iOS gates. Every implementation or configuration task uses a fresh subagent and is reviewed before the next task.

**Tech Stack:** Python 3.11.4+ standard library, pytest 9, existing `hangboard_packages` discovery/CLI, JSON, SHA-256 and PNG IHDR byte inspection, built-in `view_image` and `image_gen`, Hangboard Workbench, Swift/Xcode, `xcrun simctl`, and Markdown.

**Spec:** `docs/superpowers/specs/2026-08-30-hangboard-presentation-remediation-design.md`

## Global Constraints

- Execute Tasks 1–65 in order with `superpowers:subagent-driven-development`; `AGENTS.md` requires a fresh implementation subagent and separate controller spec/quality reviews per task. Do not parallelize tasks that share the manifest.
- Use `rtk` for shell commands. Commit and push every completed task, rejected-input/output provenance checkpoint, batch gate, and final gate.
- Preserve all 19 Phase 1 `keep` PNGs byte-for-byte. Their `board.json` files also remain byte-for-byte except `Hangboards/lattice-mini-bar/board.json`, which Task 59 must deliberately change to retain and reassign `mini-pinch` while removing only the unsupported end presentation.
- Implement exactly 17 edits and 48 regenerations. Task 59 performs the sole `removeUnsupportedPresentation`. The exclusive repair matrix assigns all 66 non-keep records exactly once; no later review creates another owner.
- Preserve literal/set validation of `packageIDs`: require unique identifiers and set equality to inventory without imposing or rewriting sorted order. Reports remain deterministically sorted.
- Preserve the Phase 1 `comparator` object unchanged as historical classification. Phase 2 uses the separate `phase2Comparator` lifecycle defined below; all reasons remain canonical style-only and never supply geometry.
- Before each canvas probe and product repair, freshly reopen every literal URL below the routed record's `/evidence/official` and `/evidence/independent` arrays, repeat every non-null evidence-gap search, inspect straight-on and oblique evidence, and record the actual date/result. Local docs, current assets, package geometry, comparators, prompts, and generated output are never product proof.
- Use only built-in `image_gen`, one call per candidate or canvas attempt. Never use the imagegen CLI/API fallback, `scripts/image_gen.py`, `OPENAI_API_KEY`, a destination-path or size argument, or batch generation.
- For built-in edits, inspect the local current target and every reference with `view_image`, then pass their exact paths via `referenced_image_paths`. For built-in generations, do not supply the current asset; supply only minimum copied official/independent inputs plus either one non-null ready singular style comparator or every non-null axis asset in a validator-approved bootstrap comparator set.
- Ruling: the first repair in a material/form-factor cohort with no accepted singular catalog baseline uses a pre-generation bootstrap comparator set made only from accepted catalog assets for each available style axis (same form factor for composition/framing/scale, same material family for texture/lighting when one exists), plus exact live official/independent material evidence and the shared render contract; none supplies geometry. After that first output passes evidence, Workbench, package, and visual review, it becomes the ready singular cohort baseline for acyclic downstream repairs. This is necessary because Phase 1 proves no accepted non-wood baseline exists; it costs stricter review of the first cohort asset and a potential rerender if the eventual cohort comparison exposes drift.
- Temporary gaps alone cannot authorize generation. A historical Phase 1 `baselineGap` remains evidence history only: it is never opened, never supplied, and never satisfies the Phase 2 comparator requirement.
- Canvas preflight is a capability-only exception, not generation authorization. Tasks 2–9 may use only the exact 17 pre-Task-9 source-supported accepted keeps as optional composition/framing references, never use a material comparator, and rely on freshly reopened official/independent evidence plus the shared material contract. Every probe output is permanently `capabilityProbeRejected`, separately recorded, and deleted; no preflight hash or path may enter production inputs, candidates, comparators, baselines, or accepted assets. Tasks 10+ still require the production singular-ready or exact nine-seed bootstrap contract without exception.
- Required dimensions and aspect ratio appear in the prompt because the built-in tool has no size field. Accept only untouched PNG output whose IHDR already matches exactly. Never crop, resize, rotate, pad, register, align, mask, composite, recolor, sharpen, smooth, trace, vectorize, simplify, detect, segment, or otherwise post-process a package candidate.
- A byte-preserving move or copy is allowed only to move untouched generated bytes, create an exact rollback copy, or restore exact original bytes after rejection. Accepted generated bytes end only at their declared package path. Source photographs never enter `Hangboards`.
- Preserve the common off-white studio background, centered orthographic working-surface view, neutral lighting, restrained contact shadows, clean antialiasing, cohort-consistent framing, and source-proved material cues. Omit unsupported facts instead of filling gaps.
- An `edit` uses the current PNG as target and topology/likeness invariant. A `regenerate` treats current bytes as human comparison only. A repair task leaves `board.json` byte-for-byte when deliberate Workbench review proves its paths correct; when primary evidence proves a mismatch, the same task directly redraws only the named path and records that terminal branch. No raster-derived geometry is allowed.
- Every changed presentation receives human side-by-side source/current/candidate/comparator review plus Workbench normal, all-active, every logical hold/piece, and hit-test review. Exact mirroring requires primary proof; a shape constraint is selected only by an operator for a genuinely regular hold.
- Each product task runs package validation and focused tests. Each material/form-factor batch gate runs the complete package test suite. Final validation runs all tests again.
- Phase 2 action blocking is distinct from historical evidence blocking. Final success requires zero blocked Phase 2 actions while retaining the two historical evidence-blocked keeps and every other Phase 1 evidence-gap value unchanged.
- No task changes training plans, timer behavior, unrelated metadata, product claims, or navigation. Do not infer materials, colors, finishes, components, dimensions, contacts, usable faces, grip guidance, or coaching claims.

## Files and responsibilities

- `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`: schema 2, prompt rendering, canvas coverage, source/candidate byte verification, comparator DAG, partial/final lifecycle, removal truth, and per-presentation simulator truth.
- `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`: exact schema/lifecycle/hash/comparator/canvas/removal/simulator tests.
- `Tools/HangboardPackages/src/hangboard_packages/cli.py`, `Tools/HangboardPackages/tests/test_cli.py`, `Tools/HangboardPackages/README.md`: Phase 2 CLI flags and durable/transient semantics.
- `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`: sole machine ledger; original record order, decisions, `currentAsset`, evidence, findings, and Phase 1 comparator values remain historical.
- `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`: batch/source/candidate/geometry/validation narrative.
- `Hangboards/*`: only the exclusive task owner changes its declared PNG; `board.json` follows the exact Workbench branch above. Task 59 alone removes a presentation asset and reassigns a physical hold.

## Complete Phase 2 schema and interfaces

The root is closed over exactly `schemaVersion`, `phase`, `reviewDate`, `packageIDs`, `records`, `phase1Checks`, and `phase2`. Schema 2 requires `schemaVersion: 2` and `phase: "assetRemediation"`; it preserves the other five Phase 1 root fields literally.

`phase2` is closed over:

```json
{
  "canvasPreflight": {
    "status": "pending",
    "blockedReason": null,
    "classes": []
  },
  "capabilityProbeCheck": {
    "artifacts": []
  },
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
```

All check objects are closed over `status` and `evidence`. `status` is `pending`, `passed`, `failed`, `blocked`, or `notRequired`. Only `pending` uses null evidence. `notRequired` requires a nonempty factual reason.

Each batch is closed over `id`, `order`, `kind`, `recordKeys`, `status`, `blockedReason`, and `checks`. `kind` is `repair` or `removal`; `status` is `pending`, `inProgress`, `passed`, or `blocked`; `checks` contains exactly `packageValidation`, `focusedTests`, and `fullPackageSuite`. Statuses form a prefix: passed batches, at most one in-progress/blocked batch, then pending batches. A passed batch owns only completed actions and three passed checks.

Every record adds these closed fields:

```json
{
  "repairBatchID": null,
  "phase2Action": {
    "state": "notRequired",
    "blockedReason": null
  },
  "phase2EvidenceReview": {
    "result": "notRequired",
    "reviewedAt": null,
    "officialURLsReopened": [],
    "independentURLsReopened": [],
    "evidenceGapSearchesRepeated": [],
    "notes": "Phase 1 keep; Phase 2 product repair does not apply."
  },
  "phase2Comparator": {
    "generationTime": null,
    "bootstrapComparatorSet": null,
    "final": null
  }
}
```

`phase2Action.state` is `notRequired`, `pending`, `inProgress`, `completed`, or `blocked`. Only blocked has a non-null reason. Keeps require `notRequired`; non-keeps never use it. For `phase2EvidenceReview`, not-required keeps have null time, empty URL/search arrays, and the exact note `Phase 1 keep; Phase 2 product repair does not apply.`; pending actions have null time, empty arrays, and `Phase 2 evidence review pending.`; confirmed/blocked reviews have an aware timestamp and nonempty factual notes. Completed Phase 2 actions require `confirmed`; an evidence failure requires both result/action `blocked` and the same nonempty reason in notes. Confirmed `officialURLsReopened` and `independentURLsReopened` preserve literal URL order and exactly equal their corresponding historical evidence URL arrays. `evidenceGapSearchesRepeated` has one result string per non-null Phase 1 gap leaf and is empty when both gap leaves are null. Gap searches are added Phase 2 audit text without changing any Phase 1 gap field.

Keeps and the removal record require all three `phase2Comparator` leaves null. Every edit/regenerate record takes exactly one mutually exclusive pre-generation path: a non-null `generationTime` ready singular comparator with null `bootstrapComparatorSet`, or a non-null selected `bootstrapComparatorSet` with null `generationTime`. Null/null is forbidden once image generation begins. A historical Phase 1 comparator gap is never a third path.

`phase2Comparator.generationTime` is closed over `mode`, `assetPath`, `sourceRecordKey`, `acceptedAssetSHA256`, `reason`, and `selectedAt`; generation-time mode is only `readyBaseline`. Its asset is either one of the 17 source-supported Phase 1 keeps at order 0 or a completed strictly earlier repair. It must match the exact form factor and at least one material token, have an accepted visual decision, and preserve an acyclic dependency graph. Its reason is exactly `Accepted singular style baseline: framing, scale, background, lighting, texture frequency, smoothing, and edge treatment only; no product geometry.`

`phase2Comparator.bootstrapComparatorSet` is permitted only for the exact nine seed rows in the ordering table below. Before generation it has `status: selected`, passed evidence review, and pending visual/Workbench/package review. Candidate acceptance writes visual passed; completed four-mode Workbench inspection writes Workbench passed; an actual package-validation exit 0 writes package passed. Only then does it transition to `acceptedCohortBaseline`. It never becomes accepted merely because bytes were generated. A blocked source, candidate, Workbench, package, or visual result transitions it to `blocked` with the same reason as `phase2Action`, and no downstream cohort row may start.

For edit/regenerate records, `phase2Comparator.final` is null until completion. A normal downstream completion uses `readyBaseline` and preserves the selected singular asset/key/hash. A seed completion uses `cohortBootstrapBaseline`, names its own accepted asset/key/hash, and uses exactly `Accepted cohort bootstrap baseline after direct evidence, Workbench, package, and visual review; style-only for downstream use, no geometry.` No other self-reference is legal. Comparator hashes must equal the applicable accepted on-disk bytes.

The schema uses these exact scalar aliases; every object below is closed and rejects extra keys:

```python
SHA256 = str              # regex: ^[0-9a-f]{64}$
ISOInstant = str          # aware datetime.fromisoformat succeeds, has UTC offset, and round-trips
NonEmpty = str            # value.strip() is nonempty
RecordKey = str           # exact "packageID/presentationID"
CheckStatus = Literal["pending", "passed", "failed", "blocked", "notRequired"]
ActionState = Literal["notRequired", "pending", "inProgress", "completed", "blocked"]
EvidenceResult = Literal["notRequired", "pending", "confirmed", "blocked"]
InputType = Literal["officialEvidence", "independentEvidence", "currentAsset", "comparator"]
ByteStatus = Literal["pending", "passed", "failed"]
GenerationMode = Literal["none", "builtInEdit", "builtInGenerate"]
CandidateDisposition = Literal["accepted", "rejected"]
ComparatorMode = Literal["readyBaseline", "cohortBootstrapBaseline"]
BootstrapStatus = Literal["selected", "acceptedCohortBaseline", "blocked"]
BootstrapAxisName = Literal["compositionFramingScale", "materialTextureLighting"]
SimulatorState = Literal[
    "pending", "passedDirectInspection", "notApplicableRemovedPresentation", "blocked"
]
FlowState = Literal[
    "passed", "notApplicableSinglePresentation", "notApplicableNoCompatiblePlan", "blocked"
]
```

The nested generation types are exactly:

```python
class ByteVerification(TypedDict):
    status: ByteStatus
    checkedAt: ISOInstant | None
    command: NonEmpty | None
    observedSHA256: SHA256 | None

class GenerationSourceInput(TypedDict):
    id: NonEmpty
    sourceType: InputType
    evidencePointer: str | None
    sourceURL: str | None
    assetPath: str | None
    role: NonEmpty
    sha256: SHA256
    suppliedToImagegen: bool
    byteVerification: ByteVerification

class RequiredCanvas(TypedDict):
    widthPixels: int
    heightPixels: int

class CandidateProvenance(TypedDict):
    tool: Literal["builtInImageGen"]
    untouchedModelOutput: Literal[True]
    postProcessing: Literal["none"]

class GenerationCandidate(TypedDict):
    attempt: Literal[1, 2, 3]
    transientOutputPath: str
    sha256: SHA256
    widthPixels: int
    heightPixels: int
    disposition: CandidateDisposition
    reason: NonEmpty
    provenance: CandidateProvenance
    byteVerification: ByteVerification

class Generation(TypedDict):
    mode: GenerationMode
    prompt: str | None
    requiredCanvas: RequiredCanvas | None
    sourceInputs: list[GenerationSourceInput]
    currentAssetRole: str | None
    candidates: list[GenerationCandidate]
```

The remaining record/root additions are exactly:

```python
class ReviewCheck(TypedDict):
    status: CheckStatus
    evidence: NonEmpty | None

class Phase2Action(TypedDict):
    state: ActionState
    blockedReason: NonEmpty | None

class Phase2EvidenceReview(TypedDict):
    result: EvidenceResult
    reviewedAt: ISOInstant | None
    officialURLsReopened: list[str]
    independentURLsReopened: list[str]
    evidenceGapSearchesRepeated: list[NonEmpty]
    notes: NonEmpty

class ComparatorSelection(TypedDict):
    mode: ComparatorMode
    assetPath: str
    sourceRecordKey: RecordKey
    acceptedAssetSHA256: SHA256
    reason: NonEmpty
    selectedAt: ISOInstant

class BootstrapComparatorAxis(TypedDict):
    axis: BootstrapAxisName
    assetPath: str
    sourceRecordKey: RecordKey
    acceptedAssetSHA256: SHA256
    matchedMaterialTokens: list[NonEmpty]
    reason: NonEmpty

class BootstrapReviewChecks(TypedDict):
    evidenceReview: ReviewCheck
    visualReview: ReviewCheck
    workbenchReview: ReviewCheck
    packageValidation: ReviewCheck

class BootstrapComparatorSet(TypedDict):
    cohortID: Literal[
        "moldedPlastic/fullWidthFixedBoard",
        "resin/fullWidthFixedBoard",
        "urethane/fullWidthFixedBoard",
        "urethane/splitFixedBoard",
        "wood/splitFixedBoard",
        "wood/reversiblePortable",
        "wood/liftingEdge",
        "resin/suspendedPortable",
        "urethane/multiOrientationDevice",
    ]
    seedRecordKey: RecordKey
    status: BootstrapStatus
    compositionFramingScale: BootstrapComparatorAxis | None
    materialTextureLighting: BootstrapComparatorAxis | None
    absentAxes: list[BootstrapAxisName]
    officialEvidenceInputIDs: list[NonEmpty]
    independentEvidenceInputIDs: list[NonEmpty]
    sharedRenderContract: Literal[
        "Common off-white studio background; centered orthographic working-surface view; "
        "complete uncropped product; neutral lighting; restrained contact shadows; "
        "clean antialiasing; cohort-consistent framing; source-proved material cues only."
    ]
    selectionRule: Literal[
        "Accepted assets only: earliest exact-form-factor asset for composition/framing/scale; "
        "earliest asset sharing the seed material-family token for texture/lighting; "
        "missing axes are explicit; no axis supplies product geometry."
    ]
    selectedAt: ISOInstant
    acceptedAt: ISOInstant | None
    reviewChecks: BootstrapReviewChecks
    blockedReason: NonEmpty | None

class Phase2Comparator(TypedDict):
    generationTime: ComparatorSelection | None
    bootstrapComparatorSet: BootstrapComparatorSet | None
    final: ComparatorSelection | None

class PreflightCompositionReference(TypedDict):
    axis: Literal["compositionFramingScale"]
    assetPath: str
    sourceRecordKey: RecordKey
    acceptedAssetSHA256: SHA256
    reason: Literal[
        "Pre-Task-9 accepted keep used only for disposable capability-probe "
        "composition, framing, and scale; no material or product geometry transfer."
    ]

class PreflightComparatorSet(TypedDict):
    mode: Literal["preflightCapabilityOnly"]
    compositionFramingScale: PreflightCompositionReference | None
    materialTextureLighting: Literal[None]
    unavailableAxes: list[BootstrapAxisName]
    officialEvidenceInputIDs: list[NonEmpty]
    independentEvidenceInputIDs: list[NonEmpty]
    sharedMaterialContract: Literal[
        "Material appearance comes only from freshly reopened official/independent evidence; "
        "the shared render contract supplies neutral lighting and no material comparator."
    ]
    productionAuthorization: Literal["forbidden"]
    selectedAt: ISOInstant

class CapabilityProbeArtifact(TypedDict):
    id: NonEmpty
    behaviorProbeID: NonEmpty
    attempt: Literal[1, 2, 3]
    returnedOutputPath: str
    transientOutputPath: str
    sha256: SHA256
    widthPixels: int
    heightPixels: int
    canvasResult: Literal["exactCanvas", "wrongCanvas"]
    disposition: Literal["capabilityProbeRejected"]
    productionUse: Literal["forbidden"]
    reason: NonEmpty
    provenance: CandidateProvenance
    byteVerification: ByteVerification
    recordedAt: ISOInstant
    deletionVerifiedAt: ISOInstant | None

class CapabilityProbeCheck(TypedDict):
    artifacts: list[CapabilityProbeArtifact]

class CanvasBehaviorProbe(TypedDict):
    id: NonEmpty
    behavior: Literal["edit", "generate"]
    representativeRecordKey: RecordKey
    prompt: NonEmpty
    sourceInputs: list[GenerationSourceInput]
    preflightComparatorSet: PreflightComparatorSet
    artifactIDs: list[NonEmpty]
    status: Literal["pending", "passed", "blocked"]
    blockedReason: NonEmpty | None

class CanvasClass(TypedDict):
    widthPixels: int
    heightPixels: int
    coveredRecordKeys: list[RecordKey]
    status: Literal["pending", "passed", "blocked"]
    blockedReason: NonEmpty | None
    behaviorProbes: list[CanvasBehaviorProbe]

class CanvasPreflight(TypedDict):
    status: Literal["pending", "passed", "blocked"]
    blockedReason: NonEmpty | None
    classes: list[CanvasClass]

class BatchChecks(TypedDict):
    packageValidation: ReviewCheck
    focusedTests: ReviewCheck
    fullPackageSuite: ReviewCheck

class RemediationBatch(TypedDict):
    id: Literal["nonwood-fixed", "wood-fixed", "portable", "multi-orientation", "mini-bar-removal"]
    order: Literal[1, 2, 3, 4, 5]
    kind: Literal["repair", "removal"]
    recordKeys: list[RecordKey]
    status: Literal["pending", "inProgress", "passed", "blocked"]
    blockedReason: NonEmpty | None
    checks: BatchChecks

class Phase2FinalChecks(TypedDict):
    crossCatalogReview: ReviewCheck
    manifestValidation: ReviewCheck
    finalInventory: ReviewCheck
    packageTestSuite: ReviewCheck
    buildForTesting: ReviewCheck
    simulatorReview: ReviewCheck
    contextCleanup: ReviewCheck

class Phase2Root(TypedDict):
    canvasPreflight: CanvasPreflight
    capabilityProbeCheck: CapabilityProbeCheck
    batches: list[RemediationBatch]
    finalChecks: Phase2FinalChecks
```

The five batches occur once in the literal enum order. Their `recordKeys` are exactly the exclusive matrix rows owned by Tasks 10–26, 28–38, 40–49, 51–57, and Task 59 respectively; the removal batch has only `lattice.mini-bar/end`. A repair row's `repairBatchID` equals its batch ID, the removal row equals `mini-bar-removal`, and every keep uses null. No record may appear in two batch lists.

The following bootstrap contract is production-only and begins at Task 10; Tasks 2–9 cannot instantiate, validate, or consume it. Production bootstrap selection uses an exact `baselineOrder`: source-supported Phase 1 keeps sort as `(0, recordIndex)`; accepted repaired assets sort as `(owningTaskNumber, recordIndex)`. An accepted asset is eligible only after its visual decision, four Workbench checks, and package validation pass. The composition axis selects the first eligible exact-form-factor asset without requiring a material match. The material axis selects the first eligible asset sharing the cohort's literal material-family token without requiring a form-factor match. Neither axis can be the seed record before it is accepted; neither reason may mention topology, holds, contacts, dimensions, component count, or silhouette. The exact axis reasons are:

- Composition: `Style axis only: composition, framing, scale, background, and lighting balance from an accepted exact-form-factor catalog asset; no product geometry or material transfer.`
- Material: `Style axis only: texture frequency, finish restraint, and lighting response for the matched material-family token; no product geometry or component transfer.`

The seed order and selected pre-generation axes are fixed:

| Owning task / cohort | Seed record | Composition/framing/scale axis | Material texture/lighting axis | Exact absent axes before generation |
| --- | --- | --- | --- | --- |
| Task 10 `moldedPlastic/fullWidthFixedBoard` | `escape-beta-22/primary` | `beastmaker-2000/primary` | null | `materialTextureLighting` |
| Task 11 `resin/fullWidthFixedBoard` | `evolv-kilter-basic-long/primary` | `beastmaker-2000/primary` | null | `materialTextureLighting` |
| Task 16 `urethane/fullWidthFixedBoard` | `soill.iron-palm-2/primary` | `beastmaker-2000/primary` | null | `materialTextureLighting` |
| Task 17 `urethane/splitFixedBoard` | `soill.split-palm/primary` | null | `soill.iron-palm-2/primary` | `compositionFramingScale` |
| Task 34 `wood/splitFixedBoard` | `trango.rock-prodigy-natural/primary` | `soill.split-palm/primary` | `beastmaker-2000/primary` | none |
| Task 40 `wood/reversiblePortable` | `captain-fingerfood.dual/primary` | null | `beastmaker-2000/primary` | `compositionFramingScale` |
| Task 46 `wood/liftingEdge` | `lattice.mxedge-lift-large/primary` | null | `beastmaker-2000/primary` | `compositionFramingScale` |
| Task 48 `resin/suspendedPortable` | `metolius.rock-rings-3d/front-pair` | null | `evolv-kilter-basic-long/primary` | `compositionFramingScale` |
| Task 54 `urethane/multiOrientationDevice` | `trango.rock-prodigy-pivot/orientation-1` | `lattice.mini-bar/primary` | `soill.iron-palm-2/primary` | none |

Task 10 is the first non-wood seed. Its accepted Beastmaker wood asset governs only composition/framing/scale. Its material axis is explicitly absent; exact live Escape evidence and the shared render contract govern molded-plastic material. The validator rejects any Task 10 reason or prompt that implies wood governs plastic texture, finish, construction, or geometry. The same absent-axis rule applies to Tasks 11 and 16 for resin and urethane. After each seed reaches `acceptedCohortBaseline`, every later compatible row must use that seed as its singular ready baseline; a second bootstrap in the same cohort is invalid.

Evidence inputs require their exact `/records/N/evidence/official/I` or `/records/N/evidence/independent/I` pointer, the byte-for-byte URL at that leaf, null `assetPath`, and a `role` equal to that leaf's `imageRole`. Current/comparator inputs require null pointer/URL and their declared package path. A `current-target` hash equals historical `currentAsset.sha256`; `style-comparator`, `bootstrap-composition`, and `bootstrap-material` hashes equal their selected comparator records. All must match bytes when transient verification runs, but durable validation uses that committed verification because the target or an upstream baseline may later change. Input IDs are unique within a record and equal `official-I-image-J`, `independent-I-image-J`, `current-target`, `style-comparator`, `bootstrap-composition`, or `bootstrap-material`, with zero-based evidence/image ordinals in source-page order. A supplied evidence input must have been copied from the corresponding freshly reopened URL. Edit requires one supplied `current-target`; regenerate prohibits it. A singular-baseline generation requires exactly one supplied `style-comparator`. A bootstrap generation requires one supplied input for each non-null bootstrap axis, no `style-comparator`, and at least one official/independent evidence input; a null axis supplies no path and appears in `absentAxes`. The exact current roles are `Built-in edit target and topology/likeness invariant.` and `Human comparison only; not evidence and not supplied to imagegen.`

Preflight probe inputs use the same closed input shape but a separate ID set: evidence IDs retain the production format, an edit probe alone may use `current-target`, and a non-null assigned composition reference requires exactly `preflight-composition`. `style-comparator`, `bootstrap-composition`, and `bootstrap-material` are forbidden in preflight. A generate probe has no current target. Every probe supplies live evidence; `preflight-composition` is optional exactly as the 22-row table declares; no material input exists.

Pending byte verification has all three remaining values null. Passed/failed verification has a date, the literal command executed, and the observed hash; passed additionally requires observed/declared equality. Before deletion, every copied input and candidate requires passed verification. Durable validation checks the record, URL/role/hash linkage, and passed command/result; it never requires deleted transient bytes to exist.

`mode: none` requires null prompt/canvas/current role and empty inputs/candidates. The two production image modes require positive canvas dimensions equal to original `currentAsset`, a non-null canonical prompt, the applicable exact current role, and exactly one lawful production comparator path above. Candidate attempts are unique, strictly increasing, bounded 1–3, and record their deterministic transient output path. Every candidate requires built-in/untouched/none provenance and passed transient verification before deletion or promotion. Completed edits/regenerations have exactly one accepted candidate; its hash/dimensions equal final/on-disk bytes. Rejected bytes may be absent only after their passed verification/provenance was committed and pushed. No path/hash in `phase2.capabilityProbeCheck.artifacts` may equal or appear in any production candidate, source input, comparator axis/selection, baseline, or final accepted asset.

Canvas preflight classes are closed over `widthPixels`, `heightPixels`, `coveredRecordKeys`, `status`, `blockedReason`, and `behaviorProbes`. Each behavior probe is closed over its ID, behavior (`edit` or `generate`), representative key, exact disposable prompt, source inputs, preflight-only comparator set, artifact IDs, status, and blocked reason. It cannot contain `bootstrapComparatorSet`, production comparator fields, or production generation candidates. Its optional composition reference must be the exact table-selected asset from the 17 pre-Task-9 source-supported accepted keeps; its material axis is always null and explicitly unavailable. Live evidence and the closed shared material contract are mandatory for every probe. Edit probes may supply the representative current asset solely as the built-in edit target, never as a style reference or accepted input. A pending probe has zero to three in-progress artifact IDs; a passed/blocked probe has one to three IDs in exact attempt order. Each ID equals the probe's literal `id`, followed by `-attempt-`, followed by its decimal attempt number; it resolves to exactly one root artifact with matching `behaviorProbeID`/attempt, and every root artifact is referenced by exactly one probe.

Every built-in probe result is recorded only in root `phase2.capabilityProbeCheck.artifacts`, always with `disposition: capabilityProbeRejected` and `productionUse: forbidden`, regardless of whether its IHDR is exact. It records both the built-in returned absolute path and the deterministic context path, is hash/byte-verified, committed as a transient checkpoint, deleted through the persistent cleanup session, then updated with non-null `deletionVerifiedAt`; a terminal probe requires both paths absent. Only untouched provenance plus IHDR width/height determine `canvasResult`: `exactCanvas` passes the behavior and `wrongCanvas` permits the next prompt-only attempt, up to three. Product likeness, material fidelity, composition quality, and visual preference are not preflight pass criteria and can never turn an artifact into an accepted output. Artifacts are never stored in any record's `generation.candidates`, never promoted, and never seed or satisfy any production baseline. Root preflight passes only when 20 unique classes cover the exact 65 edit/regenerate keys once, all 22 behavior probes pass, every referenced artifact is terminal/deleted, and artifact hashes/all recorded paths are disjoint from every production record field listed above. `PHASE2_PREFLIGHT`, `PHASE2_PARTIAL`, and `PHASE2_FINAL` all rerun the same disjointness rule so a later production task cannot reuse an earlier preflight artifact.

`final` is closed over `acceptedAssetSHA256`, `finalDimensions`, `visualReviewerDecision`, `workbenchReview`, and `validation`. The 17 source-supported keeps preserve their existing non-null accepted hash, dimensions, and `acceptedCurrentAsset` decision; each hash equals both `currentAsset.sha256` and the unchanged on-disk PNG. Only the two historical evidence-blocked keeps preserve null hash/dimensions and `blockedEvidence`. Pending repairs and removal use null hash/dimensions; completed image repairs use accepted on-disk values and `acceptedPhase2`; a Phase 2 action block uses `blockedPhase2`; Task 59 uses `removedUnsupportedPresentation`. `finalDimensions` is the exact `RequiredCanvas` shape. `workbenchReview` contains exactly `normal`, `allActive`, `individualHolds`, and `hitTest`, each an exact check object. Completed image repairs require all four passed. Removal uses four passed checks after reauthoring `mini-pinch`; it is not visually `notRequired`. Keep records preserve their three existing Phase 1 pending Workbench checks, add `hitTest: notRequired` with factual Phase 2 evidence, and are exempt from repaired-record terminal checks.

`final.validation` is closed over `packageValidation`, `focusedTests`, `fullPackageSuite`, `buildForTesting`, and `simulatorReview`. The first four are exact check objects. `simulatorReview` uses these exact nested types:

```python
class SimulatorFlows(TypedDict):
    catalog: FlowState
    plan: FlowState
    normal: FlowState
    active: FlowState
    individualHold: FlowState
    presentationSelector: FlowState
    hitTest: FlowState

class SimulatorDeviceRun(TypedDict):
    deviceClass: Literal["phone", "tablet"]
    simulatorUUID: NonEmpty
    captureSHA256s: list[SHA256]
    flows: SimulatorFlows

class SimulatorReview(TypedDict):
    state: SimulatorState
    reviewedAt: ISOInstant | None
    environmentEvidenceIDs: list[NonEmpty]
    deviceRuns: list[SimulatorDeviceRun]
```

Per-record propagation is command-ordered and fail-closed. A product task writes its record's `packageValidation` passed only after the literal package validator exits 0, then writes `focusedTests` passed only after the literal focused pytest command exits 0. A batch gate writes `fullPackageSuite` passed to every changed record in that batch only after the complete HangboardPackages suite exits 0; its batch-level package/focused checks aggregate already-passed per-record evidence and its full-suite check cites that actual gate command. Tasks 61–64 write `buildForTesting` passed to every changed record covered by their build only after the bounded build exits 0. They write `simulatorReview` record-by-record only after that exact presentation's direct phone/tablet exercise completes. Task 64 also writes the removal record's `buildForTesting` from the final catalog build while retaining its sourced simulator N/A. No task may prewrite `passed`, reuse a later command result, or promote a batch/root status before the underlying record evidence exists.

Only pending simulator review has null date and empty evidence/runs. Direct inspection has a date, nonempty environment IDs, exactly one phone and one tablet run, unique UUIDs, and nonempty capture hashes. Only selector may use `notApplicableSinglePresentation`; only plan may use `notApplicableNoCompatiblePlan`; all other applicable flows pass. Blocked has a date and evidence that agrees with the Phase 2 action's block reason. Removal uses `notApplicableRemovedPresentation`, a date and sourced removal evidence, and no device runs. Shared environment evidence does not replace per-record runs. Keeps retain pending simulator review because Phase 2 does not exercise them per-record; the root cross-catalog check records their direct cohort inspection without rewriting a keep record's pending Phase 1 validation fields.

The public interfaces are exact:

```python
class PresentationValidationMode(str, Enum):
    SOURCE_RECLASSIFICATION = "sourceReclassification"
    PHASE2_PREFLIGHT = "phase2Preflight"
    PHASE2_PARTIAL = "phase2Partial"
    PHASE2_FINAL = "phase2Final"


def render_phase2_generation_prompt(
    record: PresentationRemediationRecord,
) -> str:
    """Return the canonical prompt assembled from the record's literal Phase 2 fields."""


def render_phase2_capability_probe_prompt(
    probe: CanvasBehaviorProbe,
    required_canvas: RequiredCanvas,
) -> str:
    """Return the disposable preflight-only prompt; never production authorization."""


def verify_transient_source_files(
    manifest: PresentationRemediationManifest,
    source_files: Mapping[str, Path],
) -> tuple[str, ...]:
    """Verify supplied source-input SHA keys against temporary bytes."""


def verify_transient_candidate_files(
    manifest: PresentationRemediationManifest,
    candidate_files: Mapping[str, Path],
) -> tuple[str, ...]:
    """Verify supplied candidate SHA keys against temporary PNG bytes and IHDR."""


def validate_presentation_remediation_manifest(
    manifest: PresentationRemediationManifest,
    inventory: BoardInventory,
    *,
    hangboards_root: Path,
    selected_package_ids: frozenset[str] = frozenset(),
    final_validation: bool = False,
    validation_mode: PresentationValidationMode = PresentationValidationMode.SOURCE_RECLASSIFICATION,
    selected_batch_id: str | None = None,
    transient_source_files: Mapping[str, Path] | None = None,
    transient_candidate_files: Mapping[str, Path] | None = None,
) -> PresentationRemediationReport:
    """Validate historical, preflight, partial, or final catalog truth."""
```

CLI keeps `--final-validation` for Phase 1 and adds mutually exclusive `--phase2-preflight`, `--phase2-partial`, and `--phase2-final`; `--batch-id` is partial-only; repeated `--source-file SHA256 PATH` and `--candidate-file SHA256 PATH` are preflight/partial-only. In preflight mode, `--candidate-file` can verify only a hash/path already declared in `capabilityProbeCheck.artifacts`; in partial mode it can verify only a production `generation.candidates` hash/path. The report adds `phase`, `batchID`, `canvasClassCount`, `canvasCoveredRepairCount`, `capabilityProbeArtifactCount`, `historicalEvidenceBlockedKeeps`, `blockedPhase2ActionCount`, `originalPresentationCount`, `inventoryPresentationCount`, `keptPresentationCount`, `completedEditCount`, `completedRegenerationCount`, `completedRemovalCount`, and `pendingPhase2ActionCount`.

Partial mode validates every record and current byte state: the 17 accepted keeps retain accepted hash/dimensions/decision equal to unchanged bytes; the two evidence-blocked keeps retain null hash/dimensions; pending/in-progress repair actions remain at original bytes; completed repairs match accepted bytes; completed removal matches historical-record/absent-presentation truth. It accepts historical evidence gaps without reclassifying them as Phase 2 blocks. Final mode requires passed preflight, all batches/final checks passed, 61 packages, 85 historical records, 84 current presentations, 19 unchanged keeps including two historical evidence-blocked keeps, 17 completed edits, 48 completed regenerations, one completed removal, zero pending Phase 2 actions, and zero blocked Phase 2 actions. It requires terminal per-record validation only for the 65 repaired records and the removal record; keep records retain the truthful pending/not-required Phase 1/Phase 2 states defined above.

## Canonical prompt transformation

`render_phase2_generation_prompt` joins arrays in stored order and must return these labeled lines with literal values, not JSON pointers:

```text
Use case: precise-object-edit OR product-mockup, selected from generation.mode
Asset type: Hang Ten package presentation PNG at the record's assetPath
Primary request: edit OR regenerate the exact productName, physicalRevision, and workingSurface
Input images: one semicolon-separated item per supplied sourceInputs entry: id, sourceType, role, sourceURL or assetPath
Scene/backdrop: common off-white studio background; no wall or mounting scenery
Subject: exact supportedClaim text from every reopened evidence entry, in manifest order
Style/medium: original simplified unbranded catalog product render, not a photograph
Composition/framing: orthographic head-on to workingSurface; centered; complete uncropped product; untouched output canvas exactly widthPixels by heightPixels
Lighting/mood: neutral direction; restrained contact shadow; controlled depth relief
Materials/textures: materials joined with " + "; preserve only evidence-supported finish and construction cues
Repair findings: finding-key and explanation for every nonconforming or uncertain finding, in the fixed seven-key order
Comparator: either literal singular ready asset/hash/canonical reason, or bootstrap cohort/status plus each composition/material axis asset/hash/reason and each explicit absent axis
Bootstrap material ruling: for a missing material axis, exact live material evidence and the shared render contract govern material; a composition asset never governs material or geometry
Current asset role: exact currentAssetRole
Constraints: preserve every source-proved contact, component, silhouette, and usable-surface orientation; add no unsupported detail; output must already have exact dimensions
Avoid: branding, labels, logos, text, watermark, transparent background, camera tilt, source-photo styling, invented contacts, invented hardware, and every forbidden post-processing operation
```

Edits use `precise-object-edit`; regenerations use `product-mockup`. The validator reconstructs this string and rejects any manifest prompt mismatch.

`render_phase2_capability_probe_prompt` is separate and may be used only in `PHASE2_PREFLIGHT`. It returns exactly these labeled lines from the closed probe object:

```text
Purpose: disposable image-tool exact-canvas capability probe; never a production candidate, comparator, baseline, or accepted asset
Behavior: edit-capability OR generate-capability
Representative: literal representativeRecordKey; identity cues come only from freshly reopened official/independent evidence
Input images: ordered evidence IDs/roles/URLs; for edit-capability only, the current target is tool input but not evidence or style reference
Scene/backdrop: common off-white studio background; no wall or mounting scenery
Composition reference: literal accepted pre-Task-9 keep asset/key/hash/reason, or unavailable
Material reference: unavailable; live evidence and the shared material contract govern material appearance
Material contract: Material appearance comes only from freshly reopened official/independent evidence; the shared render contract supplies neutral lighting and no material comparator.
Canvas request: untouched PNG output exactly widthPixels by heightPixels
Disposition: every returned output is capabilityProbeRejected and must be hashed, recorded separately, and deleted
Production authorization: forbidden
Avoid: branding, labels, logos, text, watermark, transparent background, camera tilt, invented product detail, and every post-processing operation
```

The validator reconstructs this string exactly, requires at least one freshly reopened official/independent evidence input, and rejects production prompt labels or any production `readyBaseline`, `bootstrapComparatorSet`, comparator reason, or cohort status in it.

## Exact ownership, transient verification, and cleanup recipe

Every preflight and product task uses a persistent cleanup PTY for the entire task. It does not rely on a trap in a short-lived setup command. Variables use task-specific names and never declare or repurpose `HOME`, `home`, or `CODEX_HOME`.

Before browsing, generation, Workbench launch, or source copying, assign `phase2_context_path` to the task's literal absolute context directory from its Interfaces line and create that exact directory plus the children `inputs`, `candidates`, and `review`. With `apply_patch`, append the literal filenames `OWNER-sincere-otter`, `owned-resources.tsv`, and `phase2-cleanup.zsh` to `phase2_context_path` and create those exact files. The owner file contains exactly `sincere-otter`; the ledger header is exactly `state<TAB>absolute_path<TAB>sha256<TAB>promoted_destination`. The cleanup script content is exactly:

```zsh
#!/bin/zsh
set -u
setopt extendedglob

phase2_cleanup_script_path="${0:A}"
phase2_cleanup_context_path="${phase2_cleanup_script_path:h}"
phase2_cleanup_workspace_path="${phase2_cleanup_context_path:h:h}"
phase2_cleanup_ledger_path="$phase2_cleanup_context_path/owned-resources.tsv"
phase2_cleanup_owner_path="$phase2_cleanup_context_path/OWNER-sincere-otter"
phase2_cleanup_complete=0
typeset -A phase2_cleanup_states phase2_cleanup_hashes phase2_cleanup_destinations

[[ "${phase2_cleanup_workspace_path:t}" == "sincere-otter" ]] || exit 64
[[ "${phase2_cleanup_context_path:h}" == "$phase2_cleanup_workspace_path/.context" ]] || exit 64
[[ "${phase2_cleanup_context_path:t}" == sincere-otter-* ]] || exit 64
[[ "$(<"$phase2_cleanup_owner_path")" == "sincere-otter" ]] || exit 64
[[ "$(rtk head -n 1 "$phase2_cleanup_ledger_path")" == $'state\tabsolute_path\tsha256\tpromoted_destination' ]] || exit 64

phase2_cleanup_hash_file() {
  rtk shasum -a 256 "$1" | rtk awk '{print $1}'
}

phase2_cleanup_append() {
  print -r -- "$1"$'\t'"$2"$'\t'"$3"$'\t'"$4" >> "$phase2_cleanup_ledger_path"
  phase2_cleanup_states[$2]="$1"
  phase2_cleanup_hashes[$2]="$3"
  phase2_cleanup_destinations[$2]="$4"
}

phase2_cleanup_validate_owned_path() {
  case "$1" in
    "$phase2_cleanup_context_path"/*|/Users/asherlc/.codex/generated_images/*) return 0 ;;
    *) return 1 ;;
  esac
}

phase2_cleanup_register() {
  local phase2_register_path="${1:A}"
  phase2_cleanup_validate_owned_path "$phase2_register_path" || return 65
  [[ -f "$phase2_register_path" && ! -L "$phase2_register_path" ]] || return 66
  [[ -z "${phase2_cleanup_states[$phase2_register_path]-}" ]] || return 67
  local phase2_register_hash="$(phase2_cleanup_hash_file "$phase2_register_path")" || return 68
  [[ "$phase2_register_hash" == [0-9a-f]## && ${#phase2_register_hash} -eq 64 ]] || return 68
  phase2_cleanup_append registered "$phase2_register_path" "$phase2_register_hash" -
  print -r -- "ACK"$'\t'"REGISTER"$'\t'"$phase2_register_path"$'\t'"$phase2_register_hash"
}

phase2_cleanup_promote() {
  local phase2_promote_source="${1:A}"
  local phase2_promote_destination="${2:A}"
  local phase2_promote_expected_hash="$3"
  [[ "${phase2_cleanup_states[$phase2_promote_source]-}" == "registered" ]] || return 69
  [[ ! -e "$phase2_promote_source" ]] || return 70
  [[ "$phase2_promote_destination" == "$phase2_cleanup_workspace_path"/Hangboards/* ]] || return 71
  [[ -f "$phase2_promote_destination" && ! -L "$phase2_promote_destination" ]] || return 72
  [[ "$phase2_promote_expected_hash" == "${phase2_cleanup_hashes[$phase2_promote_source]}" ]] || return 73
  local phase2_promote_observed_hash="$(phase2_cleanup_hash_file "$phase2_promote_destination")" || return 74
  [[ "$phase2_promote_observed_hash" == "$phase2_promote_expected_hash" ]] || return 74
  phase2_cleanup_append promoted "$phase2_promote_source" "$phase2_promote_expected_hash" "$phase2_promote_destination"
  print -r -- "ACK"$'\t'"PROMOTE"$'\t'"$phase2_promote_source"$'\t'"$phase2_promote_destination"$'\t'"$phase2_promote_expected_hash"
}

phase2_cleanup_run() {
  local phase2_cleanup_original_status="$1"
  (( phase2_cleanup_complete == 0 )) || return
  phase2_cleanup_complete=1
  trap - EXIT INT TERM
  local phase2_cleanup_status=0
  local phase2_cleanup_path phase2_cleanup_state phase2_cleanup_destination phase2_cleanup_observed_hash
  for phase2_cleanup_path in ${(k)phase2_cleanup_states}; do
    phase2_cleanup_state="${phase2_cleanup_states[$phase2_cleanup_path]}"
    if [[ "$phase2_cleanup_state" == "registered" ]]; then
      if [[ -e "$phase2_cleanup_path" ]]; then
        rtk rm -f -- "$phase2_cleanup_path" || phase2_cleanup_status=1
      fi
      [[ ! -e "$phase2_cleanup_path" ]] || phase2_cleanup_status=1
    elif [[ "$phase2_cleanup_state" == "promoted" ]]; then
      phase2_cleanup_destination="${phase2_cleanup_destinations[$phase2_cleanup_path]}"
      [[ ! -e "$phase2_cleanup_path" ]] || phase2_cleanup_status=1
      [[ -f "$phase2_cleanup_destination" && ! -L "$phase2_cleanup_destination" ]] || phase2_cleanup_status=1
      if [[ -f "$phase2_cleanup_destination" ]]; then
        phase2_cleanup_observed_hash="$(phase2_cleanup_hash_file "$phase2_cleanup_destination")" || phase2_cleanup_status=1
        [[ "$phase2_cleanup_observed_hash" == "${phase2_cleanup_hashes[$phase2_cleanup_path]}" ]] || phase2_cleanup_status=1
      fi
    else
      phase2_cleanup_status=1
    fi
  done
  for phase2_cleanup_path in "$phase2_cleanup_context_path/inputs" "$phase2_cleanup_context_path/candidates" "$phase2_cleanup_context_path/review"; do
    rtk rmdir "$phase2_cleanup_path" 2>/dev/null || phase2_cleanup_status=1
  done
  if (( phase2_cleanup_status != 0 )); then
    print -u2 -r -- "CLEANUP_FAILED"$'\t'"$phase2_cleanup_ledger_path"
    (( phase2_cleanup_original_status != 0 )) && return "$phase2_cleanup_original_status"
    return 1
  fi
  rtk rm -f -- "$phase2_cleanup_owner_path" "$phase2_cleanup_script_path" || phase2_cleanup_status=1
  if (( phase2_cleanup_status == 0 )); then
    local phase2_cleanup_ledger_copy="$(<"$phase2_cleanup_ledger_path")"
    rtk rm -f -- "$phase2_cleanup_ledger_path" || phase2_cleanup_status=1
    if ! rtk rmdir "$phase2_cleanup_context_path" 2>/dev/null; then
      print -r -- "$phase2_cleanup_ledger_copy" > "$phase2_cleanup_ledger_path"
      phase2_cleanup_status=1
    fi
  fi
  if (( phase2_cleanup_status == 0 )); then
    print -r -- "CLEANUP_OK"$'\t'"$phase2_cleanup_context_path"
  else
    print -u2 -r -- "CLEANUP_FAILED"$'\t'"$phase2_cleanup_ledger_path"
  fi
  (( phase2_cleanup_original_status != 0 )) && return "$phase2_cleanup_original_status"
  return "$phase2_cleanup_status"
}

trap 'phase2_cleanup_run $?' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
print -r -- "READY"$'\t'"$$"$'\t'"$phase2_cleanup_context_path"

while IFS=$'\t' read -r phase2_cleanup_command phase2_cleanup_arg1 phase2_cleanup_arg2 phase2_cleanup_arg3; do
  case "$phase2_cleanup_command" in
    REGISTER) phase2_cleanup_register "$phase2_cleanup_arg1" || exit $? ;;
    PROMOTE) phase2_cleanup_promote "$phase2_cleanup_arg1" "$phase2_cleanup_arg2" "$phase2_cleanup_arg3" || exit $? ;;
    EXIT) exit 0 ;;
    *) exit 75 ;;
  esac
done
exit 76
```

At the controller level, set `phase2_cleanup_script_path` to the task's literal context path plus `/phase2-cleanup.zsh`. Launch it with this exact call shape; the string concatenation inserts that already assigned literal path into the command rather than relying on shell environment persistence:

```text
exec_command({"cmd":"/bin/zsh " + phase2_cleanup_script_path,"workdir":"/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter","tty":true,"yield_time_ms":1000,"max_output_tokens":2000})
```

Store the returned `session_id` as `phase2_cleanup_session_id`; require `READY<TAB>pid<TAB>` followed by the literal `phase2_context_path` before continuing. The persistent PTY remains alive across browsing, `view_image`, imagegen, Workbench review, validation, commits, and rollback.

Register a file with `write_stdin({"session_id":phase2_cleanup_session_id,"chars":"REGISTER\t" + phase2_owned_path + "\n","yield_time_ms":1000,"max_output_tokens":2000})`; require `ACK<TAB>REGISTER<TAB>` followed by the same absolute path and its SHA-256 before reading, inspecting, hashing independently, moving, or deleting that file. This applies to every copied input, candidate, review capture, rollback copy, and rejected artifact. Most importantly, assign the exact absolute path returned by every built-in imagegen call under `/Users/asherlc/.codex/generated_images/` to `phase2_generated_path`, then make that exact call with `phase2_owned_path = phase2_generated_path` immediately, before any inspection or movement.

After an accepted context candidate is hash-verified and moved byte-for-byte to its exact declared package asset, call `write_stdin({"session_id":phase2_cleanup_session_id,"chars":"PROMOTE\t" + phase2_candidate_path + "\t" + phase2_package_asset_path + "\t" + phase2_candidate_sha256 + "\n","yield_time_ms":1000,"max_output_tokens":2000})`. Require the exact `ACK<TAB>PROMOTE` response. Promotion causes cleanup to verify that the registered source is absent and the package destination retains the same hash; it never registers or deletes the package destination.

Normal completion calls `write_stdin({"session_id":phase2_cleanup_session_id,"chars":"EXIT\n","yield_time_ms":1000,"max_output_tokens":2000})`, then polls with `write_stdin({"session_id":phase2_cleanup_session_id,"chars":"","yield_time_ms":1000,"max_output_tokens":2000})` until exit. Require exit 0, `CLEANUP_OK`, absence of every registered non-promoted path, absence of every promoted source, retained package destination/hash, and absence of the exact context. An interruption calls the same tool with `chars:"\u0003"` and must exit 130 after cleanup. For TERM handling, assign the literal PID reported by `READY` to controller value `phase2_cleanup_pid`, call `exec_command({"cmd":"rtk kill -TERM " + phase2_cleanup_pid,"workdir":"/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter","yield_time_ms":1000,"max_output_tokens":2000})`, then poll the same session and require exit 143 after cleanup. Never use `terminate` as the normal path. A cleanup failure must return nonzero, print `CLEANUP_FAILED<TAB>ledger-path`, and retain the exact context/ledger for diagnosis; do not delete shared or unknown paths.

For each copied web input, use a deterministic filename `inputs/record-N-official-I-image-J.ext` or `inputs/record-N-independent-I-image-J.ext`, preserve original bytes, register it through the live PTY, require the cleanup-session hash equal `rtk shasum -a 256` on the exact file, add its `GenerationSourceInput`, then run:

```bash
phase2_source_input_sha256="$(rtk shasum -a 256 "$phase2_source_input_path" | rtk awk '{print $1}')"
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-partial --source-file "$phase2_source_input_sha256" "$phase2_source_input_path"
```

The command is executed with the literal computed hash/path, and its actual date/command/result is committed in `byteVerification` before deletion.

After each built-in call, take the exact absolute path returned by the tool as `phase2_generated_path`, immediately relay it with `REGISTER`, and require its ACK/hash. Only then inspect it. Require its path to match `/Users/asherlc/.codex/generated_images/*`, inspect PNG IHDR through the validator, move it byte-for-byte to the deterministic context output filename assigned to `phase2_candidate_path`, register that path, rehash into `phase2_candidate_sha256`, and require equality with both ACK hashes. A product task adds a `GenerationCandidate` with this exact `transientOutputPath`. A preflight task must instead add only a root `CapabilityProbeArtifact` with this exact path/hash and `capabilityProbeRejected`; it is forbidden from touching any record's `generation.candidates`. Then execute:

```bash
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-partial --candidate-file "$phase2_candidate_sha256" "$phase2_candidate_path"
```

No rejected production candidate, capability artifact, or input is deleted until source/candidate roles, URLs, hashes, dispositions, reasons, and passed transient commands are committed and pushed. A preflight artifact is then deleted through the live cleanup session, its absence is verified, and its non-null `deletionVerifiedAt` is committed/pushed before its probe may pass.

For acceptance, first byte-copy the original package PNG into the owned context, register it through the PTY, and require its ACK/hash. Move the accepted context candidate to the declared package path without modification, rehash it, send `PROMOTE`, and require its ACK. If package/Workbench validation fails before task completion, restore the original copy byte-for-byte, record the candidate rejection, register any newly created temporary path, commit/push provenance, and exit through the live cleanup session. Cleanup never deletes an accepted package path. Cleanup success is proved by PTY exit 0 plus exact absence/retention checks; cleanup failure retains the ledger and makes the task fail.

## Exact 20-class canvas preflight

The 65 edit/regenerate records span these 20 canvas classes. The two mixed-mode classes require separate edit and generation probes, for 22 behavior probes total. `coveredRecordKeys` is exactly the following list per class and partitions all 65 repair keys once.

Preflight's accepted-keep whitelist is frozen before Task 2 and contains exactly these 17 source-supported keys, in Phase 1 record order: `beastmaker-2000/primary`, `frictitious.megalith/primary`, `lattice-triple-rung/primary`, `lattice.mini-bar/primary`, `metolius.prime-rib/front`, `metolius.wood-grips-deluxe-ii/front`, `nature.stone-hanger-mini-karma8a/primary`, `nature.stone-hanger-mini/primary`, `nature.stone-hanger-mini/side`, `target10a.linebreaker-base/primary`, `tension.grindstone/primary`, `tension.honestone/primary`, `tension.whetstone/primary`, `the-hangboard.the-hangboard/front`, `yy.baguette-evo/rounded-tray`, `yy.baguette/stepped-face`, and `yy.baguette/reverse-face`. It explicitly excludes the two `blockedEvidence` keeps and every pending repair. Preflight selection cannot observe task order, production bootstrap status, or any Task 10+ output.

Only two whitelist assets are selected as composition references because they are the earliest accepted keeps for the only represented form factors that have a preflight-time accepted match:

| Reference ID | Exact key | Exact path | Exact accepted SHA-256 | Form factor |
| --- | --- | --- | --- | --- |
| `preflight-full-width-composition` | `beastmaker-2000/primary` | `Hangboards/beastmaker-2000/assets/primary.png` | `2a5dfd439bd67485a16d764b7c8aaf24cba22c42f4ee2b4657cb8842d743bb68` | `fullWidthFixedBoard` |
| `preflight-multi-orientation-composition` | `lattice.mini-bar/primary` | `Hangboards/lattice-mini-bar/assets/primary.png` | `db351c7c617420b84550e64d6685c8c98e60da9529feb3697bd7435af5f751fc` | `multiOrientationDevice` |

Every material axis is unavailable by preflight policy, including when a keep shares a material token, because the probe tests only untouched canvas behavior. Fresh live evidence and `sharedMaterialContract` govern the disposable subject's material appearance. A null composition is also explicit when no exact-form-factor asset exists. These are the complete 22 assignments; no fallback or forward dependency is permitted:

| Task | Probe ID / canvas / behavior / representative | Composition reference | Exact `unavailableAxes` |
| ---: | --- | --- | --- |
| 2 | `1000x1000-edit-mxedge-large` / 1000×1000 / edit / `lattice.mxedge-lift-large/primary` | null | `compositionFramingScale`, `materialTextureLighting` |
| 2 | `1000x259-edit-beastmaker-1000` / 1000×259 / edit / `beastmaker-1000/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 2 | `1233x435-generate-trango-training-center` / 1233×435 / generate / `trango.rock-prodigy-training-center/primary` | null | `compositionFramingScale`, `materialTextureLighting` |
| 3 | `1254x1254-generate-soill-split` / 1254×1254 / generate / `soill.split-palm/primary` | null | `compositionFramingScale`, `materialTextureLighting` |
| 3 | `1440x1440-edit-port-a-board` / 1440×1440 / edit / `frictitious.port-a-board/primary` | `preflight-multi-orientation-composition` | `materialTextureLighting` |
| 3 | `1503x394-edit-escape-beta` / 1503×394 / edit / `escape-beta-22/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 4 | `1536x1024-edit-crimptonite` / 1536×1024 / edit / `crimptonite.helium-mobile/primary` | null | `compositionFramingScale`, `materialTextureLighting` |
| 4 | `1536x1024-generate-captain-dual` / 1536×1024 / generate / `captain-fingerfood.dual/primary` | null | `compositionFramingScale`, `materialTextureLighting` |
| 4 | `1537x1023-edit-evolv` / 1537×1023 / edit / `evolv-kilter-basic-long/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 4 | `1537x1023-generate-grindstone-original` / 1537×1023 / generate / `tension.grindstone-original/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 5 | `1614x975-generate-simulator` / 1614×975 / generate / `metolius.simulator-3d/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 5 | `1654x951-edit-grindstone-pro` / 1654×951 / edit / `tension.grindstone-pro/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 5 | `1672x941-edit-light-rail` / 1672×941 / edit / `metolius.light-rail-2/15mm-side` | null | `compositionFramingScale`, `materialTextureLighting` |
| 6 | `1697x1200-edit-moon` / 1697×1200 / edit / `moon.armstrong/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 6 | `1717x916-generate-climbers-edge` / 1717×916 / generate / `metolius.climbers-edge/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 6 | `1774x457-generate-wood-grips-compact` / 1774×457 / generate / `metolius.wood-grips-compact-ii/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 7 | `1774x887-generate-escape-unlimited` / 1774×887 / generate / `escape.unlimited/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 7 | `1842x854-generate-nug-reverse` / 1842×854 / generate / `frictitious.nug/reverse` | null | `compositionFramingScale`, `materialTextureLighting` |
| 7 | `1980x300-edit-poker` / 1980×300 / edit / `owl-climb.poker/face-a` | `preflight-multi-orientation-composition` | `materialTextureLighting` |
| 8 | `1980x495-generate-diamond-finger` / 1980×495 / generate / `mammut.diamond-finger/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 8 | `2081x755-generate-zlag-evo` / 2081×755 / generate / `zlagboard.evo/primary` | `preflight-full-width-composition` | `materialTextureLighting` |
| 8 | `2112x745-generate-zlag-pro` / 2112×745 / generate / `zlagboard.pro/primary` | `preflight-full-width-composition` | `materialTextureLighting` |

| Class | Count | Required behavior representative(s) | Exact covered record keys |
| --- | ---: | --- | --- |
| 1000×1000 | 2 | edit `lattice.mxedge-lift-large/primary` | `lattice.mxedge-lift-large/primary`, `lattice.mxedge-lift-small/primary` |
| 1000×259 | 1 | edit `beastmaker-1000/primary` | `beastmaker-1000/primary` |
| 1233×435 | 1 | generate `trango.rock-prodigy-training-center/primary` | `trango.rock-prodigy-training-center/primary` |
| 1254×1254 | 1 | generate `soill.split-palm/primary` | `soill.split-palm/primary` |
| 1440×1440 | 3 | edit `frictitious.port-a-board/primary` | `frictitious.port-a-board/primary`, `frictitious.port-a-board/back`, `frictitious.port-a-board/side` |
| 1503×394 | 1 | edit `escape-beta-22/primary` | `escape-beta-22/primary` |
| 1536×1024 | 20 | edit `crimptonite.helium-mobile/primary`; generate `captain-fingerfood.dual/primary` | `captain-fingerfood.dual/primary`, `captain-fingerfood.dual/reverse`, `captain-fingerfood.pocket/primary`, `captain-fingerfood.unlevel/primary`, `captain-fingerfood.unlevel/reverse`, `crimptonite.helium-mobile/primary`, `crimptonite.helium-mobile/reverse`, `frictitious.nug/primary`, `metolius.light-rail-2/20mm-side`, `metolius.rock-rings-3d/front-pair`, `plateau.lifting-edge/primary`, `soill.iron-palm-2/primary`, `soill.training-tiles/primary`, `tension.flash-board/three-edge-upright`, `tension.flash-board/three-edge-inverted`, `trango.rock-prodigy-forge/primary`, `trango.rock-prodigy-natural/primary`, `yy.baguette-evo/central-30-25`, `yy.penta-evo/front-pair`, `yy.travelboard/front-25-15` |
| 1537×1023 | 2 | edit `evolv-kilter-basic-long/primary`; generate `tension.grindstone-original/primary` | `evolv-kilter-basic-long/primary`, `tension.grindstone-original/primary` |
| 1614×975 | 1 | generate `metolius.simulator-3d/primary` | `metolius.simulator-3d/primary` |
| 1654×951 | 1 | edit `tension.grindstone-pro/primary` | `tension.grindstone-pro/primary` |
| 1672×941 | 1 | edit `metolius.light-rail-2/15mm-side` | `metolius.light-rail-2/15mm-side` |
| 1697×1200 | 1 | edit `moon.armstrong/primary` | `moon.armstrong/primary` |
| 1717×916 | 1 | generate `metolius.climbers-edge/primary` | `metolius.climbers-edge/primary` |
| 1774×457 | 1 | generate `metolius.wood-grips-compact-ii/primary` | `metolius.wood-grips-compact-ii/primary` |
| 1774×887 | 20 | generate `escape.unlimited/primary` | `escape.unlimited/primary`, `frictitious.doormount-pro-7/primary`, `metolius.contact/primary`, `metolius.foundry/front`, `metolius.project/primary`, `nature.stoak-board-iii/primary`, `tension.flash-board/two-edge-upright`, `tension.flash-board/two-edge-inverted`, `trango.rock-prodigy-pivot/orientation-1`, `trango.rock-prodigy-pivot/orientation-2`, `trango.rock-prodigy-pivot/orientation-3`, `trango.rock-prodigy-pivot/orientation-4`, `yy.baguette-evo/paired-25-20-15-10`, `yy.baguette-evo/paired-12-8-6`, `yy.baguette-evo/central-20-6`, `yy.travelboard/reverse-10`, `yy.verticalboard-evo/primary`, `yy.verticalboard-first/primary`, `yy.verticalboard-light/primary`, `yy.verticalboard-one/primary` |
| 1842×854 | 1 | generate `frictitious.nug/reverse` | `frictitious.nug/reverse` |
| 1980×300 | 4 | edit `owl-climb.poker/face-a` | `owl-climb.poker/face-a`, `owl-climb.poker/face-b`, `owl-climb.poker/face-c`, `owl-climb.poker/face-d` |
| 1980×495 | 1 | generate `mammut.diamond-finger/primary` | `mammut.diamond-finger/primary` |
| 2081×755 | 1 | generate `zlagboard.evo/primary` | `zlagboard.evo/primary` |
| 2112×745 | 1 | generate `zlagboard.pro/primary` | `zlagboard.pro/primary` |

Each probe freshly reopens the representative record's evidence, hashes/verifies copied inputs, instantiates exactly its row's `PreflightComparatorSet`, uses the disposable capability prompt with the exact required canvas, and makes at most three prompt-only built-in calls. Edit probes supply the actual current target only as an edit-capability target; generation probes do not. Every returned output, including an exact-dimension output, is recorded only under root `capabilityProbeCheck.artifacts` as `capabilityProbeRejected`, committed/pushed with untouched hash and passed byte verification, deleted, and committed/pushed with deletion evidence. No preflight output is promoted, copied into a package, stored in `generation.candidates`, or reused as a product candidate/comparator/baseline/accepted asset.

---

### Task 1: Implement the complete Phase 2 validator, prompt renderer, and CLI

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `Tools/HangboardPackages/README.md`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation.md`

**Interfaces:**
- Consumes: the complete schema, enums, prompt transformation, 20-class coverage, comparator DAG, resource verification, partial/final rules, and public signatures above.
- Produces: schema 2 parser/domain, prompt equality validation, source/candidate transient verifiers, preflight/partial/final validator, exact CLI flags, initial pending Phase 2 manifest, and no `Hangboards` changes.

- [ ] **Step 1: Add exact table-driven failing schema tests.**

  `_phase2_fixture` copies the real manifest's `/records/0`, `/records/1`, `/records/3`, and `/records/23` into a temporary four-package inventory, then writes respectively a keep, completed edit, completed regenerate, and completed removal using valid one-pixel PNG bytes resized only inside the test fixture constructor. It writes passed checks, source/candidate hashes, and terminal comparator/simulator values exactly matching the schema; `_validate_phase2_document` serializes, publicly reloads, and calls the public validator. Use this exact test body and mutation table; every mutation goes through public load and validation:

  ```python
  @pytest.mark.parametrize(
      ("mutation", "message"),
      [
          (lambda d: d["phase2"].update(extra=True), "phase2 has unknown keys"),
          (lambda d: d["records"][0]["phase2Action"].update(state="pending"), "keep requires notRequired"),
          (lambda d: d["records"][1]["phase2EvidenceReview"].update(result="notRequired"), "repair evidence review cannot be notRequired"),
          (lambda d: d["records"][1]["generation"].update(mode="builtInGenerate"), "edit requires builtInEdit"),
          (lambda d: d["records"][2]["generation"].update(mode="builtInEdit"), "regenerate requires builtInGenerate"),
          (lambda d: d["records"][1]["final"]["workbenchReview"].pop("hitTest"), "workbenchReview is missing keys"),
          (lambda d: d["records"][1]["phase2Comparator"]["final"].update(mode="temporaryGap"), "final comparator cannot be a gap"),
          (lambda d: d["records"][1]["generation"]["candidates"][0]["provenance"].update(postProcessing="resize"), "postProcessing must equal none"),
      ],
  )
  def test_phase2_closed_schema_and_enums_fail_closed(
      tmp_path: Path,
      mutation: Callable[[dict[str, object]], None],
      message: str,
  ) -> None:
      boards, inventory, document = _phase2_fixture(tmp_path)
      mutation(document)
      with pytest.raises(PresentationRemediationAuditError, match=message):
          _validate_phase2_document(tmp_path, boards, inventory, document)
  ```

- [ ] **Step 2: Add exact failing canvas coverage and lifecycle tests.**

  ```python
  def test_canvas_preflight_requires_twenty_classes_and_exact_sixty_five_key_partition(
      tmp_path: Path,
  ) -> None:
      boards, inventory, document = _catalog_phase2_fixture(tmp_path)
      document["phase2"]["canvasPreflight"]["classes"][0]["coveredRecordKeys"].pop()
      with pytest.raises(
          PresentationRemediationAuditError,
          match="canvas preflight must cover exactly 65 edit/regenerate record keys",
      ):
          _validate_phase2_document(
              tmp_path,
              boards,
              inventory,
              document,
              mode=PresentationValidationMode.PHASE2_PREFLIGHT,
          )


  def test_preflight_uses_only_closed_pre_task_nine_references_and_no_material_axis(
      tmp_path: Path,
  ) -> None:
      boards, inventory, document = _catalog_phase2_fixture(tmp_path)
      probes = [
          probe
          for canvas_class in document["phase2"]["canvasPreflight"]["classes"]
          for probe in canvas_class["behaviorProbes"]
      ]
      assert len(probes) == 22
      assert all(probe["preflightComparatorSet"]["materialTextureLighting"] is None for probe in probes)
      assert all(
          "materialTextureLighting" in probe["preflightComparatorSet"]["unavailableAxes"]
          for probe in probes
      )
      assert {
          probe["preflightComparatorSet"]["compositionFramingScale"]["sourceRecordKey"]
          for probe in probes
          if probe["preflightComparatorSet"]["compositionFramingScale"] is not None
      } == {"beastmaker-2000/primary", "lattice.mini-bar/primary"}
      assert all("bootstrapComparatorSet" not in probe for probe in probes)


  @pytest.mark.parametrize(
      ("mutation", "message"),
      [
          (
              lambda d: d["phase2"]["canvasPreflight"]["classes"][3]["behaviorProbes"][0]
              .update(bootstrapComparatorSet={}),
              "preflight probe has unknown keys",
          ),
          (
              lambda d: d["phase2"]["canvasPreflight"]["classes"][3]["behaviorProbes"][0]
              ["preflightComparatorSet"].update(materialTextureLighting={}),
              "preflight material comparator is always unavailable",
          ),
          (
              lambda d: d["phase2"]["canvasPreflight"]["classes"][3]["behaviorProbes"][0]
              ["preflightComparatorSet"].update(
                  compositionFramingScale={
                      "axis": "compositionFramingScale",
                      "assetPath": "Hangboards/soill-iron-palm-2/assets/primary.png",
                      "sourceRecordKey": "soill.iron-palm-2/primary",
                      "acceptedAssetSHA256": "0" * 64,
                      "reason": "Pre-Task-9 accepted keep used only for disposable capability-probe composition, framing, and scale; no material or product geometry transfer.",
                  }
              ),
              "preflight composition reference does not match the exact assignment table",
          ),
      ],
  )
  def test_preflight_rejects_production_bootstrap_and_forward_task_dependencies(
      tmp_path: Path,
      mutation: Callable[[dict[str, object]], None],
      message: str,
  ) -> None:
      boards, inventory, document = _catalog_phase2_fixture(tmp_path)
      mutation(document)
      with pytest.raises(PresentationRemediationAuditError, match=message):
          _validate_phase2_document(
              tmp_path,
              boards,
              inventory,
              document,
              mode=PresentationValidationMode.PHASE2_PREFLIGHT,
          )


  ```

  `_preflight_and_completed_production_fixture` contains one terminal/deleted preflight artifact, a completed singular production record whose index-0 source input is its valid style comparator, and a completed bootstrap-seed record with a non-null composition axis. All production values are initially disjoint from the artifact.

  ```python
  @pytest.mark.parametrize(
      "mutation",
      [
          lambda d, a: d["records"][1]["generation"]["candidates"][0].update(
              sha256=a["sha256"]
          ),
          lambda d, a: d["records"][1]["generation"]["candidates"][0].update(
              transientOutputPath=a["transientOutputPath"]
          ),
          lambda d, a: d["records"][1]["generation"]["candidates"][0].update(
              transientOutputPath=a["returnedOutputPath"]
          ),
          lambda d, a: d["records"][1]["phase2Comparator"]["generationTime"].update(
              acceptedAssetSHA256=a["sha256"], assetPath=a["transientOutputPath"]
          ),
          lambda d, a: d["records"][1]["phase2Comparator"]["generationTime"].update(
              assetPath=a["returnedOutputPath"]
          ),
          lambda d, a: d["records"][1]["phase2Comparator"]["final"].update(
              acceptedAssetSHA256=a["sha256"], assetPath=a["transientOutputPath"]
          ),
          lambda d, a: d["records"][2]["phase2Comparator"]["bootstrapComparatorSet"]
              ["compositionFramingScale"].update(
                  acceptedAssetSHA256=a["sha256"], assetPath=a["transientOutputPath"]
              ),
          lambda d, a: d["records"][1]["final"].update(
              acceptedAssetSHA256=a["sha256"]
          ),
          lambda d, a: d["records"][1]["generation"]["sourceInputs"][0].update(
              sha256=a["sha256"], assetPath=a["transientOutputPath"]
          ),
      ],
  )
  def test_preflight_artifact_hash_and_path_never_enter_production_state(
      tmp_path: Path,
      mutation: Callable[[dict[str, object], dict[str, object]], None],
  ) -> None:
      boards, inventory, document = _preflight_and_completed_production_fixture(tmp_path)
      artifact = document["phase2"]["capabilityProbeCheck"]["artifacts"][0]
      mutation(document, artifact)
      with pytest.raises(
          PresentationRemediationAuditError,
          match="capability probe artifact overlaps production state",
      ):
          _validate_phase2_document(tmp_path, boards, inventory, document)


  def test_preflight_artifact_is_always_rejected_recorded_deleted_and_separate(
      tmp_path: Path,
  ) -> None:
      boards, inventory, document = _completed_preflight_fixture(tmp_path)
      artifact = document["phase2"]["capabilityProbeCheck"]["artifacts"][0]
      assert artifact["disposition"] == "capabilityProbeRejected"
      assert artifact["productionUse"] == "forbidden"
      assert artifact["deletionVerifiedAt"] is not None
      assert not Path(artifact["returnedOutputPath"]).exists()
      assert not Path(artifact["transientOutputPath"]).exists()
      assert all(
          candidate["sha256"] != artifact["sha256"]
          and candidate["transientOutputPath"] not in {
              artifact["returnedOutputPath"],
              artifact["transientOutputPath"],
          }
          for record in document["records"]
          for candidate in record["generation"]["candidates"]
      )
      _validate_phase2_document(
          tmp_path,
          boards,
          inventory,
          document,
          mode=PresentationValidationMode.PHASE2_PREFLIGHT,
      )


  def test_partial_mode_accepts_completed_repairs_pending_later_actions_and_historical_keep_block(
      tmp_path: Path,
  ) -> None:
      boards, inventory, document = _mixed_phase2_fixture(tmp_path)
      report = _validate_phase2_document(
          tmp_path,
          boards,
          inventory,
          document,
          mode=PresentationValidationMode.PHASE2_PARTIAL,
      )
      assert report.completed_edit_count == 1
      assert report.pending_phase2_action_count == 2
      assert report.historical_evidence_blocked_keeps == 1
      assert report.blocked_phase2_action_count == 0


  def test_final_mode_requires_no_pending_or_blocked_phase2_actions_but_preserves_historical_gaps(
      tmp_path: Path,
  ) -> None:
      boards, inventory, document = _final_phase2_fixture(tmp_path)
      document["records"][1]["phase2Action"] = {
          "state": "blocked",
          "blockedReason": "Exact-canvas output unavailable.",
      }
      with pytest.raises(
          PresentationRemediationAuditError,
          match="final Phase 2 validation requires zero blocked Phase 2 actions",
      ):
          _validate_phase2_document(
              tmp_path,
              boards,
              inventory,
              document,
              mode=PresentationValidationMode.PHASE2_FINAL,
      )
  ```

  Add an exact artifact-result table: untouched output with matching IHDR plus `exactCanvas` passes even though disposition remains `capabilityProbeRejected`; wrong dimensions labeled `exactCanvas` fail `capability probe canvasResult disagrees with IHDR`; exact dimensions labeled `wrongCanvas` fail the same invariant; any post-processing provenance fails. Do not add likeness, material, style, Workbench, visual-acceptance, promotion, or cohort-baseline assertions to preflight.

- [ ] **Step 3: Add exact failing source/candidate byte-verification tests.**

  ```python
  def test_transient_source_verifier_hashes_present_bytes_and_final_validation_uses_durable_record(
      tmp_path: Path,
  ) -> None:
      boards, inventory, document, source_path = _completed_edit_with_source(tmp_path)
      source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
      manifest = load_presentation_remediation_manifest(_write_manifest(tmp_path, document))
      assert verify_transient_source_files(manifest, {source_sha: source_path}) == (source_sha,)
      source_path.unlink()
      report = validate_presentation_remediation_manifest(
          manifest,
          inventory,
          hangboards_root=boards,
          validation_mode=PresentationValidationMode.PHASE2_PARTIAL,
      )
      assert report.completed_edit_count == 1


  def test_deleted_source_requires_passed_transient_verification_record(tmp_path: Path) -> None:
      boards, inventory, document, source_path = _completed_edit_with_source(tmp_path)
      source_path.unlink()
      document["records"][1]["generation"]["sourceInputs"][0]["byteVerification"] = {
          "status": "pending",
          "checkedAt": None,
          "command": None,
          "observedSHA256": None,
      }
      with pytest.raises(
          PresentationRemediationAuditError,
          match="deleted source input requires passed transient byte verification",
      ):
          _validate_phase2_document(tmp_path, boards, inventory, document)
  ```

  Add these exact candidate assertions using `_completed_edit_with_candidate`, which returns the edit fixture plus a temporary candidate path whose bytes equal the fixture's accepted package bytes and stores that literal path as `transientOutputPath`:

  ```python
  def test_transient_candidate_verifier_requires_hash_and_ihdr_equality(tmp_path: Path) -> None:
      boards, inventory, document, candidate_path = _completed_edit_with_candidate(tmp_path)
      sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
      manifest = load_presentation_remediation_manifest(_write_manifest(tmp_path, document))
      assert verify_transient_candidate_files(manifest, {sha: candidate_path}) == (sha,)
      candidate_path.write_bytes(candidate_path.read_bytes() + b"changed")
      with pytest.raises(PresentationRemediationAuditError, match="candidate SHA-256 mismatch"):
          verify_transient_candidate_files(manifest, {sha: candidate_path})


  def test_completed_repair_requires_accepted_candidate_to_equal_on_disk_bytes(tmp_path: Path) -> None:
      boards, inventory, document, candidate_path = _completed_edit_with_candidate(tmp_path)
      document["records"][1]["generation"]["candidates"][0]["sha256"] = "0" * 64
      with pytest.raises(PresentationRemediationAuditError, match="accepted candidate must equal on-disk asset"):
          _validate_phase2_document(tmp_path, boards, inventory, document)


  def test_rejected_candidate_may_be_deleted_only_after_passed_verification(tmp_path: Path) -> None:
      boards, inventory, document, candidate_path = _completed_edit_with_rejected_candidate(tmp_path)
      candidate_path.unlink()
      assert _validate_phase2_document(tmp_path, boards, inventory, document).completed_edit_count == 1
      rejected = document["records"][1]["generation"]["candidates"][0]
      rejected["byteVerification"]["observedSHA256"] = "0" * 64
      with pytest.raises(PresentationRemediationAuditError, match="candidate verification hash mismatch"):
          _validate_phase2_document(tmp_path, boards, inventory, document)
  ```

- [ ] **Step 4: Add exact failing comparator DAG, prompt, removal, and simulator tests.**

  Parameterize the comparator fixture with this exact outcome table and assert the listed error substring or success:

  | Fixture comparator | Expected result |
  | --- | --- |
  | compatible Phase 1 keep at order 0 | success |
  | compatible completed repair in earlier task/batch | success |
  | compatible repair in later task/batch | `comparator must precede consumer` |
  | material mismatch | `comparator material is incompatible` |
  | form-factor mismatch | `comparator form factor is incompatible` |
  | two-record cycle | `comparator graph contains a cycle` |
  | null singular comparator and null bootstrap set at generation | `generation requires a singular comparator or bootstrap set` |
  | non-null singular comparator and non-null bootstrap set | `comparator paths are mutually exclusive` |
  | legacy `temporaryGap` mode | `temporary gaps cannot authorize generation` |
  | bootstrap set on a record outside the nine-seed table | `record is not an authorized cohort seed` |
  | bootstrap seed or axis differing from the exact ordering table | `bootstrap selection does not match canonical seed order` |
  | Task 10 with Beastmaker composition axis and explicit absent material axis | success |
  | Task 10 using Beastmaker as material axis | `wood cannot govern moldedPlastic material` |
  | null axis omitted from `absentAxes` | `bootstrap absent axes do not match null axes` |
  | bootstrap marked accepted before all four review checks pass | `bootstrap acceptance requires passed evidence, visual, Workbench, and package review` |
  | downstream cohort row using another bootstrap after seed acceptance | `cohort already has a singular baseline` |
  | downstream cohort row using the accepted seed as ready singular comparator | success |
  | seed final `cohortBootstrapBaseline` naming itself after all reviews pass | success |
  | non-seed self-referential final comparator | `self reference is reserved for accepted cohort bootstrap seed` |

  Then add exact equality/one-character-drift tests for both renderers. Assert a production bootstrap prompt names both axes, explicit absent axes, live evidence inputs, and the shared render contract without geometry transfer. Assert the disposable renderer reproduces the exact capability prompt, rejects every production label, uses the table's pre-Task-9 composition reference or explicit unavailable axis, always marks material unavailable, and always states `capabilityProbeRejected`/production forbidden. Add exact Mini Bar assertions for one `primary` presentation plus `ergonomic-jug`, `edge-10`, `edge-20`, and `mini-pinch` all assigned to it; and a simulator parameterization that deletes each device class, each of the seven flow keys, and the capture hash list in turn and asserts public validation fails. Add separate invalid-state rows proving only `presentationSelector` accepts `notApplicableSinglePresentation` and only `plan` accepts `notApplicableNoCompatiblePlan`.

  Add keep-state fixtures for all 19 real keep records. Assert the 17 `acceptedCurrentAsset` records retain their exact existing accepted hashes/dimensions and equal on-disk bytes; mutate each hash/dimension/decision in turn and require failure. Assert only `aelith.cyclops-011/primary` and `dewoodstok-woodbord/primary` retain null accepted hash/dimensions with `blockedEvidence`. Assert keeps retain pending Phase 1 validation fields plus only the schema-added factual not-required fields, and final mode does not demand repaired-record terminal states from them.

  Add command-order fixtures for every per-record validation field. Starting from pending, attempt to mark package, focused, full suite, build, batch, root, and simulator fields passed without their literal command/device evidence and require failure. Add one success transition at a time in the exact order product command → focused command → batch full suite → bounded build → direct phone/tablet presentation run.

- [ ] **Step 5: Run the focused tests and confirm RED.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py
  ```

  Expected: FAIL for missing schema 2, preflight-only comparator/artifact separation, source verification, production comparator DAG, both prompt renderers, removal, simulator, and CLI behavior.

- [ ] **Step 6: Implement the schema/domain and both prompt renderers.**

  Add frozen dataclasses or enums matching every closed object and enum above. Parse schema 1 only in `SOURCE_RECLASSIFICATION` compatibility mode and schema 2 in the three Phase 2 modes. Keep byte inspection limited to SHA-256, PNG signature, and IHDR. Implement the production and disposable capability prompt transformations separately and reject stored prompt drift or lifecycle mixing.

- [ ] **Step 7: Implement transient verification and Phase 2 validation.**

  Implement both verifier functions, 20-class/65-key/22-probe coverage, the exact 17-keep preflight whitelist and 22-row assignment table, root-only capability artifact lifecycle/deletion, artifact-versus-production hash/path disjointness, production input/candidate durable rules, exact batch prefix, partial on-disk states, singular-comparator acyclicity, the Task-10+-only closed nine-seed bootstrap selection/transition table, rejection of temporary-gap authorization, Mini Bar absent-end/retained-mini-pinch truth, command-ordered per-record validation propagation, keep-state preservation, simulator rules, historical-gap separation, and exact final totals.

- [ ] **Step 8: Implement and test CLI flags.**

  Parse lifecycle flags as mutually exclusive. Parse each `--source-file` and `--candidate-file` as exactly two arguments, reject duplicate hash keys and illegal lifecycle combinations, and print the extended report. CLI tests assert preflight `--candidate-file` accepts only a declared capability artifact hash/path, partial accepts only a declared production candidate hash/path, cross-lifecycle reuse fails, and preflight/partial/final exact JSON includes `capabilityProbeArtifactCount`.

- [ ] **Step 9: Migrate the real manifest without package mutation.**

  Before editing, assign `phase2_baseline_sha="$(rtk git rev-parse HEAD)"` and write that exact 40-character SHA under the narrative's `Phase 2 baseline SHA` field. Preserve record order and every value in `packageID`, `productName`, `presentationID`, `assetPath`, `workingSurface`, `physicalRevision`, `manufacturer`, `materials`, `formFactor`, `currentAsset`, `decision`, `findings`, `evidence`, and historical `comparator`. Preserve all 19 keep decisions; preserve accepted hash/dimensions for the 17 `acceptedCurrentAsset` keeps and null hash/dimensions only for the two `blockedEvidence` keeps. Replace only the Phase 1 empty/pending repair/removal `generation` and `final` lifecycle scaffolding with schema-2 forms, then add Phase 2 record/root fields, empty closed `capabilityProbeCheck.artifacts`, the exact 20-class/22-preflight-assignment table, the separate production-only nine-seed bootstrap table, and the exact batch matrix below. Keeps use generation `none`, null Phase 2 comparators, action/evidence not-required, their existing pending Phase 1 checks, and only schema-added factual not-required fields. Preserve all five Phase 1 evidence-gap paths and strings. Add narrative lifecycle/resource/comparator/preflight sections. Do not change any PNG or `board.json`.

- [ ] **Step 10: Run GREEN verification.**

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_cli.py
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-preflight
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk git diff --name-only -- Hangboards
  ```

  Expected: tests and inventory pass; preflight report has 20 pending classes covering 65 keys, zero capability artifacts before Task 2, and zero production overlap; final diff command prints nothing.

- [ ] **Step 11: Commit and push.**

  ```bash
  rtk git add Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/src/hangboard_packages/cli.py \
    Tools/HangboardPackages/tests/test_cli.py Tools/HangboardPackages/README.md \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md
  rtk git commit -m "Validate phase two remediation lifecycle"
  rtk git push
  ```

---

## Canvas preflight task recipe

Each Task 2–8 supplies its literal context directory and exact assignment-table rows. Execute this recipe without consulting the production nine-seed table:

- [ ] Launch the persistent cleanup PTY before reopening sources. For each probe, reopen all representative `/evidence` URL leaves and gap searches; copy/register/hash/transiently verify at least one official/independent input and record all reopened evidence IDs.
- [ ] Instantiate exactly the row's `PreflightComparatorSet`. If the row names a composition reference, register/hash its exact accepted keep path and supply it as the sole `preflight-composition` comparator input. Otherwise supply no composition path and require `compositionFramingScale` in `unavailableAxes`. Always set `materialTextureLighting` null, list it in `unavailableAxes`, supply no material comparator, and use live evidence plus the literal shared material contract. Reject every reference outside the 17-key whitelist, including Task 16 Iron Palm, Task 17 Split Palm, any production repair, and any earlier preflight output.
- [ ] Render only `render_phase2_capability_probe_prompt`. Inspect evidence, the optional accepted composition keep, and—for edit behavior only—the current target with `view_image`. Call built-in `image_gen` once per attempt with those exact paths. A current edit target is tool input only; it is not a style reference, baseline, candidate, or evidence.
- [ ] Immediately register the returned generated-images path before inspection/movement. At the controller level assign `phase2_probe_artifact_id = probe["id"] + "-attempt-" + str(attempt)` and `phase2_probe_artifact_path = phase2_context_path + "/candidates/" + phase2_probe_artifact_id + ".png"`; move/register that exact path, hash/inspect untouched IHDR, and add the exact root artifact ID with both paths, hash, dimensions, `canvasResult`, `capabilityProbeRejected`, `productionUse: forbidden`, provenance, passed byte verification, `recordedAt`, and null `deletionVerifiedAt`. Add only its ID to the probe's `artifactIDs`; do not write any record `generation` or `phase2Comparator` field.
- [ ] Run transient verification in `PHASE2_PREFLIGHT`, then commit/push the artifact checkpoint before deletion. `exactCanvas` ends attempts for that probe; `wrongCanvas` permits the next prompt-only attempt, at most three. Never promote or copy an artifact into `Hangboards`.
- [ ] After all task probes reach an exact canvas or their third wrong canvas, send `EXIT` to the same cleanup PTY and poll it to exit 0/`CLEANUP_OK`. Require both recorded paths for every artifact absent. Write one non-null `deletionVerifiedAt` per artifact. A probe with an `exactCanvas` artifact becomes passed; a third `wrongCanvas` becomes blocked and blocks its class/root with the same reason. The task's Step 3 commits/pushes this terminal deletion/status update; a block stops later tasks after that cleanup commit.
- [ ] Before task completion, require the validator's global disjointness scan to prove every artifact hash, returned path, and context path absent from all production candidates, source inputs, comparator selections/axes/baselines, and final accepted hashes. Preflight never establishes `readyBaseline`, `cohortBootstrapBaseline`, or `acceptedCohortBaseline`, and never authorizes Task 10 unless Task 9 independently passes all terminal checks.

The command after each task's probes is:

```bash
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-preflight
rtk git diff --name-only -- Hangboards
```

Expected: validator passes the completed probe prefix, every completed artifact is `capabilityProbeRejected` with verified deletion, the production-overlap count is zero, and `Hangboards` diff is empty.

### Task 2: Preflight canvases 1000×1000, 1000×259, and 1233×435

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-a`; probes edit `lattice.mxedge-lift-large/primary`, edit `beastmaker-1000/primary`, and generate `trango.rock-prodigy-training-center/primary`; produces three passed class records or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all three probes, at most nine built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight small hangboard canvases"`.**

### Task 3: Preflight canvases 1254×1254, 1440×1440, and 1503×394

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-b`; probes generate `soill.split-palm/primary`, edit `frictitious.port-a-board/primary`, and edit `escape-beta-22/primary`; the So iLL Split representative routes only its already-recorded live evidence and never reads a Task 16 or Task 17 output/package candidate; produces three passed class records or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all three probes, at most nine built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight square and wide hangboard canvases"`.**

### Task 4: Preflight mixed-mode canvases 1536×1024 and 1537×1023

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-c`; probes edit `crimptonite.helium-mobile/primary`, generate `captain-fingerfood.dual/primary`, edit `evolv-kilter-basic-long/primary`, and generate `tension.grindstone-original/primary`; produces both modes passed for both classes or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all four probes, at most twelve built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight mixed-mode hangboard canvases"`.**

### Task 5: Preflight canvases 1614×975, 1654×951, and 1672×941

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-d`; probes generate `metolius.simulator-3d/primary`, edit `tension.grindstone-pro/primary`, and edit `metolius.light-rail-2/15mm-side`; produces three passed classes or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all three probes, at most nine built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight medium landscape hangboard canvases"`.**

### Task 6: Preflight canvases 1697×1200, 1717×916, and 1774×457

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-e`; probes edit `moon.armstrong/primary`, generate `metolius.climbers-edge/primary`, and generate `metolius.wood-grips-compact-ii/primary`; produces three passed classes or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all three probes, at most nine built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight wood fixed hangboard canvases"`.**

### Task 7: Preflight canvases 1774×887, 1842×854, and 1980×300

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-f`; probes generate `escape.unlimited/primary`, generate `frictitious.nug/reverse`, and edit `owl-climb.poker/face-a`; produces three passed classes or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all three probes, at most nine built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight catalog-standard and bar canvases"`.**

### Task 8: Preflight canvases 1980×495, 2081×755, and 2112×745

**Files:** manifest and narrative only.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-preflight-canvas-g`; probes generate `mammut.diamond-finger/primary`, generate `zlagboard.evo/primary`, and generate `zlagboard.pro/primary`; produces three passed classes or a committed global block.

- [ ] **Step 1: Run the canvas preflight recipe for all three probes, at most nine built-in calls total.**
- [ ] **Step 2: Run the preflight validator and prove no `Hangboards` diff.**
- [ ] **Step 3: After the recipe's transient checkpoint, cleanup, deletion evidence, and terminal validation, commit/push terminal records with `rtk git commit -m "Preflight wide mixed-material canvases"`.**

### Task 9: Close the exact-canvas preflight gate

**Files:** manifest and narrative only.

**Interfaces:** consumes all 20 classes/22 probes and root capability artifacts; produces root preflight `passed`, exactly 65 covered repair keys, zero production overlap, and authorization for Task 10 to begin its separate production comparator selection. It produces no candidate, comparator, baseline, accepted asset, or package change.

- [ ] **Step 1: Run validator mutations for every closed preflight boundary.** Remove each class, covered key, probe assignment, required evidence input, unavailable material axis, artifact ID, artifact byte-verification field, and deletion timestamp in turn; require failure. Substitute Task 16 Iron Palm, Task 17 Split Palm, a blocked keep, a preflight artifact, or any non-table asset as a composition/material reference; require failure. Add a production `bootstrapComparatorSet`, production prompt label, or production candidate to a probe; require failure.
- [ ] **Step 2: Prove artifact separation exhaustively.** For every capability artifact, inject its hash, returned path, and context path in turn into a production candidate, production source input, singular comparator, final baseline, each bootstrap axis, and final accepted hash; require `capability probe artifact overlaps production state`. Require every artifact's only disposition `capabilityProbeRejected`, production use forbidden, both paths absent, non-null deletion timestamp, and membership only in root `capabilityProbeCheck.artifacts` plus the owning probe's `artifactIDs`.
- [ ] **Step 3: Run `--phase2-preflight`; require `canvasClassCount: 20`, `canvasCoveredRepairCount: 65`, all 22 exact assignment-table probes passed, `capabilityProbeArtifactCount` between 22 and 66, every artifact terminal/deleted, production-overlap count zero, no bootstrap/cohort state, and no blocked reason.**
- [ ] **Step 4: Prove production remains unopened.** Require all 65 production actions pending, every production `generation.candidates` array empty, every production `phase2Comparator` leaf null, every final accepted Phase 2 hash null, and all nine production bootstrap sets absent. Task 10 must independently enter R3 and cannot cite preflight pass/artifacts as comparator authorization.
- [ ] **Step 5: Run the full package tests, final inventory, and `rtk git diff --name-only -- Hangboards`; require green tests/61 packages/85 presentations/empty diff.**
- [ ] **Step 6: Commit/push manifest and narrative with `rtk git commit -m "Verify exact-canvas image generation preflight"`.**

---

## Exclusive product repair matrix

This table is the sole ownership map for the 65 image repairs. `Record` is the literal manifest JSON pointer; `Evidence` and `historical comparator` are exactly `Record + /evidence` and `Record + /comparator`. A task may not change a row owned by another task. Batch order is `nonwood-fixed` (Tasks 10–26), `wood-fixed` (Tasks 28–38), `portable` (Tasks 40–49), and `multi-orientation` (Tasks 51–57). The table contains 17 edit rows and 48 regenerate rows.

| Task | Record / key | Exact asset path | Action / canvas | Evidence-routed material / form factor |
| ---: | --- | --- | --- | --- |
| 10 | `/records/11` `escape-beta-22/primary` | `Hangboards/escape-beta-22/assets/primary.png` | edit / 1503×394 | moldedPlastic / fullWidthFixedBoard |
| 11 | `/records/13` `evolv-kilter-basic-long/primary` | `Hangboards/evolv-kilter-basic-long/assets/primary.png` | edit / 1537×1023 | resin / fullWidthFixedBoard |
| 12 | `/records/28` `metolius.contact/primary` | `Hangboards/metolius-contact/assets/primary.png` | regenerate / 1774×887 | resin / fullWidthFixedBoard |
| 13 | `/records/29` `metolius.foundry/front` | `Hangboards/metolius-foundry/assets/primary.png` | regenerate / 1774×887 | resin / fullWidthFixedBoard |
| 14 | `/records/33` `metolius.project/primary` | `Hangboards/metolius-project/assets/primary.png` | regenerate / 1774×887 | resin / fullWidthFixedBoard |
| 15 | `/records/35` `metolius.simulator-3d/primary` | `Hangboards/metolius-simulator-3d/assets/primary.png` | regenerate / 1614×975 | resin / fullWidthFixedBoard |
| 16 | `/records/48` `soill.iron-palm-2/primary` | `Hangboards/soill-iron-palm-2/assets/primary.png` | regenerate / 1536×1024 | urethane / fullWidthFixedBoard |
| 17 | `/records/49` `soill.split-palm/primary` | `Hangboards/soill-split-palm/assets/primary.png` | regenerate / 1254×1254 | urethane / splitFixedBoard |
| 18 | `/records/50` `soill.training-tiles/primary` | `Hangboards/soill-training-tiles/assets/primary.png` | regenerate / 1536×1024 | urethane / splitFixedBoard |
| 19 | `/records/62` `trango.rock-prodigy-forge/primary` | `Hangboards/trango-rock-prodigy-forge/assets/primary.png` | regenerate / 1536×1024 | urethane / splitFixedBoard |
| 20 | `/records/68` `trango.rock-prodigy-training-center/primary` | `Hangboards/trango-rock-prodigy-training-center/assets/primary.png` | regenerate / 1233×435 | urethane / splitFixedBoard |
| 21 | `/records/12` `escape.unlimited/primary` | `Hangboards/escape-unlimited/assets/primary.png` | regenerate / 1774×887 | wood+metal / fullWidthFixedBoard |
| 22 | `/records/14` `frictitious.doormount-pro-7/primary` | `Hangboards/frictitious-doormount-pro-7/assets/primary.png` | regenerate / 1774×887 | wood+metal+mixedOther / fullWidthFixedBoard |
| 23 | `/records/26` `mammut.diamond-finger/primary` | `Hangboards/mammut-diamond-finger/assets/primary.png` | regenerate / 1980×495 | wood+metal+mixedOther / fullWidthFixedBoard |
| 24 | `/records/39` `nature.stoak-board-iii/primary` | `Hangboards/nature-stoak-board-iii/assets/primary.png` | regenerate / 1774×887 | wood+stoneMineralComposite+metal / fullWidthFixedBoard |
| 25 | `/records/83` `zlagboard.evo/primary` | `Hangboards/zlagboard-evo/assets/primary.png` | regenerate / 2081×755 | wood+metal+mixedOther / fullWidthFixedBoard |
| 26 | `/records/84` `zlagboard.pro/primary` | `Hangboards/zlagboard-pro/assets/primary.png` | regenerate / 2112×745 | wood+metal+mixedOther / fullWidthFixedBoard |
| 28 | `/records/1` `beastmaker-1000/primary` | `Hangboards/beastmaker-1000/assets/primary.png` | edit / 1000×259 | wood / fullWidthFixedBoard |
| 29 | `/records/27` `metolius.climbers-edge/primary` | `Hangboards/metolius-climbers-edge/assets/primary.png` | regenerate / 1717×916 | wood / fullWidthFixedBoard |
| 30 | `/records/36` `metolius.wood-grips-compact-ii/primary` | `Hangboards/metolius-wood-grips-compact-ii/assets/primary.png` | regenerate / 1774×457 | wood / fullWidthFixedBoard |
| 31 | `/records/38` `moon.armstrong/primary` | `Hangboards/moon-armstrong/assets/primary.png` | edit / 1697×1200 | wood / fullWidthFixedBoard |
| 32 | `/records/56` `tension.grindstone-original/primary` | `Hangboards/tension-grindstone-original/assets/primary.png` | regenerate / 1537×1023 | wood / fullWidthFixedBoard |
| 33 | `/records/57` `tension.grindstone-pro/primary` | `Hangboards/tension-grindstone-pro/assets/primary.png` | edit / 1654×951 | wood / fullWidthFixedBoard |
| 34 | `/records/63` `trango.rock-prodigy-natural/primary` | `Hangboards/trango-rock-prodigy-natural/assets/primary.png` | regenerate / 1536×1024 | wood / splitFixedBoard |
| 35 | `/records/79` `yy.verticalboard-evo/primary` | `Hangboards/yy-verticalboard-evo/assets/primary.png` | regenerate / 1774×887 | wood / fullWidthFixedBoard |
| 36 | `/records/80` `yy.verticalboard-first/primary` | `Hangboards/yy-verticalboard-first/assets/primary.png` | regenerate / 1774×887 | wood / fullWidthFixedBoard |
| 37 | `/records/81` `yy.verticalboard-light/primary` | `Hangboards/yy-verticalboard-light/assets/primary.png` | regenerate / 1774×887 | wood / fullWidthFixedBoard |
| 38 | `/records/82` `yy.verticalboard-one/primary` | `Hangboards/yy-verticalboard-one/assets/primary.png` | regenerate / 1774×887 | wood / fullWidthFixedBoard |
| 40 | `/records/3` `captain-fingerfood.dual/primary` | `Hangboards/captain-fingerfood-dual/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 40 | `/records/4` `captain-fingerfood.dual/reverse` | `Hangboards/captain-fingerfood-dual/assets/reverse.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 41 | `/records/5` `captain-fingerfood.pocket/primary` | `Hangboards/captain-fingerfood-pocket/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 42 | `/records/6` `captain-fingerfood.unlevel/primary` | `Hangboards/captain-fingerfood-unlevel/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 42 | `/records/7` `captain-fingerfood.unlevel/reverse` | `Hangboards/captain-fingerfood-unlevel/assets/reverse.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 43 | `/records/8` `crimptonite.helium-mobile/primary` | `Hangboards/crimptonite-helium-mobile/assets/primary.png` | edit / 1536×1024 | wood+ropeCord / reversiblePortable |
| 43 | `/records/9` `crimptonite.helium-mobile/reverse` | `Hangboards/crimptonite-helium-mobile/assets/reverse.png` | edit / 1536×1024 | wood+ropeCord / reversiblePortable |
| 44 | `/records/16` `frictitious.nug/primary` | `Hangboards/frictitious-nug/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 44 | `/records/17` `frictitious.nug/reverse` | `Hangboards/frictitious-nug/assets/reverse.png` | regenerate / 1842×854 | wood+ropeCord / reversiblePortable |
| 45 | `/records/30` `metolius.light-rail-2/20mm-side` | `Hangboards/metolius-light-rail-2/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / reversiblePortable |
| 45 | `/records/31` `metolius.light-rail-2/15mm-side` | `Hangboards/metolius-light-rail-2/assets/15mm-surface.png` | edit / 1672×941 | wood+ropeCord / reversiblePortable |
| 46 | `/records/24` `lattice.mxedge-lift-large/primary` | `Hangboards/lattice-mxedge-lift-large/assets/primary.png` | edit / 1000×1000 | wood+ropeCord / liftingEdge |
| 47 | `/records/25` `lattice.mxedge-lift-small/primary` | `Hangboards/lattice-mxedge-lift-small/assets/primary.png` | edit / 1000×1000 | wood+ropeCord / liftingEdge |
| 48 | `/records/34` `metolius.rock-rings-3d/front-pair` | `Hangboards/metolius-rock-rings-3d/assets/primary.png` | regenerate / 1536×1024 | resin+ropeCord / suspendedPortable |
| 49 | `/records/47` `plateau.lifting-edge/primary` | `Hangboards/plateau-lifting-edge/assets/primary.png` | regenerate / 1536×1024 | metal+wood+ropeCord+mixedOther / liftingEdge |
| 51 | `/records/18` `frictitious.port-a-board/primary` | `Hangboards/frictitious-port-a-board/assets/primary.png` | edit / 1440×1440 | wood+ropeCord / multiOrientationDevice |
| 51 | `/records/19` `frictitious.port-a-board/back` | `Hangboards/frictitious-port-a-board/assets/back.png` | edit / 1440×1440 | wood+ropeCord / multiOrientationDevice |
| 51 | `/records/20` `frictitious.port-a-board/side` | `Hangboards/frictitious-port-a-board/assets/side.png` | edit / 1440×1440 | wood+ropeCord / multiOrientationDevice |
| 52 | `/records/52` `tension.flash-board/three-edge-upright` | `Hangboards/tension-flash-board/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / multiOrientationDevice |
| 52 | `/records/53` `tension.flash-board/three-edge-inverted` | `Hangboards/tension-flash-board/assets/three-edge-inverted.png` | regenerate / 1536×1024 | wood+ropeCord / multiOrientationDevice |
| 52 | `/records/54` `tension.flash-board/two-edge-upright` | `Hangboards/tension-flash-board/assets/two-edge-surface.png` | regenerate / 1774×887 | wood+ropeCord / multiOrientationDevice |
| 52 | `/records/55` `tension.flash-board/two-edge-inverted` | `Hangboards/tension-flash-board/assets/two-edge-inverted.png` | regenerate / 1774×887 | wood+ropeCord / multiOrientationDevice |
| 53 | `/records/43` `owl-climb.poker/face-a` | `Hangboards/owl-climb-poker/assets/face-a.png` | edit / 1980×300 | wood+mixedOther / multiOrientationDevice |
| 53 | `/records/44` `owl-climb.poker/face-b` | `Hangboards/owl-climb-poker/assets/face-b.png` | edit / 1980×300 | wood+mixedOther / multiOrientationDevice |
| 53 | `/records/45` `owl-climb.poker/face-c` | `Hangboards/owl-climb-poker/assets/face-c.png` | edit / 1980×300 | wood+mixedOther / multiOrientationDevice |
| 53 | `/records/46` `owl-climb.poker/face-d` | `Hangboards/owl-climb-poker/assets/face-d.png` | edit / 1980×300 | wood+mixedOther / multiOrientationDevice |
| 54 | `/records/64` `trango.rock-prodigy-pivot/orientation-1` | `Hangboards/trango-rock-prodigy-pivot/assets/primary.png` | regenerate / 1774×887 | urethane / multiOrientationDevice |
| 54 | `/records/65` `trango.rock-prodigy-pivot/orientation-2` | `Hangboards/trango-rock-prodigy-pivot/assets/orientation-2.png` | regenerate / 1774×887 | urethane / multiOrientationDevice |
| 54 | `/records/66` `trango.rock-prodigy-pivot/orientation-3` | `Hangboards/trango-rock-prodigy-pivot/assets/orientation-3.png` | regenerate / 1774×887 | urethane / multiOrientationDevice |
| 54 | `/records/67` `trango.rock-prodigy-pivot/orientation-4` | `Hangboards/trango-rock-prodigy-pivot/assets/orientation-4.png` | regenerate / 1774×887 | urethane / multiOrientationDevice |
| 55 | `/records/69` `yy.baguette-evo/paired-25-20-15-10` | `Hangboards/yy-baguette-evo/assets/primary.png` | regenerate / 1774×887 | wood+ropeCord / multiOrientationDevice |
| 55 | `/records/70` `yy.baguette-evo/paired-12-8-6` | `Hangboards/yy-baguette-evo/assets/shallow-pairs.png` | regenerate / 1774×887 | wood+ropeCord / multiOrientationDevice |
| 55 | `/records/71` `yy.baguette-evo/central-30-25` | `Hangboards/yy-baguette-evo/assets/central-30-25.png` | regenerate / 1536×1024 | wood+ropeCord / multiOrientationDevice |
| 55 | `/records/72` `yy.baguette-evo/central-20-6` | `Hangboards/yy-baguette-evo/assets/central-20-6.png` | regenerate / 1774×887 | wood+ropeCord / multiOrientationDevice |
| 56 | `/records/76` `yy.penta-evo/front-pair` | `Hangboards/yy-penta-evo/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / multiOrientationDevice |
| 57 | `/records/77` `yy.travelboard/front-25-15` | `Hangboards/yy-travelboard/assets/primary.png` | regenerate / 1536×1024 | wood+ropeCord / multiOrientationDevice |
| 57 | `/records/78` `yy.travelboard/reverse-10` | `Hangboards/yy-travelboard/assets/reverse.png` | regenerate / 1774×887 | wood+ropeCord / multiOrientationDevice |

### Exact manifest-to-prompt and task routing

For each matrix row, let `R` be its already-literal `/records/N` value. The executor reads, without inference: key from `R/packageID` + `/` + `R/presentationID`; target from `R/assetPath`; action from `R/decision`; dimensions/hash from `R/currentAsset`; identity from `R/productName`, `R/physicalRevision`, and `R/workingSurface`; materials/form factor from `R/materials` and `R/formFactor`; source claims/roles/URLs from every leaf of `R/evidence/official` then `R/evidence/independent`; repeated searches from the two gap leaves; findings in this exact order: `productLikeness`, `material`, `topology`, `headOnPerspective`, `smoothing`, `framing`, `crossCatalogConsistency`; and historical comparator only from `R/comparator`. The executor writes only `R/repairBatchID`, `R/phase2Action`, `R/phase2EvidenceReview`, `R/phase2Comparator`, `R/generation`, and `R/final`, except for Task 59's explicit package topology change. `render_phase2_generation_prompt` alone transforms those literal fields into the canonical prompt.

### Product repair task recipe

Every Task 10–26, 28–38, 40–49, and 51–57 executes all steps below, in matrix row order, with its literal absolute context path, package directory, batch ID, focused tests, and commit message. A multi-row task finishes one row through package validation before starting the next; one failed/blocked row stops the task.

> Ruling: the first repair in a material/form-factor cohort with no accepted singular catalog baseline uses a pre-generation bootstrap comparator set made only from accepted catalog assets for each available style axis (same form factor for composition/framing/scale, same material family for texture/lighting when one exists), plus exact live official/independent material evidence and the shared render contract; none supplies geometry. After that first output passes evidence, Workbench, package, and visual review, it becomes the ready singular cohort baseline for acyclic downstream repairs. This is necessary because Phase 1 proves no accepted non-wood baseline exists; it costs stricter review of the first cohort asset and a potential rerender if the eventual cohort comparison exposes drift.

> The preflight capability exception ended at Task 9. A preflight composition reference, prompt, artifact hash/path, exact-canvas result, or passed probe is never a lawful Task 10+ source/comparator and cannot satisfy R3. Production still requires one ready singular baseline or the row's exact nine-seed bootstrap set.

- [ ] **Step R1 — Own resources and prove a clean start.** Set `phase2_context_path` to the task's literal absolute context, `phase2_batch_id` to the task's literal batch ID, and `phase2_package_id` to the matrix row's literal `packageID`. Create the control files with `apply_patch`, launch the persistent cleanup PTY, and require its exact READY response before opening external sources. Require the task's matrix asset hash to equal `currentAsset.sha256`; require all 19 keep hashes unchanged; require root preflight passed; require this batch `inProgress`, all prior batches passed, all later batches pending; and require every owned action pending.
- [ ] **Step R2 — Reopen and verify source inputs.** Open every literal URL in the row's official array, then independent array, in stored order. Repeat each non-null gap search using its literal query and record the search command/result/timestamp. Select only bytes that directly implement the stored `imageRole`; save them at the deterministic input path; immediately register each path with the cleanup PTY and require its ACK/hash; add the exact URL, role, evidence pointer, SHA-256, acquisition command/result/timestamp; run `verify_transient_source_files`; commit/push the passed records before any input can be deleted. Set `phase2EvidenceReview.result` to `confirmed` only after the reopened arrays equal the historical arrays exactly. A URL/search/byte failure sets evidence/action to `blocked` with the same reason, commits/pushes, exits/polls cleanup, and stops the task.
- [ ] **Step R3 — Resolve the one lawful pre-generation comparator path.** Ask partial validation for the earliest compatible singular baseline. If found, write `generationTime.readyBaseline`, leave `bootstrapComparatorSet` null, add `style-comparator`, register/hash/verify that path, and use the exact singular reason. If none exists, require the row to equal the next seed in the nine-row ordering table; write its exact `selected` bootstrap set, axis assets, absent axes, evidence IDs, shared contract, selection rule, passed evidence review, pending visual/Workbench/package reviews, and timestamps; leave `generationTime` null. Add/register/hash/verify `bootstrap-composition` and/or `bootstrap-material` only for non-null axes. For Task 10 specifically, use Beastmaker only as composition and keep material explicitly absent. If neither lawful path validates, set the action/bootstrap blocked, commit/push, exit/poll cleanup, and stop. Never open or supply a historical gap or null axis.
- [ ] **Step R4 — Produce candidates without post-processing.** Inspect target/current, evidence inputs, and the ready singular or non-null bootstrap-axis paths with `view_image`. For an edit, add/register/hash/verify the exact package target as `current-target`; for a regenerate, create no current-target input. Use the renderer-produced exact prompt. Call built-in `image_gen` with the edit target when applicable, exact evidence paths, and either the singular comparator or all non-null bootstrap axes. Make one call per attempt and at most three attempts. Immediately relay each returned generated-images path to the live cleanup session before inspection/movement; require ACK/hash, then move/register the deterministic context candidate, record that exact `transientOutputPath`, require hash equality/exact IHDR, and run `verify_transient_candidate_files`. Require its hash/path differ from every root capability artifact before adding it to `generation.candidates`. Record and commit/push every rejected attempt before cleanup. Third rejection sets action/bootstrap blocked, commits/pushes, restores original bytes, exits/polls cleanup, and stops the task.
- [ ] **Step R5 — Accept only direct human/source agreement.** Compare source/current/candidate and singular/bootstrap style axes side-by-side. Require exact canvas, supported identity/topology/material/working-surface orientation, common studio treatment, complete uncropped silhouette, no unsupported detail, and no geometry/material transfer from a style axis. Record a specific rejection or acceptance reason. Byte-copy/register the original target before moving accepted candidate bytes to the exact matrix asset; require package-path hash equal candidate hash; send PROMOTE and require ACK. Write exactly one accepted candidate, final hash/dimensions, and `acceptedPhase2`; for a seed write bootstrap visual review passed. Keep `phase2Action` in-progress, final comparator null, and bootstrap status selected until Steps R6–R7 actually pass.
- [ ] **Step R6 — Review geometry directly in Workbench.** Open the package and accepted presentation. Exercise normal, all-active, every logical hold/piece individually, and hit testing. Compare paths only to reopened primary evidence. If all boundaries agree, record all four passed checks and prove `board.json` SHA-256 equals its R1 hash. If one or more boundaries disagree, directly redraw only those named paths in Workbench, select a constraint only for a human-identified regular shape, repeat all four modes, and record every edited hold ID plus evidence pointer. Never derive geometry from raster pixels. For a seed, write bootstrap Workbench review passed only after all four record checks pass.
- [ ] **Step R7 — Validate exact partial state and then promote status.** First run partial validation while the record/action remains in-progress. Run the package validator for the literal package ID; only after exit 0 write that record's exact command/date/result as `packageValidation: passed`. Run the four common tests plus the task's focused extras; only after exit 0 write that record's exact command/date/result as `focusedTests: passed`. For a bootstrap seed, require confirmed evidence, passed visual review, four passed Workbench checks, and passed package validation, then transition bootstrap status to `acceptedCohortBaseline` and write the canonical self-naming `cohortBootstrapBaseline` final comparator. For a normal row, write the selected `readyBaseline` final comparator. Only then mark the action completed and rerun `audit-presentations --phase2-partial --batch-id "$phase2_batch_id"`. Require current/accepted hash equality, no changes outside the task package/manifest/narrative, unchanged keep truth, and no Phase 2 block. Leave full-suite/build/simulator pending.

  ```bash
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id "$phase2_batch_id"
  rtk scripts/hangboard-packages.sh validate --root Hangboards \
    --package-id "$phase2_package_id"
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
    Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
    Tools/HangboardPackages/tests/test_board_catalog.py \
    Tools/HangboardPackages/tests/test_approved_board_packages.py \
    Tools/HangboardPackages/tests/test_board_package_staging.py
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-partial --batch-id "$phase2_batch_id"
  ```
- [ ] **Step R8 — Commit, push, and clean.** Stage only the task's declared package directory, manifest, and narrative. Commit with the task's literal message and push. Send EXIT to the persistent cleanup session, poll to terminal, and require exit 0/CLEANUP_OK plus exact registered/promoted absence/retention checks. Do not delete shared or unknown files.

## Batch 1 — Nonwood and mixed-material fixed boards

### Task 10: Repair Escape Beta 22

**Files:** `Hangboards/escape-beta-22/assets/primary.png`, `Hangboards/escape-beta-22/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/11`; batch `nonwood-fixed`; bootstrap seed `moldedPlastic/fullWidthFixedBoard` with composition `beastmaker-2000/primary` and material explicitly absent; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-escape-beta-22`; focused extra `Tools/HangboardPackages/tests/test_escape_beta_22_board_package.py`; commit `Repair Escape Beta 22 presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 11: Repair Evolv Kilter Basic Long

**Files:** `Hangboards/evolv-kilter-basic-long/assets/primary.png`, `Hangboards/evolv-kilter-basic-long/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/13`; batch `nonwood-fixed`; bootstrap seed `resin/fullWidthFixedBoard` with composition `beastmaker-2000/primary` and material explicitly absent; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-evolv-kilter`; no focused extra; commit `Repair Evolv Kilter presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 12: Repair Metolius Contact

**Files:** `Hangboards/metolius-contact/assets/primary.png`, `Hangboards/metolius-contact/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/28`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-metolius-contact`; no focused extra; commit `Repair Metolius Contact presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 13: Repair Metolius Foundry

**Files:** `Hangboards/metolius-foundry/assets/primary.png`, `Hangboards/metolius-foundry/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/29`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-metolius-foundry`; no focused extra; commit `Repair Metolius Foundry presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 14: Repair Metolius Project

**Files:** `Hangboards/metolius-project/assets/primary.png`, `Hangboards/metolius-project/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/33`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-metolius-project`; no focused extra; commit `Repair Metolius Project presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 15: Repair Metolius Simulator 3D

**Files:** `Hangboards/metolius-simulator-3d/assets/primary.png`, `Hangboards/metolius-simulator-3d/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/35`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-metolius-simulator`; no focused extra; commit `Repair Metolius Simulator presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 16: Repair So iLL Iron Palm 2

**Files:** `Hangboards/soill-iron-palm-2/assets/primary.png`, `Hangboards/soill-iron-palm-2/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/48`; batch `nonwood-fixed`; bootstrap seed `urethane/fullWidthFixedBoard` with composition `beastmaker-2000/primary` and material explicitly absent; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-soill-iron-palm`; no focused extra; commit `Repair So iLL Iron Palm presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 17: Repair So iLL Split Palm

**Files:** `Hangboards/soill-split-palm/assets/primary.png`, `Hangboards/soill-split-palm/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/49`; batch `nonwood-fixed`; bootstrap seed `urethane/splitFixedBoard` with composition absent and material `soill.iron-palm-2/primary`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-soill-split-palm`; no focused extra; commit `Repair So iLL Split Palm presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 18: Repair So iLL Training Tiles

**Files:** `Hangboards/soill-training-tiles/assets/primary.png`, `Hangboards/soill-training-tiles/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/50`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-soill-training-tiles`; no focused extra; commit `Repair So iLL Training Tiles presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 19: Repair Trango Rock Prodigy Forge

**Files:** `Hangboards/trango-rock-prodigy-forge/assets/primary.png`, `Hangboards/trango-rock-prodigy-forge/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/62`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-trango-forge`; no focused extra—the Training Center test is deliberately not run for Forge; commit `Repair Trango Rock Prodigy Forge presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 20: Repair Trango Rock Prodigy Training Center

**Files:** `Hangboards/trango-rock-prodigy-training-center/assets/primary.png`, `Hangboards/trango-rock-prodigy-training-center/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/68`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-trango-training-center`; focused extra `Tools/HangboardPackages/tests/test_trango_rock_prodigy_training_center_board_package.py`; commit `Repair Trango Rock Prodigy Training Center presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 21: Repair Escape Unlimited

**Files:** `Hangboards/escape-unlimited/assets/primary.png`, `Hangboards/escape-unlimited/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/12`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-escape-unlimited`; no focused extra; commit `Repair Escape Unlimited presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 22: Repair Frictitious DoorMount Pro 7

**Files:** `Hangboards/frictitious-doormount-pro-7/assets/primary.png`, `Hangboards/frictitious-doormount-pro-7/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/14`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-doormount-pro`; no focused extra; commit `Repair Frictitious DoorMount presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 23: Repair Mammut Diamond Finger

**Files:** `Hangboards/mammut-diamond-finger/assets/primary.png`, `Hangboards/mammut-diamond-finger/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/26`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-mammut-diamond-finger`; no focused extra; commit `Repair Mammut Diamond Finger presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 24: Repair Nature Climbing Stoak Board III

**Files:** `Hangboards/nature-stoak-board-iii/assets/primary.png`, `Hangboards/nature-stoak-board-iii/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/39`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-stoak-board`; no focused extra; commit `Repair Stoak Board presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 25: Repair Zlagboard Evo

**Files:** `Hangboards/zlagboard-evo/assets/primary.png`, `Hangboards/zlagboard-evo/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/83`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-zlagboard-evo`; no focused extra; commit `Repair Zlagboard Evo presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 26: Repair Zlagboard Pro

**Files:** `Hangboards/zlagboard-pro/assets/primary.png`, `Hangboards/zlagboard-pro/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/84`; batch `nonwood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-zlagboard-pro`; no focused extra; commit `Repair Zlagboard Pro presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 27: Gate the nonwood and mixed-material fixed-board batch

**Files:** manifest and narrative only.

- [ ] **Step 1:** Require exactly the 17 Batch 1 matrix rows completed, current/accepted hashes equal, four passed Workbench checks each, no blocked action, and all other action rows pending.
- [ ] **Step 2:** Run `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests`, final inventory, and partial audit with literal `--batch-id nonwood-fixed`; require all pass.
- [ ] **Step 3:** Only after Step 2's full package command exits 0, write that literal command/date/result as `fullPackageSuite: passed` to each of the 17 owned records. Then set the batch package/focused aggregates, full-suite check, and batch status passed; rerun partial audit with literal `--batch-id nonwood-fixed` and require the terminal batch state to pass; commit/push with `rtk git commit -m "Gate nonwood fixed-board presentation repairs"`.

## Batch 2 — Wood fixed and split boards

### Task 28: Repair Beastmaker 1000

**Files:** `Hangboards/beastmaker-1000/assets/primary.png`, `Hangboards/beastmaker-1000/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/1`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-beastmaker-1000`; focused extra `Tools/HangboardPackages/tests/test_beastmaker_depth_metadata.py`; commit `Repair Beastmaker 1000 presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 29: Repair Metolius Climber's Edge

**Files:** `Hangboards/metolius-climbers-edge/assets/primary.png`, `Hangboards/metolius-climbers-edge/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/27`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-climbers-edge`; no focused extra; commit `Repair Metolius Climbers Edge presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 30: Repair Metolius Wood Grips Compact II

**Files:** `Hangboards/metolius-wood-grips-compact-ii/assets/primary.png`, `Hangboards/metolius-wood-grips-compact-ii/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/36`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-wood-grips-compact`; no focused extra; commit `Repair Metolius Wood Grips Compact presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 31: Repair Moon Armstrong

**Files:** `Hangboards/moon-armstrong/assets/primary.png`, `Hangboards/moon-armstrong/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/38`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-moon-armstrong`; focused extra `Tools/HangboardPackages/tests/test_moon_armstrong_geometry_repair.py`; commit `Repair Moon Armstrong presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 32: Repair Tension Grindstone Original

**Files:** `Hangboards/tension-grindstone-original/assets/primary.png`, `Hangboards/tension-grindstone-original/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/56`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-grindstone-original`; focused extra `Tools/HangboardPackages/tests/test_tension_grindstone_legacy_board_packages.py`; commit `Repair Tension Grindstone Original presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 33: Repair Tension Grindstone Pro

**Files:** `Hangboards/tension-grindstone-pro/assets/primary.png`, `Hangboards/tension-grindstone-pro/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/57`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-grindstone-pro`; focused extra `Tools/HangboardPackages/tests/test_tension_grindstone_legacy_board_packages.py`; commit `Repair Tension Grindstone Pro presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 34: Repair Trango Rock Prodigy Natural

**Files:** `Hangboards/trango-rock-prodigy-natural/assets/primary.png`, `Hangboards/trango-rock-prodigy-natural/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/63`; batch `wood-fixed`; bootstrap seed `wood/splitFixedBoard` with composition `soill.split-palm/primary` and material `beastmaker-2000/primary`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-trango-natural`; no focused extra; commit `Repair Trango Rock Prodigy Natural presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 35: Repair YY VerticalBoard Evo

**Files:** `Hangboards/yy-verticalboard-evo/assets/primary.png`, `Hangboards/yy-verticalboard-evo/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/79`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-verticalboard-evo`; no focused extra; commit `Repair YY VerticalBoard Evo presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 36: Repair YY VerticalBoard First

**Files:** `Hangboards/yy-verticalboard-first/assets/primary.png`, `Hangboards/yy-verticalboard-first/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/80`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-verticalboard-first`; no focused extra; commit `Repair YY VerticalBoard First presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 37: Repair YY VerticalBoard Light

**Files:** `Hangboards/yy-verticalboard-light/assets/primary.png`, `Hangboards/yy-verticalboard-light/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/81`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-verticalboard-light`; no focused extra; commit `Repair YY VerticalBoard Light presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 38: Repair YY VerticalBoard One

**Files:** `Hangboards/yy-verticalboard-one/assets/primary.png`, `Hangboards/yy-verticalboard-one/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/82`; batch `wood-fixed`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-verticalboard-one`; no focused extra; commit `Repair YY VerticalBoard One presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 39: Gate the wood fixed/split batch

**Files:** manifest and narrative only.

- [ ] **Step 1:** Require exactly the 11 Batch 2 matrix rows completed in addition to passed Batch 1, with accepted hashes/four Workbench checks/no blocks, and later rows pending.
- [ ] **Step 2:** Run `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests`, `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, and partial audit with literal `--batch-id wood-fixed`; require all pass.
- [ ] **Step 3:** Only after Step 2's full package command exits 0, write that literal command/date/result as `fullPackageSuite: passed` to each of the 11 owned records. Then set the batch package/focused aggregates, full-suite check, and batch status passed; rerun partial audit with literal `--batch-id wood-fixed` and require the terminal batch state to pass; commit/push with `rtk git commit -m "Gate wood fixed-board presentation repairs"`.

## Batch 3 — Reversible and lifting portable devices

### Task 40: Repair Captain Fingerfood Dual

**Files:** `Hangboards/captain-fingerfood-dual/assets/primary.png`, `Hangboards/captain-fingerfood-dual/assets/reverse.png`, `Hangboards/captain-fingerfood-dual/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/3` then `/records/4`; batch `portable`; first-row bootstrap seed `wood/reversiblePortable` with composition absent and material `beastmaker-2000/primary`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-captain-dual`; no focused extra; commit `Repair Captain Fingerfood Dual presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the two physical-face rows.**

### Task 41: Repair Captain Fingerfood Pocket

**Files:** `Hangboards/captain-fingerfood-pocket/assets/primary.png`, `Hangboards/captain-fingerfood-pocket/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/5`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-captain-pocket`; no focused extra; commit `Repair Captain Fingerfood Pocket presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 42: Repair Captain Fingerfood Unlevel

**Files:** `Hangboards/captain-fingerfood-unlevel/assets/primary.png`, `Hangboards/captain-fingerfood-unlevel/assets/reverse.png`, `Hangboards/captain-fingerfood-unlevel/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/6` then `/records/7`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-captain-unlevel`; no focused extra; commit `Repair Captain Fingerfood Unlevel presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the two physical-face rows.**

### Task 43: Repair Crimptonite Helium Mobile

**Files:** `Hangboards/crimptonite-helium-mobile/assets/primary.png`, `Hangboards/crimptonite-helium-mobile/assets/reverse.png`, `Hangboards/crimptonite-helium-mobile/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/8` then `/records/9`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-crimptonite-helium`; no focused extra; commit `Repair Crimptonite Helium presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the two physical-face rows.**

### Task 44: Repair Frictitious NUG

**Files:** `Hangboards/frictitious-nug/assets/primary.png`, `Hangboards/frictitious-nug/assets/reverse.png`, `Hangboards/frictitious-nug/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/16` then `/records/17`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-frictitious-nug`; no focused extra; commit `Repair Frictitious NUG presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the two physical-face rows.**

### Task 45: Repair Metolius Light Rail 2

**Files:** `Hangboards/metolius-light-rail-2/assets/primary.png`, `Hangboards/metolius-light-rail-2/assets/15mm-surface.png`, `Hangboards/metolius-light-rail-2/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/30` then `/records/31`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-light-rail`; no focused extra; commit `Repair Metolius Light Rail presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the two physical-face rows.**

### Task 46: Repair Lattice MXEdge Lift Large

**Files:** `Hangboards/lattice-mxedge-lift-large/assets/primary.png`, `Hangboards/lattice-mxedge-lift-large/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/24`; batch `portable`; bootstrap seed `wood/liftingEdge` with composition absent and material `beastmaker-2000/primary`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-mxedge-lift-large`; no focused extra; commit `Repair Lattice MXEdge Lift Large presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 47: Repair Lattice MXEdge Lift Small

**Files:** `Hangboards/lattice-mxedge-lift-small/assets/primary.png`, `Hangboards/lattice-mxedge-lift-small/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/25`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-mxedge-lift-small`; no focused extra; commit `Repair Lattice MXEdge Lift Small presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 48: Repair Metolius Rock Rings 3D

**Files:** `Hangboards/metolius-rock-rings-3d/assets/primary.png`, `Hangboards/metolius-rock-rings-3d/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/34`; batch `portable`; bootstrap seed `resin/suspendedPortable` with composition absent and material `evolv-kilter-basic-long/primary`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-rock-rings`; no focused extra; commit `Repair Metolius Rock Rings presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 49: Repair Plateau Lifting Edge

**Files:** `Hangboards/plateau-lifting-edge/assets/primary.png`, `Hangboards/plateau-lifting-edge/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/47`; batch `portable`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-plateau-lifting-edge`; no focused extra; commit `Repair Plateau Lifting Edge presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 50: Gate the portable-device batch

**Files:** manifest and narrative only.

- [ ] **Step 1:** Require exactly the 15 Batch 3 rows completed in addition to Batches 1–2, with accepted hashes/four Workbench checks/no blocks, and later rows pending.
- [ ] **Step 2:** Run `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests`, `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, and partial audit with literal `--batch-id portable`; require all pass.
- [ ] **Step 3:** Only after Step 2's full package command exits 0, write that literal command/date/result as `fullPackageSuite: passed` to each of the 15 owned records. Then set the batch package/focused aggregates, full-suite check, and batch status passed; rerun partial audit with literal `--batch-id portable` and require the terminal batch state to pass; commit/push with `rtk git commit -m "Gate portable presentation repairs"`.

## Batch 4 — Multi-orientation devices

### Task 51: Repair Frictitious Port-A-Board

**Files:** `Hangboards/frictitious-port-a-board/assets/primary.png`, `Hangboards/frictitious-port-a-board/assets/back.png`, `Hangboards/frictitious-port-a-board/assets/side.png`, `Hangboards/frictitious-port-a-board/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/18`, `/records/19`, then `/records/20`; batch `multi-orientation`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-port-a-board`; no focused extra; commit `Repair Frictitious Port-A-Board presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the three orientations.**

### Task 52: Repair Tension Flash Board

**Files:** `Hangboards/tension-flash-board/assets/primary.png`, `Hangboards/tension-flash-board/assets/three-edge-inverted.png`, `Hangboards/tension-flash-board/assets/two-edge-surface.png`, `Hangboards/tension-flash-board/assets/two-edge-inverted.png`, `Hangboards/tension-flash-board/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/52`, `/records/53`, `/records/54`, then `/records/55`; batch `multi-orientation`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-flash-board`; no focused extra; commit `Repair Tension Flash Board presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the four source-proved orientations.**

### Task 53: Repair Owl Climb Poker

**Files:** `Hangboards/owl-climb-poker/assets/face-a.png`, `Hangboards/owl-climb-poker/assets/face-b.png`, `Hangboards/owl-climb-poker/assets/face-c.png`, `Hangboards/owl-climb-poker/assets/face-d.png`, `Hangboards/owl-climb-poker/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/43`, `/records/44`, `/records/45`, then `/records/46`; batch `multi-orientation`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-owl-poker`; no focused extra; commit `Repair Owl Climb Poker presentations`.

- [ ] **Execute Steps R1–R8 sequentially for faces A, B, C, and D.**

### Task 54: Repair Trango Rock Prodigy Pivot

**Files:** `Hangboards/trango-rock-prodigy-pivot/assets/primary.png`, `Hangboards/trango-rock-prodigy-pivot/assets/orientation-2.png`, `Hangboards/trango-rock-prodigy-pivot/assets/orientation-3.png`, `Hangboards/trango-rock-prodigy-pivot/assets/orientation-4.png`, `Hangboards/trango-rock-prodigy-pivot/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/64`, `/records/65`, `/records/66`, then `/records/67`; batch `multi-orientation`; first-row bootstrap seed `urethane/multiOrientationDevice` with composition `lattice.mini-bar/primary` and material `soill.iron-palm-2/primary`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-trango-pivot`; focused extra `Tools/HangboardPackages/tests/test_coderabbit_mirrored_geometry.py`; commit `Repair Trango Rock Prodigy Pivot presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the four source-proved orientations.**

### Task 55: Repair YY Baguette Evo

**Files:** `Hangboards/yy-baguette-evo/assets/primary.png`, `Hangboards/yy-baguette-evo/assets/shallow-pairs.png`, `Hangboards/yy-baguette-evo/assets/central-30-25.png`, `Hangboards/yy-baguette-evo/assets/central-20-6.png`, `Hangboards/yy-baguette-evo/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/69`, `/records/70`, `/records/71`, then `/records/72`; batch `multi-orientation`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-baguette-evo`; no focused extra; commit `Repair YY Baguette Evo presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the four source-proved surfaces.**

### Task 56: Repair YY Penta Evo

**Files:** `Hangboards/yy-penta-evo/assets/primary.png`, `Hangboards/yy-penta-evo/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/76`; batch `multi-orientation`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-penta-evo`; no focused extra; commit `Repair YY Penta Evo presentation`.

- [ ] **Execute Steps R1–R8 for the one owned row.**

### Task 57: Repair YY TravelBoard

**Files:** `Hangboards/yy-travelboard/assets/primary.png`, `Hangboards/yy-travelboard/assets/reverse.png`, `Hangboards/yy-travelboard/board.json`, manifest, narrative.

**Interfaces:** matrix `/records/77` then `/records/78`; batch `multi-orientation`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-repair-travelboard`; no focused extra; commit `Repair YY TravelBoard presentations`.

- [ ] **Execute Steps R1–R8 sequentially for the two source-proved surfaces.**

### Task 58: Gate the multi-orientation batch

**Files:** manifest and narrative only.

- [ ] **Step 1:** Require exactly the 22 Batch 4 rows completed in addition to Batches 1–3, with accepted hashes/four Workbench checks/no blocks.
- [ ] **Step 2:** Run `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests`, `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, and partial audit with literal `--batch-id multi-orientation`; require all pass.
- [ ] **Step 3:** Only after Step 2's full package command exits 0, write that literal command/date/result as `fullPackageSuite: passed` to each of the 22 owned records. Then require cumulative totals 17 edits, 48 regenerations, zero removals, 19 byte-identical keeps, 85 current presentations, and zero Phase 2 blocks; set the batch package/focused aggregates, full-suite check, and batch status passed; rerun partial audit with literal `--batch-id multi-orientation` and require the terminal batch state to pass; commit/push with `rtk git commit -m "Gate multi-orientation presentation repairs"`.

---

### Task 59: Remove only the unsupported Mini Bar end presentation and retain all four grips

**Files:**
- Modify: `Hangboards/lattice-mini-bar/board.json`
- Delete: `Hangboards/lattice-mini-bar/assets/end.png`
- Preserve byte-for-byte: `Hangboards/lattice-mini-bar/assets/primary.png`
- Modify: `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py`
- Modify: manifest and narrative

**Interfaces:** owns only `/records/23` `lattice.mini-bar/end`; batch `mini-bar-removal`; context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-remove-mini-bar-end`; consumes the official and independent record-23 evidence proving one physical four-grip lengthwise bar; produces one `primary` presentation, the same four hold IDs, a directly reauthored lengthwise `mini-pinch`, an absent `end.png`, one historical removal, and no image-generation call.

- [ ] **Step 1: Establish sourced removal truth and backups.** Launch the persistent cleanup PTY with the literal context, register every rollback copy immediately, and keep that session alive through commit and cleanup. Reopen every official and independent record-23 URL and repeat each gap search. Record exact URL/role/date/result. Hash and ledger rollback copies of `primary.png`, `end.png`, and `board.json`. Require `primary.png` hash equal its historical keep hash. Set the removal batch and record action to `inProgress`; leave every removal-batch check pending.
- [ ] **Step 2: Add this exact failing package test.** Put the assertion in `test_board_catalog.py`; add parallel removal-history assertions to the audit test.

  ```python
  def test_lattice_mini_bar_retains_four_physical_grips_on_lengthwise_presentation() -> None:
      module = load_board_catalog_module()
      repository_root = Path(__file__).resolve().parents[3]
      package = module.load_board_package(repository_root / "Hangboards/lattice-mini-bar")
      assert [presentation.id for presentation in package.board.presentations] == ["primary"]
      assert package.board.presentations[0].asset_path == "assets/primary.png"
      assert {hold.id for hold in package.board.holds} == {
          "ergonomic-jug",
          "edge-10",
          "edge-20",
          "mini-pinch",
      }
      assert {hold.presentation_id for hold in package.board.holds} == {"primary"}
      assert not (repository_root / "Hangboards/lattice-mini-bar/assets/end.png").exists()
  ```

- [ ] **Step 3: Confirm RED.** Run only the two test files. Expected: current `end` presentation/file and `mini-pinch.presentationID == "end"` fail the new assertions.
- [ ] **Step 4: Directly reauthor the Mini Pinch on the lengthwise view.** Open `primary` in Workbench alongside the reopened straight-on and oblique Mini Bar evidence. Deliberately draw the `mini-pinch` canonical path over its source-proved lengthwise contact and set only `mini-pinch.presentationID` from `end` to `primary`; do not reuse, project, transform, align, or infer the old end-view path. Review `ergonomic-jug`, `edge-10`, `edge-20`, and `mini-pinch` in normal, all-active, individual, and hit-test modes. Record the new path commands and evidence pointers in the narrative.
- [ ] **Step 5: Remove only the unsupported presentation while remaining in progress.** Delete only the `end` presentation object and `Hangboards/lattice-mini-bar/assets/end.png`. Do not delete or rename any hold. Do not change the `primary` presentation object or PNG. Record `/records/23` evidence as confirmed, all four actual Workbench reviews as passed, the removed visual decision, and `simulatorReview.notApplicableRemovedPresentation` with the same source evidence. Keep `phase2Action.state` and removal-batch status `inProgress`, keep package/focused/full-suite checks pending, and keep all three removal `phase2Comparator` leaves null; deletion and visual review alone are not completion.
- [ ] **Step 6: Validate, then publish terminal state in command order.** Run the two focused test files; only after exit 0 write the literal command/date/result as the removal record's `focusedTests: passed`. Run the package validator; only after exit 0 write its literal command/date/result as `packageValidation: passed`. Run partial audit with `--batch-id mini-bar-removal` while the action remains `inProgress` and require that truthful intermediate state to pass. Then run the full HangboardPackages directory and final inventory; only after those exit 0 write `fullPackageSuite: passed`. Require 61 packages, 84 current presentations, 85 historical records, four Mini Bar holds on `primary`, absent `end.png`, unchanged `primary.png` hash, 19 byte-identical keeps, and one pending removal at this intermediate instant. Now, and only now, set the action `completed`, retain all three removal comparator leaves null, set all three removal-batch checks and batch status passed, and rerun partial audit with literal `--batch-id mini-bar-removal`; require one completed removal and zero pending/blocked removal actions.
- [ ] **Step 7: Commit/push and clean through the live session.** Stage only the declared files; commit `Retain Mini Bar grips while removing end presentation`; push; send `EXIT` to the persistent cleanup PTY, poll the same session to exit 0, and require `CLEANUP_OK`, exact owned paths absent, and the promoted package state retained.

### Task 60: Perform the direct cross-catalog visual and integrity review

**Files:** manifest and narrative only; no package changes.

**Interfaces:** context `/Users/asherlc/.paseo/worktrees/0h78jp9r/sincere-otter/.context/sincere-otter-cross-catalog-review`; consumes the final 84 presentation paths and all 85 historical records; produces a terminal review entry for every current presentation and an absent-presentation entry for `/records/23`.

- [ ] **Step 1: Own review artifacts.** Launch the persistent cleanup PTY with the literal context and keep it alive through review, commit, push, and cleanup; immediately register every montage or screenshot and require its ACK/hash before inspection or deletion.
- [ ] **Step 2: Inspect all current presentations directly.** In deterministic package/presentation order, open each of the 84 PNGs with `view_image`, compare the 65 replacements to reopened evidence and their final comparator, and compare the 19 keeps to their historical hashes. Record one terminal result per current key: `passed` with image hash/date/reviewer notes, or `blocked` with a concrete defect. Record `/records/23` as `notApplicableRemovedPresentation` only after checking the absent file/presentation and retained four-grip Mini Bar truth.
- [ ] **Step 3: Inspect the catalog as a cohort.** Require common off-white background, centered orthographic working surface, complete silhouettes, comparable scale/framing within form-factor cohorts, neutral light/shadow, no branding/text/watermarks, and source-proved material cues. Require 17 edited hashes, 48 regenerated hashes, 19 unchanged hashes, and one absent historical path.
- [ ] **Step 4: Route defects to their exclusive owners.** A defect reopens the owning product task and its following batch gate; do not alter package bytes in Task 60. The owner changes the prior accepted disposition to rejected with the cross-catalog reason, uses only the remaining slots in the original three-attempt limit, and finishes with exactly one accepted candidate. Exhausting attempt 3 blocks the owner and stops Phase 2. Repeat Task 60 only after the owner commits/pushes a new accepted candidate and the affected gate passes.
- [ ] **Step 5: Validate and close.** Run the full HangboardPackages tests, final inventory, and partial audit. Set `phase2.finalChecks.crossCatalogReview` passed only after all 85 entries are terminal and no defect remains. Commit/push with `rtk git commit -m "Review remediated presentation catalog"`; execute and verify exact cleanup.

## Isolated iOS direct-inspection recipe

Tasks 61–64 use `validate-hang-ten-ios` and read `docs/IOS_SIMULATOR_VALIDATION.md` plus `docs/IOS_RUNTIME_SERVICES.md` completely before creating a simulator. Each task creates exactly the two literal devices stated in its Interfaces line. Set `phase2_phone_device_type_id=com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro` and `phase2_tablet_device_type_id=com.apple.CoreSimulator.SimDeviceType.iPad-Pro-11-inch-M4`; require both exact identifiers in `xcrun simctl list devicetypes -j`. Set `phase2_runtime_id` to the final item after filtering `xcrun simctl list runtimes -j` to available iOS runtimes and sorting numeric `version` components ascending; require exactly one non-null selected identifier. Commit the three literal identifiers and both JSON-query commands as environment evidence. Install the skill's exact pending/owned manifest traps before either `simctl create`, append each validated UUID to pending before owned, and use those two explicit UUIDs for every later command. Never address `booted`.

```zsh
phase2_phone_device_type_id='com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro'
phase2_tablet_device_type_id='com.apple.CoreSimulator.SimDeviceType.iPad-Pro-11-inch-M4'
phase2_device_types_json="$(rtk xcrun simctl list devicetypes -j)"
print -r -- "$phase2_device_types_json" | rtk jq -e --arg id "$phase2_phone_device_type_id" \
  'any(.devicetypes[]; .identifier == $id)'
print -r -- "$phase2_device_types_json" | rtk jq -e --arg id "$phase2_tablet_device_type_id" \
  'any(.devicetypes[]; .identifier == $id)'
phase2_runtime_id="$(rtk xcrun simctl list runtimes -j | rtk jq -er \
  '[.runtimes[] | select(.isAvailable == true and (.name | startswith("iOS "))) \
    | {identifier, numericVersion: (.version | split(".") | map(tonumber))}] \
   | sort_by(.numericVersion) | last | .identifier')"
test -n "$phase2_runtime_id"
```

Build once per task for the explicit phone destination, with signing enabled and an 1,800-second hard bound:

```bash
rtk perl -e 'alarm 1800; exec @ARGV' xcodebuild \
  -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$phase2_phone_uuid" \
  -derivedDataPath .context/DerivedData build-for-testing
```

`phase2_phone_uuid` is assigned only from the validated `simctl create` result for the task's exact Phone resource. A timeout or nonzero exit sets every unreviewed owned record to `blocked`, records the command/result, commits/pushes that terminal state, runs archive cleanup, and stops the task. Only after the bounded build command exits 0, write that literal command/date/result as `buildForTesting: passed` to every image-repair record owned by that simulator task; Task 64 writes the same successful final-catalog build evidence to removal `/records/23` as well. Install the exact built app on both UUIDs, verify each app container and built/installed executable hash, and launch by explicit UUID.

For each owned image-repair record, inspect both devices directly and record a separate run. Use `HANGTEN_REVIEW_BOARD_PICKER=1` to open the picker, select `boardPicker.board.<packageID>`, and prove the catalog/normal view. Open a compatible plan and workout with the review routes when the repository has a plan whose declared board compatibility includes that package; otherwise record only the plan flow as `notApplicableNoCompatiblePlan` and cite the catalog query that returned no plan. Inspect inactive and active/highlight states, every logical hold/piece individually, and hit-test alignment. Open every presentation in source order; only a package with exactly one current presentation records selector `notApplicableSinglePresentation`. Capture at least one inactive, one all-active, one individual-hold, and one selector image per multi-presentation package on each device; hash every capture before cleanup. All other applicable flows must be `passed`. A presentation defect reopens its product task under Task 60's remaining-attempt rule, then repeats the affected batch gate, Task 60, and this simulator task; the QA task itself never changes package bytes.

After each presentation's phone and tablet exercise actually completes, write that record's `simulatorReview` immediately with its exact runs, terminal flows, and capture hashes; do not prefill later records from an earlier presentation. After the last record, run partial audit and require every owned `simulatorReview.state == passedDirectInspection`, exactly one phone/one tablet run, all seven terminal flows, nonempty capture hashes, and literal environment IDs. Commit/push manifest/narrative before cleanup. Invoke the skill's archive cleanup; require both exact UUIDs absent, pending/owned entries consumed, and `.context/DerivedData`, `.context/workout-raw.png`, and `.context/workout-landscape.png` absent. Preserve manifests and fail if archive cleanup fails; never delete a shared or unknown simulator.

### Task 61: Directly inspect Batch 1 presentations on iPhone and iPad

**Files:** manifest and narrative only.

**Interfaces:** simulator names `Hang Ten Paseo sincere-otter Task-61 Phone` and `Hang Ten Paseo sincere-otter Task-61 Tablet`; owns exactly `/records/11`, `/records/13`, `/records/28`, `/records/29`, `/records/33`, `/records/35`, `/records/48`, `/records/49`, `/records/50`, `/records/62`, `/records/68`, `/records/12`, `/records/14`, `/records/26`, `/records/39`, `/records/83`, `/records/84`; commit `Validate nonwood presentation repairs on iOS`.

- [ ] **Execute the isolated iOS direct-inspection recipe for all 17 records, commit/push, and prove cleanup.**

### Task 62: Directly inspect Batch 2 presentations on iPhone and iPad

**Files:** manifest and narrative only.

**Interfaces:** simulator names `Hang Ten Paseo sincere-otter Task-62 Phone` and `Hang Ten Paseo sincere-otter Task-62 Tablet`; owns exactly `/records/1`, `/records/27`, `/records/36`, `/records/38`, `/records/56`, `/records/57`, `/records/63`, `/records/79`, `/records/80`, `/records/81`, `/records/82`; commit `Validate wood presentation repairs on iOS`.

- [ ] **Execute the isolated iOS direct-inspection recipe for all 11 records, commit/push, and prove cleanup.**

### Task 63: Directly inspect Batch 3 presentations on iPhone and iPad

**Files:** manifest and narrative only.

**Interfaces:** simulator names `Hang Ten Paseo sincere-otter Task-63 Phone` and `Hang Ten Paseo sincere-otter Task-63 Tablet`; owns exactly `/records/3`, `/records/4`, `/records/5`, `/records/6`, `/records/7`, `/records/8`, `/records/9`, `/records/16`, `/records/17`, `/records/30`, `/records/31`, `/records/24`, `/records/25`, `/records/34`, `/records/47`; commit `Validate portable presentation repairs on iOS`.

- [ ] **Execute the isolated iOS direct-inspection recipe for all 15 records, commit/push, and prove cleanup.**

### Task 64: Directly inspect Batch 4 presentations on iPhone and iPad

**Files:** manifest and narrative only.

**Interfaces:** simulator names `Hang Ten Paseo sincere-otter Task-64 Phone` and `Hang Ten Paseo sincere-otter Task-64 Tablet`; owns exactly `/records/18`, `/records/19`, `/records/20`, `/records/52`, `/records/53`, `/records/54`, `/records/55`, `/records/43`, `/records/44`, `/records/45`, `/records/46`, `/records/64`, `/records/65`, `/records/66`, `/records/67`, `/records/69`, `/records/70`, `/records/71`, `/records/72`, `/records/76`, `/records/77`, `/records/78`; also rechecks the current Mini Bar `primary` catalog/normal/active/individual/hit-test behavior, writes removal `/records/23` `buildForTesting` only after this task's bounded build passes, and leaves its removed presentation `simulatorReview` at sourced `notApplicableRemovedPresentation`; commit `Validate multi-orientation presentation repairs on iOS`.

- [ ] **Execute the isolated iOS direct-inspection recipe for all 22 image records and current Mini Bar primary.** After this task's build and all per-record reviews pass, require all four task build records and all 65 repaired-record simulator reviews terminal; then set root `phase2.finalChecks.buildForTesting` and `phase2.finalChecks.simulatorReview` passed with the exact four build results and per-record review summary. Commit/push and prove cleanup.

### Task 65: Run the final Phase 2 catalog gate

**Files:** manifest and narrative only.

**Interfaces:** consumes all preceding commits and produces the only `phase2Final` success state; no package, app, routine, or training-plan change.

- [ ] **Step 1: Run partial validation before changing any final check.** Run `rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json --phase2-partial`. Require every one of the 65 repair records to have confirmed evidence, completed action, exactly one accepted candidate, passed transient input/candidate verification, accepted/on-disk hash equality, an accepted singular final comparator (including an accepted bootstrap seed's self baseline), four Workbench passes, per-record package/focused/full-suite/build evidence, two direct simulator runs, and no blocked flow. Require every preflight capability artifact still `capabilityProbeRejected`, terminal/deleted, and hash/path-disjoint from all now-completed production state. Require record 23 completed removal with confirmed evidence, per-record package/focused/full-suite/build evidence, and valid removed-presentation N/A. Require zero pending or blocked Phase 2 actions while preserving all five Phase 1 gap strings, all 17 source-supported keep hashes/dimensions/accepted decisions, and the two evidence-blocked keep null hashes/dimensions/decisions unchanged. Leave the four Task 65-owned final checks pending during this command.
- [ ] **Step 2: Run the actual final checks while their fields remain pending.** Execute these commands with the four check fields still pending:

  ```bash
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  phase2_live_owned_paths="$(rtk find .context -maxdepth 1 \( -name '*sincere-otter*' -o -name DerivedData -o -name workout-raw.png -o -name workout-landscape.png \) -print)"
  test -z "$phase2_live_owned_paths"
  rtk uv run python -c 'from pathlib import Path; import re; files=(Path("docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json"),Path("docs/source-audits/2026-08-30-hangboard-presentation-remediation.md")); text="\n".join(p.read_text() for p in files); paths=sorted(set(re.findall(r"/Users/asherlc/(?:\.codex/generated_images|\.paseo/worktrees/0h78jp9r/sincere-otter/\.context/sincere-otter-[^/\s`\"\x27]+)[^\s`\"\x27]*",text))); live=[p for p in paths if Path(p).exists()]; assert not live, live'
  rtk xcrun simctl list devices -j | rtk jq -e '[.devices[][] | select(.name | startswith("Hang Ten Paseo sincere-otter "))] | length == 0'
  ```

  The empty `find`, path assertion, and simulator query together check every committed task-owned ledger path, registered generated-image path, simulator UUID/name and pending/owned manifest path, and exact task context is absent while leaving shared or unknown resources untouched. Require every command to exit 0; require 61 packages, 85 historical records, 84 current presentations, 19 keep records whose PNG hashes still equal Phase 1, 17 completed edits, 48 completed regenerations, one completed removal, absent Mini Bar `end`, retained Mini Bar `primary` plus all four physical grips, package-ID set equality without order rewriting, and a clean owned-resource scan.
- [ ] **Step 3: Record exactly the four Task 65-owned final checks from actual results.** Write `manifestValidation: passed` from Step 1's literal partial-audit command/date/result, `packageTestSuite: passed` from Step 2's literal full-suite command/date/result, `finalInventory: passed` from Step 2's literal inventory command/date/result, and `contextCleanup: passed` from Step 2's literal cleanup-scan command/date/result. Do not alter `crossCatalogReview`, which Task 60 already passed, or `buildForTesting`/`simulatorReview`, whose per-record and aggregate evidence Tasks 61–64 already passed. No check may be written before its command exits 0.
- [ ] **Step 4: Only now run the final validator and unrelated-code proof.**

  ```bash
  phase2_baseline_sha="$(rtk awk -F': ' '/^Phase 2 baseline SHA: / {print $2; exit}' \
    docs/source-audits/2026-08-30-hangboard-presentation-remediation.md)"
  test "${#phase2_baseline_sha}" -eq 40
  rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards \
    --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
    --phase2-final
  rtk git diff --name-only "$phase2_baseline_sha..HEAD" -- TrainingPlans HangTen
  ```

  Expected: Phase 2 report is 20 canvas classes, 65 covered repairs, 22–66 terminal rejected capability artifacts, zero artifact/production overlaps, 19 keeps, 17 edits, 48 regenerations, one removal, two historical evidence-blocked keeps, zero pending actions, and zero blocked actions; the unrelated-code diff is empty. This is the first and only `--phase2-final` invocation in Task 65.
- [ ] **Step 5: Review, commit, and push.** Review the final diff plus manifest/narrative consistency. Stage only manifest and narrative, commit `Complete hangboard presentation remediation phase two`, and push. Record the pushed SHA and final validator output in the handoff.
