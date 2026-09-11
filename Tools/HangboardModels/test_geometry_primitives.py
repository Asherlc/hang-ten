"""Semantic snapshot regression tests for the shared Blender geometry helpers.

Run with Blender from the repository root::

    blender --background --factory-startup --python-exit-code 1 \
      --python Tools/HangboardModels/test_geometry_primitives.py

The test deliberately snapshots authored data rather than image pixels.  Review
objects are explicitly marked non-exportable and are required to remain outside
the model set.
"""

from __future__ import annotations

import atexit
import json
import hashlib
from collections import Counter
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

if bpy is not None:
    from geometry_primitives import (  # noqa: E402
        create_passage,
        create_recess,
        create_rounded_body,
        create_stepped_edge,
        make_review_rig,
        semantic_snapshot,
        split_contact_surface,
        tag_piece,
    )


# The baseline is extracted read-only from the pre-task commit during every
# Blender run.  Do not replace this with manually copied fingerprints: that
# would only label a baseline rather than prove its source and execution.
PRE_MIGRATION_BASELINE_COMMIT = "cbcee2850abe5221fdcf24d8fdf2ce822c86f67f"
HISTORICAL_GENERATORS = {
    "beastmaker": Path("Tools/HangboardModels/beastmaker_1000.py"),
    "compact": Path("Tools/HangboardModels/wood_grips_compact_ii.py"),
}
# These are every non-standard-library project input read while the historical
# generators build their compiler-only scenes.  They must remain byte-identical
# to the pre-task commit, otherwise an exact historical generator source alone
# would not establish a genuine historical semantic baseline.
HISTORICAL_DEPENDENCIES = {
    "beastmaker": (
        Path("Tools/HangboardModels/canonical_neutral_wood.py"),
        Path("Hangboards/beastmaker-1000/board.json"),
    ),
    "compact": (
        Path("Tools/HangboardModels/canonical_neutral_wood.py"),
        Path("Hangboards/metolius-wood-grips-compact-ii/board.json"),
    ),
}
_OWNED_RESOURCE_DIRECTORIES = set()


class _OwnedResourceDirectory:
    """Owned `.context` directory with normal and interpreter-exit cleanup."""

    def __init__(self, repo: Path, label: str):
        self.path = Path(tempfile.mkdtemp(prefix=f"{repo.name}-{label}-", dir=repo / ".context"))
        self._closed = False
        self.path.joinpath("ownership.json").write_text(json.dumps({
            "owner": repo.name,
            "resources": [str(self.path)],
            "external_resources": [],
        }, indent=2) + "\n", encoding="utf-8")
        _OWNED_RESOURCE_DIRECTORIES.add(self)

    def cleanup(self) -> None:
        if self._closed:
            return
        shutil.rmtree(self.path, ignore_errors=False)
        self._closed = True
        _OWNED_RESOURCE_DIRECTORIES.discard(self)
        assert not self.path.exists(), f"owned resource remains: {self.path}"


@atexit.register
def _cleanup_owned_resource_directories() -> None:
    # `finally` provides immediate verification; this protects an unexpected
    # interpreter exit after an assertion or Blender script failure.
    for resource in list(_OWNED_RESOURCE_DIRECTORIES):
        resource.cleanup()


def _reset() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                       bpy.data.lights, bpy.data.images):
        for item in list(datablocks):
            if item.users == 0:
                datablocks.remove(item)


def _material(name: str):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    return material


def _image_material(name: str):
    material = _material(name)
    image = bpy.data.images.new(name + " image", width=1, height=1)
    image.generated_color = (0.2, 0.3, 0.4, 1.0)
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    shader = material.node_tree.nodes.get("Principled BSDF")
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    return material


def _records(snapshot):
    return {item["name"]: item for item in snapshot["objects"]}


def _semantic_fingerprints(snapshot):
    groups = {
        "topology": ("name", "vertexCount", "topologyCount", "vertexHash", "topologyHash"),
        "transforms": ("name", "transform"),
        "bindings": ("name", "role", "holdID", "materials", "polygonMaterialIndices", "polygonMaterials"),
        "materialNodes": ("name", "materialNodes"),
    }
    result = {}
    for group, keys in groups.items():
        payload = {"objects": [{key: item[key] for key in keys}
                                for item in snapshot["objects"] if item["export"]]}
        if group == "materialNodes":
            payload["materialImageBytes"] = snapshot["materialImageBytes"]
        result[group] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).stdout


def _historical_generator_source(repo: Path, baseline_key: str) -> tuple[Path, bytes, dict[str, str]]:
    """Read and validate the exact pre-task generator without mutating Git."""
    resolved_commit = _git_bytes(repo, "rev-parse", "--verify",
                                 PRE_MIGRATION_BASELINE_COMMIT + "^{commit}").strip().decode()
    assert resolved_commit == PRE_MIGRATION_BASELINE_COMMIT, resolved_commit
    relative_path = HISTORICAL_GENERATORS[baseline_key]
    object_spec = f"{resolved_commit}:{relative_path.as_posix()}"
    _git_bytes(repo, "cat-file", "-e", object_spec)
    blob = _git_bytes(repo, "rev-parse", "--verify", object_spec).strip().decode()
    source = _git_bytes(repo, "show", object_spec)
    assert source and source == _git_bytes(repo, "cat-file", "blob", blob), object_spec
    for dependency in HISTORICAL_DEPENDENCIES[baseline_key]:
        historical = _git_bytes(repo, "show", f"{resolved_commit}:{dependency.as_posix()}")
        assert (repo / dependency).read_bytes() == historical, (
            "historical generator dependency changed", dependency)
    return relative_path, source, {
        "commit": resolved_commit,
        "generator": relative_path.as_posix(),
        "blob": blob,
        "sourceSHA256": hashlib.sha256(source).hexdigest(),
    }


def _run_historical_generator_snapshot(repo: Path, baseline_key: str, output: Path,
                                       extra_args=()):
    """Execute exact `cbcee285` source in memory and snapshot its fresh scene."""
    relative_path, source, provenance = _historical_generator_source(repo, baseline_key)
    script = repo / relative_path
    original_argv = sys.argv
    try:
        _reset()
        # The source comes from Git, but the canonical __file__ preserves the
        # historical generator's documented Path(__file__) root contract.
        sys.argv = [str(script), "--", "--output", str(output), *extra_args]
        namespace = {"__name__": "__main__", "__file__": str(script), "__package__": None}
        try:
            exec(compile(source, f"{PRE_MIGRATION_BASELINE_COMMIT}:{relative_path}", "exec"), namespace)
        except SystemExit as error:
            assert error.code in (0, None), error.code
        snapshot = semantic_snapshot(bpy.context.scene)
        print("HISTORICAL_BASELINE", json.dumps(provenance, sort_keys=True))
        return snapshot
    finally:
        sys.argv = original_argv


def _assert_preserved(before, after, name):
    left, right = _records(before)[name], _records(after)[name]
    for key in ("transform", "vertexCount", "topologyCount", "vertexHash",
                "topologyHash", "materials", "polygonMaterialIndices",
                "polygonMaterials", "materialNodes"):
        assert right[key] == left[key], (name, key)


def _run_generator_snapshot(script, output, extra_args=()):
    original_argv = sys.argv
    try:
        _reset()
        sys.argv = [str(script), "--", "--output", str(output), *extra_args]
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as error:
            assert error.code in (0, None), error.code
        return semantic_snapshot(bpy.context.scene)
    finally:
        sys.argv = original_argv


def _assert_generator_snapshot(script, output, expected_hold_count, baseline_snapshot, extra_args=()):
    snapshot = _run_generator_snapshot(script, output, extra_args)
    exported = [item for item in snapshot["objects"] if item["export"]]
    holds = [item for item in exported if item["role"] == "hold"]
    assert len(holds) == expected_hold_count, [(item["name"], item["role"], item["holdID"]) for item in exported]
    assert len([item for item in exported if item["role"] == "body"]) == 1
    assert snapshot["reviewObjectNames"] == []
    assert all(item["polygonMaterialIndices"] for item in exported)
    assert all(item["materialNodes"] for item in exported)
    assert _semantic_fingerprints(snapshot) == _semantic_fingerprints(baseline_snapshot), (
        script.name, _semantic_fingerprints(snapshot), _semantic_fingerprints(baseline_snapshot))
    return snapshot


def main() -> None:
    if bpy is None:
        print("GEOMETRY_PRIMITIVES_TEST skipped: requires Blender's bpy module")
        return
    _reset()
    wood = _image_material("semantic wood")
    baseline = create_rounded_body(
        "baseline-body", [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [(0, 1, 2, 3)], materials=(wood,))
    tag_piece(baseline, "body", coordinate_frame="hang-ten-board-v1")

    # Each creation family is isolated: snapshot the existing authored scene,
    # call exactly one helper, then prove the prior mesh/material payload is
    # byte-for-byte semantically unchanged.
    for factory, name, vertices, faces in (
        (create_rounded_body, "rounded-body", [(0, 0, 0), (1, 0, 0), (1, 1, 0)], [(0, 1, 2)]),
        (create_recess, "recess", [(0, 0, 0), (1, 0, 0), (1, 1, 0)], [(0, 1, 2)]),
        (create_stepped_edge, "stepped", [(0, 0, 0), (1, 0, 0), (1, 1, 0)], [(0, 1, 2)]),
        (create_passage, "passage", [(0, 0, 0), (0, 1, 0), (0, 0, 1)], [(0, 1, 2)]),
    ):
        before = semantic_snapshot(bpy.context.scene)
        created = factory(name, vertices, faces, materials=(wood,))
        after = semantic_snapshot(bpy.context.scene)
        _assert_preserved(before, after, "baseline-body")
        assert _records(after)[name]["vertexCount"] == len(vertices)
        assert _records(after)[name]["topologyCount"] == len(faces)

    before = semantic_snapshot(bpy.context.scene)
    tag_piece(baseline, "hold", "semantic-hold", coordinate_frame="hang-ten-board-v1")
    after = semantic_snapshot(bpy.context.scene)
    _assert_preserved(before, after, "baseline-body")
    assert _records(after)["baseline-body"]["role"] == "hold"
    assert _records(after)["baseline-body"]["holdID"] == "semantic-hold"

    # Blender's Boolean pipeline may assign a different opaque vertex-index
    # order to an otherwise identical mesh. A topology audit must compare the
    # complete positioned face cycles, not those transient storage indices.
    _reset()
    first = create_rounded_body(
        "canonical-topology",
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [(0, 1, 2, 3)],
    )
    tag_piece(first, "body")
    canonical_before = semantic_snapshot(bpy.context.scene)
    _reset()
    reordered = create_rounded_body(
        "canonical-topology",
        [(1, 1, 0), (0, 0, 0), (0, 1, 0), (1, 0, 0)],
        [(1, 3, 0, 2)],
    )
    tag_piece(reordered, "body")
    canonical_after = semantic_snapshot(bpy.context.scene)
    assert _semantic_fingerprints(canonical_before)["topology"] == (
        _semantic_fingerprints(canonical_after)["topology"])

    # A factory-scene reset removes its material datablocks. The real mesh
    # helper must reject the stale RNA object instead of accepting an ordering
    # that the following fresh-scene fixture avoids.
    _reset()
    stale_material = _material("stale fixture lifetime material")
    _reset()
    try:
        create_rounded_body(
            "stale-fixture-lifetime", [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)],
            materials=(stale_material,))
    except ReferenceError as error:
        assert "Material" in str(error) and "removed" in str(error), error
    else:
        raise AssertionError("expected stale material to be rejected after _reset()")

    _reset()
    fixture_material = _material("fixture lifetime material")
    fixture_body = create_rounded_body(
        "fixture-lifetime", [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)],
        materials=(fixture_material,))
    assert fixture_body.data.materials[0] == fixture_material

    # Material bindings belong to positioned canonical faces, not raw polygon
    # slots. Face ordering and loop rotation remain tolerated, but exchanging
    # two materials on those faces must invalidate the topology audit.
    _reset()
    material_a = _material("canonical material A")
    material_b = _material("canonical material B")
    face_vertices = [
        (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
        (2, 0, 0), (3, 0, 0), (3, 1, 0), (2, 1, 0),
    ]
    bound_first = create_rounded_body(
        "canonical-materials", face_vertices, [(0, 1, 2, 3), (4, 5, 6, 7)],
        materials=(material_a, material_b),
    )
    bound_first.data.polygons[1].material_index = 1
    tag_piece(bound_first, "body")
    bound_snapshot = semantic_snapshot(bpy.context.scene)
    _reset()
    material_a = _material("canonical material A")
    material_b = _material("canonical material B")
    bound_reordered = create_rounded_body(
        "canonical-materials", face_vertices, [(6, 7, 4, 5), (2, 3, 0, 1)],
        materials=(material_a, material_b),
    )
    bound_reordered.data.polygons[0].material_index = 1
    tag_piece(bound_reordered, "body")
    reordered_snapshot = semantic_snapshot(bpy.context.scene)
    assert _semantic_fingerprints(bound_snapshot)["topology"] == (
        _semantic_fingerprints(reordered_snapshot)["topology"])
    _reset()
    material_a = _material("canonical material A")
    material_b = _material("canonical material B")
    bound_swapped = create_rounded_body(
        "canonical-materials", face_vertices, [(0, 1, 2, 3), (4, 5, 6, 7)],
        materials=(material_a, material_b),
    )
    bound_swapped.data.polygons[0].material_index = 1
    tag_piece(bound_swapped, "body")
    swapped_snapshot = semantic_snapshot(bpy.context.scene)
    assert _semantic_fingerprints(bound_snapshot)["topology"] != (
        _semantic_fingerprints(swapped_snapshot)["topology"])

    # Split changes object partitioning but must preserve the total authored
    # vertex/topology/material binding payload. Start a fresh scene so this
    # family has no unrelated meshes in its before/after audit.
    _reset()
    wood = _image_material("split wood")
    split_material = _material("split material")
    split_body = create_rounded_body(
        "split-body",
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0), (2, 1, 0)],
        [(0, 1, 2), (3, 4, 5)], materials=(wood, split_material))
    split_body.data.polygons[1].material_index = 1
    tag_piece(split_body, "body")
    before = semantic_snapshot(bpy.context.scene)
    split_contact_surface(split_body, ("split material",))
    after = semantic_snapshot(bpy.context.scene)
    before_record = _records(before)["split-body"]
    split_records = [item for item in after["objects"] if item["export"]]
    assert sum(item["vertexCount"] for item in split_records) == before_record["vertexCount"]
    assert sum(item["topologyCount"] for item in split_records) == before_record["topologyCount"]
    assert sum(len(item["polygonMaterialIndices"]) for item in split_records) == len(before_record["polygonMaterialIndices"])
    before_bindings = list(zip(before_record["polygonMaterialIndices"], before_record["polygonMaterials"]))
    after_bindings = [
        (index, material)
        for item in split_records
        for index, material in zip(item["polygonMaterialIndices"], item["polygonMaterials"])
    ]
    assert sorted(material for _, material in after_bindings) == sorted(material for _, material in before_bindings)
    assert Counter(material for _, material in after_bindings) == Counter(
        material for _, material in before_bindings)
    assert all(isinstance(index, int) for index, _ in after_bindings)
    for item in split_records:
        assert all(index == item["materials"].index(material)
                   for index, material in zip(item["polygonMaterialIndices"], item["polygonMaterials"]))
    assert {material for _, material in after_bindings} == set(before_record["materials"])

    _reset()
    wood = _image_material("review wood")
    review_body = create_rounded_body(
        "review-body", [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)], materials=(wood,))
    tag_piece(review_body, "body")
    before = semantic_snapshot(bpy.context.scene)
    camera, _ = make_review_rig(owner="geometry-primitives-test")
    after = semantic_snapshot(bpy.context.scene)
    for item in before["objects"]:
        if item["export"]:
            _assert_preserved(before, after, item["name"])
    review_names = {camera.name, "ReviewKey", "ReviewFill", "ReviewRim"}
    assert after["reviewObjectNames"] == sorted(review_names)

    # Run each migrated generator in an owned temporary output and capture its
    # final compiler-input scene; this catches a helper migration that passes
    # toy primitives but drops a real board tag/material/topology.
    repo = TOOLS.parents[1]
    owned_resource = _OwnedResourceDirectory(repo, "task4-snapshots")
    owner_dir = owned_resource.path
    try:
        beast_baseline = _run_historical_generator_snapshot(
            repo, "beastmaker", owner_dir / "baseline-beastmaker", ("--compiler-only",))
        beast_snapshot = _assert_generator_snapshot(
            TOOLS / "beastmaker_1000.py", owner_dir / "beastmaker", 22,
            beast_baseline, ("--compiler-only",))
        compact_baseline = _run_historical_generator_snapshot(
            repo, "compact", owner_dir / "baseline-compact", ("--compiler-only",))
        compact_snapshot = _assert_generator_snapshot(
            TOOLS / "wood_grips_compact_ii.py", owner_dir / "compact", 19,
            compact_baseline, ("--compiler-only",))
        assert beast_snapshot["materialImageBytes"]
        assert compact_snapshot["materialImageBytes"]
    finally:
        owned_resource.cleanup()
    print("GEOMETRY_PRIMITIVES_TEST passed")


if __name__ == "__main__":
    main()
