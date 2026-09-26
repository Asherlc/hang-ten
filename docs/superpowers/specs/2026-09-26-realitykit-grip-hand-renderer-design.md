# RealityKit grip-hand renderer

Date: 2026-09-26

## Goal

Remove the final SceneKit renderer from Hang Ten by migrating the interactive
3D grip-hand illustration in `GripHandModelView` to RealityKit. Preserve the
current evaluated Blender mesh, posture-specific surfaces, explicit finger
highlighting, left/right presentation, camera framing, drag orbit, pinch zoom,
reset behavior, and unavailable-asset fallback. The hand remains an
illustration; it does not supply anatomical measurements or training cues.

## Current behavior

`GripHandAsset` decodes and validates the bundled schema-v2
`HangTen/Resources/GripHand/hand-mesh.json`. It contains the evaluated vertex
positions and normals for each grip surface, shared triangle indices, per-vertex
digit membership, and authored highlight weights. `GripHandSurface` builds
SceneKit geometry and uses a geometry shader to interpolate between the warm
skin base and orange highlight. `GripHandModelView.Coordinator` mirrors the
hand by side, frames the currently posed vertices with an orthographic camera,
and applies bounded orbit and zoom. The same view is used in cue cards, the
inspector, and the DEBUG review screen.

## Design

Keep the JSON asset, its decoder and validation, `GripHandPose`, and the public
SwiftUI call sites. Replace the `UIViewRepresentable` / `SCNView` stack with a
SwiftUI `RealityView` backed by RealityKit entities and an
`OrthographicCameraComponent`. Construct a `MeshResource` from each authored
pose surface's positions, normals, and shared triangle indices; do not regenerate
or deform the Blender mesh. Apply side mirroring as an entity transform and
retain the existing world-space bounds framing and bounded turntable orbit.

Preserve the shader's highlight equation and exact finger semantics. For each
vertex, select its authored highlight weight only when its `digitIndices` entry
matches one of the explicitly selected fingers, clamp the result to 0...1, and
mix the existing linear-RGB base and highlight colors. Use RealityKit-supported
mesh/material data for the computed per-vertex color; implementation planning
must include an early rendering probe to confirm the chosen API preserves smooth
interpolation and the colors on the bundled mesh. The pose geometry cache stays
bounded, and its key must include both the pose and selected-finger set if the
colored output is cached. Do not infer finger membership from grip type or
finger count.

Move pan and pinch handling to SwiftUI gestures attached to the RealityView.
Translate drag deltas and magnification changes through the same orbit limits,
turntable axes, and zoom bounds used today. Recompute canonical framing when
the view size, pose, or side changes; reset the camera when the existing
`resetToken` changes. Keep the current placeholder text when the asset cannot
be loaded or validated. Preserve accessibility labels and keep the 3D entity
out of the accessibility element tree, as the current UIKit view does.

## Scope and constraints

- Modify `HangTen/Views/GripHandModelView.swift` and
  `HangTenTests/GripHandOrbitTests.swift`; update project references only if
  RealityKit requires a new compiled resource.
- Keep the `hand-mesh.json` schema and Blender authoring/export pipeline
  unchanged.
- Preserve all existing `GripHandCueCardTests` and their source-fidelity
  guarantees.
- Remove SceneKit imports and APIs from the grip-hand renderer and its tests;
  after migration, application and test targets must have no SceneKit dependency.
- Do not add a SceneKit fallback, new package dependency, anatomical claims, or
  changes to workout prescription data.

## Verification

- Add failing RealityKit tests before implementation for pose mesh creation,
  exact finger-to-highlight mapping (including empty and multi-finger sets),
  mirrored sides, camera orbit/zoom limits, and reset behavior.
- Run `GripHandOrbitTests`, `GripHandCueCardTests`, and the full iOS test target.
- Build and visually review the existing cue-card/inspector flows on an isolated
iOS Simulator. Compare neutral, single-finger, and multi-finger highlights on
both left and right hands, and exercise drag, pinch, resize, and reset.
- Search application sources and tests for SceneKit symbols; the search must
  return no matches.

## Apple API references

- [RealityView](https://developer.apple.com/documentation/realitykit/realityview)
- [MeshDescriptor](https://developer.apple.com/documentation/realitykit/meshdescriptor)
- [OrthographicCameraComponent](https://developer.apple.com/documentation/realitykit/orthographiccameracomponent)
- [Transforming RealityKit entities using gestures](https://developer.apple.com/documentation/realitykit/transforming-realitykit-entities-using-gestures)
