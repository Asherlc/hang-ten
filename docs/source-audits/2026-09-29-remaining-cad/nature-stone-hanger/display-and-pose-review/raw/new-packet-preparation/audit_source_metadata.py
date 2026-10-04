#!/usr/bin/env python3
"""Read the frozen native archives; do not open FreeCAD or change package bytes."""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[4]
BASE = ROOT / ".context/placid-badger/nature-stone-review9"
OLD = BASE / "pre-vertical-groove-installed-packet/raw/package/nature-stone-hanger.FCStd"
NEW = BASE / "vertical-groove-correction/native-author/nature-stone-hanger.FCStd"
EXPECTED_OLD = "1b0113f264ee1d0b31d7b30b68f8b1e64839268ecd53b97a2ba8067e29a01108"
EXPECTED_NEW = "ee189092c1727c096894b1223ce78fd5214f858de2908507cc5ee0e6fb1297e6"
DEPTHS = {
    "edge-front-15mm-incut": 15, "edge-front-15mm-flat": 15,
    "edge-front-20mm-wood-flat": 20, "edge-front-20mm-granite": 20,
    "edge-reverse-10mm-incut": 10, "edge-reverse-10mm-flat": 10,
    "edge-reverse-06mm-flat": 6, "edge-reverse-06mm-incut": 6,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive(path, expected):
    raw = path.read_bytes()
    assert digest(raw) == expected, path
    with zipfile.ZipFile(path) as z:
        xml = ET.fromstring(z.read("Document.xml"))
        manifest = xml.findall("./Properties/Property[@name='HangTenBoardManifest']/String")
        assert len(manifest) == 1
        payload = manifest[0].get("value")
        members = {n: digest(z.read(n)) for n in z.namelist() if n.lower().endswith(".brp")}
    objects = {o.get("name"): o.get("type") for o in xml.findall("./Objects/Object")}
    properties = {o.get("name"): {p.get("name"): p for p in o.findall("./Properties/Property")}
                  for o in xml.findall("./ObjectData/Object")}
    return xml, payload, json.loads(payload), members, objects, properties


def properties_value(properties, name, property_name):
    element = properties[name][property_name]
    assert len(element) >= 1
    return dict(element[0].attrib)


def main():
    _, old_payload, old_manifest, old_members, old_objects, old_properties = archive(OLD, EXPECTED_OLD)
    _, payload, manifest, members, objects, properties = archive(NEW, EXPECTED_NEW)
    assert old_payload == payload and old_manifest == manifest
    contacts = {c["id"]: c for c in manifest["contacts"]}
    assert set(contacts) == set(DEPTHS)
    for name, depth in DEPTHS.items():
        assert contacts[name]["depth"]["range"] == {"minimum": depth, "maximum": depth}
    positions = manifest["positions"]
    assert len(positions) == 8 and {p["id"] for p in positions} == set(DEPTHS)
    assert all(p["contactIDs"] == [p["id"]] and p["presentationID"] == "primary" for p in positions)
    display = manifest["presentations"][0]["media"]["display"]
    assert display["surfaceFinish"] == "wood"
    assert display["graniteNodeIDs"] == ["edge_front_20mm_granite_mesh_001"]

    added = {n: objects[n] for n in objects.keys() - old_objects.keys()}
    assert added == {"LeftVerticalCordGroove": "Part::Cylinder", "RightVerticalCordGroove": "Part::Cylinder",
                     "CordSeat_Left": "Part::Cut", "CordSeat_Right": "Part::Cut"}
    assert not old_objects.keys() - objects.keys()
    assert all(objects[n] == kind for n, kind in old_objects.items())
    vertical = {}
    for side, x, base in (("Left", -52.5, "Port_RightVisibleMouth"), ("Right", 52.5, "CordSeat_Left")):
        tool, cut = side + "VerticalCordGroove", "CordSeat_" + side
        radius = float(properties_value(properties, tool, "Radius")["value"])
        height = float(properties_value(properties, tool, "Height")["value"])
        placement = properties_value(properties, tool, "Placement")
        assert radius == 1.75 and height == 110
        assert [float(placement[k]) for k in ("Px", "Py", "Pz")] == [x, 0, -55]
        assert [float(placement[k]) for k in ("Q0", "Q1", "Q2", "Q3")] == [0, 0, 0, 1]
        assert properties_value(properties, cut, "Base")["value"] == base
        assert properties_value(properties, cut, "Tool")["value"] == tool
        vertical[side.lower()] = {"tool": tool, "cut": cut, "radiusMM": radius,
                                  "toolHeightMM": height, "nativeBaseXYZMM": [x, 0, -55],
                                  "nativeAxis": [0, 0, 1], "numericProvenance": "Operator display estimate"}
    transverse = {}
    for side in ("Left", "Right"):
        for i in range(3):
            tool = side + "Adjustment" + str(i)
            cut = "Groove_" + tool
            assert objects[tool] == "Part::Cylinder" and objects[cut] == "Part::Cut"
            values = {}
            for field in ("Radius", "Height", "Placement"):
                values[field] = properties_value(properties, tool, field)
                assert values[field] == properties_value(old_properties, tool, field)
            for field in ("Base", "Tool"):
                assert properties_value(properties, cut, field) == properties_value(old_properties, cut, field)
            transverse[tool] = values
    regions = ["Region_" + c.replace("-", "_") + ".Shape.brp" for c in sorted(DEPTHS)]
    assert all(n in old_members and n in members for n in regions)
    changed = sorted(n for n in old_members.keys() & members.keys() if old_members[n] != members[n])
    result = {
        "status": "pass-static-archive-metadata-only",
        "sourceSHA256": EXPECTED_NEW, "beforeSourceSHA256": EXPECTED_OLD,
        "fileSHA256": {str(OLD.relative_to(ROOT)): EXPECTED_OLD, str(NEW.relative_to(ROOT)): EXPECTED_NEW},
        "manifestUTF8SHA256": digest(payload.encode()), "manifestBytesIdentical": True,
        "contacts": 8, "contactIDs": sorted(DEPTHS), "publishedDepthsMM": DEPTHS,
        "allContactFactsUnchanged": True, "allEightSingletonPositionsUnchanged": True,
        "woodAndGraniteMetadataUnchanged": True,
        "nativeBodyGeometryChanged": True, "addedNativeObjects": added,
        "verticalSeats": vertical, "transverseNotchesPreserved": 6,
        "transverseToolParametersAndCutLinksUnchanged": True,
        "transverseTools": transverse,
        "archiveShapeMembers": {"before": len(old_members), "after": len(members),
                                "new": sorted(members.keys() - old_members.keys()),
                                "changedCommon": changed,
                                "contactRegionBytesEqual": {n: old_members[n] == members[n] for n in regions}},
        "limits": [
            "Static native ZIP/XML and complete manifest comparison only; no FreeCAD, solver, shape judgement or runtime resources were launched.",
            "The two vertical tool definitions and retained transverse definitions are verified. Their actual native Boolean validity and contact surface equivalence require the separate fresh source-bound native reports.",
            "Contact BRep archive bytes differ after recompute; no contact BRep byte preservation is claimed.",
            "No cord, exported mesh, posed bearing, app appearance, test completion or human acceptance gate is supplied by this metadata audit.",
        ],
        "blockingFindings": [], "humanAcceptance": "pending", "canonicalMutation": False,
    }
    output = PREP / "source-metadata-inspection.json"
    assert not output.exists(), "retain the previous report before writing another revision"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "report": str(output.relative_to(ROOT)),
                      "sha256": digest(output.read_bytes()), "contacts": 8,
                      "addedVerticalSeats": 2, "transverseNotchesPreserved": 6}))


if __name__ == "__main__":
    main()
