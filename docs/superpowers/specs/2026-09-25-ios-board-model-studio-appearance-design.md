# iOS board model studio appearance (IBL + neutral matte)

Date: 2026-09-25

## Problem

Bundled hangboard USDZ packages ship with unbound meshes and no materials or
textures, by policy. `BoardModelScene.configureCameraAndLighting`
(`HangTen/Views/BoardModelView.swift:2504`) lights the imported default
material with an ambient light (250) plus one directional light (850) and no
lighting environment. The result is a flat, textureless render that reads as
"funky" in the app rather than as a physical board.

A diagnostic render confirmed that adding an image-based lighting environment
alone blows the default imported material out to near-white with no form: the
default material does not respond usefully to IBL. A neutral runtime material
is required in addition to the environment.

## Goal

Make every board model render in iOS with believable form and material
response, without changing any committed USDZ and without touching geometry,
picking, or suspension.

## Non-goals

- No edits to USDZ files, `board.json`, or package descriptors. The model
  material policy still holds: committed models remain unbound.
- No per-role colors, procedural texture shaders, cel shading, or RealityKit.
- No changes to board geometry, contact hit-testing, camera framing, or the
  suspension solver.
- No feature flag. This is a deliberate, universal visual change.

## Decision

Use a presentation-time appearance pass (Approach A):

- The model-decode layer keeps its current contract of preserving whatever
  materials it is given, so existing `BoardModelScene` decode tests stay valid.
- The studio look is applied once per model by the view layer, which is where
  "how to draw it" belongs.

Rejected alternatives: baking neutral materials into `prepareModel`
(entangles rendering with decode and breaks material-preservation tests), and
migrating to RealityKit (would require reimplementing the orbit, pick, and
selection logic in `BoardModelSCNView`).

## Design

### Components

**`StudioLightingEnvironment`** (new, `HangTen/Views/`)

- Produces a cached, deterministic equirectangular `UIImage` (1024x512) drawn
  with CoreGraphics: a vertical studio gradient (bright ceiling to dark floor)
  plus a warm key softbox in the upper third and a cool fill blob. No
  randomness, no bundled asset, no network.
- Exposes the image and nothing else. It cannot throw; if the CGContext cannot
  be created it returns `nil` and the caller skips the environment.

**`BoardModelScene.applyStudioAppearance()`**

- Idempotent: an internal flag makes repeat calls no-ops, so `updateUIView`
  cannot redo the work.
- Sets `scene.lightingEnvironment.contents` to the environment image and
  `scene.lightingEnvironment.intensity` to the tuned value.
- Mutates each material already present on `geometryNodes` in place:
  `lightingModel = .physicallyBased`, diffuse to a warm off-white
  `(0.82, 0.80, 0.77)`, `roughness = 0.5`, `metalness = 0`, and clears
  emission, normal, and specular map contents.
- In-place mutation is deliberate: the highlight system captures the material
  objects in `originalMaterials` at `HangTen/Views/BoardModelView.swift:719`
  and restores those same objects when a highlight clears. Keeping object
  identity means no rebinding is needed and highlight restore returns the new
  neutral material rather than the flat default.

**Cord materials**

- Set `lightingModel = .physicallyBased` on the cord material where it is
  created (`HangTen/Views/BoardModelView.swift:1766`), keeping the existing
  dark `0.08` diffuse and `0.8` roughness. This is independent of call
  ordering, since cords are built during `selectPositionIfNeeded`.

### Seam

`BoardModelSCNView.display(_:)` (`HangTen/Views/BoardModelView.swift:2779`)
already guards `self.model !== model`, so it runs once per model identity.
Call `model.applyStudioAppearance()` there after `scene = model.scene`. This
covers every caller (display-only picker cards and interactive board screens)
and stays out of `BoardModelScene.init`, leaving model-decode tests unchanged.

### Lighting values

- Keep the directional key light: it casts the shadow that grounds the board.
- Reduce ambient from 250 to approximately 150 so the environment carries the
  form shading instead of washing it out.
- Environment intensity approximately 1.5.
- Keep screen-space ambient occlusion unchanged.
- Background remains `view.backgroundColor = .clear`; only
  `lightingEnvironment` is set, so the SwiftUI card material behind the view
  still shows.

Exact values are tuned against side-by-side SceneKit renders before the change
is reported complete.

### Error handling

- If the environment image is unavailable, apply the PBR materials only. The
  board still renders with the existing ambient and key lights.
- Idempotency flag prevents repeated work and repeated material mutation.

## Testing and verification

New unit tests (TDD, written before implementation):

1. `applyStudioAppearance` sets `scene.lightingEnvironment.contents` and a
   positive intensity.
2. Board geometry materials become `.physicallyBased` with the expected
   diffuse, `roughness == 0.5`, and `metalness == 0`.
3. Calling it twice is idempotent (same material objects, no duplication).
4. Highlight a contact then clear it: the node's material returns to the same
   neutral material object captured before highlighting.
5. Cord materials are `.physicallyBased` and keep the dark diffuse.
6. `StudioLightingEnvironment` returns a 1024x512 image whose top is brighter
   than its bottom.

Existing `BoardModelScene` tests must pass unchanged, including those that
assert custom materials survive decode.

Visual verification:

- Re-render the SceneKit preview harness for before/after comparison.
- Capture real iOS Simulator screenshots for at least one model-media board
  using the `validate-hang-ten-ios` skill, on an isolated simulator, before
  reporting the change complete.
