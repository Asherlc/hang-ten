"""Set or replace a CAD source's board manifest.

A CAD-backed board's logical metadata lives in its FCStd as the document-level
``HangTenBoardManifest`` string property (see ``board_manifest.py``). This is
the supported way to change it:

    # 1. start from the current metadata
    python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug> > /tmp/m.json
    # 2. edit /tmp/m.json (board.json fields minus "id"); cite sources per AGENTS.md
    # 3. write it into the FCStd
    python3 Tools/HangboardCAD/set_board_manifest.py --package <slug> /tmp/m.json
    # 4. validate the package (board.json is generated from the FCStd in memory)
    scripts/hangboard-packages.sh validate --root Hangboards --final-inventory

``board.json`` is not written anywhere: for a CAD-backed package it is generated
at build time and must not exist in the package. ``board_manifest.py --package
<slug> [--output <path>]`` prints or writes the generated file for inspection.

The input may be a manifest (no ``id``) or a full ``board.json``-shaped object
whose ``id`` equals the source's ``HangTenBoardID``.

This deliberately does *not* re-save the document through FreeCAD. A FreeCAD
save re-serializes every shape (``*.brp``, element maps, placements) with
last-ulp differences, which can change the compiled asset. Instead the archive
is rewritten with only ``Document.xml`` changed: the property element is
inserted (or its value replaced) textually, exactly as FreeCAD itself writes a
document-level ``App::PropertyString``, and every other member's content is
copied unchanged. The result is verified by re-reading it, by
``cad_source.inspect_archive``, and by requiring every other member to be
byte-identical. FreeCAD opens the result normally, and editing the property in
the FreeCAD GUI is equally valid (it just re-saves the whole document).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

# Puts Tools/HangboardPackages/src on sys.path (host python3 and freecadcmd).
import use_hangboard_packages  # noqa: F401
from hangboard_packages import cad_source

import board_manifest

PROPERTY = cad_source.MANIFEST_PROPERTY
PROPERTY_DOC = (
    "board.json minus id, as compact JSON. board.json is generated from this; "
    "see Tools/HangboardCAD/board_manifest.py"
)  # Unchanged wording: it is stored in every embedded FCStd.
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
        raise cad_source.ManifestError("Document.xml has no document-level Properties")
    start = opening.end()
    close = data.find(b"</Properties>", start)
    if close < 0:
        raise cad_source.ManifestError("unterminated document-level Properties")
    block = data[start:close]
    if b"<Properties" in block:
        raise cad_source.ManifestError("unexpected nested Properties block")

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
        raise cad_source.ManifestError("document-level Properties block is empty")
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
    cad_source.inspect_archive(source)
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        members = {info.filename: archive.read(info.filename) for info in infos}
        comment = archive.comment
    properties = cad_source.document_properties_from_xml(members["Document.xml"])
    board_id = (properties.get(cad_source.ID_PROPERTY) or ("", None))[1]
    board = cad_source.manifest_to_board(manifest, board_id)
    text = cad_source.render_manifest(cad_source.board_to_manifest(board))
    current = properties.get(PROPERTY, ("", None))[1]
    if current == text:
        return False

    document = rewrite_document_xml(members["Document.xml"], text)
    handle, staged_name = tempfile.mkstemp(prefix=".manifest-", suffix=".FCStd", dir=source.parent)
    os.close(handle)
    staged = Path(staged_name)
    # mkstemp creates 0600; keep the source's own mode across the replace.
    os.chmod(staged, stat.S_IMODE(source.stat().st_mode))
    try:
        with zipfile.ZipFile(staged, "w") as out:
            out.comment = comment
            for info in infos:
                data = document if info.filename == "Document.xml" else members[info.filename]
                out.writestr(_copy_info(info), data)
        cad_source.inspect_archive(staged)
        with zipfile.ZipFile(staged) as check:
            if [i.filename for i in check.infolist()] != [i.filename for i in infos]:
                raise cad_source.ManifestError("rewrite changed the member inventory")
            for info in infos:
                if info.filename != "Document.xml" and check.read(info.filename) != members[info.filename]:
                    raise cad_source.ManifestError(f"rewrite changed {info.filename}")
        if cad_source.load_board(staged) != board:
            raise cad_source.ManifestError("rewritten manifest does not read back")
        os.replace(staged, source)
    finally:
        if staged.exists():
            staged.unlink()
    return True


def read_input(path: Path, board_id: str) -> dict:
    value = cad_source.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise cad_source.ManifestError("input must be a JSON object")
    if "id" in value:
        if value["id"] != board_id:
            raise cad_source.ManifestError(
                f"input id {value['id']!r} does not match HangTenBoardID {board_id!r}; "
                "the id is owned by the CAD source"
            )
        value = cad_source.board_to_manifest(value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--package", help="Hangboards/<slug>")
    target.add_argument("--source", type=Path, help="an FCStd outside a package")
    parser.add_argument("input", type=Path, help="manifest or board.json-shaped JSON")
    arguments = parser.parse_args(argv)

    root = board_manifest.REPOSITORY
    source = (
        board_manifest.package_source(root, arguments.package)
        if arguments.package else arguments.source
    )
    # read_document_xml runs the archive contract first and reports a corrupt
    # or missing source as a ManifestError.
    properties = cad_source.document_properties_from_xml(
        cad_source.read_document_xml(source)
    )
    board_id = (properties.get(cad_source.ID_PROPERTY) or ("", None))[1]
    changed = embed(source, read_input(arguments.input, board_id))
    print(f"{source}: {PROPERTY} {'updated' if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (cad_source.ManifestError, ValueError, OSError) as error:
        print(f"MANIFEST ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
