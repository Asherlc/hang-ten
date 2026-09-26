# RealityKit board model renderer

Date: 2026-09-25

## Problem

Bundled hangboard USDZ packages ship with unbound meshes and no materials or
textures, by policy. The SceneKit presentation path
(`HangTen/Views/BoardModelView.swift`) lights the imported default material with
an ambient light plus one directional light and no lighting environment, which
produces a flat, textureless render that reads as "funky" rather than as a
physical board.

A prior proposal
(`docs/superpowers/specs/2026-09-25-ios-board-model-studio-appearance-design.md`)
kept SceneKit and added a runtime studio appearance pass. This spec supersedes
that proposal: instead of patching SceneKit's flat default, migrate the board
presentation to RealityKit, whose default appearance is physically based with
image-based lighting and therefore renders an unbound mesh with believable form
out of the box.

## Goal

Render every model-media hangboard with RealityKit in the iOS app, preserving
board positions, contact picking, highlight tinting, and camera framing, and
validate the result with real iOS Simulator screenshots in both a native
perspective camera and a narrow-FOV telephoto variant.

## Decisions

- **Framework:** RealityKit replaces SceneKit for board model presentation.
  SceneKit is no longer the render path.
- **Deployment:** raise `IPHONEOS_DEPLOYMENT_TARGET` to 18.0. The RealityKit
  camera components (`PerspectiveCamera`, `RealityViewCameraControls`) require
  iOS 18, and the iOS 17 fallback is removed rather than maintained.
- **Model layer:** the SceneKit model layer (`BoardModelScene`: package decode,
  descriptor binding, instance transforms, mirrored geometry, positions,
  suspension, hit-test bindings) stays the source of truth. Only drawing moves
  to RealityKit. Reusing it avoids re-implementing the audited geometry,
  reflection, and picking contract, and keeps the existing `BoardModelScene`
  tests valid.
- **Camera:** RealityKit has no orthographic projection. Board packages declare
  `display.camera.type = "orthographic"` and `BoardModelScene.framing` hard-guards
  on it. The orthographic look is treated as negotiable. Phase 1 renders a
  native perspective camera; screenshots compare it against a narrow-FOV
  telephoto approximation so the perceptual change is visible.
- **Phase boundary:** this phase adds the RealityKit renderer and switches
  `BoardModelSurface` to it. The SceneKit renderer (`BoardModelView` /
  `BoardModelSCNView`) remains in-tree but is no longer referenced by the app;
  it and its tests are removed in a follow-up once the look is approved. This
  keeps the phase-1 diff from deleting 3,690 lines of SCN-typed tests before
  validation.

## Non-goals

- No edits to USDZ files, `board.json`, or package descriptors. The model
  material policy still holds: committed models remain unbound and the renderer
  supplies its own neutral material.
- No per-role colors, procedural texture shaders, or cel shading.
- No changes to hoverboard geometry authoring, suspension solver math, or
  contact requirement normalization.
- No suspension-cord rendering or mesh-triangle clearance in this phase (not
  used by the validation board; RealityKit does not expose mesh vertex buffers).
- No feature flag.

## Design

### Seam

`BoardModelSurface` (`HangTen/Views/BoardModelView.swift:426`) is the only
consumer-facing seam; `BoardMapView` renders it at the board detail map
(`BoardMapView.swift:383`) and the picker card (`:624`). Its `ResultState.ready`
still holds a `BoardModelScene`; the surface now renders it through
`BoardModelRealityView` instead of `BoardModelView`. The loader, cache, resource
lease, and SHA-256 verification are unchanged. `BoardPresentation.aspectRatio(for:)`
(`BoardMapView.swift:120`) keeps using the pure static `BoardModelScene.framing`
math, which is unchanged.

### Components

**`BoardRealityRenderer`** (new, `HangTen/Views/BoardModelView.swift`)

- `@MainActor` class that owns a RealityKit `Entity` root and a
  `PerspectiveCamera`, and mirrors `BoardModelScene.geometryNodes` into
  `ModelEntity`s.
- Bridges each prepared `SCNGeometry` into a `MeshResource`. USDZ geometry
  indexes positions and normals with independent interleaved index channels
  (`indicesChannelCount` 1–4), which `MeshDescriptor` cannot express, so the
  bridge expands every triangle into three unshared vertices with the authored
  per-vertex normals and an identity index list. Missing normals are synthesized
  per face.
- Assigns one neutral `PhysicallyBasedMaterial` (warm off-white diffuse,
  roughness 0.5, metalness 0) to board geometry; RealityKit supplies default
  image-based lighting, so no lighting rig or environment image is bundled.
- Copies `node.simdWorldTransform` onto each entity, so instance placement,
  mirroring (already baked into the cloned geometry by `BoardModelScene`), and
  position changes flow through without re-implementing them.
- Binds contact entities to contact IDs and gives only those entities collision
  shapes, preserving "only contacts are pickable".
- Maps a hit entity back to its contact ID for tap handling.
- Highlights reassign the contact entity's `PhysicallyBasedMaterial` (value
  type) to the highlight tint and restore the neutral base material on clear.

**`BoardModelRealityView`** (new, SwiftUI, `HangTen/Views/BoardModelView.swift`)

- A `RealityView` that installs the renderer's root and camera and hosts a
  `PerspectiveCamera` entity.
- Framing derives a perspective fit distance from the existing
  `BoardModelScene.fittedOrthographicScale(in:)` half-height and `fitPadding`
  (orthographic half-height / tan(fov/2)), so the board fills the viewport at
  the chosen field of view.
- Reuses `BoardModelScene.orbit` / `select` for orbit, pinch zoom, and position
  changes by driving the SceneKit camera and re-reading its transform.
- Picking uses `SpatialTapGesture().targetedToAnyEntity()`.
- Projects contact centers with the same camera math to expose
  `boardModel.contact.<id>` accessibility elements, matching the prior contract.
- Closed state (no tap handler) renders without picking, matching the existing
  display-only card behavior.

**Camera variants**

- Native perspective: `PerspectiveCamera` with a 30° vertical field of view.
- Telephoto: a 6° vertical field of view with a proportionally larger fit
  distance, approximating the prior orthographic presentation.
- A DEBUG-only environment switch (`HANGTEN_REVIEW_BOARD_TELEPHOTO=1`) selects
  the variant so both can be screenshotted without a rebuild. The switch does
  not exist in release.

### Data flow

`BoardModelSurface.task` -> `BoardModelLoader.load` (unchanged) -> SHA-256 verify
+ resource lease + SceneKit decode -> `BoardModelScene` -> `BoardModelRealityView`
mirrors it into RealityKit entities -> `RealityView` renders, `select` applies
the position transform, `highlight` tints contacts, `SpatialTapGesture`
reports a tapped contact.

### Error handling

- Verification, lease, gate, or decode failure -> existing `.unavailable` state.
- A geometry that cannot be bridged (unsupported primitive type or channel
  layout) is skipped rather than crashing; the rest of the board still renders.
- A position the scene cannot select -> `onUnavailable` fires, matching the
  SceneKit view's behavior.

## Testing and verification

- The existing `BoardModelScene` tests continue to pass unchanged, because the
  SceneKit model layer is left in place this phase (70 `BoardModelTests` pass on
  an iOS 26.5 simulator).
- Build the app for an isolated iOS Simulator and screenshot the board detail
  screen for `trango-rock-prodigy-pivot` in both camera variants, using the
  `validate-hang-ten-ios` skill.
- Report the screenshots against the pre-migration SceneKit render so the
  perceptual change is visible.

## Deferrals

- Deletion of the SceneKit renderer and rewrite/removal of its SCN-typed tests.
- Replacing the SceneKit model/decode layer with a RealityKit-native scene.
- Suspension-cord rendering and mesh-triangle clearance parity (the bridge has
  no cord entities; `BoardModelScene` still computes the solver).
- Full accessibility parity for the `presentation`-tree stall handling; the
  RealityKit view projects contact centers directly instead.
