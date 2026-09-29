"""Derive sliding aperture regions from explicitly selected native CAD features.

The initial adapter supports straight, axis-aligned Box channels. Unsupported
feature types fail explicitly; their apertures must never be guessed from an
overlay mesh or from a cached rope route.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import FreeCAD as App
import Part

from export_rope_collision_solid import model_point, native_mesh


def _feature(document, name):
    feature = document.getObject(name)
    if feature is None or not hasattr(feature, "Shape"):
        raise ValueError(f"missing solid feature {name}")
    if not feature.Shape.isValid() or len(feature.Shape.Solids) != 1:
        raise ValueError(f"{name} must be one valid solid")
    return feature


def _portal(face, identifier):
    center = face.CenterOfMass
    normal = face.normalAt(0, 0)
    normal.normalize()
    points = [vertex.Point for vertex in face.OuterWire.Vertexes]
    # Sort the native planar cap's vertices about its CAD center; no sampled
    # image geometry and no authored contact coordinates enter this record.
    reference = points[0] - center
    reference.normalize()
    tangent = normal.cross(reference)
    points.sort(key=lambda point: math.atan2((point-center).dot(tangent),
                                            (point-center).dot(reference)))
    boundary = [model_point(point) for point in points]
    start = min(range(len(boundary)), key=lambda index: boundary[index])
    boundary = boundary[start:] + boundary[:start]
    return {"id": identifier, "center": model_point(center),
            "normal": [round(normal.x, 9), round(normal.z, 9), round(-normal.y, 9)],
            "boundary": boundary}


def export_rope_physics(document, body_feature: str, channel_features: dict) -> dict:
    body = _feature(document, body_feature).Shape
    box = body.BoundBox
    envelope = Part.makeBox(box.XLength, box.YLength, box.ZLength,
                            App.Vector(box.XMin, box.YMin, box.ZMin))
    portals, channels = [], []
    for identifier, feature_name in sorted(channel_features.items()):
        feature = _feature(document, feature_name)
        axis_name = getattr(feature, "HangTenChannelAxis", "")
        if axis_name not in {"x", "y", "z"}:
            raise ValueError(f"{feature_name} needs an operator-selected HangTenChannelAxis")
        if feature.TypeId != "Part::Box" or feature.Placement.Rotation.Angle > 1e-10:
            raise ValueError(f"{feature_name}: unsupported channel adapter (expected axis-aligned Box)")
        axis = {"x": App.Vector(1, 0, 0), "y": App.Vector(0, 1, 0),
                "z": App.Vector(0, 0, 1)}[axis_name]
        region = feature.Shape.common(envelope)
        geometry = native_mesh(region)
        if region.common(body).Volume > 1e-6:
            raise ValueError(f"{feature_name}: channel region intersects wood")
        caps = [face for face in region.Faces
                if abs(face.normalAt(0, 0).dot(axis)) > 1 - 1e-9]
        if len(caps) != 2:
            raise ValueError(f"{feature_name}: expected two planar aperture caps")
        caps.sort(key=lambda face: model_point(face.CenterOfMass), reverse=True)
        records = [_portal(face, f"{identifier}-{suffix}")
                   for face, suffix in zip(caps, ("front", "back"))]
        # The cap must coincide with a real mouth, not merely a bounding box
        # clipping plane. Each boundary edge must touch the wood solid.
        for face in caps:
            if any(body.distToShape(edge)[0] > 1e-5 for edge in face.Edges):
                raise ValueError(f"{feature_name}: cap is not a native wood aperture")
        portals.extend(records)
        channels.append({"id": identifier, "portalIDs": [p["id"] for p in records],
                         "spine": [p["center"] for p in records], **geometry})
    return {"collision": native_mesh(body), "portals": portals, "channels": channels}


def build_physics_descriptor(document, source: Path, model_sha256: str, config: dict) -> dict:
    if set(config) != {"bodyFeature", "channelFeatures", "profiles"}:
        raise ValueError("rope-physics.json needs bodyFeature, channelFeatures and profiles only")
    from hangboard_packages.rope_physics import validate_rope_physics
    descriptor = {"schemaVersion": 1,
                  "sourceSHA256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "modelSHA256": model_sha256,
                  "coordinateSystem": "hang-ten-board-v1",
                  **export_rope_physics(document, config["bodyFeature"], config["channelFeatures"]),
                  "profiles": config["profiles"]}
    validate_rope_physics(descriptor, model_sha256)
    return descriptor
