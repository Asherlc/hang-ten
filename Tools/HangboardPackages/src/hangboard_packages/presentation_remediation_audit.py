"""Fail-closed parsing and validation for presentation remediation manifests."""

from __future__ import annotations

import hashlib
import json
import re
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
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
    generation: PresentationGeneration
    final: PresentationFinalState


@dataclass(frozen=True)
class PresentationRemediationManifest:
    schema_version: int
    phase: str
    review_date: date
    package_ids: tuple[str, ...]
    records: tuple[PresentationRemediationRecord, ...]
    phase1_checks: Mapping[str, Phase1Check]


@dataclass(frozen=True)
class PresentationRemediationReport:
    package_ids: tuple[str, ...]
    presentation_count: int
    decisions: Mapping[str, int]
    evidence_blocked_assets: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "packageIDs": list(self.package_ids),
            "packageCount": len(self.package_ids),
            "presentationCount": self.presentation_count,
            "decisions": {key: self.decisions[key] for key in sorted(self.decisions)},
            "evidenceBlockedAssets": list(self.evidence_blocked_assets),
        }


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
    _closed(
        payload,
        {
            "schemaVersion",
            "phase",
            "reviewDate",
            "packageIDs",
            "records",
            "phase1Checks",
        },
        "presentation remediation manifest",
    )
    if (
        isinstance(payload["schemaVersion"], bool)
        or not isinstance(payload["schemaVersion"], int)
        or payload["schemaVersion"] != 1
    ):
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.schemaVersion must be a JSON integer equal to 1"
        )
    if payload["phase"] != "sourceReclassification":
        raise PresentationRemediationAuditError(
            "presentation remediation manifest.phase must be sourceReclassification"
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
    records = tuple(
        _load_record(record, f"records[{index}]", review_date)
        for index, record in enumerate(records_value)
    )
    return PresentationRemediationManifest(
        1,
        "sourceReclassification",
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
    )


def _current_png_facts(path: Path) -> tuple[str, int, int]:
    data = path.read_bytes()
    if data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        raise PresentationRemediationAuditError(f"asset is not a PNG: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return hashlib.sha256(data).hexdigest(), width, height


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


def validate_presentation_remediation_manifest(
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
