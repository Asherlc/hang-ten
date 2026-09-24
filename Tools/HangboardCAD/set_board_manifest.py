"""Set or replace a CAD source's board manifest, then regenerate ``board.json``.

A CAD-backed board's logical metadata lives in its FCStd as the document-level
``HangTenBoardManifest`` string property (see ``board_manifest.py``). This is
the supported way to change it:

    # 1. start from the current metadata
    python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug> > /tmp/m.json
    # 2. edit /tmp/m.json (board.json fields minus "id"); cite sources per AGENTS.md
    # 3. write it into the FCStd and regenerate Hangboards/<slug>/board.json
    python3 Tools/HangboardCAD/set_board_manifest.py --package <slug> /tmp/m.json

The input may be a manifest (no ``id``) or a full ``board.json``-shaped object
whose ``id`` equals the source's ``HangTenBoardID``.

This deliberately does *not* re-save the document through FreeCAD. A FreeCAD
save re-serializes every shape (``*.brp``, element maps, placements) with
last-ulp differences, which can change the compiled asset. Instead the archive
is rewritten with only ``Document.xml`` changed: the property element is
inserted (or its value replaced) textually, exactly as FreeCAD itself writes a
document-level ``App::PropertyString``, and every other member's content is
copied unchanged. The result is verified by re-reading it, by
``contract.inspect_archive``, and by requiring every other member to be
byte-identical. FreeCAD opens the result normally, and editing the property in
the FreeCAD GUI is equally valid (it just re-saves the whole document).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import board_manifest  # noqa: E402
import contract  # noqa: E402

PROPERTY = board_manifest.MANIFEST_PROPERTY
PROPERTY_DOC = (
    "board.json minus id, as compact JSON. board.json is generated from this; "
    "see Tools/HangboardCAD/board_manifest.py"
)
_PROPERTIES_OPEN = re.compile(rb'<Properties Count="(\d+)"( TransientCount="\d+")?>')
_ESCAPES = {
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;",
    "\n": "&#10;", "\r": "&#13;", "\t": "&#9;",
}


def _escape(value: str) -> str:
    return "".join(_ESCAPES.get(character, character) for character in value)


def _property_block(name: str, value: str, indent: bytes) -> bytes:
    inner = indent + b"    "
    return (
        indent
        + f'<Property name="{name}" type="App::PropertyString" group="HangTen" '
          f'doc="{_escape(PROPERTY_DOC)}" attr="0" ro="0" hide="0" status="2097153">\n'.encode()
        + inner + f'<String value="{_escape(value)}"/>\n'.encode()
        + indent + b"</Property>\n"
    )


def rewrite_document_xml(data: bytes, manifest_text: str) -> bytes:
    """Insert or replace the manifest property in the document-level block only."""
    opening = _PROPERTIES_OPEN.search(data)
    if opening is None:
        raise board_manifest.ManifestError("Document.xml has no document-level Properties")
    start = opening.end()
    close = data.find(b"</Properties>", start)
    if close < 0:
        raise board_manifest.ManifestError("unterminated document-level Properties")
    block = data[start:close]
    if b"<Properties" in block:
        raise board_manifest.ManifestError("unexpected nested Properties block")

    existing = re.search(
        rb'<Property name="' + PROPERTY.encode() + rb'" [^>]*>\s*<String value="[^"]*"/>',
        block,
    )
    if existing is not None:
        element = f'<String value="{_escape(manifest_text)}"/>'.encode()
        replaced = re.sub(
            rb'<String value="[^"]*"/>', lambda _match: element, existing.group(0), count=1
        )
        block = block[: existing.start()] + replaced + block[existing.end():]
        return data[:start] + block + data[close:]

    # FreeCAD writes properties sorted by name; insert before the first
    # document-level property whose name sorts after ours.
    entries = list(re.finditer(rb'\n( *)<Property name="([^"]+)"', block))
    if not entries:
        raise board_manifest.ManifestError("document-level Properties block is empty")
    indent = entries[0].group(1)
    for entry in entries:
        if entry.group(2).decode() > PROPERTY:
            position = entry.start() + 1
            break
    else:
        position = block.rfind(b"\n") + 1
    block = block[:position] + _property_block(PROPERTY, manifest_text, indent) + block[position:]
    count = int(opening.group(1)) + 1
    header = f'<Properties Count="{count}"'.encode() + (opening.group(2) or b"") + b">"
    return data[: opening.start()] + header + block + data[close:]


def _copy_info(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    copy = zipfile.ZipInfo(info.filename, date_time=info.date_time)
    copy.compress_type = info.compress_type
    copy.create_system = info.create_system
    copy.external_attr = info.external_attr
    copy.internal_attr = info.internal_attr
    copy.comment = info.comment
    return copy


def embed(source: Path, manifest: dict) -> bool:
    """Write ``manifest`` into ``source`` in place; True when the bytes changed."""
    source = Path(source)
    contract.inspect_archive(source)
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        members = {info.filename: archive.read(info.filename) for info in infos}
        comment = archive.comment
    properties = board_manifest.document_properties_from_xml(members["Document.xml"])
    board_id = (properties.get(board_manifest.ID_PROPERTY) or ("", None))[1]
    board = board_manifest.manifest_to_board(manifest, board_id)
    text = board_manifest.render_manifest(board_manifest.board_to_manifest(board))
    current = properties.get(PROPERTY, ("", None))[1]
    if current == text:
        return False

    document = rewrite_document_xml(members["Document.xml"], text)
    handle, staged_name = tempfile.mkstemp(prefix=".manifest-", suffix=".FCStd", dir=source.parent)
    os.close(handle)
    staged = Path(staged_name)
    try:
        with zipfile.ZipFile(staged, "w") as out:
            out.comment = comment
            for info in infos:
                data = document if info.filename == "Document.xml" else members[info.filename]
                out.writestr(_copy_info(info), data)
        contract.inspect_archive(staged)
        with zipfile.ZipFile(staged) as check:
            if [i.filename for i in check.infolist()] != [i.filename for i in infos]:
                raise board_manifest.ManifestError("rewrite changed the member inventory")
            for info in infos:
                if info.filename != "Document.xml" and check.read(info.filename) != members[info.filename]:
                    raise board_manifest.ManifestError(f"rewrite changed {info.filename}")
        if board_manifest.load_board(staged) != board:
            raise board_manifest.ManifestError("rewritten manifest does not read back")
        os.replace(staged, source)
    finally:
        if staged.exists():
            staged.unlink()
    return True


def read_input(path: Path, board_id: str) -> dict:
    value = board_manifest.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise board_manifest.ManifestError("input must be a JSON object")
    if "id" in value:
        if value["id"] != board_id:
            raise board_manifest.ManifestError(
                f"input id {value['id']!r} does not match HangTenBoardID {board_id!r}; "
                "the id is owned by the CAD source"
            )
        value = board_manifest.board_to_manifest(value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--package", help="Hangboards/<slug>; also regenerates board.json")
    target.add_argument("--source", type=Path, help="an FCStd outside a package")
    parser.add_argument("input", type=Path, help="manifest or board.json-shaped JSON")
    arguments = parser.parse_args(argv)

    root = board_manifest.REPOSITORY
    source = (
        board_manifest.package_source(root, arguments.package)
        if arguments.package else arguments.source
    )
    properties = board_manifest.document_properties_from_xml(
        board_manifest.read_document_xml(source)
    )
    board_id = (properties.get(board_manifest.ID_PROPERTY) or ("", None))[1]
    changed = embed(source, read_input(arguments.input, board_id))
    print(f"{source}: {PROPERTY} {'updated' if changed else 'unchanged'}")
    if arguments.package:
        regenerated = board_manifest.write_package(root, arguments.package)
        print(f"{arguments.package}: board.json {'regenerated' if regenerated else 'already fresh'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (board_manifest.ManifestError, ValueError) as error:
        print(f"MANIFEST ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
