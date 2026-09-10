"""Shared, fail-closed verification for model-first board packages.

The package and descriptor checks in this module are deliberately usable on a
machine without Blender.  Blender is imported only once all cheap filesystem,
inventory, and descriptor-input checks have passed.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
import zipfile


@dataclass(frozen=True)
class MaterialPolicy:
    name: str = "none"
    require_image: bool = False
    require_embedded_texture: bool = False
    texture_suffixes: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})
    texture_name: str | None = None
    texture_path: Path | None = None

    @classmethod
    def canonical_wood(cls) -> "MaterialPolicy":
        path = Path(__file__).resolve().parent / "assets" / "canonical-neutral-wood.png"
        return cls("canonical-wood", True, True, frozenset({".png"}), path.name, path)


@dataclass(frozen=True)
class BoardProbe(Protocol):
    id: str

    def run(self, imported: object, config: "ModelVerificationConfig") -> object: ...


@dataclass(frozen=True)
class SuspensionVerificationPolicy:
    """Extension point reserved for the shared suspension verifier."""

    required: bool = True


@dataclass(frozen=True)
class ModelVerificationConfig:
    board_id: str
    board_json: Path
    package_relative_assets: frozenset[str]
    expected_hold_ids: tuple[str, ...]
    expected_position_ids: tuple[str, ...] = ()
    triangle_ceiling: int | None = None
    required_roles: frozenset[str] = frozenset({"body", "hold"})
    forbidden_name_tokens: tuple[str, ...] = ()
    material_policy: MaterialPolicy = field(default_factory=MaterialPolicy.canonical_wood)
    suspension_policy: SuspensionVerificationPolicy | None = None
    board_probes: tuple[BoardProbe, ...] = ()


@dataclass(frozen=True)
class VerificationReport:
    board_id: str
    checks: Mapping[str, object] = field(default_factory=dict)
    command: tuple[str, ...] = ()
    options: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"boardID": self.board_id, "checks": dict(self.checks)}
        if self.command:
            result["command"] = list(self.command)
        if self.options:
            result["options"] = dict(self.options)
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n"


@dataclass(frozen=True)
class _ImportedModel:
    scene: object
    nodes: tuple[object, ...]
    snapshot: object
    source_node_ids: Mapping[str, str]
    descriptor: Mapping[str, object]
    model_path: Path


def _regular(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")
    return path.resolve()


def _ordered_hold_ids(board_json: Path) -> tuple[str, ...]:
    path = _regular(board_json, "board JSON")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"board JSON is not readable valid JSON: {path}") from error
    if not isinstance(document, Mapping) or not isinstance(document.get("holds"), list):
        raise ValueError("logical inventory must contain a holds array")
    ids = tuple(item.get("id") if isinstance(item, Mapping) else None for item in document["holds"])
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("logical inventory contains invalid or duplicate hold IDs")
    return ids


def _asset_inventory(package: Path) -> frozenset[str]:
    assets = package / "assets"
    if assets.is_symlink() or not assets.is_dir():
        raise ValueError(f"asset inventory requires regular assets directory: {assets}")
    entries = list(assets.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("asset inventory may contain only regular files")
    if any(path.is_dir() for path in entries if path.name == "empty"):
        raise ValueError("asset inventory contains an empty nested directory")
    files = {path.relative_to(package).as_posix() for path in entries if path.is_file()}
    return frozenset(files)


def _descriptor(path: Path) -> dict[str, object]:
    try:
        value = json.loads(_regular(path, "descriptor").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"descriptor is not readable valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError("descriptor must be an object")
    return dict(value)


def _check_archive(model_path: Path, policy: MaterialPolicy) -> list[str]:
    try:
        with zipfile.ZipFile(model_path) as archive:
            members = archive.namelist()
            textures = [name for name in members if Path(name).suffix.lower() in policy.texture_suffixes]
            if policy.texture_name is not None:
                matches = [name for name in textures if Path(name).name == policy.texture_name]
                if len(matches) != 1:
                    raise ValueError(f"material policy requires texture {policy.texture_name}")
                if policy.texture_path is None or archive.read(matches[0]) != policy.texture_path.read_bytes():
                    raise ValueError("material policy canonical texture bytes do not match")
            if policy.require_embedded_texture and (not textures or any(not archive.read(name) for name in textures)):
                raise ValueError("material policy requires non-empty embedded textures")
            return textures
    except zipfile.BadZipFile as error:
        raise ValueError("USDZ is not a readable archive") from error


def verify_model_package(package: Path, config: ModelVerificationConfig, *, render: bool = False) -> VerificationReport:
    package = Path(package)
    if package.is_symlink() or not package.is_dir():
        raise ValueError(f"package must be a regular directory: {package}")
    actual_assets = _asset_inventory(package)
    if actual_assets != config.package_relative_assets:
        raise ValueError(f"asset inventory mismatch: expected {sorted(config.package_relative_assets)}, got {sorted(actual_assets)}")
    actual_ids = _ordered_hold_ids(config.board_json)
    if actual_ids != tuple(config.expected_hold_ids) or len(set(config.expected_hold_ids)) != len(config.expected_hold_ids):
        raise ValueError("logical inventory IDs are missing, unknown, or reordered")
    model_path = package / "assets/primary.usdz"
    descriptor_path = package / "assets/primary.model.json"
    textures = _check_archive(model_path, config.material_policy)
    descriptor = _descriptor(descriptor_path)
    if descriptor.get("modelSHA256") != hashlib.sha256(model_path.read_bytes()).hexdigest():
        raise ValueError("descriptor model hash does not match USDZ bytes")
    # Blender-only work begins here.  This import is intentionally unreachable
    # for malformed package fixtures and keeps report tests bpy-free.
    try:
        import compile_model_package as compiler
        bpy = compiler._bpy()
    except (ImportError, RuntimeError) as error:
        raise RuntimeError("model package verification requires Blender after core checks pass") from error
    bpy.ops.wm.read_factory_settings(use_empty=True)
    imported_scene = bpy.ops.wm.usd_import(filepath=str(model_path), merge_parent_xform=True)
    if "FINISHED" not in imported_scene:
        raise ValueError("USDZ reimport did not finish")
    scene = bpy.context.scene
    bindings = compiler.validate_tagged_scene(scene, frozenset(actual_ids), imported=True)
    mesh_objects = [obj for obj in scene.objects if getattr(obj, "type", None) == "MESH"]
    if any(token.lower() in obj.name.lower() for obj in mesh_objects for token in config.forbidden_name_tokens):
        raise ValueError("forbidden mesh name token in imported model")
    if not config.required_roles.issubset({binding.role for binding in bindings}):
        raise ValueError("imported model is missing a required mesh role")
    if len(mesh_objects) != len(bindings):
        raise ValueError("imported model contains unbound mesh geometry")
    snapshot = compiler._snapshot_scene(scene, bindings, transform_to_board_frame=True,
                                        require_imported_materials=config.material_policy.require_image,
                                        require_triangles=True)
    correspondence = compiler._imported_source_node_ids(scene, bindings)
    triangles = sum(max(0, len(polygon.vertices) - 2) for obj in mesh_objects for polygon in obj.data.polygons)
    if config.triangle_ceiling is not None and triangles > config.triangle_ceiling:
        raise ValueError("imported model exceeds triangle ceiling")
    from model_descriptor import compile_descriptor
    regenerated = compile_descriptor(model_path.read_bytes(), snapshot.nodes,
                                     snapshot.vertices_by_node_id, frozenset(actual_ids)).to_json()
    if regenerated != descriptor:
        raise ValueError("descriptor is not regenerated from imported vertices")
    imported = _ImportedModel(scene, tuple(bindings), snapshot, correspondence, descriptor, model_path)
    # Preserve the legacy authored verifier contract without making names the
    # source of identity: aliases are copied from validated bindings and the
    # review ray helper sees the canonical board frame.
    axis_transform = compiler._board_axis_transform()
    by_name = {obj.name: obj for obj in scene.objects}
    for binding in bindings:
        obj = by_name[binding.node_id]
        obj["role"] = binding.role
        if binding.hold_id is not None:
            obj["hold_id"] = binding.hold_id
        obj.matrix_world = axis_transform @ obj.matrix_world
    probe_results = []
    for probe in config.board_probes:
        result = probe.run(imported, config)
        probe_results.append(result if isinstance(result, Mapping) else {"id": probe.id, "result": result})
    report = {"modelSHA256": descriptor["modelSHA256"], "descriptorSHA256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
              "logicalHoldIDs": list(actual_ids), "sourcePieceCorrespondence": dict(correspondence),
              "triangles": triangles, "triangleCeiling": config.triangle_ceiling,
              "embeddedTextureMembers": textures, "probeResults": probe_results, "rendersSkipped": not render}
    return VerificationReport(config.board_id, report, options={"render": render})
