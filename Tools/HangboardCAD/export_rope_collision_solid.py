"""Export a native FreeCAD solid for offline settled-rope collision solving.

Environment variables:
  HANGTEN_ROPE_PACKAGE        Hangboards package slug
  HANGTEN_ROPE_SOLID_FEATURE  final wood feature name in the FCStd
  HANGTEN_ROPE_SOLID_OUTPUT   workspace-owned JSON path

Run with FreeCAD's Python interpreter. Coordinates in the output are the
same meter-based model frame used by suspension.json. This is an authoring
intermediate, never a bundled model or USDZ material.
"""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parents[2]
package = os.environ["HANGTEN_ROPE_PACKAGE"]
feature_name = os.environ["HANGTEN_ROPE_SOLID_FEATURE"]
destination = Path(os.environ["HANGTEN_ROPE_SOLID_OUTPUT"])
source = ROOT / "Hangboards" / package / f"{package}.FCStd"
document = App.openDocument(str(source))
feature = document.getObject(feature_name)
if feature is None or not feature.Shape.isValid() or len(feature.Shape.Solids) != 1:
    raise ValueError(f"{feature_name} is not one valid wood solid")
points, triangles = feature.Shape.tessellate(0.25)
vertices = [[point.x / 1000, point.z / 1000, -point.y / 1000] for point in points]
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    json.dumps(
        {
            "sourcePackage": package,
            "sourceFeature": feature_name,
            "sourceSHA256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "vertices": vertices,
            "triangles": [list(face) for face in triangles],
        }
    )
    + "\n"
)
print(f"{destination}: {len(vertices)} vertices, {len(triangles)} triangles")
