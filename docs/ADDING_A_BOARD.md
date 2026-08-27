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

## 2. Freeze the physical hold inventory

List every distinct physical contact before drawing. Continuous contact surfaces
are one logical hold even when they require multiple disconnected geometry
pieces. Separate physical contacts are separate holds. Use stable descriptive
IDs and conservative `jug`, `edge`, `pocket`, `pinch`, or `sloper` kinds.

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
`id`, `name`, one of `jug`, `edge`, `pocket`, `pinch`, or `sloper`, and a
nonempty `geometry` array. Each geometry piece contains a normalized `frame`, a
closed supported `shape`, and optional physical treatment. Measurements, depth
ranges, finger capacity, hand capacity, grip posture, and feature tags are optional.
When present, `sizeMillimeters` and both `depthRangeMillimeters` bounds must be
positive finite JSON numbers; fractional millimetre values are preserved exactly.
The lower depth bound must not exceed the upper bound.

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

The Trango Rock Prodigy Pivot package is the structural and path-style
precedent: it uses smooth normalized closed paths, exact mirroring where the
physical board is symmetric, and multiple pieces only for one genuinely
disconnected contact. It is not a geometry template. Never copy its coordinates
or product-specific hold layout to another board.

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
