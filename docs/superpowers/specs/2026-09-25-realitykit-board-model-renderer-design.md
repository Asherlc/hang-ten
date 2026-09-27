# RealityKit board model renderer

Date: 2026-09-25; Phase 2 updated 2026-09-26

## Goal

Render model-media hangboards with a native RealityKit scene. Preserve package
validation, descriptor contact binding, reusable instances, pose selection,
suspension solving, picking, highlights, camera framing, and accessibility
without using SceneKit as the board model or rendering layer.

## Architecture

`BoardModelRealityScene` (`HangTen/Models/BoardModelRealityTypes.swift`) owns
the imported RealityKit entity hierarchy, transformed instance entities,
contact-to-entity mapping, transient cord geometry, camera, highlights, and
selection state. `BoardModelRealityLoader` verifies the package SHA-256, holds
on-demand resource access, serializes memory-intensive loads, deduplicates
in-flight requests, and does not retain loaded sources after the requesting
scene releases them. SHA-256 file reads run off the main actor. USDZ files load
directly through RealityKit's `Entity(contentsOf:)`; no ModelIO validation,
SceneKit conversion, or intermediate geometry bridge is used.

Descriptor node IDs bind by exact imported entity name or exact slash-delimited
path beneath each instance root. Unmatched required nodes fail loading rather
than receiving a fuzzy or inherited contact binding. Reusable media creates
one transformed entity clone per declared instance, including base and
position transforms and X reflection. Only contact entities receive
collision shapes and input targets. `SpatialTapGesture` resolves a hit through
the entity's parent chain. Accessibility projects contact centers into the
active perspective view and exposes the existing `boardModel.contact.<id>`
elements.

`select(positionID:)` applies the authored instance or orientation transform,
solves single-cord, paired-lead, and two-branch suspension through the existing
pure `SuspendedBoardPresentation` solvers, and creates transient, non-pickable
RealityKit cylinder segments. Clearing a selection detaches those segments and
restores the base instance transforms. The solver remains authoritative for
cord paths and clearance; RealityKit meshes are display geometry only.

Board meshes use a neutral `PhysicallyBasedMaterial` (warm off-white, roughness
0.5, metalness 0). Highlight state replaces contact materials and restores the
neutral baseline when cleared. RealityKit's default image-based lighting is
used; model packages remain unbound and contain no added materials or textures.

Camera framing uses package view direction, up vector, bounds expansion,
distance multiplier, fit padding, field of view, and viewport aspect. Pure
framing and rotation helpers live with the RealityKit scene and are shared with
the board map. The live camera uses a 30-degree vertical perspective field of
view; DEBUG environment `HANGTEN_REVIEW_BOARD_TELEPHOTO=1` selects 6 degrees.
Drag and magnification gestures update the RealityKit camera directly.

`BoardModelSurface` (`HangTen/Views/BoardModelView.swift`) is the view seam for
the board detail map and picker. Its ready state contains
`BoardModelRealityScene`; `BoardModelRealityView` installs the scene root and
camera into SwiftUI `RealityView` and routes position, highlight, contact tap,
and accessibility updates.

## Framework boundary

The board model path contains no SceneKit types, loader, renderer, or tests.
SceneKit remains in `GripHandModelView` for the unrelated hand visualization;
that component is outside this migration. `SuspendedBoardPresentation` and
`SuspensionProfiles` remain framework-independent math and validation code.

## Non-goals

- No edits to USDZ files, `board.json`, or model descriptors.
- No per-role colors, procedural material textures, or cel shading.
- No automatic geometry authoring or mesh-triangle collision/clearance system.
  Suspension clearance continues to be validated by the existing solver.
- No feature flag or SceneKit fallback for board models.

## Errors

Package hash mismatch, unavailable resource, invalid USDZ, load cancellation,
and missing contact descriptors are typed RealityKit errors. The surface maps
load or selection failures to its existing unavailable state. Cancellation
removes waiting load-gate/cache requests and releases resource access through
the owning lease.

## Verification

- Build and run the native RealityKit model tests plus the package and pure
  suspension suites on an iOS Simulator.
- Verify descriptor contacts, materials, instance transforms, selection,
  highlights, suspension segment rendering, camera orbit/reset, load-gate
  handoff/cancellation, and invalid asset handling.
- Inspect simulator screenshots for the board detail view and compare board
  size, selected contact, and card layout with the previous renderer.
