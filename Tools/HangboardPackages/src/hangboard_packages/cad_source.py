"""The FreeCAD authoring source of a CAD-backed hangboard package.

A CAD-backed package keeps all authored metadata in the adjacent flat
``Hangboards/<slug>.FCStd`` document-level string properties:

* ``HangTenBoardID`` -- the board ``id``;
* ``HangTenBoardManifest`` -- compact JSON of ``board.json`` *minus* ``id``, in
  the key order ``board.json`` is emitted in, with every number spelled as
  authored.

* ``HangTenSuspensionAuthoring`` -- cord topology, evidence and solver input;
* ``HangTenRopePhysics`` -- native feature selections and simulation parameters.

``board.json`` for such a package is generated from the FCStd and its compiled
``assets/suspension.json`` artifact at build time and
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
import copy
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

MANIFEST_PROPERTY = "HangTenBoardManifest"
ID_PROPERTY = "HangTenBoardID"
SUSPENSION_PROPERTY = "HangTenSuspensionAuthoring"
ROPE_PHYSICS_PROPERTY = "HangTenRopePhysics"
MAX_AUTHORING_BYTES = 1024 * 1024
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
        if not name or name in properties:
            raise ManifestError(f"duplicate or missing document property: {name!r}")
        value = None
        child = next(iter(prop), None)
        if child is not None and len(prop) == 1 and "value" in child.attrib \
                and (kind != "App::PropertyString" or child.tag == "String"):
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


def _finite_json(value, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ManifestError(f"{label} object keys must be strings")
            _finite_json(item, label)
    elif isinstance(value, list):
        for item in value:
            _finite_json(item, label)
    elif isinstance(value, (int, float)):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ManifestError(f"{label} numbers must be finite")
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise ManifestError(f"{label} must contain JSON values")


def _finite_vector(value, count: int, label: str) -> None:
    if not isinstance(value, list) or len(value) != count or any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        or not math.isfinite(item) for item in value
    ):
        raise ManifestError(f"{label} must contain {count} finite coordinates")


def _reject_generated_suspension_fields(value, path: str = SUSPENSION_PROPERTY) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"sourceSHA256", "modelSHA256", "translation", "cordContactPoints", "wrappedRoutes"}:
                raise ManifestError(f"{path}.{key} is generated and must not enter native authoring")
            _reject_generated_suspension_fields(item, f"{path}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_generated_suspension_fields(item, path)


def _suspension_entries(document: dict) -> list[dict]:
    """The three retained source layouts, without rewriting their identities."""
    if not isinstance(document, dict) or type(document.get("schemaVersion")) is not int:
        raise ManifestError("suspension authoring has invalid schema or members")
    if document.get("schemaVersion") == 2 and "entries" in document:
        if set(document) != {"schemaVersion", "entries"} \
                or not isinstance(document["entries"], list) or not document["entries"]:
            raise ManifestError("suspension authoring schema 2 requires a nonempty entries array")
        entries = document["entries"]
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or "schemaVersion" in entry:
                raise ManifestError("suspension authoring entries cannot carry schemaVersion")
            identity = (entry.get("presentationID"), entry.get("equipmentObjectID"))
            if any(not isinstance(value, str) or not value for value in identity if value is not None):
                raise ManifestError("suspension authoring entries require presentation/instance identifiers")
            if identity in seen:
                raise ManifestError("suspension authoring has duplicate presentation/instance entries")
            seen.add(identity)
        return entries
    if document.get("schemaVersion") not in (1, 2):
        raise ManifestError("suspension authoring has invalid schema or members")
    return [document]


def _entry_setups(entry: dict) -> list[dict]:
    if "instanceSuspensions" in entry:
        setups = entry["instanceSuspensions"]
        if not isinstance(setups, dict) or not setups or any(
            not isinstance(key, str) or not key or not isinstance(value, dict)
            for key, value in setups.items()
        ):
            raise ManifestError("instanceSuspensions authoring must identify reusable instances")
        return list(setups.values())
    if not isinstance(entry.get("suspension"), dict):
        raise ManifestError("suspension authoring payload must be an object")
    return [entry["suspension"]]


def validate_suspension_authoring(document: dict) -> dict:
    """Validate native input, rejecting every generated pose/hash field."""
    _finite_json(document, SUSPENSION_PROPERTY)
    _reject_generated_suspension_fields(document)
    entries = _suspension_entries(document)
    for entry in entries:
        instance_setup = "instanceSuspensions" in entry
        payload = "instanceSuspensions" if instance_setup else "suspension"
        required = {"presentationID", payload}
        optional = {"ropeSolver"}
        if entry is document:
            required.add("schemaVersion")
            if instance_setup != (document["schemaVersion"] == 2):
                raise ManifestError("suspension authoring has invalid schema or members")
        if not instance_setup:
            optional.add("equipmentObjectID")
        if not required <= set(entry) or set(entry) - required - optional:
            raise ManifestError("suspension authoring must not carry generated hashes or unknown members")
        if not isinstance(entry["presentationID"], str) or not entry["presentationID"] \
                or ("equipmentObjectID" in entry and (
                    not isinstance(entry["equipmentObjectID"], str) or not entry["equipmentObjectID"])):
            raise ManifestError("suspension authoring requires presentation/instance identifiers")
        solver = entry.get("ropeSolver", {"sectionPlane": "mouth-x"})
        for setup in _entry_setups(entry):
            if setup.get("type") not in {"twoBranchCord", "threadedLoopCord", "cadRoutedCord"}:
                raise ManifestError("native suspension authoring requires a supported CAD cord topology")
            poses = setup.get("canonicalPoses")
            if not isinstance(poses, dict) or not poses:
                raise ManifestError("suspension authoring requires nonempty canonicalPoses")
            for identifier, pose in poses.items():
                if not isinstance(identifier, str) or not identifier or not isinstance(pose, dict) \
                        or not {"rotation", "camera"} <= set(pose) \
                        or set(pose) - {"rotation", "camera", "offsetXZ"}:
                    raise ManifestError("canonical pose authoring permits rotation, camera and offsetXZ only; routes and translation are generated")
                _finite_vector(pose["rotation"], 4, "canonical pose rotation")
                if abs(math.hypot(*pose["rotation"]) - 1) > 1e-6:
                    raise ManifestError("canonical pose rotation must be normalized")
                camera = pose["camera"]
                if not isinstance(camera, dict) or set(camera) != {"viewDirection", "fitPadding"}:
                    raise ManifestError("canonical pose camera requires viewDirection and fitPadding")
                _finite_vector(camera["viewDirection"], 3, "canonical pose camera viewDirection")
                padding = camera["fitPadding"]
                if math.hypot(*camera["viewDirection"]) <= 1e-12 or isinstance(padding, bool) \
                        or not isinstance(padding, (int, float)) or padding <= 0:
                    raise ManifestError("canonical pose camera direction/padding must be nonzero and positive")
                if "offsetXZ" in pose:
                    _finite_vector(pose["offsetXZ"], 2, "canonical pose offsetXZ")
                    if any(round(component, 9) != component for component in pose["offsetXZ"]):
                        raise ManifestError("canonical pose offsetXZ must retain at most nine decimal places")
            if isinstance(solver, dict) and isinstance(solver.get("grooveGuides"), dict) \
                    and "sourceSHA256" in solver["grooveGuides"]:
                raise ManifestError("grooveGuides sourceSHA256 is generated and must not enter native authoring")
            _validate_suspension_solver(solver, {"suspension": setup}, authoring=True)
    return document


def validate_rope_physics_authoring(document: dict) -> dict:
    """Validate authored features/graphs; native export checks aperture geometry."""
    _finite_json(document, ROPE_PHYSICS_PROPERTY)
    if not isinstance(document, dict) or set(document) != {"bodyFeature", "channelFeatures", "profiles"}:
        raise ManifestError(f"{ROPE_PHYSICS_PROPERTY} requires bodyFeature, channelFeatures and profiles only")
    if not isinstance(document["bodyFeature"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", document["bodyFeature"]):
        raise ManifestError("rope physics bodyFeature must name a native CAD feature")
    channels = document["channelFeatures"]
    if not isinstance(channels, dict) or any(
        not isinstance(key, str) or not key or not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)
        for key, value in channels.items()
    ):
        raise ManifestError("rope physics channelFeatures must map identifiers to native CAD features")
    profiles = document["profiles"]
    if not isinstance(profiles, list) or not profiles or any(not isinstance(item, dict) for item in profiles):
        raise ManifestError("rope physics profiles must be a nonempty array of objects")
    # Share scalar, identity and provenance rules with the runtime descriptor.
    # Portal fit and channel-solid checks require native exported geometry.
    from . import rope_physics as physics
    try:
        for identifier in channels:
            physics._identifier(identifier)
        profile_instances = set()
        portal_ids = {f"{identifier}-{suffix}" for identifier in channels for suffix in ("front", "back")}
        for profile in physics._indexed(profiles).values():
            physics._closed(profile, {"id", "presentationID", "boardMass", "ropes"}, {"instanceID"})
            physics._identifier(profile["presentationID"])
            if "instanceID" in profile:
                physics._identifier(profile["instanceID"])
            identity = (profile["presentationID"], profile.get("instanceID"))
            if identity in profile_instances:
                raise ValueError("duplicate physics profile for presentation instance")
            profile_instances.add(identity)
            physics._estimate(profile["boardMass"])
            ropes = physics._indexed(profile["ropes"])
            if not ropes:
                raise ValueError("physics profile requires ropes")
            for rope in ropes.values():
                physics._closed(rope, {"id", "baselineRadius", "thicknessScale", "radius", "restLength", "lengthProvenance", "linearMass", "nodes", "edges"})
                radius = physics.derive_radius(rope["baselineRadius"], rope["thicknessScale"])
                if abs(physics._number(rope["radius"], "radius", True) - radius) > 1e-12:
                    raise ValueError("rope radius must match selected baseline scale")
                physics._number(rope["restLength"], "rope length", True)
                physics._provenance(rope["lengthProvenance"])
                physics._estimate(rope["linearMass"])
                nodes = physics._indexed(rope["nodes"])
                if len(nodes) < 2:
                    raise ValueError("rope graph requires two endpoints")
                for node in nodes.values():
                    if node.get("kind") == "portal":
                        physics._closed(node, {"id", "kind", "portalID"})
                        if physics._identifier(node["portalID"]) not in portal_ids:
                            raise ValueError("rope graph portal must identify a selected native channel")
                    elif node.get("kind") in ("support", "attachment"):
                        physics._closed(node, {"id", "kind", "point"})
                        physics._vector(node["point"])
                    else:
                        raise ValueError("invalid rope graph node kind")
                ordered = list(nodes)
                if nodes[ordered[0]]["kind"] != "support" or nodes[ordered[-1]]["kind"] not in ("support", "attachment"):
                    raise ValueError("rope graph must start at support and end at support or attachment")
                edges = rope["edges"]
                if not isinstance(edges, list) or len(edges) != len(nodes) - 1:
                    raise ValueError("rope graph edges must form one ordered continuous chain")
                for index, edge in enumerate(edges):
                    physics._closed(edge, {"from", "to", "kind"}, {"channelID", "winding"})
                    if edge["from"] != ordered[index] or edge["to"] != ordered[index + 1]:
                        raise ValueError("rope graph edges must follow node order")
                    if edge["kind"] == "channel":
                        channel = edge.get("channelID")
                        if "winding" in edge or physics._identifier(channel) not in channels \
                                or {nodes[edge[key]].get("portalID") for key in ("from", "to")} != {f"{channel}-front", f"{channel}-back"}:
                            raise ValueError("channel graph endpoints must match selected native channel portals")
                    elif edge["kind"] == "free":
                        if "channelID" in edge or edge.get("winding") not in (None, "clockwise", "counterclockwise"):
                            raise ValueError("invalid free rope edge")
                    else:
                        raise ValueError("invalid rope graph edge kind")
    except ValueError as error:
        raise ManifestError(f"{ROPE_PHYSICS_PROPERTY}: {error}") from error
    return document


def _load_authoring(source: Path, name: str, validator) -> dict | None:
    properties = document_properties_from_xml(read_document_xml(source))
    if name not in properties:
        return None
    kind, text = properties[name]
    if kind != "App::PropertyString" or text is None:
        raise ManifestError(f"{name} must be an App::PropertyString")
    if len(text.encode("utf-8")) > MAX_AUTHORING_BYTES:
        raise ManifestError(f"{name} exceeds its 1 MiB authoring size limit")
    try:
        return validator(loads(text))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise ManifestError(f"{name} is invalid JSON: {error}") from error


def load_suspension_authoring(source: Path) -> dict | None:
    return _load_authoring(source, SUSPENSION_PROPERTY, validate_suspension_authoring)


def load_rope_physics_authoring(source: Path) -> dict | None:
    return _load_authoring(source, ROPE_PHYSICS_PROPERTY, validate_rope_physics_authoring)


def _rewrite_authoring_properties(data: bytes, replacements: dict[str, str | None]) -> bytes:
    """Change only the document-level property text, leaving CAD XML intact."""
    root = _parse_document(data)
    props = root.find("Properties")
    if props is None:
        raise ManifestError("Document.xml has no document-level Properties")
    opening = re.search(rb"<Properties\b[^>]*>", data)
    if opening is None:
        raise ManifestError("Document.xml has no document-level Properties")
    start = opening.end()
    if opening.group().endswith(b"/>"):
        close, end, block = start, start, b""
    else:
        close = data.find(b"</Properties>", start)
        if close < 0:
            raise ManifestError("unterminated document-level Properties")
        end, block = close + len(b"</Properties>"), data[start:close]
    pattern = re.compile(rb"<Property\b[^>]*(?:/>|>.*?</Property>)", re.DOTALL)
    entries = [(match, ET.fromstring(match.group()).get("name")) for match in pattern.finditer(block)]
    indent_match = re.search(rb"\n([ \t]*)<[_]?Property\b", block)
    indent = indent_match.group(1) if indent_match else b"    "
    count = len(props.findall("Property"))
    for name, value in replacements.items():
        current = next((match for match, identifier in entries if identifier == name), None)
        new = b""
        if value is not None:
            escaped = value.translate(str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;", "\n": "&#10;", "\r": "&#13;", "\t": "&#9;"}))
            new = (f'<Property name="{name}" type="App::PropertyString" group="HangTen" '
                   f'attr="0" ro="0" hide="0" status="2097153"><String value="{escaped}"/></Property>').encode("utf-8")
        if current is not None:
            block = block[:current.start()] + new + block[current.end():]
            if value is None:
                count -= 1
        elif value is not None:
            following = next((match for match, identifier in entries if identifier and identifier > name), None)
            position = following.start() if following else len(block)
            block = block[:position] + new + b"\n" + indent + block[position:]
            count += 1
        entries = [(match, ET.fromstring(match.group()).get("name")) for match in pattern.finditer(block)]
    header = opening.group()
    if header.endswith(b"/>"):
        header = header[:-2] + b">"
    count_attribute = re.compile(rb"\bCount=([\"'])(.*?)\1")
    if count_attribute.search(header):
        header = count_attribute.sub(lambda match: b"Count=" + match.group(1) + str(count).encode() + match.group(1), header, count=1)
    else:
        header = header[:-1] + f' Count="{count}">'.encode()
    return data[:opening.start()] + header + block + b"</Properties>" + data[end:]


def embed_authoring(source: Path, *, suspension=None, rope_physics=None, destination: Path | None = None) -> bool:
    """Write both native properties; None omits one. Preserve all other members."""
    source = Path(source)
    destination = Path(destination) if destination is not None else source
    document = read_document_xml(source)
    properties = document_properties_from_xml(document)
    values = {}
    for name, value, validator in (
        (SUSPENSION_PROPERTY, suspension, validate_suspension_authoring),
        (ROPE_PHYSICS_PROPERTY, rope_physics, validate_rope_physics_authoring),
    ):
        if name in properties and (properties[name][0] != "App::PropertyString" or properties[name][1] is None):
            raise ManifestError(f"{name} must be an App::PropertyString")
        values[name] = None if value is None else render_manifest(validator(value))
        if values[name] is not None and len(values[name].encode("utf-8")) > MAX_AUTHORING_BYTES:
            raise ManifestError(f"{name} exceeds its 1 MiB authoring size limit")
    rewritten = _rewrite_authoring_properties(document, values)
    unchanged = all(properties.get(name, (None, None))[1] == text for name, text in values.items())
    if unchanged and destination == source:
        return False
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ManifestError("authoring destination must be a regular non-symlink file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        members = {info.filename: archive.read(info) for info in infos}
        comment = archive.comment
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(Path.cwd()))).name
    handle, filename = tempfile.mkstemp(prefix=f".{owner}-authoring-", suffix=SOURCE_SUFFIX, dir=destination.parent)
    os.close(handle)
    staged = Path(filename)
    try:
        staged.chmod(stat.S_IMODE(source.stat().st_mode))
        with zipfile.ZipFile(staged, "w") as out:
            out.comment = comment
            for info in infos:
                out.writestr(copy.copy(info), rewritten if info.filename == "Document.xml" else members[info.filename])
        inspect_archive(staged)
        with zipfile.ZipFile(staged) as check:
            if check.namelist() != [info.filename for info in infos] or any(
                check.read(name) != value for name, value in members.items() if name != "Document.xml"
            ):
                raise ManifestError("authoring rewrite changed a retained geometry archive member")
        if load_suspension_authoring(staged) != suspension or load_rope_physics_authoring(staged) != rope_physics:
            raise ManifestError("rewritten authoring does not read back")
        changed = not destination.is_file() or destination.read_bytes() != staged.read_bytes()
        if changed:
            os.replace(staged, destination)
        return changed
    finally:
        staged.unlink(missing_ok=True)


def materialize_suspension(authoring: dict, model_hashes: dict[str, str], source_sha256: str) -> dict:
    """Create native solver input, with hash bindings and unsolved Y=0 poses."""
    validate_suspension_authoring(authoring)
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ManifestError("suspension sourceSHA256 must be a SHA-256 digest")
    if not isinstance(model_hashes, dict):
        raise ManifestError("suspension model hashes must identify presentations")
    runtime = copy.deepcopy(authoring)
    for entry in _suspension_entries(runtime):
        model_hash = model_hashes.get(entry["presentationID"])
        if not isinstance(model_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", model_hash):
            raise ManifestError(f"missing or invalid modelSHA256 for presentation {entry['presentationID']!r}")
        entry["modelSHA256"] = model_hash
        solver = entry.get("ropeSolver")
        if isinstance(solver, dict) and "grooveGuides" in solver:
            solver["grooveGuides"]["sourceSHA256"] = source_sha256
        for setup in _entry_setups(entry):
            for identifier, pose in setup["canonicalPoses"].items():
                offset = pose.get("offsetXZ", [0, 0])
                setup["canonicalPoses"][identifier] = {
                    "rotation": pose["rotation"],
                    "translation": [LexemeFloat(f"{component:.9f}") for component in (offset[0], 0, offset[1])],
                    "camera": pose["camera"],
                }
    runtime["sourceSHA256"] = source_sha256
    return runtime


def _validate_route_cache(routes, identifiers: set[str], minimum_points: int) -> None:
    if not identifiers or not isinstance(routes, dict) or set(routes) != identifiers:
        raise ManifestError("compiled route cache must exactly match authored strand or passage IDs")
    for route in routes.values():
        if not isinstance(route, list) or len(route) < minimum_points:
            raise ManifestError(f"compiled route cache requires at least {minimum_points} points per route")
        for point in route:
            _finite_vector(point, 3, "compiled cord route")
        if any(math.dist(first, second) <= 1e-7 for first, second in zip(route, route[1:])):
            raise ManifestError("compiled route cache points must be distinct")


def _validate_compiled_routes(setup: dict, pose: dict) -> None:
    if setup["type"] == "cadRoutedCord":
        if "cordContactPoints" in pose:
            raise ManifestError("cadRoutedCord compiled cache must contain wrappedRoutes only")
        _validate_route_cache(pose.get("wrappedRoutes"), {strand["id"] for strand in setup["strands"]}, 3)
        return
    passages = setup.get("passages")
    if not isinstance(passages, dict) or set(passages) != {"left", "right"} \
            or any(not isinstance(side, list) for side in passages.values()) \
            or any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
                   or not item["id"] for side in passages.values() for item in side):
        raise ManifestError("connected cord route cache requires authored passage IDs")
    _validate_route_cache(pose.get("cordContactPoints"), {item["id"] for side in passages.values() for item in side}, 1)
    if "wrappedRoutes" in pose:
        if "meshWrap" not in setup:
            raise ManifestError("connected cord wrappedRoutes cache requires authored meshWrap")
        branches = setup.get("branches")
        if not isinstance(branches, list) or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in branches):
            raise ManifestError("meshWrap route cache requires authored branch IDs")
        _validate_route_cache(pose["wrappedRoutes"], {item["id"] for item in branches}, 3)


def merge_suspension_artifact(board: dict, package_root: Path, source: Path) -> dict:
    """Merge only a complete compiled suspension bound to current native input."""
    authoring = load_suspension_authoring(source)
    path = Path(package_root) / "assets/suspension.json"
    if authoring is None:
        if path.exists() or path.is_symlink():
            raise ManifestError("compiled suspension exists without native suspension authoring")
        return board
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_AUTHORING_BYTES:
        raise ManifestError("assets/suspension.json must be a regular compiled artifact of at most 1 MiB; run scripts/build-board-assets.sh")
    try:
        artifact = loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"compiled suspension is unreadable or invalid: {error}") from error
    _finite_json(artifact, "compiled suspension")
    source_hash = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    if not isinstance(artifact, dict) or artifact.get("sourceSHA256") != source_hash:
        raise ManifestError("compiled suspension sourceSHA256 does not match its native CAD source")
    projected = copy.deepcopy(artifact)
    projected.pop("sourceSHA256")
    entries = _suspension_entries({key: value for key, value in projected.items() if key != "modelSHA256"}) if "entries" in projected else [projected]
    authored_entries = _suspension_entries(authoring)
    if len(entries) != len(authored_entries):
        raise ManifestError("compiled suspension entries do not match native authoring")
    for entry, authored_entry in zip(entries, authored_entries):
        model_hash = entry.pop("modelSHA256", None)
        if not isinstance(model_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", model_hash):
            raise ManifestError("compiled suspension requires a modelSHA256 for each presentation")
        solver = entry.get("ropeSolver")
        if isinstance(solver, dict) and isinstance(solver.get("grooveGuides"), dict):
            if solver["grooveGuides"].pop("sourceSHA256", None) != source_hash:
                raise ManifestError("compiled grooveGuides sourceSHA256 does not match native CAD source")
        setups, authored_setups = _entry_setups(entry), _entry_setups(authored_entry)
        if len(setups) != len(authored_setups):
            raise ManifestError("compiled instance suspensions do not match native authoring")
        for setup, authored_setup in zip(setups, authored_setups):
            poses = setup.get("canonicalPoses")
            authored_poses = authored_setup["canonicalPoses"]
            if not isinstance(poses, dict) or set(poses) != set(authored_poses):
                raise ManifestError("compiled canonical poses do not match native authoring")
            for identifier, pose in poses.items():
                if not isinstance(pose, dict) or not {"rotation", "translation", "camera"} <= set(pose) \
                        or set(pose) - {"rotation", "translation", "camera", "cordContactPoints", "wrappedRoutes"}:
                    raise ManifestError("compiled suspension pose has invalid members")
                translation = pose.pop("translation")
                _finite_vector(translation, 3, "compiled pose translation")
                authored_pose = authored_poses[identifier]
                if [translation[0], translation[2]] != authored_pose.get("offsetXZ", [0, 0]):
                    raise ManifestError("compiled pose horizontal offset does not match native authoring")
                _validate_compiled_routes(authored_setup, pose)
                pose.pop("cordContactPoints", None)
                pose.pop("wrappedRoutes", None)
                if "offsetXZ" in authored_pose:
                    pose["offsetXZ"] = [translation[0], translation[2]]
    if projected != authoring:
        raise ManifestError("compiled suspension payload does not match native authoring; rebuild runtime assets")
    document = {key: value for key, value in artifact.items() if key != "sourceSHA256"}
    if "entries" in document:
        for entry in document["entries"]:
            schema = 2 if "instanceSuspensions" in entry else 1
            board = _merge_suspension_entry(board, package_root, {"schemaVersion": schema, **entry})
        return board
    return _merge_suspension_entry(board, package_root, document)


def _validate_suspension_solver(solver: dict, document: dict, *, authoring: bool = False) -> None:
    if isinstance(solver, dict) and "collisionFeature" in solver and (
        not isinstance(solver["collisionFeature"], str)
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", solver["collisionFeature"])
    ):
        raise ManifestError("ropeSolver collisionFeature must name a native CAD feature")
    if isinstance(solver, dict) and solver.get("method") == "nativeRoutes" and "terminalsByPoseID" in solver:
        overrides = solver["terminalsByPoseID"]
        suspension = document.get("suspension")
        poses = suspension.get("canonicalPoses") if isinstance(suspension, dict) else None
        if not isinstance(overrides, dict) or not overrides or not isinstance(poses, dict) \
                or any(not isinstance(key, str) or not key or key not in poses for key in overrides):
            raise ManifestError("nativeRoutes terminalsByPoseID must identify existing canonical poses")
        if "grooveGuides" in solver:
            raise ManifestError("nativeRoutes pose terminals cannot be combined with grooveGuides")
        # Validate each effective station map against this instance's topology.
        # These authoring-only settings never enter the generated board.
        base_solver = {key: value for key, value in solver.items() if key != "terminalsByPoseID"}
        for terminals in overrides.values():
            _validate_suspension_solver({**base_solver, "terminalsByStrandID": terminals}, document, authoring=authoring)
        solver = base_solver
    if isinstance(solver, dict) and solver.get("method") == "nativeRoutes":
        if set(solver) - {"method", "clearance", "terminalsByStrandID", "supportDirection", "sectionPlane", "tightening", "pathSearch", "grooveGuides", "collisionFeature"} or not {"method", "clearance", "terminalsByStrandID"} <= set(solver) \
                or isinstance(solver["clearance"], bool) \
                or not isinstance(solver["clearance"], (int,float)) or not math.isfinite(solver["clearance"]) \
                or not 0 < solver["clearance"] <= .01 \
                or not isinstance(solver["terminalsByStrandID"], dict) or not solver["terminalsByStrandID"] \
                or isinstance(solver.get("supportDirection", 1), bool) or solver.get("supportDirection", 1) not in (-1,1) \
                or solver.get("sectionPlane", "fixed") not in ("fixed", "anchor"):
            raise ManifestError("suspension.json nativeRoutes solver settings are invalid")
        if "pathSearch" in solver and solver["pathSearch"] != "aStar":
            raise ManifestError("nativeRoutes pathSearch must be aStar when present")
        if "tightening" in solver and solver["tightening"] != "coupled3D":
            raise ManifestError("nativeRoutes tightening must be coupled3D when present")
        for entry in solver["terminalsByStrandID"].values():
            if not isinstance(entry, dict) or not {"points", "planeNormal"} <= set(entry) \
                    or set(entry) - {"points", "planeNormal", "planeAxis", "mouthAxis"}:
                raise ManifestError("nativeRoutes requires terminal stations and section normals")
            def finite_vector(value):
                return isinstance(value, list) and len(value) == 3 and all(
                    isinstance(component, (int, float)) and not isinstance(component, bool)
                    and math.isfinite(component) for component in value)
            if not isinstance(entry["points"], list) or len(entry["points"]) not in (1, 2) \
                    or not all(finite_vector(point) for point in entry["points"]) \
                    or not finite_vector(entry["planeNormal"]) \
                    or math.hypot(*entry["planeNormal"]) <= 1e-12 \
                    or ("planeAxis" in entry and (not finite_vector(entry["planeAxis"])
                        or math.hypot(*entry["planeAxis"]) <= 1e-12)) \
                    or ("mouthAxis" in entry and (not finite_vector(entry["mouthAxis"])
                        or math.hypot(*entry["mouthAxis"]) <= 1e-12)):
                raise ManifestError("nativeRoutes stations and nonzero plane normals must be finite 3D vectors")
        suspension = document.get("suspension")
        strands = suspension.get("strands") if isinstance(suspension, dict) else None
        if not isinstance(suspension, dict) or suspension.get("type") != "cadRoutedCord" \
                or not isinstance(strands, list) or not strands \
                or any(not isinstance(strand, dict) or not isinstance(strand.get("id"), str)
                    or not strand["id"] or strand.get("kind") not in ("lead", "loop", "segment") for strand in strands) \
                or len({strand["id"] for strand in strands}) != len(strands) \
                or set(solver["terminalsByStrandID"]) != {strand["id"] for strand in strands}:
            raise ManifestError("nativeRoutes terminals must exactly match cadRoutedCord strands")
        if any(len(solver["terminalsByStrandID"][strand["id"]]["points"]) != (1 if strand["kind"] == "lead" else 2)
               for strand in strands):
            raise ManifestError("nativeRoutes needs one terminal per lead and two stations per loop or segment")
        if "grooveGuides" in solver:
            guides=solver["grooveGuides"]
            poses=suspension.get("canonicalPoses",{})
            required_guides = {"byPoseID"} if authoring else {"sourceSHA256", "byPoseID"}
            if not isinstance(guides,dict) or set(guides)!=required_guides \
                    or (not authoring and (not isinstance(guides.get("sourceSHA256"),str) or not re.fullmatch(r"[0-9a-f]{64}",guides["sourceSHA256"]))) \
                    or not isinstance(guides.get("byPoseID"),dict) or set(guides["byPoseID"])!=set(poses) \
                    or solver.get("sectionPlane")!="anchor" or solver.get("supportDirection",1)!=1 \
                    or "tightening" in solver or any(x["kind"]!="lead" for x in strands):
                raise ManifestError("native grooveGuides requires exact source/pose bindings and independent anchor-plane leads")
            identifiers={x["id"] for x in strands}
            for selections in guides["byPoseID"].values():
                if not isinstance(selections,dict) or set(selections)!=identifiers:
                    raise ManifestError("native grooveGuides must select every strand in every pose")
                for identifier,selection in selections.items():
                    if not isinstance(selection,dict) or set(selection)!={"feature","boreFeature","exitSign"} \
                            or any(not isinstance(selection.get(key),str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",selection[key]) for key in ("feature","boreFeature")) \
                            or isinstance(selection.get("exitSign"),bool) or selection.get("exitSign") not in (-1,1) \
                            or "mouthAxis" not in solver["terminalsByStrandID"][identifier]:
                        raise ManifestError("native grooveGuides requires native feature names, finite exit choice and mouth axes")
        if "tightening" in solver and (solver.get("sectionPlane", "fixed") != "anchor" or any(
                strand["kind"] != "lead" or "mouthAxis" not in solver["terminalsByStrandID"][strand["id"]]
                for strand in strands)):
            raise ManifestError("nativeRoutes tightening requires anchor sections and front-entry leads only")
        if any("mouthAxis" in solver["terminalsByStrandID"][strand["id"]]
               and (strand["kind"] != "lead" or solver.get("sectionPlane", "fixed") != "anchor") for strand in strands):
            raise ManifestError("nativeRoutes mouthAxis requires a lead in an anchor section plane")
    elif not isinstance(solver, dict) or "sectionPlane" not in solver \
            or set(solver) - {"sectionPlane", "channelProfile", "collisionFeature"} \
            or solver["sectionPlane"] not in ("mouth-x", "anchor") \
            or ("channelProfile" in solver and (solver["channelProfile"] != "rectangular" or solver["sectionPlane"] != "mouth-x")):
        raise ManifestError("suspension.json ropeSolver requires mouth-x or anchor; rectangular channelProfile requires mouth-x")


def _merge_suspension_entry(board: dict, package_root: Path, document: dict) -> dict:
    instance_setup = isinstance(document, dict) and document.get("schemaVersion") == 2
    payload_key = "instanceSuspensions" if instance_setup else "suspension"
    required = {"schemaVersion", "presentationID", "modelSHA256", payload_key}
    optional = {"ropeSolver"} if instance_setup else {"ropeSolver", "equipmentObjectID"}
    if not isinstance(document, dict) or not required <= set(document) \
            or set(document) - required - optional or document["schemaVersion"] not in (1, 2):
        raise ManifestError("suspension.json has invalid schema or members")
    # Authoring-only settings for Tools/HangboardCAD/solve_threaded_rope.py;
    # never merged into board.json.
    solver = document.get("ropeSolver", {"sectionPlane": "mouth-x"})
    if not isinstance(document[payload_key], dict):
        raise ManifestError("suspension.json suspension payload must be an object")
    setups = document[payload_key].values() if instance_setup else [document["suspension"]]
    for setup in setups:
        _validate_suspension_solver(solver, {"suspension": setup})
    presentation_id = document["presentationID"]
    model_hash = document["modelSHA256"]
    if not isinstance(presentation_id, str) or not isinstance(model_hash, str) \
            or not re.fullmatch(r"[0-9a-f]{64}", model_hash) \
            or not isinstance(document[payload_key], dict):
        raise ManifestError("suspension.json has invalid presentationID, modelSHA256, or suspension")
    presentations = board.get("presentations")
    if not isinstance(presentations, list):
        raise ManifestError("CAD board has no presentations for suspension.json")
    selected = [item for item in presentations if isinstance(item, dict) and item.get("id") == presentation_id]
    if len(selected) != 1:
        raise ManifestError("suspension.json presentationID must identify one CAD presentation")
    media = selected[0].get("media")
    if not isinstance(media, dict) or media.get("type") != "model" :
        raise ManifestError("suspension.json requires a model presentation without embedded suspension")
    equipment_id = document.get("equipmentObjectID")
    instance = None
    if equipment_id is not None:
        matches = [item for item in media.get("instances", []) if item.get("equipmentObjectID") == equipment_id]
        if len(matches) != 1:
            raise ManifestError("suspension.json equipmentObjectID must identify one model instance")
        instance = matches[0]
    target = instance if instance is not None else media
    if "suspension" in target:
        raise ManifestError("suspension.json requires a target without embedded suspension")
    descriptor_path = media.get("descriptorPath")
    if not isinstance(descriptor_path, str) or safe_member(descriptor_path) != descriptor_path \
            or not descriptor_path.startswith("assets/"):
        raise ManifestError("suspension.json presentation has an invalid descriptorPath")
    descriptor_file = Path(package_root) / descriptor_path
    if descriptor_file.is_symlink() or not descriptor_file.is_file():
        raise ManifestError("suspension.json descriptor must be a regular file; run scripts/build-board-assets.sh to generate runtime assets")
    try:
        descriptor = loads(descriptor_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"suspension.json descriptor is unreadable or invalid: {error}") from error
    if not isinstance(descriptor, dict) or descriptor.get("modelSHA256") != model_hash:
        raise ManifestError("suspension.json modelSHA256 does not match its descriptor")
    if instance_setup:
        import copy
        instances = media.get("instances")
        setups = document["instanceSuspensions"]
        if not isinstance(instances, list) or len(instances) != 2 or not all(
            isinstance(item, dict) and isinstance(item.get("equipmentObjectID"), str)
            and item["equipmentObjectID"] for item in instances
        ):
            raise ManifestError("instanceSuspensions requires exactly two reusable instances with valid equipment IDs")
        if len(setups) != len(instances) or set(setups) != {item["equipmentObjectID"] for item in instances}:
            raise ManifestError("instanceSuspensions must identify every reusable instance exactly once")
        if any("suspension" in item for item in instances) or not all(isinstance(value, dict) for value in setups.values()):
            raise ManifestError("instanceSuspensions cannot replace embedded suspension")
        merged = copy.deepcopy(board)
        target = next(item for item in merged["presentations"] if item["id"] == presentation_id)
        for instance in target["media"]["instances"]:
            instance["suspension"] = copy.deepcopy(setups[instance["equipmentObjectID"]])
        return merged
    merged = dict(board)
    merged_presentations = []
    for presentation in presentations:
        if presentation is selected[0]:
            updated = dict(presentation)
            updated_media = {}
            for key, value in media.items():
                if key == "instances" and instance is not None:
                    updated_media[key] = [dict(item, suspension=document["suspension"]) if item is instance else item for item in value]
                elif key == "orientation" and instance is None:
                    updated_media["suspension"] = document["suspension"]
                    updated_media[key] = value
                else:
                    updated_media[key] = value
            if instance is None and "suspension" not in updated_media:
                updated_media["suspension"] = document["suspension"]
            updated["media"] = updated_media
            merged_presentations.append(updated)
        else:
            merged_presentations.append(presentation)
    merged["presentations"] = merged_presentations
    return merged


def generate_board_json(source: Path, package_root: Path | None = None) -> bytes:
    source = Path(source)
    board = load_board(source)
    package_root = Path(package_root) if package_root is not None else source.parent / source.stem
    board = merge_suspension_artifact(board, package_root, source)
    return render_board(board)


# --- packages ---------------------------------------------------------------


def package_source_path(package_root: Path) -> Path:
    """``Hangboards/<slug>.FCStd``: the native source adjacent to the package."""
    package_root = Path(package_root)
    return package_root.parent / f"{package_root.name}{SOURCE_SUFFIX}"


def is_cad_package(package_root: Path) -> bool:
    """True when the package has an adjacent flat CAD source (regular or not).

    Any filesystem entry at the source path counts, so a symlink or directory
    there is reported by the package validator instead of silently making the
    package look hand-authored.
    """
    source = package_source_path(package_root)
    return source.exists() or source.is_symlink()
