"""One-off migration: move each CAD board's board.json into its FCStd.

Before this migration a CAD-backed package carried two hand-maintained inputs,
``<slug>.FCStd`` and ``board.json``. Afterwards the FCStd's
``HangTenBoardManifest`` property is the only source and ``board.json`` is
generated from it (``Tools/HangboardCAD/board_manifest.py``).

For every source-backed package this:

1. reads the committed ``board.json`` and requires its ``id`` to equal the
   source's ``HangTenBoardID``;
2. embeds ``board.json`` minus ``id`` with ``set_board_manifest.embed`` (only
   ``Document.xml`` changes; every geometry member stays byte-identical);
3. regenerates ``board.json`` and requires it to be *token-identical* to the
   committed one: equal values, equal key order at every level, and every
   number spelled exactly as before (the package validator reads some number
   lexemes, e.g. nine-decimal instance translations). Only whitespace and
   string escaping may change: the generator's canonical ``indent=2``/UTF-8
   layout replaces hand formatting such as inline arrays or ``\\u00d7``.

Historical record: this migration was applied in commit 3e1653b and is not
part of any build or CI step. Edit an embedded manifest with
``Tools/HangboardCAD/set_board_manifest.py`` instead.

Host Python only; FreeCAD is not needed.

    python3 Tools/HangboardCAD/migration/embed_board_manifest.py [--package <slug>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import board_manifest  # noqa: E402
import set_board_manifest  # noqa: E402


def _typed(value):
    """A comparison form that keeps key order and distinguishes int from float."""
    if isinstance(value, dict):
        return ("object", [(key, _typed(item)) for key, item in value.items()])
    if isinstance(value, list):
        return ("array", [_typed(item) for item in value])
    if isinstance(value, board_manifest.LexemeFloat):
        return ("number", value.lexeme)
    return (type(value).__name__, value)


def migrate(root: Path, package: str) -> dict:
    source = board_manifest.package_source(root, package)
    target = root / "Hangboards" / package / "board.json"
    original_bytes = target.read_bytes()
    original = board_manifest.loads(original_bytes.decode("utf-8"))
    properties = board_manifest.document_properties_from_xml(
        board_manifest.read_document_xml(source)
    )
    board_id = (properties.get(board_manifest.ID_PROPERTY) or ("", None))[1]
    if original.get("id") != board_id:
        raise SystemExit(f"{package}: board.json id does not match HangTenBoardID")
    embedded = set_board_manifest.embed(source, board_manifest.board_to_manifest(original))
    generated = board_manifest.generate_board_json(source)
    if _typed(board_manifest.loads(generated.decode("utf-8"))) != _typed(original):
        raise SystemExit(f"{package}: generated board.json is not token-identical")
    board_manifest.write_package(root, package)
    return {
        "package": package,
        "manifestEmbedded": embedded,
        "boardJSONByteIdentical": generated == original_bytes,
        "boardJSONTokenIdentical": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="append", default=[])
    arguments = parser.parse_args(argv)
    root = board_manifest.REPOSITORY
    packages = arguments.package or board_manifest.source_backed_packages(root)
    reports = [migrate(root, package) for package in packages]
    print(json.dumps(reports, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
