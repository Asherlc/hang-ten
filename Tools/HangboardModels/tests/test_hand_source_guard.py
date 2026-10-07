"""An unsupported Blender must not mutate the retained hand source."""
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("version", [(5, 2, 1), (4, 5, 0)])
def test_hand_rebuild_rejects_unpinned_blender_before_mutation(monkeypatch, version):
    def mutate_scene(**kwargs):
        pytest.fail("unsupported Blender mutated the authoring scene")

    monkeypatch.setitem(sys.modules, "bpy", SimpleNamespace(
        app=SimpleNamespace(version=version),
        ops=SimpleNamespace(wm=SimpleNamespace(read_factory_settings=mutate_scene)),
    ))
    monkeypatch.setitem(sys.modules, "bmesh", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(
        Vector=object, Quaternion=object, Matrix=object,
    ))
    script = Path(__file__).resolve().parents[3] / "Art/GripHand/build_hand.py"
    with pytest.raises(RuntimeError, match="hand authoring requires pinned Blender 5.2.0"):
        runpy.run_path(str(script), run_name="__main__")
