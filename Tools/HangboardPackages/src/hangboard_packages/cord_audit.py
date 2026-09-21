"""Fail-closed source-audit coverage for model hangboard cord decisions."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import date
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .board_catalog import (
    BoardInventory,
    BoardModelPairedLeadCord,
    BoardModelSingleCordSuspension,
    BoardModelTwoBranchSuspension,
    PresentationMediaModel,
    is_board_identifier,
)


_DECISIONS = frozenset({"represented", "excluded"})
_TOPOLOGIES = frozenset({"singleCord", "pairedLeadCord", "twoBranchCord"})
_SOURCE_FACTS = frozenset({"documentedSuspension", "noDocumentedSuspension"})
_SOURCE_TIERS = frozenset({"independent", "manufacturer", "manufacturer-instruction", "retailer"})
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_SNAPSHOT_ROOT = Path("docs/source-audits/2026-09-13-model-cord-snapshots")
_SELF_AUTHORED_LEDGER_SUFFIXES = frozenset({".json", ".md", ".markdown"})


class CordAuditError(ValueError):
    """Raised when a cord audit is malformed or disagrees with model packages."""


@dataclass(frozen=True)
class CordAuditEvidence:
    view: str
    url: str
    exact_revision_id: str
    source_tier: str
    snapshot_sha256: str
    snapshot_path: str


@dataclass(frozen=True)
class CordAuditHumanApproval:
    approved: bool
    reviewer: str
    reviewed_at: str
    notes: str


@dataclass(frozen=True)
class CordAuditRecord:
    package_id: str
    decision: str
    source_fact: str
    topology: str | None
    ruling: str
    evidence: tuple[CordAuditEvidence, ...]
    human_approval: CordAuditHumanApproval


@dataclass(frozen=True)
class CordAuditManifest:
    schema_version: int
    records: tuple[CordAuditRecord, ...]


@dataclass(frozen=True)
class CordAuditReport:
    model_package_ids: tuple[str, ...]
    decisions: Mapping[str, int]

    def to_json(self) -> dict[str, object]:
        return {
            "modelPackageIDs": list(self.model_package_ids),
            "decisions": {decision: self.decisions[decision] for decision in sorted(self.decisions)},
        }


def _mapping(value: Any, source: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CordAuditError(f"{source} must be an object")
    return value


def _closed(payload: Mapping[str, Any], required: set[str], source: str) -> None:
    unknown = set(payload) - required
    missing = required - set(payload)
    if unknown:
        raise CordAuditError(f"{source} has unknown keys: {sorted(unknown)}")
    if missing:
        raise CordAuditError(f"{source} is missing keys: {sorted(missing)}")


def _nonempty_string(value: Any, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CordAuditError(f"{source} must be a non-empty string")
    return value


def _package_id(value: Any, source: str) -> str:
    package_id = _nonempty_string(value, source)
    if not is_board_identifier(package_id):
        raise CordAuditError(f"{source} must be identifier-shaped")
    return package_id


def _sha256(value: Any, source: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CordAuditError(f"{source} must be a 64-character SHA-256 digest")
    return value.lower()


def _relative_snapshot_path(value: Any, source: str) -> str:
    path = _nonempty_string(value, source)
    candidate = Path(path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise CordAuditError(f"{source} must be a relative retained path")
    try:
        candidate.relative_to(_SNAPSHOT_ROOT)
    except ValueError as error:
        raise CordAuditError(
            f"{source} must remain beneath {_SNAPSHOT_ROOT.as_posix()}"
        ) from error
    return path


def _snapshot_base(manifest_path: Path) -> Path:
    """Use the repository root for repository manifests, or their directory for fixtures."""
    resolved_manifest = manifest_path.resolve()
    for candidate in (resolved_manifest.parent, *resolved_manifest.parent.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved_manifest.parent


def _verify_snapshot(
    evidence: CordAuditEvidence, *, manifest_path: Path, source: str
) -> None:
    base = _snapshot_base(manifest_path)
    snapshot_candidate = base / evidence.snapshot_path
    try:
        snapshot_candidate.relative_to(base)
    except ValueError as error:
        raise CordAuditError(
            f"{source}.snapshotPath must remain beneath the repository base"
        ) from error
    component = base
    parts = Path(evidence.snapshot_path).parts
    for index, part in enumerate(parts):
        component /= part
        try:
            mode = component.lstat().st_mode
        except OSError as error:
            raise CordAuditError(
                f"{source}.snapshot path does not name a regular file: "
                f"{evidence.snapshot_path}"
            ) from error
        if stat.S_ISLNK(mode):
            raise CordAuditError(
                f"{source}.snapshotPath must not contain a symbolic link: "
                f"{evidence.snapshot_path}"
            )
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise CordAuditError(
                f"{source}.snapshot path does not name a regular file: "
                f"{evidence.snapshot_path}"
            )
        if index == len(parts) - 1 and not stat.S_ISREG(mode):
            raise CordAuditError(
                f"{source}.snapshot path does not name a regular file: "
                f"{evidence.snapshot_path}"
            )
    try:
        digest = hashlib.sha256(snapshot_candidate.read_bytes()).hexdigest()
    except OSError as error:
        raise CordAuditError(
            f"{source}.snapshot could not be read: {evidence.snapshot_path}"
        ) from error
    if digest != evidence.snapshot_sha256:
        raise CordAuditError(
            f"{source}.snapshot SHA-256 does not match: {evidence.snapshot_path}"
        )


def _load_evidence(
    value: Any, source: str, *, allow_empty: bool = False
) -> tuple[CordAuditEvidence, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        expected = "array" if allow_empty else "non-empty array"
        raise CordAuditError(f"{source} must be an {expected}")
    evidence: list[CordAuditEvidence] = []
    for index, raw_evidence in enumerate(value):
        evidence_source = f"{source}[{index}]"
        payload = _mapping(raw_evidence, evidence_source)
        _closed(
            payload,
            {"view", "url", "exactRevisionID", "sourceTier", "snapshotSHA256", "snapshotPath"},
            evidence_source,
        )
        url = _nonempty_string(payload["url"], f"{evidence_source}.url")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise CordAuditError(f"{evidence_source}.url must be an HTTPS URL")
        snapshot_path = _relative_snapshot_path(
            payload["snapshotPath"], f"{evidence_source}.snapshotPath"
        )
        if Path(snapshot_path).suffix.casefold() in _SELF_AUTHORED_LEDGER_SUFFIXES:
            raise CordAuditError(
                f"{evidence_source}.snapshotPath must reference a retained source artifact, "
                "not a self-authored markdown ledger"
            )
        evidence.append(
            CordAuditEvidence(
                view=_nonempty_string(payload["view"], f"{evidence_source}.view"),
                url=url,
                exact_revision_id=_nonempty_string(
                    payload["exactRevisionID"], f"{evidence_source}.exactRevisionID"
                ),
                source_tier=_source_tier(payload["sourceTier"], f"{evidence_source}.sourceTier"),
                snapshot_sha256=_sha256(
                    payload["snapshotSHA256"], f"{evidence_source}.snapshotSHA256"
                ),
                snapshot_path=snapshot_path,
            )
        )
    return tuple(evidence)


def _source_tier(value: Any, source: str) -> str:
    tier = _nonempty_string(value, source)
    if tier not in _SOURCE_TIERS:
        raise CordAuditError(f"{source} must be one of {sorted(_SOURCE_TIERS)}")
    return tier


def _load_human_approval(value: Any, source: str) -> CordAuditHumanApproval:
    payload = _mapping(value, source)
    _closed(payload, {"approved", "reviewer", "reviewedAt", "notes"}, source)
    if payload["approved"] is not True:
        raise CordAuditError(f"{source}.approved must be true")
    reviewed_at = _nonempty_string(payload["reviewedAt"], f"{source}.reviewedAt")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_at):
        raise CordAuditError(f"{source}.reviewedAt must be an ISO date")
    try:
        date.fromisoformat(reviewed_at)
    except ValueError as error:
        raise CordAuditError(f"{source}.reviewedAt must be an ISO calendar date") from error
    return CordAuditHumanApproval(
        approved=True,
        reviewer=_nonempty_string(payload["reviewer"], f"{source}.reviewer"),
        reviewed_at=reviewed_at,
        notes=_nonempty_string(payload["notes"], f"{source}.notes"),
    )


def _load_record(value: Any, source: str) -> CordAuditRecord:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "packageID",
            "decision",
            "sourceFact",
            "topology",
            "ruling",
            "evidence",
            "humanApproval",
        },
        source,
    )
    decision = _nonempty_string(payload["decision"], f"{source}.decision")
    if decision not in _DECISIONS:
        raise CordAuditError(f"{source}.decision must be one of {sorted(_DECISIONS)}")
    source_fact = _nonempty_string(payload["sourceFact"], f"{source}.sourceFact")
    if source_fact not in _SOURCE_FACTS:
        raise CordAuditError(
            f"{source}.sourceFact must be one of {sorted(_SOURCE_FACTS)}"
        )
    topology_value = payload["topology"]
    if topology_value is not None and (
        not isinstance(topology_value, str) or topology_value not in _TOPOLOGIES
    ):
        raise CordAuditError(f"{source}.topology must be null or one of {sorted(_TOPOLOGIES)}")
    if decision == "represented" and topology_value is None:
        raise CordAuditError(f"{source}.topology is required for represented records")
    if decision == "excluded" and topology_value is not None:
        raise CordAuditError(f"{source}.topology must be null for excluded records")
    if decision == "represented" and source_fact != "documentedSuspension":
        raise CordAuditError(
            f"{source}.sourceFact must document suspended presentation for represented records"
        )
    if decision == "excluded" and source_fact != "noDocumentedSuspension":
        raise CordAuditError(
            f"{source} source fact documents suspended presentation and cannot be excluded"
        )
    evidence = _load_evidence(
        payload["evidence"],
        f"{source}.evidence",
        allow_empty=True,
    )
    if not evidence:
        raise CordAuditError(
            f"{source} requires retained source evidence for {decision} records"
        )
    return CordAuditRecord(
        package_id=_package_id(payload["packageID"], f"{source}.packageID"),
        decision=decision,
        source_fact=source_fact,
        topology=topology_value,
        ruling=_nonempty_string(payload["ruling"], f"{source}.ruling"),
        evidence=evidence,
        human_approval=_load_human_approval(payload["humanApproval"], f"{source}.humanApproval"),
    )


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CordAuditError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_cord_audit_manifest(path: Path) -> CordAuditManifest:
    """Load a closed cord-audit manifest without accepting unknown structure."""
    try:
        payload = _mapping(
            json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_json_keys),
            "cord audit manifest",
        )
    except (OSError, json.JSONDecodeError, CordAuditError) as error:
        if isinstance(error, CordAuditError):
            raise
        raise CordAuditError(f"cord audit manifest is invalid JSON: {path}") from error
    _closed(payload, {"schemaVersion", "records"}, "cord audit manifest")
    if payload["schemaVersion"] != 1 or isinstance(payload["schemaVersion"], bool):
        raise CordAuditError("cord audit manifest schemaVersion must be 1")
    if not isinstance(payload["records"], list):
        raise CordAuditError("cord audit manifest records must be an array")
    records = tuple(
        _load_record(record, f"cord audit manifest records[{index}]")
        for index, record in enumerate(payload["records"])
    )
    for record_index, record in enumerate(records):
        for evidence_index, evidence in enumerate(record.evidence):
            _verify_snapshot(
                evidence,
                manifest_path=path,
                source=f"cord audit manifest records[{record_index}].evidence[{evidence_index}]",
            )
    return CordAuditManifest(
        schema_version=1,
        records=records,
    )


def _suspension_topology(suspension: object | None) -> str | None:
    if suspension is None:
        return None
    if isinstance(suspension, BoardModelSingleCordSuspension):
        return "singleCord"
    if isinstance(suspension, BoardModelPairedLeadCord):
        return "pairedLeadCord"
    if isinstance(suspension, BoardModelTwoBranchSuspension):
        return "twoBranchCord"
    raise CordAuditError("model package has unsupported suspension topology")


def _model_package_topologies(inventory: BoardInventory) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for package in inventory.packages:
        model_media = tuple(
            presentation.media
            for presentation in package.board.presentations
            if isinstance(presentation.media, PresentationMediaModel)
        )
        if not model_media:
            continue
        if package.board.id in result:
            raise CordAuditError(f"duplicate model package ID in inventory: {package.board.id}")
        if len(model_media) != 1:
            raise CordAuditError(
                f"model package must contain exactly one model presentation: {package.board.id}"
            )
        result[package.board.id] = _suspension_topology(model_media[0].suspension)
    return result


def validate_cord_audit_manifest(
    manifest: CordAuditManifest, inventory: BoardInventory
) -> CordAuditReport:
    """Require exactly one evidence-backed cord decision for every model package."""
    topologies_by_package = _model_package_topologies(inventory)
    records_by_package: dict[str, CordAuditRecord] = {}
    for record in manifest.records:
        if record.package_id in records_by_package:
            raise CordAuditError(f"duplicate model package record: {record.package_id}")
        records_by_package[record.package_id] = record

    inventory_ids = set(topologies_by_package)
    manifest_ids = set(records_by_package)
    if manifest_ids != inventory_ids:
        details: list[str] = []
        for package_id in sorted(manifest_ids - inventory_ids):
            details.append(f"unknown model package record: {package_id}")
        for package_id in sorted(inventory_ids - manifest_ids):
            details.append(f"missing model package record: {package_id}")
        raise CordAuditError(
            "manifest model package IDs must equal inventory; " + "; ".join(details)
        )

    for package_id, record in records_by_package.items():
        package_topology = topologies_by_package[package_id]
        revision_ids = {item.exact_revision_id for item in record.evidence}
        if record.evidence and len(revision_ids) != 1:
            raise CordAuditError(
                f"evidence must agree on one exact revision ID: {package_id}"
            )
        if record.evidence:
            evidence_paths = {item.snapshot_path for item in record.evidence}
            evidence_digests = {item.snapshot_sha256 for item in record.evidence}
            if (
                len(evidence_paths) != len(record.evidence)
                or len(evidence_digests) != len(record.evidence)
            ):
                raise CordAuditError(
                    "record requires distinct retained source artifacts: "
                    f"{package_id}"
                )
        if record.decision == "represented":
            if not record.evidence:
                raise CordAuditError(
                    f"represented record requires retained source evidence: {package_id}"
                )
            evidence_views = {item.view.strip().casefold() for item in record.evidence}
            if len(evidence_views) != len(record.evidence) or len(evidence_views) < 2:
                raise CordAuditError(
                    f"represented record requires two distinct evidence views: {package_id}"
                )
            evidence_urls = {item.url for item in record.evidence}
            if len(evidence_urls) != len(record.evidence) or len(evidence_urls) < 2:
                raise CordAuditError(
                    f"represented record requires two distinct evidence URLs: {package_id}"
                )
            if record.topology != package_topology:
                raise CordAuditError(
                    f"represented record topology does not match package suspension topology: {package_id}"
                )
        elif package_topology is not None:
            raise CordAuditError(
                f"excluded record requires no package suspension: {package_id}"
            )

    decisions = {decision: 0 for decision in _DECISIONS}
    for record in records_by_package.values():
        decisions[record.decision] += 1
    return CordAuditReport(
        model_package_ids=tuple(sorted(inventory_ids)),
        decisions={decision: count for decision, count in decisions.items() if count},
    )
