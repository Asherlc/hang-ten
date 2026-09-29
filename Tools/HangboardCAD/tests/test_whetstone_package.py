"""Protect Whetstone identity and its photographed, non-mirrored depth order."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

from hangboard_packages import cad_source


PACKAGE = Path(__file__).resolve().parents[3] / "Hangboards" / "tension-whetstone"


def test_whetstone_cad_preserves_contacts_and_photographed_depth_order():
    source = PACKAGE / "tension-whetstone.FCStd"
    assert source.is_file(), "Whetstone must have its own native CAD source"
    board = cad_source.load_board(source)
    expected = {"top-ergo-jug", "edge-40-center"}
    expected |= {f"{kind}-{depth}-{side}" for side in ("left", "right")
                 for kind, depth in (("pocket", 40), ("edge", 40), ("edge", 30),
                                     ("edge", 25), ("edge", 20))}
    assert {contact["id"] for contact in board["contacts"]} == expected
    assert board["dimensions"] == "25 × 6 × 2 in"
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert "contactGeometry" not in media
    assert not (PACKAGE / "board.json").exists()
    descriptor = json.loads((PACKAGE / media["descriptorPath"]).read_text())
    contacts = descriptor["contacts"]
    assert set(contacts) == expected
    # Tension's front photograph labels both slots left-to-right 40/30 and
    # 25/20: only the silhouette is mirrored, not these depth assignments.
    for side in ("left", "right"):
        for deeper, shallower in ((40, 30), (25, 20)):
            assert contacts[f"edge-{deeper}-{side}"]["center"][0] < contacts[f"edge-{shallower}-{side}"]["center"][0]
    assert all(contact["nodeIDs"] for contact in contacts.values())


@pytest.mark.skipif(
    not Path(os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")).is_file(),
    reason="FreeCAD native interpreter unavailable",
)
def test_whetstone_native_edits_keep_contact_surfaces_on_body():
    tools = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(tools / "run_freecad.py"), "--freecad",
         os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"),
         str(tools / "tests" / "whetstone_native_source_checks.py"),
         str(PACKAGE / "tension-whetstone.FCStd")],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"sourceBytesUnchanged": true' in result.stdout
