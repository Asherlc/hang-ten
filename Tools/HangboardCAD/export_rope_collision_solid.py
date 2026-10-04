"""Export a native FreeCAD solid for offline settled-rope collision solving.

Environment variables:
  HANGTEN_ROPE_PACKAGE        Hangboards package slug
  HANGTEN_ROPE_SOLID_FEATURE  final wood feature name in the FCStd
  HANGTEN_ROPE_SOLID_OUTPUT   workspace-owned JSON path

Run with FreeCAD's Python interpreter. Coordinates in the output are the
same meter-based model frame used by generated assets/suspension.json. This is an authoring
intermediate, never a bundled model or USDZ material.
"""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path

import FreeCAD as App

def model_point(point):
    return [round(point.x / 1000, 9), round(point.z / 1000, 9), round(-point.y / 1000, 9)]


def native_mesh(shape, *, canonical=True):
    """Weld CAD tessellation seams, retaining the solid's outward winding."""
    if not shape.isValid() or len(shape.Solids) != 1 or shape.Volume <= 0:
        raise ValueError("collision source must be one valid positive-volume solid")
    points, faces = shape.tessellate(0.25)
    if not canonical:
        # Preserve the legacy section solver's exact floating-point inputs and
        # ordering; its existing cached authoring routes depend on those bytes.
        return {"vertices": [[p.x/1000, p.z/1000, -p.y/1000] for p in points],
                "triangles": [list(face) for face in faces]}
    keys = [tuple(model_point(point)) for point in points]
    vertices = sorted(set(keys))
    indices = {point: index for index, point in enumerate(vertices)}
    triangles = []
    for face in faces:
        triangle = tuple(indices[keys[index]] for index in face)
        if len(set(triangle)) != 3:
            raise ValueError("CAD tessellation contains a degenerate triangle")
        # Rotate, never reverse, so deterministic ordering preserves winding.
        start = triangle.index(min(triangle))
        triangles.append(triangle[start:] + triangle[:start])
    return {"vertices": [list(point) for point in vertices],
            "triangles": [list(face) for face in sorted(triangles)]}


def main():
    root = Path(__file__).resolve().parents[2]
    package = os.environ["HANGTEN_ROPE_PACKAGE"]
    feature_name = os.environ["HANGTEN_ROPE_SOLID_FEATURE"]
    destination = Path(os.environ["HANGTEN_ROPE_SOLID_OUTPUT"])
    source = root / "Hangboards" / f"{package}.FCStd"
    document = App.openDocument(str(source))
    try:
        feature = document.getObject(feature_name)
        if feature is None:
            raise ValueError(f"missing wood feature {feature_name}")
        mesh = native_mesh(feature.Shape, canonical=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {"sourcePackage": package, "sourceFeature": feature_name,
            "sourceSHA256": hashlib.sha256(source.read_bytes()).hexdigest(), **mesh}
        grooves = [name for name in os.environ.get("HANGTEN_ROPE_GROOVE_FEATURES", "").split(",") if name]
        bores = [name for name in os.environ.get("HANGTEN_ROPE_BORE_FEATURES", "").split(",") if name]
        if grooves or bores:
            from native_cord_features import extract_native_cord_features
            payload["nativeCordFeatures"] = extract_native_cord_features(document, feature.Shape, grooves, bores)
        destination.write_text(json.dumps(payload) + "\n")
        print(f"{destination}: {len(mesh['vertices'])} vertices, {len(mesh['triangles'])} triangles")
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__":
    main()
