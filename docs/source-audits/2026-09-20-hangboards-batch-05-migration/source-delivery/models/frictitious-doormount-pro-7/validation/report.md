# Current export validation

`frictitious-doormount-pro-7.glb`

SHA256 `8b639807ff660566dca2fd313f00abfadaae0bfbaf0c28ecbc82477f2732113f`

Structural pass: **True**

- PASS: clean_trimesh_and_VTK_import
- PASS: unique_nodes
- PASS: exact_hold_mapping
- PASS: hold_extras
- PASS: body_extras
- PASS: only_production_nodes
- PASS: root_coordinate_conversion
- PASS: applied_mesh_transforms
- PASS: self_contained
- PASS: no_environment
- PASS: material_on_every_primitive
- PASS: assembled_watertight
- PASS: consistent_winding
- PASS: positive_volume
- PASS: finite_nondegenerate
- PASS: no_duplicate_triangles
- PASS: one_connected_patch_per_contact
- PASS: physical_unit_count
- PASS: metric_bounds
- PASS: normalized_finite_normals
- PASS: shared_contact_boundary_normals
- PASS: indexed_vertex_efficiency
- PASS: meaningful_size_reduction
- PASS: UV0_finite_unit_square
- PASS: UV_local_stretch
- PASS: locked_contact_boundaries
- PASS: sampled_surface_deviation

Visual review: Reviewed all five current views. Curved-transition protection removes the large triangular shading patches without flattening the lip geometry. All 13 contact regions remain; nested cavities and mounting opening are genuine geometry. Rear details remain simplified as documented.

Evidence and target-device limitations are listed in README; structural success does not certify physical-product fidelity.
