"""Focused regression coverage for explicit multi-body model packages."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_model_package as compiler
from model_descriptor import NodeBinding, compile_descriptor


REPOSITORY_ROOT = TOOLS.parents[1]
PACKAGES_SOURCE = TOOLS.parent / "HangboardPackages" / "src"
if str(PACKAGES_SOURCE) not in sys.path:
    sys.path.insert(0, str(PACKAGES_SOURCE))

from hangboard_packages.board_catalog import load_board_package  # noqa: E402


class FakeSceneObject(dict[str, object]):
    def __init__(self, name: str, *, role: str, hold_id: str | None = None) -> None:
        super().__init__()
        self.name = name
        self.type = "MESH"
        self["role"] = role
        if hold_id is not None:
            self["hold_id"] = hold_id


class FakeScene:
    def __init__(self, *objects: FakeSceneObject) -> None:
        self.objects = objects


class MultipleBodyMeshesTests(unittest.TestCase):
    def test_explicit_body_meshes_remain_nonselectable(self) -> None:
        """Catches rejecting a source package solely because it has two body meshes."""
        scene = FakeScene(
            FakeSceneObject("body-L", role="body"),
            FakeSceneObject("body-R", role="body"),
            FakeSceneObject("hold-L-pocket", role="hold", hold_id="left-pocket"),
        )

        try:
            bindings = compiler.validate_tagged_scene(scene, frozenset({"left-pocket"}))
        except ValueError as error:
            self.fail(f"explicit body meshes must be accepted: {error}")
        descriptor = compile_descriptor(
            b"exact-usdz-bytes",
            bindings,
            {
                "body-L": [(0, 0, 0), (1, 1, 1)],
                "body-R": [(1, 0, 0), (2, 1, 1)],
                "hold-L-pocket": [(0.2, 0.4, 0), (0.4, 0.6, 0.2)],
            },
            frozenset({"left-pocket"}),
        )

        self.assertEqual(
            descriptor.nodes,
            (
                NodeBinding("body-L", "body"),
                NodeBinding("body-R", "body"),
                NodeBinding("hold-L-pocket", "hold", "left-pocket"),
            ),
        )
        self.assertEqual(set(descriptor.holds), {"left-pocket"})
        self.assertNotIn("body-L", descriptor.holds["left-pocket"].node_ids)
        self.assertNotIn("body-R", descriptor.holds["left-pocket"].node_ids)

    def test_shipped_training_tiles_package_keeps_both_body_nodes_nonselectable(self) -> None:
        package_root = REPOSITORY_ROOT / "Hangboards" / "soill-training-tiles"
        package = load_board_package(package_root)
        descriptor = json.loads(
            (package_root / "assets" / "primary.model.json").read_text(encoding="utf-8")
        )

        self.assertEqual(package.board.id, "soill.training-tiles")
        body_node_ids = {
            node["nodeID"] for node in descriptor["nodes"] if node["role"] == "body"
        }
        bound_hold_node_ids = {
            node_id
            for hold in descriptor["holds"].values()
            for node_id in hold["nodeIDs"]
        }
        self.assertEqual(body_node_ids, {"body_L_001", "body_R_001"})
        self.assertTrue(body_node_ids.isdisjoint(bound_hold_node_ids))


if __name__ == "__main__":
    unittest.main()
