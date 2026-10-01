"""Derive sliding aperture regions from explicitly selected native CAD features.

Adapters support straight Box/Cylinder channels and circular native pipes. Unsupported
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
from measure_channel_spines import spine_samples


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
    if len(points) < 3:
        # A native circular cap has one seam vertex, not a polygonal boundary.
        # Discretize the CAD wire itself; no image or cached cord route enters it.
        points = list(face.OuterWire.discretize(Number=65))
        if points[0].distanceToPoint(points[-1]) < 1e-7:
            points.pop()
        if len(points) < 3:
            raise ValueError(f"{identifier}: native cap has no complete boundary")
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


def _circle_boundary(center, normal, radius):
    reference=normal.cross(App.Vector(0,0,1))
    if reference.Length < 1e-8:
        reference=normal.cross(App.Vector(1,0,0))
    reference.normalize()
    tangent=normal.cross(reference)
    return [center+reference*(radius*math.cos(i*math.tau/64))
            +tangent*(radius*math.sin(i*math.tau/64)) for i in range(64)]


def _pipe_regions(feature, body, identifier):
    """Keep the actual curved-mouth void; use interior sections for topology.

    A curved wood surface has no planar mouth cap. A complete CAD-derived
    circular section just inside each exit tracks material crossings without
    approximating that contact surface. Exact wood triangles govern the rim.
    """
    profile=feature.Profile[0]
    if len(profile.Geometry)!=1 or not isinstance(profile.Geometry[0],Part.Circle):
        raise ValueError(f"{feature.Name}: circular pipe profile required")
    samples=spine_samples(feature.Spine[0])
    radius=profile.Geometry[0].Radius
    tool=feature.AddSubShape.copy()
    tool.Placement=feature.Placement.multiply(tool.Placement)
    before=feature.BaseFeature.Shape
    region=tool.common(before)
    if region.common(body).Volume>1e-6:
        raise ValueError(f"{feature.Name}: native pipe void intersects wood")
    indices=[]
    records=[]
    for reverse,suffix in [(False,"front"),(True,"back")]:
        candidates=range(len(samples)-2,0,-1) if reverse else range(1,len(samples)-1)
        for i in candidates:
            normal=samples[i+1]-samples[i-1]
            normal.normalize()
            if not reverse:normal=-normal
            boundary=_circle_boundary(samples[i],normal,radius)
            if all(before.isInside(p,1e-7,True) for p in boundary):
                # A virtual section must remain on the actual native void,
                # including its entire circular boundary.
                if any(region.distToShape(Part.Vertex(p))[0]>1e-5 for p in boundary):
                    continue
                indices.append(i)
                points=[model_point(p) for p in boundary]
                start=min(range(len(points)),key=lambda j:points[j])
                points=points[start:]+points[:start]
                records.append({"id":f"{identifier}-{suffix}","center":model_point(samples[i]),
                    "normal":[round(normal.x,9),round(normal.z,9),round(-normal.y,9)],
                    "boundary":points})
                break
        else:
            raise ValueError(f"{feature.Name}: no complete interior crossing section")
    if indices[0]>=indices[1]:
        raise ValueError(f"{feature.Name}: crossing sections do not bracket a channel")
    channel={"id":identifier,"portalIDs":[p["id"] for p in records],
             "spine":[model_point(p) for p in samples[indices[0]:indices[1]+1]],
             **native_mesh(region)}
    return records,channel


def _cylinder_mesh(region, caps):
    """Preserve native sides; triangulate convex planar caps repeatably.

    OCCT may choose different interior diagonals on a newly intersected
    circular cap. Its side seam vertices are stable. Reuse that boundary,
    leaving the exported solid surface and winding unchanged.
    """
    mesh=native_mesh(region)
    points=[App.Vector(*p) for p in mesh["vertices"]]
    triangles=[tuple(t) for t in mesh["triangles"]]
    for face in caps:
        center=App.Vector(*model_point(face.CenterOfMass))
        native=face.normalAt(0,0)
        normal=App.Vector(native.x,native.z,-native.y)
        selected=[t for t in triangles if all(abs((points[i]-center).dot(normal))<1e-9 for i in t)]
        selected_set=set(selected)
        sides=[t for t in triangles if t not in selected_set]
        boundary=sorted(set(i for t in selected for i in t)&set(i for t in sides for i in t))
        if len(boundary)<3:
            raise ValueError("native cylindrical cap has no closed side seam")
        reference=points[boundary[0]]-center
        reference.normalize()
        tangent=normal.cross(reference)
        boundary.sort(key=lambda i:math.atan2((points[i]-center).dot(tangent),(points[i]-center).dot(reference)))
        start=boundary.index(min(boundary))
        boundary=boundary[start:]+boundary[:start]
        triangles=sides+[(boundary[0],boundary[i],boundary[i+1]) for i in range(1,len(boundary)-1)]
    used=sorted(set(i for t in triangles for i in t))
    remap={i:j for j,i in enumerate(used)}
    canonical=[]
    for triangle in triangles:
        t=tuple(remap[i] for i in triangle)
        first=t.index(min(t))
        canonical.append(t[first:]+t[:first])
    return {"vertices":[mesh["vertices"][i] for i in used],"triangles":[list(t) for t in sorted(canonical)]}


def export_rope_physics(document, body_feature: str, channel_features: dict) -> dict:
    body = _feature(document, body_feature).Shape
    box = body.BoundBox
    envelope = Part.makeBox(box.XLength, box.YLength, box.ZLength,
                            App.Vector(box.XMin, box.YMin, box.ZMin))
    portals, channels = [], []
    for identifier, feature_name in sorted(channel_features.items()):
        feature = _feature(document, feature_name)
        if feature.TypeId == "PartDesign::SubtractivePipe":
            records,channel=_pipe_regions(feature,body,identifier)
            portals.extend(records)
            channels.append(channel)
            continue
        if feature.TypeId == "Part::Cylinder":
            # The deliberately authored primitive supplies its own bore axis,
            # including a non-identity placement such as Helium's through-bores.
            axis = feature.Placement.Rotation.multVec(App.Vector(0, 0, 1))
        else:
            axis_name = getattr(feature, "HangTenChannelAxis", "")
            if axis_name not in {"x", "y", "z"}:
                raise ValueError(f"{feature_name} needs an operator-selected HangTenChannelAxis")
            if feature.TypeId != "Part::Box" or feature.Placement.Rotation.Angle > 1e-10:
                raise ValueError(f"{feature_name}: unsupported channel adapter (expected axis-aligned Box or native Cylinder)")
            axis = {"x": App.Vector(1, 0, 0), "y": App.Vector(0, 1, 0),
                    "z": App.Vector(0, 0, 1)}[axis_name]
        region = feature.Shape.common(envelope)
        if region.common(body).Volume > 1e-6:
            raise ValueError(f"{feature_name}: channel region intersects wood")
        caps = [face for face in region.Faces
                if abs(face.normalAt(0, 0).dot(axis)) > 1 - 1e-9]
        if len(caps) != 2:
            raise ValueError(f"{feature_name}: expected two planar aperture caps")
        caps.sort(key=lambda face: model_point(face.CenterOfMass), reverse=True)
        geometry = _cylinder_mesh(region,caps) if feature.TypeId == "Part::Cylinder" else native_mesh(region)
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
