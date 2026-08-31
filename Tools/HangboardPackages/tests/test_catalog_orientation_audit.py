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
        "right-half product detail image",
        "safety guide",
        "side product image",
        "top-and-bottom product profile image",
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
    "soillholds.com": (
        "https://cdn.shopify.com/s/files/1/0424/1145/",
    ),
    "thehangboard.com": (
        "https://cdn.shopify.com/s/files/1/0764/5210/2426/",
    ),
    "yyvertical.com": (
        "https://cdn.shopify.com/s/files/1/0285/5010/3128/",
    ),
}
EXPLICIT_MEDIA_URLS_BY_PRIMARY_URL = {
    "https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105": frozenset(
        {
            "https://oberalp.imgix.net/ef857c73-13f1-4205-ac47-706cd101e1bb.jpg?auto=format&cs=srgb&fit=clip&type=still&w=628",
            "https://oberalp.imgix.net/f8a564c9-b501-445f-bd43-af630730abfd.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628",
            "https://oberalp.imgix.net/e3b05632-02ce-467f-9226-d2a2862c482a.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628",
            "https://oberalp.imgix.net/88ad8128-f05a-45e1-8060-6a5dc3c74052.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628",
        }
    ),
    "https://www.mammut.com/int/en/products/2060-00020/diamond-finger-hangboard": frozenset(
        {
            "https://static.mammut.com/file/2060-00020_man_en_070420_DiamondFingerHangboard_Manual.pdf",
        }
    ),
    "https://www.yyvertical.com/en/products/baguette-evo": frozenset(
        {"https://youtu.be/M4zTMJRORYg"}
    ),
    "https://www.yyvertical.com/en/products/penta-evo": frozenset(
        {"https://youtu.be/GIAO1XCpUQE"}
    ),
}
NO_MEDIA_REVIEW_PREFIX = "no-media-review="
NO_MEDIA_ATTEMPT_SCHEMAS = {
    "rendered_gallery": frozenset(
        {
            "source_url",
            "rendered_items",
            "separately_addressable_urls",
            "observation",
        }
    ),
    "html_media": frozenset(
        {"source_url", "candidate_urls", "observation"}
    ),
    "documents": frozenset(
        {"source_url", "candidate_urls", "observation"}
    ),
    "structured_data": frozenset(
        {"source_url", "status", "reason", "candidate_urls", "observation"}
    ),
}
STRUCTURED_DATA_REASONS_BY_STATUS = {
    "absent": frozenset({"no-media-properties", "no-product-record"}),
    "available": frozenset({"media-candidates-present"}),
    "http-error": frozenset({"http-404", "http-410", "request-timeout"}),
    "not-applicable": frozenset({"no-structured-data-source"}),
}
GENERIC_NO_MEDIA_TEXT_PATTERNS = (
    re.compile(r"^no media (?:was |were )?(?:found|available)\b", re.IGNORECASE),
    re.compile(r"^nothing (?:was )?(?:found|available)\b", re.IGNORECASE),
    re.compile(r"^all (?:available )?sources (?:were )?checked\b", re.IGNORECASE),
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
            or media_url
            in EXPLICIT_MEDIA_URLS_BY_PRIMARY_URL.get(primary_url, frozenset())
            or any(
                media_url.startswith(prefix)
                for prefix in SHARED_CDN_PREFIXES_BY_PRODUCT_HOST.get(
                    primary_host, ()
                )
            )
        ):
            return True
    return False


def _parse_no_media_review(package: str, limitation: str) -> dict[str, object]:
    missing_review_message = (
        f"{package}: structured missing-media limitation requires a "
        "reproducible no-media review with product-specific results"
    )
    assert limitation.startswith(NO_MEDIA_REVIEW_PREFIX), missing_review_message
    try:
        review = json.loads(limitation.removeprefix(NO_MEDIA_REVIEW_PREFIX))
    except json.JSONDecodeError as error:
        raise AssertionError(missing_review_message) from error
    assert isinstance(review, dict), missing_review_message
    assert set(review) == {
        "reviewed_date",
        "inspected_pages",
        "attempts",
        "result",
    }, f"{package}: no-media review has an invalid top-level schema"
    return review


def _validate_no_media_review(
    record: OrientationAuditRecord,
) -> None:
    package = record.package
    review = _parse_no_media_review(package, record.limitation)

    assert review["reviewed_date"] == record.reviewed_date, (
        f"{package}: no-media review date must match the record review date"
    )
    inspected_pages = review["inspected_pages"]
    assert isinstance(inspected_pages, list) and inspected_pages, (
        f"{package}: no-media review must name exact inspected pages"
    )
    assert all(isinstance(url, str) and url.startswith("https://") for url in inspected_pages), (
        f"{package}: inspected pages must be exact HTTPS URLs"
    )
    assert tuple(inspected_pages) == record.primary_urls, (
        f"{package}: inspected pages must exactly match primary source URLs"
    )

    attempts = review["attempts"]
    assert isinstance(attempts, dict), (
        f"{package}: no-media attempts must be a structured object"
    )
    assert set(attempts) == set(NO_MEDIA_ATTEMPT_SCHEMAS), (
        f"{package}: no-media review must record every required extraction attempt"
    )

    observations: list[str] = []
    for method, expected_keys in NO_MEDIA_ATTEMPT_SCHEMAS.items():
        method_attempts = attempts[method]
        assert isinstance(method_attempts, list) and method_attempts, (
            f"{package}: {method} must contain at least one attempted source"
        )
        source_urls: set[str] = set()
        for attempt in method_attempts:
            assert isinstance(attempt, dict), (
                f"{package}: {method} attempt must be a structured object"
            )
            assert "source_url" in attempt, (
                f"{package}: {method} attempt must include source_url"
            )
            assert set(attempt) == expected_keys, (
                f"{package}: {method} attempt has an invalid schema"
            )
            source_url = attempt["source_url"]
            assert isinstance(source_url, str) and source_url.startswith("https://"), (
                f"{package}: attempted source URLs must be exact HTTPS URLs"
            )
            assert _has_first_party_relationship(source_url, record.primary_urls), (
                f"{package}: attempted source URL lacks a first-party relationship"
            )
            source_urls.add(source_url)

            observation = attempt["observation"]
            assert isinstance(observation, str) and len(observation.strip()) >= 60, (
                f"{package}: attempt observation must be specific and reproducible"
            )
            assert not any(
                pattern.search(observation.strip())
                for pattern in GENERIC_NO_MEDIA_TEXT_PATTERNS
            ), f"{package}: no-media review contains generic boilerplate"
            assert record.physical_revision.casefold() in observation.casefold(), (
                f"{package}: attempt observation must name the physical revision"
            )
            observations.append(observation.strip())

            candidate_key = (
                "separately_addressable_urls"
                if method == "rendered_gallery"
                else "candidate_urls"
            )
            candidate_urls = attempt[candidate_key]
            assert isinstance(candidate_urls, list), (
                f"{package}: {method} candidate URLs must be a list"
            )
            if method == "structured_data":
                status = attempt["status"]
                reason = attempt["reason"]
                assert (
                    isinstance(status, str)
                    and isinstance(reason, str)
                    and reason
                    in STRUCTURED_DATA_REASONS_BY_STATUS.get(status, frozenset())
                ), f"{package}: structured-data status/reason is invalid"
                assert bool(candidate_urls) == (status == "available"), (
                    f"{package}: structured-data status/candidates are contradictory"
                )
            assert not candidate_urls, (
                f"{package}: cannot claim no media when an attempt records "
                "a candidate URL"
            )
            if method == "rendered_gallery":
                rendered_items = attempt["rendered_items"]
                assert (
                    isinstance(rendered_items, int)
                    and not isinstance(rendered_items, bool)
                    and rendered_items >= 0
                ), f"{package}: rendered_items must be a non-negative integer"

        if method != "structured_data":
            assert set(inspected_pages) <= source_urls, (
                f"{package}: {method} must attempt every inspected page URL"
            )

    assert len(set(observations)) == len(observations), (
        f"{package}: no-media review contains generic boilerplate"
    )

    result = review["result"]
    assert isinstance(result, dict) and set(result) == {
        "code",
        "physical_revision",
        "reason",
    }, f"{package}: no-media result has an invalid schema"
    assert result["code"] == "no-separately-addressable-first-party-media", (
        f"{package}: no-media result code is invalid"
    )
    assert result["physical_revision"] == record.physical_revision, (
        f"{package}: no-media result must name the exact physical revision"
    )
    reason = result["reason"]
    assert isinstance(reason, str) and len(reason.strip()) >= 80, (
        f"{package}: no-media result must give a specific reproducible reason"
    )
    assert not any(
        pattern.search(reason.strip())
        for pattern in GENERIC_NO_MEDIA_TEXT_PATTERNS
    ), f"{package}: no-media review contains generic boilerplate"
    assert record.physical_revision.casefold() in reason.casefold(), (
        f"{package}: no-media result must name the physical revision"
    )


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
        _validate_no_media_review(record)
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


def _strict_no_media_limitation(
    *,
    html_candidates: list[str] | None = None,
    include_html_source_url: bool = True,
    generic_observations: bool = False,
    include_structured_reason: bool = True,
    structured_status: str = "absent",
    structured_reason: str = "no-product-record",
    structured_candidates: list[str] | None = None,
    structured_observation: str | None = None,
    result_reason: str | None = None,
) -> str:
    html_attempt: dict[str, object] = {
        "candidate_urls": html_candidates or [],
        "observation": (
            "The Example revision product-content image and source attributes "
            "contained zero revision-specific asset URLs after site-chrome assets "
            "were excluded."
        ),
    }
    if include_html_source_url:
        html_attempt["source_url"] = (
            "https://manufacturer.example/products/example"
        )
    review = {
        "reviewed_date": "2026-08-30",
        "inspected_pages": [
            "https://manufacturer.example/products/example",
        ],
        "attempts": {
            "rendered_gallery": [
                {
                    "source_url": "https://manufacturer.example/products/example",
                    "rendered_items": 0,
                    "separately_addressable_urls": [],
                    "observation": (
                        "The rendered product region contained no gallery item or "
                        "media control for the Example revision."
                    ),
                }
            ],
            "html_media": [html_attempt],
            "documents": [
                {
                    "source_url": "https://manufacturer.example/products/example",
                    "candidate_urls": [],
                    "observation": (
                        "The Example revision product-content links contained zero "
                        "PDF, manual, installation-guide, or model-guide URLs."
                    ),
                }
            ],
            "structured_data": [
                {
                    "source_url": "https://manufacturer.example/products/example.js",
                    "status": structured_status,
                    "candidate_urls": structured_candidates or [],
                    "observation": structured_observation
                    or (
                        "The exact product JSON endpoint returned no structured "
                        "product record for the Example revision."
                    ),
                }
            ],
        },
        "result": {
            "code": "no-separately-addressable-first-party-media",
            "physical_revision": "Example revision",
            "reason": result_reason
            or (
                "The Example revision product record exposes only revision prose; "
                "the four recorded extraction paths expose no product asset or "
                "document."
            ),
        },
    }
    if include_structured_reason:
        review["attempts"]["structured_data"][0]["reason"] = structured_reason
    if generic_observations:
        for attempts in review["attempts"].values():
            for attempt in attempts:
                attempt["observation"] = (
                    "No media was found after checking this exact source page "
                    "and each available source category carefully."
                )
        review["result"]["reason"] = (
            "No media was found after checking this exact source page and each "
            "available source category carefully."
        )
    return "no-media-review=" + json.dumps(review, separators=(",", ":"))


def test_orientation_audit_accepts_reproducible_missing_media_review() -> None:
    record = _record(media=(), limitation=_strict_no_media_limitation())

    _validate_record(record, {"primary"})


def test_orientation_audit_rejects_false_no_media_claim() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            html_candidates=[
                "https://manufacturer.example/media/front.jpg",
            ]
        ),
    )

    with pytest.raises(AssertionError, match="cannot claim no media"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_missing_attempted_source_url() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            include_html_source_url=False,
        ),
    )

    with pytest.raises(AssertionError, match="attempt must include source_url"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_revision_prefixed_boilerplate() -> None:
    record = _record(
        media=(),
        limitation=(
            "product=Example revision<br>attempted=direct images, manuals<br>"
            "unavailable=Example revision: the official product page did not "
            "yield usable model assets after reviewing every source category"
        ),
    )

    with pytest.raises(AssertionError, match="reproducible no-media review"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_structured_generic_boilerplate() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(generic_observations=True),
    )

    with pytest.raises(AssertionError, match="generic boilerplate"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_missing_structured_data_reason() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            include_structured_reason=False,
        ),
    )

    with pytest.raises(AssertionError, match="invalid schema"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_unallowable_structured_status_reason() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            structured_status="absent",
            structured_reason="request-failed",
        ),
    )

    with pytest.raises(AssertionError, match="status/reason"):
        _validate_record(record, {"primary"})


@pytest.mark.parametrize(
    ("status", "reason", "candidate_urls"),
    (
        ("available", "media-candidates-present", []),
        (
            "absent",
            "no-product-record",
            ["https://manufacturer.example/media/front.jpg"],
        ),
    ),
)
def test_orientation_audit_rejects_contradictory_structured_status_candidates(
    status: str, reason: str, candidate_urls: list[str]
) -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            structured_status=status,
            structured_reason=reason,
            structured_candidates=candidate_urls,
        ),
    )

    with pytest.raises(AssertionError, match="status/candidates are contradictory"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_generic_structured_observation() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            structured_observation=(
                "The structured-data inspection completed successfully and no usable "
                "media candidates were returned by the checked source."
            ),
        ),
    )

    with pytest.raises(AssertionError, match="must name the physical revision"):
        _validate_record(record, {"primary"})


def test_orientation_audit_rejects_generic_no_media_result() -> None:
    record = _record(
        media=(),
        limitation=_strict_no_media_limitation(
            result_reason=(
                "The required source checks completed successfully and returned no "
                "separately addressable product media or documents for this record."
            ),
        ),
    )

    with pytest.raises(AssertionError, match="must name the physical revision"):
        _validate_record(record, {"primary"})


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


def test_orientation_audit_accepts_exact_manufacturer_linked_video() -> None:
    record = _record(
        primary_urls=("https://www.yyvertical.com/en/products/baguette-evo",),
        media=(
            MediaEvidence(
                role="product-use guide",
                url="https://youtu.be/M4zTMJRORYg",
            ),
        ),
    )

    _validate_record(record, {"primary"})


def test_orientation_audit_rejects_unrecorded_video_on_linked_host() -> None:
    record = _record(
        primary_urls=("https://www.yyvertical.com/en/products/baguette-evo",),
        media=(
            MediaEvidence(
                role="product-use guide",
                url="https://youtu.be/arbitrary-video-id",
            ),
        ),
    )

    with pytest.raises(AssertionError, match="first-party relationship"):
        _validate_record(record, {"primary"})


@pytest.mark.parametrize(
    ("primary_url", "media_url"),
    (
        (
            "https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105",
            "https://oberalp.imgix.net/arbitrary-product.jpg",
        ),
        (
            "https://www.mammut.com/int/en/products/2060-00020/diamond-finger-hangboard",
            "https://static.mammut.com/file/arbitrary-manual.pdf",
        ),
    ),
)
def test_orientation_audit_rejects_unrecorded_media_on_hosted_media_domain(
    primary_url: str, media_url: str
) -> None:
    record = _record(
        primary_urls=(primary_url,),
        media=(MediaEvidence(role="product specification", url=media_url),),
    )

    with pytest.raises(AssertionError, match="first-party relationship"):
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


def test_orientation_audit_records_the_hangboard_structured_gallery() -> None:
    record = parse_orientation_audit(AUDIT_PATH)["the-hangboard"]

    assert record.primary_urls == (
        "https://thehangboard.com/products/hangboard",
        "https://thehangboard.com/products/hangboard.js",
    )
    gallery_prefix = "https://cdn.shopify.com/s/files/1/0764/5210/2426/files/"
    assert tuple(
        item for item in record.media_evidence if item.url.startswith(gallery_prefix)
    ) == (
        MediaEvidence(
            role="front product image",
            url=(
                gallery_prefix
                + "hangboard-straight-2_ddf25e96-22ac-422d-9a62-7db961398ca4.png"
                "?v=1747623739"
            ),
        ),
        MediaEvidence(
            role="reverse product image",
            url=gallery_prefix + "hangboard-back-2.png?v=1747623739",
        ),
        MediaEvidence(
            role="right-half product detail image",
            url=gallery_prefix + "half-right-hangboard.png?v=1747623739",
        ),
        MediaEvidence(
            role="side product image",
            url=gallery_prefix + "hangboard-side-2-right.png?v=1747623739",
        ),
        MediaEvidence(
            role="side product image",
            url=gallery_prefix + "hangboard-side-2.png?v=1747623739",
        ),
        MediaEvidence(
            role="top-and-bottom product profile image",
            url=gallery_prefix + "hangboard-top-bottom-2.png?v=1747623739",
        ),
        MediaEvidence(
            role="oblique product image",
            url=gallery_prefix + "IMG_0761-Photoroom-Photoroom.png?v=1747623739",
        ),
        MediaEvidence(
            role="oblique product image",
            url=gallery_prefix + "IMG_0762-Photoroom-Photoroom.png?v=1747623739",
        ),
    )
