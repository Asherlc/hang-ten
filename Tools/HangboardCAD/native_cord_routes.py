"""Native-solid route solver for evidenced exterior cords and partial leads.

Inputs are terminal mouths or two exterior bearing stations, never drawn
centerlines. Sections preserve open grooves, multiple solids and voids. Every
generated visible segment must also clear the complete closed 3D CAD solid.
"""
from __future__ import annotations
import heapq
import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon
from hangboard_packages.cord_paths import validate_cord_paths


class _CollarCollision(ValueError):
    """A certified collision eligible for a larger generated section margin."""


class NativeSection:
    @classmethod
    def for_span(cls, mesh, start, finish, preferred_normal, radius, clearance, plane_axis=None, rotation_degrees=0):
        """A section through both endpoints, with optional generated chord rotation."""
        span = np.asarray(finish, dtype=float) - np.asarray(start, dtype=float)
        distance = np.linalg.norm(span)
        if not np.isfinite(distance) or distance <= 1e-10:
            raise ValueError("native cord span endpoints must be distinct and finite")
        axis = span / distance
        normal = np.asarray(preferred_normal, dtype=float)
        if plane_axis is not None:
            normal = np.cross(axis, np.asarray(plane_axis, dtype=float))
        else:
            normal = normal - np.dot(normal, axis) * axis
        if np.linalg.norm(normal) <= 1e-10:
            seed = np.eye(3)[np.argmin(np.abs(axis))]
            normal = np.cross(axis, seed)
        if rotation_degrees:
            # Rotate the SECTION, not either endpoint, around their chord.
            angle = np.radians(rotation_degrees)
            normal = normal*np.cos(angle) + np.cross(axis, normal)*np.sin(angle)
        return cls(mesh, finish, normal, radius, clearance)

    def __init__(self, mesh, origin, normal, radius, clearance):
        self.origin = np.asarray(origin, dtype=float)
        normal = np.asarray(normal, dtype=float)
        self.normal = normal / np.linalg.norm(normal)
        seed = np.eye(3)[np.argmin(np.abs(self.normal))]
        self.up = np.cross(self.normal, seed)
        self.up /= np.linalg.norm(self.up)
        self.across = np.cross(self.normal, self.up)
        cross = mesh.section(plane_origin=self.origin, plane_normal=self.normal)
        if cross is None:
            raise ValueError("native section misses the CAD solid")
        wood = Polygon()
        for loop in cross.discrete:
            polygon = Polygon(self.to_plane(loop))
            if not polygon.is_valid:
                raise ValueError("native section has an invalid boundary")
            # Even/odd boundaries retain real holes rather than filling them.
            wood = wood.symmetric_difference(polygon)
        self.obstacle = wood.buffer(radius + clearance, quad_segs=8)
        self._rebuild_graph()

    def _rebuild_graph(self):
        self.points = []
        pieces = [self.obstacle] if self.obstacle.geom_type == "Polygon" else list(self.obstacle.geoms)
        for piece in pieces:
            for ring in [piece.exterior, *piece.interiors]:
                self.points.extend(np.asarray(ring.coords)[:-1])
        self.points = np.asarray(self.points)
        self.adj = {}

    def reserve_tube(self, start, finish, exclusion_radius):
        """Reserve another generated collar, including this cord's radius.

        A capsule parallel to this plane, at distance d, intersects it in a
        capsule of radius sqrt(R²-d²). Oblique capsules have different sections;
        reject them explicitly rather than silently projecting their volume.
        """
        start, finish = np.asarray(start, dtype=float), np.asarray(finish, dtype=float)
        span = finish - start
        if start.shape != (3,) or finish.shape != (3,) or not np.isfinite([start, finish]).all() \
                or not np.isfinite(exclusion_radius) or exclusion_radius <= 0 or np.linalg.norm(span) <= 1e-10:
            raise ValueError("native occupied collar requires finite distinct endpoints and a positive radius")
        if abs(float(span @ self.normal)) / np.linalg.norm(span) > 1e-8:
            raise ValueError("native occupied collar must be parallel to the routing section; oblique reservation is unsupported")
        distance = abs(float((start - self.origin) @ self.normal))
        if distance >= exclusion_radius:
            return
        planar_radius = float(np.sqrt(exclusion_radius**2 - distance**2))
        # Circumscribe the exact circular section: Shapely's usual inscribed
        # polygon would underestimate capsule clearance between its vertices.
        polygon_radius = planar_radius / np.cos(np.pi / 32)
        capsule = LineString(self.to_plane([start, finish])).buffer(polygon_radius, quad_segs=8)
        self.obstacle = self.obstacle.union(capsule)
        self._rebuild_graph()

    def neighbors(self, index):
        if index not in self.adj:
            point = self.points[index]
            self.adj[index] = [(other, float(np.linalg.norm(point-candidate)))
                for other, candidate in enumerate(self.points)
                if other != index and self.visible(point, candidate)]
        return self.adj[index]

    def to_plane(self, points):
        points = np.asarray(points) - self.origin
        return np.stack([points @ self.up, points @ self.across], axis=-1)

    def to_world(self, points):
        points = np.asarray(points)
        return self.origin + points[..., :1]*self.up + points[..., 1:2]*self.across

    def visible(self, a, b):
        return LineString([a,b]).relate(self.obstacle)[0] == "F"

    def route(self, start, finish):
        start, finish = np.asarray(start,dtype=float), np.asarray(finish,dtype=float)
        first, last = self.to_plane(start), self.to_plane(finish)
        if self.obstacle.contains(Point(first)) or self.obstacle.contains(Point(last)):
            raise ValueError("cord terminal or support is inside the rope-offset native solid")
        if self.visible(first,last):
            return np.array([start, (start+finish)/2, finish])
        n = len(self.points)
        points = np.vstack([self.points, first, last])
        # Explore reachable vertices only. Native sections can have thousands
        # of vertices in closed holes that neither endpoint can reach.
        endpoints = {n: [], n+1: []}
        links = {}
        for index, endpoint in ((n,first),(n+1,last)):
            for j, point in enumerate(self.points):
                if self.visible(endpoint,point):
                    length = float(np.linalg.norm((start if index==n else finish)-self.to_world(point)))
                    endpoints[index].append((j,length))
                    links.setdefault(j, []).append((index,length))
        distances, previous, queue = {n:0.0},{},[(0.0,n)]
        while queue:
            distance,index = heapq.heappop(queue)
            if distance > distances[index]+1e-12: continue
            if index == n+1:
                indices = [index]
                while indices[-1] != n: indices.append(previous[indices[-1]])
                path = self.to_world(points[indices[::-1]])
                path[0],path[-1] = start,finish
                return path
            adjacency = self.neighbors(index) + links.get(index, []) if index < n else endpoints[index]
            for neighbor, edge in adjacency:
                candidate = distance+edge
                if candidate < distances.get(neighbor,float("inf"))-1e-12:
                    distances[neighbor],previous[neighbor] = candidate,index
                    heapq.heappush(queue,(candidate,neighbor))
        raise ValueError("no exterior native-solid route connects these stations")


def checked_clearance(mesh, path, radius):
    """Certify the complete polyline using signed-distance Lipschitz bounds.

    Endpoint samples alone cannot exclude a thin obstacle between them. Signed
    distance is 1-Lipschitz, so an interval of length L whose endpoint exterior
    distances are a and b has minimum distance at least (a+b-L)/2. Subdivide
    every uncertified interval until it clears the radius (10 micrometre
    numerical tolerance) or an actual collision is found.
    """
    points = np.asarray(path, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 \
            or not np.isfinite(points).all() or not np.isfinite(radius) or radius <= 0:
        raise ValueError("native cord clearance requires a finite polyline and positive radius")
    limit = radius - 1e-5
    remaining_samples = 131072
    def distances(samples):
        nonlocal remaining_samples
        remaining_samples -= len(samples)
        if remaining_samples < 0:
            raise ValueError("native CAD cord clearance could not be certified within the sample budget")
        values = np.concatenate([-trimesh.proximity.signed_distance(mesh, batch)
            for batch in np.array_split(samples, max(1, int(np.ceil(len(samples)/2048))))])
        minimum = float(values.min())
        if not np.isfinite(values).all() or minimum < limit:
            raise ValueError(f"native CAD cord collision: clearance {minimum:.9f} m < radius {radius:.9f} m")
        return values
    values = distances(points)
    starts, ends = points[:-1], points[1:]
    first, last = values[:-1], values[1:]
    certified = float("inf")
    for _ in range(60):
        spans = np.linalg.norm(ends-starts, axis=1)
        lower = (first+last-spans)/2
        accepted = lower >= limit
        if accepted.any():
            certified = min(certified, float(lower[accepted].min()))
        pending = ~accepted
        if not pending.any():
            return certified
        starts, ends, first, last = starts[pending], ends[pending], first[pending], last[pending]
        if len(starts) > 32768:
            raise ValueError("native CAD cord clearance could not be certified within the interval budget")
        middle = (starts+ends)/2
        midpoint = distances(middle)
        starts, ends = np.vstack([starts, middle]), np.vstack([middle, ends])
        first, last = np.concatenate([first, midpoint]), np.concatenate([midpoint, last])
    raise ValueError("native CAD cord clearance could not be certified")


def length(path):
    return sum(float(np.linalg.norm(b-a)) for a,b in zip(path,path[1:]))


def native_mouth_collar(mesh, mouth, mouth_axis, radius, clearance):
    """Derive a clear exterior endpoint along an evidenced native bore axis.

    The mouth is the only authored point. The solid's support plane along the
    outward axis determines the short exit segment; no route station or hidden
    connection is authored. Certify the entire segment, including its mouth.
    """
    mouth = np.asarray(mouth, dtype=float)
    axis = np.asarray(mouth_axis, dtype=float)
    if mouth.shape != (3,) or axis.shape != (3,) or not np.isfinite(mouth).all() \
            or not np.isfinite(axis).all() or np.linalg.norm(axis) <= 1e-10:
        raise ValueError("native mouthAxis requires a finite mouth and nonzero direction")
    axis = axis / np.linalg.norm(axis)
    support = float(np.max(np.asarray(mesh.vertices) @ axis))
    distance = max(0.0, support - float(mouth @ axis)) + radius + clearance
    exterior = mouth + axis * distance
    checked_clearance(mesh, np.asarray([mouth, exterior]), radius)
    return exterior


def solve_native_routes(mesh, data, descriptor):
    """Preserve valid preferred routes; recover collared-lead conflicts only.

    Recovery is a bounded deterministic search of native section orientations,
    not a global minimum or a full rope-physics simulation. Actual mouths and
    bore axes stay fixed; each attempt derives its collar endpoint from the
    native support plane and clearance margin, then settles and certifies anew.
    """
    setup = data["suspension"]
    if not setup["canonicalPoses"]:
        return _solve_native_routes(mesh, data, descriptor)
    collar_ids = sorted(strand["id"] for strand in setup["strands"]
                        if strand["kind"] == "lead" and "mouthAxis" in
                        data["ropeSolver"]["terminalsByStrandID"].get(strand["id"], {}))
    if len(collar_ids) < 2:
        return _solve_native_routes(mesh, data, descriptor)
    output = {}
    for pose_id, pose in setup["canonicalPoses"].items():
        one = {**data, "suspension": {**setup, "canonicalPoses": {pose_id: pose}}}
        try:
            output.update(_solve_native_routes(mesh, one, descriptor))
            continue
        except ValueError as error:
            initial_error = str(error)
            conflict = initial_error.startswith(("native cord tubes intersect:", "native cord paths intersect:",
                                                "native cord paths retrace:", "native occupied collar must be parallel"))
            if len(collar_ids) < 2 or not conflict:
                raise
        failures = []
        solved = False
        # Ascending maximum deviation, then total deviation, stable strand IDs
        # and signs. At most 5 * (2N + N(N-1)) candidates for N collared leads.
        for angle in (5, 10, 20, 35, 50):
            candidates = [{identifier: sign*angle} for identifier in collar_ids for sign in (-1, 1)]
            candidates += [{first: sign*angle, second: -sign*angle}
                           for index, first in enumerate(collar_ids) for second in collar_ids[index+1:]
                           for sign in (-1, 1)]
            for rotations in candidates:
                try:
                    # An oblique section cannot use the parallel capsule helper.
                    # Try its actual native route without that helper and require
                    # the complete 3D collar/path tube certificate unchanged.
                    result = _solve_native_routes(mesh, one, descriptor, rotations, False)[pose_id]
                except ValueError as error:
                    failures.append({"rotationsDegrees": rotations, "error": str(error)})
                    continue
                result["sectionOrientationRecovery"] = {
                    "initialConflict": initial_error, "rotationsDegrees": rotations,
                    "rejectedCandidates": failures,
                    "policy": "First certified candidate in bounded ascending maximum/total section deviation order; no global optimum claim."}
                output[pose_id] = result
                solved = True
                break
            if solved:
                break
        if not solved:
            raise ValueError(f"{pose_id}: bounded native section orientation search exhausted after {len(failures)} candidates; "
                             f"initial conflict: {initial_error}; final failure: {failures[-1]['error']}")
    return output


def _solve_native_routes(mesh, data, descriptor, section_rotations=None, allow_collar_reservation=True):
    from solve_threaded_rope import rotate_inverse
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError("native CAD collision solid must be closed and consistently wound")
    setup, solver = data["suspension"], data["ropeSolver"]
    geometry=solver["terminalsByStrandID"]
    strands=setup["strands"]
    if set(geometry) != {strand["id"] for strand in strands}:
        raise ValueError("native cord terminals must exactly match visible strands")
    bounds=descriptor["modelBounds"]
    anchor=(np.asarray(bounds["min"])+np.asarray(bounds["max"]))/2
    anchor[1]=bounds["max"][1]
    anchor+=np.asarray(setup["anchor"]["offsetFromBoardBounds"])
    direction=float(solver.get("supportDirection",1))
    clearance=float(solver["clearance"])
    plane_mode = solver.get("sectionPlane", "fixed")
    if plane_mode not in ("fixed", "anchor"):
        raise ValueError("nativeRoutes sectionPlane must be fixed or anchor")
    collar_ids = set()
    for strand in strands:
        entry = geometry[strand["id"]]
        if "mouthAxis" in entry:
            if strand["kind"] != "lead" or plane_mode != "anchor" or len(entry["points"]) != 1:
                raise ValueError("native mouthAxis requires one lead mouth and an anchor section")
            collar_ids.add(strand["id"])
    output={}
    fixed_sections = {}
    for pose_id,pose in setup["canonicalPoses"].items():
        translation=np.asarray(pose["translation"],dtype=float).copy()
        margins = {strand["id"]: clearance for strand in strands}
        lead_ends = {}
        reserve_collars = False
        def build_sections(height):
            translation[1] = height
            local = rotate_inverse(pose["rotation"], anchor - translation)
            result = {}
            for strand in strands:
                entry = geometry[strand["id"]]
                points = entry["points"]
                if len(points) != (1 if strand["kind"] == "lead" else 2):
                    raise ValueError("native cord needs one terminal for a lead, two bearing stations for a loop or segment")
                first_point = lead_ends.get(strand["id"], points[0])
                fixed = None
                if plane_mode != "anchor" or strand["kind"] != "lead":
                    if strand["id"] not in fixed_sections:
                        fixed_sections[strand["id"]] = NativeSection(mesh, points[0], entry["planeNormal"], strand["radius"], clearance)
                    fixed = fixed_sections[strand["id"]]
                first, last = fixed, fixed
                if plane_mode == "anchor" and strand["kind"] != "segment":
                    first = NativeSection.for_span(mesh, local, first_point, entry["planeNormal"], strand["radius"], margins[strand["id"]],
                                                   plane_axis=entry.get("planeAxis"),
                                                   rotation_degrees=(section_rotations or {}).get(strand["id"], 0))
                    if reserve_collars:
                        for other in strands:
                            other_id = other["id"]
                            if other_id in collar_ids and other_id != strand["id"]:
                                first.reserve_tube(geometry[other_id]["points"][0], lead_ends[other_id],
                                                   strand["radius"] + other["radius"] + margins[strand["id"]])
                    if strand["kind"] == "loop":
                        last = NativeSection.for_span(mesh, points[1], local, entry["planeNormal"], strand["radius"], clearance,
                                                      plane_axis=entry.get("planeAxis"))
                result[strand["id"]] = (first, fixed, last)
            return result

        sections = {}

        def evaluate(height,check=False):
            translation[1]=height
            local=rotate_inverse(pose["rotation"],anchor-translation)
            paths,ratios,clearances,full_paths={},{},{},{}
            for strand in strands:
                identifier=strand["id"]
                points=np.asarray(geometry[identifier]["points"],dtype=float)
                first_section, bearing_section, last_section = sections[identifier]
                if strand["kind"]=="lead":
                    path=first_section.route(local,lead_ends.get(identifier,points[0]))
                    if identifier in lead_ends:
                        path=np.vstack([path,points[0]])
                elif strand["kind"]=="segment": path=bearing_section.route(points[0],points[1])
                else:
                    first=first_section.route(local,points[0])
                    bearing=bearing_section.route(points[0],points[1])
                    second=last_section.route(points[1],local)
                    path=np.vstack([first,bearing[1:],second[1:]])
                ratios[identifier]=length(path)/strand["restLength"]
                # The free support stays in world space. Store only body-space
                # points; runtime adds its fixed support to the lead/loop ends.
                route=path[1:] if strand["kind"] in {"lead","loop"} else path
                if strand["kind"]=="loop": route=route[:-1]
                if len(route)<3:
                    route=np.vstack([route[0],(route[0]+route[-1])/2,route[-1]]) if len(route)>1 else np.vstack([
                        local+(route[0]-local)*.98, local+(route[0]-local)*.99,route[0]])
                paths[identifier]=[[round(float(v),9) for v in point] for point in route]
                # Certify what the renderer receives, including the rounded
                # hanging height, rather than only the solver's internal path.
                cached=np.asarray(paths[identifier])
                runtime_translation=translation.copy()
                runtime_translation[1]=round(float(height),9)
                support=rotate_inverse(pose["rotation"],anchor-runtime_translation)
                if strand["kind"] in {"lead","loop"}: cached=np.vstack([support,cached])
                if strand["kind"]=="loop": cached=np.vstack([cached,support])
                full_paths[identifier]=cached
                if check:
                    try:
                        clearances[identifier]=checked_clearance(mesh,cached,strand["radius"])
                    except ValueError as error:
                        error_type = _CollarCollision if identifier in collar_ids and str(error).startswith("native CAD cord collision:") else ValueError
                        raise error_type(f"{pose_id}/{identifier}: {error}") from error
            if check:
                validate_cord_paths(full_paths, {strand["id"]: strand["radius"] for strand in strands})
            return paths,ratios,clearances

        def settle():
            high = 0.0
            if max(evaluate(high)[1].values()) > 1+1e-6:
                raise ValueError(f"{pose_id}: declared visible cord is too short at the base pose")
            distance = 2*max(strand["restLength"] for strand in strands)
            low = -direction*distance
            if max(evaluate(low)[1].values()) < 1:
                raise ValueError(f"{pose_id}: cannot bracket native hanging height")
            for _ in range(27):
                middle = (low+high)/2
                if max(evaluate(middle)[1].values()) > 1: low = middle
                else: high = middle
            return (low+high)/2

        # Oblique sections can underestimate distance to the full 3D solid.
        # Only a generated bore-axis collar permits expanding that section
        # without swallowing the actual mouth. Retry deterministically; every
        # result still requires the unchanged continuous 3D and tube gates.
        margin_attempt = 0
        # Keep already-valid caches exact. Reserve occupied collars only after
        # the unchanged full-path gate detects a genuine interstrand overlap.
        # Five solid-clearance margins plus at most one occupied-collar retry.
        for _ in range(6):
            for strand in strands:
                identifier = strand["id"]
                if identifier in collar_ids:
                    margins[identifier] = clearance + margin_attempt * strand["radius"] / 4
                    entry = geometry[identifier]
                    lead_ends[identifier] = native_mouth_collar(mesh, entry["points"][0],
                        entry["mouthAxis"], strand["radius"], margins[identifier])
            sections = build_sections(0)
            height = settle()
            if plane_mode == "anchor":
                for _ in range(20):
                    sections = build_sections(height)
                    settled = settle()
                    converged = abs(settled-height) < 1e-8
                    height = settled
                    if converged: break
                else:
                    raise ValueError(f"{pose_id}: native anchor-plane sections did not converge")
                sections = build_sections(height)
            try:
                paths,ratios,minimums=evaluate(height,True)
            except _CollarCollision:
                if margin_attempt == 4:
                    raise
                margin_attempt += 1
                continue
            except ValueError as error:
                if allow_collar_reservation and not reserve_collars and len(collar_ids) > 1 and str(error).startswith("native cord tubes intersect:"):
                    reserve_collars = True
                    continue
                raise
            output[pose_id]={"height":round(height,9),"routes":paths,"lengthRatios":ratios,"minimumClearance":minimums}
            if collar_ids:
                output[pose_id]["mouthCollars"] = {identifier: {
                    "sectionClearance": margins[identifier],
                    "derivedExteriorPoint": lead_ends[identifier].tolist(),
                    "attempt": margin_attempt + 1} for identifier in sorted(collar_ids)}
            if reserve_collars:
                output[pose_id]["occupiedCollarsReserved"] = True
            break
    return output
