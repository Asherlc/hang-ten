"""Guard the two physical revisions and their continuous physical contacts.

These integration checks catch revision identity collisions, accidental
left/right splits of a continuous rail, and descriptor bindings that omit a
selectable surface. Depth expectations come from the designer's published
18/14/12/10/9/8/7/6 mm inventory, not from the compiler.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "Tools/HangboardPackages/src"))
from hangboard_packages.cad_source import generate_board_json
from hangboard_packages.board_catalog import load_board_package

PACKAGES = (
    "surfaces-for-climbing-transgression-2011",
    "surfaces-for-climbing-transgression-2013",
)
EDGE_DEPTHS = {"edge-18": 18, "edge-14": 14, "edge-12": 12, "edge-10": 10,
               "edge-9": 9, "edge-8": 8, "edge-7": 7, "edge-6": 6}


def board_for(slug: str) -> dict:
    source = REPOSITORY / "Hangboards" / slug / f"{slug}.FCStd"
    assert source.is_file(), f"missing native source: {source}"
    return json.loads(generate_board_json(source))


def test_revisions_have_distinct_persistable_identities():
    original, revised = map(board_for, PACKAGES)
    assert original["id"] != revised["id"]
    assert original["revisionID"] != revised["revisionID"]


@pytest.mark.parametrize("slug", PACKAGES)
def test_every_continuous_contact_loads_with_its_real_model_binding(slug):
    board = board_for(slug)
    contacts = {contact["id"]: contact for contact in board["contacts"]}
    assert set(contacts) == set(EDGE_DEPTHS) | {"jug-top"}
    for contact_id, depth in EDGE_DEPTHS.items():
        contact = contacts[contact_id]
        assert contact["kind"] == "edge"
        assert contact["depth"] == {"range": {"minimum": depth, "maximum": depth}}
        assert "pairedContactID" not in contact
    assert contacts["jug-top"]["kind"] == "jug"
    assert "depth" not in contacts["jug-top"]

    root = REPOSITORY / "Hangboards" / slug
    load_board_package(root)  # Real consumer validates generated metadata + assets.
    descriptor = json.loads((root / "assets/primary.model.json").read_text())
    assert set(descriptor["contacts"]) == set(contacts)
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (root / "assets/primary.usdz").read_bytes()
    ).hexdigest()
    for binding in descriptor["contacts"].values():
        assert len(binding["nodeIDs"]) == 1


@pytest.mark.skipif(
    not Path(os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")).is_file()
    and os.environ.get("CI", "").lower() != "true",
    reason="FreeCAD native interpreter unavailable locally",
)
@pytest.mark.parametrize("slug", PACKAGES)
def test_native_edits_keep_all_contacts_on_the_body(slug):
    tools = REPOSITORY / "Tools/HangboardCAD"
    source = REPOSITORY / "Hangboards" / slug / f"{slug}.FCStd"
    result = subprocess.run(
        [sys.executable, str(tools / "run_freecad.py"), "--freecad",
         os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"),
         str(tools / "tests/transgression_native_source_checks.py"), str(source)],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "original bytes preserved" in result.stdout
