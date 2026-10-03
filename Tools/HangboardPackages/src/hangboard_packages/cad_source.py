"""The FreeCAD authoring source of a CAD-backed hangboard package.

A CAD-backed package (``Hangboards/<slug>/<slug>.FCStd``) keeps its board
metadata inside the FCStd, in two document-level string properties:

* ``HangTenBoardID`` -- the board ``id``;
* ``HangTenBoardManifest`` -- compact JSON of ``board.json`` *minus* ``id``, in
  the key order ``board.json`` is emitted in, with every number spelled as
  authored.

``board.json`` for such a package is generated from the FCStd and an optional
adjacent ``suspension.json`` authoring sidecar at build time and
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
import math
from pathlib import Path, PurePosixPath
import re
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


def merge_suspension_sidecar(board: dict, package_root: Path) -> dict:
    """Overlay authoring-only suspension data onto a CAD-generated board."""
    path = Path(package_root) / "suspension.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ManifestError("suspension.json must be a regular file of at most 1 MiB")
    try:
        document = loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"suspension.json is unreadable or invalid: {error}") from error
    if isinstance(document, dict) and document.get("schemaVersion") == 2 and "entries" in document:
        if set(document) != {"schemaVersion", "entries"} or not isinstance(document["entries"], list) or not document["entries"]:
            raise ManifestError("suspension.json schema 2 requires a nonempty entries array")
        seen = set()
        for entry in document["entries"]:
            if not isinstance(entry, dict) or "schemaVersion" in entry \
                    or not isinstance(entry.get("presentationID"), str) \
                    or not entry["presentationID"] \
                    or ("equipmentObjectID" in entry and (
                        not isinstance(entry["equipmentObjectID"], str) or not entry["equipmentObjectID"])):
                raise ManifestError("suspension.json entries require presentation/instance identifiers and no schemaVersion")
            identity = (entry.get("presentationID"), entry.get("equipmentObjectID"))
            if identity in seen:
                raise ManifestError("suspension.json has duplicate presentation/instance entries")
            seen.add(identity)
            board = _merge_suspension_entry(board, package_root, {"schemaVersion": 1, **entry})
        return board
    return _merge_suspension_entry(board, package_root, document)


def _validate_suspension_solver(solver: dict, document: dict) -> None:
    if isinstance(solver, dict) and solver.get("method") == "nativeRoutes":
        if set(solver) - {"method", "clearance", "terminalsByStrandID", "supportDirection", "sectionPlane", "tightening", "pathSearch", "grooveGuides"} or not {"method", "clearance", "terminalsByStrandID"} <= set(solver) \
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
            if not isinstance(guides,dict) or set(guides)!={"sourceSHA256","byPoseID"} \
                    or not isinstance(guides.get("sourceSHA256"),str) or not re.fullmatch(r"[0-9a-f]{64}",guides["sourceSHA256"]) \
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
            or set(solver) - {"sectionPlane", "channelProfile"} \
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
        raise ManifestError("suspension.json descriptor must be a regular file")
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


def generate_board_json(source: Path) -> bytes:
    source = Path(source)
    board = load_board(source)
    sidecar = source.parent / "suspension.json"
    if sidecar.exists() or sidecar.is_symlink():
        board = merge_suspension_sidecar(board, source.parent)
    return render_board(board)


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
