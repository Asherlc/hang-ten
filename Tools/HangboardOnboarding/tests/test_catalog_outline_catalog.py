from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.catalog_outlines import (
    CatalogOutlineDocument,
    load_catalog_source_hints,
    validate_catalog_document,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_DIR = REPO_ROOT / "docs" / "hangboard-generative-catalog"
SOURCE_DIR = Path(os.environ.get("HANGBOARD_CATALOG_SOURCE_DIR", str(DEFAULT_SOURCE_DIR)))
OUTPUT_DIR = Path(
    os.environ.get("HANGBOARD_CATALOG_OUTLINE_DIR", str(DEFAULT_SOURCE_DIR / "outlines"))
)
CONTACT_SHEET_NAMES = frozenset(
    {"contact-sheet-primary.png", "flat-illustrations-contact-sheet.png"}
)


def _catalog_sources() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in SOURCE_DIR.glob("*.png")
            if path.is_file() and path.name not in CONTACT_SHEET_NAMES
        )
    )


def _catalog_outputs() -> tuple[Path, ...]:
    return tuple(sorted(OUTPUT_DIR.glob("*.json")))


def _expected_references(stem: str) -> tuple[dict[str, object], ...]:
    payload = load_catalog_source_hints()
    entry = payload[stem]
    references = entry["references"]
    return tuple(
        {
            "title": str(reference["title"]),
            "url": str(reference["url"]),
            "hints": tuple(str(hint) for hint in reference.get("hints", ())),
        }
        for reference in references
    )


def test_catalog_outline_documents_match_catalog_sources() -> None:
    sources = _catalog_sources()
    outputs = _catalog_outputs()
    expected_stems = {path.stem for path in sources}
    actual_stems = {path.stem for path in outputs}

    assert not CONTACT_SHEET_NAMES.intersection({path.name for path in outputs})
    assert actual_stems == expected_stems
    assert expected_stems == set(load_catalog_source_hints())

    for output_path in outputs:
        source_path = SOURCE_DIR / f"{output_path.stem}.png"
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        document = CatalogOutlineDocument.from_json(payload)

        assert document.source_image == f"../{source_path.name}"
        with Image.open(source_path) as source_image:
            assert (document.canvas_width, document.canvas_height) == source_image.size
        assert document.references == _expected_references(output_path.stem)
        validate_catalog_document(document, source_path=source_path)


def test_catalog_sources_include_conservative_outline_guidance() -> None:
    hints = load_catalog_source_hints()

    assert set(hints) == {path.stem for path in _catalog_sources()}
    for stem, entry in hints.items():
        guidance = entry["outlineGuidance"]
        assert isinstance(guidance["approximateHoldCount"], int)
        assert guidance["approximateHoldCount"] > 0
        assert isinstance(guidance["minimumContours"], int)
        assert guidance["minimumContours"] > 0
        assert isinstance(guidance["layout"], str) and guidance["layout"]
        assert isinstance(guidance["symmetric"], bool)
        assert isinstance(guidance["allowsLongRails"], bool)


def test_catalog_source_discovery_excludes_flat_contact_sheet() -> None:
    assert not CONTACT_SHEET_NAMES.intersection({path.name for path in _catalog_sources()})


def test_every_catalog_output_has_plausible_internal_outline_geometry() -> None:
    outputs = _catalog_outputs()
    source_hints = load_catalog_source_hints()
    assert len(outputs) == 32

    for output_path in outputs:
        allows_long_rails = source_hints[output_path.stem]["outlineGuidance"][
            "allowsLongRails"
        ]
        document = CatalogOutlineDocument.from_json(
            json.loads(output_path.read_text(encoding="utf-8"))
        )
        assert document.outlines
        for outline in document.outlines:
            x, y, width, height = outline.bounds
            assert x > 0.005 and y > 0.005, (output_path.name, outline.id, outline.bounds)
            assert x + width < 0.995 and y + height < 0.995, (
                output_path.name,
                outline.id,
                outline.bounds,
            )
            assert width >= 0.012 and height >= 0.012, (
                output_path.name,
                outline.id,
                outline.bounds,
            )
            if not allows_long_rails:
                assert not (width > 0.88 and height < 0.18), (
                    output_path.name,
                    outline.id,
                    outline.bounds,
                )
