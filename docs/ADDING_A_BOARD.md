# Adding a hangboard

This is the only supported authoring process for a physical Hang Ten board.
Research the product, author its paths directly, validate the finished package,
and visually review it. Physical identity, hold metadata, and exact selectable
geometry live in one `board.json`; research and training-plan semantics stay
outside board packages.

## 1. Establish the physical source of truth

Collect primary manufacturer evidence before naming or classifying holds:

1. The current product page and official dimensions.
2. A straight-on image for spacing and hold count.
3. An oblique or side image for jugs, slopers, shelves, and recess depth.
4. A manufacturer hold-depth diagram, numbered guide, or manual when one exists.
5. Source URLs, review date, and field mappings in a source-audit document.

Do not infer measurements, finger capacity, hand capacity, or grip posture when the source does
not establish them. Omit unknown optional fields instead of supplying defaults.

Establish whether the evidence describes a genuinely different physical
revision or another selectable surface, side, or mounting orientation of the
same product. Different revisions get stable packages of their own so saved
identity is never overwritten; presentation-only changes stay in one package.

## 2. Freeze the physical hold inventory

List every distinct physical contact before drawing. Continuous contact surfaces
are one logical hold even when they require multiple disconnected geometry
pieces. Separate physical contacts are separate holds. Use stable descriptive
IDs and conservative `jug`, `edge`, `pocket`, `pinch`, `sloper`, or `gaston` kinds. A
`gaston` requires an explicit reciprocal `pairedHoldID`; do not infer pairing from geometry.

Do not infer measurements, finger capacity, hand capacity, grip posture, feature tags, or
coaching semantics from a picture. Omit an optional field when the source does
not establish it. Record any app-specific semantic adaptation outside the board
package and label it as an adaptation.

## 3. Create one direct-child package

Every board is a flat directory below `Hangboards/`. Direct discovery treats a
directory containing `board.json` as app content. A finished package contains
exactly `board.json`, an `assets/` directory, and the PNG files declared by its
one or more named presentations:

```text
Hangboards/
  manufacturer-model/
    board.json
    assets/
      primary.png
      optional-additional-presentation.png
```

A partial directory is not an authoring workspace: Workbench does not list or
open it, and app staging ignores it. Create a structurally valid, complete
`board.json` with deliberately authored initial paths before opening the package
in Workbench. Do not add a registry, sidecar JSON, source photo, README, review
directory, generated draft, or duplicate geometry.

`board.json` contains product identity and physical holds. Every hold requires
`id`, `name`, one of `jug`, `edge`, `pocket`, `pinch`, `sloper`, or `gaston`, and a
nonempty `geometry` array. Each geometry piece contains a normalized `frame`, a
closed supported `shape`, and optional physical treatment. Measurements, depth
ranges, finger capacity, hand capacity, grip posture, and feature tags are optional.
When present, `sizeMillimeters` and both `depthRangeMillimeters` bounds must be
positive finite JSON numbers; fractional millimetre values are preserved exactly.
The lower depth bound must not exceed the upper bound.

A `gaston` hold must also declare `pairedHoldID`, the identifier of its explicit
counterpart on the same board. The counterpart must be a different `gaston` hold
whose `pairedHoldID` points back. No other hold kind may declare `pairedHoldID`.
This is pairing metadata only: do not infer it from geometry or validate geometric
symmetry.

`board.json.presentations` is a nonempty array. Every presentation has a unique
identifier, a nonempty display name, an `assetPath`, an image-matching aspect
ratio, and a `default` flag; exactly one presentation is the default. Every
hold's `presentationID` must name one of those presentations. Each `assetPath`
must be a relative `.png` path beneath `assets/`, and the files beneath
`assets/` must exactly match the set of declared presentation assets. Missing
or undeclared asset files and any extra package-root entry are rejected.

For the normal one-surface board, retain the simple convention of one `Primary`
presentation at `assets/primary.png`. When first-party evidence establishes
multiple selectable surfaces, sides, or physical orientations of the same
product, keep one board package and add a clearly named presentation and PNG
for each supported variation. Scope each hold record to the presentation whose
image and canonical geometry it describes; do not split one physical product
into separate catalog boards solely because its presentation changes.

When multiple positions show the same physical face, keep one canonical face
image and make each additional presentation an alias with
`sourcePresentationID`. An alias may declare `rotationDegrees`, a finite
clockwise in-plane rotation normalized to the half-open range `[0, 360)`.
Artwork, hold geometry, markers, and cord attachment points rotate together
around `geometryRotationAnchor` (the normalized canvas center when omitted),
while a cord rig's pull point and support loop remain world-up under gravity.
An alias that declares `rotationDegrees` must reuse its canonical face's
`assetPath`; this keeps one raster per physical face. Explicit rotations other
than 0 or 180 degrees require a `cordRig` on the canonical presentation so its
padded scene prevents rotated artwork from being clipped.
Do not declare both `rotationDegrees` and the legacy `isInverted` field;
`isInverted: true` remains readable as 180 degrees only for compatibility,
including older packages whose inverted alias used a distinct asset.

A presentation may also declare `availableHoldIDs` when only part of its
canonical face is usable in that orientation. The array must be nonempty,
contain unique identifier-shaped hold IDs, and reference only existing holds
owned by that presentation's canonical face. When the field is omitted, every
hold on the canonical face remains available for backward compatibility.
Rendering, highlighting, hit testing, position resolution, and Workbench's
focused editor view all use this effective hold subset.

A canonical presentation may own either the compatible `directTwoAnchor` rig
or a generalized `routed` cord rig. A routed rig retains `sceneSize`,
`sourceFrame`, and `innerFaceFrame`, then declares these required fields:

- `style`: positive finite `diameter`; `outlineColor`, `baseColor`, and exactly
  two `braidColors`, each encoded as `#RRGGBB`.
- `ports`: unique identifier-shaped ports with `space` equal to `body` or
  `world` and a finite `{x, y}` point.
- `tensionGroups`: unique groups containing equally sized, nonempty, internally
  unique `bodyPortIDs` and `worldPortIDs`; `pairing` is `declared` or
  `screenOrder`, and `layer` is `behindFace`, `aboveFace`, or `overpass`.
- `paths`: unique authored cord paths with a `body` or `world` space, a layer,
  and path commands in the same array vocabulary as hold paths: `move`,
  `line`, `quad`, `curve`, and optional terminal `close`.
- `occlusions`: `radialLip` entries reference a body port and require
  `0 < chordOffset < radius`, while `facePatch` entries contain a closed path.

All four routed arrays are required in canonical JSON, including when `paths`
or `occlusions` is empty. Every point and path coordinate is expressed in
finite source-frame-local units: add `sourceFrame`'s origin to place it in the
scene. Body-space geometry rotates with the board; world-space geometry stays
fixed in that scene. Routed rigs follow the same canonical-presentation
ownership, alias inheritance, scene-aspect, and PNG-to-`innerFaceFrame` aspect
rules as `directTwoAnchor` rigs. Unknown rig, space, pairing, layer, command,
and occlusion types are rejected.

The Trango Rock Prodigy Pivot package is the structural and path-style
precedent: it uses smooth normalized closed paths, exact mirroring where the
physical board is symmetric, and multiple pieces only for one genuinely
disconnected contact. It is not a geometry template. Never copy its coordinates
or product-specific hold layout to another board.

Presentation assets must match the established catalog render style for the
real product's material and form factor. For a wood board, use the comparable
wood-board treatment: pale timber, realistic recessed holds, soft studio
lighting, and an off-white background. Do not render a non-wood board as wood;
select a comparable catalog board whose material and form factor match the
product being authored. Before PR submission, review the new asset side by side
with that comparable catalog render and correct visible style mismatches.

## 4. Author canonical geometry directly

Start Workbench from the repository root and open the complete package:

```sh
rtk python Tools/HangboardWorkbench/server.py
```

Draw and refine each hold directly against the presentation image and the
manufacturer evidence. Keep paths economical and smooth without sacrificing
the visible contact boundary. Author one side and mirror it exactly when the
official evidence establishes symmetry; otherwise draw the sides independently.

If the checked-out schema and Workbench support shape constraints, prefer an
operator-selected circle, oval, pill, rounded rectangle, or rectangle for a
hold that genuinely has that regular form. Use a freeform path for irregular
contacts. Selecting a constraint is a human decision, never a pixel-derived
classification. Constraint metadata only preserves editing behavior: the saved
canonical path remains the sole source for rendering, highlighting, and hit
testing. If constraint support has not landed in the current checkout, author
the same geometry as a normal path and do not invent a schema field.

Do not use image-driven hold detection, segmentation, generated masks or
contours, source registration/alignment, vectorization, automatic path
simplification, automatic cropping, or proposal/refine/promote pipelines. Do
not create generated geometry for later cleanup. Direct authoring plus human
review is the process.

## 5. Validate the package and visual result

Validate direct discovery and the package contract after every package change:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
```

`--final-inventory` rejects every incomplete direct child. Do not commit a
primary-only or geometry-less board directory.

## 6. Bundle discovered packages directly

Xcode invokes `scripts/stage-board-packages.py` during every build. It validates
each complete direct child and copies only those package directories into the
app resource bundle. It does not generate a registry or app-side board catalog.

Confirm the package loader compiles with the normal bounded simulator build:

```sh
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
```

## Completion checklist

- Source URLs and field mappings are recorded in a source audit.
- The package root contains exactly `board.json` and `assets/`; the files below
  `assets/` exactly match the one or more presentation assets declared in
  `board.json`.
- Exactly one named presentation is the default. A simple one-surface package
  uses the `Primary` / `assets/primary.png` convention; genuine sourced
  variations remain presentations of the same board.
- Each presentation asset matches the catalog render style for the product's
  actual material and form factor. It has been reviewed side by side with a
  comparable existing catalog board before PR submission.
- Every hold has unique identity and nonempty normalized geometry.
- Unsupported optional physical facts remain omitted.
- Each physical contact is represented once; disconnected pieces share a hold
  only when they form one contact.
- Regular holds use operator-selected constraints when supported and
  appropriate; irregular holds use freeform paths.
- The canonical path—not a constraint or raster—drives rendering, highlights,
  and hit testing.
- The final inventory contains only complete packages and zero drafts.
- Direct discovery and staging tests pass.
- Normal, active, and hit-testing paths are inspected on an owned simulator.
