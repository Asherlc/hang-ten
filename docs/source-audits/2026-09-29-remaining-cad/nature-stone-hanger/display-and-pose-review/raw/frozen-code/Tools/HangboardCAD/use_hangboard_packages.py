"""Make ``hangboard_packages`` importable from the HangboardCAD tools.

The FCStd archive contract and the board-manifest generator live in
``hangboard_packages.cad_source`` (``Tools/HangboardPackages/src``), shared with
the package validator. The HangboardCAD tools run as plain scripts under two
interpreters that do not have that package installed: host ``python3`` (for
example the ``git diff`` textconv driver) and FreeCAD's ``freecadcmd``, which
does not inherit ``PYTHONPATH``. This is the one place that puts the package
source on ``sys.path`` for them; import it before importing
``hangboard_packages``:

    import use_hangboard_packages  # noqa: F401
    from hangboard_packages import cad_source

The repository copy is put first so that an unrelated installed version can
never shadow it. When the package is already installed in editable mode (as in
CI), both resolve to the same source.
"""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "HangboardPackages" / "src"

if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))
