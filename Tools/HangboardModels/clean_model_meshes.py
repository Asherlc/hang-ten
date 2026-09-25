#!/usr/bin/env python3
"""Clean up contact meshes in imported USDZ for hangboard models."""

import bpy
import sys
import os

def clean_contact_meshes(board_id: str, usdz_path: str, output_usdz: str, output_blend: str, board_json: str):
    """Import USDZ, clean contact meshes, re-export."""
    
    # Load board.json to get logical contact IDs and their real `kind`
    # (jug/sloper/pocket/edge/...). The kind drives how each hold is smoothed
    # below; it must come from board.json, not guessed from the id string,
    # since some ids (e.g. "pocket-top-left") don't match their real kind
    # ("edge").
    import json
    with open(board_json, 'r') as f:
        board = json.load(f)
    logical_contact_ids = {c['id'] for c in board['contacts']}
    contact_kinds = {c['id']: c.get('kind') for c in board['contacts']}
    print(f"Logical contact IDs: {logical_contact_ids}")
    
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Import USDZ
    result = bpy.ops.wm.usd_import(filepath=usdz_path, merge_parent_xform=True)
    if 'FINISHED' not in result:
        raise RuntimeError(f"USDZ import failed: {result}")
    
    # Process each object
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':
            # Remove non-mesh objects (like _materials empty from USD import)
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
            
        role = obj.get('role')
        # Support both hold_id (older models) and contact_id (newer models)
        hold_id = obj.get('hold_id') or obj.get('contact_id')
        source_node_id = obj.get('hang_ten_source_node_id')
        
        print(f"Processing: {obj.name} (role={role}, hold_id={hold_id})")
        
        if role == 'body':
            # Keep body as-is, just ensure clean normals
            for poly in obj.data.polygons:
                poly.use_smooth = True
            continue
            
        if role in ('hold', 'contact') and hold_id in logical_contact_ids:
            # Clean up contact mesh
            clean_hold_mesh(obj, hold_id, contact_kinds.get(hold_id))
            # Compiler expects 'role: contact' and 'contact_id'
            obj['role'] = 'contact'
            obj['contact_id'] = hold_id
            # Remove hold_id if it existed (cleanup)
            if 'hold_id' in obj:
                del obj['hold_id']
            continue
            
        if role in ('hold', 'contact') and hold_id not in logical_contact_ids:
            print(f"  WARNING: hold_id '{hold_id}' not in logical contacts, keeping as-is")
            continue
            
        print(f"  UNKNOWN role/hold_id, keeping as-is")
    
    # Save .blend file for compiler
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"Saved cleaned .blend to {output_blend}")
    
    # Export USDZ
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
    
    selected = bpy.context.selected_objects
    if not selected:
        raise RuntimeError(f"No mesh objects selected for export: {usdz_path}")
    bpy.context.view_layer.objects.active = selected[0]
    
    result = bpy.ops.wm.usd_export(
        filepath=output_usdz,
        selected_objects_only=True,
        # Committed models ship unbound (AGENTS.md model material policy).
        export_materials=False,
        export_custom_properties=True,
        convert_orientation=True,
        export_global_forward_selection='NEGATIVE_Z',
        export_global_up_selection='Y',
    )
    
    if 'FINISHED' not in result:
        raise RuntimeError(f"USDZ export failed: {result}")
    
    print(f"Exported cleaned USDZ to {output_usdz}")


def clean_hold_mesh(obj: bpy.types.Object, hold_id: str, kind: str | None):
    """Apply cleanup operations to a contact mesh."""
    bpy.context.view_layer.objects.active = obj

    # Force this object's mesh to be single-user before mutating it: several
    # of these contact objects were authored as mirrored duplicates sharing
    # one mesh datablock, and modifier_apply silently swaps obj.data to a new
    # single-user copy the first time that happens, which would otherwise
    # leave any cached "mesh" reference (and derived triangle counts) stale.
    obj.data = obj.data.copy()

    is_edge_hold = kind == 'edge'
    is_pocket_hold = kind == 'pocket'

    # 1. Remove duplicate vertices, welding any near-touching loose islands
    #    together so the hold reads as one contiguous shape.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0004)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 2. Limited dissolve - merge coplanar faces (for flat holds like edges)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_limited(angle_limit=0.0872665)  # 5 degrees
    bpy.ops.object.mode_set(mode='OBJECT')

    if is_edge_hold:
        # 3a. Flat holds (edges) should stay flat and angular; just soften
        # the hard silhouette corners with a small bevel instead of a
        # full round-over.
        dims = [d for d in obj.dimensions if d > 0.0001]
        min_dim = min(dims) if dims else 0.01
        bevel_mod = obj.modifiers.new(name="EdgeSoften", type='BEVEL')
        bevel_mod.width = max(0.0006, min_dim * 0.035)
        bevel_mod.segments = 2
        bevel_mod.limit_method = 'ANGLE'
        bevel_mod.angle_limit = 0.5236  # 30 degrees
        bpy.ops.object.modifier_apply(modifier=bevel_mod.name)
    elif is_pocket_hold:
        # 3b. Pockets are concave cavities, often modeled as a fan of faces
        # converging on a single point at the bottom. A Subdivision Surface
        # pinches that point into a sharp cone, so pockets only get a light,
        # topology-preserving Corrective Smooth to soften facets without
        # collapsing their shape.
        smooth_mod = obj.modifiers.new(name="RoundSmooth", type='CORRECTIVE_SMOOTH')
        smooth_mod.factor = 0.3
        smooth_mod.iterations = 2
        smooth_mod.smooth_type = 'LENGTH_WEIGHTED'
        bpy.ops.object.modifier_apply(modifier=smooth_mod.name)
    else:
        # 3c. Round other organic holds (jugs, slopers, pinches) with a
        # Subdivision Surface pass: unlike a voxel remesh, subsurf
        # interpolates the existing UV map instead of discarding it, so
        # these flush surface-patch holds keep sampling the correct spot on
        # the body's wood texture instead of picking up garbage texels from
        # a blank UV.
        subsurf_mod = obj.modifiers.new(name="RoundSubsurf", type='SUBSURF')
        subsurf_mod.subdivision_type = 'CATMULL_CLARK'
        subsurf_mod.levels = 2
        subsurf_mod.render_levels = 2
        bpy.ops.object.modifier_apply(modifier=subsurf_mod.name)

        # Light corrective smoothing to round the remaining facets further
        # without shrinking the overall hold volume.
        smooth_mod = obj.modifiers.new(name="RoundSmooth", type='CORRECTIVE_SMOOTH')
        smooth_mod.factor = 0.5
        smooth_mod.iterations = 3
        smooth_mod.smooth_type = 'LENGTH_WEIGHTED'
        bpy.ops.object.modifier_apply(modifier=smooth_mod.name)
        print(f"  Rounded {hold_id} -> {len(obj.data.polygons)} polys (pre-triangulate)")

    # 4. Triangulate unconditionally before counting: bevel/subsurf add
    # quad-dominant geometry, and some source meshes (e.g. the Metolius
    # simulator) are quad/ngon based to begin with, so `polygons` can't be
    # trusted as a triangle count until this runs. Skipping this step is what
    # caused triangle counts to double (or even grow) after decimation
    # earlier, since use_collapse_triangulate triangulates surviving quads
    # *after* the ratio is computed against a quad count.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')

    # 5. Decimate for high-poly meshes - reduce triangle count after rounding
    tri_count = len(obj.data.polygons)
    target_cap = 500 if is_edge_hold else 900
    if tri_count > target_cap:
        decimate_ratio = min(1.0, target_cap / tri_count)
        mod = obj.modifiers.new(name="DecimateCleanup", type='DECIMATE')
        mod.ratio = decimate_ratio
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"  Decimated {hold_id}: {tri_count} -> {len(obj.data.polygons)} triangles")

    # 5. Ensure smooth shading for organic shapes (jugs, slopers, pockets)
    # Flat holds (edges) should stay flat
    use_smooth = not is_edge_hold
    for poly in obj.data.polygons:
        poly.use_smooth = use_smooth

    # 6. Recalculate normals
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"  Cleaned {hold_id} ({kind}): {len(obj.data.polygons)} triangles, {'smooth' if not is_edge_hold else 'flat'}")


def main():
    # Parse args after '--'
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = argv[1:]

    if len(argv) < 5:
        print("Usage: blender --background --python clean_model_meshes.py -- <board_id> <usdz_path> <output_usdz> <output_blend> <board_json>")
        sys.exit(1)

    board_id, usdz_path, output_usdz, output_blend, board_json = argv[:5]
    
    print(f"Cleaning {board_id}")
    print(f"  Input:  {usdz_path}")
    print(f"  Output USDZ: {output_usdz}")
    print(f"  Output .blend: {output_blend}")
    print(f"  Board:  {board_json}")
    
    clean_contact_meshes(board_id, usdz_path, output_usdz, output_blend, board_json)


if __name__ == "__main__":
    main()