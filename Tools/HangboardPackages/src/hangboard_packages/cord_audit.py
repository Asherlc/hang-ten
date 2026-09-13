"""Fail-closed source-audit coverage for model hangboard cord decisions."""

from __future__ import annotations

import json
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


class CordAuditError(ValueError):
    """Raised when a cord audit is malformed or disagrees with model packages."""


@dataclass(frozen=True)
class CordAuditEvidence:
    view: str
    url: str


@dataclass(frozen=True)
class CordAuditRecord:
    package_id: str
    decision: str
    topology: str | None
    ruling: str
    evidence: tuple[CordAuditEvidence, ...]


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


def _load_evidence(value: Any, source: str) -> tuple[CordAuditEvidence, ...]:
    if not isinstance(value, list) or not value:
        raise CordAuditError(f"{source} must be a non-empty array")
    evidence: list[CordAuditEvidence] = []
    for index, raw_evidence in enumerate(value):
        evidence_source = f"{source}[{index}]"
        payload = _mapping(raw_evidence, evidence_source)
        _closed(payload, {"view", "url"}, evidence_source)
        url = _nonempty_string(payload["url"], f"{evidence_source}.url")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise CordAuditError(f"{evidence_source}.url must be an HTTPS URL")
        evidence.append(
            CordAuditEvidence(
                view=_nonempty_string(payload["view"], f"{evidence_source}.view"),
                url=url,
            )
        )
    return tuple(evidence)


def _load_record(value: Any, source: str) -> CordAuditRecord:
    payload = _mapping(value, source)
    _closed(payload, {"packageID", "decision", "topology", "ruling", "evidence"}, source)
    decision = _nonempty_string(payload["decision"], f"{source}.decision")
    if decision not in _DECISIONS:
        raise CordAuditError(f"{source}.decision must be one of {sorted(_DECISIONS)}")
    topology_value = payload["topology"]
    if topology_value is not None and (
        not isinstance(topology_value, str) or topology_value not in _TOPOLOGIES
    ):
        raise CordAuditError(f"{source}.topology must be null or one of {sorted(_TOPOLOGIES)}")
    if decision == "represented" and topology_value is None:
        raise CordAuditError(f"{source}.topology is required for represented records")
    if decision == "excluded" and topology_value is not None:
        raise CordAuditError(f"{source}.topology must be null for excluded records")
    return CordAuditRecord(
        package_id=_package_id(payload["packageID"], f"{source}.packageID"),
        decision=decision,
        topology=topology_value,
        ruling=_nonempty_string(payload["ruling"], f"{source}.ruling"),
        evidence=_load_evidence(payload["evidence"], f"{source}.evidence"),
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
    return CordAuditManifest(
        schema_version=1,
        records=tuple(
            _load_record(record, f"cord audit manifest records[{index}]")
            for index, record in enumerate(payload["records"])
        ),
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
        if record.decision == "represented":
            if len({item.view for item in record.evidence}) < 2:
                raise CordAuditError(
                    f"represented record requires two distinct evidence views: {package_id}"
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
