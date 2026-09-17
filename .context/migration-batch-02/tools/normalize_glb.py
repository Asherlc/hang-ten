"""Import a delivered GLB, bake the coordinate-wrapper empties into the meshes,
give every material a solid-color image texture derived from its Principled base
color (the compiler requires image-backed materials), and re-export a
compiler-ready GLB."""
import bpy, sys


def to_srgb(value: float) -> float:
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def main(src: str, dst: str) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    if any(o.type != "MESH" for o in bpy.context.scene.objects):
        raise SystemExit("non-mesh objects remain")

    for material in bpy.data.materials:
        tree = getattr(material, "node_tree", None)
        if tree is None:
            continue
        bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        if bsdf.inputs["Base Color"].is_linked:
            continue
        color = list(bsdf.inputs["Base Color"].default_value)
        image = bpy.data.images.new(
            f"neutral-{material.name}", width=1, height=1, alpha=True
        )
        image.colorspace_settings.name = "sRGB"
        image.pixels = [
            to_srgb(color[0]),
            to_srgb(color[1]),
            to_srgb(color[2]),
            1.0,
        ]
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image = image
        texture.location = (bsdf.location.x - 320, bsdf.location.y)
        tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])

    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", use_selection=False)


main(sys.argv[sys.argv.index("--") + 1], sys.argv[sys.argv.index("--") + 2])
