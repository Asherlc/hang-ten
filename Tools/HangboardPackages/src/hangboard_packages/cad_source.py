"""The FreeCAD authoring source of a CAD-backed hangboard package.

A CAD-backed package (``Hangboards/<slug>/<slug>.FCStd``) keeps its board
metadata inside the FCStd, in two document-level string properties:

* ``HangTenBoardID`` -- the board ``id``;
* ``HangTenBoardManifest`` -- compact JSON of ``board.json`` *minus* ``id``, in
  the key order ``board.json`` is emitted in, with every number spelled as
  authored.

``board.json`` for such a package is generated from the FCStd at build time and
is never committed: the package validator (``board_catalog``), the iOS and
Android staging (``scripts/stage-board-packages.py``), and every tool that needs
the board document call :func:`generate_board_json`. An on-disk ``board.json``
inside a CAD-backed package is rejected as a stale hand edit.

This module is pure host Python (stdlib only) and never imports FreeCAD. The
``Tools/HangboardCAD`` scripts (``board_manifest.py``, ``set_board_manifest.py``,
``compile_board.py``) import it directly; ``Tools/HangboardCAD/
use_hangboard_packages.py`` makes it importable there under host Python and
FreeCAD's ``freecadcmd``.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import stat
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

MANIFEST_PROPERTY = "HangTenBoardManifest"
ID_PROPERTY = "HangTenBoardID"
DERIVED_KEYS = ("id",)
SOURCE_SUFFIX = ".FCStd"
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"

# --- archive contract -------------------------------------------------------

MAX_ARCHIVE_BYTES = 2 * 1024**3
MAX_XML_BYTES = 32 * 1024**2
# Exact builtin types: prefix matching would admit arbitrary addon/Python objects.
BUILTIN_TYPES = frozenset({
    "App::DocumentObjectGroup", "App::Part", "App::Origin", "App::Line", "App::Plane",
    "App::Point",
    "Part::Feature", "Part::Box", "Part::Cylinder", "Part::Cone", "Part::Sphere",
    "Part::Torus", "Part::Ellipsoid", "Part::Prism", "Part::Extrusion", "Part::Cut",
    "Part::Fuse", "Part::MultiFuse", "Part::Common", "Part::MultiCommon", "Part::Face",
    "Part::Fillet", "Part::Chamfer", "Part::Loft", "Part::RuledSurface", "Part::Sweep",
    "Part::Compound", "Part::Refine", "Part::Thickness", "Part::Mirroring", "Part::Reverse",
    "PartDesign::Body", "PartDesign::Feature", "PartDesign::Pad", "PartDesign::Pocket",
    "PartDesign::Revolution", "PartDesign::Groove", "PartDesign::AdditiveLoft",
    "PartDesign::SubtractiveLoft", "PartDesign::AdditivePipe", "PartDesign::SubtractivePipe",
    "PartDesign::Fillet", "PartDesign::Chamfer", "PartDesign::Draft",
    "PartDesign::Mirrored", "PartDesign::LinearPattern", "PartDesign::PolarPattern",
    "PartDesign::MultiTransform", "PartDesign::SubShapeBinder", "PartDesign::ShapeBinder",
    "Sketcher::SketchObject",
    "Mesh::Feature",
})
# Cross-document reference properties. FreeCAD stores the referencing document's
# path in a ``file`` attribute; an empty value means the reference stays inside
# this document. A non-empty value is an external dependency and is rejected.
XLINK_TYPES = frozenset({
    "App::PropertyXLink", "App::PropertyXLinkSub", "App::PropertyXLinkSubList",
    "App::PropertyXLinkList", "App::PropertyXLinkSubHidden",
    "App::PropertyXLinkContainer",
})
REJECTED_TYPES = frozenset({
    "App::PropertyFile", "App::PropertyPath", "App::PropertyPersistentObject",
})


def safe_member(name: str) -> str:
    """Validate a portable, relative ZIP member or output path, without normalizing."""
    if (not isinstance(name, str) or not name or "\x00" in name or "\\" in name
            or name.startswith("/") or ":" in name
            or any(p in {"", ".", ".."} for p in name.split("/"))
            or PurePosixPath(name).as_posix() != name):
        raise ValueError(f"unsafe member path: {name!r}")
    return name


def inspect_archive(path: Path) -> dict:
    """Reject unsafe/nonportable sources before FreeCAD can restore objects.

    This is a contract check, not a general sandbox for arbitrary CAD documents.
    Builds must still run without secrets and in an isolated process.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("CAD input must be a regular, non-symlink file")
    with path.open("rb") as stream:
        if stream.read(80).startswith(LFS_POINTER):
            raise ValueError("CAD input is a Git LFS pointer; fetch its LFS object first")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > 10000 or sum(x.file_size for x in infos) > MAX_ARCHIVE_BYTES:
                raise ValueError("CAD archive exceeds source size limits")
            names = set()
            portable = set()
            for info in infos:
                name = safe_member(info.filename.rstrip("/") if info.is_dir() else info.filename)
                key = unicodedata.normalize("NFD", name).casefold()
                if name in names or key in portable:
                    raise ValueError("duplicate or case-colliding archive member")
                names.add(name)
                portable.add(key)
                kind = stat.S_IFMT(info.external_attr >> 16)
                if kind not in {0, stat.S_IFREG, stat.S_IFDIR} or info.flag_bits & 1:
                    raise ValueError("unsupported archive member type or encryption")
            if "Document.xml" not in names:
                raise ValueError("CAD archive is missing Document.xml")
            if archive.getinfo("Document.xml").file_size > MAX_XML_BYTES:
                raise ValueError("CAD document XML exceeds size limit")
            data = archive.read("Document.xml")
            if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
                raise ValueError("unsupported XML declaration")
            root = ET.fromstring(data)
            if root.tag != "Document":
                raise ValueError("invalid CAD document XML root")
            objects = {}
            for item in root.findall("./Objects/Object"):
                name, kind = item.get("name"), item.get("type")
                if not name or name in objects:
                    raise ValueError("duplicate or missing document object name")
                if kind not in BUILTIN_TYPES:
                    raise ValueError(f"unsupported document object type: {kind}")
                objects[name] = kind
            if not objects:
                raise ValueError("empty CAD document")
            data_names = [o.get("name") for o in root.findall("./ObjectData/Object")]
            if len(data_names) != len(set(data_names)) or set(data_names) != set(objects):
                raise ValueError("document object/data inventory mismatch")
            for prop in root.findall(".//Property"):
                kind = prop.get("type", "")
                if "Python" in kind or kind in REJECTED_TYPES:
                    raise ValueError(f"unsupported executable/external property: {kind}")
                if kind in XLINK_TYPES:
                    for link in prop.iter():
                        if link.get("file"):
                            raise ValueError(
                                "unsupported external document reference: "
                                f"{prop.get('name', '')} -> {link.get('file')}"
                            )
                if kind == "App::PropertyFileIncluded":
                    child = prop.find("FileIncluded")
                    name = child.get("file", "") if child is not None else ""
                    if not name or safe_member(name) not in names:
                        raise ValueError("missing included file in CAD document")
            return {"objects": objects, "members": sorted(names)}
    except (zipfile.BadZipFile, ET.ParseError, OSError) as error:
        raise ValueError(f"invalid FCStd archive/XML: {error}") from error


class ManifestError(ValueError):
    """The source's board manifest is missing, malformed, or inconsistent."""


# --- document properties ----------------------------------------------------


def _parse_document(data: bytes) -> ET.Element:
    if len(data) > MAX_XML_BYTES:
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
    """``Document.xml`` of an FCStd that passes :func:`inspect_archive`."""
    source = Path(source)
    try:
        inspect_archive(source)
        with zipfile.ZipFile(source) as archive:
            return archive.read("Document.xml")
    except (ValueError, OSError, zipfile.BadZipFile, KeyError) as error:
        if isinstance(error, ManifestError):
            raise
        raise ManifestError(f"{source}: {error}") from error


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


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    board: dict = {}
    for key, value in pairs:
        if key in board:
            raise ManifestError(f"duplicate JSON key: {key!r}")
        board[key] = value
    return board


def loads(text: str):
    """Parse JSON keeping key order and every float's original spelling.

    A duplicate object key is an error rather than silently keeping the last
    value, matching the package validator.
    """
    return json.loads(text, parse_float=LexemeFloat, object_pairs_hook=_unique_object)


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
    """Whether a source carries a manifest; the archive contract is checked first."""
    return MANIFEST_PROPERTY in document_properties_from_xml(read_document_xml(source))


def load_board(source: Path) -> dict:
    """Validate the source archive and return the board it defines."""
    source = Path(source)
    found = manifest_from_properties(document_properties_from_xml(read_document_xml(source)))
    if found is None:
        raise ManifestError(f"{source} carries no {MANIFEST_PROPERTY} property")
    board_id, manifest = found
    return manifest_to_board(manifest, board_id)


def generate_board_json(source: Path) -> bytes:
    return render_board(load_board(source))


# --- packages ---------------------------------------------------------------


def package_source_path(package_root: Path) -> Path:
    """``<package>/<package>.FCStd``: the only CAD source a package may carry."""
    package_root = Path(package_root)
    return package_root / f"{package_root.name}{SOURCE_SUFFIX}"


def is_cad_package(package_root: Path) -> bool:
    """True when the package carries its own CAD source (a regular file or not).

    Any filesystem entry at the source path counts, so a symlink or directory
    there is reported by the package validator instead of silently making the
    package look hand-authored.
    """
    source = package_source_path(package_root)
    return source.exists() or source.is_symlink()
