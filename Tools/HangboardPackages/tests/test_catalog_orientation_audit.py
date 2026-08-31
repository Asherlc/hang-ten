from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest


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
ALLOWED_MEDIA_ROLES = frozenset(
    {
        "depth guide",
        "front product image",
        "grip-identification chart",
        "installation guide",
        "installation manual",
        "installed-use product image",
        "manufacturer catalog",
        "mounting guide",
        "numbered hold diagram",
        "numbered depth diagram",
        "oblique product image",
        "orientation guide",
        "pocket detail image",
        "product identity image",
        "product specification",
        "product spread image",
        "product-use guide",
        "rail detail image",
        "reverse product image",
        "safety guide",
        "side product image",
        "training guide",
    }
)
SHARED_CDN_PREFIXES_BY_PRODUCT_HOST = {
    "beastmaker.co.uk": (
        "https://cdn.shopify.com/s/files/1/0107/6442/",
    ),
    "en.captainfingerfood.rocks": (
        "https://cdn.shopify.com/s/files/1/0602/4547/5542/",
    ),
    "escapeclimbing.com": (
        "https://cdn.shopify.com/s/files/1/0051/0374/7160/",
    ),
    "frictitiousclimbing.com": (
        "https://cdn.shopify.com/s/files/1/0093/8783/5451/",
    ),
    "metoliusclimbing.com": (
        "https://cdn.shopify.com/s/files/1/0955/0030/4457/",
    ),
    "natureclimbing.com": (
        "https://cdn.shopify.com/s/files/1/0657/7736/9334/",
    ),
    "trango.com": (
        "https://cdn.shopify.com/s/files/1/0282/7557/2841/",
    ),
}
EXPLICIT_MEDIA_HOSTS_BY_PRODUCT_HOST = {
    "mammut.com": frozenset({"static.mammut.com"}),
}
ALLOWED_ATTEMPTED_SOURCE_CLASSES = frozenset(
    {"catalogs", "direct images", "guides", "manuals", "model-specific diagrams"}
)
MISSING_MEDIA_LIMITATION_PATTERN = re.compile(
    r"product=([^<]+)<br>attempted=([^<]+)<br>unavailable=(.+)"
)
PLACEHOLDER_LIMITATIONS = frozenset(
    {
        "",
        "-",
        "—",
        "n/a",
        "na",
        "none",
        "none.",
        "not applicable",
        "not applicable.",
    }
)
GENERIC_UNAVAILABLE_REASON_PATTERNS = (
    re.compile(
        r"^no (?:separately addressable )?(?:first-party )?media(?: url)? "
        r"(?:was |were )?(?:found|recorded)",
        re.IGNORECASE,
    ),
    re.compile(r"^no (?:direct|stable|usable) media\b", re.IGNORECASE),
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


def _normalized_host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


def _has_first_party_relationship(
    media_url: str, primary_urls: tuple[str, ...]
) -> bool:
    media_host = _normalized_host(media_url)
    for primary_url in primary_urls:
        primary_host = _normalized_host(primary_url)
        if (
            media_host == primary_host
            or media_host
            in EXPLICIT_MEDIA_HOSTS_BY_PRODUCT_HOST.get(primary_host, frozenset())
            or any(
                media_url.startswith(prefix)
                for prefix in SHARED_CDN_PREFIXES_BY_PRODUCT_HOST.get(
                    primary_host, ()
                )
            )
        ):
            return True
    return False


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


def _validate_record(
    record: OrientationAuditRecord, declared_presentations: set[str]
) -> None:
    package = record.package
    assert record.physical_revision
    assert record.reviewed_date == "2026-08-30"
    assert record.primary_urls, f"{record.package}: no first-party source URL"
    assert all(url.startswith("https://") for url in record.primary_urls)
    if not record.media_evidence:
        limitation_match = MISSING_MEDIA_LIMITATION_PATTERN.fullmatch(
            record.limitation
        )
        assert limitation_match, (
            f"{package}: missing media requires a structured missing-media limitation"
        )
        product, attempted, unavailable = limitation_match.groups()
        attempted_classes = {
            source_class.strip() for source_class in attempted.split(",")
        }
        assert product == record.physical_revision, (
            f"{package}: limitation product must match the physical revision"
        )
        assert attempted_classes and attempted_classes <= (
            ALLOWED_ATTEMPTED_SOURCE_CLASSES
        ), f"{package}: limitation must name allowed attempted source classes"
        assert unavailable.startswith(f"{record.physical_revision}: "), (
            f"{package}: unavailable reason must name the physical revision"
        )
        reason = unavailable.removeprefix(f"{record.physical_revision}: ").strip()
        assert reason.lower() not in PLACEHOLDER_LIMITATIONS and len(reason) >= 40, (
            f"{package}: unavailable reason must be product-specific"
        )
        assert not any(
            pattern.search(reason)
            for pattern in GENERIC_UNAVAILABLE_REASON_PATTERNS
        ), f"{package}: unavailable reason must be product-specific"
    assert len({item.url for item in record.media_evidence}) == len(
        record.media_evidence
    ), f"{package}: duplicate reviewed-media URL"
    assert all(
        item.role in ALLOWED_MEDIA_ROLES for item in record.media_evidence
    ), f"{package}: reviewed media must use an allowed evidence role"
    assert all(
        _has_first_party_relationship(item.url, record.primary_urls)
        for item in record.media_evidence
    ), f"{package}: reviewed media lacks a first-party relationship"
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


def _record(
    *,
    media: tuple[MediaEvidence, ...],
    limitation: str = "Specific limitation.",
    primary_urls: tuple[str, ...] = (
        "https://manufacturer.example/products/example",
    ),
) -> OrientationAuditRecord:
    return OrientationAuditRecord(
        package="example-board",
        physical_revision="Example revision",
        reviewed_date="2026-08-30",
        primary_urls=primary_urls,
        media_evidence=media,
        presentation_evidence={"primary": "front presentation"},
        hold_mappings={"primary": "one contact"},
        limitation=limitation,
    )


def test_orientation_audit_rejects_ambiguous_media_role() -> None:
    record = _record(
        media=(
            MediaEvidence(
                role="product image or diagram",
                url="https://manufacturer.example/media/front.jpg",
            ),
        )
    )

    with pytest.raises(AssertionError, match="allowed evidence role"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_unrelated_media_host() -> None:
    record = _record(
        media=(
            MediaEvidence(
                role="front product image",
                url="https://unrelated.example/media/front.jpg",
            ),
        )
    )

    with pytest.raises(AssertionError, match="first-party relationship"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_unrelated_shared_cdn_account() -> None:
    record = _record(
        primary_urls=("https://www.beastmaker.co.uk/products/example",),
        media=(
            MediaEvidence(
                role="front product image",
                url=(
                    "https://cdn.shopify.com/s/files/1/9999/9999/files/"
                    "unrelated.jpg"
                ),
            ),
        ),
    )

    with pytest.raises(AssertionError, match="first-party relationship"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_placeholder_missing_media_limitation() -> None:
    record = _record(media=(), limitation="None.")

    with pytest.raises(AssertionError, match="structured missing-media limitation"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_generic_missing_media_limitation() -> None:
    record = _record(
        media=(),
        limitation=(
            "No separately addressable first-party media URL was recorded; "
            "the presentation conclusion is limited to the product page."
        ),
    )

    with pytest.raises(AssertionError, match="structured missing-media limitation"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_structured_but_generic_media_limitation() -> None:
    record = _record(
        media=(),
        limitation=(
            "product=Example revision<br>attempted=direct images, manuals<br>"
            "unavailable=Example revision: no separately addressable first-party "
            "media URL was recorded after reviewing the product page"
        ),
    )

    with pytest.raises(AssertionError, match="product-specific"):
        _validate_record(record, {"primary"})


@pytest.mark.parametrize(
    ("primary_url", "media_url"),
    (
        (
            "https://stpetesites.com/products/example",
            "https://other-tenant.stpetesites.com/media/front.jpg",
        ),
        (
            "https://thehangboard.stpetesites.com/products/example",
            "https://stpetesites.com/media/front.jpg",
        ),
    ),
)
def test_orientation_audit_rejects_shared_parent_host_provenance(
    primary_url: str, media_url: str
) -> None:
    record = _record(
        primary_urls=(primary_url,),
        media=(MediaEvidence(role="front product image", url=media_url),),
    )

    with pytest.raises(AssertionError, match="first-party relationship"):
        _validate_record(record, {"primary"})


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

        _validate_record(record, declared_presentations)
