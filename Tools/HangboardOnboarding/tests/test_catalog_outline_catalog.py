from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.catalog_outlines import (
    CatalogOutlineDocument,
    load_catalog_source_hints,
    validate_catalog_document,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "docs" / "hangboard-generative-catalog"
OUTPUT_DIR = SOURCE_DIR / "outlines"
CONTACT_SHEET_NAME = "contact-sheet-primary.png"


def _catalog_sources() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in SOURCE_DIR.glob("*.png")
            if path.is_file() and path.name != CONTACT_SHEET_NAME
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

    assert CONTACT_SHEET_NAME not in {path.name for path in outputs}
    assert actual_stems == expected_stems
    assert expected_stems == set(load_catalog_source_hints())

    for output_path in outputs:
        source_path = SOURCE_DIR / f"{output_path.stem}.png"
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        document = CatalogOutlineDocument.from_json(payload)

        assert document.source_image == source_path.name
        with Image.open(source_path) as source_image:
            assert (document.canvas_width, document.canvas_height) == source_image.size
        assert document.references == _expected_references(output_path.stem)
        validate_catalog_document(document, source_path=source_path)
