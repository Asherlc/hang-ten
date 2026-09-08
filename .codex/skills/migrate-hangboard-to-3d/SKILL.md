---
name: migrate-hangboard-to-3d
description: Use when migrating an existing Hang Ten hangboard to an interactive 3D display model, or refining its geometry, exported materials, picking, or app integration.
---

# Migrate a hangboard to 3D

Deliver a faithful display model with selectable physical contacts. Preserve canonical board JSON, PNG, editor paths, saved identities, and 2D fallback. This is not manufacturing CAD or a source for training prescriptions.

## Establish the contract once

Identify the exact board revision and read its existing package and source audit. Reuse verified manufacturer references; research only missing evidence. Record sourced dimensions separately from estimated positions, thickness, radii, and sections. Derive physical contact IDs from the package: Compact II's 19 contacts are an example, not a universal count. Omit all screw holes, mounting holes, and mounting hardware from every hangboard display model. Document each omission as a deliberate display simplification; never imply that the physical product lacks those features.

Read relevant sections of the [working example](../../../Tools/HangboardModels/README.md), then inspect only the generator functions needed. Follow `add-hangboard` if canonical package content must change.

## Build shape before finish

Directly author analytic silhouettes, sections, and recesses from visually reviewed evidence; do not trace or segment pixels. Author symmetric geometry once where the product is symmetric. Give every physical contact its canonical identity, preserving disconnected pieces when necessary.

Model real mouth/back fillets, jug rolls, and continuous curves. A global bevel and smooth normals cannot repair blocky geometry. Inspect inexpensive front and oblique clay views, including a close pocket section, before expensive texture baking and galleries. Then use an original material appropriate to the product and enough tessellation to preserve reviewed curvature at mobile viewing sizes.

## Prove the actual export

Reuse the [export verifier](../../../Tools/HangboardModels/verify_wood_grips_compact_ii.py), adapting board-specific expectations. Reimport actual exports in isolation with source materials/images removed; check dimensions, inventory, textures, triangle count, and visual continuity.

Explicitly triangulate Boolean cap n-gons for USDZ export without changing editable geometry. Blender roundtrips alone missed SceneKit's untextured body and faces occluding pockets. Inspect the bundled asset natively: body and every contact need materials; nearest triangle hits must resolve to the expected IDs. Handle normalized USD names and parent nodes. Orthographic tests use parallel rays; CPU-only SceneKit tests need `SCNTransaction.flush()` before picking.

## Integrate through the existing bridge

Inspect [BoardModelView](../../../HangTen/Views/BoardModelView.swift) and [regressions](../../../HangTenTests/BoardModelTests.swift). The bridge currently supports one board; extend identity, resource, and cache routing deliberately rather than copying a renderer or assuming a registry exists. Gate models to the exact supported revision/presentation; edited, inverted, unsupported, missing, or invalid assets retain 2D fallback.

Keep asynchronous cached loading, independent cloned materials, scene/camera rebinding on identity changes, stable accessibility elements, and on-demand rendering. Use head-on orthographic app framing with lighting that reveals recess depth. Match preview/rest and active highlight semantics; restore wood when cleared.

## Verify, retain, stop

Copy the reviewed asset into app resources and compare SHA-256 hashes. On the first migration, use `validate-hang-ten-ios` to inspect normal/highlighted portrait and landscape views, physically tap every hold, and check preview, active, clearing, reappearance, and fallback. Tests complement visual review.

Keep source/export hashes, evidence mappings, screenshots, and results under workspace-owned output; clean owned resources. Completion means reviewed fidelity, complete selectable inventory, valid native materials/picking, matching bundle hash, and passing relevant checks.

Batch independent reads with bounded output. Reuse evidence and scripts; delegate repository-required implementation tasks with file paths and a narrow contract instead of full histories. After a pass, rerun only checks invalidated by changes or failures. Use verifier format selection/skip-render options for unaffected visuals; regenerate galleries when partitions change or requested. Avoid repeated broad research, full suites, and all-hold renders for small lighting or camera edits.
