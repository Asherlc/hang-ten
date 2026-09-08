---
name: migrate-hangboard-to-3d
description: Use when migrating an existing Hang Ten hangboard to an interactive 3D display model, or refining its geometry, exported materials, picking, or app integration.
---

# Migrate a hangboard to 3D

Deliver a faithful, 3D-only display model with selectable physical contacts. Migration replaces the target board's raster presentation and canonical 2D hold geometry; the 3D model and its package metadata become the sole source of truth for rendering, highlighting, and hit-testing. Preserve logical hold IDs, saved identities, and source-backed metadata. This is not manufacturing CAD or a source for training prescriptions.

## Establish the contract once

Identify the exact board revision and read its existing package and source audit. Reuse verified manufacturer references; research only missing evidence. Record sourced dimensions separately from estimated positions, thickness, radii, and sections. Derive physical contact IDs from the package: Compact II's 19 contacts are an example, not a universal count. Remove the migrated target's raster asset and canonical 2D hold paths from product resources; retain its stable IDs and source-backed metadata in the 3D-only package representation. When an already-migrated board that still carries legacy raster assets or paths is included in scope, bring it to this same contract. Omit all screw holes, mounting holes, and mounting hardware from every hangboard display model. Document each omission as a deliberate display simplification; never imply that the physical product lacks those features.

Read relevant sections of the [working example](../../../Tools/HangboardModels/README.md), then inspect only the generator functions needed. Treat any dual 2D/3D structure in an older example as legacy, not as a requirement to preserve raster assets or paths. Follow `add-hangboard` for source-backed package metadata, while applying this skill's 3D-only migration contract.

## Separate logical data from model geometry

Keep physical identity, source-backed logical holds, equipment, and positions in `board.json`. Use explicitly tagged raster/model presentations so unrelated raster boards can coexist with migrated boards. Each migrated package owns a required USDZ and an explicit mesh-to-logical-hold-ID binding; multiple disconnected mesh pieces may share one ID. The mesh is the sole geometry for rendering, highlighting, and picking: do not retain parallel raster paths or hand-edited spatial bounds.

Derive spatial centers and bounds used by workout matching from the mesh in a defined board coordinate frame. A build-generated index bound to the model hash may provide these values without eagerly decoding every USDZ during catalog loading. Keep camera configuration separate from physical metadata, and never silently promote estimated model geometry to physical dimensions.

Carry model media through package validation, staging, and sync. Workbench must explicitly disable model geometry editing it does not support; do not reconstruct raster geometry to enable it. A missing or malformed USDZ is a package validation/build defect, with an explicit unavailable state if encountered at runtime.

## Build shape before finish

Directly author analytic silhouettes, sections, and recesses from visually reviewed evidence; do not trace or segment pixels. Author symmetric geometry once where the product is symmetric. Give every physical contact its canonical identity, preserving disconnected pieces when necessary.

Model real mouth/back fillets, jug rolls, and continuous curves. A global bevel and smooth normals cannot repair blocky geometry. Inspect inexpensive front and oblique clay views, including a close pocket section, before expensive texture baking and galleries. Then use an original material appropriate to the product and enough tessellation to preserve reviewed curvature at mobile viewing sizes. Match material fidelity effort to the user's brief; generic original wood is acceptable when a species match is not required.

When independent comparisons are requested, give candidates identical evidence and briefs, isolate their code and artifacts, and do not share candidate work between them. Compare matched cameras and lights, inspect front, oblique, clay, and detail views before selecting, and record render-engine differences that affect comparison. Complete the requested draft comparison before production integration; the number and identity of candidates belong to the user's request, not this workflow.

## Prove the actual export

Reuse the [export verifier](../../../Tools/HangboardModels/verify_wood_grips_compact_ii.py), adapting board-specific expectations. Reimport actual exports in isolation with source materials/images removed; check dimensions, inventory, textures, triangle count, and visual continuity. Package validation or the build must require the model asset and reject missing, malformed, materialless, or wrong-inventory exports as defects.

Explicitly triangulate Boolean cap n-gons for USDZ export without changing editable geometry. Blender roundtrips alone missed SceneKit's untextured body and faces occluding pockets. Inspect the bundled asset natively: body and every contact need materials; nearest triangle hits must resolve to the expected IDs. Handle normalized USD names and parent nodes. Orthographic tests use parallel rays; CPU-only SceneKit tests need `SCNTransaction.flush()` before picking.

## Integrate through the existing bridge

Inspect [BoardModelView](../../../HangTen/Views/BoardModelView.swift), package loading, and [regressions](../../../HangTenTests/BoardModelTests.swift). Extend identity, resource, and cache routing deliberately rather than copying a renderer or assuming a registry exists. Gate models to the exact supported revision and presentation. Do not retain or recreate a raster fallback for edited, inverted, unsupported, missing, or invalid states. Validation should make asset failure unreachable in a shipped package; if it escapes at runtime, fail closed to an explicit unavailable/error state.

Keep asynchronous cached loading, independent cloned materials, scene/camera rebinding on identity changes, stable accessibility elements, and on-demand rendering. Use head-on orthographic app framing with lighting that reveals recess depth. Match preview/rest and active highlight semantics; restore wood when cleared.

## Verify, retain, stop

Copy the reviewed asset into app resources and compare SHA-256 hashes. Verify the migrated package no longer ships or references the target's raster presentation or canonical 2D hold paths. On the first migration, use `validate-hang-ten-ios` to inspect normal/highlighted portrait and landscape views, physically tap every hold, and check preview, active, clearing, reappearance, and the explicit unavailable/error state. Tests complement visual review.

Keep source/export hashes, evidence mappings, screenshots, and results under workspace-owned output; clean owned resources. Completion means reviewed fidelity, complete selectable inventory, valid native materials/picking, matching bundle hash, and passing relevant checks.

Batch independent reads with bounded output. Reuse evidence and scripts; delegate repository-required implementation tasks with file paths and a narrow contract instead of full histories. After a pass, rerun only checks invalidated by changes or failures. Use verifier format selection/skip-render options for unaffected visuals; regenerate galleries when partitions change or requested. Avoid repeated broad research, full suites, and all-hold renders for small lighting or camera edits.
