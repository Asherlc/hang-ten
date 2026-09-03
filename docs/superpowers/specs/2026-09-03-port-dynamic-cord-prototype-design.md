# Port-A-Board Dynamic Cord Prototype Design

## Status and intent

This design is approved for a phase-one prototype on the Frictitious
Port-A-Board. It replaces baked-in cord pixels with a deterministic,
presentation-driven cord layer while preserving the board image and canonical
hold geometry. The renderer and package model are generic from the first
implementation; only the Port-A-Board opts in during phase one.

If the Port prototype passes visual review, phase two is explicitly intended to
convert the rest of the corded-board catalog. That conversion is not part of
this prototype, and no other package changes merely because the renderer
exists.

## Goal and success criteria

Each Port presentation shows a complete, taut suspension above the loaded
board without baking cord pixels into the product image. The rendered scene has
three independently testable inputs:

1. one transparent, cord-free raster for each physical face;
2. canonical hold paths and a canonical pair of normalized cord attachment
   points; and
3. the selected presentation's existing alias/orientation metadata.

The feature succeeds when:

- the same cord-free face bytes are used for a canonical presentation and all
  of its inverted aliases;
- the board image, hold paths, hit targets, markers, and attachment points use
  the same 180-degree projection around `geometryRotationAnchor`;
- the support assembly stays at the top of the screen when the board is
  inverted;
- both strands are straight and taut, and the complete support loop and knot
  remain visible inside the canvas at every supported map size;
- highlights and taps remain aligned with the visible holds;
- the cord is decorative and cannot intercept input or add accessibility
  elements; and
- a board with no opted-in cord rig executes the existing image and hold-map
  path unchanged, with identical rendered output and interaction behavior.

## Current system constraints

`BoardPackageStore` currently requires every presentation to declare an
`assetPath`, requires that path to name a decodable PNG under `assets/`, checks
the image aspect ratio, and requires the package's actual asset files to equal
the set of declared paths. Repeated paths are already representable because
finished-package validation operates on a set.

`sourcePresentationID` identifies the canonical face whose holds an alias uses.
`isInverted` tells `BoardPresentationGeometryProjection` to rotate canonical
hold points and paths by 180 degrees. `geometryRotationAnchor` supplies the
normalized pivot and defaults to the canvas center when absent. The store
already rejects alias chains, mismatched aspect ratios, invalid normalized
anchors, and projected hold frames outside the canvas.

The image is different: `BoardPresentationImage` currently loads the selected
presentation's declared file without applying the geometry projection. The
Port package therefore contains separately rendered upright and inverted
rasters with cords included. This is the seam the prototype changes. The
existing projection remains the coordinate authority and is extended so its
single affine transform can also position the opted-in face image and cord
anchors.

Both `BoardMapView` and `BoardDetailMapView` place the image below hold visuals
in a `ZStack`. The detail map also places numbered markers above the image.
The prototype must preserve that shared-bounds invariant and must not create a
second, approximately equivalent transform.

## Scope

Phase one includes:

- a strict, reusable `cordRig` package schema;
- a generic runtime model and deterministic renderer;
- schema parity in the iOS loader/writer, Python package validator, and
  Hangboard Workbench;
- three transparent, cord-free Port face assets (`primary`, `back`, and
  `side`), shared by aliases rather than duplicated;
- Port configuration for all six existing presentations: Front Upright, Front
  Inverted, Cord Option 4 — 20 mm In-cut, Back Upright, Back Inverted, and
  Pinch Side; and
- focused unit, package, rendering, interaction, accessibility, and visual
  acceptance tests.

Phase one does not include rope physics, sag, slack, collision detection,
board/cord intersection solving, animation, dragging, interactive rotation,
spring behavior, or a catalog-wide package conversion. It also does not
change any hold path, hold metadata, training content, or Port presentation
name.

## Approaches considered

### 1. Deterministic presentation renderer — recommended

Store a small direct-rig description with a canonical presentation. Render a
fixed loop-and-knot template plus two straight tensioned strands. For an
inverted alias, rotate only the shared face image, canonical holds, and the two
attachment points around `geometryRotationAnchor`; leave the support assembly
in world-up canvas coordinates.

This approach makes orientation correct by construction, preserves exact face
pixels, is cheap to render, is straightforward to snapshot, and provides one
reusable code path for later package adoption. Its limitation is intentional:
the first schema represents one direct two-anchor topology, not every possible
corded product.

### 2. Full rope simulation — rejected

A particle, spline, or constraint simulation could model gravity, sag,
collisions, and interactive motion. It would also introduce time-dependent
output, tuning state, device-dependent settling, clipping edge cases, and
accessibility/interaction risk for a scene that is meant to be a static product
diagram. It would make screenshot tests nondeterministic and would still need
package-specific topology. None of those costs advances the prototype's
purpose.

### 3. Pre-rendered cord overlay images — rejected

Transparent overlay PNGs would preserve the board raster but would retain one
cord asset per orientation and canvas composition. Each alias would need a
separately reviewed overlay, support direction could drift, scaling could
soften the cord independently of the board, and phase-two migration would
multiply assets. Overlays also move alignment and cropping errors into manual
raster production. Deterministic vector geometry gives stronger invariants
with less package data.

## Package and runtime model

Add an optional `cordRig` to a canonical presentation. The runtime model is an
enum so later deterministic topologies can be added without Port-specific
conditionals:

```swift
enum BoardCordRig: Hashable {
    case directTwoAnchor(BoardDirectTwoAnchorCordRig)
}

struct BoardDirectTwoAnchorCordRig: Hashable {
    let attachmentPoints: [BoardNormalizedPoint] // validated count: exactly 2
    let supportPoint: BoardNormalizedPoint
    let cordColor: BoardRGBColor
    let cordWidth: Double
    let loopRadius: Double
}
```

`cordWidth` and `loopRadius` are fractions of the shorter presentation-canvas
dimension. `supportPoint` is the center reference for the renderer's fixed
world-up loop-and-knot template. Attachment points are in the canonical face's
normalized coordinates, in declared order. They identify physical cord exits,
such as the centers of the Port eyelets; they are not hold geometry and are
authored deliberately from manufacturer evidence rather than detected from
pixels.

The JSON is a closed tagged object. This example is a synthetic parser fixture,
not Port authoring data:

```json
"cordRig": {
  "type": "directTwoAnchor",
  "attachmentPoints": [
    {"x": 0.30, "y": 0.64},
    {"x": 0.70, "y": 0.64}
  ],
  "supportPoint": {"x": 0.50, "y": 0.10},
  "cordColor": "#171719",
  "cordWidth": 0.012,
  "loopRadius": 0.045
}
```

There are no optional topology fields in phase one. In particular there are
no control points, per-strand curves, loose ends, wrapping rules, collision
surfaces, simulation constants, or animation settings.

The rig belongs only to a canonical presentation
(`sourcePresentationID == nil`, `isInverted == false`). An alias inherits the
rig of its `sourcePresentationID`; it cannot declare or override one. This
keeps physical attachment ownership beside canonical hold ownership. The
selected presentation still drives the result: it selects the canonical face,
orientation, rotation anchor, asset, name, and picker state.

## Strict validation contract

All schema consumers reject unknown keys and implement the same rules:

- `type` must be exactly `directTwoAnchor`.
- `attachmentPoints` must contain exactly two distinct points. Every coordinate
  must be a finite JSON number in `[0, 1]`.
- `supportPoint` must contain exactly finite normalized `x` and `y` values.
- `cordColor` must be an opaque six-digit `#RRGGBB` sRGB value.
- `cordWidth` and `loopRadius` must be finite and positive, and the loop radius
  must be large enough for the standard knot template at the declared width.
- The stroke-expanded bounds of the computed loop, knot, and strands must be
  entirely inside the normalized canvas.
- The support assembly must be above both attachment points in canvas
  coordinates. The same rule is checked again after projecting attachment
  points for every inverted alias of that canonical face.
- `cordRig` is invalid on an alias. An inverted alias of a rigged source must
  declare an explicit finite normalized `geometryRotationAnchor`, even when
  the intended value is `{ "x": 0.5, "y": 0.5 }`.
- A rigged alias's required `assetPath` must equal its canonical source's
  required `assetPath`. Its aspect ratio must continue to match the source.
- A rigged canonical asset must be a readable RGBA PNG with meaningful
  transparency, transparent corners, nonempty visible content, and no cord
  pixels. Its alpha-content bounds, transformed around each alias's rotation
  anchor, must remain inside the target canvas. The final no-cord assertion is
  a documented human review because cord recognition must not be implemented
  as image segmentation.

The existing `assetPath` field is not made optional. Package validation still
compares the actual file set with the unique set of declared paths. Shared
canonical/alias paths therefore reduce physical files without weakening the
package boundary.

Syntactically malformed rig data produces the same malformed-document failure
as other decoding errors. Semantically invalid coordinates, relationships,
appearance values, or computed bounds produce an `invalidPackage` error naming
the presentation and failed rule. Invalid rigs never silently fall back to a
partial or legacy cord rendering.

These stricter alpha, shared-path, and rig rules run only for opted-in rigs.
They do not retroactively reject or reinterpret existing packages.

## Coordinate and rendering contract

`BoardPresentationGeometryProjection` exposes one affine transform for a
canvas rectangle. For a normalized anchor `(a_x, a_y)`, inverted points retain
the existing formula:

```text
x' = 2a_x - x
y' = 2a_y - y
```

One projection instance is created for the selected presentation and passed to
all presentation layers.

- A canonical presentation loads its own cord-free image without a transform.
- A rigged alias loads the exact same `assetPath` bytes as its canonical
  source and applies the projection's 180-degree affine transform to the image.
- Canonical hold paths, marker centers, interaction shapes, and accessibility
  shapes continue to use that projection.
- The canonical rig's two attachment points use that projection.
- `supportPoint`, the loop, and the knot are canvas/world coordinates. They are
  never projected, so the support remains above the board in both
  orientations.

`BoardCordRigGeometry` is a pure function of the validated rig, presentation,
and canvas rectangle. It creates a fixed closed support loop, a compact
symmetric binding-knot path immediately below it, and two straight paths from
the knot exits to the projected attachment points. Width, loop scale, line caps,
joins, and all Bezier coefficients are constants or declared rig values; there
is no clock, random input, previous frame, solver, or device motion. The pure
result exposes its stroke-expanded bounding box so package tests and runtime
assertions can prove that the complete loop and knot are not cropped.

`directTwoAnchor` permanently identifies one normalized path template. Its
loop, knot, exit-point, cap, join, and strand-order formulas are frozen in a
shared fixture contract with expected normalized path elements and bounds.
Swift and Workbench implement that contract independently and run the same
fixtures. Changing the shipped template's topology requires a new `type`, not
silent retuning that changes existing packages.

The renderer is a normal stateless SwiftUI view backed by those paths. It adds
no gesture and opts out of implicit animation. Selecting a presentation may
replace one deterministic geometry with another, but the cord does not swing,
settle, interpolate, or respond to a drag.

## Shared presentation artwork layer

Add one shared artwork component used by `BoardMapView` and
`BoardDetailMapView`. It owns only the image and optional cord, while the
screens retain their existing hold and marker construction. This keeps the
prototype narrow and ensures the two cord render sites cannot drift. Within
the exact explicit `boardBounds`, the z-order is:

1. the transparent cord-free board image, transformed only for an opted-in
   alias;
2. the dynamic cord layer, including both taut strands and the entire support
   loop/knot;
3. hold highlight visuals and their existing interaction/accessibility shapes;
   and
4. numbered detail-map markers.

The cord starts at the declared eyelet centers and is allowed to occlude the
underlying board only along its visible drawn path. The tracked source PNG is
never painted, masked, inpainted, composited, cropped, or regenerated by this
feature; normal display scaling remains the existing SwiftUI behavior.
Highlight geometry remains above the cord so an active hold is legible even
where a strand crosses the face.

The shared artwork layer must preserve the current aspect-fit container and give
the image, cord geometry, holds, markers, and interaction shapes the identical
canvas rectangle. An alias is rejected rather than corrected with a separate
image offset, per-layer anchor, or hand-tuned hold translation.

## Port-A-Board phase-one package

Phase one restores the repository's last cord-free, transparent 1400 × 1400
RGBA canonical face assets from commit `e12e7f66` and preserves their bytes:

| Physical face | Asset | SHA-256 |
| --- | --- | --- |
| front | `assets/primary.png` | `6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0` |
| back | `assets/back.png` | `39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e` |
| pinch side | `assets/side.png` | `cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad` |

The implementation re-verifies those hashes, dimensions, alpha, transparency,
and visual contents before promotion. If a historical blob fails a stated
gate, implementation stops for user review; it does not repair or regenerate
the board. This is how the prototype preserves exact board, labels, hold
relief, grommets, and transparent-background pixels.

Every existing Port presentation remains in the picker, but the six records
declare only three unique paths:

| Presentation | Role | Required `assetPath` | Cord behavior |
| --- | --- | --- | --- |
| `primary` | canonical front upright | `assets/primary.png` | owns front direct rig |
| `front-inverted` | inverted alias of `primary` | `assets/primary.png` | rotates front image and attachments around its explicit anchor |
| `cord-option-4-20mm-incut` | inverted alias of `primary` | `assets/primary.png` | uses the same exact face/orientation and direct rig; no unique routing is invented |
| `back` | canonical back upright | `assets/back.png` | owns back direct rig |
| `back-inverted` | inverted alias of `back` | `assets/back.png` | rotates back image and attachments around its explicit anchor |
| `side` | canonical pinch side | `assets/side.png` | owns side direct rig |

An operator supplies the final normalized attachment, support, width, loop,
color, and alias-anchor values by deliberate review of the manufacturer
evidence and the restored face art. They must pass the closed validation and
visual gates above. No value is inferred by hold detection, segmentation,
registration, vectorization, or automatic pixel analysis. The `holds` array
and every saved hold path remain unchanged.

The now-redundant `front-inverted.png`, `back-inverted.png`, and
`cord-option-4-20mm-incut.png` files are removed only when their presentation
records share the canonical paths and full package validation passes. This
leaves exactly one cord-free image per physical Port face.

## Fallback and non-opted-in behavior

The optional model value defaults to `nil` for hand-built fixtures and package
presentations without `cordRig`. When the resolved canonical presentation has
no rig, both map screens execute the current `BoardPresentationImage` path:
they load the selected presentation's own `assetPath`, do not source-remap or
transform the image, add no cord view, and retain current hold projection and
interaction behavior. This conditional legacy branch is an explicit
compatibility requirement, not merely an expectation that an empty cord layer
will look equivalent.

For an opted-in rig, failure to load the already validated face image suppresses
the entire image-plus-cord layer and raises a debug assertion rather than
showing a floating cord. Normal package loading should make that state
unreachable. It does not fall back to a separately baked alias image.

## Accessibility and interaction

The cord view uses `.allowsHitTesting(false)` and
`.accessibilityHidden(true)`. It has no `contentShape`, labels, actions, focus,
or hover state. The existing single projected hold path remains the source for
fill, stroke, tap hit testing, VoiceOver target, and marker placement. Existing
surface-picker labels and hold announcements do not change.

Tests must prove that taps on a strand but outside a hold do nothing, taps on a
hold under a strand still select the hold, and VoiceOver exposes no additional
cord or support element.

## Extension point and phase-two intent

Application code switches on the `BoardCordRig` enum and contains no check for
the Port board ID, manufacturer, asset filename, or presentation name. Package
data is the only opt-in mechanism.

After Port visual approval, phase two is intended to convert every corded board
to cord-free face assets and deterministic rigs. The catalog must be audited
presentation by presentation; this prototype does not claim that every product
has the Port topology. Boards that use more than two direct attachments or
simple evidence-backed guide points will require separately approved additive
enum cases, such as `directMultiAnchor` or `waypointBranches`. Those cases can
reuse normalized points, appearance, projection, bounds validation, layer
stack, and fallback behavior without changing existing `directTwoAnchor`
documents.

That extension seam is deliberate, but the extra cases are not accepted by the
phase-one parser and are not implemented speculatively. Complex body wraps,
crossings whose order conveys product identity, pulleys, collisions, slack,
sag, and simulated rope behavior remain outside this prototype. A later board
blocks on a faithful topology design rather than being forced into two straight
strands.

## Implementation surfaces

The implementation plan should cover these coherent surfaces:

- `TrainingModels.swift`: normalized point/color types, the tagged cord-rig
  model, optional canonical presentation ownership, and a reusable affine
  projection accessor;
- `BoardPackageStore.swift`: strict decoding, semantic relationship checks,
  rig-only PNG/alpha/content-bounds validation, and runtime model adaptation;
- `BoardPackageWriter.swift`: exact schema round-trip and matching validation;
- `BoardMapView.swift` plus a focused cord-geometry/view file: the shared artwork
  stack, exact image projection, pure deterministic path construction, and
  decorative behavior;
- `Tools/HangboardPackages` and `Tools/HangboardWorkbench`: schema parity,
  validation, API/types, read-only alias projection, authoring/round-trip, and
  preview of the same resolved rig geometry;
- `Hangboards/frictitious-port-a-board`: only presentation/rig fields and the
  three exact restored assets; and
- authoring documentation and the Port source audit: explain `cordRig`, shared
  alias assets, manual anchor authorship, transparency, and visual evidence.

No runtime or tool component may contain Port-specific geometry constants.

## Test and visual acceptance plan

### Model and schema tests

- Decode and round-trip a valid direct rig through the iOS loader/writer,
  Python catalog model, and Workbench.
- Reject every unknown key, unknown type, missing required value, wrong JSON
  type, nonfinite/out-of-range point, duplicate attachment point, invalid
  color, nonpositive width/radius, cropped computed path, downward support,
  alias-owned rig, rigged alias with a different asset, missing explicit alias
  anchor, and projected content outside the canvas.
- Preserve existing error categories and verify an omitted rig decodes as
  `nil`.
- Keep current source/alias aspect-ratio, alias-chain, projected-hold-frame,
  package-root, declared-asset-set, and PNG checks passing.

### Pure geometry and rendering tests

- Assert exact projected attachment coordinates for upright, centered-inverse,
  and noncenter-anchor inverse fixtures.
- Assert the face image, a hold point, its marker, and each attachment all use
  the same affine transform.
- Assert the support point and loop/knot path are unchanged between source and
  inverted alias while the face and attachments rotate 180 degrees.
- Freeze the deterministic path commands and stroke-expanded bounds at least
  two canvas sizes; prove the loop is closed, both strands are straight, and
  no geometry is outside the canvas.
- Snapshot both map screens so their layer ordering and geometry are identical
  apart from detail markers.
- Capture a before/after pixel snapshot of representative non-rig canonical
  and alias presentations and require identical hashes. Exercise their existing
  taps and VoiceOver output as a behavioral regression gate.

### Port package and visual acceptance

- Assert the three canonical face hashes listed above, 1400 × 1400 RGBA format,
  meaningful transparency, transparent corners, and exactly three unique
  declared/actual asset paths.
- Assert the six presentation-to-source/path relationships in the phase-one
  table and unchanged canonical hold JSON.
- In the app and Workbench, capture all six presentations at compact and large
  map sizes with one real hold selected on each physical face.
- At original-resolution inspection, verify unchanged face pixels beneath the
  vector layer, exact hold/highlight alignment, cord endpoints centered on the
  reviewed attachments, straight upward strands, a complete uncropped loop
  and knot, transparent surroundings, no lower support, and no generated or
  erased board detail.
- For each inverted alias, compare against its source and verify that board
  pixels, holds, markers, hit targets, and attachments are the same 180-degree
  transform around the declared `geometryRotationAnchor`, while the support
  remains world-up.
- Perform tap and VoiceOver checks with the cord visible and confirm no cord
  interaction or accessibility element exists.

Phase one is complete only after automated gates pass and the user approves
the six-view Port visual gallery. That approval is the gate to plan the
phase-two catalog conversion; it does not silently start or authorize the
conversion.
