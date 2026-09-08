"""Export the saved Blender actions as evaluated, post-subdivision surfaces."""
import bpy, json
from mathutils import Matrix, Vector
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parents[1] / "HangTen/Resources/GripHand/hand-mesh.json"
# Reflected canonical view: fingers +Y, thumb -X, palm +Z, wrist around Y=0.
TRANSFORM = Matrix(((0,-20,0,0),(0,0,-20,1.11550942),(-20,0,0,.5),(0,0,0,1)))
NORMAL = TRANSFORM.to_3x3().inverted().transposed()
def activate(rig, name):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

def export():
    rig = bpy.data.objects["GripHandRig"]; obj = bpy.data.objects["GripHandSurface"]
    previous = rig.animation_data.action.name
    result = {"schemaVersion":2, "indices":[], "digitIndices":[], "highlightWeights":[], "poses":{}}
    result["source"] = {
        "url": "https://raw.githubusercontent.com/immersive-web/webxr-input-profiles/main/packages/assets/profiles/generic-hand/right.glb",
        "license": "MIT",
        "notice": (HERE / "LICENSE.md").read_text(),
    }
    for name in rig["pose_names"]:
        activate(rig,name)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
        # Fixed fan avoids Blender changing quad diagonals between poses.
        indices = [i for p in mesh.polygons for j in range(1,len(p.vertices)-1) for i in (p.vertices[0],p.vertices[j+1],p.vertices[j])]
        if not result["indices"]:
            result["indices"] = indices
            attrs = [mesh.attributes["highlight_" + d] for d in ("thumb","index","middle","ring","pinky")]
            for i in range(len(mesh.vertices)):
                values = [a.data[i].value for a in attrs]; best = max(range(5),key=values.__getitem__)
                result["digitIndices"].append(best+1 if values[best] > .001 else 0)
                strength = min(1, max(0, (values[best] - .35) / .60))
                result["highlightWeights"].append(round(strength * strength * (3 - 2 * strength),6))
        else: assert indices == result["indices"], f"Topology changed in {name}"
        positions=[]; normals=[]
        for v in mesh.vertices:
            positions.extend(round(x,6) for x in TRANSFORM @ v.co)
            normals.extend(round(x,6) for x in (NORMAL @ v.normal).normalized())
        result["poses"][name] = {"positions":positions,"normals":normals}
        evaluated.to_mesh_clear()
    activate(rig,previous)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,separators=(",",":"))+"\n")
    print(f"Exported {len(result['digitIndices'])} vertices, {len(result['indices'])//3} triangles, {len(result['poses'])} poses; {OUTPUT.stat().st_size:,} bytes")
if __name__ == "__main__": export()
