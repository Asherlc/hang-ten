#!/usr/bin/env python3
"""Verify the exact shipped Trango Rock Prodigy Training Center USDZ."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

EXPECTED_CONTACT_IDS = (
    "jug-left", "jug-right", "edge-large-vder-left", "edge-shallow-vder-left",
    "edge-thin-crimp-left", "edge-thin-crimp-right", "pocket-three-finger-slot-left",
    "pocket-three-finger-slot-right", "pocket-index-middle-deep-left",
    "pocket-index-middle-deep-right", "pocket-middle-ring-deep-left",
    "pocket-middle-ring-deep-right", "pocket-index-middle-medium-shallow-left",
    "pocket-index-middle-medium-shallow-right", "pocket-middle-ring-shallow-left",
    "pocket-middle-ring-shallow-right", "pinch-medium-left", "pinch-wide-left",
    "edge-large-vder-right", "edge-shallow-vder-right", "pinch-medium-right",
    "pinch-wide-right", "sloper-left", "sloper-right",
)

def _load_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def require_disjoint_pinch_triangles(triangles_by_contact: Mapping[str, set[tuple]]) -> dict[str, int]:
    """Reject duplicate/co-located surfaces even when importer node IDs differ."""
    counts = {}
    for side in ("left", "right"):
        medium = triangles_by_contact[f"pinch-medium-{side}"]
        wide = triangles_by_contact[f"pinch-wide-{side}"]
        if not medium or not wide:
            raise ValueError(f"{side} pinch surface is empty")
        if medium & wide:
            raise ValueError(f"{side} medium/wide pinch surfaces share triangles")
        counts[f"pinch-medium-{side}"] = len(medium)
        counts[f"pinch-wide-{side}"] = len(wide)
    return counts


def verify_shipped_package(package_root: Path) -> dict[str, object]:
    """Hash-check and rebuild the native CAD half's reusable descriptor."""
    descriptor_path = Path(package_root) / "assets/primary.model.json"
    if _load_object(descriptor_path, "descriptor").get("schemaVersion") != 2:
        raise ValueError("Training Center requires its native reusable descriptor")
    return _verify_reusable_package(Path(package_root))


def require_reusable_descriptor_matches_source(package, model_bytes, model, descriptor):
    """Rebuild caches from native authored bindings/outlines and exported points."""
    import zipfile
    import xml.etree.ElementTree as ET
    from contact_model_descriptor import SlotNodeBinding, compile_reusable_descriptor

    with zipfile.ZipFile(package / f"{package.name}.FCStd") as archive:
        document = ET.fromstring(archive.read("Document.xml"))
    nodes, outlines = [], {}
    for obj in document.findall("./ObjectData/Object"):
        properties = {
            prop.attrib["name"]: prop.find("String").get("value")
            for prop in obj.findall("./Properties/Property")
            if prop.find("String") is not None
        }
        role = properties.get("NodeRole")
        if not role:
            continue
        slot = properties.get("ContactSlotID") if role == "contact" else None
        nodes.append(SlotNodeBinding(properties["NodeID"], role, slot))
        if slot and properties.get("HangTenHoldOutline"):
            outlines[slot] = [tuple(value / 1000 for value in point)
                              for point in json.loads(properties["HangTenHoldOutline"])]
    vertices = {name: node["points_m"] for name, node in model["nodes"].items()}
    rebuilt = compile_reusable_descriptor(
        model_bytes, nodes, vertices,
        frozenset(node.contact_slot_id for node in nodes if node.role == "contact"),
        outlines,
    ).to_json()
    if rebuilt != descriptor:
        raise ValueError("descriptor does not match CAD source bindings/outlines and exported USDZ geometry")


def _verify_reusable_package(package: Path) -> dict[str, object]:
    """Verify the canonical CAD half and both physical instance bindings."""
    from pxr import Usd, UsdShade
    cad_tools = _TOOLS.parent / "HangboardCAD"
    sys.path.insert(0, str(cad_tools))
    import board_manifest  # Installs the shared package module search path.
    from hangboard_packages.cad_source import load_board
    from usdz_writer import read_usdz

    model_path = package / "assets/primary.usdz"
    descriptor = _load_object(package / "assets/primary.model.json", "descriptor")
    board = load_board(package / f"{package.name}.FCStd")
    if tuple(c["id"] for c in board["contacts"]) != EXPECTED_CONTACT_IDS:
        raise ValueError("physical Training Center contact inventory changed")
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if descriptor["modelSHA256"] != digest:
        raise ValueError("descriptor model hash does not match shipped USDZ")
    model = read_usdz(model_path)
    if set(model["nodes"]) != {n["nodeID"] for n in descriptor["nodes"]}:
        raise ValueError("descriptor node inventory differs from shipped USDZ")
    require_reusable_descriptor_matches_source(package, model_path.read_bytes(), model, descriptor)
    stage = Usd.Stage.Open(str(model_path))
    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Material) or prim.IsA(UsdShade.Shader) or prim.HasAPI(UsdShade.MaterialBindingAPI):
            raise ValueError("canonical model must remain unbound")
    if any(p[0] >= 0 for node in model["nodes"].values() for p in node["points_m"]):
        raise ValueError("canonical asset contains geometry outside its left half")
    instances = board["presentations"][0]["media"]["instances"]
    if len(instances) != 2 or instances[1]["baseTransform"].get("reflection") != "x":
        raise ValueError("expected two instances with the right half reflected")
    triangles = {}
    mapped = []
    for side, instance in zip(("left", "right"), instances):
        bindings = instance["contactIDsBySlotID"]
        if set(bindings) != set(descriptor["contactSlots"]):
            raise ValueError("instance does not bind every canonical slot")
        for slot, contact_id in bindings.items():
            if contact_id != f"{slot}-{side}":
                raise ValueError("left/right contact binding changed")
            mapped.append(contact_id)
        for kind in ("medium", "wide"):
            slot = f"pinch-{kind}"
            region = set()
            for node_id in descriptor["contactSlots"][slot]["nodeIDs"]:
                node = model["nodes"][node_id]
                for face in node["triangles"]:
                    region.add(tuple(sorted(tuple(round(v, 9) for v in node["points_m"][i]) for i in face)))
            triangles[bindings[slot]] = region
    if len(set(mapped)) != 24 or set(mapped) != set(EXPECTED_CONTACT_IDS):
        raise ValueError("physical contact coverage is incomplete")
    counts = require_disjoint_pinch_triangles(triangles)
    return {"status": "verified", "modelSHA256": digest,
            "descriptorMatchesCADAndUSDZ": True,
            "nodeCount": len(model["nodes"]), "canonicalHalfCount": 1,
            "physicalInstanceCount": 2, "contactCount": len(mapped),
            "disjointPinchTriangleCounts": counts}


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2] / "Hangboards/trango-rock-prodigy-training-center")
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[sys.argv.index("--") + 1:]) if argv is None and "--" in sys.argv else list(sys.argv[1:] if argv is None else argv)
    arguments = _arguments(raw)
    arguments.report.write_text(json.dumps(verify_shipped_package(arguments.package_root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
