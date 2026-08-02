# Hang Ten App Icon Design

## Context

Hang Ten currently has no `AppIcon.appiconset`. The app's visual language is
warm cream, honey wood, deep evergreen, and a red-orange active-hold accent.
The project already contains a faithful Compact II board illustration and a
deterministic board-rendering language, so the icon should identify the app as
a hangboard training tool rather than introduce a separate visual system.

## Goal

Add a recognizable iOS app icon that reads clearly at small sizes and connects
the Hang Ten brand to the physical action of training on a hangboard.

## Approved visual design

- Use a deep evergreen rounded-square field. The rounded corners are part of
  the preview composition; iOS applies the final platform mask.
- Center a simplified, faithful Compact II hangboard silhouette. It should
  retain the board's broad rounded ends, stepped rails, and orderly two-row
  recessed-hold layout so it does not read as a generic plank.
- Place a small warm-cream climbing hand at the lower-center hold. The hand is
  localized to that hold: four simplified fingers enter the pocket and a
  compact palm sits below the board. It must not span across or cover the
  board face, and it must not include a forearm or wristband.
- Highlight exactly one lower-center pocket in red-orange. No other orange
  accent or object is allowed; the active color belongs to the hold itself.
- Use flat-to-subtle dimensional shading with crisp, vector-inspired edges.
  Avoid photorealistic anatomy, busy wood grain, typography, labels, scenery,
  gear, watermarks, and arbitrary board geometry.
- Keep the hand and selected hold large enough to remain legible as an icon,
  while preserving enough surrounding board geometry to communicate the
  hangboard.

## Asset and integration

- Create `HangTen/Resources/Assets.xcassets/AppIcon.appiconset/` with a
  canonical 1024x1024 PNG named `AppIcon-1024.png`.
- Add a standard Xcode asset `Contents.json` that points the universal 1024px
  image at the App Store icon slot.
- Set the app target's asset catalog app-icon name to `AppIcon` in both Debug
  and Release build settings if Xcode does not infer it from the asset
  catalog.
- Do not alter the existing board imagery, runtime UI, color definitions, or
  bundle identifier.

## Validation

- Inspect the final 1024px image and confirm the board silhouette, single
  highlighted pocket, localized hand, absence of the orange wrist bar, and
  high contrast against the evergreen field.
- Build the `HangTen` scheme for an iOS Simulator with `xcodebuild`.
- Confirm the built app resolves the `AppIcon` asset without asset-catalog or
  missing-resource warnings.
- Check the icon at a small thumbnail scale to ensure the hand and active hold
  remain distinguishable.

## Out of scope

- Redesigning the in-app brand palette or UI.
- Adding alternate app icons, marketing screenshots, launch-screen artwork, or
  an app icon animation.
- Reworking the board model or its existing illustration.
