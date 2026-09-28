"""Solve settled threaded-rope routes against a native CAD wood solid.

The source sidecar supplies mouths, a connected-channel length, one overhead
anchor, loop length, pose rotations, and winding. This authoring command finds
the shortest nonpenetrating route in each winding class on a rope-radius
offset CAD section, then lowers the board until the longest loop is taut.
Its generated route cache stays in suspension.json, outside the USDZ.

This is a static massless-rope equilibrium for bar-shaped boards whose end
sections are representative of the exterior bearing surface. It does not
model friction, rope elasticity, swing, or arbitrary 3D sliding along the bar.
"""

import argparse
import heapq
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[2]


def rotate_inverse(quaternion, vector):
    xyz = -np.asarray(quaternion[:3], dtype=float)
    turn = 2 * np.cross(xyz, vector)
    return vector + quaternion[3] * turn + np.cross(xyz, turn)


class Section:
    def __init__(self, mouth, mesh, radius, clearance):
        self.mouth = mouth
        self.x = mouth["pointInModel"][0]
        cross = mesh.section(plane_origin=[self.x, 0, 0], plane_normal=[1, 0, 0])
        assert cross is not None and len(cross.discrete) == 1
        self.polygon = orient(
            Polygon(cross.discrete[0][:, 1:3]).buffer(radius + clearance, quad_segs=12),
            1,
        )
        assert self.polygon.is_valid and not self.polygon.interiors
        self.points = np.vstack(
            [
                np.array(mouth["pointInModel"][1:3]),
                np.array(self.polygon.exterior.coords)[:-1],
            ]
        )
        self.ray_y = self.polygon.centroid.x
        self.ray_z = self.polygon.centroid.y
        assert not self.polygon.contains(Point(self.points[0]))
        n = len(self.points)
        self.adj = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                a, b = self.points[i], self.points[j]
                distance = float(np.linalg.norm(a - b))
                if distance < 1e-8:
                    continue
                if LineString([a, b]).relate(self.polygon)[0] != "F":
                    continue
                cross = self.crossing(a, b)
                self.adj[i].append((j, distance, cross))
                self.adj[j].append((i, distance, -cross))

    def crossing(self, a, b):
        if (a[0] < self.ray_y) == (b[0] < self.ray_y):
            return 0
        t = (self.ray_y - a[0]) / (b[0] - a[0])
        if a[1] + t * (b[1] - a[1]) >= self.ray_z:
            return 0
        return 1 if b[0] > a[0] else -1

    def winding_from_direction(self, anchor, direction):
        options = []
        for winding in (-1, 0, 1):
            try:
                length, path = self.solve(anchor, winding)
            except RuntimeError:
                continue
            path = np.array(path)
            angle = np.arctan2(path[:, 1] - self.ray_z, path[:, 0] - self.ray_y)
            turn = float(
                np.arctan2(np.sin(np.diff(angle)), np.cos(np.diff(angle))).sum()
            )
            options.append((winding, length, turn))
        direction_sign = -1 if direction == "clockwise" else 1
        matching = [item for item in options if item[2] * direction_sign > 1e-5]
        if not matching:
            raise ValueError(
                f"{self.mouth['id']}: no {direction} route from this anchor"
            )
        return min(matching, key=lambda item: item[1])[0]

    def solve(self, anchor, winding):
        start = np.array(anchor[1:3])
        assert not self.polygon.contains(Point(start))
        links = []
        for j, point in enumerate(self.points):
            if LineString([start, point]).relate(self.polygon)[0] != "F":
                continue
            three_d_length = float(np.linalg.norm(anchor - np.array([self.x, *point])))
            links.append((j, three_d_length, self.crossing(start, point)))
        distances = {(-1, 0): 0.0}
        previous = {}
        queue = [(0.0, -1, 0)]
        while queue:
            length, index, state = heapq.heappop(queue)
            if length > distances[(index, state)] + 1e-12:
                continue
            if index == 0 and state == winding:
                path = []
                key = (index, state)
                while key in previous:
                    path.append(self.points[key[0]].tolist())
                    key = previous[key]
                path.append(start.tolist())
                path = list(reversed(path))
                return length, path
            edges = links if index == -1 else self.adj[index]
            for neighbor, edge, cross in edges:
                next_state = state + cross
                if abs(next_state) > 2:
                    continue
                key = (neighbor, next_state)
                new_length = length + edge
                if new_length < distances.get(key, float("inf")) - 1e-12:
                    distances[key] = new_length
                    previous[key] = (index, state)
                    heapq.heappush(queue, (new_length, neighbor, next_state))
        raise RuntimeError(
            f'no path from anchor to {self.mouth["id"]} with winding {winding}'
        )


def solve_package(package, mesh, suspension, descriptor):
    setup = suspension["suspension"]
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError("the native CAD collision solid is not watertight")
    bounds = descriptor["modelBounds"]
    center = (np.asarray(bounds["min"]) + np.asarray(bounds["max"])) / 2
    anchor = np.array([center[0], bounds["max"][1], center[2]]) + np.asarray(
        setup["anchor"]["offsetFromBoardBounds"], dtype=float
    )
    mouths = {p["id"]: p for side in setup["passages"].values() for p in side}
    if len(mouths) != 4 or len(setup["branches"]) != 2:
        raise ValueError("threaded-rope solver expects two loops with four mouths")
    radii = {branch["radius"] for branch in setup["branches"]}
    rest_lengths = {branch["restLength"] for branch in setup["branches"]}
    if len(radii) != 1 or len(rest_lengths) != 1:
        raise ValueError("both loops must have the same radius and length")
    radius = radii.pop()
    rest = rest_lengths.pop()
    clearance = setup["internalLoop"]["clearance"]
    sections = {
        key: Section(mouth, mesh, radius, clearance) for key, mouth in mouths.items()
    }
    print(
        "sections",
        [(key, len(value.points)) for key, value in sections.items()],
        flush=True,
    )

    def local_anchor(pose, height):
        translation = np.asarray(pose["translation"], dtype=float).copy()
        translation[1] = height
        return rotate_inverse(pose["rotation"], anchor - translation)

    def evaluate(pose, height, winding, with_routes=False):
        local = local_anchor(pose, height)
        lengths = {}
        routes = {}
        for key, section in sections.items():
            length, path = section.solve(local, winding[key])
            lengths[key] = length
            if with_routes:
                routes[key] = path
        branches = {}
        for branch in setup["branches"]:
            first, second = branch["passageIDs"]
            branches[branch["id"]] = (
                lengths[first]
                + lengths[second]
                + setup["internalLoop"]["channelLengthByBranchID"][branch["id"]]
            )
        return branches, routes

    output = {}
    for pose_id, pose in setup["canonicalPoses"].items():
        initial = local_anchor(pose, 0)
        winding = {
            key: section.winding_from_direction(
                initial, setup["internalLoop"]["windingByPassageID"][key]
            )
            for key, section in sections.items()
        }
        low, high = -2 * rest, 0.0
        if max(evaluate(pose, high, winding)[0].values()) > rest:
            raise ValueError(f"{pose_id}: loop is too short at the base pose")
        if max(evaluate(pose, low, winding)[0].values()) < rest:
            raise ValueError(f"{pose_id}: cannot bracket the hanging height")
        for _ in range(27):
            midpoint = (low + high) / 2
            if max(evaluate(pose, midpoint, winding)[0].values()) > rest:
                low = midpoint
            else:
                high = midpoint
        height = (low + high) / 2
        branches, routes = evaluate(pose, height, winding, True)
        if any(
            rest - length > 0.0005 or length - rest > 0.00001
            for length in branches.values()
        ):
            raise ValueError(
                f"{pose_id}: loop slack or stretch is excessive: {branches}"
            )
        contacts = {}
        second_mouths = {branch["passageIDs"][1] for branch in setup["branches"]}
        for key, path in routes.items():
            x = mouths[key]["pointInModel"][0]
            world = np.column_stack([np.full(len(path), x), np.asarray(path)])
            world[0] = local_anchor(pose, height)
            samples = []
            for start, end in zip(world, world[1:]):
                count = max(2, int(np.ceil(np.linalg.norm(end - start) / 0.0005)) + 1)
                samples.extend(
                    start + (end - start) * fraction
                    for fraction in np.linspace(0, 1, count)
                )
            signed = trimesh.proximity.signed_distance(mesh, np.asarray(samples))
            minimum = -float(signed.max())
            if minimum < radius - 0.00001:
                raise ValueError(f"{pose_id}/{key}: CAD collision at {minimum:.6f} m")
            points = world[1:]
            if key in second_mouths:
                points = points[::-1]
            contacts[key] = [
                [round(float(value), 9) for value in point] for point in points
            ]
            print(f"{pose_id}/{key}: CAD clearance {minimum:.6f} m", flush=True)
        output[pose_id] = {
            "height": round(height, 9),
            "lengths": branches,
            "winding": winding,
            "contacts": contacts,
        }
        print(f"{pose_id}: height {height:.6f} m, loops {branches}", flush=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--solid", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--apply", action="store_true", help="update generated poses in suspension.json"
    )
    action.add_argument(
        "--check",
        action="store_true",
        help="verify generated poses match suspension.json",
    )
    arguments = parser.parse_args()
    package = ROOT / "Hangboards" / arguments.package
    sidecar = package / "suspension.json"
    descriptor = package / "assets" / "primary.model.json"
    source = json.loads(arguments.solid.read_text())
    if source.get("sourcePackage") != arguments.package:
        raise ValueError("collision solid belongs to another package")
    cad_source = package / f"{arguments.package}.FCStd"
    if (
        source.get("sourceSHA256")
        != hashlib.sha256(cad_source.read_bytes()).hexdigest()
    ):
        raise ValueError("collision solid is stale relative to the native CAD source")
    data = json.loads(sidecar.read_text())
    model = json.loads(descriptor.read_text())
    if data["modelSHA256"] != model["modelSHA256"]:
        raise ValueError("suspension and model hashes differ")
    mesh = trimesh.Trimesh(
        vertices=source["vertices"], faces=source["triangles"], process=False
    )
    solved = solve_package(arguments.package, mesh, data, model)
    for pose_id, result in solved.items():
        pose = data["suspension"]["canonicalPoses"][pose_id]
        if arguments.check:
            if (
                abs(pose["translation"][1] - result["height"]) > 1e-8
                or pose.get("cordContactPoints") != result["contacts"]
            ):
                raise ValueError(f"{pose_id}: generated route cache is stale")
        else:
            pose["translation"][1] = result["height"]
            pose["cordContactPoints"] = result["contacts"]
    if arguments.apply:
        formatted = json.dumps(data, indent=2)
        number = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
        triplet = re.compile(
            rf"\[\n\s+({number}),\n\s+({number}),\n\s+({number})\n\s+\]"
        )
        formatted = triplet.sub(
            lambda match: f"[{match[1]}, {match[2]}, {match[3]}]", formatted
        )
        if json.loads(formatted) != data:
            raise AssertionError("route formatting changed the JSON data")
        sidecar.write_text(formatted + "\n")


if __name__ == "__main__":
    main()
