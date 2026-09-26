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
- **Camera:** RealityKit has no orthographic projection. Board packages declare
  `display.camera.type = "orthographic"` and `BoardModelScene.framing` hard-guards
  on it. The orthographic look is treated as negotiable. Phase 1 renders a
  native perspective camera; screenshots compare it against a narrow-FOV
  telephoto approximation so the perceptual change is visible.
- **Phase boundary:** this phase adds the RealityKit path and switches the app to
  it. Existing SceneKit sources remain in-tree but unreferenced; they and their
  tests are removed in a follow-up once the look is approved. This keeps the
  phase-1 diff from deleting 3,690 lines of SCN-typed tests before validation.

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
holds a `BoardModelScene` today. Phase 1 introduces a RealityKit scene type and
routes the seam through it. `BoardPresentation.aspectRatio(for:)`
(`BoardMapView.swift:120`) keeps using the pure static `BoardModelScene.framing`
math, which is unchanged.

### Components

**`BoardModelRealityScene`** (new, `HangTen/Views/`)

- Owns an `Entity` root built from the verified package URL.
- Decodes by loading the USDZ into an entity and binding descriptor `nodeID`s to
  entities by name (schema-v2 descriptors use bare importer IDs; path
  descriptors walk the hierarchy). Node role (`body`/`contact`/`attachment`) and
  contact-slot IDs come from the descriptor exactly as they do today.
- Builds one entity per `BoardModelInstance`, applies `baseTransform`, and
  applies per-position transforms for the selected `positionID` using the
  existing `reusableMatrix` math.
- Mirrors an instance whose `baseTransform.reflection == .x`. The implementation
  is chosen by a spike: either a negative-scale container, or a ModelIO-based
  re-decode (`MDLAsset` -> `MeshResource.generate(from:)`) with negated x
  positions/normals and reversed winding. Because packages are guaranteed
  unbound, ModelIO re-decode does not need to import materials.
- Assigns one neutral `PhysicallyBasedMaterial` (warm off-white diffuse,
  roughness ~0.5, metalness 0) to board geometry; RealityKit supplies default
  image-based lighting.
- Exposes contact lookup (entity -> contactID) and the per-position transforms
  needed by the view.
- Idempotent: appearances are assigned once per decode, not per SwiftUI update.

**`BoardModelRealityLoader`** (new)

- Mirrors `BoardModelLoader` (`BoardModelView.swift:371`): same resource lease,
  load gate, cache key, and SHA-256 verification, but returns a
  `BoardModelRealityScene`. Reuses `BoardModelAsset` verification and
  `BoardModelCache`.

**`BoardModelRealityView`** (new, SwiftUI)

- A `RealityView` that adds the scene root and hosts a `PerspectiveCamera`
  entity.
- Framing computes a fit distance from the existing `BoardModelScene.framing`
  projected width/height and `fitPadding`, solving for the camera distance that
  fits the board in the viewport at the chosen field of view.
- Picking uses `SpatialTapGesture().targetedToAnyEntity()`; contact entities get
  `CollisionComponent` shapes, body/attachment entities do not, preserving
  today's "only contacts are pickable" behavior. The hit entity maps back to a
  contact ID and fires `onContactTap`.
- Highlights reassign the contact entity's `PhysicallyBasedMaterial` (value
  type) to the highlight tint and restore the neutral base material on clear.
- Closed state (no tap handler) renders without picking, matching the current
  display-only card behavior.

**Camera variants**

- Native perspective: `PerspectiveCamera` with a normal field of view.
- Telephoto: a narrow field of view (single-digit degrees) with a proportionally
  larger fit distance, approximating the prior orthographic presentation.
- A DEBUG-only switch selects the variant so both can be screenshotted without a
  rebuild. The switch does not exist in release.

### Data flow

`BoardModelSurface.task` -> `BoardModelRealityLoader.load` -> SHA-256 verify +
resource lease -> RealityKit decode -> `BoardModelRealityScene` -> `RealityView`
renders, `select` applies the position transform, `highlight` tints contacts,
`SpatialTapGesture` reports a tapped contact.

### Error handling

- Verification, lease, gate, or decode failure -> existing `.unavailable` state.
- A node in the descriptor that cannot be bound -> the scene fails to construct,
  matching the current `prepareModel` all-or-nothing contract.
- Mirroring or model-buffer failures during the spike fall back to the other
  mirroring implementation; a board that cannot be mirrored fails to construct
  rather than rendering a wrong half.

## Testing and verification

- Unit tests on `BoardModelRealityScene` (device/simulator required):
  descriptor node binding, instance construction, reflection presence, position
  transform application, contact ID lookup, and highlight material swap/restore.
- The existing SceneKit `BoardModelScene` tests continue to pass unchanged,
  because the SceneKit sources are left in place this phase.
- Build the app for an isolated iOS Simulator and screenshot the board detail
  screen for at least `trango-rock-prodigy-pivot` in both camera variants, using
  the `validate-hang-ten-ios` skill.
- Report the screenshots against the current SceneKit render so the perceptual
  change (perspective and telephoto) is visible.

## Deferrals

- Deletion of the SceneKit renderer and rewrite/removal of its SCN-typed tests.
- Suspension-cord rendering and mesh-triangle clearance parity.
- Accessibility-projection parity for contacts (`presentation`-tree stall
  handling does not exist in RealityKit); if needed, contacts can be exposed via
  the descriptor `center`/`facePlaneAABB` rather than mesh projection.
