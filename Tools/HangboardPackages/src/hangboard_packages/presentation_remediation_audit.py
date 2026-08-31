"""Fail-closed parsing and validation for presentation remediation manifests."""

from __future__ import annotations

import hashlib
import json
import re
import struct
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .board_catalog import (
    BoardInventory,
    is_board_identifier,
)

_MATERIALS = frozenset(
    {
        "wood",
        "moldedPlastic",
        "resin",
        "urethane",
        "metal",
        "stoneMineralComposite",
        "ropeCord",
        "mixedOther",
    }
)
_FORM_FACTORS = frozenset(
    {
        "fullWidthFixedBoard",
        "splitFixedBoard",
        "compactFixedBoard",
        "liftingEdge",
        "suspendedPortable",
        "reversiblePortable",
        "multiOrientationDevice",
    }
)
_DECISIONS = frozenset(
    {
        "keep",
        "regenerate",
        "edit",
        "removeUnsupportedPresentation",
        "splitPhysicalRevision",
    }
)
_FINDING_KEYS = frozenset(
    {
        "productLikeness",
        "material",
        "topology",
        "headOnPerspective",
        "smoothing",
        "framing",
        "crossCatalogConsistency",
    }
)
_FINDING_ORDER = (
    "productLikeness",
    "material",
    "topology",
    "headOnPerspective",
    "smoothing",
    "framing",
    "crossCatalogConsistency",
)
_OUTCOMES = frozenset({"conforms", "nonconforming", "uncertain", "notApplicable"})
_OFFICIAL_KINDS = frozenset(
    {
        "officialProductPage",
        "officialManual",
        "officialCatalog",
        "archivedFirstParty",
        "officialImage",
    }
)
_INDEPENDENT_KINDS = frozenset({"retailer", "review", "ownerPhoto"})
_PHASE1_CHECKS = frozenset(
    {"manifestValidation", "packageValidation", "packageTestSuite", "hangboardsDiff"}
)
_WORKBENCH_CHECKS = frozenset({"normal", "allActive", "individualHolds"})
_VALIDATION_CHECKS = frozenset(
    {
        "packageValidation",
        "focusedTests",
        "fullPackageSuite",
        "buildForTesting",
        "simulatorReview",
    }
)
_PRESENTATION_CHECK_STATUSES = frozenset({"pending", "passed", "failed"})
_PHASE1_CHECK_STATUSES = frozenset({"pending", "passed"})
_BOUNDED_EDIT_FINDINGS = frozenset(
    {
        "material",
        "headOnPerspective",
        "smoothing",
        "framing",
        "crossCatalogConsistency",
    }
)
_FAILURE_OUTCOMES = frozenset({"nonconforming", "uncertain"})
_PLANNED_AUDIT_DATE = date(2026, 8, 30)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SEARCH_HOSTS = frozenset(
    {
        "bing.com",
        "duckduckgo.com",
        "google.com",
        "search.brave.com",
        "search.yahoo.com",
        "yandex.com",
    }
)
_NAMED_REVISION = re.compile(
    r"\b(?:revision|model|version|generation|mk)\s*[a-z0-9]", re.IGNORECASE
)
_STYLE_ONLY_TERMS = frozenset(
    {"framing", "lighting", "background", "texture", "smoothing", "edge treatment"}
)

_PHASE2_CHECK_STATUSES = frozenset(
    {"pending", "passed", "failed", "blocked", "notRequired"}
)
_ACTION_STATES = frozenset(
    {"notRequired", "pending", "inProgress", "completed", "blocked"}
)
_EVIDENCE_RESULTS = frozenset({"notRequired", "pending", "confirmed", "blocked"})
_INPUT_TYPES = frozenset(
    {"officialEvidence", "independentEvidence", "currentAsset", "comparator"}
)
_BYTE_STATUSES = frozenset({"pending", "passed", "failed"})
_GENERATION_MODES = frozenset({"none", "builtInEdit", "builtInGenerate"})
_CANDIDATE_DISPOSITIONS = frozenset({"accepted", "rejected"})
_COMPARATOR_MODES = frozenset({"readyBaseline", "cohortBootstrapBaseline"})
_BOOTSTRAP_STATUSES = frozenset(
    {"selected", "acceptedCohortBaseline", "blocked"}
)
_BOOTSTRAP_AXIS_NAMES = frozenset(
    {"compositionFramingScale", "materialTextureLighting"}
)
_SIMULATOR_STATES = frozenset(
    {"pending", "passedDirectInspection", "notApplicableRemovedPresentation", "blocked"}
)
_FLOW_STATES = frozenset(
    {"passed", "notApplicableSinglePresentation", "notApplicableNoCompatiblePlan", "blocked"}
)
_SIMULATOR_FLOW_KEYS = frozenset(
    {"catalog", "plan", "normal", "active", "individualHold", "presentationSelector", "hitTest"}
)
_SINGULAR_COMPARATOR_REASON = (
    "Accepted singular style baseline: framing, scale, background, lighting, "
    "texture frequency, smoothing, and edge treatment only; no product geometry."
)
_COHORT_BASELINE_REASON = (
    "Accepted cohort bootstrap baseline after direct evidence, Workbench, package, "
    "and visual review; style-only for downstream use, no geometry."
)
_BOOTSTRAP_SHARED_RENDER_CONTRACT = (
    "Common off-white studio background; centered orthographic working-surface view; "
    "complete uncropped product; neutral lighting; restrained contact shadows; "
    "clean antialiasing; cohort-consistent framing; source-proved material cues only."
)
_BOOTSTRAP_SELECTION_RULE = (
    "Accepted assets only: earliest exact-form-factor asset for composition/framing/scale; "
    "earliest asset sharing the seed material-family token for texture/lighting; "
    "missing axes are explicit; no axis supplies product geometry."
)
_BOOTSTRAP_COMPOSITION_REASON = (
    "Style axis only: composition, framing, scale, background, and lighting balance "
    "from an accepted exact-form-factor catalog asset; no product geometry or material transfer."
)
_BOOTSTRAP_MATERIAL_REASON = (
    "Style axis only: texture frequency, finish restraint, and lighting response for "
    "the matched material-family token; no product geometry or component transfer."
)
_PREFLIGHT_COMPOSITION_REASON = (
    "Pre-Task-9 accepted keep used only for disposable capability-probe composition, "
    "framing, and scale; no material or product geometry transfer."
)
_PREFLIGHT_MATERIAL_CONTRACT = (
    "Material appearance comes only from freshly reopened official/independent evidence; "
    "the shared render contract supplies neutral lighting and no material comparator."
)
_KEEP_PHASE2_NOTE = "Phase 1 keep; Phase 2 product repair does not apply."
_PENDING_PHASE2_NOTE = "Phase 2 evidence review pending."


class PresentationValidationMode(str, Enum):
    SOURCE_RECLASSIFICATION = "sourceReclassification"
    PHASE2_PREFLIGHT = "phase2Preflight"
    PHASE2_PARTIAL = "phase2Partial"
    PHASE2_FINAL = "phase2Final"


_PREFLIGHT_REFERENCES = {
    "preflight-full-width-composition": (
        "beastmaker-2000/primary",
        "Hangboards/beastmaker-2000/assets/primary.png",
        "2a5dfd439bd67485a16d764b7c8aaf24cba22c42f4ee2b4657cb8842d743bb68",
    ),
    "preflight-multi-orientation-composition": (
        "lattice.mini-bar/primary",
        "Hangboards/lattice-mini-bar/assets/primary.png",
        "db351c7c617420b84550e64d6685c8c98e60da9529feb3697bd7435af5f751fc",
    ),
}
_SOURCE_SUPPORTED_KEEP_KEYS = (
    "beastmaker-2000/primary",
    "frictitious.megalith/primary",
    "lattice-triple-rung/primary",
    "lattice.mini-bar/primary",
    "metolius.prime-rib/front",
    "metolius.wood-grips-deluxe-ii/front",
    "nature.stone-hanger-mini-karma8a/primary",
    "nature.stone-hanger-mini/primary",
    "nature.stone-hanger-mini/side",
    "target10a.linebreaker-base/primary",
    "tension.grindstone/primary",
    "tension.honestone/primary",
    "tension.whetstone/primary",
    "the-hangboard.the-hangboard/front",
    "yy.baguette-evo/rounded-tray",
    "yy.baguette/stepped-face",
    "yy.baguette/reverse-face",
)
_HISTORICAL_BLOCKED_KEEP_KEYS = (
    "aelith.cyclops-011/primary",
    "dewoodstok-woodbord/primary",
)
_PREFLIGHT_ASSIGNMENTS = (
    ("1000x1000-edit-mxedge-large", 1000, 1000, "edit", "lattice.mxedge-lift-large/primary", None),
    ("1000x259-edit-beastmaker-1000", 1000, 259, "edit", "beastmaker-1000/primary", "preflight-full-width-composition"),
    ("1233x435-generate-trango-training-center", 1233, 435, "generate", "trango.rock-prodigy-training-center/primary", None),
    ("1254x1254-generate-soill-split", 1254, 1254, "generate", "soill.split-palm/primary", None),
    ("1440x1440-edit-port-a-board", 1440, 1440, "edit", "frictitious.port-a-board/primary", "preflight-multi-orientation-composition"),
    ("1503x394-edit-escape-beta", 1503, 394, "edit", "escape-beta-22/primary", "preflight-full-width-composition"),
    ("1536x1024-edit-crimptonite", 1536, 1024, "edit", "crimptonite.helium-mobile/primary", None),
    ("1536x1024-generate-captain-dual", 1536, 1024, "generate", "captain-fingerfood.dual/primary", None),
    ("1537x1023-edit-evolv", 1537, 1023, "edit", "evolv-kilter-basic-long/primary", "preflight-full-width-composition"),
    ("1537x1023-generate-grindstone-original", 1537, 1023, "generate", "tension.grindstone-original/primary", "preflight-full-width-composition"),
    ("1614x975-generate-simulator", 1614, 975, "generate", "metolius.simulator-3d/primary", "preflight-full-width-composition"),
    ("1654x951-edit-grindstone-pro", 1654, 951, "edit", "tension.grindstone-pro/primary", "preflight-full-width-composition"),
    ("1672x941-edit-light-rail", 1672, 941, "edit", "metolius.light-rail-2/15mm-side", None),
    ("1697x1200-edit-moon", 1697, 1200, "edit", "moon.armstrong/primary", "preflight-full-width-composition"),
    ("1717x916-generate-climbers-edge", 1717, 916, "generate", "metolius.climbers-edge/primary", "preflight-full-width-composition"),
    ("1774x457-generate-wood-grips-compact", 1774, 457, "generate", "metolius.wood-grips-compact-ii/primary", "preflight-full-width-composition"),
    ("1774x887-generate-escape-unlimited", 1774, 887, "generate", "escape.unlimited/primary", "preflight-full-width-composition"),
    ("1842x854-generate-nug-reverse", 1842, 854, "generate", "frictitious.nug/reverse", None),
    ("1980x300-edit-poker", 1980, 300, "edit", "owl-climb.poker/face-a", "preflight-multi-orientation-composition"),
    ("1980x495-generate-diamond-finger", 1980, 495, "generate", "mammut.diamond-finger/primary", "preflight-full-width-composition"),
    ("2081x755-generate-zlag-evo", 2081, 755, "generate", "zlagboard.evo/primary", "preflight-full-width-composition"),
    ("2112x745-generate-zlag-pro", 2112, 745, "generate", "zlagboard.pro/primary", "preflight-full-width-composition"),
)
_PREFLIGHT_COVERAGE = {
    (1000, 1000): ("lattice.mxedge-lift-large/primary", "lattice.mxedge-lift-small/primary"),
    (1000, 259): ("beastmaker-1000/primary",),
    (1233, 435): ("trango.rock-prodigy-training-center/primary",),
    (1254, 1254): ("soill.split-palm/primary",),
    (1440, 1440): ("frictitious.port-a-board/primary", "frictitious.port-a-board/back", "frictitious.port-a-board/side"),
    (1503, 394): ("escape-beta-22/primary",),
    (1536, 1024): ("captain-fingerfood.dual/primary", "captain-fingerfood.dual/reverse", "captain-fingerfood.pocket/primary", "captain-fingerfood.unlevel/primary", "captain-fingerfood.unlevel/reverse", "crimptonite.helium-mobile/primary", "crimptonite.helium-mobile/reverse", "frictitious.nug/primary", "metolius.light-rail-2/20mm-side", "metolius.rock-rings-3d/front-pair", "plateau.lifting-edge/primary", "soill.iron-palm-2/primary", "soill.training-tiles/primary", "tension.flash-board/three-edge-upright", "tension.flash-board/three-edge-inverted", "trango.rock-prodigy-forge/primary", "trango.rock-prodigy-natural/primary", "yy.baguette-evo/central-30-25", "yy.penta-evo/front-pair", "yy.travelboard/front-25-15"),
    (1537, 1023): ("evolv-kilter-basic-long/primary", "tension.grindstone-original/primary"),
    (1614, 975): ("metolius.simulator-3d/primary",),
    (1654, 951): ("tension.grindstone-pro/primary",),
    (1672, 941): ("metolius.light-rail-2/15mm-side",),
    (1697, 1200): ("moon.armstrong/primary",),
    (1717, 916): ("metolius.climbers-edge/primary",),
    (1774, 457): ("metolius.wood-grips-compact-ii/primary",),
    (1774, 887): ("escape.unlimited/primary", "frictitious.doormount-pro-7/primary", "metolius.contact/primary", "metolius.foundry/front", "metolius.project/primary", "nature.stoak-board-iii/primary", "tension.flash-board/two-edge-upright", "tension.flash-board/two-edge-inverted", "trango.rock-prodigy-pivot/orientation-1", "trango.rock-prodigy-pivot/orientation-2", "trango.rock-prodigy-pivot/orientation-3", "trango.rock-prodigy-pivot/orientation-4", "yy.baguette-evo/paired-25-20-15-10", "yy.baguette-evo/paired-12-8-6", "yy.baguette-evo/central-20-6", "yy.travelboard/reverse-10", "yy.verticalboard-evo/primary", "yy.verticalboard-first/primary", "yy.verticalboard-light/primary", "yy.verticalboard-one/primary"),
    (1842, 854): ("frictitious.nug/reverse",),
    (1980, 300): ("owl-climb.poker/face-a", "owl-climb.poker/face-b", "owl-climb.poker/face-c", "owl-climb.poker/face-d"),
    (1980, 495): ("mammut.diamond-finger/primary",),
    (2081, 755): ("zlagboard.evo/primary",),
    (2112, 745): ("zlagboard.pro/primary",),
}

_BOOTSTRAP_SEEDS = {
    "moldedPlastic/fullWidthFixedBoard": ("escape-beta-22/primary", "beastmaker-2000/primary", None, ("materialTextureLighting",)),
    "resin/fullWidthFixedBoard": ("evolv-kilter-basic-long/primary", "beastmaker-2000/primary", None, ("materialTextureLighting",)),
    "urethane/fullWidthFixedBoard": ("soill.iron-palm-2/primary", "beastmaker-2000/primary", None, ("materialTextureLighting",)),
    "urethane/splitFixedBoard": ("soill.split-palm/primary", None, "soill.iron-palm-2/primary", ("compositionFramingScale",)),
    "wood/splitFixedBoard": ("trango.rock-prodigy-natural/primary", "soill.split-palm/primary", "beastmaker-2000/primary", ()),
    "wood/reversiblePortable": ("captain-fingerfood.dual/primary", None, "beastmaker-2000/primary", ("compositionFramingScale",)),
    "wood/liftingEdge": ("lattice.mxedge-lift-large/primary", None, "beastmaker-2000/primary", ("compositionFramingScale",)),
    "resin/suspendedPortable": ("metolius.rock-rings-3d/front-pair", None, "evolv-kilter-basic-long/primary", ("compositionFramingScale",)),
    "urethane/multiOrientationDevice": ("trango.rock-prodigy-pivot/orientation-1", "lattice.mini-bar/primary", "soill.iron-palm-2/primary", ()),
}

_BATCH_RECORD_KEYS = {
    "nonwood-fixed": (
        "escape-beta-22/primary", "evolv-kilter-basic-long/primary", "metolius.contact/primary",
        "metolius.foundry/front", "metolius.project/primary", "metolius.simulator-3d/primary",
        "soill.iron-palm-2/primary", "soill.split-palm/primary", "soill.training-tiles/primary",
        "trango.rock-prodigy-forge/primary", "trango.rock-prodigy-training-center/primary",
        "escape.unlimited/primary", "frictitious.doormount-pro-7/primary", "mammut.diamond-finger/primary",
        "nature.stoak-board-iii/primary", "zlagboard.evo/primary", "zlagboard.pro/primary",
    ),
    "wood-fixed": (
        "beastmaker-1000/primary", "metolius.climbers-edge/primary", "metolius.wood-grips-compact-ii/primary",
        "moon.armstrong/primary", "tension.grindstone-original/primary", "tension.grindstone-pro/primary",
        "trango.rock-prodigy-natural/primary", "yy.verticalboard-evo/primary", "yy.verticalboard-first/primary",
        "yy.verticalboard-light/primary", "yy.verticalboard-one/primary",
    ),
    "portable": (
        "captain-fingerfood.dual/primary", "captain-fingerfood.dual/reverse", "captain-fingerfood.pocket/primary",
        "captain-fingerfood.unlevel/primary", "captain-fingerfood.unlevel/reverse", "crimptonite.helium-mobile/primary",
        "crimptonite.helium-mobile/reverse", "frictitious.nug/primary", "frictitious.nug/reverse",
        "metolius.light-rail-2/20mm-side", "metolius.light-rail-2/15mm-side",
        "lattice.mxedge-lift-large/primary", "lattice.mxedge-lift-small/primary",
        "metolius.rock-rings-3d/front-pair", "plateau.lifting-edge/primary",
    ),
    "multi-orientation": (
        "frictitious.port-a-board/primary", "frictitious.port-a-board/back", "frictitious.port-a-board/side",
        "tension.flash-board/three-edge-upright", "tension.flash-board/three-edge-inverted",
        "tension.flash-board/two-edge-upright", "tension.flash-board/two-edge-inverted",
        "owl-climb.poker/face-a", "owl-climb.poker/face-b", "owl-climb.poker/face-c", "owl-climb.poker/face-d",
        "trango.rock-prodigy-pivot/orientation-1", "trango.rock-prodigy-pivot/orientation-2",
        "trango.rock-prodigy-pivot/orientation-3", "trango.rock-prodigy-pivot/orientation-4",
        "yy.baguette-evo/paired-25-20-15-10", "yy.baguette-evo/paired-12-8-6",
        "yy.baguette-evo/central-30-25", "yy.baguette-evo/central-20-6",
        "yy.penta-evo/front-pair", "yy.travelboard/front-25-15", "yy.travelboard/reverse-10",
    ),
    "mini-bar-removal": ("lattice.mini-bar/end",),
}
_BATCH_IDS = tuple(_BATCH_RECORD_KEYS)
_REPAIR_TASK_BY_KEY = {
    **{key: task for task, key in zip(range(10, 27), _BATCH_RECORD_KEYS["nonwood-fixed"], strict=True)},
    **{key: task for task, key in zip(range(28, 39), _BATCH_RECORD_KEYS["wood-fixed"], strict=True)},
    **{key: task for task, keys in ((40, _BATCH_RECORD_KEYS["portable"][:2]), (41, _BATCH_RECORD_KEYS["portable"][2:3]), (42, _BATCH_RECORD_KEYS["portable"][3:5]), (43, _BATCH_RECORD_KEYS["portable"][5:7]), (44, _BATCH_RECORD_KEYS["portable"][7:9]), (45, _BATCH_RECORD_KEYS["portable"][9:11]), (46, _BATCH_RECORD_KEYS["portable"][11:12]), (47, _BATCH_RECORD_KEYS["portable"][12:13]), (48, _BATCH_RECORD_KEYS["portable"][13:14]), (49, _BATCH_RECORD_KEYS["portable"][14:])) for key in keys},
    **{key: task for task, keys in ((51, _BATCH_RECORD_KEYS["multi-orientation"][:3]), (52, _BATCH_RECORD_KEYS["multi-orientation"][3:7]), (53, _BATCH_RECORD_KEYS["multi-orientation"][7:11]), (54, _BATCH_RECORD_KEYS["multi-orientation"][11:15]), (55, _BATCH_RECORD_KEYS["multi-orientation"][15:19]), (56, _BATCH_RECORD_KEYS["multi-orientation"][19:20]), (57, _BATCH_RECORD_KEYS["multi-orientation"][20:])) for key in keys},
    "lattice.mini-bar/end": 59,
}


class PresentationRemediationAuditError(ValueError):
    """Raised for malformed or package-inconsistent presentation manifests."""


@dataclass(frozen=True)
class PresentationRemediationSource:
    url: str
    publisher: str
    source_kind: str
    reviewed_at: date
    revision_applicability: str
    image_role: str
    supported_claim: str


@dataclass(frozen=True)
class PresentationFinding:
    outcome: str
    explanation: str


@dataclass(frozen=True)
class PresentationComparator:
    asset_path: str | None
    material_match: str | None
    form_factor_match: str | None
    reason: str | None
    baseline_gap: str | None


@dataclass(frozen=True)
class PresentationCurrentAsset:
    sha256: str
    width_pixels: int
    height_pixels: int


@dataclass(frozen=True)
class PresentationCheck:
    status: str
    evidence: str | None


@dataclass(frozen=True)
class Phase1Check:
    status: str
    command: str | None


@dataclass(frozen=True)
class PresentationFinalState:
    accepted_asset_sha256: str | None
    final_dimensions: tuple[int, int] | None
    visual_reviewer_decision: str
    workbench_review: Mapping[str, PresentationCheck]
    validation: Mapping[str, PresentationCheck]


@dataclass(frozen=True)
class PresentationEvidence:
    official: tuple[PresentationRemediationSource, ...]
    independent: tuple[PresentationRemediationSource, ...]
    official_evidence_gap: str | None
    independent_evidence_gap: str | None


@dataclass(frozen=True)
class PresentationGeneration:
    prompt: str | None
    source_images: tuple[str, ...]
    current_asset_role: str | None
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class ByteVerification:
    status: str
    checked_at: datetime | None
    command: str | None
    observed_sha256: str | None


@dataclass(frozen=True)
class GenerationSourceInput:
    id: str
    source_type: str
    evidence_pointer: str | None
    source_url: str | None
    asset_path: str | None
    role: str
    sha256: str
    supplied_to_imagegen: bool
    byte_verification: ByteVerification


@dataclass(frozen=True)
class RequiredCanvas:
    width_pixels: int
    height_pixels: int


@dataclass(frozen=True)
class CandidateProvenance:
    tool: str
    untouched_model_output: bool
    post_processing: str


@dataclass(frozen=True)
class GenerationCandidate:
    attempt: int
    transient_output_path: str
    sha256: str
    width_pixels: int
    height_pixels: int
    disposition: str
    reason: str
    provenance: CandidateProvenance
    byte_verification: ByteVerification


@dataclass(frozen=True)
class Phase2Generation:
    mode: str
    prompt: str | None
    required_canvas: RequiredCanvas | None
    source_inputs: tuple[GenerationSourceInput, ...]
    current_asset_role: str | None
    candidates: tuple[GenerationCandidate, ...]


@dataclass(frozen=True)
class Phase2Action:
    state: str
    blocked_reason: str | None


@dataclass(frozen=True)
class Phase2EvidenceReview:
    result: str
    reviewed_at: datetime | None
    official_urls_reopened: tuple[str, ...]
    independent_urls_reopened: tuple[str, ...]
    evidence_gap_searches_repeated: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class ComparatorSelection:
    mode: str
    asset_path: str
    source_record_key: str
    accepted_asset_sha256: str
    reason: str
    selected_at: datetime


@dataclass(frozen=True)
class BootstrapComparatorAxis:
    axis: str
    asset_path: str
    source_record_key: str
    accepted_asset_sha256: str
    matched_material_tokens: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class BootstrapReviewChecks:
    evidence_review: PresentationCheck
    visual_review: PresentationCheck
    workbench_review: PresentationCheck
    package_validation: PresentationCheck


@dataclass(frozen=True)
class BootstrapComparatorSet:
    cohort_id: str
    seed_record_key: str
    status: str
    composition_framing_scale: BootstrapComparatorAxis | None
    material_texture_lighting: BootstrapComparatorAxis | None
    absent_axes: tuple[str, ...]
    official_evidence_input_ids: tuple[str, ...]
    independent_evidence_input_ids: tuple[str, ...]
    shared_render_contract: str
    selection_rule: str
    selected_at: datetime
    accepted_at: datetime | None
    review_checks: BootstrapReviewChecks
    blocked_reason: str | None


@dataclass(frozen=True)
class Phase2Comparator:
    generation_time: ComparatorSelection | None
    bootstrap_comparator_set: BootstrapComparatorSet | None
    final: ComparatorSelection | None


@dataclass(frozen=True)
class PreflightCompositionReference:
    axis: str
    asset_path: str
    source_record_key: str
    accepted_asset_sha256: str
    reason: str


@dataclass(frozen=True)
class PreflightComparatorSet:
    mode: str
    composition_framing_scale: PreflightCompositionReference | None
    material_texture_lighting: None
    unavailable_axes: tuple[str, ...]
    official_evidence_input_ids: tuple[str, ...]
    independent_evidence_input_ids: tuple[str, ...]
    shared_material_contract: str
    production_authorization: str
    selected_at: datetime


@dataclass(frozen=True)
class CapabilityProbeArtifact:
    id: str
    behavior_probe_id: str
    attempt: int
    returned_output_path: str
    transient_output_path: str
    sha256: str
    width_pixels: int
    height_pixels: int
    canvas_result: str
    disposition: str
    production_use: str
    reason: str
    provenance: CandidateProvenance
    byte_verification: ByteVerification
    recorded_at: datetime
    deletion_verified_at: datetime | None


@dataclass(frozen=True)
class CanvasBehaviorProbe:
    id: str
    behavior: str
    representative_record_key: str
    prompt: str
    source_inputs: tuple[GenerationSourceInput, ...]
    preflight_comparator_set: PreflightComparatorSet
    artifact_ids: tuple[str, ...]
    status: str
    blocked_reason: str | None


@dataclass(frozen=True)
class CanvasClass:
    width_pixels: int
    height_pixels: int
    covered_record_keys: tuple[str, ...]
    status: str
    blocked_reason: str | None
    behavior_probes: tuple[CanvasBehaviorProbe, ...]


@dataclass(frozen=True)
class CanvasPreflight:
    status: str
    blocked_reason: str | None
    classes: tuple[CanvasClass, ...]


@dataclass(frozen=True)
class RemediationBatch:
    id: str
    order: int
    kind: str
    record_keys: tuple[str, ...]
    status: str
    blocked_reason: str | None
    checks: Mapping[str, PresentationCheck]


@dataclass(frozen=True)
class Phase2Root:
    canvas_preflight: CanvasPreflight
    capability_probe_artifacts: tuple[CapabilityProbeArtifact, ...]
    batches: tuple[RemediationBatch, ...]
    final_checks: Mapping[str, PresentationCheck]


@dataclass(frozen=True)
class SimulatorDeviceRun:
    device_class: str
    simulator_uuid: str
    capture_sha256s: tuple[str, ...]
    flows: Mapping[str, str]


@dataclass(frozen=True)
class SimulatorReview:
    state: str
    reviewed_at: datetime | None
    environment_evidence_ids: tuple[str, ...]
    device_runs: tuple[SimulatorDeviceRun, ...]


@dataclass(frozen=True)
class PresentationRemediationRecord:
    package_id: str
    product_name: str
    presentation_id: str
    asset_path: str
    working_surface: str
    physical_revision: str
    manufacturer: str
    materials: tuple[str, ...]
    form_factor: str
    current_asset: PresentationCurrentAsset
    decision: str
    findings: Mapping[str, PresentationFinding]
    evidence: PresentationEvidence
    comparator: PresentationComparator
    generation: PresentationGeneration | Phase2Generation
    final: PresentationFinalState
    repair_batch_id: str | None = None
    phase2_action: Phase2Action | None = None
    phase2_evidence_review: Phase2EvidenceReview | None = None
    phase2_comparator: Phase2Comparator | None = None


@dataclass(frozen=True)
class PresentationRemediationManifest:
    schema_version: int
    phase: str
    review_date: date
    package_ids: tuple[str, ...]
    records: tuple[PresentationRemediationRecord, ...]
    phase1_checks: Mapping[str, Phase1Check]
    phase2: Phase2Root | None = None


@dataclass(frozen=True)
class PresentationRemediationReport:
    package_ids: tuple[str, ...]
    presentation_count: int
    decisions: Mapping[str, int]
    evidence_blocked_assets: tuple[str, ...]
    phase: str | None = None
    batch_id: str | None = None
    canvas_class_count: int = 0
    canvas_covered_repair_count: int = 0
    capability_probe_artifact_count: int = 0
    historical_evidence_blocked_keeps: int = 0
    blocked_phase2_action_count: int = 0
    original_presentation_count: int = 0
    inventory_presentation_count: int = 0
    kept_presentation_count: int = 0
    completed_edit_count: int = 0
    completed_regeneration_count: int = 0
    completed_removal_count: int = 0
    pending_phase2_action_count: int = 0

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "packageIDs": list(self.package_ids),
            "packageCount": len(self.package_ids),
            "presentationCount": self.presentation_count,
            "decisions": {key: self.decisions[key] for key in sorted(self.decisions)},
            "evidenceBlockedAssets": list(self.evidence_blocked_assets),
        }
        if self.phase is not None:
            payload.update(
                {
                    "phase": self.phase,
                    "batchID": self.batch_id,
                    "canvasClassCount": self.canvas_class_count,
                    "canvasCoveredRepairCount": self.canvas_covered_repair_count,
                    "capabilityProbeArtifactCount": self.capability_probe_artifact_count,
                    "historicalEvidenceBlockedKeeps": self.historical_evidence_blocked_keeps,
                    "blockedPhase2ActionCount": self.blocked_phase2_action_count,
                    "originalPresentationCount": self.original_presentation_count,
                    "inventoryPresentationCount": self.inventory_presentation_count,
                    "keptPresentationCount": self.kept_presentation_count,
                    "completedEditCount": self.completed_edit_count,
                    "completedRegenerationCount": self.completed_regeneration_count,
                    "completedRemovalCount": self.completed_removal_count,
                    "pendingPhase2ActionCount": self.pending_phase2_action_count,
                }
            )
        return payload


def _mapping(value: Any, source: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PresentationRemediationAuditError(f"{source} must be an object")
    return value


def _closed(
    payload: Mapping[str, Any], required: frozenset[str] | set[str], source: str
) -> None:
    required_set = set(required)
    unknown, missing = set(payload) - required_set, required_set - set(payload)
    if unknown:
        raise PresentationRemediationAuditError(
            f"{source} has unknown keys: {sorted(unknown)}"
        )
    if missing:
        raise PresentationRemediationAuditError(
            f"{source} is missing keys: {sorted(missing)}"
        )


def _string(value: Any, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PresentationRemediationAuditError(f"{source} must be a non-empty string")
    return value


def _optional_string(value: Any, source: str) -> str | None:
    return None if value is None else _string(value, source)


def _positive_int(value: Any, source: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PresentationRemediationAuditError(f"{source} must be a positive integer")
    return value


def _date(value: Any, source: str) -> date:
    text = _string(value, source)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise PresentationRemediationAuditError(
            f"{source} must be an ISO date"
        ) from error
    if parsed.isoformat() != text:
        raise PresentationRemediationAuditError(f"{source} must be an ISO date")
    return parsed


def _instant(value: Any, source: str) -> datetime:
    text = _string(value, source)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise PresentationRemediationAuditError(
            f"{source} must be an aware ISO instant"
        ) from error
    if parsed.utcoffset() is None or parsed.isoformat() != text:
        raise PresentationRemediationAuditError(
            f"{source} must be an aware ISO instant"
        )
    return parsed


def _optional_instant(value: Any, source: str) -> datetime | None:
    return None if value is None else _instant(value, source)


def _literal(value: Any, allowed: frozenset[str], source: str) -> str:
    text = _string(value, source)
    if text not in allowed:
        raise PresentationRemediationAuditError(
            f"{source} must be one of {sorted(allowed)}"
        )
    return text


def _bool(value: Any, source: str) -> bool:
    if not isinstance(value, bool):
        raise PresentationRemediationAuditError(f"{source} must be a boolean")
    return value


def _sha256(value: Any, source: str) -> str:
    digest = _string(value, source)
    if not _SHA256.fullmatch(digest):
        raise PresentationRemediationAuditError(f"{source} must be a lowercase SHA-256")
    return digest


def _url(value: Any, source: str) -> str:
    url = _string(value, source)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise PresentationRemediationAuditError(f"{source} must be a direct HTTPS URL")
    hostname = parsed.hostname.casefold().removesuffix(".").removeprefix("www.")
    path_segments = tuple(
        segment for segment in unquote(parsed.path).casefold().split("/") if segment
    )
    if "search" in path_segments or hostname in _SEARCH_HOSTS:
        raise PresentationRemediationAuditError(
            f"{source} must not be a search-result URL"
        )
    return url


def _string_array(value: Any, source: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PresentationRemediationAuditError(f"{source} must be an array")
    return tuple(
        _string(item, f"{source}[{index}]") for index, item in enumerate(value)
    )


def _literal_array(value: Any, allowed: frozenset[str], source: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PresentationRemediationAuditError(f"{source} must be an array")
    result = tuple(
        _literal(item, allowed, f"{source}[{index}]")
        for index, item in enumerate(value)
    )
    if len(result) != len(set(result)):
        raise PresentationRemediationAuditError(f"{source} values must be unique")
    return result


def _load_check(value: Any, source: str) -> PresentationCheck:
    payload = _mapping(value, source)
    _closed(payload, {"status", "evidence"}, source)
    status = _string(payload["status"], f"{source}.status")
    if status not in _PRESENTATION_CHECK_STATUSES:
        raise PresentationRemediationAuditError(
            f"{source}.status must be one of {sorted(_PRESENTATION_CHECK_STATUSES)}"
        )
    evidence = _optional_string(payload["evidence"], f"{source}.evidence")
    if (status == "pending") != (evidence is None):
        raise PresentationRemediationAuditError(
            f"{source} status and evidence must be pending/null or passed-or-failed/non-empty"
        )
    return PresentationCheck(status, evidence)


def _load_phase1_check(value: Any, source: str) -> Phase1Check:
    payload = _mapping(value, source)
    _closed(payload, {"status", "command"}, source)
    status = _string(payload["status"], f"{source}.status")
    if status not in _PHASE1_CHECK_STATUSES:
        raise PresentationRemediationAuditError(
            f"{source}.status must be one of {sorted(_PHASE1_CHECK_STATUSES)}"
        )
    command = _optional_string(payload["command"], f"{source}.command")
    if (status == "pending") != (command is None):
        raise PresentationRemediationAuditError(
            f"{source} status and command must be pending/null or passed/non-empty"
        )
    return Phase1Check(status, command)


def _load_source(
    value: Any,
    source: str,
    valid_kinds: frozenset[str],
    review_date: date,
) -> PresentationRemediationSource:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "url",
            "publisher",
            "sourceKind",
            "reviewedAt",
            "revisionApplicability",
            "imageRole",
            "supportedClaim",
        },
        source,
    )
    kind = _string(payload["sourceKind"], f"{source}.sourceKind")
    if kind not in valid_kinds:
        raise PresentationRemediationAuditError(
            f"{source}.sourceKind must be one of {sorted(valid_kinds)}"
        )
    reviewed_at = _date(payload["reviewedAt"], f"{source}.reviewedAt")
    if reviewed_at != review_date:
        raise PresentationRemediationAuditError(
            f"{source}.reviewedAt must equal manifest reviewDate {review_date.isoformat()}"
        )
    return PresentationRemediationSource(
        _url(payload["url"], f"{source}.url"),
        _string(payload["publisher"], f"{source}.publisher"),
        kind,
        reviewed_at,
        _string(payload["revisionApplicability"], f"{source}.revisionApplicability"),
        _string(payload["imageRole"], f"{source}.imageRole"),
        _string(payload["supportedClaim"], f"{source}.supportedClaim"),
    )


def _load_evidence(
    value: Any, source: str, review_date: date
) -> PresentationEvidence:
    payload = _mapping(value, source)
    _closed(
        payload,
        {"official", "independent", "officialEvidenceGap", "independentEvidenceGap"},
        source,
    )
    loaded: list[tuple[PresentationRemediationSource, ...]] = []
    for key, kinds in (
        ("official", _OFFICIAL_KINDS),
        ("independent", _INDEPENDENT_KINDS),
    ):
        entries = payload[key]
        if not isinstance(entries, list):
            raise PresentationRemediationAuditError(f"{source}.{key} must be an array")
        loaded.append(
            tuple(
                _load_source(
                    entry, f"{source}.{key}[{index}]", kinds, review_date
                )
                for index, entry in enumerate(entries)
            )
        )
    official_gap = _optional_string(
        payload["officialEvidenceGap"], f"{source}.officialEvidenceGap"
    )
    independent_gap = _optional_string(
        payload["independentEvidenceGap"], f"{source}.independentEvidenceGap"
    )
    for key, entries, gap in (
        ("official", loaded[0], official_gap),
        ("independent", loaded[1], independent_gap),
    ):
        if bool(entries) == bool(gap):
            raise PresentationRemediationAuditError(
                f"{key} evidence requires exactly one of sources or a non-empty gap"
            )
    return PresentationEvidence(loaded[0], loaded[1], official_gap, independent_gap)


def _load_record(
    value: Any, source: str, review_date: date
) -> PresentationRemediationRecord:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "packageID",
            "productName",
            "presentationID",
            "assetPath",
            "workingSurface",
            "physicalRevision",
            "manufacturer",
            "materials",
            "formFactor",
            "currentAsset",
            "decision",
            "findings",
            "evidence",
            "comparator",
            "generation",
            "final",
        },
        source,
    )
    package_id = _string(payload["packageID"], f"{source}.packageID")
    if not is_board_identifier(package_id):
        raise PresentationRemediationAuditError(
            f"{source}.packageID must be identifier-shaped"
        )
    materials_raw = payload["materials"]
    if not isinstance(materials_raw, list) or not materials_raw:
        raise PresentationRemediationAuditError(
            f"{source}.materials must be a non-empty array"
        )
    materials = tuple(
        _string(item, f"{source}.materials[{index}]")
        for index, item in enumerate(materials_raw)
    )
    if len(materials) != len(set(materials)) or not set(materials) <= _MATERIALS:
        raise PresentationRemediationAuditError(
            f"{source}.materials must be unique supported materials"
        )
    form_factor = _string(payload["formFactor"], f"{source}.formFactor")
    if form_factor not in _FORM_FACTORS:
        raise PresentationRemediationAuditError(
            f"{source}.formFactor must be one of {sorted(_FORM_FACTORS)}"
        )
    asset_payload = _mapping(payload["currentAsset"], f"{source}.currentAsset")
    _closed(
        asset_payload,
        {"sha256", "widthPixels", "heightPixels"},
        f"{source}.currentAsset",
    )
    decision = _string(payload["decision"], f"{source}.decision")
    if decision not in _DECISIONS:
        raise PresentationRemediationAuditError(
            f"{source}.decision must be one of {sorted(_DECISIONS)}"
        )
    findings_payload = _mapping(payload["findings"], f"{source}.findings")
    _closed(findings_payload, _FINDING_KEYS, f"{source}.findings")
    findings: dict[str, PresentationFinding] = {}
    for key in _FINDING_KEYS:
        finding = _mapping(findings_payload[key], f"{source}.findings.{key}")
        _closed(finding, {"outcome", "explanation"}, f"{source}.findings.{key}")
        outcome = _string(finding["outcome"], f"{source}.findings.{key}.outcome")
        if outcome not in _OUTCOMES:
            raise PresentationRemediationAuditError(
                f"{source}.findings.{key}.outcome must be one of {sorted(_OUTCOMES)}"
            )
        findings[key] = PresentationFinding(
            outcome,
            _string(finding["explanation"], f"{source}.findings.{key}.explanation"),
        )
    comparator_payload = _mapping(payload["comparator"], f"{source}.comparator")
    _closed(
        comparator_payload,
        {"assetPath", "materialMatch", "formFactorMatch", "reason", "baselineGap"},
        f"{source}.comparator",
    )
    comparator = PresentationComparator(
        *(
            _optional_string(comparator_payload[key], f"{source}.comparator.{key}")
            for key in (
                "assetPath",
                "materialMatch",
                "formFactorMatch",
                "reason",
                "baselineGap",
            )
        )
    )
    generation_payload = _mapping(payload["generation"], f"{source}.generation")
    _closed(
        generation_payload,
        {"prompt", "sourceImages", "currentAssetRole", "candidates"},
        f"{source}.generation",
    )
    generation = PresentationGeneration(
        _optional_string(generation_payload["prompt"], f"{source}.generation.prompt"),
        _string_array(
            generation_payload["sourceImages"], f"{source}.generation.sourceImages"
        ),
        _optional_string(
            generation_payload["currentAssetRole"],
            f"{source}.generation.currentAssetRole",
        ),
        _string_array(
            generation_payload["candidates"], f"{source}.generation.candidates"
        ),
    )
    final_payload = _mapping(payload["final"], f"{source}.final")
    _closed(
        final_payload,
        {
            "acceptedAssetSHA256",
            "finalDimensions",
            "visualReviewerDecision",
            "workbenchReview",
            "validation",
        },
        f"{source}.final",
    )
    dimensions_value = final_payload["finalDimensions"]
    if dimensions_value is None:
        dimensions = None
    else:
        dims = _mapping(dimensions_value, f"{source}.final.finalDimensions")
        _closed(
            dims, {"widthPixels", "heightPixels"}, f"{source}.final.finalDimensions"
        )
        dimensions = (
            _positive_int(
                dims["widthPixels"], f"{source}.final.finalDimensions.widthPixels"
            ),
            _positive_int(
                dims["heightPixels"], f"{source}.final.finalDimensions.heightPixels"
            ),
        )
    review_payload, validation_payload = (
        _mapping(final_payload["workbenchReview"], f"{source}.final.workbenchReview"),
        _mapping(final_payload["validation"], f"{source}.final.validation"),
    )
    _closed(review_payload, _WORKBENCH_CHECKS, f"{source}.final.workbenchReview")
    _closed(validation_payload, _VALIDATION_CHECKS, f"{source}.final.validation")
    final = PresentationFinalState(
        None
        if final_payload["acceptedAssetSHA256"] is None
        else _sha256(
            final_payload["acceptedAssetSHA256"], f"{source}.final.acceptedAssetSHA256"
        ),
        dimensions,
        _string(
            final_payload["visualReviewerDecision"],
            f"{source}.final.visualReviewerDecision",
        ),
        {
            key: _load_check(
                review_payload[key], f"{source}.final.workbenchReview.{key}"
            )
            for key in _WORKBENCH_CHECKS
        },
        {
            key: _load_check(
                validation_payload[key], f"{source}.final.validation.{key}"
            )
            for key in _VALIDATION_CHECKS
        },
    )
    return PresentationRemediationRecord(
        package_id,
        _string(payload["productName"], f"{source}.productName"),
        _string(payload["presentationID"], f"{source}.presentationID"),
        _string(payload["assetPath"], f"{source}.assetPath"),
        _string(payload["workingSurface"], f"{source}.workingSurface"),
        _string(payload["physicalRevision"], f"{source}.physicalRevision"),
        _string(payload["manufacturer"], f"{source}.manufacturer"),
        materials,
        form_factor,
        PresentationCurrentAsset(
            _sha256(asset_payload["sha256"], f"{source}.currentAsset.sha256"),
            _positive_int(
                asset_payload["widthPixels"], f"{source}.currentAsset.widthPixels"
            ),
            _positive_int(
                asset_payload["heightPixels"], f"{source}.currentAsset.heightPixels"
            ),
        ),
        decision,
        findings,
        _load_evidence(payload["evidence"], f"{source}.evidence", review_date),
        comparator,
        generation,
        final,
    )


def _load_phase2_check(value: Any, source: str) -> PresentationCheck:
    payload = _mapping(value, source)
    _closed(payload, {"status", "evidence"}, source)
    status = _literal(payload["status"], _PHASE2_CHECK_STATUSES, f"{source}.status")
    evidence = _optional_string(payload["evidence"], f"{source}.evidence")
    if status == "pending" and evidence is not None:
        raise PresentationRemediationAuditError(
            f"{source} pending status requires null evidence"
        )
    if status != "pending" and evidence is None:
        raise PresentationRemediationAuditError(
            f"{source} non-pending status requires non-empty evidence"
        )
    return PresentationCheck(status, evidence)


def _load_byte_verification(value: Any, source: str) -> ByteVerification:
    payload = _mapping(value, source)
    _closed(payload, {"status", "checkedAt", "command", "observedSHA256"}, source)
    status = _literal(payload["status"], _BYTE_STATUSES, f"{source}.status")
    checked_at = _optional_instant(payload["checkedAt"], f"{source}.checkedAt")
    command = _optional_string(payload["command"], f"{source}.command")
    observed = (
        None
        if payload["observedSHA256"] is None
        else _sha256(payload["observedSHA256"], f"{source}.observedSHA256")
    )
    values_present = checked_at is not None and command is not None and observed is not None
    if status == "pending" and any(
        item is not None for item in (checked_at, command, observed)
    ):
        raise PresentationRemediationAuditError(
            f"{source} pending byte verification requires null details"
        )
    if status != "pending" and not values_present:
        raise PresentationRemediationAuditError(
            f"{source} terminal byte verification requires date, command, and hash"
        )
    return ByteVerification(status, checked_at, command, observed)


def _load_source_input(value: Any, source: str) -> GenerationSourceInput:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "id",
            "sourceType",
            "evidencePointer",
            "sourceURL",
            "assetPath",
            "role",
            "sha256",
            "suppliedToImagegen",
            "byteVerification",
        },
        source,
    )
    return GenerationSourceInput(
        _string(payload["id"], f"{source}.id"),
        _literal(payload["sourceType"], _INPUT_TYPES, f"{source}.sourceType"),
        _optional_string(payload["evidencePointer"], f"{source}.evidencePointer"),
        None if payload["sourceURL"] is None else _url(payload["sourceURL"], f"{source}.sourceURL"),
        _optional_string(payload["assetPath"], f"{source}.assetPath"),
        _string(payload["role"], f"{source}.role"),
        _sha256(payload["sha256"], f"{source}.sha256"),
        _bool(payload["suppliedToImagegen"], f"{source}.suppliedToImagegen"),
        _load_byte_verification(payload["byteVerification"], f"{source}.byteVerification"),
    )


def _load_required_canvas(value: Any, source: str) -> RequiredCanvas:
    payload = _mapping(value, source)
    _closed(payload, {"widthPixels", "heightPixels"}, source)
    return RequiredCanvas(
        _positive_int(payload["widthPixels"], f"{source}.widthPixels"),
        _positive_int(payload["heightPixels"], f"{source}.heightPixels"),
    )


def _load_candidate_provenance(value: Any, source: str) -> CandidateProvenance:
    payload = _mapping(value, source)
    _closed(payload, {"tool", "untouchedModelOutput", "postProcessing"}, source)
    if payload["tool"] != "builtInImageGen":
        raise PresentationRemediationAuditError(f"{source}.tool must equal builtInImageGen")
    if payload["untouchedModelOutput"] is not True:
        raise PresentationRemediationAuditError(
            f"{source}.untouchedModelOutput must equal true"
        )
    if payload["postProcessing"] != "none":
        raise PresentationRemediationAuditError("postProcessing must equal none")
    return CandidateProvenance("builtInImageGen", True, "none")


def _load_generation_candidate(value: Any, source: str) -> GenerationCandidate:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "attempt",
            "transientOutputPath",
            "sha256",
            "widthPixels",
            "heightPixels",
            "disposition",
            "reason",
            "provenance",
            "byteVerification",
        },
        source,
    )
    attempt = _positive_int(payload["attempt"], f"{source}.attempt")
    if attempt not in (1, 2, 3):
        raise PresentationRemediationAuditError(f"{source}.attempt must be 1, 2, or 3")
    return GenerationCandidate(
        attempt,
        _string(payload["transientOutputPath"], f"{source}.transientOutputPath"),
        _sha256(payload["sha256"], f"{source}.sha256"),
        _positive_int(payload["widthPixels"], f"{source}.widthPixels"),
        _positive_int(payload["heightPixels"], f"{source}.heightPixels"),
        _literal(payload["disposition"], _CANDIDATE_DISPOSITIONS, f"{source}.disposition"),
        _string(payload["reason"], f"{source}.reason"),
        _load_candidate_provenance(payload["provenance"], f"{source}.provenance"),
        _load_byte_verification(payload["byteVerification"], f"{source}.byteVerification"),
    )


def _load_phase2_generation(value: Any, source: str) -> Phase2Generation:
    payload = _mapping(value, source)
    _closed(
        payload,
        {"mode", "prompt", "requiredCanvas", "sourceInputs", "currentAssetRole", "candidates"},
        source,
    )
    inputs = payload["sourceInputs"]
    candidates = payload["candidates"]
    if not isinstance(inputs, list) or not isinstance(candidates, list):
        raise PresentationRemediationAuditError(
            f"{source}.sourceInputs and candidates must be arrays"
        )
    return Phase2Generation(
        _literal(payload["mode"], _GENERATION_MODES, f"{source}.mode"),
        _optional_string(payload["prompt"], f"{source}.prompt"),
        None if payload["requiredCanvas"] is None else _load_required_canvas(payload["requiredCanvas"], f"{source}.requiredCanvas"),
        tuple(_load_source_input(item, f"{source}.sourceInputs[{index}]") for index, item in enumerate(inputs)),
        _optional_string(payload["currentAssetRole"], f"{source}.currentAssetRole"),
        tuple(_load_generation_candidate(item, f"{source}.candidates[{index}]") for index, item in enumerate(candidates)),
    )


def _load_comparator_selection(value: Any, source: str) -> ComparatorSelection:
    payload = _mapping(value, source)
    _closed(payload, {"mode", "assetPath", "sourceRecordKey", "acceptedAssetSHA256", "reason", "selectedAt"}, source)
    if payload["mode"] == "temporaryGap":
        raise PresentationRemediationAuditError(
            "final comparator cannot be a gap"
            if source.endswith(".final")
            else "temporary gaps cannot authorize generation"
        )
    return ComparatorSelection(
        _literal(payload["mode"], _COMPARATOR_MODES, f"{source}.mode"),
        _string(payload["assetPath"], f"{source}.assetPath"),
        _string(payload["sourceRecordKey"], f"{source}.sourceRecordKey"),
        _sha256(payload["acceptedAssetSHA256"], f"{source}.acceptedAssetSHA256"),
        _string(payload["reason"], f"{source}.reason"),
        _instant(payload["selectedAt"], f"{source}.selectedAt"),
    )


def _load_bootstrap_axis(value: Any, source: str) -> BootstrapComparatorAxis:
    payload = _mapping(value, source)
    _closed(payload, {"axis", "assetPath", "sourceRecordKey", "acceptedAssetSHA256", "matchedMaterialTokens", "reason"}, source)
    return BootstrapComparatorAxis(
        _literal(payload["axis"], _BOOTSTRAP_AXIS_NAMES, f"{source}.axis"),
        _string(payload["assetPath"], f"{source}.assetPath"),
        _string(payload["sourceRecordKey"], f"{source}.sourceRecordKey"),
        _sha256(payload["acceptedAssetSHA256"], f"{source}.acceptedAssetSHA256"),
        _string_array(payload["matchedMaterialTokens"], f"{source}.matchedMaterialTokens"),
        _string(payload["reason"], f"{source}.reason"),
    )


def _load_bootstrap_set(value: Any, source: str) -> BootstrapComparatorSet:
    payload = _mapping(value, source)
    _closed(payload, {"cohortID", "seedRecordKey", "status", "compositionFramingScale", "materialTextureLighting", "absentAxes", "officialEvidenceInputIDs", "independentEvidenceInputIDs", "sharedRenderContract", "selectionRule", "selectedAt", "acceptedAt", "reviewChecks", "blockedReason"}, source)
    checks = _mapping(payload["reviewChecks"], f"{source}.reviewChecks")
    _closed(checks, {"evidenceReview", "visualReview", "workbenchReview", "packageValidation"}, f"{source}.reviewChecks")
    cohort = _string(payload["cohortID"], f"{source}.cohortID")
    if cohort not in _BOOTSTRAP_SEEDS:
        raise PresentationRemediationAuditError(f"{source}.cohortID is not supported")
    return BootstrapComparatorSet(
        cohort,
        _string(payload["seedRecordKey"], f"{source}.seedRecordKey"),
        _literal(payload["status"], _BOOTSTRAP_STATUSES, f"{source}.status"),
        None if payload["compositionFramingScale"] is None else _load_bootstrap_axis(payload["compositionFramingScale"], f"{source}.compositionFramingScale"),
        None if payload["materialTextureLighting"] is None else _load_bootstrap_axis(payload["materialTextureLighting"], f"{source}.materialTextureLighting"),
        _literal_array(payload["absentAxes"], _BOOTSTRAP_AXIS_NAMES, f"{source}.absentAxes"),
        _string_array(payload["officialEvidenceInputIDs"], f"{source}.officialEvidenceInputIDs"),
        _string_array(payload["independentEvidenceInputIDs"], f"{source}.independentEvidenceInputIDs"),
        _string(payload["sharedRenderContract"], f"{source}.sharedRenderContract"),
        _string(payload["selectionRule"], f"{source}.selectionRule"),
        _instant(payload["selectedAt"], f"{source}.selectedAt"),
        _optional_instant(payload["acceptedAt"], f"{source}.acceptedAt"),
        BootstrapReviewChecks(*(_load_phase2_check(checks[key], f"{source}.reviewChecks.{key}") for key in ("evidenceReview", "visualReview", "workbenchReview", "packageValidation"))),
        _optional_string(payload["blockedReason"], f"{source}.blockedReason"),
    )


def _load_phase2_comparator(value: Any, source: str) -> Phase2Comparator:
    payload = _mapping(value, source)
    _closed(payload, {"generationTime", "bootstrapComparatorSet", "final"}, source)
    return Phase2Comparator(
        None if payload["generationTime"] is None else _load_comparator_selection(payload["generationTime"], f"{source}.generationTime"),
        None if payload["bootstrapComparatorSet"] is None else _load_bootstrap_set(payload["bootstrapComparatorSet"], f"{source}.bootstrapComparatorSet"),
        None if payload["final"] is None else _load_comparator_selection(payload["final"], f"{source}.final"),
    )


def _load_simulator_review(value: Any, source: str) -> SimulatorReview:
    payload = _mapping(value, source)
    _closed(payload, {"state", "reviewedAt", "environmentEvidenceIDs", "deviceRuns"}, source)
    runs_raw = payload["deviceRuns"]
    if not isinstance(runs_raw, list):
        raise PresentationRemediationAuditError(f"{source}.deviceRuns must be an array")
    runs: list[SimulatorDeviceRun] = []
    for index, item in enumerate(runs_raw):
        run_source = f"{source}.deviceRuns[{index}]"
        run = _mapping(item, run_source)
        _closed(run, {"deviceClass", "simulatorUUID", "captureSHA256s", "flows"}, run_source)
        device_class = _string(run["deviceClass"], f"{run_source}.deviceClass")
        if device_class not in {"phone", "tablet"}:
            raise PresentationRemediationAuditError(
                f"{run_source}.deviceClass must be phone or tablet"
            )
        flow_payload = _mapping(run["flows"], f"{run_source}.flows")
        _closed(flow_payload, _SIMULATOR_FLOW_KEYS, f"{run_source}.flows")
        flows = {
            key: _literal(flow_payload[key], _FLOW_STATES, f"{run_source}.flows.{key}")
            for key in _SIMULATOR_FLOW_KEYS
        }
        for key, state in flows.items():
            if state == "notApplicableSinglePresentation" and key != "presentationSelector":
                raise PresentationRemediationAuditError(
                    "only presentationSelector accepts notApplicableSinglePresentation"
                )
            if state == "notApplicableNoCompatiblePlan" and key != "plan":
                raise PresentationRemediationAuditError(
                    "only plan accepts notApplicableNoCompatiblePlan"
                )
        captures_raw = run["captureSHA256s"]
        if not isinstance(captures_raw, list):
            raise PresentationRemediationAuditError(
                f"{run_source}.captureSHA256s must be an array"
            )
        runs.append(
            SimulatorDeviceRun(
                device_class,
                _string(run["simulatorUUID"], f"{run_source}.simulatorUUID"),
                tuple(_sha256(item, f"{run_source}.captureSHA256s[{capture_index}]") for capture_index, item in enumerate(captures_raw)),
                flows,
            )
        )
    return SimulatorReview(
        _literal(payload["state"], _SIMULATOR_STATES, f"{source}.state"),
        _optional_instant(payload["reviewedAt"], f"{source}.reviewedAt"),
        _string_array(payload["environmentEvidenceIDs"], f"{source}.environmentEvidenceIDs"),
        tuple(runs),
    )


def _load_phase2_final(value: Any, source: str) -> PresentationFinalState:
    payload = _mapping(value, source)
    _closed(payload, {"acceptedAssetSHA256", "finalDimensions", "visualReviewerDecision", "workbenchReview", "validation"}, source)
    dimensions = None if payload["finalDimensions"] is None else _load_required_canvas(payload["finalDimensions"], f"{source}.finalDimensions")
    workbench = _mapping(payload["workbenchReview"], f"{source}.workbenchReview")
    _closed(workbench, {"normal", "allActive", "individualHolds", "hitTest"}, f"{source}.workbenchReview")
    validation = _mapping(payload["validation"], f"{source}.validation")
    _closed(validation, _VALIDATION_CHECKS, f"{source}.validation")
    return PresentationFinalState(
        None if payload["acceptedAssetSHA256"] is None else _sha256(payload["acceptedAssetSHA256"], f"{source}.acceptedAssetSHA256"),
        None if dimensions is None else (dimensions.width_pixels, dimensions.height_pixels),
        _string(payload["visualReviewerDecision"], f"{source}.visualReviewerDecision"),
        {key: _load_phase2_check(workbench[key], f"{source}.workbenchReview.{key}") for key in ("normal", "allActive", "individualHolds", "hitTest")},
        {
            **{key: _load_phase2_check(validation[key], f"{source}.validation.{key}") for key in ("packageValidation", "focusedTests", "fullPackageSuite", "buildForTesting")},
            "simulatorReview": _load_simulator_review(validation["simulatorReview"], f"{source}.validation.simulatorReview"),
        },
    )


def _load_phase2_record(value: Any, source: str, review_date: date) -> PresentationRemediationRecord:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "packageID", "productName", "presentationID", "assetPath", "workingSurface",
            "physicalRevision", "manufacturer", "materials", "formFactor", "currentAsset",
            "decision", "findings", "evidence", "comparator", "generation", "final",
            "repairBatchID", "phase2Action", "phase2EvidenceReview", "phase2Comparator",
        },
        source,
    )
    legacy = dict(payload)
    legacy["generation"] = {"prompt": None, "sourceImages": [], "currentAssetRole": None, "candidates": []}
    final_payload = _mapping(payload["final"], f"{source}.final")
    legacy["final"] = {
        "acceptedAssetSHA256": final_payload.get("acceptedAssetSHA256"),
        "finalDimensions": final_payload.get("finalDimensions"),
        "visualReviewerDecision": final_payload.get("visualReviewerDecision"),
        "workbenchReview": {name: {"status": "pending", "evidence": None} for name in ("normal", "allActive", "individualHolds")},
        "validation": {name: {"status": "pending", "evidence": None} for name in _VALIDATION_CHECKS},
    }
    for key in ("repairBatchID", "phase2Action", "phase2EvidenceReview", "phase2Comparator"):
        legacy.pop(key)
    common = _load_record(legacy, source, review_date)
    action_payload = _mapping(payload["phase2Action"], f"{source}.phase2Action")
    _closed(action_payload, {"state", "blockedReason"}, f"{source}.phase2Action")
    evidence_review = _mapping(payload["phase2EvidenceReview"], f"{source}.phase2EvidenceReview")
    _closed(evidence_review, {"result", "reviewedAt", "officialURLsReopened", "independentURLsReopened", "evidenceGapSearchesRepeated", "notes"}, f"{source}.phase2EvidenceReview")
    return replace(
        common,
        generation=_load_phase2_generation(payload["generation"], f"{source}.generation"),
        final=_load_phase2_final(payload["final"], f"{source}.final"),
        repair_batch_id=_optional_string(payload["repairBatchID"], f"{source}.repairBatchID"),
        phase2_action=Phase2Action(
            _literal(action_payload["state"], _ACTION_STATES, f"{source}.phase2Action.state"),
            _optional_string(action_payload["blockedReason"], f"{source}.phase2Action.blockedReason"),
        ),
        phase2_evidence_review=Phase2EvidenceReview(
            _literal(evidence_review["result"], _EVIDENCE_RESULTS, f"{source}.phase2EvidenceReview.result"),
            _optional_instant(evidence_review["reviewedAt"], f"{source}.phase2EvidenceReview.reviewedAt"),
            _string_array(evidence_review["officialURLsReopened"], f"{source}.phase2EvidenceReview.officialURLsReopened"),
            _string_array(evidence_review["independentURLsReopened"], f"{source}.phase2EvidenceReview.independentURLsReopened"),
            _string_array(evidence_review["evidenceGapSearchesRepeated"], f"{source}.phase2EvidenceReview.evidenceGapSearchesRepeated"),
            _string(evidence_review["notes"], f"{source}.phase2EvidenceReview.notes"),
        ),
        phase2_comparator=_load_phase2_comparator(payload["phase2Comparator"], f"{source}.phase2Comparator"),
    )


def _load_preflight_comparator_set(value: Any, source: str) -> PreflightComparatorSet:
    payload = _mapping(value, source)
    _closed(payload, {"mode", "compositionFramingScale", "materialTextureLighting", "unavailableAxes", "officialEvidenceInputIDs", "independentEvidenceInputIDs", "sharedMaterialContract", "productionAuthorization", "selectedAt"}, source)
    if payload["mode"] != "preflightCapabilityOnly":
        raise PresentationRemediationAuditError(f"{source}.mode must equal preflightCapabilityOnly")
    if payload["materialTextureLighting"] is not None:
        raise PresentationRemediationAuditError("preflight material comparator is always unavailable")
    if payload["productionAuthorization"] != "forbidden":
        raise PresentationRemediationAuditError(f"{source}.productionAuthorization must equal forbidden")
    composition = None
    if payload["compositionFramingScale"] is not None:
        item = _mapping(payload["compositionFramingScale"], f"{source}.compositionFramingScale")
        _closed(item, {"axis", "assetPath", "sourceRecordKey", "acceptedAssetSHA256", "reason"}, f"{source}.compositionFramingScale")
        if item["axis"] != "compositionFramingScale":
            raise PresentationRemediationAuditError(f"{source}.compositionFramingScale.axis must equal compositionFramingScale")
        if item["reason"] != _PREFLIGHT_COMPOSITION_REASON:
            raise PresentationRemediationAuditError(f"{source}.compositionFramingScale.reason is not canonical")
        composition = PreflightCompositionReference(
            "compositionFramingScale",
            _string(item["assetPath"], f"{source}.compositionFramingScale.assetPath"),
            _string(item["sourceRecordKey"], f"{source}.compositionFramingScale.sourceRecordKey"),
            _sha256(item["acceptedAssetSHA256"], f"{source}.compositionFramingScale.acceptedAssetSHA256"),
            _PREFLIGHT_COMPOSITION_REASON,
        )
    return PreflightComparatorSet(
        "preflightCapabilityOnly",
        composition,
        None,
        _literal_array(payload["unavailableAxes"], _BOOTSTRAP_AXIS_NAMES, f"{source}.unavailableAxes"),
        _string_array(payload["officialEvidenceInputIDs"], f"{source}.officialEvidenceInputIDs"),
        _string_array(payload["independentEvidenceInputIDs"], f"{source}.independentEvidenceInputIDs"),
        _string(payload["sharedMaterialContract"], f"{source}.sharedMaterialContract"),
        "forbidden",
        _instant(payload["selectedAt"], f"{source}.selectedAt"),
    )


def _load_capability_artifact(value: Any, source: str) -> CapabilityProbeArtifact:
    payload = _mapping(value, source)
    _closed(payload, {"id", "behaviorProbeID", "attempt", "returnedOutputPath", "transientOutputPath", "sha256", "widthPixels", "heightPixels", "canvasResult", "disposition", "productionUse", "reason", "provenance", "byteVerification", "recordedAt", "deletionVerifiedAt"}, source)
    attempt = _positive_int(payload["attempt"], f"{source}.attempt")
    if attempt not in (1, 2, 3):
        raise PresentationRemediationAuditError(f"{source}.attempt must be 1, 2, or 3")
    canvas_result = _string(payload["canvasResult"], f"{source}.canvasResult")
    if canvas_result not in {"exactCanvas", "wrongCanvas"}:
        raise PresentationRemediationAuditError(f"{source}.canvasResult must be exactCanvas or wrongCanvas")
    if payload["disposition"] != "capabilityProbeRejected" or payload["productionUse"] != "forbidden":
        raise PresentationRemediationAuditError(
            "capability probe artifact must remain rejected and production-forbidden"
        )
    return CapabilityProbeArtifact(
        _string(payload["id"], f"{source}.id"),
        _string(payload["behaviorProbeID"], f"{source}.behaviorProbeID"),
        attempt,
        _string(payload["returnedOutputPath"], f"{source}.returnedOutputPath"),
        _string(payload["transientOutputPath"], f"{source}.transientOutputPath"),
        _sha256(payload["sha256"], f"{source}.sha256"),
        _positive_int(payload["widthPixels"], f"{source}.widthPixels"),
        _positive_int(payload["heightPixels"], f"{source}.heightPixels"),
        canvas_result,
        "capabilityProbeRejected",
        "forbidden",
        _string(payload["reason"], f"{source}.reason"),
        _load_candidate_provenance(payload["provenance"], f"{source}.provenance"),
        _load_byte_verification(payload["byteVerification"], f"{source}.byteVerification"),
        _instant(payload["recordedAt"], f"{source}.recordedAt"),
        _optional_instant(payload["deletionVerifiedAt"], f"{source}.deletionVerifiedAt"),
    )


def _load_canvas_preflight(value: Any, source: str) -> CanvasPreflight:
    payload = _mapping(value, source)
    _closed(payload, {"status", "blockedReason", "classes"}, source)
    status = _string(payload["status"], f"{source}.status")
    if status not in {"pending", "passed", "blocked"}:
        raise PresentationRemediationAuditError(f"{source}.status must be pending, passed, or blocked")
    classes_raw = payload["classes"]
    if not isinstance(classes_raw, list):
        raise PresentationRemediationAuditError(f"{source}.classes must be an array")
    classes: list[CanvasClass] = []
    for class_index, class_item in enumerate(classes_raw):
        class_source = f"{source}.classes[{class_index}]"
        canvas_class = _mapping(class_item, class_source)
        _closed(canvas_class, {"widthPixels", "heightPixels", "coveredRecordKeys", "status", "blockedReason", "behaviorProbes"}, class_source)
        probes_raw = canvas_class["behaviorProbes"]
        if not isinstance(probes_raw, list):
            raise PresentationRemediationAuditError(f"{class_source}.behaviorProbes must be an array")
        probes: list[CanvasBehaviorProbe] = []
        for probe_index, probe_item in enumerate(probes_raw):
            probe_source = f"{class_source}.behaviorProbes[{probe_index}]"
            probe = _mapping(probe_item, probe_source)
            _closed(probe, {"id", "behavior", "representativeRecordKey", "prompt", "sourceInputs", "preflightComparatorSet", "artifactIDs", "status", "blockedReason"}, "preflight probe")
            inputs_raw = probe["sourceInputs"]
            if not isinstance(inputs_raw, list):
                raise PresentationRemediationAuditError(f"{probe_source}.sourceInputs must be an array")
            behavior = _string(probe["behavior"], f"{probe_source}.behavior")
            if behavior not in {"edit", "generate"}:
                raise PresentationRemediationAuditError(f"{probe_source}.behavior must be edit or generate")
            probe_status = _string(probe["status"], f"{probe_source}.status")
            if probe_status not in {"pending", "passed", "blocked"}:
                raise PresentationRemediationAuditError(f"{probe_source}.status must be pending, passed, or blocked")
            probes.append(
                CanvasBehaviorProbe(
                    _string(probe["id"], f"{probe_source}.id"),
                    behavior,
                    _string(probe["representativeRecordKey"], f"{probe_source}.representativeRecordKey"),
                    _string(probe["prompt"], f"{probe_source}.prompt"),
                    tuple(_load_source_input(item, f"{probe_source}.sourceInputs[{index}]") for index, item in enumerate(inputs_raw)),
                    _load_preflight_comparator_set(probe["preflightComparatorSet"], f"{probe_source}.preflightComparatorSet"),
                    _string_array(probe["artifactIDs"], f"{probe_source}.artifactIDs"),
                    probe_status,
                    _optional_string(probe["blockedReason"], f"{probe_source}.blockedReason"),
                )
            )
        class_status = _string(canvas_class["status"], f"{class_source}.status")
        if class_status not in {"pending", "passed", "blocked"}:
            raise PresentationRemediationAuditError(f"{class_source}.status must be pending, passed, or blocked")
        classes.append(
            CanvasClass(
                _positive_int(canvas_class["widthPixels"], f"{class_source}.widthPixels"),
                _positive_int(canvas_class["heightPixels"], f"{class_source}.heightPixels"),
                _string_array(canvas_class["coveredRecordKeys"], f"{class_source}.coveredRecordKeys"),
                class_status,
                _optional_string(canvas_class["blockedReason"], f"{class_source}.blockedReason"),
                tuple(probes),
            )
        )
    return CanvasPreflight(status, _optional_string(payload["blockedReason"], f"{source}.blockedReason"), tuple(classes))


def _load_phase2_root(value: Any, source: str = "phase2") -> Phase2Root:
    payload = _mapping(value, source)
    _closed(payload, {"canvasPreflight", "capabilityProbeCheck", "batches", "finalChecks"}, source)
    capability = _mapping(payload["capabilityProbeCheck"], f"{source}.capabilityProbeCheck")
    _closed(capability, {"artifacts"}, f"{source}.capabilityProbeCheck")
    artifacts_raw = capability["artifacts"]
    batches_raw = payload["batches"]
    if not isinstance(artifacts_raw, list) or not isinstance(batches_raw, list):
        raise PresentationRemediationAuditError(f"{source} artifacts and batches must be arrays")
    batches: list[RemediationBatch] = []
    for index, item in enumerate(batches_raw):
        batch_source = f"{source}.batches[{index}]"
        batch = _mapping(item, batch_source)
        _closed(batch, {"id", "order", "kind", "recordKeys", "status", "blockedReason", "checks"}, batch_source)
        checks = _mapping(batch["checks"], f"{batch_source}.checks")
        _closed(checks, {"packageValidation", "focusedTests", "fullPackageSuite"}, f"{batch_source}.checks")
        batches.append(
            RemediationBatch(
                _string(batch["id"], f"{batch_source}.id"),
                _positive_int(batch["order"], f"{batch_source}.order"),
                _string(batch["kind"], f"{batch_source}.kind"),
                _string_array(batch["recordKeys"], f"{batch_source}.recordKeys"),
                _string(batch["status"], f"{batch_source}.status"),
                _optional_string(batch["blockedReason"], f"{batch_source}.blockedReason"),
                {key: _load_phase2_check(checks[key], f"{batch_source}.checks.{key}") for key in ("packageValidation", "focusedTests", "fullPackageSuite")},
            )
        )
    final_checks = _mapping(payload["finalChecks"], f"{source}.finalChecks")
    final_names = {"crossCatalogReview", "manifestValidation", "finalInventory", "packageTestSuite", "buildForTesting", "simulatorReview", "contextCleanup"}
    _closed(final_checks, final_names, f"{source}.finalChecks")
    return Phase2Root(
        _load_canvas_preflight(payload["canvasPreflight"], f"{source}.canvasPreflight"),
        tuple(_load_capability_artifact(item, f"{source}.capabilityProbeCheck.artifacts[{index}]") for index, item in enumerate(artifacts_raw)),
        tuple(batches),
        {key: _load_phase2_check(final_checks[key], f"{source}.finalChecks.{key}") for key in final_names},
    )


def load_presentation_remediation_manifest(
    path: Path,
) -> PresentationRemediationManifest:
    """Load a closed manifest without reading a board package."""
    manifest_path = Path(path)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PresentationRemediationAuditError(
            f"presentation remediation manifest must be a regular file: {manifest_path}"
        )
    try:
        payload = _mapping(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            "presentation remediation manifest",
        )
    except json.JSONDecodeError as error:
        raise PresentationRemediationAuditError(
            f"presentation remediation manifest is invalid JSON: {manifest_path}"
        ) from error
    if "schemaVersion" not in payload:
        raise PresentationRemediationAuditError(
            "presentation remediation manifest is missing keys: ['schemaVersion']"
        )
    if (
        isinstance(payload["schemaVersion"], bool)
        or not isinstance(payload["schemaVersion"], int)
    ):
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.schemaVersion must be a JSON integer equal to 1"
        )
    schema_version = payload["schemaVersion"]
    if schema_version not in (1, 2):
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.schemaVersion must equal 1 or 2"
        )
    root_keys = {"schemaVersion", "phase", "reviewDate", "packageIDs", "records", "phase1Checks"}
    if schema_version == 2:
        root_keys.add("phase2")
    _closed(payload, root_keys, "presentation remediation manifest")
    expected_phase = "sourceReclassification" if schema_version == 1 else "assetRemediation"
    if payload["phase"] != expected_phase:
        raise PresentationRemediationAuditError(
            f"presentation remediation manifest.phase must be {expected_phase}"
        )
    review_date = _date(
        payload["reviewDate"], "presentation remediation manifest.reviewDate"
    )
    if review_date != _PLANNED_AUDIT_DATE:
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.reviewDate must equal planned audit date "
            f"{_PLANNED_AUDIT_DATE.isoformat()}"
        )
    package_ids = _string_array(
        payload["packageIDs"], "presentation remediation manifest.packageIDs"
    )
    if len(package_ids) != len(set(package_ids)) or any(
        not is_board_identifier(identifier) for identifier in package_ids
    ):
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.packageIDs must be unique board IDs"
        )
    records_value = payload["records"]
    if not isinstance(records_value, list):
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.records must be an array"
        )
    phase1_payload = _mapping(
        payload["phase1Checks"], "presentation remediation manifest.phase1Checks"
    )
    _closed(
        phase1_payload, _PHASE1_CHECKS, "presentation remediation manifest.phase1Checks"
    )
    loader = _load_record if schema_version == 1 else _load_phase2_record
    records = tuple(loader(record, f"records[{index}]", review_date) for index, record in enumerate(records_value))
    return PresentationRemediationManifest(
        schema_version,
        expected_phase,
        review_date,
        package_ids,
        records,
        {
            key: _load_phase1_check(
                phase1_payload[key],
                f"presentation remediation manifest.phase1Checks.{key}",
            )
            for key in _PHASE1_CHECKS
        },
        None if schema_version == 1 else _load_phase2_root(payload["phase2"]),
    )


def _current_png_facts(path: Path) -> tuple[str, int, int]:
    data = path.read_bytes()
    if data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        raise PresentationRemediationAuditError(f"asset is not a PNG: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return hashlib.sha256(data).hexdigest(), width, height


def _render_input(input_item: GenerationSourceInput) -> str:
    location = input_item.source_url or input_item.asset_path or "unavailable"
    return f"{input_item.id}, {input_item.source_type}, {input_item.role}, {location}"


def _render_bootstrap_axis(axis: BootstrapComparatorAxis | None) -> str:
    if axis is None:
        return "unavailable"
    return (
        f"{axis.axis}: {axis.asset_path}, {axis.source_record_key}, "
        f"{axis.accepted_asset_sha256}, {axis.reason}"
    )


def render_phase2_generation_prompt(record: PresentationRemediationRecord) -> str:
    """Return the canonical prompt assembled from literal Phase 2 fields."""
    if not isinstance(record.generation, Phase2Generation):
        raise PresentationRemediationAuditError("production prompt requires a schema-2 record")
    generation = record.generation
    if generation.mode not in {"builtInEdit", "builtInGenerate"}:
        raise PresentationRemediationAuditError("production prompt requires built-in edit or generate mode")
    if generation.required_canvas is None or record.phase2_comparator is None:
        raise PresentationRemediationAuditError("production prompt requires canvas and Phase 2 comparator")
    singular = record.phase2_comparator.generation_time
    bootstrap = record.phase2_comparator.bootstrap_comparator_set
    if (singular is None) == (bootstrap is None):
        raise PresentationRemediationAuditError("comparator paths are mutually exclusive")
    use_case = "precise-object-edit" if generation.mode == "builtInEdit" else "product-mockup"
    request = "edit" if generation.mode == "builtInEdit" else "regenerate"
    input_images = "; ".join(_render_input(item) for item in generation.source_inputs)
    subject = "; ".join(
        source.supported_claim for source in (*record.evidence.official, *record.evidence.independent)
    )
    findings = "; ".join(
        f"{key}: {record.findings[key].explanation}"
        for key in _FINDING_ORDER
        if record.findings[key].outcome in _FAILURE_OUTCOMES
    )
    if singular is not None:
        comparator = (
            f"singular {singular.mode}: {singular.asset_path}, {singular.source_record_key}, "
            f"{singular.accepted_asset_sha256}, {singular.reason}"
        )
        material_ruling = "not applicable; singular ready baseline selected"
    else:
        assert bootstrap is not None
        absent = ", ".join(bootstrap.absent_axes) if bootstrap.absent_axes else "none"
        comparator = (
            f"bootstrap {bootstrap.cohort_id}/{bootstrap.status}; "
            f"{_render_bootstrap_axis(bootstrap.composition_framing_scale)}; "
            f"{_render_bootstrap_axis(bootstrap.material_texture_lighting)}; "
            f"explicit absent axes: {absent}"
        )
        material_ruling = (
            "for a missing material axis, exact live material evidence and the shared render "
            "contract govern material; a composition asset never governs material or geometry"
        )
    canvas = generation.required_canvas
    lines = (
        f"Use case: {use_case}",
        f"Asset type: Hang Ten package presentation PNG at {record.asset_path}",
        f"Primary request: {request} {record.product_name}; physical revision: {record.physical_revision}; working surface: {record.working_surface}",
        f"Input images: {input_images}",
        "Scene/backdrop: common off-white studio background; no wall or mounting scenery",
        f"Subject: {subject}",
        "Style/medium: original simplified unbranded catalog product render, not a photograph",
        f"Composition/framing: orthographic head-on to {record.working_surface}; centered; complete uncropped product; untouched output canvas exactly {canvas.width_pixels} by {canvas.height_pixels}",
        "Lighting/mood: neutral direction; restrained contact shadow; controlled depth relief",
        f"Materials/textures: {' + '.join(record.materials)}; preserve only evidence-supported finish and construction cues",
        f"Repair findings: {findings}",
        f"Comparator: {comparator}",
        f"Bootstrap material ruling: {material_ruling}",
        f"Current asset role: {generation.current_asset_role}",
        "Constraints: preserve every source-proved contact, component, silhouette, and usable-surface orientation; add no unsupported detail; output must already have exact dimensions",
        "Avoid: branding, labels, logos, text, watermark, transparent background, camera tilt, source-photo styling, invented contacts, invented hardware, and every forbidden post-processing operation",
    )
    return "\n".join(lines)


def render_phase2_capability_probe_prompt(
    probe: CanvasBehaviorProbe,
    required_canvas: RequiredCanvas,
) -> str:
    """Return the disposable preflight-only prompt; never production authorization."""
    if probe.behavior not in {"edit", "generate"}:
        raise PresentationRemediationAuditError("capability prompt behavior is invalid")
    comparator = probe.preflight_comparator_set
    if comparator.material_texture_lighting is not None:
        raise PresentationRemediationAuditError("preflight material comparator is always unavailable")
    if comparator.production_authorization != "forbidden":
        raise PresentationRemediationAuditError("preflight production authorization must be forbidden")
    evidence_inputs = tuple(
        item for item in probe.source_inputs if item.source_type in {"officialEvidence", "independentEvidence"}
    )
    current_targets = tuple(item for item in probe.source_inputs if item.id == "current-target")
    if probe.behavior == "generate" and current_targets:
        raise PresentationRemediationAuditError("generate capability probe cannot use a current target")
    input_images = "; ".join(_render_input(item) for item in evidence_inputs)
    if probe.behavior == "edit":
        input_images += (
            "; for edit-capability only, the current target is tool input but not evidence or style reference"
        )
    composition = comparator.composition_framing_scale
    composition_text = (
        "unavailable"
        if composition is None
        else f"{composition.asset_path}, {composition.source_record_key}, {composition.accepted_asset_sha256}, {composition.reason}"
    )
    lines = (
        "Purpose: disposable image-tool exact-canvas capability probe; never a production candidate, comparator, baseline, or accepted asset",
        f"Behavior: {probe.behavior}-capability",
        f"Representative: {probe.representative_record_key}; identity cues come only from freshly reopened official/independent evidence",
        f"Input images: {input_images}",
        "Scene/backdrop: common off-white studio background; no wall or mounting scenery",
        f"Composition reference: {composition_text}",
        "Material reference: unavailable; live evidence and the shared material contract govern material appearance",
        f"Material contract: {comparator.shared_material_contract}",
        f"Canvas request: untouched PNG output exactly {required_canvas.width_pixels} by {required_canvas.height_pixels}",
        "Disposition: every returned output is capabilityProbeRejected and must be hashed, recorded separately, and deleted",
        "Production authorization: forbidden",
        "Avoid: branding, labels, logos, text, watermark, transparent background, camera tilt, invented product detail, and every post-processing operation",
    )
    rendered = "\n".join(lines)
    forbidden = ("readyBaseline", "bootstrapComparatorSet", "acceptedCohortBaseline", "cohortBootstrapBaseline")
    if any(label in rendered for label in forbidden):
        raise PresentationRemediationAuditError("capability prompt contains a production label")
    return rendered


def _all_source_inputs(manifest: PresentationRemediationManifest) -> tuple[GenerationSourceInput, ...]:
    inputs: list[GenerationSourceInput] = []
    for record in manifest.records:
        if isinstance(record.generation, Phase2Generation):
            inputs.extend(record.generation.source_inputs)
    if manifest.phase2 is not None:
        for canvas_class in manifest.phase2.canvas_preflight.classes:
            for probe in canvas_class.behavior_probes:
                inputs.extend(probe.source_inputs)
    return tuple(inputs)


def verify_transient_source_files(
    manifest: PresentationRemediationManifest,
    source_files: Mapping[str, Path],
) -> tuple[str, ...]:
    """Verify supplied source-input SHA keys against temporary bytes."""
    declared: dict[str, set[str | None]] = {}
    for input_item in _all_source_inputs(manifest):
        declared.setdefault(input_item.sha256, set()).add(input_item.asset_path)
    verified: list[str] = []
    for digest, path_value in source_files.items():
        expected = _sha256(digest, "source-file SHA-256")
        path = Path(path_value)
        if expected not in declared:
            raise PresentationRemediationAuditError("source file hash is not declared by this manifest")
        declared_paths = {item for item in declared[expected] if item is not None}
        if declared_paths and str(path) not in declared_paths:
            raise PresentationRemediationAuditError("source file path is not declared for its hash")
        if path.is_symlink() or not path.is_file():
            raise PresentationRemediationAuditError(f"source file must be a regular file: {path}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise PresentationRemediationAuditError("source SHA-256 mismatch")
        verified.append(expected)
    return tuple(sorted(verified))


def verify_transient_candidate_files(
    manifest: PresentationRemediationManifest,
    candidate_files: Mapping[str, Path],
) -> tuple[str, ...]:
    """Verify supplied candidate SHA keys against temporary PNG bytes and IHDR."""
    declared: dict[str, list[tuple[str, int, int]]] = {}
    for record in manifest.records:
        if isinstance(record.generation, Phase2Generation):
            for candidate in record.generation.candidates:
                declared.setdefault(candidate.sha256, []).append(
                    (candidate.transient_output_path, candidate.width_pixels, candidate.height_pixels)
                )
    if manifest.phase2 is not None:
        for artifact in manifest.phase2.capability_probe_artifacts:
            for path in (artifact.returned_output_path, artifact.transient_output_path):
                declared.setdefault(artifact.sha256, []).append(
                    (path, artifact.width_pixels, artifact.height_pixels)
                )
    verified: list[str] = []
    for digest, path_value in candidate_files.items():
        expected = _sha256(digest, "candidate-file SHA-256")
        path = Path(path_value)
        declarations = declared.get(expected, [])
        if not declarations:
            raise PresentationRemediationAuditError("candidate file hash is not declared by this manifest")
        matching = tuple(item for item in declarations if item[0] == str(path))
        if not matching:
            raise PresentationRemediationAuditError("candidate file path is not declared for its hash")
        if path.is_symlink() or not path.is_file():
            raise PresentationRemediationAuditError(f"candidate file must be a regular file: {path}")
        observed, width, height = _current_png_facts(path)
        if observed != expected:
            raise PresentationRemediationAuditError("candidate SHA-256 mismatch")
        if any((width, height) != (item[1], item[2]) for item in matching):
            raise PresentationRemediationAuditError("candidate IHDR dimensions mismatch")
        verified.append(expected)
    return tuple(sorted(verified))


def _is_evidence_blocked(record: PresentationRemediationRecord) -> bool:
    return (
        record.evidence.official_evidence_gap is not None
        or record.evidence.independent_evidence_gap is not None
    )


def _canonical_statement_matches(value: str, statement: str) -> bool:
    return value == statement


def _surface_unusable_statement(working_surface: str) -> str:
    return f'Surface "{working_surface}" is unusable.'


def _revision_conflict_statement(
    working_surface: str, first_revision: str, second_revision: str
) -> str:
    return (
        f'Surface "{working_surface}" has conflicting physical revisions: '
        f'"{first_revision}" versus "{second_revision}".'
    )


def _physical_revision_declaration(first_revision: str, second_revision: str) -> str:
    return f'Physical revisions: "{first_revision}" versus "{second_revision}".'


def _is_canonical_style_only_reason(reason: str) -> bool:
    prefix = "Accepted cohort baseline; style-only: "
    if not reason.startswith(prefix):
        return False
    if not reason.endswith("."):
        return False
    terms = tuple(reason.removeprefix(prefix).removesuffix(".").split(", "))
    return (
        bool(terms)
        and len(terms) == len(set(terms))
        and set(terms) <= _STYLE_ONLY_TERMS
    )


def _validate_unsupported_surface_removal(
    record: PresentationRemediationRecord,
) -> None:
    finding = record.findings["topology"]
    cited_sources = (*record.evidence.official, *record.evidence.independent)
    statement = _surface_unusable_statement(record.working_surface)
    if (
        _is_evidence_blocked(record)
        or finding.outcome != "nonconforming"
        or not _canonical_statement_matches(finding.explanation, statement)
        or not any(
            _canonical_statement_matches(source.supported_claim, statement)
            for source in cited_sources
        )
    ):
        raise PresentationRemediationAuditError(
            "removeUnsupportedPresentation requires canonical cited proof that the declared working surface is unusable"
        )


def _validate_physical_revision_split(record: PresentationRemediationRecord) -> None:
    sources = (*record.evidence.official, *record.evidence.independent)
    named_sources = tuple(
        source
        for source in sources
        if _NAMED_REVISION.search(source.revision_applicability)
    )
    named_revisions = {
        source.revision_applicability.casefold(): source.revision_applicability
        for source in named_sources
    }
    if _is_evidence_blocked(record) or len(named_revisions) != 2:
        raise PresentationRemediationAuditError(
            "splitPhysicalRevision requires canonical physicalRevision declaration"
        )
    first_revision, second_revision = sorted(named_revisions.values(), key=str.casefold)
    statement = _revision_conflict_statement(
        record.working_surface, first_revision, second_revision
    )
    if record.physical_revision != _physical_revision_declaration(
        first_revision, second_revision
    ):
        raise PresentationRemediationAuditError(
            "splitPhysicalRevision requires canonical physicalRevision declaration"
        )
    for source in named_sources:
        if not _canonical_statement_matches(source.supported_claim, statement):
            raise PresentationRemediationAuditError(
                "splitPhysicalRevision requires canonical cited conflict proof for named physical revisions"
            )


def _all_findings_conform(record: PresentationRemediationRecord) -> bool:
    return all(
        record.findings[key].outcome == "conforms" for key in _FINDING_KEYS
    )


def _checks_are_pending(record: PresentationRemediationRecord) -> bool:
    return all(
        check.status == "pending" and check.evidence is None
        for check in (
            *record.final.workbench_review.values(),
            *record.final.validation.values(),
        )
    )


def _is_ready_accepted_keep(record: PresentationRemediationRecord) -> bool:
    return (
        record.decision == "keep"
        and not _is_evidence_blocked(record)
        and _all_findings_conform(record)
        and record.final.accepted_asset_sha256 == record.current_asset.sha256
        and record.final.final_dimensions
        == (record.current_asset.width_pixels, record.current_asset.height_pixels)
        and record.final.visual_reviewer_decision == "acceptedCurrentAsset"
        and _checks_are_pending(record)
    )


def _validate_phase_truth(record: PresentationRemediationRecord) -> None:
    repair = record.decision != "keep"
    if repair:
        if (
            record.generation.prompt is not None
            or record.generation.current_asset_role is not None
            or record.generation.source_images
            or record.generation.candidates
            or record.final.accepted_asset_sha256 is not None
            or record.final.final_dimensions is not None
            or record.final.visual_reviewer_decision != "pendingPhase2"
            or not _checks_are_pending(record)
        ):
            raise PresentationRemediationAuditError(
                f"{record.decision} must not claim accepted output or final validation in Phase 1"
            )
        if record.decision == "removeUnsupportedPresentation":
            _validate_unsupported_surface_removal(record)
        elif record.decision == "splitPhysicalRevision":
            _validate_physical_revision_split(record)
        elif record.decision == "edit":
            if any(
                record.findings[key].outcome != "conforms"
                for key in ("productLikeness", "topology")
            ):
                raise PresentationRemediationAuditError(
                    "edit requires conforming productLikeness and topology findings"
                )
            if not any(
                record.findings[key].outcome in _FAILURE_OUTCOMES
                for key in _BOUNDED_EDIT_FINDINGS
            ):
                raise PresentationRemediationAuditError(
                    "edit requires a bounded presentation failure or uncertainty"
                )
        elif record.decision == "regenerate" and not any(
            record.findings[key].outcome in _FAILURE_OUTCOMES
            for key in ("productLikeness", "topology")
        ):
            raise PresentationRemediationAuditError(
                "regenerate requires a productLikeness or topology failure or uncertainty"
            )
        return
    if (
        record.generation.prompt is not None
        or record.generation.current_asset_role is not None
        or record.generation.source_images
        or record.generation.candidates
    ):
        raise PresentationRemediationAuditError(
            "keep must not claim Phase 2 generation"
        )
    if not _checks_are_pending(record):
        raise PresentationRemediationAuditError(
            "sourceReclassification presentation checks must remain pending with null evidence"
        )
    if _is_evidence_blocked(record):
        if (
            not any(
                finding.outcome == "uncertain" for finding in record.findings.values()
            )
            or record.final.accepted_asset_sha256 is not None
            or record.final.final_dimensions is not None
            or record.final.visual_reviewer_decision != "blockedEvidence"
        ):
            raise PresentationRemediationAuditError(
                "evidence-blocked keep must remain blockedEvidence without accepted output"
            )
    else:
        if not _all_findings_conform(record):
            raise PresentationRemediationAuditError(
                "source-supported accepted keep requires all seven findings to conform"
            )
        if (
            record.final.accepted_asset_sha256 != record.current_asset.sha256
            or record.final.final_dimensions
            != (record.current_asset.width_pixels, record.current_asset.height_pixels)
            or record.final.visual_reviewer_decision != "acceptedCurrentAsset"
        ):
            raise PresentationRemediationAuditError(
                "keep accepted hash must match current asset and dimensions"
            )


def _validate_source_reclassification_manifest(
    manifest: PresentationRemediationManifest,
    inventory: BoardInventory,
    *,
    hangboards_root: Path,
    selected_package_ids: frozenset[str] = frozenset(),
    final_validation: bool = False,
) -> PresentationRemediationReport:
    """Cross-check a manifest against real inventory and on-disk PNG facts."""
    if final_validation and selected_package_ids:
        raise PresentationRemediationAuditError(
            "final Phase 1 validation requires full-catalog coverage"
        )
    if final_validation and any(
        check.status != "passed" or check.command is None
        for check in manifest.phase1_checks.values()
    ):
        raise PresentationRemediationAuditError(
            "final Phase 1 validation requires all phase1Checks passed"
        )
    expected = {
        (package.board.id, presentation.id): (
            package,
            presentation,
            Path(hangboards_root).name
            + "/"
            + package.root.name
            + "/"
            + presentation.asset_path,
        )
        for package in inventory.packages
        for presentation in package.board.presentations
    }
    inventory_ids = frozenset(package.board.id for package in inventory.packages)
    if set(manifest.package_ids) != inventory_ids:
        raise PresentationRemediationAuditError(
            "manifest packageIDs must exactly equal inventory board IDs"
        )
    if not selected_package_ids <= inventory_ids:
        raise PresentationRemediationAuditError(
            f"unknown selected package IDs: {sorted(selected_package_ids - inventory_ids)}"
        )
    actual = {
        (record.package_id, record.presentation_id): record
        for record in manifest.records
    }
    if len(actual) != len(manifest.records):
        raise PresentationRemediationAuditError("duplicate presentation record")
    for key, record in actual.items():
        if key not in expected:
            raise PresentationRemediationAuditError(
                f"unknown presentation record: {'/'.join(key)}"
            )
        package, presentation, expected_asset_path = expected[key]
        if record.product_name != package.board.name:
            raise PresentationRemediationAuditError(
                f"productName does not match for {'/'.join(key)}"
            )
        if record.manufacturer != package.board.manufacturer:
            raise PresentationRemediationAuditError(
                f"manufacturer does not match for {'/'.join(key)}"
            )
        if record.asset_path != expected_asset_path:
            raise PresentationRemediationAuditError(
                f"assetPath does not match for {'/'.join(key)}"
            )
        digest, width, height = _current_png_facts(
            package.root / presentation.asset_path
        )
        if record.current_asset.sha256 != digest:
            raise PresentationRemediationAuditError(
                f"SHA-256 does not match for {'/'.join(key)}"
            )
        if (record.current_asset.width_pixels, record.current_asset.height_pixels) != (
            width,
            height,
        ):
            raise PresentationRemediationAuditError(
                f"dimensions do not match for {'/'.join(key)}"
            )
        _validate_phase_truth(record)
    required_ids = selected_package_ids or inventory_ids
    for package_id, presentation_id in sorted(expected):
        if package_id in required_ids and (package_id, presentation_id) not in actual:
            raise PresentationRemediationAuditError(
                f"missing presentation record: {package_id}/{presentation_id}"
            )
    for record in manifest.records:
        comparator = record.comparator
        ready = (
            all(
                value is not None
                for value in (
                    comparator.asset_path,
                    comparator.material_match,
                    comparator.form_factor_match,
                    comparator.reason,
                )
            )
            and comparator.baseline_gap is None
        )
        gap = (
            all(
                value is None
                for value in (
                    comparator.asset_path,
                    comparator.material_match,
                    comparator.form_factor_match,
                    comparator.reason,
                )
            )
            and comparator.baseline_gap is not None
        )
        if not ready and not gap:
            raise PresentationRemediationAuditError(
                "comparator must use exactly one ready or gap mode"
            )
        if gap:
            if record.decision == "keep" and not _is_evidence_blocked(record):
                raise PresentationRemediationAuditError(
                    "accepted keep requires a ready comparator"
                )
            continue
        target = next(
            (
                candidate
                for candidate in manifest.records
                if candidate.asset_path == comparator.asset_path
            ),
            None,
        )
        if target is None or not _is_ready_accepted_keep(target):
            raise PresentationRemediationAuditError(
                "comparator must identify a ready accepted keep record"
            )
        if not set(record.materials) & set(target.materials):
            raise PresentationRemediationAuditError(
                "comparator material is incompatible"
            )
        if record.form_factor != target.form_factor:
            raise PresentationRemediationAuditError(
                "comparator form factor is incompatible"
            )
        if not _is_canonical_style_only_reason(comparator.reason):
            raise PresentationRemediationAuditError(
                "comparator reason must use canonical style-only statement"
            )
    selected_records = [
        record for record in manifest.records if record.package_id in required_ids
    ]
    decisions: dict[str, int] = {}
    for record in selected_records:
        decisions[record.decision] = decisions.get(record.decision, 0) + 1
    return PresentationRemediationReport(
        tuple(sorted(required_ids)),
        len(selected_records),
        decisions,
        tuple(
            sorted(
                record.asset_path
                for record in selected_records
                if _is_evidence_blocked(record)
            )
        ),
    )


def _record_key(record: PresentationRemediationRecord) -> str:
    return f"{record.package_id}/{record.presentation_id}"


def _is_phase2_keep(record: PresentationRemediationRecord) -> bool:
    return record.decision == "keep"


def _check_pending(check: PresentationCheck) -> bool:
    return check.status == "pending" and check.evidence is None


def _check_passed(check: PresentationCheck) -> bool:
    return check.status == "passed" and check.evidence is not None


def _require_command_evidence(check: PresentationCheck, name: str) -> None:
    if not _check_passed(check):
        return
    assert check.evidence is not None
    requirements = {
        "packageValidation": ("scripts/hangboard-packages.sh validate",),
        "focusedTests": ("python -m pytest", "test_presentation_remediation_audit.py"),
        "fullPackageSuite": ("python -m pytest", "Tools/HangboardPackages/tests"),
        "buildForTesting": ("xcodebuild",),
    }
    if any(token not in check.evidence for token in requirements[name]):
        raise PresentationRemediationAuditError(
            f"{name} passed status requires its literal command evidence"
        )


def _verify_durable_byte_record(
    declared_sha: str,
    verification: ByteVerification,
    *,
    missing_message: str,
    mismatch_message: str,
) -> None:
    if verification.status != "passed":
        raise PresentationRemediationAuditError(missing_message)
    if verification.observed_sha256 != declared_sha:
        raise PresentationRemediationAuditError(mismatch_message)


def _require_verification_command(
    verification: ByteVerification,
    mode_flag: str,
    file_flag: str,
) -> None:
    if verification.status != "passed":
        return
    assert verification.command is not None
    if mode_flag not in verification.command or file_flag not in verification.command:
        raise PresentationRemediationAuditError(
            "byte verification command does not match the declared lifecycle"
        )


def _validate_phase2_evidence_review(record: PresentationRemediationRecord) -> None:
    assert record.phase2_action is not None
    assert record.phase2_evidence_review is not None
    action = record.phase2_action
    review = record.phase2_evidence_review
    if (action.state == "blocked") != (action.blocked_reason is not None):
        raise PresentationRemediationAuditError(
            "blocked Phase 2 action requires exactly one non-empty blockedReason"
        )
    if record.decision == "keep":
        if action.state != "notRequired":
            raise PresentationRemediationAuditError("keep requires notRequired")
        if (
            review.result != "notRequired"
            or review.reviewed_at is not None
            or review.official_urls_reopened
            or review.independent_urls_reopened
            or review.evidence_gap_searches_repeated
            or review.notes != _KEEP_PHASE2_NOTE
        ):
            raise PresentationRemediationAuditError(
                "keep Phase 2 evidence review must remain factually notRequired"
            )
        return
    if review.result == "notRequired":
        raise PresentationRemediationAuditError(
            "repair evidence review cannot be notRequired"
        )
    if action.state == "pending":
        if (
            review.result != "pending"
            or review.reviewed_at is not None
            or review.official_urls_reopened
            or review.independent_urls_reopened
            or review.evidence_gap_searches_repeated
            or review.notes != _PENDING_PHASE2_NOTE
        ):
            raise PresentationRemediationAuditError(
                "pending Phase 2 action requires the exact pending evidence review"
            )
    if action.state == "completed" and review.result != "confirmed":
        raise PresentationRemediationAuditError(
            "completed Phase 2 action requires confirmed evidence review"
        )
    if action.state == "inProgress" and review.result != "confirmed":
        raise PresentationRemediationAuditError(
            "in-progress Phase 2 action requires confirmed evidence review"
        )
    if review.result in {"confirmed", "blocked"}:
        if review.reviewed_at is None:
            raise PresentationRemediationAuditError(
                "terminal Phase 2 evidence review requires reviewedAt"
            )
        official = tuple(source.url for source in record.evidence.official)
        independent = tuple(source.url for source in record.evidence.independent)
        if review.official_urls_reopened != official or review.independent_urls_reopened != independent:
            raise PresentationRemediationAuditError(
                "reopened evidence URLs must exactly preserve historical URL order"
            )
        gap_count = sum(
            item is not None
            for item in (
                record.evidence.official_evidence_gap,
                record.evidence.independent_evidence_gap,
            )
        )
        if len(review.evidence_gap_searches_repeated) != gap_count:
            raise PresentationRemediationAuditError(
                "evidence gap searches must be repeated once per historical gap"
            )
    if review.result == "blocked":
        if action.state != "blocked" or review.notes != action.blocked_reason:
            raise PresentationRemediationAuditError(
                "blocked evidence review and action must share the same reason"
            )


def _validate_source_input_linkage(
    record: PresentationRemediationRecord,
    record_index: int,
    input_item: GenerationSourceInput,
) -> None:
    if not input_item.supplied_to_imagegen:
        raise PresentationRemediationAuditError("declared generation source input must be supplied to imagegen")
    if input_item.id == "current-target" and input_item.source_type != "currentAsset":
        raise PresentationRemediationAuditError("current-target must use currentAsset sourceType")
    if input_item.id in {"style-comparator", "bootstrap-composition", "bootstrap-material", "preflight-composition"} and input_item.source_type != "comparator":
        raise PresentationRemediationAuditError("comparator input ID must use comparator sourceType")
    if input_item.source_type == "officialEvidence" and re.fullmatch(r"official-\d+-image-\d+", input_item.id) is None:
        raise PresentationRemediationAuditError("official evidence input ID is not canonical")
    if input_item.source_type == "independentEvidence" and re.fullmatch(r"independent-\d+-image-\d+", input_item.id) is None:
        raise PresentationRemediationAuditError("independent evidence input ID is not canonical")
    if input_item.byte_verification.status == "passed" and input_item.byte_verification.observed_sha256 != input_item.sha256:
        raise PresentationRemediationAuditError("source verification hash mismatch")
    if input_item.source_type in {"officialEvidence", "independentEvidence"}:
        evidence_kind = "official" if input_item.source_type == "officialEvidence" else "independent"
        entries = record.evidence.official if evidence_kind == "official" else record.evidence.independent
        match = re.fullmatch(rf"/records/{record_index}/evidence/{evidence_kind}/(\d+)", input_item.evidence_pointer or "")
        if match is None or int(match.group(1)) >= len(entries):
            raise PresentationRemediationAuditError("evidence input pointer does not resolve")
        id_match = re.fullmatch(rf"{evidence_kind}-(\d+)-image-(\d+)", input_item.id)
        if id_match is None or int(id_match.group(1)) != int(match.group(1)):
            raise PresentationRemediationAuditError("evidence input ID does not match its pointer")
        evidence = entries[int(match.group(1))]
        if input_item.source_url != evidence.url or input_item.role != evidence.image_role or input_item.asset_path is not None:
            raise PresentationRemediationAuditError("evidence input does not match its historical evidence leaf")
    else:
        if input_item.evidence_pointer is not None or input_item.source_url is not None or input_item.asset_path is None:
            raise PresentationRemediationAuditError("current/comparator input must use only its package asset path")
    path = Path(input_item.asset_path) if input_item.asset_path is not None else None
    if input_item.byte_verification.status == "passed":
        if input_item.byte_verification.observed_sha256 != input_item.sha256:
            raise PresentationRemediationAuditError("source verification hash mismatch")
    elif path is not None and path.exists():
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != input_item.sha256:
            raise PresentationRemediationAuditError("source SHA-256 mismatch")
    elif path is not None:
        raise PresentationRemediationAuditError(
            "deleted source input requires passed transient byte verification"
        )


def _validate_generation_and_final(
    record: PresentationRemediationRecord,
    record_index: int,
    on_disk_facts: tuple[str, int, int] | None,
) -> None:
    assert isinstance(record.generation, Phase2Generation)
    assert record.phase2_action is not None
    generation = record.generation
    action = record.phase2_action
    key = _record_key(record)
    if record.decision == "splitPhysicalRevision":
        raise PresentationRemediationAuditError(
            "schema 2 has no splitPhysicalRevision action in the approved remediation matrix"
        )
    allowed_final_decisions = {
        "acceptedCurrentAsset",
        "blockedEvidence",
        "pendingPhase2",
        "acceptedPhase2",
        "blockedPhase2",
        "removedUnsupportedPresentation",
    }
    if record.final.visual_reviewer_decision not in allowed_final_decisions:
        raise PresentationRemediationAuditError("visualReviewerDecision is not a supported Phase 2 state")
    ids = tuple(item.id for item in generation.source_inputs)
    if len(ids) != len(set(ids)):
        raise PresentationRemediationAuditError("generation source input IDs must be unique")
    for input_item in generation.source_inputs:
        _validate_source_input_linkage(record, record_index, input_item)
        _require_verification_command(
            input_item.byte_verification, "--phase2-partial", "--source-file"
        )
    attempts = tuple(candidate.attempt for candidate in generation.candidates)
    if attempts != tuple(sorted(set(attempts))) or any(attempt not in (1, 2, 3) for attempt in attempts):
        raise PresentationRemediationAuditError("candidate attempts must be unique increasing values from 1 through 3")
    for candidate in generation.candidates:
        _require_verification_command(
            candidate.byte_verification, "--phase2-partial", "--candidate-file"
        )
        if candidate.byte_verification.status == "passed" and candidate.byte_verification.observed_sha256 != candidate.sha256:
            raise PresentationRemediationAuditError("candidate verification hash mismatch")
        candidate_path = Path(candidate.transient_output_path)
        if candidate_path.exists():
            observed, width, height = _current_png_facts(candidate_path)
            if observed != candidate.sha256:
                raise PresentationRemediationAuditError("candidate SHA-256 mismatch")
            if (width, height) != (candidate.width_pixels, candidate.height_pixels):
                raise PresentationRemediationAuditError("candidate IHDR dimensions mismatch")
        else:
            _verify_durable_byte_record(
                candidate.sha256,
                candidate.byte_verification,
                missing_message="deleted candidate requires passed transient byte verification",
                mismatch_message="candidate verification hash mismatch",
            )
    if record.decision == "keep":
        if generation.mode != "none" or generation.prompt is not None or generation.required_canvas is not None or generation.source_inputs or generation.current_asset_role is not None or generation.candidates:
            raise PresentationRemediationAuditError("keep requires generation mode none")
        accepted_keep = not _is_evidence_blocked(record)
        expected_decision = "acceptedCurrentAsset" if accepted_keep else "blockedEvidence"
        if record.final.visual_reviewer_decision != expected_decision:
            raise PresentationRemediationAuditError("keep final decision does not preserve Phase 1 truth")
        if accepted_keep:
            if record.final.accepted_asset_sha256 != record.current_asset.sha256 or record.final.final_dimensions != (record.current_asset.width_pixels, record.current_asset.height_pixels) or on_disk_facts != (record.current_asset.sha256, record.current_asset.width_pixels, record.current_asset.height_pixels):
                raise PresentationRemediationAuditError("keep accepted hash/dimensions must equal unchanged on-disk bytes")
        elif record.final.accepted_asset_sha256 is not None or record.final.final_dimensions is not None:
            raise PresentationRemediationAuditError("evidence-blocked keep must preserve null accepted hash/dimensions")
        if any(not _check_pending(record.final.workbench_review[name]) for name in ("normal", "allActive", "individualHolds")):
            raise PresentationRemediationAuditError("keeps retain pending Phase 1 Workbench checks")
        hit_test = record.final.workbench_review["hitTest"]
        if hit_test.status != "notRequired" or hit_test.evidence is None:
            raise PresentationRemediationAuditError("keep hitTest must be factually notRequired")
        if any(not _check_pending(record.final.validation[name]) for name in ("packageValidation", "focusedTests", "fullPackageSuite", "buildForTesting")):
            raise PresentationRemediationAuditError("keeps retain pending Phase 1 validation fields")
        simulator = record.final.validation["simulatorReview"]
        assert isinstance(simulator, SimulatorReview)
        if simulator.state != "pending" or simulator.reviewed_at is not None or simulator.environment_evidence_ids or simulator.device_runs:
            raise PresentationRemediationAuditError("keeps retain pending simulator review")
        return
    expected_mode = {"edit": "builtInEdit", "regenerate": "builtInGenerate", "removeUnsupportedPresentation": "none"}[record.decision]
    if generation.mode != expected_mode:
        if record.decision == "edit":
            raise PresentationRemediationAuditError("edit requires builtInEdit")
        if record.decision == "regenerate":
            raise PresentationRemediationAuditError("regenerate requires builtInGenerate")
        raise PresentationRemediationAuditError("removal requires generation mode none")
    if record.decision == "removeUnsupportedPresentation":
        if generation.prompt is not None or generation.required_canvas is not None or generation.source_inputs or generation.candidates or generation.current_asset_role is not None:
            raise PresentationRemediationAuditError("removal cannot contain image generation state")
    else:
        if generation.required_canvas is None or (generation.required_canvas.width_pixels, generation.required_canvas.height_pixels) != (record.current_asset.width_pixels, record.current_asset.height_pixels):
            raise PresentationRemediationAuditError("generation requiredCanvas must equal historical current asset dimensions")
        role = "Built-in edit target and topology/likeness invariant." if record.decision == "edit" else "Human comparison only; not evidence and not supplied to imagegen."
        if generation.current_asset_role != role:
            raise PresentationRemediationAuditError("currentAssetRole does not match generation mode")
        if generation.prompt is not None and generation.prompt != render_phase2_generation_prompt(record):
            raise PresentationRemediationAuditError("stored Phase 2 generation prompt does not equal canonical rendering")
        if action.state in {"inProgress", "completed", "blocked"} and generation.source_inputs and generation.prompt is None:
            raise PresentationRemediationAuditError("started generation requires a canonical prompt")
        current_targets = tuple(item for item in generation.source_inputs if item.id == "current-target")
        if record.decision == "edit" and generation.source_inputs and len(current_targets) != 1:
            raise PresentationRemediationAuditError("edit requires exactly one current-target input")
        if record.decision == "regenerate" and current_targets:
            raise PresentationRemediationAuditError("regenerate prohibits current-target input")
        if current_targets and current_targets[0].sha256 != record.current_asset.sha256:
            raise PresentationRemediationAuditError("current-target hash must equal historical currentAsset")
        comparator = record.phase2_comparator
        assert comparator is not None
        style_inputs = tuple(item for item in generation.source_inputs if item.id == "style-comparator")
        bootstrap_composition = tuple(item for item in generation.source_inputs if item.id == "bootstrap-composition")
        bootstrap_material = tuple(item for item in generation.source_inputs if item.id == "bootstrap-material")
        if comparator.generation_time is not None and generation.source_inputs:
            if len(style_inputs) != 1 or bootstrap_composition or bootstrap_material:
                raise PresentationRemediationAuditError("singular comparator generation requires exactly one style-comparator input")
            if style_inputs[0].sha256 != comparator.generation_time.accepted_asset_sha256 or style_inputs[0].asset_path != comparator.generation_time.asset_path:
                raise PresentationRemediationAuditError("style-comparator input does not match selection")
        bootstrap = comparator.bootstrap_comparator_set
        if bootstrap is not None and generation.source_inputs:
            if style_inputs:
                raise PresentationRemediationAuditError("bootstrap generation prohibits style-comparator input")
            expected_composition = 0 if bootstrap.composition_framing_scale is None else 1
            expected_material = 0 if bootstrap.material_texture_lighting is None else 1
            if len(bootstrap_composition) != expected_composition or len(bootstrap_material) != expected_material:
                raise PresentationRemediationAuditError("bootstrap generation inputs must match every non-null axis")
            if not any(item.source_type in {"officialEvidence", "independentEvidence"} for item in generation.source_inputs):
                raise PresentationRemediationAuditError("bootstrap generation requires live evidence input")
            official_ids = tuple(item.id for item in generation.source_inputs if item.source_type == "officialEvidence")
            independent_ids = tuple(item.id for item in generation.source_inputs if item.source_type == "independentEvidence")
            if official_ids != bootstrap.official_evidence_input_ids or independent_ids != bootstrap.independent_evidence_input_ids:
                raise PresentationRemediationAuditError("bootstrap evidence input IDs must match supplied inputs in order")
        if (generation.candidates or action.state == "completed") and any(item.byte_verification.status != "passed" for item in generation.source_inputs):
            raise PresentationRemediationAuditError("deleted source input requires passed transient byte verification")
    validation = record.final.validation
    package_check = validation["packageValidation"]
    focused_check = validation["focusedTests"]
    full_check = validation["fullPackageSuite"]
    build_check = validation["buildForTesting"]
    assert isinstance(package_check, PresentationCheck)
    assert isinstance(focused_check, PresentationCheck)
    assert isinstance(full_check, PresentationCheck)
    assert isinstance(build_check, PresentationCheck)
    for name, check in (
        ("packageValidation", package_check),
        ("focusedTests", focused_check),
        ("fullPackageSuite", full_check),
        ("buildForTesting", build_check),
    ):
        _require_command_evidence(check, name)
    if _check_passed(focused_check) and not _check_passed(package_check):
        raise PresentationRemediationAuditError("focused tests cannot pass before package validation")
    if _check_passed(full_check) and not _check_passed(focused_check):
        raise PresentationRemediationAuditError("full package suite cannot pass before focused tests")
    if _check_passed(build_check) and not _check_passed(full_check):
        raise PresentationRemediationAuditError("build cannot pass before the batch full package suite")
    simulator = validation["simulatorReview"]
    assert isinstance(simulator, SimulatorReview)
    _validate_simulator_review(record, simulator, _check_passed(build_check))
    if action.state == "completed":
        if record.decision in {"edit", "regenerate"}:
            accepted = tuple(candidate for candidate in generation.candidates if candidate.disposition == "accepted")
            if len(accepted) != 1:
                raise PresentationRemediationAuditError("completed repair requires exactly one accepted candidate")
            candidate = accepted[0]
            if candidate.byte_verification.status != "passed":
                raise PresentationRemediationAuditError(
                    "completed repair requires passed accepted-candidate byte verification"
                )
            if record.final.accepted_asset_sha256 != candidate.sha256 or record.final.final_dimensions != (candidate.width_pixels, candidate.height_pixels) or on_disk_facts != (candidate.sha256, candidate.width_pixels, candidate.height_pixels):
                raise PresentationRemediationAuditError("accepted candidate must equal on-disk asset")
            if record.final.visual_reviewer_decision != "acceptedPhase2":
                raise PresentationRemediationAuditError("completed repair requires acceptedPhase2")
        else:
            if on_disk_facts is not None or record.final.accepted_asset_sha256 is not None or record.final.final_dimensions is not None or record.final.visual_reviewer_decision != "removedUnsupportedPresentation":
                raise PresentationRemediationAuditError("completed removal requires absent presentation and removedUnsupportedPresentation")
        if any(not _check_passed(check) for check in record.final.workbench_review.values()):
            raise PresentationRemediationAuditError("completed Phase 2 action requires four passed Workbench checks")
        if not _check_passed(package_check) or not _check_passed(focused_check):
            raise PresentationRemediationAuditError("completed Phase 2 action requires package and focused validation")
    elif action.state == "pending":
        if record.final.accepted_asset_sha256 is not None or record.final.final_dimensions is not None or record.final.visual_reviewer_decision != "pendingPhase2":
            raise PresentationRemediationAuditError("pending action must retain pending Phase 2 final state")
        if any(not _check_pending(check) for check in record.final.workbench_review.values()):
            raise PresentationRemediationAuditError("pending action cannot prewrite Workbench results")
        if on_disk_facts != (record.current_asset.sha256, record.current_asset.width_pixels, record.current_asset.height_pixels):
            raise PresentationRemediationAuditError("pending action must retain original on-disk bytes")
    elif action.state in {"blocked", "inProgress"} and record.final.accepted_asset_sha256 is None:
        if on_disk_facts != (record.current_asset.sha256, record.current_asset.width_pixels, record.current_asset.height_pixels):
            raise PresentationRemediationAuditError("non-accepted action must retain original on-disk bytes")


def _validate_simulator_review(
    record: PresentationRemediationRecord,
    review: SimulatorReview,
    build_passed: bool,
) -> None:
    if review.state == "pending":
        if review.reviewed_at is not None or review.environment_evidence_ids or review.device_runs:
            raise PresentationRemediationAuditError("pending simulator review must have no evidence or runs")
        return
    if review.state == "notApplicableRemovedPresentation":
        if record.decision != "removeUnsupportedPresentation" or review.reviewed_at is None or not review.environment_evidence_ids or review.device_runs:
            raise PresentationRemediationAuditError("removed-presentation simulator state requires sourced removal evidence and no runs")
        return
    if review.state == "passedDirectInspection":
        if not build_passed:
            raise PresentationRemediationAuditError("simulator review cannot pass before buildForTesting")
        if review.reviewed_at is None or not review.environment_evidence_ids:
            raise PresentationRemediationAuditError("direct simulator review requires date and environment evidence")
        if tuple(sorted(run.device_class for run in review.device_runs)) != ("phone", "tablet"):
            raise PresentationRemediationAuditError("direct simulator review requires exactly phone and tablet device classes")
        if len({run.simulator_uuid for run in review.device_runs}) != 2:
            raise PresentationRemediationAuditError("simulator UUIDs must be unique")
        for run in review.device_runs:
            if not run.capture_sha256s:
                raise PresentationRemediationAuditError("simulator device run requires capture hash list")
            for key, state in run.flows.items():
                if state == "blocked":
                    raise PresentationRemediationAuditError("passed simulator review cannot contain blocked flows")
                if state == "notApplicableSinglePresentation" and key != "presentationSelector":
                    raise PresentationRemediationAuditError("only presentationSelector accepts notApplicableSinglePresentation")
                if state == "notApplicableNoCompatiblePlan" and key != "plan":
                    raise PresentationRemediationAuditError("only plan accepts notApplicableNoCompatiblePlan")
        return
    if review.state == "blocked":
        if review.reviewed_at is None or not review.environment_evidence_ids or record.phase2_action is None or record.phase2_action.state != "blocked":
            raise PresentationRemediationAuditError("blocked simulator review must agree with blocked Phase 2 action")


def _accepted_record_hash(record: PresentationRemediationRecord) -> str | None:
    return record.final.accepted_asset_sha256


def _validate_selection(
    consumer: PresentationRemediationRecord,
    selection: ComparatorSelection,
    records_by_key: Mapping[str, PresentationRemediationRecord],
    *,
    final: bool,
) -> None:
    consumer_key = _record_key(consumer)
    if selection.mode == "cohortBootstrapBaseline":
        if not final or selection.source_record_key != consumer_key:
            raise PresentationRemediationAuditError(
                "self reference is reserved for accepted cohort bootstrap seed"
            )
        if selection.reason != _COHORT_BASELINE_REASON:
            raise PresentationRemediationAuditError("cohort bootstrap final reason is not canonical")
        if selection.asset_path != consumer.asset_path or selection.accepted_asset_sha256 != consumer.final.accepted_asset_sha256:
            raise PresentationRemediationAuditError("cohort bootstrap final comparator must name its own accepted asset")
        return
    if selection.mode != "readyBaseline":
        raise PresentationRemediationAuditError("temporary gaps cannot authorize generation")
    target = records_by_key.get(selection.source_record_key)
    if target is None:
        raise PresentationRemediationAuditError("comparator source record does not exist")
    if selection.source_record_key == consumer_key:
        raise PresentationRemediationAuditError(
            "self reference is reserved for accepted cohort bootstrap seed"
        )
    if selection.asset_path != target.asset_path or selection.accepted_asset_sha256 != _accepted_record_hash(target):
        raise PresentationRemediationAuditError("comparator selection does not match accepted source asset")
    if target.final.visual_reviewer_decision not in {"acceptedCurrentAsset", "acceptedPhase2"}:
        raise PresentationRemediationAuditError("comparator must identify an accepted visual asset")
    if not set(consumer.materials) & set(target.materials):
        raise PresentationRemediationAuditError("comparator material is incompatible")
    if consumer.form_factor != target.form_factor:
        raise PresentationRemediationAuditError("comparator form factor is incompatible")
    if selection.reason != _SINGULAR_COMPARATOR_REASON:
        raise PresentationRemediationAuditError("singular comparator reason is not canonical")
    record_order = {key: index for index, key in enumerate(records_by_key)}
    consumer_order = (
        _REPAIR_TASK_BY_KEY.get(consumer_key, 10_000),
        record_order[consumer_key],
    )
    target_order = (
        0 if target.decision == "keep" else _REPAIR_TASK_BY_KEY.get(selection.source_record_key, 10_000),
        record_order[selection.source_record_key],
    )
    if target.decision != "keep" and (target.phase2_action is None or target.phase2_action.state != "completed"):
        raise PresentationRemediationAuditError("comparator repair is not completed")
    if target_order >= consumer_order:
        raise PresentationRemediationAuditError("comparator must precede consumer")


def _validate_bootstrap_set(
    record: PresentationRemediationRecord,
    bootstrap: BootstrapComparatorSet,
    records_by_key: Mapping[str, PresentationRemediationRecord],
) -> None:
    key = _record_key(record)
    canonical = _BOOTSTRAP_SEEDS.get(bootstrap.cohort_id)
    if canonical is not None and canonical[0] != key:
        seed = records_by_key.get(canonical[0])
        if (
            seed is not None
            and seed.phase2_comparator is not None
            and seed.phase2_comparator.bootstrap_comparator_set is not None
            and seed.phase2_comparator.bootstrap_comparator_set.status == "acceptedCohortBaseline"
        ):
            raise PresentationRemediationAuditError("cohort already has a singular baseline")
    if canonical is None or canonical[0] != key:
        raise PresentationRemediationAuditError("record is not an authorized cohort seed")
    expected_seed, expected_composition, expected_material, expected_absent = canonical
    if bootstrap.seed_record_key != expected_seed:
        raise PresentationRemediationAuditError("bootstrap selection does not match canonical seed order")
    actual_composition = None if bootstrap.composition_framing_scale is None else bootstrap.composition_framing_scale.source_record_key
    actual_material = None if bootstrap.material_texture_lighting is None else bootstrap.material_texture_lighting.source_record_key
    if key == "escape-beta-22/primary" and bootstrap.material_texture_lighting is not None:
        material_source = records_by_key.get(actual_material or "")
        if material_source is not None and "wood" in material_source.materials:
            raise PresentationRemediationAuditError("wood cannot govern moldedPlastic material")
    if (actual_composition, actual_material) != (expected_composition, expected_material):
        raise PresentationRemediationAuditError("bootstrap selection does not match canonical seed order")
    null_axes = tuple(
        axis_name
        for axis_name, axis in (
            ("compositionFramingScale", bootstrap.composition_framing_scale),
            ("materialTextureLighting", bootstrap.material_texture_lighting),
        )
        if axis is None
    )
    if bootstrap.absent_axes != null_axes or bootstrap.absent_axes != expected_absent:
        raise PresentationRemediationAuditError("bootstrap absent axes do not match null axes")
    for axis_name, axis, reason in (
        ("compositionFramingScale", bootstrap.composition_framing_scale, _BOOTSTRAP_COMPOSITION_REASON),
        ("materialTextureLighting", bootstrap.material_texture_lighting, _BOOTSTRAP_MATERIAL_REASON),
    ):
        if axis is None:
            continue
        target = records_by_key.get(axis.source_record_key)
        if axis.axis != axis_name or target is None or axis.asset_path != target.asset_path or axis.accepted_asset_sha256 != target.final.accepted_asset_sha256 or axis.reason != reason:
            raise PresentationRemediationAuditError("bootstrap selection does not match canonical seed order")
        if target.decision != "keep" and (
            target.phase2_action is None or target.phase2_action.state != "completed"
        ):
            raise PresentationRemediationAuditError(
                "bootstrap selection does not match canonical seed order"
            )
        if axis_name == "materialTextureLighting":
            expected_tokens = tuple(item for item in record.materials if item in target.materials)
            if not expected_tokens or axis.matched_material_tokens != expected_tokens:
                raise PresentationRemediationAuditError("bootstrap material tokens do not match source and seed")
        elif axis.matched_material_tokens:
            raise PresentationRemediationAuditError("composition axis cannot claim material tokens")
    if bootstrap.shared_render_contract != _BOOTSTRAP_SHARED_RENDER_CONTRACT or bootstrap.selection_rule != _BOOTSTRAP_SELECTION_RULE:
        raise PresentationRemediationAuditError("bootstrap render contract or selection rule is not canonical")
    checks = bootstrap.review_checks
    if not _check_passed(checks.evidence_review):
        raise PresentationRemediationAuditError("bootstrap selection requires passed evidence review")
    if record.phase2_evidence_review is None or record.phase2_evidence_review.result != "confirmed":
        raise PresentationRemediationAuditError("bootstrap selection requires confirmed record evidence review")
    all_four = all(_check_passed(check) for check in (checks.evidence_review, checks.visual_review, checks.workbench_review, checks.package_validation))
    if bootstrap.status == "acceptedCohortBaseline":
        package_check = record.final.validation["packageValidation"]
        assert isinstance(package_check, PresentationCheck)
        record_reviews_pass = (
            record.final.visual_reviewer_decision == "acceptedPhase2"
            and all(_check_passed(check) for check in record.final.workbench_review.values())
            and _check_passed(package_check)
        )
        if not all_four or not record_reviews_pass or bootstrap.accepted_at is None or bootstrap.blocked_reason is not None:
            raise PresentationRemediationAuditError(
                "bootstrap acceptance requires passed evidence, visual, Workbench, and package review"
            )
    elif bootstrap.status == "selected":
        if bootstrap.accepted_at is not None or bootstrap.blocked_reason is not None:
            raise PresentationRemediationAuditError("selected bootstrap cannot claim acceptance or block")
    elif bootstrap.status == "blocked":
        if bootstrap.blocked_reason is None or record.phase2_action is None or record.phase2_action.blocked_reason != bootstrap.blocked_reason:
            raise PresentationRemediationAuditError("blocked bootstrap and action must share the same reason")


def _validate_phase2_comparator_graph(manifest: PresentationRemediationManifest) -> None:
    records_by_key = {_record_key(record): record for record in manifest.records}
    edges = {
        _record_key(record): record.phase2_comparator.generation_time.source_record_key
        for record in manifest.records
        if record.phase2_comparator is not None
        and record.phase2_comparator.generation_time is not None
    }
    for start in edges:
        seen: set[str] = set()
        cursor = start
        while cursor in edges:
            if cursor in seen:
                raise PresentationRemediationAuditError("comparator graph contains a cycle")
            seen.add(cursor)
            cursor = edges[cursor]
    for record in manifest.records:
        comparator = record.phase2_comparator
        assert comparator is not None
        key = _record_key(record)
        if record.decision in {"keep", "removeUnsupportedPresentation"}:
            if comparator.generation_time is not None or comparator.bootstrap_comparator_set is not None or comparator.final is not None:
                raise PresentationRemediationAuditError("keep/removal Phase 2 comparators must be null")
            continue
        generation = record.generation
        assert isinstance(generation, Phase2Generation)
        started = bool(generation.source_inputs or generation.candidates or generation.prompt) or (record.phase2_action is not None and record.phase2_action.state in {"inProgress", "completed", "blocked"})
        singular = comparator.generation_time
        bootstrap = comparator.bootstrap_comparator_set
        if started and singular is None and bootstrap is None:
            raise PresentationRemediationAuditError("generation requires a singular comparator or bootstrap set")
        if singular is not None and bootstrap is not None:
            raise PresentationRemediationAuditError("comparator paths are mutually exclusive")
        if singular is not None:
            _validate_selection(record, singular, records_by_key, final=False)
        if bootstrap is not None:
            _validate_bootstrap_set(record, bootstrap, records_by_key)
        if record.phase2_action is not None and record.phase2_action.state == "completed":
            if comparator.final is None:
                raise PresentationRemediationAuditError("completed repair requires a final comparator")
            _validate_selection(record, comparator.final, records_by_key, final=True)
            if bootstrap is not None:
                if comparator.final.mode != "cohortBootstrapBaseline" or comparator.final.source_record_key != key or bootstrap.status != "acceptedCohortBaseline":
                    raise PresentationRemediationAuditError("seed final comparator must name its accepted cohort baseline")
            elif singular is not None and comparator.final != singular:
                raise PresentationRemediationAuditError("final comparator must preserve generation-time singular selection")
        elif comparator.final is not None:
            raise PresentationRemediationAuditError("final comparator cannot precede completion")


def _production_hashes_and_paths(manifest: PresentationRemediationManifest) -> tuple[set[str], set[str]]:
    hashes: set[str] = set()
    paths: set[str] = set()
    for record in manifest.records:
        if isinstance(record.generation, Phase2Generation):
            for input_item in record.generation.source_inputs:
                hashes.add(input_item.sha256)
                if input_item.asset_path is not None:
                    paths.add(input_item.asset_path)
            for candidate in record.generation.candidates:
                hashes.add(candidate.sha256)
                paths.add(candidate.transient_output_path)
        if record.final.accepted_asset_sha256 is not None:
            hashes.add(record.final.accepted_asset_sha256)
        comparator = record.phase2_comparator
        if comparator is not None:
            for selection in (comparator.generation_time, comparator.final):
                if selection is not None:
                    hashes.add(selection.accepted_asset_sha256)
                    paths.add(selection.asset_path)
            bootstrap = comparator.bootstrap_comparator_set
            if bootstrap is not None:
                for axis in (bootstrap.composition_framing_scale, bootstrap.material_texture_lighting):
                    if axis is not None:
                        hashes.add(axis.accepted_asset_sha256)
                        paths.add(axis.asset_path)
    return hashes, paths


def _validate_artifact_disjointness(manifest: PresentationRemediationManifest) -> None:
    assert manifest.phase2 is not None
    production_hashes, production_paths = _production_hashes_and_paths(manifest)
    artifact_hashes: set[str] = set()
    artifact_paths: set[str] = set()
    for artifact in manifest.phase2.capability_probe_artifacts:
        if artifact.sha256 in production_hashes or artifact.returned_output_path in production_paths or artifact.transient_output_path in production_paths:
            raise PresentationRemediationAuditError("capability probe artifact overlaps production state")
        if artifact.sha256 in artifact_hashes or artifact.returned_output_path in artifact_paths or artifact.transient_output_path in artifact_paths:
            raise PresentationRemediationAuditError("duplicate capability probe artifact hash or path")
        artifact_hashes.add(artifact.sha256)
        artifact_paths.update((artifact.returned_output_path, artifact.transient_output_path))


def _validate_canvas_preflight(manifest: PresentationRemediationManifest) -> None:
    assert manifest.phase2 is not None
    preflight = manifest.phase2.canvas_preflight
    repair_keys = {_record_key(record) for record in manifest.records if record.decision in {"edit", "regenerate"}}
    full_catalog = len(repair_keys) == 65
    if full_catalog:
        dimensions = tuple((item.width_pixels, item.height_pixels) for item in preflight.classes)
        if len(preflight.classes) != 20 or set(dimensions) != set(_PREFLIGHT_COVERAGE):
            raise PresentationRemediationAuditError("canvas preflight must contain the exact 20 canvas classes")
        covered = tuple(key for item in preflight.classes for key in item.covered_record_keys)
        if len(covered) != 65 or len(set(covered)) != 65 or set(covered) != repair_keys:
            raise PresentationRemediationAuditError(
                "canvas preflight must cover exactly 65 edit/regenerate record keys"
            )
    artifacts = {artifact.id: artifact for artifact in manifest.phase2.capability_probe_artifacts}
    if len(artifacts) != len(manifest.phase2.capability_probe_artifacts):
        raise PresentationRemediationAuditError("capability artifact IDs must be unique")
    referenced_artifacts: set[str] = set()
    assignments = {item[0]: item for item in _PREFLIGHT_ASSIGNMENTS}
    records_by_key = {_record_key(record): (index, record) for index, record in enumerate(manifest.records)}
    probe_count = 0
    for canvas_class in preflight.classes:
        dims = (canvas_class.width_pixels, canvas_class.height_pixels)
        if full_catalog and canvas_class.covered_record_keys != _PREFLIGHT_COVERAGE[dims]:
            raise PresentationRemediationAuditError("canvas class coveredRecordKeys do not match canonical partition")
        for probe in canvas_class.behavior_probes:
            probe_count += 1
            assignment = assignments.get(probe.id)
            if full_catalog and assignment is None:
                raise PresentationRemediationAuditError("preflight probe is not in the exact assignment table")
            if assignment is not None:
                _, width, height, behavior, representative, reference_id = assignment
                if dims != (width, height) or probe.behavior != behavior or probe.representative_record_key != representative:
                    raise PresentationRemediationAuditError("preflight probe does not match the exact assignment table")
                comparator = probe.preflight_comparator_set
                expected_unavailable = (
                    ("compositionFramingScale", "materialTextureLighting")
                    if reference_id is None
                    else ("materialTextureLighting",)
                )
                if comparator.unavailable_axes != expected_unavailable:
                    raise PresentationRemediationAuditError("preflight unavailable axes do not match the exact assignment table")
                composition = comparator.composition_framing_scale
                if reference_id is None:
                    if composition is not None:
                        raise PresentationRemediationAuditError("preflight composition reference does not match the exact assignment table")
                else:
                    expected_key, expected_path, expected_hash = _PREFLIGHT_REFERENCES[reference_id]
                    if composition is None or (composition.source_record_key, composition.asset_path, composition.accepted_asset_sha256) != (expected_key, expected_path, expected_hash):
                        raise PresentationRemediationAuditError("preflight composition reference does not match the exact assignment table")
            comparator = probe.preflight_comparator_set
            if comparator.material_texture_lighting is not None or "materialTextureLighting" not in comparator.unavailable_axes:
                raise PresentationRemediationAuditError("preflight material comparator is always unavailable")
            if comparator.shared_material_contract != _PREFLIGHT_MATERIAL_CONTRACT or comparator.production_authorization != "forbidden":
                raise PresentationRemediationAuditError("preflight material/authorization contract is not canonical")
            input_ids = {item.id for item in probe.source_inputs}
            if len(input_ids) != len(probe.source_inputs):
                raise PresentationRemediationAuditError("preflight source input IDs must be unique")
            official_ids = tuple(item.id for item in probe.source_inputs if item.source_type == "officialEvidence")
            independent_ids = tuple(item.id for item in probe.source_inputs if item.source_type == "independentEvidence")
            if official_ids != comparator.official_evidence_input_ids or independent_ids != comparator.independent_evidence_input_ids:
                raise PresentationRemediationAuditError("preflight evidence IDs must match supplied inputs in order")
            if (set(comparator.official_evidence_input_ids) | set(comparator.independent_evidence_input_ids)) - input_ids:
                raise PresentationRemediationAuditError("preflight comparator evidence IDs do not resolve")
            if probe.source_inputs:
                representative = records_by_key.get(probe.representative_record_key)
                if representative is None:
                    raise PresentationRemediationAuditError("preflight representative record does not exist")
                record_index, record = representative
                for input_item in probe.source_inputs:
                    if input_item.id in {"style-comparator", "bootstrap-composition", "bootstrap-material"}:
                        raise PresentationRemediationAuditError("preflight source input uses a production comparator label")
                    _validate_source_input_linkage(record, record_index, input_item)
                    _require_verification_command(
                        input_item.byte_verification,
                        "--phase2-preflight",
                        "--source-file",
                    )
                current_targets = tuple(item for item in probe.source_inputs if item.id == "current-target")
                composition_inputs = tuple(item for item in probe.source_inputs if item.id == "preflight-composition")
                if probe.behavior == "edit" and len(current_targets) != 1:
                    raise PresentationRemediationAuditError("edit preflight probe requires exactly one current-target")
                if probe.behavior == "generate" and current_targets:
                    raise PresentationRemediationAuditError("generate preflight probe prohibits current-target")
                expected_composition_count = 0 if comparator.composition_framing_scale is None else 1
                if len(composition_inputs) != expected_composition_count:
                    raise PresentationRemediationAuditError("preflight composition input does not match assigned reference")
                if composition_inputs and (
                    composition_inputs[0].asset_path != comparator.composition_framing_scale.asset_path
                    or composition_inputs[0].sha256 != comparator.composition_framing_scale.accepted_asset_sha256
                ):
                    raise PresentationRemediationAuditError("preflight composition input does not match assigned reference")
                if not any(item.source_type in {"officialEvidence", "independentEvidence"} for item in probe.source_inputs):
                    raise PresentationRemediationAuditError("preflight probe requires live evidence input")
            rendered = render_phase2_capability_probe_prompt(
                probe,
                RequiredCanvas(canvas_class.width_pixels, canvas_class.height_pixels),
            )
            if probe.prompt != rendered:
                raise PresentationRemediationAuditError("stored capability prompt does not equal canonical rendering")
            for attempt_index, artifact_id in enumerate(probe.artifact_ids, 1):
                if artifact_id != f"{probe.id}-attempt-{attempt_index}":
                    raise PresentationRemediationAuditError("preflight artifact IDs must use exact attempt order")
                artifact = artifacts.get(artifact_id)
                if artifact is None or artifact.behavior_probe_id != probe.id or artifact.attempt != attempt_index:
                    raise PresentationRemediationAuditError("preflight artifact reference does not resolve exactly once")
                if artifact_id in referenced_artifacts:
                    raise PresentationRemediationAuditError(
                        "preflight artifact reference does not resolve exactly once"
                    )
                referenced_artifacts.add(artifact_id)
                exact = (artifact.width_pixels, artifact.height_pixels) == dims
                artifact_path = next(
                    (
                        Path(path)
                        for path in (artifact.transient_output_path, artifact.returned_output_path)
                        if Path(path).is_file()
                    ),
                    None,
                )
                if artifact_path is not None:
                    observed_sha, observed_width, observed_height = _current_png_facts(artifact_path)
                    if observed_sha != artifact.sha256 or (observed_width, observed_height) != (artifact.width_pixels, artifact.height_pixels):
                        raise PresentationRemediationAuditError("capability artifact bytes disagree with recorded hash/IHDR")
                if (artifact.canvas_result == "exactCanvas") != exact:
                    raise PresentationRemediationAuditError("capability probe canvasResult disagrees with IHDR")
                _verify_durable_byte_record(
                    artifact.sha256,
                    artifact.byte_verification,
                    missing_message="capability artifact requires passed transient byte verification",
                    mismatch_message="capability artifact verification hash mismatch",
                )
                _require_verification_command(
                    artifact.byte_verification,
                    "--phase2-preflight",
                    "--candidate-file",
                )
                if artifact.deletion_verified_at is None and not (
                    Path(artifact.returned_output_path).is_file()
                    or Path(artifact.transient_output_path).is_file()
                ):
                    raise PresentationRemediationAuditError(
                        "undeleted capability artifact must remain present at a recorded path"
                    )
                if artifact.deletion_verified_at is not None and (Path(artifact.returned_output_path).exists() or Path(artifact.transient_output_path).exists()):
                    raise PresentationRemediationAuditError("deleted capability artifact path still exists")
            if len(probe.artifact_ids) > 3:
                raise PresentationRemediationAuditError("preflight probe permits at most three attempts")
            if probe.status in {"passed", "blocked"}:
                if not probe.artifact_ids or any(artifacts[item].deletion_verified_at is None for item in probe.artifact_ids):
                    raise PresentationRemediationAuditError("terminal preflight probe requires recorded deleted artifacts")
                results = tuple(artifacts[item].canvas_result for item in probe.artifact_ids)
                if probe.status == "passed" and results[-1] != "exactCanvas":
                    raise PresentationRemediationAuditError("passed preflight probe requires terminal exactCanvas")
                if probe.status == "blocked" and (len(results) != 3 or any(result != "wrongCanvas" for result in results)):
                    raise PresentationRemediationAuditError("blocked preflight probe requires three wrongCanvas attempts")
            elif probe.blocked_reason is not None:
                raise PresentationRemediationAuditError("pending preflight probe cannot have blockedReason")
        class_statuses = tuple(probe.status for probe in canvas_class.behavior_probes)
        expected_class_status = (
            "blocked"
            if "blocked" in class_statuses
            else "passed"
            if class_statuses and all(status == "passed" for status in class_statuses)
            else "pending"
        )
        if canvas_class.status != expected_class_status:
            raise PresentationRemediationAuditError("canvas class status does not match its probe states")
    if full_catalog and probe_count != 22:
        raise PresentationRemediationAuditError("canvas preflight must contain exactly 22 behavior probes")
    if referenced_artifacts != set(artifacts):
        raise PresentationRemediationAuditError("every capability artifact must be referenced exactly once")
    class_states = tuple(item.status for item in preflight.classes)
    expected_preflight_status = (
        "blocked"
        if "blocked" in class_states
        else "passed"
        if class_states and all(state == "passed" for state in class_states)
        else "pending"
    )
    if preflight.status != expected_preflight_status:
        raise PresentationRemediationAuditError("canvas preflight status does not match class states")
    _validate_artifact_disjointness(manifest)


def _validate_batches(
    manifest: PresentationRemediationManifest,
    selected_batch_id: str | None,
) -> None:
    assert manifest.phase2 is not None
    batches = manifest.phase2.batches
    full_catalog = len(manifest.records) == 85
    if full_catalog and tuple(batch.id for batch in batches) != _BATCH_IDS:
        raise PresentationRemediationAuditError("Phase 2 batches must occur once in canonical order")
    if selected_batch_id is not None and selected_batch_id not in {batch.id for batch in batches}:
        raise PresentationRemediationAuditError("selected batch ID is not declared")
    seen_nonpassed = False
    active_count = 0
    owned: set[str] = set()
    records = {_record_key(record): record for record in manifest.records}
    for index, batch in enumerate(batches, 1):
        if batch.id not in _BATCH_IDS or batch.order != index or batch.kind != ("removal" if batch.id == "mini-bar-removal" else "repair"):
            raise PresentationRemediationAuditError("batch ID/order/kind does not match canonical order")
        if batch.status not in {"pending", "inProgress", "passed", "blocked"}:
            raise PresentationRemediationAuditError("batch status is invalid")
        if batch.status == "passed" and seen_nonpassed:
            raise PresentationRemediationAuditError("batch statuses must form a passed prefix")
        if batch.status != "passed":
            seen_nonpassed = True
        if batch.status in {"inProgress", "blocked"}:
            active_count += 1
        if (batch.status == "blocked") != (batch.blocked_reason is not None):
            raise PresentationRemediationAuditError("blocked batch requires exactly one reason")
        overlap = owned & set(batch.record_keys)
        if overlap:
            raise PresentationRemediationAuditError("record appears in more than one batch")
        owned.update(batch.record_keys)
        if full_catalog and batch.record_keys != _BATCH_RECORD_KEYS[batch.id]:
            raise PresentationRemediationAuditError("batch recordKeys do not match exclusive repair matrix")
        for key in batch.record_keys:
            record = records.get(key)
            if record is None or record.repair_batch_id != batch.id:
                raise PresentationRemediationAuditError("record repairBatchID does not match owning batch")
        if batch.status == "passed":
            if any(records[key].phase2_action is None or records[key].phase2_action.state != "completed" for key in batch.record_keys):
                raise PresentationRemediationAuditError("passed batch owns only completed actions")
            if any(not _check_passed(check) for check in batch.checks.values()):
                raise PresentationRemediationAuditError("passed batch requires three passed checks")
        _require_command_evidence(
            batch.checks["fullPackageSuite"], "fullPackageSuite"
        )
    if active_count > 1:
        raise PresentationRemediationAuditError("at most one batch may be in progress or blocked")
    nonkeeps = {_record_key(record) for record in manifest.records if record.decision != "keep"}
    if full_catalog and owned != nonkeeps:
        raise PresentationRemediationAuditError("batches must own every non-keep record exactly once")


def _validate_phase2_final_check_evidence(manifest: PresentationRemediationManifest) -> None:
    assert manifest.phase2 is not None
    token_requirements = {
        "manifestValidation": ("--phase2-partial",),
        "finalInventory": ("--final-inventory",),
        "packageTestSuite": ("python -m pytest", "tools/hangboardpackages/tests"),
        "buildForTesting": ("xcodebuild",),
        "simulatorReview": ("phone", "tablet"),
        "contextCleanup": ("cleanup_ok",),
    }
    for name, tokens in token_requirements.items():
        check = manifest.phase2.final_checks[name]
        if _check_passed(check):
            assert check.evidence is not None
            evidence = check.evidence.casefold()
            if any(token.casefold() not in evidence for token in tokens):
                raise PresentationRemediationAuditError(
                    f"Phase 2 finalChecks.{name} passed status requires literal evidence"
                )


def _record_asset_path(hangboards_root: Path, record: PresentationRemediationRecord) -> Path:
    relative = Path(record.asset_path)
    if relative.parts and relative.parts[0] == Path(hangboards_root).name:
        relative = Path(*relative.parts[1:])
    return Path(hangboards_root) / relative


def _validate_mini_bar_state(
    manifest: PresentationRemediationManifest,
    inventory: BoardInventory,
) -> None:
    records = {_record_key(record): record for record in manifest.records}
    primary = records.get("lattice.mini-bar/primary")
    removal = records.get("lattice.mini-bar/end")
    if primary is None or removal is None:
        return
    if primary.comparator.asset_path != primary.asset_path:
        raise PresentationRemediationAuditError("Mini Bar primary must preserve its Phase 1 self-baseline")
    package = next((item for item in inventory.packages if item.board.id == "lattice.mini-bar"), None)
    if package is None:
        raise PresentationRemediationAuditError("Mini Bar package is missing")
    if removal.phase2_action is not None and removal.phase2_action.state == "completed":
        if tuple(presentation.id for presentation in package.board.presentations) != ("primary",):
            raise PresentationRemediationAuditError("completed Mini Bar removal requires one primary presentation")
        assignments = {hold.id: hold.presentation_id for hold in package.board.holds}
        for hold_id in ("ergonomic-jug", "edge-10", "edge-20", "mini-pinch"):
            if assignments.get(hold_id) != "primary":
                raise PresentationRemediationAuditError("Mini Bar retained holds must all use primary presentation")


def _validate_phase2_manifest(
    manifest: PresentationRemediationManifest,
    inventory: BoardInventory,
    *,
    hangboards_root: Path,
    validation_mode: PresentationValidationMode,
    selected_batch_id: str | None,
    transient_source_files: Mapping[str, Path] | None,
    transient_candidate_files: Mapping[str, Path] | None,
) -> PresentationRemediationReport:
    if manifest.schema_version != 2 or manifest.phase != "assetRemediation" or manifest.phase2 is None:
        raise PresentationRemediationAuditError("Phase 2 validation requires schemaVersion 2 assetRemediation manifest")
    if manifest.phase2.canvas_preflight.status != "passed" and any(
        record.decision != "keep"
        and record.phase2_action is not None
        and record.phase2_action.state in {"inProgress", "completed", "blocked"}
        for record in manifest.records
    ):
        raise PresentationRemediationAuditError(
            "production actions require passed canvas preflight"
        )
    if validation_mode == PresentationValidationMode.PHASE2_FINAL and selected_batch_id is not None:
        raise PresentationRemediationAuditError("final Phase 2 validation rejects batch selection")
    if validation_mode == PresentationValidationMode.PHASE2_FINAL:
        initial_actions = tuple(
            record.phase2_action
            for record in manifest.records
            if record.phase2_action is not None
        )
        if any(action.state == "blocked" for action in initial_actions):
            raise PresentationRemediationAuditError(
                "final Phase 2 validation requires zero blocked Phase 2 actions"
            )
        if any(action.state in {"pending", "inProgress"} for action in initial_actions):
            raise PresentationRemediationAuditError(
                "final Phase 2 validation requires zero pending Phase 2 actions"
            )
    inventory_ids = frozenset(package.board.id for package in inventory.packages)
    if set(manifest.package_ids) != inventory_ids:
        raise PresentationRemediationAuditError("manifest packageIDs must exactly equal inventory board IDs")
    if len(manifest.package_ids) != len(set(manifest.package_ids)):
        raise PresentationRemediationAuditError("manifest packageIDs must remain unique")
    packages = {package.board.id: package for package in inventory.packages}
    expected = {
        f"{package.board.id}/{presentation.id}": (package, presentation)
        for package in inventory.packages
        for presentation in package.board.presentations
    }
    records_by_key = {_record_key(record): record for record in manifest.records}
    if len(records_by_key) != len(manifest.records):
        raise PresentationRemediationAuditError("duplicate presentation record")
    for index, record in enumerate(manifest.records):
        key = _record_key(record)
        package = packages.get(record.package_id)
        if package is None:
            raise PresentationRemediationAuditError(f"unknown presentation record: {key}")
        if record.product_name != package.board.name:
            raise PresentationRemediationAuditError(f"productName does not match for {key}")
        if record.manufacturer != package.board.manufacturer:
            raise PresentationRemediationAuditError(f"manufacturer does not match for {key}")
        expected_entry = expected.get(key)
        completed_removal = record.decision == "removeUnsupportedPresentation" and record.phase2_action is not None and record.phase2_action.state == "completed"
        if expected_entry is None and not completed_removal:
            raise PresentationRemediationAuditError(f"unknown presentation record: {key}")
        if expected_entry is not None:
            _, presentation = expected_entry
            expected_asset = f"{Path(hangboards_root).name}/{package.root.name}/{presentation.asset_path}"
            if record.asset_path != expected_asset:
                raise PresentationRemediationAuditError(f"assetPath does not match for {key}")
        asset_path = _record_asset_path(hangboards_root, record)
        facts = _current_png_facts(asset_path) if asset_path.is_file() else None
        if completed_removal and facts is not None:
            raise PresentationRemediationAuditError("completed removal asset still exists")
        if not completed_removal and facts is None:
            raise PresentationRemediationAuditError(f"presentation asset is missing for {key}")
        assert record.phase2_action is not None and record.phase2_evidence_review is not None and record.phase2_comparator is not None
        _validate_phase2_evidence_review(record)
        _validate_generation_and_final(record, index, facts)
    expected_keys = set(expected)
    missing = expected_keys - set(records_by_key)
    if missing:
        raise PresentationRemediationAuditError(f"missing presentation record: {sorted(missing)[0]}")
    if len(manifest.records) == 85:
        accepted_keeps = {
            _record_key(record)
            for record in manifest.records
            if record.decision == "keep" and not _is_evidence_blocked(record)
        }
        blocked_keeps = {
            _record_key(record)
            for record in manifest.records
            if record.decision == "keep" and _is_evidence_blocked(record)
        }
        if accepted_keeps != set(_SOURCE_SUPPORTED_KEEP_KEYS) or blocked_keeps != set(_HISTORICAL_BLOCKED_KEEP_KEYS):
            raise PresentationRemediationAuditError("Phase 2 keep partition must preserve the exact 17 accepted and two historical blocked keeps")
    if transient_source_files:
        verified_sources = verify_transient_source_files(manifest, transient_source_files)
        allowed_sources = _allowed_transient_source_hashes(manifest, validation_mode, selected_batch_id)
        if not set(verified_sources) <= allowed_sources:
            raise PresentationRemediationAuditError("source file is not legal in the selected lifecycle")
    if transient_candidate_files:
        verified_candidates = verify_transient_candidate_files(manifest, transient_candidate_files)
        allowed_candidates = _allowed_transient_candidate_hashes(manifest, validation_mode, selected_batch_id)
        if not set(verified_candidates) <= allowed_candidates:
            raise PresentationRemediationAuditError("candidate file is not legal in the selected lifecycle")
    _validate_canvas_preflight(manifest)
    _validate_batches(manifest, selected_batch_id)
    _validate_phase2_final_check_evidence(manifest)
    _validate_phase2_comparator_graph(manifest)
    _validate_mini_bar_state(manifest, inventory)
    actions = tuple(record.phase2_action for record in manifest.records if record.phase2_action is not None)
    blocked = sum(action.state == "blocked" for action in actions)
    pending = sum(action.state in {"pending", "inProgress"} for action in actions)
    if validation_mode == PresentationValidationMode.PHASE2_FINAL:
        if blocked:
            raise PresentationRemediationAuditError("final Phase 2 validation requires zero blocked Phase 2 actions")
        if pending:
            raise PresentationRemediationAuditError("final Phase 2 validation requires zero pending Phase 2 actions")
        if manifest.phase2.canvas_preflight.status != "passed" or any(batch.status != "passed" for batch in manifest.phase2.batches) or any(not _check_passed(check) for check in manifest.phase2.final_checks.values()):
            raise PresentationRemediationAuditError("final Phase 2 validation requires passed preflight, batches, and final checks")
    decisions: dict[str, int] = {}
    for record in manifest.records:
        decisions[record.decision] = decisions.get(record.decision, 0) + 1
    report = PresentationRemediationReport(
        tuple(sorted(inventory_ids)),
        len(manifest.records),
        decisions,
        tuple(sorted(record.asset_path for record in manifest.records if _is_evidence_blocked(record))),
        phase=manifest.phase,
        batch_id=selected_batch_id,
        canvas_class_count=len(manifest.phase2.canvas_preflight.classes),
        canvas_covered_repair_count=len({key for item in manifest.phase2.canvas_preflight.classes for key in item.covered_record_keys}),
        capability_probe_artifact_count=len(manifest.phase2.capability_probe_artifacts),
        historical_evidence_blocked_keeps=sum(record.decision == "keep" and _is_evidence_blocked(record) for record in manifest.records),
        blocked_phase2_action_count=blocked,
        original_presentation_count=len(manifest.records),
        inventory_presentation_count=len(expected),
        kept_presentation_count=sum(record.decision == "keep" for record in manifest.records),
        completed_edit_count=sum(record.decision == "edit" and record.phase2_action is not None and record.phase2_action.state == "completed" for record in manifest.records),
        completed_regeneration_count=sum(record.decision == "regenerate" and record.phase2_action is not None and record.phase2_action.state == "completed" for record in manifest.records),
        completed_removal_count=sum(record.decision == "removeUnsupportedPresentation" and record.phase2_action is not None and record.phase2_action.state == "completed" for record in manifest.records),
        pending_phase2_action_count=pending,
    )
    if validation_mode == PresentationValidationMode.PHASE2_FINAL:
        expected_totals = (61, 85, 84, 19, 17, 48, 1, 2)
        actual_totals = (
            len(inventory_ids), report.original_presentation_count, report.inventory_presentation_count,
            report.kept_presentation_count, report.completed_edit_count,
            report.completed_regeneration_count, report.completed_removal_count,
            report.historical_evidence_blocked_keeps,
        )
        if actual_totals != expected_totals:
            raise PresentationRemediationAuditError("final Phase 2 catalog totals do not match 61/85/84/19/17/48/1/2")
    return report


def _allowed_transient_source_hashes(
    manifest: PresentationRemediationManifest,
    mode: PresentationValidationMode,
    selected_batch_id: str | None,
) -> set[str]:
    if mode == PresentationValidationMode.PHASE2_PREFLIGHT:
        assert manifest.phase2 is not None
        return {item.sha256 for canvas in manifest.phase2.canvas_preflight.classes for probe in canvas.behavior_probes for item in probe.source_inputs}
    if mode == PresentationValidationMode.PHASE2_PARTIAL:
        return {
            item.sha256
            for record in manifest.records
            if selected_batch_id is None or record.repair_batch_id == selected_batch_id
            if isinstance(record.generation, Phase2Generation)
            for item in record.generation.source_inputs
        }
    return set()


def _allowed_transient_candidate_hashes(
    manifest: PresentationRemediationManifest,
    mode: PresentationValidationMode,
    selected_batch_id: str | None,
) -> set[str]:
    if mode == PresentationValidationMode.PHASE2_PREFLIGHT:
        assert manifest.phase2 is not None
        return {item.sha256 for item in manifest.phase2.capability_probe_artifacts}
    if mode == PresentationValidationMode.PHASE2_PARTIAL:
        return {
            item.sha256
            for record in manifest.records
            if selected_batch_id is None or record.repair_batch_id == selected_batch_id
            if isinstance(record.generation, Phase2Generation)
            for item in record.generation.candidates
        }
    return set()


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
    if validation_mode == PresentationValidationMode.SOURCE_RECLASSIFICATION:
        if selected_batch_id is not None or transient_source_files or transient_candidate_files:
            raise PresentationRemediationAuditError("Phase 1 validation rejects Phase 2 lifecycle arguments")
        return _validate_source_reclassification_manifest(
            manifest,
            inventory,
            hangboards_root=hangboards_root,
            selected_package_ids=selected_package_ids,
            final_validation=final_validation,
        )
    if final_validation:
        raise PresentationRemediationAuditError("--final-validation is only valid for Phase 1")
    if selected_package_ids:
        raise PresentationRemediationAuditError("Phase 2 validation rejects package lane selection")
    if validation_mode == PresentationValidationMode.PHASE2_FINAL and (transient_source_files or transient_candidate_files):
        raise PresentationRemediationAuditError("final Phase 2 validation rejects transient files")
    return _validate_phase2_manifest(
        manifest,
        inventory,
        hangboards_root=hangboards_root,
        validation_mode=validation_mode,
        selected_batch_id=selected_batch_id,
        transient_source_files=transient_source_files,
        transient_candidate_files=transient_candidate_files,
    )
