"""Fail-closed, read-only validation before restoring a native FCStd document."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

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
NODE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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
        if stream.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
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


def validate_bindings(nodes: Sequence[Mapping], board: Mapping, version: int,
                      slots: Sequence[str]) -> None:
    """Require explicit, complete role bindings; never infer meaning from geometry."""
    if isinstance(version, bool) or version not in {1, 2}:
        raise ValueError("descriptor version must be 1 or 2")
    if board.get("schemaVersion") != 3 or not isinstance(board.get("id"), str):
        raise ValueError("board metadata must be schema-v3 with an ID")
    contacts = board.get("contacts")
    if not isinstance(contacts, list) or not contacts:
        raise ValueError("board contacts must be a nonempty list")
    ids = [c.get("id") if isinstance(c, Mapping) else None for c in contacts]
    if any(not isinstance(c, str) or not c for c in ids) or len(ids) != len(set(ids)):
        raise ValueError("invalid or duplicate board contact IDs")
    if version == 1 and slots:
        raise ValueError("v1 source must not declare reusable slots")
    if version == 2 and (not slots or any(not isinstance(s, str) or not s for s in slots)
                         or len(slots) != len(set(slots))):
        raise ValueError("invalid reusable slot inventory")
    names, bound = set(), set()
    bodies = 0
    key = "contact" if version == 1 else "slot"
    for node in nodes:
        name, role = node.get("id"), node.get("role")
        if (not isinstance(name, str) or not NODE_ID.fullmatch(name) or name in names
                or role not in {"body", "contact", "attachment"}):
            raise ValueError("invalid/duplicate node ID or role")
        if set(node) - {"id", "role", key}:
            raise ValueError("unexpected node binding fields")
        names.add(name)
        if role == "contact":
            value = node.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError("contact node requires its explicit binding")
            bound.add(value)
        elif key in node:
            raise ValueError("non-contact node cannot carry contact binding")
        bodies += role == "body"
    expected = set(ids if version == 1 else slots)
    if not bodies or bound != expected:
        raise ValueError("source body/contact inventory does not match board/slots")
