from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = (
    ROOT
    / "docs/source-audits/2026-08-30-independent-catalog-orientation-audit.md"
)
RECORD_HEADER = (
    "package",
    "physical revision",
    "reviewed date",
    "first-party product url",
    "reviewed first-party media",
    "supported presentations",
    "hold-to-presentation mapping",
    "source limitation",
)
URL_PATTERN = re.compile(r"https?://[^\s<>)|]+")
MEDIA_LINK_PATTERN = re.compile(r"\[([^\]]+)]\((https://[^)]+)\)")
PRESENTATION_ENTRY_PATTERN = re.compile(r"`([^`]+)`\s*=>\s*(.+)")
PRODUCT_PAGE_PATH_PATTERN = re.compile(r"/products?/", re.IGNORECASE)
DIRECT_MEDIA_PATTERN = re.compile(
    r"\.(?:pdf|jpe?g|png|webp|avif)(?:[?#]|$)", re.IGNORECASE
)


@dataclass(frozen=True)
class MediaEvidence:
    role: str
    url: str


@dataclass(frozen=True)
class OrientationAuditRecord:
    package: str
    physical_revision: str
    reviewed_date: str
    primary_urls: tuple[str, ...]
    media_evidence: tuple[MediaEvidence, ...]
    presentation_evidence: dict[str, str]
    hold_mappings: dict[str, str]
    limitation: str


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _entries(cell: str) -> tuple[str, ...]:
    return tuple(entry.strip() for entry in cell.split("<br>") if entry.strip())


def _parse_media_evidence(package: str, cell: str) -> tuple[MediaEvidence, ...]:
    if cell == "—":
        return ()
    evidence: list[MediaEvidence] = []
    for entry in _entries(cell):
        match = MEDIA_LINK_PATTERN.fullmatch(entry)
        assert match, f"{package}: malformed reviewed-media entry: {entry}"
        role, url = match.groups()
        assert role.strip(), f"{package}: reviewed-media role is empty"
        evidence.append(MediaEvidence(role=role.strip(), url=url))
    return tuple(evidence)


def _parse_presentation_entries(package: str, cell: str) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for entry in _entries(cell):
        match = PRESENTATION_ENTRY_PATTERN.fullmatch(entry)
        assert match, f"{package}: malformed presentation entry: {entry}"
        presentation_id, description = match.groups()
        assert presentation_id not in evidence, (
            f"{package}: duplicate presentation entry: {presentation_id}"
        )
        assert description.strip(), f"{package}: empty presentation evidence"
        evidence[presentation_id] = description.strip()
    return evidence


def parse_orientation_audit(path: Path) -> dict[str, OrientationAuditRecord]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next(
        index
        for index, line in enumerate(lines)
        if tuple(cell.lower() for cell in _cells(line)) == RECORD_HEADER
    )

    records: dict[str, OrientationAuditRecord] = {}
    duplicates: set[str] = set()
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = _cells(line)
        if len(cells) != len(RECORD_HEADER):
            raise AssertionError(f"malformed orientation-audit row: {line}")
        package = cells[0].strip("`")
        if package in records:
            duplicates.add(package)
        urls = tuple(URL_PATTERN.findall(cells[3]))
        records[package] = OrientationAuditRecord(
            package=package,
            physical_revision=cells[1],
            reviewed_date=cells[2],
            primary_urls=urls,
            media_evidence=_parse_media_evidence(package, cells[4]),
            presentation_evidence=_parse_presentation_entries(package, cells[5]),
            hold_mappings=_parse_presentation_entries(package, cells[6]),
            limitation=cells[7],
        )

    assert not duplicates, f"duplicate package audit rows: {sorted(duplicates)}"
    return records


def test_orientation_audit_covers_every_discovered_package() -> None:
    packages = {
        path.parent.name for path in (ROOT / "Hangboards").glob("*/board.json")
    }
    records = parse_orientation_audit(AUDIT_PATH)

    assert set(records) == packages
    for package, record in records.items():
        board = json.loads(
            (ROOT / "Hangboards" / package / "board.json").read_text(
                encoding="utf-8"
            )
        )
        declared_presentations = {
            presentation["id"] for presentation in board["presentations"]
        }

        assert record.physical_revision
        assert record.reviewed_date == "2026-08-30"
        assert record.primary_urls, f"{record.package}: no first-party source URL"
        assert all(url.startswith("https://") for url in record.primary_urls)
        assert record.media_evidence or record.limitation, (
            f"{package}: missing media evidence requires an explicit limitation"
        )
        assert len({item.url for item in record.media_evidence}) == len(
            record.media_evidence
        ), f"{package}: duplicate reviewed-media URL"
        assert all(
            item.role.lower()
            not in {"product page", "first-party supporting page"}
            for item in record.media_evidence
        ), f"{package}: reviewed media must state a specific evidence role"
        assert all(
            item.url not in record.primary_urls for item in record.media_evidence
        ), f"{package}: a product page cannot stand in for gallery media"
        assert all(
            not PRODUCT_PAGE_PATH_PATTERN.search(item.url)
            or DIRECT_MEDIA_PATTERN.search(item.url)
            for item in record.media_evidence
        ), f"{package}: a product-page URL cannot be reviewed-media evidence"
        assert set(record.presentation_evidence) == declared_presentations, (
            f"{package}: presentation evidence IDs do not match board.json"
        )
        assert set(record.hold_mappings) == declared_presentations, (
            f"{package}: hold-mapping IDs do not match board.json"
        )
