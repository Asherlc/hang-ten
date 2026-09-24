"""Genuine native checks for the metolius-rock-rings-3d v2 source document.

Run under FreeCAD's own interpreter:

    HANGTEN_CAD_PYTHONPATH=<extra> \
      /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
      Tools/HangboardCAD/tests/metolius_native_source_checks.py <path-to.FCStd>

The board is descriptor schema v2 with a single reusable unit: one node per
contact slot serves both physical rings. These checks reopen the saved document
in a fresh process, recompute it, and exercise a real edit, including the
slot/instance relationship, which a v1 board cannot exercise.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

REPOSITORY = Path(__file__).resolve().parents[3]
# board.json is generated from the FCStd's HangTenBoardManifest (never committed).
BOARD_SOURCE = REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "metolius-rock-rings-3d.FCStd"

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    if not condition:
        FAILURES.append(label)


def bound_objects(document):
    return [
        obj
        for obj in document.Objects
        if "NodeID" in obj.PropertiesList and getattr(obj, "NodeID", "")
    ]


def published_depths(board):
    by_id = {contact["id"]: contact for contact in board.get("contacts", [])}
    depths = {}
    for presentation in board.get("presentations", []):
        for instance in presentation.get("media", {}).get("instances", []):
            for slot, contact_id in instance.get("contactIDsBySlotID", {}).items():
                span = ((by_id.get(contact_id) or {}).get("depth") or {}).get("range") or {}
                low, high = span.get("minimum"), span.get("maximum")
                if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low == high:
                    depths[slot] = float(low)
    return depths


def main() -> int:
    source = Path(sys.argv[1]).resolve()
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    sys.path.insert(0, str(REPOSITORY / "Tools" / "HangboardCAD"))
    import use_hangboard_packages  # noqa: F401
    from hangboard_packages import cad_source

    board = json.loads(cad_source.generate_board_json(BOARD_SOURCE))
    expected_depths = published_depths(board)

    document = App.openDocument(str(source))
    document.recompute()

    print("reopen and recompute", flush=True)
    check("source document reopens", document is not None)
    check(
        "document declares schema version 2",
        document.getPropertyByName("HangTenSchemaVersion") == 2,
        str(document.getPropertyByName("HangTenSchemaVersion")),
    )
    stale = [
        f"{obj.Name}={obj.State}"
        for obj in document.Objects
        if set(obj.State) & {"Invalid", "Error", "Touched", "Recompute"}
    ]
    check("every object recomputes cleanly", not stale, "; ".join(stale))

    outline = document.getObject("Outline")
    check("outline sketch is fully constrained", bool(outline.FullyConstrained))

    nodes = bound_objects(document)
    inventory = sorted((obj.NodeID, obj.NodeRole) for obj in nodes)
    check("bound node inventory", len(nodes) == 7, f"{inventory}")
    body = next((obj for obj in nodes if obj.NodeRole == "body"), None)
    contacts = {obj.ContactSlotID: obj for obj in nodes if obj.NodeRole == "contact"}
    attachments = [obj for obj in nodes if obj.NodeRole == "attachment"]
    check("one body node", body is not None)
    check("four contact slots", sorted(contacts) == ["jug", "pocket-25", "pocket-32", "pocket-40"])
    check("two attachment nodes", len(attachments) == 2)
    check("body occupies the native frame", abs(body.Shape.BoundBox.XLength - 146.0) < 1.0
          and abs(body.Shape.BoundBox.YLength - 57.0) < 0.1
          and abs(body.Shape.BoundBox.ZLength - 184.0) < 1.0,
          f"({body.Shape.BoundBox.XLength:.2f},{body.Shape.BoundBox.YLength:.2f},{body.Shape.BoundBox.ZLength:.2f})")

    # Each pocket's authored region depth must equal the published grip depth.
    for slot, depth in sorted(expected_depths.items()):
        obj = contacts.get(slot)
        measured = round(float(obj.Shape.BoundBox.YLength), 3) if obj else None
        check(
            f"{slot} authored depth matches its published grip depth",
            obj is not None and abs(measured - depth) < 0.25,
            f"authored={measured} published={depth}",
        )

    # Every contact region must be a region of the body surface, not a proxy.
    for slot, obj in sorted(contacts.items()):
        worst = 0.0
        for vertex in obj.Shape.Vertexes:
            worst = max(worst, body.Shape.distToShape(Part.Vertex(vertex.Point))[0])
        check(
            f"{slot} region lies on the body surface",
            worst < 0.01,
            f"max distance to body = {worst:.5f} mm",
        )

    print("edit: pocket-40 floor depth 40 -> 34 mm", flush=True)
    floor = document.getObject("Floor_pocket_40")
    before = {slot: round(float(obj.Shape.BoundBox.YLength), 3) for slot, obj in contacts.items()}
    floor.Placement.Base.y = floor.Placement.Base.y - 6.0
    document.recompute()
    after = {slot: round(float(obj.Shape.BoundBox.YLength), 3) for slot, obj in contacts.items()}
    check(
        "the depth edit moves the intended pocket region",
        abs(after["pocket-40"] - (before["pocket-40"] - 6.0)) < 0.05,
        f"{before['pocket-40']} -> {after['pocket-40']} mm",
    )
    check(
        "unrelated pocket regions keep their depth",
        all(abs(after[slot] - before[slot]) < 0.05 for slot in ("pocket-25", "pocket-32")),
        f"pocket-25={after['pocket-25']} pocket-32={after['pocket-32']}",
    )
    floor.Placement.Base.y = floor.Placement.Base.y + 6.0
    document.recompute()

    # The same node must still serve both physical contacts of a slot: the
    # board's two instances map the slot to distinct contacts, and the slot
    # declares exactly one node.
    descriptor = json.loads(
        (REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "assets" / "primary.model.json").read_text()
    )
    instances = board["presentations"][0]["media"]["instances"]
    left = instances[0]["contactIDsBySlotID"]
    right = instances[1]["contactIDsBySlotID"]
    shared = [
        slot
        for slot in descriptor["contactSlots"]
        if left.get(slot) != right.get(slot)
        and descriptor["contactSlots"][slot]["nodeIDs"] == [contacts[slot].NodeID]
    ]
    check(
        "each slot node serves both left and right contacts",
        len(shared) == 4,
        f"slots={sorted(shared)}",
    )

    check(
        "source bytes are unchanged by reopen and edits",
        hashlib.sha256(source.read_bytes()).hexdigest() == original_digest,
    )

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed:", flush=True)
        for label in FAILURES:
            print(f"  - {label}", flush=True)
        return 1
    print("\nall native source checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
