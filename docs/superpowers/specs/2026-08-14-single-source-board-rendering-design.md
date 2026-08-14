# Single-Source Board Rendering Design

## Goal

Make each registered hangboard package's `assets/primary.png` the only runtime
visual definition of its board. The app must not load, validate, or render a
separate vector artwork document.

## Current problem

The Compact II package currently contains both `assets/primary.png` and
`artwork.json`. Although the PNG is package-owned and staged into the app,
every visible board screen uses `BoardMapView`, which draws the `BoardDesign`
decoded from `artwork.json`. The PNG therefore cannot determine what the user
sees, and the two visual representations can diverge.

## Approved design

`assets/primary.png` is the sole visual authority. `BoardMapView` loads the
package-declared PNG as its base image in all its existing call sites.

`Hangboards/` is the complete canonical, app-independent store for board
information. A registered package owns its identity, manufacturer facts, hold
IDs and normalized frames, semantic mappings, evidence, and canonical image.
The iOS app owns only board-agnostic decisions about rendering and interaction;
it contains no board-specific geometry, artwork, asset names, or rendering
branches.

`board.json` remains the source of hold identity, facts, and normalized
rectangular `frame` values. The generic `BoardMapView` uses those frames only
to place:

- transparent tap targets for selectable holds;
- simple highlight overlays for targeted holds.

Frames are interaction metadata, not a second depiction of the board. The
overlay must not recreate board silhouettes, wood grain, recesses, or hold
shapes. It may be a rounded rectangular tint/border inside the existing hold
frame so active and preview targets remain visible over the canonical PNG.

## Package and runtime changes

Remove `artwork.json` from every registered package, starting with Compact II.
It is board-specific rendering instruction data rather than canonical board
information required by the approved boundary. Remove its evidence entries and
all iOS/Python schema validation, decoding, store state, and tests whose sole
purpose is artwork delivery. The package contract becomes `board.json`,
`evidence.json`, `semantics.json`, and package-owned assets referenced by
`board.json`.

`BoardPackageStore` continues to validate and expose registered boards,
semantics, and the declared presentation PNG. It must not expose a board
design. `BoardMapView` must not contain a Canvas vector board renderer or a
generic vector fallback.

## Error handling

An approved package without a readable declared presentation image remains a
launch-blocking package error, as it is today. A board has no alternate visual
or asset-catalog fallback. Normalized hold frames remain validated so overlay
and tap placement cannot escape the displayed image.

## Verification

Automated tests must prove that:

1. registered packages have no `artwork.json` and do not require artwork
   evidence;
2. the app bundles and resolves the package-declared `assets/primary.png`;
3. `BoardPackageStore` exposes no vector design API;
4. source-boundary checks reject legacy artwork-delivery code and duplicate
   board visual assets;
5. `BoardMapView` retains correct frame-based interaction and highlight
   behavior without a vector renderer.

The focused iOS test suite and an iOS Simulator build must pass. A visual
simulator check must confirm the Compact II screen matches the package PNG and
still shows target highlighting.

## Scope

This change does not alter board facts, hold IDs, semantic mappings, training
plans, or the canonical `primary.png` bytes. It is limited to eliminating the
second visual source and preserving the existing interaction affordances.
