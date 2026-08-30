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


@dataclass(frozen=True)
class OrientationAuditRecord:
    package: str
    physical_revision: str
    reviewed_date: str
    primary_urls: tuple[str, ...]
    presentation_evidence: str
    limitation: str


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


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
            presentation_evidence=f"{cells[5]} {cells[6]}".strip(),
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
        assert record.presentation_evidence or record.limitation
        assert all(
            presentation_id in record.presentation_evidence
            for presentation_id in declared_presentations
        ), f"{package}: presentation evidence is incomplete"
