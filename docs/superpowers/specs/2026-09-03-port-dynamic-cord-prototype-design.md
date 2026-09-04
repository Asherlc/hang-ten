# Port-A-Board Dynamic Cord Vertical-Slice Design

## Status

This revision supersedes the original all-surfaces, all-tooling prototype
design. A disposable browser spike proved the important visual behavior and
the user approved it as good enough to implement:

- the board rotates in the image plane like a clock face;
- the support stays world-up while both strands remain taut;
- projected attachment points are paired by screen position so the strands do
  not cross after inversion;
- the cord is a dark, path-driven braid rather than baked raster pixels;
- a direction-aware foreground eyelet crescent makes each strand read as
  entering the hole continuously; and
- raising the pull point to exactly 1.5 times its former vertical distance
  gives the suspension enough height.

The first production slice is intentionally only the Port-A-Board `primary`
front face and its `front-inverted` presentation. It proves the app renderer and package seam
before Workbench support, exhaustive schema matrices, asset cleanup, the other
Port faces, or any catalog-wide migration are built.

## Goal

Render the Port front face from one exact transparent, cord-free source image
in upright and 180-degree clock-face orientations. The board, holds, markers,
hit shapes, eyelets, and eyelet foreground pieces share one 2D affine
transform. The support bight, knot, and pull point stay fixed above the board
in screen coordinates.

The slice succeeds when two isolated transparent board-canvas renders match
the approved spike at `0°` and `180°`, the hold geometry stays aligned, and
every presentation without a resolved rig follows the current image path
unchanged.

## Validated reference

The approved inverted proof is recorded at
`.context/joyful-donkey-port-front-imagemagick-rotation/front-rotated-180-with-cords.png`.
Its exact bytes are also tracked under `docs/source-audits/review-assets/` so
the PR can retain the approved evidence. It is evidence for the geometry and
visual treatment, not production code.

The manufacturer's product photography supports the near-black braided cord,
dark eyelet entry, and wood face appearance:

- product: <https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard>
- front: <https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840>
- back: <https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840>
- side: <https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840>

The photographs crop the upper suspension connection. The compact top bight
and interwoven knot are therefore a generic, physically plausible
illustration. They must not be documented or presented as the manufacturer's
exact supplied knot.

## Approved coordinate contract

All authored values use a canonical coordinate system and scale
proportionally into the actual SwiftUI canvas. No value is inferred from hold
paths or detected from image pixels.

### Scene and face frames

The transparent scene is exactly `1200 × 1464`, with width-to-height aspect
ratio `50 / 61`. Raising the pull point did not scale the board. Instead, the
previous `1200 × 1250` composition was translated down by `214` units and
transparent headroom was added.

| Name | Coordinate space | Value | Purpose |
| --- | --- | --- | --- |
| `sceneSize` | canonical scene | `(1200, 1464)` | complete transparent output |
| `sourceFrame` | scene | `(x: 0, y: 214, width: 1200, height: 1250)` | embeds the previous composition at unchanged scale |
| `innerFaceFrame` | relative to `sourceFrame` | `(x: -100, y: -10, width: 1400, height: 1400)` | draws the exact square source raster and maps canonical holds |

The resulting face-image frame in scene coordinates is
`(x: -100, y: 204, width: 1400, height: 1400)`. The source raster's nonzero
alpha bounds are `[216, 316]–[1185, 1157]`, so the visible face bounds become
`[116, 520]–[1085, 1361]` in the scene and remain fully inside it. Transparent
pixels may extend outside the horizontal scene edges; visible pixels may not.

`sourceFrame` and `innerFaceFrame` are canonical layout data, not crop
instructions. The source PNG is decoded unchanged, drawn once into the inner
frame, and clipped only by the outer scene.

### Face, pivot, anchors, and pull point

The following values are relative to `sourceFrame` unless noted otherwise:

| Item | Source-frame value | Scene value |
| --- | --- | --- |
| face rotation center | `(600, 690)` | `(600, 904)` |
| left eyelet endpoint | `(276, 804)` | `(276, 1018)` |
| right eyelet endpoint | `(920, 804)` | `(920, 1018)` |
| pull point / strand-exit midpoint | `(600, 71.5)` | `(600, 285.5)` |
| left strand exit | `(578, 71.5)` | `(578, 285.5)` |
| right strand exit | `(622, 71.5)` | `(622, 285.5)` |

The front proof manually selected source-image eyelet centers near `(375, 813)`
and `(1019, 813)`. The rig endpoints are one pixel-center unit lower/right,
which makes the exact cardinal runtime transform land at the approved raster's
screen endpoints `(280, 790)` and `(924, 790)`.
The inverted alias declares a normalized scene rotation anchor of
`(0.5, 113 / 183)`, which resolves to the scene point `(600, 904)`.

The `71.5` pull-point y-coordinate is inherited unchanged from the previously
approved raised-support template. That template's 50% raise was exact:

```text
old vertical distance = 712 - 285   = 427
new vertical distance = 712 - 71.5  = 640.5
640.5 = 1.5 × 427
```

The upper assembly was translated upward by `213.5` source units; its scale
and shape did not change. The complete stroked result must remain inside the
`1200 × 1464` scene.

## Clock-face projection

The projection is a two-dimensional rotation in the image plane. It must not
use `rotation3DEffect`, perspective, skew, or an x/y-axis flip. For scene point
`p = (x, y)`, scene pivot `c = (c_x, c_y)`, and clockwise screen angle `θ`:

```text
x' = c_x + cos(θ)(x - c_x) - sin(θ)(y - c_y)
y' = c_y + sin(θ)(x - c_x) + cos(θ)(y - c_y)
```

Production currently requests only `θ = 0°` for `primary` and `θ = 180°` for
`front-inverted`; the browser spike's `90°` view was only an axis proof. One
affine transform rotates all face-owned layers:

- the cord-free face image;
- canonical hold paths;
- highlight and hit-test paths;
- number-marker positions;
- the two eyelet attachment points; and
- the source image used by the small foreground eyelet crescents.

The pull point, strand exits, bight, and knot never receive that transform.
At `180°`, the projected physical endpoints are `(924, 790)` and `(280, 790)`.
They are sorted by screen `x` (then `y` only as a deterministic tie-break) and
paired to the left and right exits in that order. This intentional visual
pairing supersedes the earlier declared-order rule and prevents a crossed
render after inversion.

At an exactly side-on `90°`/`270°` angle the flat model can place both eyelets
on one screen x-coordinate. That is a known ambiguity of a 2D illustration,
not a rope-physics problem, and no such presentation ships in this slice.

## Package model

Add an optional, closed `cordRig` object to a canonical presentation. The
first tagged topology is `directTwoAnchor`; using an enum in Swift preserves a
clean extension point without claiming it fits every board.

```json
"cordRig": {
  "type": "directTwoAnchor",
  "sceneSize": {"width": 1200, "height": 1464},
  "sourceFrame": {"x": 0, "y": 214, "width": 1200, "height": 1250},
  "innerFaceFrame": {"x": -100, "y": -10, "width": 1400, "height": 1400},
  "attachmentPoints": [
    {"x": 276, "y": 804},
    {"x": 920, "y": 804}
  ],
  "pullPoint": {"x": 600, "y": 71.5},
  "eyeletRadius": 34
}
```

All points other than the normalized presentation rotation anchor use the
canonical source units above. The renderer derives strand exits as
`pullPoint.x ± 22` at `pullPoint.y` for this topology. Cord color, stroke
layers, braid, and the generic upper template are renderer-owned visual
constants rather than manufacturer claims or per-package tuning fields.

The runtime shape is:

```swift
enum BoardCordRig: Hashable {
    case directTwoAnchor(BoardDirectTwoAnchorCordRig)
}

struct BoardDirectTwoAnchorCordRig: Hashable {
    let sceneSize: CGSize
    let sourceFrame: CGRect
    let innerFaceFrame: CGRect
    let attachmentPoints: [CGPoint]
    let pullPoint: CGPoint
    let eyeletRadius: CGFloat
}
```

The decoder and writer enforce the closed keys, the exact two-point count,
finite numbers, positive sizes/radius, a positive scene, and a
`sceneSize`/presentation aspect-ratio match. A rig may be owned only by a
canonical presentation. An alias inherits its canonical rig and never
overrides it. Rigged-alias hold-bounds validation maps canonical hold corners
through the inner face and source frames before applying the scene affine;
non-rig aliases retain the current normalized validation path.

For a resolved rig, the presentation aspect ratio describes `sceneSize`, while
the PNG aspect ratio describes `innerFaceFrame`. This deliberate distinction
allows the exact square source PNG to sit inside the taller transparent scene.
An alias may declare that same canonical square asset path; it is checked
against the square inner-face ratio even though the presentation itself uses
the taller scene ratio. Non-rig image-aspect checks remain unchanged.

Rendering a resolved rig deliberately loads the canonical source
presentation's asset. In this approved slice, `front-inverted` also declares
that canonical `assets/primary.png` path, so there is exactly one stored front
face raster and no transitional alias raster.

## Deterministic cord artwork

The cord is stateless path artwork. It has no physics solver, sag, spring,
collision detection, animation, gesture, or random input.

At canonical scale the approved paths are the spike's exact geometry. The
following commands are relative to `pullPoint = (600, 71.5)`:

```text
bight:
M(-12,-61)
C(-26,-82) (-30,-115) (-21,-142)
C(-14,-163) (-5,-174) (1,-177)
C(9,-171) (18,-157) (24,-136)
C(31,-109) (26,-81) (12,-61)

left knot/exit:
M(-12,-63)
C(1,-52) (18,-51) (21,-39)
C(24,-28) (16,-19) (5,-18)
C(-8,-17) (-17,-9) (-22,0)

right knot/exit:
M(12,-63)
C(-1,-52) (-18,-51) (-21,-39)
C(-24,-28) (-16,-19) (-5,-18)
C(8,-17) (17,-9) (22,0)

knot overpass:
M(-18,-35) C(-10,-24) (9,-22) (18,-35)
```

Each strand is one straight segment from an exit to its screen-paired
projected eyelet. The approved dark braid is rendered proportionally in these
passes:

1. soft contact shadow: width `35`, offset `(4, 5)`, blur `2.3`, black at
   `0.34` opacity;
2. outline: width `31`, `#050607`;
3. body: width `25`, `#151718`;
4. clipped `12 × 12` alternating diagonal braid over a width-`23` stroke;
5. broken fiber ridge: width `2.4`, dash `1.5 / 5.5`, light gray at `0.18`
   opacity, offset `(-2, -1)`; and
6. a dark separation stroke under the redrawn knot overpass.

Line caps and joins are round. The canvas background remains transparent.
These constants reproduce the approved visual; they are not physical cord
measurements.

## Eyelet continuity

The cord is above the main face image, but a small piece of the same transformed
face image is redrawn above each cord endpoint. A full annulus is forbidden
because it visibly cuts the strand. The foreground piece is a
direction-aware crescent opposite the outgoing strand.

For eyelet center `center`, assigned strand exit `toward`, radius `r = 34`, and
chord offset `d = 7` in canonical units:

```text
u = normalize(toward - center)
n = (-u.y, u.x)
s = sqrt(r² - d²)
start = center + d·u + s·n
end   = center + d·u - s·n
```

The major circular arc from `start` to `end` closes the crescent. Clip a
second draw of the already transformed canonical face image to that path.
This hides the strand's terminal cap beneath the near eyelet lip while leaving
the strand visually continuous into the black center at every orientation.

## Shared artwork and legacy branch

Both board-map sites use one `BoardPresentationArtwork` resolver. For a
resolved rig, its z-order is:

1. canonical cord-free face in `innerFaceFrame`, with the selected
   presentation's clock-face transform;
2. cord shadow, braid, bight, knot, and two taut strands;
3. the two transformed-image foreground eyelet crescents;
4. existing hold highlights and hit shapes; and
5. existing detail-map number markers.

The cord and crescents are decorative:
`.allowsHitTesting(false)` and `.accessibilityHidden(true)`.

For a presentation with no resolved rig, the resolver must call the existing
`BoardPresentationImage(board:presentationID:)` with the selected
presentation's own ID, use the full current map rectangle for holds, add no
cord/crescent layer, and apply no image transform. This explicit legacy branch
keeps all non-rig boards and the three non-opted-in Port presentations
unchanged.

## Port asset and rollout contract

Commit `e12e7f66` is the only approved source for the three transparent,
cord-free Port physical faces:

| Physical face | Historical path | SHA-256 |
| --- | --- | --- |
| front | `assets/primary.png` | `6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0` |
| back | `assets/back.png` | `39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e` |
| pinch side | `assets/side.png` | `cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad` |

All three are `1400 × 1400` RGBA images with transparent backgrounds. The
vertical slice verifies all three historical blobs but promotes only the exact
`primary.png` bytes.

Only these presentation changes ship initially:

| Presentation | Change in this slice |
| --- | --- |
| `primary` | restore exact cord-free `primary.png`; own the approved rig; set aspect ratio to `50 / 61` |
| `front-inverted` | inherit the `primary` rig; share `assets/primary.png`; set aspect ratio to `50 / 61`; declare rotation anchor `(0.5, 113 / 183)` |

The user approved one stored raster per physical face and the removal of
duplicate presentation metadata. `cord-option-4-20mm-incut` resolved to the
same front face and exact 180-degree rotation as `front-inverted`, so that
duplicate record and both redundant front alias PNGs are removed. No hold
record, hold path, hold metadata, remaining presentation name, training
content, or product URL changes.

## Proportional verification

The user explicitly chose visual proof before a broad test/setup investment.
Implementation therefore stops at these gates:

- one geometry test covering canonical frames, the approved raised pull point,
  `90°` clock-face axis proof, `180°` projection, screen-x pairing, uncropped
  upper geometry, and the eyelet-crescent formula;
- one iOS loader/alias test covering canonical ownership, inheritance,
  canonical-image resolution for the inverted alias, and the unchanged
  non-rig branch;
- one iOS writer round-trip test for the exact closed JSON object;
- one Python parser-compatibility test for the same object and Port alias;
- one focused iOS Simulator build; and
- two isolated transparent `1200 × 1464` board-canvas outputs, shown one at a
  time (`primary`, then `front-inverted`) with the manufacturer link.

There is no full unit/UI suite, app-review screenshot set, multi-size matrix,
Workbench gallery, interaction matrix, or accessibility matrix before this
visual gate. The implementation still sets the decorative interaction and
accessibility modifiers; broader regression proof follows only if the slice is
accepted.

## Explicit deferrals

Until the production `primary` and `front-inverted` outputs receive visual
approval, defer all of the following:

- Workbench parsing, authoring, preview, and round-trip support;
- exhaustive malformed/semantic fixture matrices;
- full package, unit, UI, interaction, and accessibility suites;
- changing the other three Port presentations;
- additional rig topology cases; and
- catalog-wide migration.

A catalog audit found 19 remaining cord-attached packages and multiple routing
topology families. “Apply this to all” is therefore a staged program, not a
single `directTwoAnchor` data migration. After this vertical slice is approved,
first migrate the remaining Port faces one by one. Then classify each of the
19 packages from manufacturer evidence and design only the topology families
they actually require. No board is forced into the Port two-anchor model.
