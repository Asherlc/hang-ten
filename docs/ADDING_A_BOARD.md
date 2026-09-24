# Adding a hangboard

This is the supported authoring process for a physical Hang Ten board. Research
the exact revision, record source mappings, author canonical geometry directly,
validate the package, and visually review it. Never invent training content or
derive a contact fact from the image or model.

This document describes direct raster-board authoring. For model-media
migration or refinement, use `migrate-hangboard-to-3d`. For a portable 3D
board's cord, attachment, suspension audit, or suspected Apple offline/ODR
cache issue, use `audit-3d-hangboard-suspension` and read
[`3D_SUSPENSION_AND_ODR.md`](3D_SUSPENSION_AND_ODR.md); that model-specific
contract supersedes the raster-only package examples below.

## 1. Establish factual evidence

Collect primary manufacturer evidence for the current revision: product page,
dimensions, straight and oblique views, and any official numbered/depth guide.
Record URLs, review date, revision decision, and field-by-field mappings in a
tracked source audit. Omit any optional measurement, capacity, side, pairing,
grip type, or feature the evidence does not establish.

Board facts do not define routine targets. A training plan may contain only the
factual `ContactRequirement` supported by its own plan evidence. Source-generic
work remains targetless and is recorded as the athlete's explicit self-selection;
there is no semantic, contact-ID, or fallback resolution layer.

## 2. Freeze the physical contact inventory

Create one `contacts[]` entry for every distinct physical contact. A continuous
surface is one contact; genuinely disconnected pieces may share one contact ID
only when they are parts of that same physical contact. Use stable descriptive
IDs and a conservative sourced kind. `pairedContactID` is allowed only for an
explicitly documented reciprocal relationship; never infer pairing or symmetry.

Each contact owns facts only:

- required `id`, `equipmentObjectID`, `name`, and `kind`;
- optional `side`, `pairedContactID`, `shape`, `depth`, `fingerCapacity`,
  `handCapacity`, and `gripTypes`, only when directly supported. `shape` is
  one of `flat`, `round`, `incut`, or `slot`. `depth` is exactly one factual
  representation: either `{ "range": { "minimum": ..., "maximum": ... } }`
  for a published measurement or `{ "category": "large" }` (and the other
  supported size categories) when the source gives only a relative size. Never
  convert a source category into an estimated measurement.

Contacts never contain paths, frames, presentation IDs, model nodes, or cached
bounds.

## 3. Create one schema-v3 package

Every board is one direct child of `Hangboards/` with exactly `board.json` and
the assets declared by its presentations:

```text
Hangboards/manufacturer-model/
  board.json
  assets/
    primary.png
```

Set `schemaVersion` to `3`, declare stable board/revision identity,
`equipmentObjects[]`, `contacts[]`, any sourced positions, and one or more
presentations. Exactly one presentation is default. Do not add sidecars, source
photos, drafts, review directories, or undeclared assets to a shipped package.
The conventional raster asset path is `assets/primary.png`; the declaration in
`board.json`, rather than that filename convention, remains authoritative.

For raster media, `media.contactGeometry` maps contact IDs to nonempty arrays of
geometry pieces. Every piece contains a normalized frame, a closed supported
shape, treatment, and optionally an operator-selected shape constraint. This is
presentation-owned media geometry; factual contact fields must not be copied
into it.

For model media, declare only the USDZ asset, descriptor, display, and any
audited orientation/suspension configuration. The descriptor binds source
contacts to actual model nodes and cached measurements. A model package has no
raster fallback and is read-only in the apps.

A model package with a native CAD source (`Hangboards/<slug>/<slug>.FCStd`) is
different: it has no committed `board.json`. The board document is generated from
the FCStd's `HangTenBoardManifest` property at build time (package validation,
iOS and Android staging), and the validator rejects an on-disk copy. Change the
metadata as in "Board metadata" in `Tools/HangboardCAD/README.md`. To author a
new CAD-backed board, follow "Authoring a new CAD board" in that README and
`docs/freecad-authoring-migration.md`.

## 4. Author raster paths directly

Author every canonical path directly in the package's `board.json`; the apps
only read packages and have no in-app editor. Deliberately draw and review
every canonical path against manufacturer evidence. Prefer
exact left/right mirroring only when the product is actually symmetric. Use a
human-selected circle, oval, pill, rounded rectangle, or rectangle constraint
for a genuinely regular contact; use freeform paths otherwise.

The saved path is the sole rendering, highlighting, and hit-testing source.
Constraints preserve editing intent only. Never use image segmentation,
detection, generated contours, source registration, vectorization, automatic
simplification/cropping, or proposal/refine/promote geometry pipelines.

The Trango Rock Prodigy Pivot is the structural and path-style precedent, not a
coordinate template. Review material and render style against a comparable real
catalog product; do not make a non-wood product look like wood.

## 5. Validate and bundle

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
```

Xcode's staging script validates and copies complete direct-child packages; it
does not create a registry or convert older schemas.

## Completion checklist

- Every factual field maps to cited primary evidence; unsupported fields are absent.
- The package is schema v3 with exact declared assets and one default presentation.
- Contact facts appear only in `contacts[]`; raster paths appear only in
  `media.contactGeometry` and model bindings only in the descriptor.
- Every raster path was directly authored and human reviewed; no geometry was inferred.
- Model assets/descriptors are hash-bound and model packages have no fallback.
- Package validation, direct staging, full tests/build, and owned-simulator review pass.
