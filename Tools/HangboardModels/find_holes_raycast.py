import bpy, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
usdz_path = argv[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=usdz_path)

deps = bpy.context.evaluated_depsgraph_get()
scene = bpy.context.scene
DIR = Vector((0.0, 1.0, 0.0))
START_Y = -1.0

# board bounds
minx = miny = minz = 1e9
maxx = maxy = maxz = -1e9
for o in scene.objects:
    if o.type != "MESH":
        continue
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        minx, maxx = min(minx, w.x), max(maxx, w.x)
        minz, maxz = min(minz, w.z), max(maxz, w.z)

STEP = 0.0005  # 0.5 mm
nx = int((maxx - minx) / STEP) + 1
nz = int((maxz - minz) / STEP) + 1
print(f"scanning {nx} x {nz} = {nx*nz} rays over x[{minx:.3f},{maxx:.3f}] z[{minz:.3f},{maxz:.3f}]")

hit_grid = {}
for ix in range(nx):
    x = minx + ix * STEP
    for iz in range(nz):
        z = minz + iz * STEP
        hit, loc, nrm, idx, obj, mat = scene.ray_cast(deps, Vector((x, START_Y, z)), DIR)
        hit_grid[(ix, iz)] = (hit, loc.y if hit else None, obj.name if hit else None)

misses = {k for k, v in hit_grid.items() if not v[0]}
print(f"total misses: {len(misses)}")

# cluster misses by 4-connectivity
visited = set()
clusters = []
for start in misses:
    if start in visited:
        continue
    stack = [start]
    comp = set()
    while stack:
        p = stack.pop()
        if p in comp or p not in misses:
            continue
        comp.add(p)
        ix, iz = p
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (ix + d[0], iz + d[1])
            if q in misses and q not in comp:
                stack.append(q)
    visited |= comp
    clusters.append(comp)

clusters.sort(key=len, reverse=True)
print(f"miss clusters: {len(clusters)}")
print("(largest cluster is the background outside the board silhouette)")
for c in clusters[:20]:
    xs = [minx + ix * STEP for ix, iz in c]
    zs = [minz + iz * STEP for ix, iz in c]
    cx = sum(xs) / len(xs)
    cz = sum(zs) / len(zs)
    w = max(xs) - min(xs)
    h = max(zs) - min(zs)
    print(f"  cells={len(c):>6}  center=({cx:+.4f}, {cz:+.4f})  extent=({w*1000:.1f}mm x {h*1000:.1f}mm)")
