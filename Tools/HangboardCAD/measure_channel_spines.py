"""Measure hidden cord-channel centerlines from authored FreeCAD pipe spines.

Run with FreeCAD's Python interpreter, for example:

    HANGTEN_CHANNEL_PACKAGE=lattice-mini-bar \
    HANGTEN_CHANNEL_FEATURES_JSON='{"left-loop":"LeftCordChannel","right-loop":"RightCordChannel"}' \
    freecadcmd Tools/HangboardCAD/measure_channel_spines.py

The native document's HangTenSuspensionAuthoring supplies each branch's
two mouth coordinates.
This command reports the measured length between their projections on each
channel's spine. A channel is either a `PartDesign::SubtractivePipe` (its
Sketcher spine, as on the Mini Bar) or a straight `Part::Cylinder` through-bore
(its axis, as on the Helium Mobile), a `Part::Box` rectangular channel
with the operator-selected `HangTenChannelAxis` set to x, y, or z (as on
Clavellium), or a `Part::MultiFuse` with a linked ordered Part::Feature Spine
(Rock Rings). Schema-2 entries can be selected with
HANGTEN_CHANNEL_PRESENTATION_ID and HANGTEN_CHANNEL_EQUIPMENT_OBJECT_ID.
Reusable-instance configurations require the equipment ID. The command is
read-only and never edits the CAD source or generated suspension artifact.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import FreeCAD as App

import use_hangboard_packages  # noqa: F401
from hangboard_packages import cad_source


ROOT = Path(__file__).resolve().parents[2]


def model_to_native(point):
    x, y, z = point
    return App.Vector(x * 1000, -z * 1000, y * 1000)


def spine_samples(sketch):
    samples = []
    for geometry in sketch.Geometry:
        edge = geometry.toShape()
        count = max(2, math.ceil(edge.Length / 0.25) + 1)
        points = [sketch.Placement.multVec(point) for point in edge.discretize(Number=count)]
        if samples:
            points = points[1:]
        samples.extend(points)
    if len(samples) < 2:
        raise ValueError(f"{sketch.Name} has no usable spine")
    return samples


def cylinder_axis_samples(feature):
    """A straight bore's spine: the Part::Cylinder axis, base to top cap."""
    placement = feature.Placement
    start = placement.multVec(App.Vector(0, 0, 0))
    end = placement.multVec(App.Vector(0, 0, float(feature.Height)))
    count = max(2, math.ceil(start.distanceToPoint(end) / 0.25) + 1)
    return [start.add(end.sub(start).multiply(i / (count - 1))) for i in range(count)]


def box_axis_samples(feature):
    """Operator-selected axis of a straight rectangular sling passage."""
    axis = getattr(feature, "HangTenChannelAxis", "")
    if axis not in ("x", "y", "z"):
        raise ValueError(f"{feature.Name} must declare HangTenChannelAxis x, y or z")
    dimensions = [float(feature.Length), float(feature.Width), float(feature.Height)]
    first = [length / 2 for length in dimensions]
    second = first.copy()
    index = "xyz".index(axis)
    first[index] = 0
    second[index] = dimensions[index]
    return [feature.Placement.multVec(App.Vector(*first)),
            feature.Placement.multVec(App.Vector(*second))]


def channel_samples(feature, name):
    if feature is None:
        raise ValueError(f"{name} is missing")
    if feature.TypeId == "PartDesign::SubtractivePipe":
        return spine_samples(feature.Spine[0])
    if feature.TypeId == "Part::Cylinder":
        return cylinder_axis_samples(feature)
    if feature.TypeId == "Part::Box":
        return box_axis_samples(feature)
    if feature.TypeId == "Part::MultiFuse" and "Spine" in feature.PropertiesList:
        samples = []
        if feature.Spine is None or feature.Spine.Shape.isNull() or feature.Spine.Shape.ShapeType != "Wire":
            raise ValueError(f"{name} has no usable spine")
        # Shape edges already include the linked feature's Placement.
        # Apply only the channel's own placement, avoiding a second spine transform.
        for edge in feature.Spine.Shape.OrderedEdges:
            points = edge.discretize(Number=max(2, math.ceil(edge.Length / 0.25) + 1))
            points = [feature.Placement.multVec(point) for point in points]
            samples.extend(points if not samples else points[1:])
        if len(samples) < 2:
            raise ValueError(f"{name} has no usable spine")
        return samples
    raise ValueError(f"{name} has no supported native channel spine")



def station_on_spine(point, samples):
    best = (float("inf"), None)
    station = 0.0
    for start, end in zip(samples, samples[1:]):
        segment = end.sub(start)
        length = segment.Length
        if length == 0:
            continue
        fraction = max(0.0, min(1.0, point.sub(start).dot(segment) / (length * length)))
        projected = start.add(segment.multiply(fraction))
        distance = point.distanceToPoint(projected)
        if distance < best[0]:
            best = (distance, station + fraction * length)
        station += length
    if best[1] is None or best[0] > 0.25:
        raise ValueError(f"mouth is {best[0]:.3f} mm from its declared channel spine")
    return best[1]


def point_at_station(samples, station):
    traversed = 0.0
    for start, end in zip(samples, samples[1:]):
        length = start.distanceToPoint(end)
        if station <= traversed + length:
            fraction = (station - traversed) / length if length else 0.0
            return start.add(end.sub(start).multiply(fraction))
        traversed += length
    return samples[-1]


def path_between_stations(samples, first, second):
    low, high = sorted((first, second))
    station = 0.0
    result = [point_at_station(samples, low)]
    for start, end in zip(samples, samples[1:]):
        station += start.distanceToPoint(end)
        if low < station < high:
            result.append(end)
    result.append(point_at_station(samples, high))
    return result if first <= second else list(reversed(result))


def native_to_model(point):
    return [point.x / 1000, point.z / 1000, -point.y / 1000]


def selected_suspension(data, presentation_id=None, equipment_id=None):
    """Select one authored setup without consulting a generated route cache."""
    if "entries" in data:
        entries = [entry for entry in data["entries"]
                   if (presentation_id is None or entry["presentationID"] == presentation_id)
                   and (equipment_id is None or entry.get("equipmentObjectID") == equipment_id)]
        if len(entries) != 1:
            raise ValueError(
                "select exactly one authored setup with HANGTEN_CHANNEL_PRESENTATION_ID "
                "and HANGTEN_CHANNEL_EQUIPMENT_OBJECT_ID"
            )
        return entries[0]["suspension"]
    if presentation_id is not None and data.get("presentationID") != presentation_id:
        raise ValueError(f"unknown presentation: {presentation_id}")
    if "instanceSuspensions" in data:
        instances = data["instanceSuspensions"]
        if equipment_id not in instances:
            raise ValueError("set HANGTEN_CHANNEL_EQUIPMENT_OBJECT_ID to one of: "
                             + ", ".join(instances))
        return instances[equipment_id]
    if equipment_id is not None:
        raise ValueError("this authored setup has no equipment-object instances")
    return data["suspension"]


def main():
    PACKAGE = os.environ["HANGTEN_CHANNEL_PACKAGE"]
    FEATURES = json.loads(os.environ["HANGTEN_CHANNEL_FEATURES_JSON"])
    SOURCE = ROOT / "Hangboards" / f"{PACKAGE}.FCStd"
    data = cad_source.load_suspension_authoring(SOURCE)
    if data is None:
        raise ValueError(f"{SOURCE} has no authored suspension")
    suspension = selected_suspension(
        data, os.environ.get("HANGTEN_CHANNEL_PRESENTATION_ID"),
        os.environ.get("HANGTEN_CHANNEL_EQUIPMENT_OBJECT_ID"),
    )
    document = App.openDocument(str(SOURCE))
    try:
        passages_by_id = {
            passage["id"]: passage for side in suspension["passages"].values()
            for passage in side
        }
        output = {}
        paths = {}
        for branch in suspension["branches"]:
            feature_name = FEATURES[branch["id"]]
            samples = channel_samples(document.getObject(feature_name), feature_name)
            first, second = (
                model_to_native(passages_by_id[passage_id]["pointInModel"])
                for passage_id in branch["passageIDs"]
            )
            first_station = station_on_spine(first, samples)
            second_station = station_on_spine(second, samples)
            length = abs(second_station - first_station) / 1000
            output[branch["id"]] = round(length, 9)
            paths[branch["id"]] = [native_to_model(point) for point in
                                   path_between_stations(samples, first_station, second_station)]
        if os.environ.get("HANGTEN_CHANNEL_VERIFY") == "1":
            declared = suspension["internalLoop"]["channelLengthByBranchID"]
            if set(declared) != set(output) or any(
                abs(declared[branch] - measured) > 1e-6 for branch, measured in output.items()
            ):
                raise ValueError(f"channel lengths differ from CAD spine: {output}")
        print(json.dumps(output, sort_keys=True))
        if destination := os.environ.get("HANGTEN_CHANNEL_SAMPLES_OUTPUT"):
            Path(destination).write_text(json.dumps(paths, sort_keys=True) + "\n")
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__":
    main()
