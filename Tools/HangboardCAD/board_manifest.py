"""Generate a CAD-backed board's ``board.json`` from its FreeCAD source.

For a package with a native source (``Hangboards/<slug>/<slug>.FCStd``) the
FCStd is the single source of truth for the board's logical metadata as well as
its geometry. The metadata lives in two document-level string properties:

* ``HangTenBoardID`` -- the board ``id`` (also bound by the compiler);
* ``HangTenBoardManifest`` -- compact JSON of ``board.json`` *minus* ``id``, in
  the key order ``board.json`` is emitted in.

``board.json`` is then a generated, committed build output: Xcode bundles
``Hangboards/<slug>`` directly and cannot run FreeCAD, so the file stays in the
repository and CI checks it is fresh. Never hand-edit a generated ``board.json``;
change the manifest with ``set_board_manifest.py`` and regenerate.

Everything that is derivable from the CAD or the build is left out of the
manifest. Only ``id`` qualifies: ``aspectRatio`` is a presentation fact that is
not reproducible from the descriptor ``modelBounds`` for most boards, and
published grip depths are sourced product facts that ``compile_board.py``
validates the geometry against, so both stay in the manifest.

This module is pure host Python (stdlib only). It never imports FreeCAD, so the
freshness check runs anywhere, including CI on Linux.

    python3 Tools/HangboardCAD/board_manifest.py --package <slug>          # write
    python3 Tools/HangboardCAD/board_manifest.py --check --all             # CI
    python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug>   # manifest
    python3 Tools/HangboardCAD/board_manifest.py --dump-file <path.FCStd>  # textconv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract  # noqa: E402

REPOSITORY = Path(__file__).resolve().parents[2]
MANIFEST_PROPERTY = "HangTenBoardManifest"
ID_PROPERTY = "HangTenBoardID"
DERIVED_KEYS = ("id",)
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"


class ManifestError(ValueError):
    """The source's board manifest is missing, malformed, or inconsistent."""


# --- document properties ----------------------------------------------------


def _parse_document(data: bytes) -> ET.Element:
    if len(data) > contract.MAX_XML_BYTES:
        raise ManifestError("CAD document XML exceeds size limit")
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ManifestError("unsupported XML declaration")
    root = ET.fromstring(data)
    if root.tag != "Document":
        raise ManifestError("invalid CAD document XML root")
    return root


def document_properties_from_xml(data: bytes) -> dict[str, tuple[str, str | None]]:
    """Document-level properties as ``name -> (type, scalar value or None)``."""
    root = _parse_document(data)
    properties: dict[str, tuple[str, str | None]] = {}
    for prop in root.findall("./Properties/Property"):
        name, kind = prop.get("name", ""), prop.get("type", "")
        value = None
        child = next(iter(prop), None)
        if child is not None and "value" in child.attrib:
            value = child.get("value")
        properties[name] = (kind, value)
    return properties


def read_document_xml(source: Path) -> bytes:
    with zipfile.ZipFile(source) as archive:
        return archive.read("Document.xml")


def _is_lfs_pointer(path: Path) -> bool:
    with Path(path).open("rb") as stream:
        return stream.read(len(LFS_POINTER)) == LFS_POINTER


# --- JSON with preserved number spelling -----------------------------------


class LexemeFloat(float):
    """A float that remembers how it was written.

    Number spelling is part of the package contract, not just formatting: the
    package validator requires reusable instance translations to be written
    with exactly nine decimal places (``0.000000000``), which a plain float
    round trip would rewrite as ``0.0``. Every float keeps its source lexeme.
    """

    lexeme: str

    def __new__(cls, lexeme: str):
        value = super().__new__(cls, lexeme)
        value.lexeme = lexeme
        return value


def loads(text: str):
    """Parse JSON keeping key order and every float's original spelling."""
    return json.loads(text, parse_float=LexemeFloat)


def _encode(value, indent: int | None, level: int = 0) -> str:
    if isinstance(value, LexemeFloat):
        return value.lexeme
    if isinstance(value, dict) or isinstance(value, list):
        items = list(value.items()) if isinstance(value, dict) else list(value)
        opening, closing = ("{", "}") if isinstance(value, dict) else ("[", "]")
        if not items:
            return opening + closing

        def item(entry) -> str:
            if isinstance(value, dict):
                key, member = entry
                separator = ": " if indent is not None else ":"
                return json.dumps(key, ensure_ascii=False) + separator + _encode(
                    member, indent, level + 1
                )
            return _encode(entry, indent, level + 1)

        if indent is None:
            return opening + ",".join(item(entry) for entry in items) + closing
        inner = "\n" + " " * (indent * (level + 1))
        return (
            opening + inner + ("," + inner).join(item(entry) for entry in items)
            + "\n" + " " * (indent * level) + closing
        )
    return json.dumps(value, ensure_ascii=False)


# --- manifest <-> board -----------------------------------------------------


def render_manifest(manifest: dict) -> str:
    """The exact string stored in ``HangTenBoardManifest``.

    Compact and single-line so the XML attribute never carries a newline; key
    order and number spelling are preserved because ``board.json`` is emitted
    from it.
    """
    return _encode(manifest, None)


def render_board(board: dict) -> bytes:
    """The canonical ``board.json`` bytes: ``json.dumps(indent=2)`` layout,
    literal UTF-8, and each number spelled as it was authored."""
    return (_encode(board, 2) + "\n").encode("utf-8")


def board_to_manifest(board: dict) -> dict:
    if not isinstance(board, dict) or board.get("schemaVersion") != 3:
        raise ManifestError("board metadata must be a schema-v3 object")
    if list(board)[:2] != ["schemaVersion", "id"]:
        raise ManifestError("board.json must start with schemaVersion then id")
    return {key: value for key, value in board.items() if key not in DERIVED_KEYS}


def manifest_to_board(manifest: dict, board_id: str) -> dict:
    """Rebuild ``board.json``: ``id`` is inserted directly after ``schemaVersion``."""
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 3:
        raise ManifestError(f"{MANIFEST_PROPERTY} must be a schema-v3 object")
    if list(manifest)[:1] != ["schemaVersion"]:
        raise ManifestError(f"{MANIFEST_PROPERTY} must start with schemaVersion")
    for key in DERIVED_KEYS:
        if key in manifest:
            raise ManifestError(f"{MANIFEST_PROPERTY} must not carry derived key {key!r}")
    if not isinstance(board_id, str) or not board_id:
        raise ManifestError(f"{ID_PROPERTY} is missing or empty")
    board: dict = {}
    for key, value in manifest.items():
        board[key] = value
        if key == "schemaVersion":
            board["id"] = board_id
    return board


def parse_manifest(text: str) -> dict:
    try:
        manifest = loads(text)
    except json.JSONDecodeError as error:
        raise ManifestError(f"{MANIFEST_PROPERTY} is not valid JSON: {error}") from error
    if not isinstance(manifest, dict):
        raise ManifestError(f"{MANIFEST_PROPERTY} must be a JSON object")
    return manifest


def manifest_from_properties(properties: dict) -> tuple[str, dict] | None:
    """``(board id, manifest)`` from parsed document properties, or None if absent."""
    if MANIFEST_PROPERTY not in properties:
        return None
    kind, text = properties[MANIFEST_PROPERTY]
    if kind != "App::PropertyString" or text is None:
        raise ManifestError(f"{MANIFEST_PROPERTY} must be an App::PropertyString")
    id_kind, board_id = properties.get(ID_PROPERTY, ("", None))
    if id_kind != "App::PropertyString" or not board_id:
        raise ManifestError(f"source carries {MANIFEST_PROPERTY} but no {ID_PROPERTY}")
    return board_id, parse_manifest(text)


def has_manifest(source: Path) -> bool:
    source = Path(source)
    if _is_lfs_pointer(source):
        raise ManifestError(f"{source} is a Git LFS pointer; fetch its LFS object first")
    return MANIFEST_PROPERTY in document_properties_from_xml(read_document_xml(source))


def load_board(source: Path) -> dict:
    """Validate the source archive and return the board it defines."""
    source = Path(source)
    try:
        contract.inspect_archive(source)
    except ValueError as error:
        raise ManifestError(f"{source}: {error}") from error
    found = manifest_from_properties(document_properties_from_xml(read_document_xml(source)))
    if found is None:
        raise ManifestError(f"{source} carries no {MANIFEST_PROPERTY} property")
    board_id, manifest = found
    return manifest_to_board(manifest, board_id)


def generate_board_json(source: Path) -> bytes:
    return render_board(load_board(source))


# --- packages ---------------------------------------------------------------


def package_source(root: Path, package: str) -> Path:
    return root / "Hangboards" / package / f"{package}.FCStd"


def source_backed_packages(root: Path) -> list[str]:
    return sorted(
        path.parent.name
        for path in (root / "Hangboards").glob("*/*.FCStd")
        if path.stem == path.parent.name
    )


def check_package(root: Path, package: str) -> str | None:
    """None when ``board.json`` is fresh, otherwise a human-readable problem."""
    source = package_source(root, package)
    target = root / "Hangboards" / package / "board.json"
    if not source.is_file():
        return f"{package}: missing source {source.relative_to(root)}"
    try:
        expected = generate_board_json(source)
    except ManifestError as error:
        return f"{package}: {error}"
    if not target.is_file():
        return f"{package}: board.json is missing; regenerate it from the FCStd"
    if target.read_bytes() != expected:
        return (
            f"{package}: board.json is stale or hand-edited; it is generated from "
            f"{MANIFEST_PROPERTY} in {source.name}. Edit the manifest with "
            "Tools/HangboardCAD/set_board_manifest.py, then run "
            f"`python3 Tools/HangboardCAD/board_manifest.py --package {package}`"
        )
    return None


def write_package(root: Path, package: str) -> bool:
    """Regenerate ``board.json``; True when the file changed."""
    expected = generate_board_json(package_source(root, package))
    target = root / "Hangboards" / package / "board.json"
    if target.is_file() and target.read_bytes() == expected:
        return False
    staged = target.with_name(f".{target.name}.staged")
    staged.write_bytes(expected)
    os.replace(staged, target)
    return True


# --- textconv ---------------------------------------------------------------


def _resolve_lfs_pointer(path: Path) -> Path | None:
    """Map an LFS pointer (as git hands a blob to textconv) to its local object."""
    fields = dict(
        line.split(" ", 1)
        for line in path.read_text(errors="replace").splitlines()
        if " " in line
    )
    oid = fields.get("oid", "")
    if not oid.startswith("sha256:"):
        return None
    digest = oid.split(":", 1)[1]
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    candidate = Path(common) / "lfs" / "objects" / digest[:2] / digest[2:4] / digest
    return candidate if candidate.is_file() else None


def describe_source(path: Path) -> str:
    """A stable text rendering of an FCStd for ``git diff`` (textconv).

    HangTen document properties, the pretty-printed board manifest, and one
    ``sha256 size name`` line per archive member, so metadata edits read as JSON
    diffs and geometry edits show up as changed member digests.
    """
    path = Path(path)
    lines: list[str] = []
    if _is_lfs_pointer(path):
        resolved = _resolve_lfs_pointer(path)
        if resolved is None:
            return "Git LFS pointer (object not available locally):\n" + path.read_text(
                errors="replace"
            )
        path = resolved
    try:
        with zipfile.ZipFile(path) as archive:
            members = [
                (info.filename, archive.read(info.filename)) for info in archive.infolist()
            ]
    except zipfile.BadZipFile as error:
        return f"not an FCStd archive: {error}\n"
    document = dict(members).get("Document.xml", b"")
    try:
        properties = document_properties_from_xml(document)
    except (ManifestError, ET.ParseError) as error:
        properties = {}
        lines.append(f"# unreadable Document.xml: {error}")
    lines.append("# HangTen document properties")
    for name in sorted(properties):
        if name.startswith("HangTen") and name != MANIFEST_PROPERTY:
            lines.append(f"{name} = {properties[name][1]}")
    lines.append("")
    lines.append(f"# {MANIFEST_PROPERTY}")
    kind, text = properties.get(MANIFEST_PROPERTY, ("", None))
    if text is None:
        lines.append("(absent)")
    else:
        try:
            lines.append(_encode(loads(text), 2))
        except json.JSONDecodeError:
            lines.append(f"(invalid JSON) {text}")
    lines.append("")
    lines.append("# archive members (sha256 size name)")
    for name, data in members:
        lines.append(f"{hashlib.sha256(data).hexdigest()} {len(data):>10} {name}")
    return "\n".join(lines) + "\n"


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--package", action="append", default=[], help="Hangboards/<slug>")
    parser.add_argument("--all", action="store_true", help="every source-backed package")
    parser.add_argument("--check", action="store_true", help="fail if board.json is stale")
    parser.add_argument("--dump", action="store_true", help="print the manifest JSON")
    parser.add_argument("--dump-file", type=Path, help="textconv rendering of an FCStd path")
    parser.add_argument("--root", type=Path, default=REPOSITORY, help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()

    if arguments.dump_file is not None:
        sys.stdout.write(describe_source(arguments.dump_file))
        return 0

    packages = list(arguments.package)
    if arguments.all:
        packages = source_backed_packages(root)
    if not packages:
        parser.error("name --package <slug> or --all")
    for package in packages:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", package):
            parser.error(f"invalid package name: {package!r}")

    if arguments.dump:
        for package in packages:
            board = load_board(package_source(root, package))
            print(_encode(board_to_manifest(board), 2))
        return 0

    if arguments.check:
        problems = [problem for p in packages if (problem := check_package(root, p))]
        for problem in problems:
            print(f"STALE: {problem}", file=sys.stderr)
        if problems:
            return 1
        print(f"board.json is fresh for {len(packages)} CAD-backed package(s)")
        return 0

    for package in packages:
        changed = write_package(root, package)
        print(f"{package}: board.json {'regenerated' if changed else 'already fresh'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManifestError as error:
        print(f"MANIFEST ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
