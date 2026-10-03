"""Solve settled threaded-rope routes against a native CAD wood solid.

The source sidecar supplies mouths, a connected-channel length, one overhead
anchor, loop length, pose rotations, and winding. This authoring command finds
the shortest nonpenetrating route in each winding class on a rope-radius
offset CAD section, then lowers the board until the longest loop is taut.
Its generated route cache stays in suspension.json, outside the USDZ.

A connected channel may be a curved pipe whose mouths lie in different
sections (Lattice Mini Bar) or a straight through-bore whose mouths share one
section (Crimptonite Helium Mobile). A through-bore splits its own section in
two; the solver bridges that gap to recover the exterior bearing outline and
reopens only the notch at the mouth being solved.

The sidecar's optional authoring-only `ropeSolver.sectionPlane` selects each
mouth's section plane. `mouth-x` (the default) cuts at the mouth's x, which
suits mouths on a constant-section bar (Mini Bar). `anchor` cuts the plane
through the mouth that contains the model depth axis and the overhead anchor,
which is the plane a taut leg actually hangs in; use it when the mouth sits
where the section varies along x, such as a rounded end (Helium Mobile). The
anchor plane follows the solved board height until it converges.

This is a static massless-rope equilibrium for bar-shaped boards whose end
sections are representative of the exterior bearing surface. It does not
model friction, rope elasticity, swing, or arbitrary 3D sliding along the bar.
"""

import argparse
import heapq
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]


def rotate_inverse(quaternion, vector):
    xyz = -np.asarray(quaternion[:3], dtype=float)
    turn = 2 * np.cross(xyz, vector)
    return vector + quaternion[3] * turn + np.cross(xyz, turn)


def bearing_section(pieces, mouth, offset, channel_profile=None):
    """Rope-centerline-free region of one section, open only at this mouth.

    One piece is the ordinary case. Several pieces mean a straight channel in
    this plane cut the section apart; close that gap so the exterior outline
    is intact, then subtract the channel's own clearance strip near the mouth
    so the rope can reach it. Other mouths in the plane stay closed.
    """
    wood = unary_union(pieces)
    grown = wood.buffer(offset, quad_segs=12)
    if len(pieces) == 1:
        return grown
    if channel_profile == "rectangular":
        # Circular morphological closing bows inward at a wide square mouth.
        # An explicitly authored straight rectangular slot has parallel depth
        # rims: join those rims without changing either remaining wood piece.
        ordered = sorted(pieces, key=lambda piece: piece.bounds[0])
        if len(ordered) != 2:
            raise ValueError("rectangular channel requires two section pieces")
        lower, upper = (piece.bounds for piece in ordered)
        if lower[2] >= upper[0] or max(abs(lower[i] - upper[i]) for i in (1, 3)) > 1e-6:
            raise ValueError("rectangular channel requires separated pieces with matching depth rims")
        closed = wood.union(box(lower[2], lower[1], upper[0], lower[3]))
    else:
        gap = max(a.distance(b) for i, a in enumerate(pieces) for b in pieces[i + 1:])
        bridge = gap / 2 + 1e-5
        closed = wood.buffer(bridge, quad_segs=12).buffer(-bridge, quad_segs=12)
        # A curved exit can have a narrow closest gap but a wider throat.
        # Keep the existing outline when it succeeds; otherwise increase only
        # this temporary topological closure, never the actual collision solid.
        # Every generated route is still checked against the full native wood.
        for _ in range(3):
            if closed.geom_type == "Polygon" and not closed.interiors:
                break
            bridge *= 2
            closed = wood.buffer(bridge, quad_segs=12).buffer(-bridge, quad_segs=12)
    if closed.geom_type != "Polygon" or closed.interiors:
        raise ValueError("section channel could not be bridged into one outline")
    channel = closed.buffer(offset, quad_segs=12).difference(grown)
    notch = channel.intersection(Point(mouth).buffer(offset * 1.25, quad_segs=12))
    if notch.is_empty:
        raise ValueError("mouth does not open into its through-bore channel")
    return closed.buffer(offset, quad_segs=12).difference(notch)


class Section:
    DEPTH = np.array([0.0, 0.0, 1.0])

    def __init__(self, mouth, mesh, radius, clearance, anchor=None, channel_profile=None):
        """Section through `mouth`: the x-plane, or the plane holding `anchor`.

        Plane coordinates are (distance along `up`, model z). For the x-plane
        `up` is model +Y, so they are exactly the model (y, z).
        """
        self.mouth = mouth
        origin = np.asarray(mouth["pointInModel"], dtype=float)
        if anchor is None:
            self.up = np.array([0.0, 1.0, 0.0])
            self.normal = np.array([1.0, 0.0, 0.0])
            plane_origin = [origin[0], 0, 0]
        else:
            toward = np.asarray(anchor, dtype=float) - origin
            up = toward - toward.dot(self.DEPTH) * self.DEPTH
            self.up = up / np.linalg.norm(up)
            self.normal = np.cross(self.up, self.DEPTH)
            plane_origin = origin
        self.offset = float(origin @ self.normal)
        cross = mesh.section(plane_origin=plane_origin, plane_normal=self.normal)
        assert cross is not None and cross.discrete
        self.polygon = orient(
            bearing_section(
                [Polygon(self.to_plane(loop)) for loop in cross.discrete],
                self.to_plane(origin),
                radius + clearance,
                channel_profile,
            ),
            1,
        )
        assert self.polygon.is_valid and not self.polygon.interiors
        self.points = np.vstack(
            [
                self.to_plane(origin),
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

    def to_plane(self, points):
        points = np.asarray(points, dtype=float)
        return np.stack([points @ self.up, points[..., 2]], axis=-1)

    def to_world(self, points):
        points = np.asarray(points, dtype=float)
        return (
            points[..., :1] * self.up
            + points[..., 1:2] * self.DEPTH
            + self.offset * self.normal
        )

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
        start = self.to_plane(anchor)
        assert not self.polygon.contains(Point(start))
        links = []
        for j, point in enumerate(self.points):
            if LineString([start, point]).relate(self.polygon)[0] != "F":
                continue
            three_d_length = float(np.linalg.norm(anchor - self.to_world(point)))
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


def solve_direct_loop(mesh, setup, descriptor, native_solid=None):
    """Settle a single loop with unobstructed rising legs from CAD mouths.

    The connected CAD spine supplies the entire interior route. Reject any
    bearing or collision instead of drawing substitute contacts by hand.
    """
    branch = setup["branches"][0]
    mouths = {p["id"]: p for side in setup["passages"].values() for p in side}
    first, second = (np.asarray(mouths[key]["pointInModel"], dtype=float) for key in branch["passageIDs"])
    points = setup["internalLoop"]["channelPointsByBranchID"][branch["id"]]
    channel_length = sum(np.linalg.norm(np.asarray(b) - a) for a, b in zip(points, points[1:]))
    declared = setup["internalLoop"]["channelLengthByBranchID"][branch["id"]]
    if abs(channel_length - declared) > 1e-6:
        raise ValueError("channel length differs from its native spine")
    bounds = descriptor["modelBounds"]
    center = (np.asarray(bounds["min"]) + np.asarray(bounds["max"])) / 2
    anchor = np.array([center[0], bounds["max"][1], center[2]]) + setup["anchor"]["offsetFromBoardBounds"]
    rest = branch["restLength"]
    output = {}
    for pose_id, pose in setup["canonicalPoses"].items():
        def local(height):
            translation = np.asarray(pose["translation"], dtype=float).copy()
            translation[1] = height
            return rotate_inverse(pose["rotation"], anchor - translation)
        def length(height):
            support = local(height)
            return np.linalg.norm(support - first) + np.linalg.norm(support - second) + channel_length
        low, high = -2 * rest, 0.0
        if length(high) > rest or length(low) < rest:
            raise ValueError("cannot bracket the threaded loop hanging height")
        for _ in range(40):
            midpoint = (low + high) / 2
            if length(midpoint) > rest: low = midpoint
            else: high = midpoint
        height = (low + high) / 2
        support = local(height)
        segments = [(support, first), *zip(points, points[1:]), (second, support)]
        samples = np.concatenate([np.linspace(a, b, max(2, math.ceil(np.linalg.norm(np.asarray(b)-a)/0.0005)+1)) for a,b in segments])
        if native_solid is not None:
            import FreeCAD as App, Part
            def signed_clearance(point):
                vertex = App.Vector(point[0]*1000, -point[2]*1000, point[1]*1000)
                distance = native_solid.distToShape(Part.Vertex(vertex))[0] / 1000
                return -distance if native_solid.isInside(vertex, 1e-7, True) else distance
            clearance = min(signed_clearance(point) for point in samples)
        else:
            clearance = -float(trimesh.proximity.signed_distance(mesh, samples).max())
        required_clearance = branch["radius"] + setup["internalLoop"]["clearance"]
        if clearance < required_clearance - 1e-5:
            raise ValueError(f"{pose_id}: threaded channel or free leg collides with CAD: {clearance}")
        contacts = {key: [mouths[key]["pointInModel"]] for key in branch["passageIDs"]}
        output[pose_id] = {"height": round(height, 9), "lengths": {branch["id"]: float(length(height))}, "contacts": contacts}
        print(f"{pose_id}: single loop {length(height):.9f} m; CAD clearance {clearance:.9f} m", flush=True)
    return output


def solve_package(package, mesh, suspension, descriptor):
    setup = suspension["suspension"]
    if setup["type"] == "threadedLoopCord":
        mouths = {p["id"]: p for side in setup["passages"].values() for p in side}
        if len(mouths) != 2 or len(setup["branches"]) != 1:
            raise ValueError("threadedLoopCord requires one connected loop with two mouths")
        passage_ids = setup["branches"][0]["passageIDs"]
        if len(passage_ids) != 2 or set(passage_ids) != set(mouths):
            raise ValueError("threadedLoopCord passageIDs must name both distinct mouths")
        native = mesh.metadata.get("nativeSolid")
        if native is None and (not mesh.is_watertight or not mesh.is_winding_consistent):
            raise ValueError("single loop clearance requires the native CAD solid or a watertight tessellation")
        return solve_direct_loop(mesh, setup, descriptor, native)
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError("the native CAD collision solid is not watertight")
    bounds = descriptor["modelBounds"]
    center = (np.asarray(bounds["min"]) + np.asarray(bounds["max"])) / 2
    anchor = np.array([center[0], bounds["max"][1], center[2]]) + np.asarray(
        setup["anchor"]["offsetFromBoardBounds"], dtype=float
    )
    mouths = {p["id"]: p for side in setup["passages"].values() for p in side}
    branch_count = len(setup["branches"])
    if branch_count not in (1, 2) or len(mouths) != 2 * branch_count:
        raise ValueError("threaded-rope solver expects one or two loops with two mouths each")
    paired_ids = [key for branch in setup["branches"] for key in branch["passageIDs"]]
    if (any(len(branch["passageIDs"]) != 2 for branch in setup["branches"])
            or len(set(paired_ids)) != len(paired_ids) or set(paired_ids) != set(mouths)):
        raise ValueError("threaded-rope branches must pair every distinct mouth exactly once")
    radii = {branch["radius"] for branch in setup["branches"]}
    rest_lengths = {branch["restLength"] for branch in setup["branches"]}
    if len(radii) != 1 or len(rest_lengths) != 1:
        raise ValueError("both loops must have the same radius and length")
    radius = radii.pop()
    rest = rest_lengths.pop()
    clearance = setup["internalLoop"]["clearance"]
    plane = suspension.get("ropeSolver", {}).get("sectionPlane", "mouth-x")
    channel_profile = suspension.get("ropeSolver", {}).get("channelProfile")
    if channel_profile not in (None, "rectangular") or (channel_profile == "rectangular" and plane != "mouth-x"):
        raise ValueError("rectangular channelProfile requires the mouth-x section plane")
    if plane not in ("mouth-x", "anchor"):
        raise ValueError(f"unknown ropeSolver.sectionPlane {plane!r}")

    def build_sections(local=None):
        built = {
            key: Section(mouth, mesh, radius, clearance, local, channel_profile)
            for key, mouth in mouths.items()
        }
        print(
            "sections",
            [(key, len(value.points)) for key, value in built.items()],
            flush=True,
        )
        return built

    sections = build_sections() if plane == "mouth-x" else {}

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

    def settle(pose_id, pose):
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
        return (low + high) / 2, winding

    output = {}
    for pose_id, pose in setup["canonicalPoses"].items():
        if plane == "mouth-x":
            height, winding = settle(pose_id, pose)
        else:
            height = 0.0
            for _ in range(20):
                sections = build_sections(local_anchor(pose, height))
                settled, winding = settle(pose_id, pose)
                converged = abs(settled - height) < 1e-8
                height = settled
                if converged:
                    break
            else:
                raise ValueError(f"{pose_id}: anchor-plane sections did not converge")
            sections = build_sections(local_anchor(pose, height))
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
            world = sections[key].to_world(path)
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
    parser.add_argument("--presentation", help="select a schema-2 sidecar entry")
    parser.add_argument("--equipment-object", help="select a reusable unit's sidecar entry")
    parser.add_argument("--report", type=Path, help="retain generated length and native-clearance results")
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
    source = json.loads(arguments.solid.read_text())
    if source.get("sourcePackage") != arguments.package:
        raise ValueError("collision solid belongs to another package")
    cad_source = package / f"{arguments.package}.FCStd"
    if (
        source.get("sourceSHA256")
        != hashlib.sha256(cad_source.read_bytes()).hexdigest()
    ):
        raise ValueError("collision solid is stale relative to the native CAD source")
    document = json.loads(sidecar.read_text())
    if document.get("schemaVersion") == 2 and "entries" in document:
        selected = [entry for entry in document["entries"] if entry["presentationID"] == arguments.presentation
                    and entry.get("equipmentObjectID") == arguments.equipment_object]
        if len(selected) != 1:
            raise ValueError("select exactly one sidecar entry with --presentation and optional --equipment-object")
        data = selected[0]
    else:
        data = document
    import use_hangboard_packages
    from hangboard_packages import cad_source as source_metadata
    board = source_metadata.load_board(cad_source)
    presentation = next(item for item in board["presentations"] if item["id"] == data["presentationID"])
    descriptor = package / presentation["media"]["descriptorPath"]
    model = json.loads(descriptor.read_text())
    if data["modelSHA256"] != model["modelSHA256"]:
        raise ValueError("suspension and model hashes differ")
    mesh = trimesh.Trimesh(
        vertices=source["vertices"], faces=source["triangles"], process=False
    )
    setups = data.get("instanceSuspensions", {"single": data.get("suspension")})
    if any(setup["type"] == "threadedLoopCord" for setup in setups.values()):
        try:
            import FreeCAD as App
        except ImportError as error:
            raise ValueError("run the single-loop solve with FreeCAD Python for exact native-solid clearance") from error
        cad_document = App.openDocument(str(cad_source.resolve()))
        native_solid = cad_document.getObject(source["sourceFeature"]).Shape
        if not native_solid.isValid() or len(native_solid.Solids) != 1:
            raise ValueError("collision source is not one valid native CAD solid")
        mesh.metadata["nativeSolid"] = native_solid
    native_routes = data.get("ropeSolver", {}).get("method") == "nativeRoutes"
    solutions = {}
    for equipment_id, setup in setups.items():
        import copy
        local_data = {**data, "suspension": copy.deepcopy(setup)}
        if native_routes:
            from native_cord_routes import solve_native_routes
            solved = solve_native_routes(mesh, local_data, model)
        else:
            solved = solve_package(arguments.package, mesh, local_data, model)
        solutions[equipment_id] = solved
        for pose_id, result in solved.items():
            pose = setup["canonicalPoses"][pose_id]
            route_key = "wrappedRoutes" if native_routes else "cordContactPoints"
            routes = result["routes" if native_routes else "contacts"]
            if arguments.check:
                if abs(pose["translation"][1] - result["height"]) > 1e-8 or pose.get(route_key) != routes:
                    raise ValueError(f"{equipment_id}/{pose_id}: generated route cache is stale")
            else:
                pose["translation"][1] = result["height"]
                pose[route_key] = routes
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        report = {"package": arguments.package, "presentationID": data["presentationID"],
            "modelSHA256": model["modelSHA256"], "sourceSHA256": source["sourceSHA256"],
            "method": "nativeRoutes" if native_routes else "internalLoop"}
        if set(solutions) == {"single"}:
            report["poses"] = solutions["single"]
        else:
            report["instances"] = solutions
        arguments.report.write_text(json.dumps(report, indent=2)+"\n")

    if arguments.apply:
        formatted = json.dumps(document, indent=2)
        number = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
        triplet = re.compile(
            rf"\[\n\s+({number}),\n\s+({number}),\n\s+({number})\n\s+\]"
        )
        formatted = triplet.sub(
            lambda match: f"[{match[1]}, {match[2]}, {match[3]}]", formatted
        )
        if json.loads(formatted) != document:
            raise AssertionError("route formatting changed the JSON data")
        sidecar.write_text(formatted + "\n")


if __name__ == "__main__":
    main()
