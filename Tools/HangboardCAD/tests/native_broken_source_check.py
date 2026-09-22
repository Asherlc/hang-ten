"""A source that fails to recompute must fail the build, not publish stale shapes.

Reproduces the defect found in review: deleting a profile segment opens the
sketch wire, so ``PartDesign::Pad`` recomputes to ``Invalid`` and keeps its
previously saved shape. The compiler used to tessellate that stale body together
with freshly recomputed contact bands and publish the inconsistent mix with exit
status 0.

Run under FreeCAD's interpreter; exit status is non-zero if the check fails.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "Tools" / "HangboardCAD"))

import FreeCAD as App  # noqa: E402

import compile_board  # noqa: E402

PACKAGE = "lattice-triple-rung"
SOURCE = REPOSITORY / "ModelSources" / f"{PACKAGE}.FCStd"
BOARD = REPOSITORY / "Hangboards" / PACKAGE / "board.json"

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    if not condition:
        FAILURES.append(label)


def main() -> int:
    scratch = Path(tempfile.mkdtemp(prefix="hangten-broken-"))
    try:
        broken = scratch / f"{PACKAGE}.FCStd"
        shutil.copyfile(SOURCE, broken)

        document = App.openDocument(str(broken))
        sketch = document.getObject("Profile")
        sketch.delGeometry(0)
        document.recompute()
        document.save()
        pad = document.getObject("Pad")
        states = {obj.Name: sorted(obj.State) for obj in document.Objects}
        volume_before = pad.Shape.Volume
        App.closeDocument(document.Name)
        print("broken source state:", flush=True)
        for name in ("Pad", "Body", "Surface_edge_10"):
            print(f"      {name}: {states.get(name)}", flush=True)

        check(
            "the broken source really is broken",
            any(state != ["Up-to-date"] for state in states.values()),
        )
        assets = scratch / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        raised = None
        try:
            compile_board.build(PACKAGE, broken, BOARD, assets, publish=True)
        except compile_board.BuildError as error:
            raised = error
        except Exception as error:  # noqa: BLE001 - report the unexpected type
            raised = error
            check("the build fails with BuildError", False, f"got {type(error).__name__}: {error}")

        check(
            "the build fails on a source that did not recompute cleanly",
            isinstance(raised, compile_board.BuildError),
            str(raised),
        )
        if raised is not None:
            check(
                "the failure names the offending object",
                "Pad" in str(raised),
                str(raised),
            )
        check(
            "nothing was published",
            not (assets / "primary.usdz").exists()
            and not (assets / "primary.model.json").exists(),
        )
        check(
            "no staged directory was left behind",
            not any(p.name.startswith(".hangten-build-") for p in assets.iterdir()),
        )
        check("the stale shape was non-empty (the trap was live)", volume_before > 0)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed:", flush=True)
        for label in FAILURES:
            print(f"  - {label}", flush=True)
        return 1
    print("\nbroken-source checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
