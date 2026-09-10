"""Closed-schema validation for Stage 0 hangboard evidence packets.

Evidence packets preserve source material and source-backed logical facts.  They
are deliberately not a geometry interchange format: authored shape belongs to
the later Astra/model stages and cannot enter this contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse


SourceTier = Literal["manufacturer", "commerce"]

_PACKET_KEYS = frozenset(
    {
        "boardRevision",
        "boardRevisionDate",
        "locale",
        "primarySources",
        "commerceSources",
        "logicalInventory",
        "sourcedClaims",
        "conflictsAndRulings",
        "unknownsForAstra",
        "deliberateOmissions",
        "materialFidelity",
        "requiredReviewViews",
        "suspendedPresentation",
    }
)
_REQUIRED_PACKET_KEYS = _PACKET_KEYS - {"suspendedPresentation"}
_PROPOSAL_KEYS = frozenset(
    {"geometry", "coordinates", "contours", "masks", "vectors", "trace", "alignment"}
)
_HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_LOCALE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
_SEARCH_RESULT_HOSTS = frozenset(
    {
        "google.com",
        "bing.com",
        "duckduckgo.com",
        "search.yahoo.com",
    }
)
_NUMERIC_SHAPE_PRESCRIPTION = re.compile(
    r"(?:\b(?:radius|radii|section|profile|contour|depth|width|height)\b[^\n]{0,32}"
    r"\d+(?:\.\d+)?\s*(?:mm|cm|in)?|"
    r"\d+(?:\.\d+)?\s*(?:mm|cm|in)\s*\b(?:radius|radii|section|profile|contour|depth)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceSource:
    """A retained, hashed source snapshot referenced by an evidence packet."""

    local_path: str
    sha256: str
    source_tier: SourceTier
    url: str
    retailer: str | None = None
    snapshot_sha256: str | None = None


@dataclass(frozen=True)
class EvidencePacket:
    """Validated packet data, with JSON camel-case fields exposed as Python names."""

    board_revision: str
    board_revision_date: str
    locale: str
    primary_sources: tuple[EvidenceSource, ...]
    commerce_sources: tuple[EvidenceSource, ...]
    logical_inventory: tuple[dict[str, Any], ...]
    sourced_claims: tuple[dict[str, Any], ...]
    conflicts_and_rulings: tuple[Any, ...]
    unknowns_for_astra: tuple[str, ...]
    deliberate_omissions: tuple[str, ...]
    material_fidelity: Any
    required_review_views: tuple[str, ...]
    suspended_presentation: dict[str, Any] | None = None


def validate_evidence_packet(packet_path: Path) -> EvidencePacket:
    """Load and fail-closed validate *packet_path*.

    Every source is checked against the bytes retained beside the packet.  No
    network request is made; URLs are provenance pointers only.
    """

    path = Path(packet_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"packet is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid evidence packet JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("evidence packet must be a JSON object")

    _reject_proposal_keys(payload)
    unknown_keys = set(payload) - _PACKET_KEYS
    if unknown_keys:
        raise ValueError(f"closed packet contains unknown key: {sorted(unknown_keys)[0]}")

    for required in _REQUIRED_PACKET_KEYS:
        if required not in payload:
            raise ValueError(f"evidence packet is missing {required}")
    board_revision = _required_string(payload, "boardRevision")
    board_revision_date = _required_string(payload, "boardRevisionDate")
    try:
        date.fromisoformat(board_revision_date)
    except ValueError as exc:
        raise ValueError("boardRevisionDate must be an ISO-8601 date") from exc
    locale = _required_string(payload, "locale")
    if not _LOCALE.fullmatch(locale):
        raise ValueError("locale must be a BCP-47-style language or language-region tag")

    primary = _sources(payload["primarySources"], path.parent, "manufacturer")
    if not primary:
        raise ValueError("primarySources must contain at least one manufacturer source")
    commerce = _sources(payload["commerceSources"], path.parent, "commerce")
    source_paths = [source.local_path for source in (*primary, *commerce)]
    if len(source_paths) != len(set(source_paths)):
        raise ValueError("duplicate retained localPath across evidence sources")
    source_tiers = {
        source.local_path: source.source_tier for source in (*primary, *commerce)
    }
    _validate_inventory(payload["logicalInventory"], set(source_tiers))
    claims = _dict_list(payload["sourcedClaims"], "sourcedClaims")
    conflicts = _list(payload["conflictsAndRulings"], "conflictsAndRulings")
    unknowns = _strings(payload["unknownsForAstra"], "unknownsForAstra")
    _reject_numeric_shape_prescriptions(unknowns, "unknownsForAstra")
    omissions = _strings(payload["deliberateOmissions"], "deliberateOmissions")
    omission_set = {item.casefold() for item in omissions}
    if "screw holes" not in omission_set or "mounting hardware" not in omission_set:
        raise ValueError("deliberateOmissions must contain screw holes and mounting hardware")
    review_views = _strings(payload["requiredReviewViews"], "requiredReviewViews")
    required_views = {"front", "three-quarter", "clay-detail"}
    if not required_views.issubset(review_views):
        raise ValueError("requiredReviewViews must contain front, three-quarter, and clay-detail")
    if not isinstance(payload["materialFidelity"], (dict, str)):
        raise ValueError("materialFidelity must be an object or string")

    _validate_claim_references(claims, source_tiers)
    _validate_cross_tier_claims(claims, source_tiers, conflicts)

    suspended = payload.get("suspendedPresentation")
    if suspended is not None:
        _validate_suspended_presentation(suspended, source_tiers, payload["logicalInventory"])

    return EvidencePacket(
        board_revision=board_revision,
        board_revision_date=board_revision_date,
        locale=locale,
        primary_sources=tuple(primary),
        commerce_sources=tuple(commerce),
        logical_inventory=tuple(payload["logicalInventory"]),
        sourced_claims=tuple(claims),
        conflicts_and_rulings=tuple(conflicts),
        unknowns_for_astra=tuple(unknowns),
        deliberate_omissions=tuple(omissions),
        material_fidelity=payload["materialFidelity"],
        required_review_views=tuple(review_views),
        suspended_presentation=suspended,
    )


def _validate_suspended_presentation(
    value: Any, source_tiers: dict[str, SourceTier], inventory: list[dict[str, Any]]
) -> None:
    if not isinstance(value, dict):
        raise ValueError("suspendedPresentation must be an object")
    allowed = {"positionIDs", "positionMappings", "attachmentEvidence", "visualApproval", "displayEstimates"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"suspendedPresentation contains unknown key: {sorted(unknown)[0]}")
    for key in allowed:
        if key not in value:
            raise ValueError(f"suspendedPresentation is missing {key}")

    position_ids = _strings(value["positionIDs"], "suspendedPresentation.positionIDs")
    if len(position_ids) != len(set(position_ids)):
        raise ValueError("suspendedPresentation.positionIDs contains duplicate position")
    mappings = _dict_list(value["positionMappings"], "suspendedPresentation.positionMappings")
    if not mappings:
        raise ValueError("suspendedPresentation.positionMappings must be non-empty")
    inventory_ids = {item.get("id") for item in inventory}
    seen: set[str] = set()
    for mapping in mappings:
        if set(mapping) - {"positionID", "holdIDs", "sourceLocalPath"}:
            raise ValueError("position mapping contains unknown key")
        position = mapping.get("positionID")
        if not isinstance(position, str) or position not in position_ids:
            raise ValueError(f"unknown position ID in suspendedPresentation: {position}")
        if position in seen:
            raise ValueError(f"duplicate position mapping: {position}")
        seen.add(position)
        holds = _strings(mapping.get("holdIDs"), "position mapping holdIDs")
        if not holds:
            raise ValueError("position mapping holdIDs must be non-empty")
        if any(hold not in inventory_ids for hold in holds):
            raise ValueError("position mapping references unknown hold ID")
        _require_retained_reference(mapping.get("sourceLocalPath"), source_tiers, "position mapping")
    if seen != set(position_ids):
        raise ValueError("positionMappings must provide a mapping for every declared position")

    attachment = value["attachmentEvidence"]
    if not isinstance(attachment, dict):
        raise ValueError("attachmentEvidence must be an object")
    if set(attachment) - {"sourceLocalPath", "view", "supports"}:
        raise ValueError("attachmentEvidence contains unknown key")
    _require_retained_reference(attachment.get("sourceLocalPath"), source_tiers, "attachmentEvidence")
    for key in ("view", "supports"):
        _required_string(attachment, key)

    approval = value["visualApproval"]
    if not isinstance(approval, dict):
        raise ValueError("visualApproval must be an object")
    if set(approval) - {"approvedSnapshotPaths", "materiallyDistinct", "decisionDate"}:
        raise ValueError("visualApproval contains unknown key")
    snapshots = _strings(approval.get("approvedSnapshotPaths"), "visualApproval.approvedSnapshotPaths")
    if len(snapshots) < 2 or len(snapshots) != len(set(snapshots)) or not approval.get("materiallyDistinct"):
        raise ValueError("visualApproval requires two or more materially distinct snapshots")
    for snapshot in snapshots:
        _require_retained_reference(snapshot, source_tiers, "visualApproval snapshot")
    decision_date = approval.get("decisionDate")
    if not isinstance(decision_date, str) or not decision_date.strip():
        raise ValueError("visualApproval requires decisionDate")
    try:
        date.fromisoformat(decision_date)
    except ValueError as exc:
        raise ValueError("visualApproval decisionDate must be an ISO-8601 date") from exc

    estimates = _dict_list(value["displayEstimates"], "suspendedPresentation.displayEstimates")
    if not estimates:
        raise ValueError("displayEstimates must be non-empty")
    for estimate in estimates:
        if set(estimate) - {"name", "value", "provenance"}:
            raise ValueError("display estimate contains unknown key")
        _required_string(estimate, "name")
        _required_string(estimate, "value")
        provenance = estimate.get("provenance")
        if provenance not in {"displayEstimate", "estimatedFromApprovedModel"}:
            raise ValueError("display estimate provenance must be displayEstimate or estimatedFromApprovedModel")


def _require_retained_reference(reference: Any, source_tiers: dict[str, SourceTier], field: str) -> None:
    if not isinstance(reference, str) or not reference.strip() or reference not in source_tiers:
        raise ValueError(f"{field} sourceLocalPath must reference a retained source")


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def _strings(value: Any, field: str) -> list[str]:
    values = _list(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{field} must contain non-empty strings")
    return values


def _dict_list(value: Any, field: str) -> list[dict[str, Any]]:
    values = _list(value, field)
    if any(not isinstance(item, dict) for item in values):
        raise ValueError(f"{field} must contain objects")
    return values


def _validate_inventory(value: Any, source_paths: set[str]) -> None:
    inventory = _dict_list(value, "logicalInventory")
    if not inventory:
        raise ValueError("logicalInventory must contain at least one logical contact")
    for item in inventory:
        if not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError("logicalInventory entries require a non-empty id")
        source_path = item.get("sourceLocalPath")
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError("logicalInventory entries require sourceLocalPath")
        if source_path not in source_paths:
            raise ValueError(f"logicalInventory sourceLocalPath is not retained: {source_path}")


def _sources(value: Any, packet_dir: Path, expected_tier: SourceTier) -> list[EvidenceSource]:
    objects = _dict_list(value, "primarySources" if expected_tier == "manufacturer" else "commerceSources")
    sources: list[EvidenceSource] = []
    for raw in objects:
        allowed = {"localPath", "sha256", "sourceTier", "url"}
        if expected_tier == "commerce":
            allowed |= {"retailer", "snapshotSHA256"}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"source contains unknown key: {sorted(unknown)[0]}")
        local_path = raw.get("localPath")
        if not isinstance(local_path, str) or not local_path or Path(local_path).is_absolute():
            raise ValueError("source localPath must be a relative retained path")
        if any(part == ".." for part in Path(local_path).parts):
            raise ValueError("source localPath must stay beneath the packet directory")
        source_path = packet_dir / local_path
        _validate_retained_path(source_path, packet_dir)
        digest = raw.get("sha256")
        _validate_sha256(digest, "sha256")
        actual_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest.casefold() != actual_digest:
            raise ValueError(f"source SHA-256 does not match retained bytes: {local_path}")
        source_tier = raw.get("sourceTier")
        if source_tier != expected_tier:
            if expected_tier == "manufacturer":
                raise ValueError("primarySources may contain only manufacturer sources")
            raise ValueError("commerceSources may contain only commerce sources")
        url = raw.get("url")
        parsed_url = urlparse(url) if isinstance(url, str) else None
        if not isinstance(url, str) or parsed_url is None or parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("source url must be HTTPS")
        if expected_tier == "manufacturer" and _is_search_result_url(parsed_url):
            raise ValueError("manufacturer source URL must not be a search result")
        retailer: str | None = None
        snapshot_sha256: str | None = None
        if expected_tier == "commerce":
            retailer = raw.get("retailer")
            if not isinstance(retailer, str) or not retailer.strip():
                raise ValueError("commerce source requires retailer identity")
            snapshot_sha256 = raw.get("snapshotSHA256")
            _validate_sha256(snapshot_sha256, "snapshotSHA256")
            if snapshot_sha256.casefold() != actual_digest:
                raise ValueError(f"commerce snapshotSHA256 does not match retained bytes: {local_path}")
        sources.append(
            EvidenceSource(
                local_path=local_path,
                sha256=digest,
                source_tier=source_tier,
                url=url,
                retailer=retailer,
                snapshot_sha256=snapshot_sha256,
            )
        )
    return sources


def _is_search_result_url(parsed_url: Any) -> bool:
    host = parsed_url.hostname.casefold() if parsed_url.hostname else ""
    return (
        host in _SEARCH_RESULT_HOSTS
        or any(host.endswith(f".{search_host}") for search_host in _SEARCH_RESULT_HOSTS)
    )


def _validate_sha256(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _HEX_SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a 64-character SHA-256 digest")


def _validate_retained_path(source_path: Path, packet_dir: Path) -> None:
    packet_root = packet_dir.resolve()
    try:
        relative = source_path.relative_to(packet_dir)
    except ValueError as exc:
        raise ValueError("source localPath must stay beneath the packet directory") from exc
    current = packet_dir
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"retained source must not be a symlink: {relative}")
    try:
        source_path.resolve().relative_to(packet_root)
    except ValueError as exc:
        raise ValueError("retained source resolves outside the packet directory") from exc
    if not source_path.is_file() or source_path.is_symlink():
        raise ValueError(f"retained source must be an existing regular file: {relative}")


def _validate_claim_references(
    claims: list[dict[str, Any]], source_tiers: dict[str, SourceTier]
) -> None:
    for claim in claims:
        claim_id = claim.get("claimID")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("sourcedClaims entries require claimID")
        reference = claim.get("sourceLocalPath")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(f"sourcedClaims entry {claim_id} requires sourceLocalPath")
        if reference not in source_tiers:
            raise ValueError(f"sourcedClaim references an unknown source: {reference}")


def _validate_cross_tier_claims(
    claims: list[dict[str, Any]],
    source_tiers: dict[str, SourceTier],
    conflicts: list[Any],
) -> None:
    claim_tiers: dict[str, set[SourceTier]] = {}
    for claim in claims:
        claim_id = claim["claimID"]
        claim_tiers.setdefault(claim_id, set()).add(source_tiers[claim["sourceLocalPath"]])
    ruled_claims = {
        item.get("claimID")
        for item in conflicts
        if isinstance(item, dict)
        and isinstance(item.get("claimID"), str)
        and isinstance(item.get("ruling"), str)
        and bool(item["ruling"].strip())
    }
    for claim_id, tiers in claim_tiers.items():
        if {"manufacturer", "commerce"}.issubset(tiers) and claim_id not in ruled_claims:
            raise ValueError(
                f"claim {claim_id} is supported by manufacturer and commerce sources without a ruling"
            )


def _reject_proposal_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _PROPOSAL_KEYS:
                raise ValueError(f"proposal field is not allowed in evidence packet: {key}")
            _reject_proposal_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_proposal_keys(child)


def _reject_numeric_shape_prescriptions(unknowns: list[str], field: str) -> None:
    for value in unknowns:
        if _NUMERIC_SHAPE_PRESCRIPTION.search(value) or re.search(r"\[\s*[-+]?\d", value):
            raise ValueError(f"{field} contains a numeric shape prescription")
