"""Semantic snapshot regression tests for the shared Blender geometry helpers.

Run with Blender from the repository root::

    blender --background --factory-startup --python-exit-code 1 \
      --python Tools/HangboardModels/test_geometry_primitives.py

The test deliberately snapshots authored data rather than image pixels.  Review
objects are explicitly marked non-exportable and are required to remain outside
the model set.
"""

from __future__ import annotations

import json
import hashlib
from collections import Counter
import runpy
import shutil
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


# Approved semantic fingerprints captured from the exact pre-task generators
# at commit cbcee285. Each projection includes every exported
# object and the complete snapshot fields relevant to that audit category.
PRE_MIGRATION_BASELINE_COMMIT = "cbcee285"
PRE_MIGRATION_BASELINES = {
    "beastmaker": {
        "topology": "31d0bd8362301289e3fce021045ece72720a58f090d207955c4c5390c2af6ac4",
        "transforms": "69fb4bd022831d85032415bab41b24960c8e3d5bbd2a8e568f18b9444a5ab824",
        "bindings": "26279998308a9e735e96a4259473a4d86a7a1c71e5380671ef42443871b45efe",
        "materialNodes": "05910bc195086c458bfde95b9cd4b434b5353747452399e5333a5e0e43121267",
    },
    "compact": {
        "topology": "86f29969101a72c3fa52e18b274620a725212fb14c76a87d82f1251cf1c78d08",
        "transforms": "7e30a29f490e28560adcc8dcf4ea2fae4510044e9fa107c675962cd5d5c5d2a9",
        "bindings": "c5acc203f7de83a61d9776067c1fb8013606fda22a3506dc0290e6caf35ad6cb",
        "materialNodes": "03f59de336e25ae2388e4125870cd4d76cf7388304a6d157cf3cabb8f1ca3047",
    },
}


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


def _assert_generator_snapshot(script, output, expected_hold_count, baseline_key, extra_args=()):
    snapshot = _run_generator_snapshot(script, output, extra_args)
    exported = [item for item in snapshot["objects"] if item["export"]]
    holds = [item for item in exported if item["role"] == "hold"]
    assert len(holds) == expected_hold_count, [(item["name"], item["role"], item["holdID"]) for item in exported]
    assert len([item for item in exported if item["role"] == "body"]) == 1
    assert snapshot["reviewObjectNames"] == []
    assert all(item["polygonMaterialIndices"] for item in exported)
    assert all(item["materialNodes"] for item in exported)
    assert _semantic_fingerprints(snapshot) == PRE_MIGRATION_BASELINES[baseline_key], (
        baseline_key, _semantic_fingerprints(snapshot), PRE_MIGRATION_BASELINES[baseline_key])
    return snapshot


def main() -> None:
    if bpy is None:
        raise unittest.SkipTest("requires Blender's bpy module")
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
    owner_dir = Path(tempfile.mkdtemp(prefix=f"{repo.name}-task4-snapshots-", dir=repo / ".context"))
    try:
        (owner_dir / "ownership.json").write_text(json.dumps({"owner": repo.name, "resources": [str(owner_dir)], "external_resources": []}) + "\n")
        beast_snapshot = _assert_generator_snapshot(
            TOOLS / "beastmaker_1000.py", owner_dir / "beastmaker", 22, "beastmaker", ("--compiler-only",))
        compact_snapshot = _assert_generator_snapshot(
            TOOLS / "wood_grips_compact_ii.py", owner_dir / "compact", 19, "compact", ("--compiler-only",))
        assert beast_snapshot["materialImageBytes"]
        assert compact_snapshot["materialImageBytes"]
    finally:
        shutil.rmtree(owner_dir)
        assert not owner_dir.exists()
    print("GEOMETRY_PRIMITIVES_TEST passed")


if __name__ == "__main__":
    main()
