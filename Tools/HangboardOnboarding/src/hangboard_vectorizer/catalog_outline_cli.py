from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import io
import json
import os
from pathlib import Path
from typing import Any
from contextlib import redirect_stderr, redirect_stdout

from hangboard_vectorizer.catalog_outlines import (
    CatalogOutlineDocument,
    render_catalog_review_overlay,
    validate_catalog_document,
    vectorize_catalog_image,
    write_catalog_document,
)


@dataclass(slots=True)
class CliResult:
    exit_code: int
    output: str
    exception: BaseException | None = None


class CliRunner:
    def invoke(self, command: Any, args: list[str]) -> CliResult:
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                outcome = command(args)
        except SystemExit as error:
            code = error.code if isinstance(error.code, int) else 1
            return CliResult(exit_code=code, output=stdout.getvalue() + stderr.getvalue(), exception=error)
        except BaseException as error:  # pragma: no cover - mirrors click testing shape
            return CliResult(exit_code=1, output=stdout.getvalue() + stderr.getvalue(), exception=error)
        exit_code = int(outcome) if isinstance(outcome, int) else 0
        return CliResult(exit_code=exit_code, output=stdout.getvalue() + stderr.getvalue())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hangboard-catalog-outlines")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    sources = _discover_sources(args.source_dir, args.limit)
    if args.check:
        return _check_outputs(sources, args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.review_dir is not None:
        args.review_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        document = vectorize_catalog_image(source)
        output_path = args.output_dir / f"{source.stem}.json"
        document = replace(document, source_image=_source_image_reference(source, output_path))
        write_catalog_document(document, output_path)
        if args.review_dir is not None:
            render_catalog_review_overlay(source, document, args.review_dir / source.name)
    return 0


def _discover_sources(source_dir: Path, limit: int | None) -> list[Path]:
    sources = sorted(
        path
        for path in source_dir.glob("*.png")
        if path.is_file() and path.name != "contact-sheet-primary.png"
    )
    if limit is not None:
        return sources[:limit]
    return sources


def _check_outputs(sources: list[Path], output_dir: Path) -> int:
    if not sources:
        return 1
    expected = {source.stem for source in sources}
    actual = {path.stem for path in output_dir.glob("*.json")} if output_dir.exists() else set()
    if expected != actual:
        return 1
    for source in sources:
        output_path = output_dir / f"{source.stem}.json"
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            document = CatalogOutlineDocument.from_json(payload)
            source_image = Path(document.source_image)
            if source_image.is_absolute():
                return 1
            resolved_source = (output_path.parent / source_image).resolve()
            if resolved_source != source.resolve():
                return 1
            validate_catalog_document(document, source_path=resolved_source)
        except (OSError, ValueError, json.JSONDecodeError):
            return 1
    return 0


def _source_image_reference(source: Path, output_path: Path) -> str:
    return Path(os.path.relpath(source.resolve(), output_path.parent.resolve())).as_posix()
