"""Measure hidden cord-channel centerlines from authored FreeCAD pipe spines.

Run with FreeCAD's Python interpreter, for example:

    HANGTEN_CHANNEL_PACKAGE=lattice-mini-bar \
    HANGTEN_CHANNEL_FEATURES_JSON='{"left-loop":"LeftCordChannel","right-loop":"RightCordChannel"}' \
    freecadcmd Tools/HangboardCAD/measure_channel_spines.py

The adjacent suspension.json supplies each branch's two mouth coordinates.
This command reports the measured length between their projections on the
SubtractivePipe spine. It never edits the CAD source or sidecar.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import FreeCAD as App


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = os.environ["HANGTEN_CHANNEL_PACKAGE"]
FEATURES = json.loads(os.environ["HANGTEN_CHANNEL_FEATURES_JSON"])
SOURCE = ROOT / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SIDECAR = SOURCE.with_name("suspension.json")


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


def main():
    document = App.openDocument(str(SOURCE))
    suspension = json.loads(SIDECAR.read_text())["suspension"]
    passages_by_id = {
        passage["id"]: passage for side in suspension["passages"].values()
        for passage in side
    }
    output = {}
    for branch in suspension["branches"]:
        feature_name = FEATURES[branch["id"]]
        feature = document.getObject(feature_name)
        if feature is None or feature.TypeId != "PartDesign::SubtractivePipe":
            raise ValueError(f"{feature_name} is not a SubtractivePipe")
        spine = feature.Spine[0]
        samples = spine_samples(spine)
        first, second = (
            model_to_native(passages_by_id[passage_id]["pointInModel"])
            for passage_id in branch["passageIDs"]
        )
        length = abs(station_on_spine(second, samples) - station_on_spine(first, samples)) / 1000
        output[branch["id"]] = round(length, 9)
    if os.environ.get("HANGTEN_CHANNEL_VERIFY") == "1":
        declared = suspension["internalLoop"]["channelLengthByBranchID"]
        if set(declared) != set(output) or any(
            abs(declared[branch] - measured) > 1e-6 for branch, measured in output.items()
        ):
            raise ValueError(f"channel lengths differ from CAD spine: {output}")
    print(json.dumps(output, sort_keys=True))


main()
