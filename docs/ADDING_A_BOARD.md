# Adding a hangboard

This is the supported authoring process for a physical Hang Ten board. Research
the exact revision, record source mappings, author canonical geometry directly,
validate the package, and visually review it. Never invent training content or
derive a contact fact from the image or model.

Catalog boards retain one flat `Hangboards/<slug>.FCStd` containing native
FreeCAD geometry and embedded board, cord, and simulation inputs; runtime
assets are generated. Use `migrate-hangboard-to-3d` for CAD geometry or model
integration work. For a portable 3D
board's cord, attachment, suspension audit, or suspected Apple offline/ODR
cache issue, use `audit-3d-hangboard-suspension` and read
[`3D_SUSPENSION_AND_ODR.md`](3D_SUSPENSION_AND_ODR.md); that model-specific
contract governs its cord metadata and native solver authoring.

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

Every catalog board has one flat native source in `Hangboards/`. Generated
runtime assets keep the existing package directory. Commit the FCStd and source
audits; generate the runtime files:

```text
Hangboards/
  manufacturer-model.FCStd     # geometry + embedded board/cord/physics inputs
  manufacturer-model/assets/
    primary.usdz              # ignored build output
    primary.model.json        # ignored build output
    suspension.json           # optional ignored solved suspension artifact
    primary.physics.json      # optional ignored build output
```

In the FCStd's `HangTenBoardManifest`, set `schemaVersion` to `3` and declare stable board/revision identity,
`equipmentObjects[]`, `contacts[]`, any sourced positions, and one or more
presentations. Exactly one presentation is default. Keep evidence, source
photos, drafts, and review output outside the board package. Only the supported
flat source documents and declared generated package assets belong under
`Hangboards/`; no authored JSON sidecars belong in the package.

For model media, declare only the USDZ asset, descriptor, display, and any
audited orientation/suspension configuration. The descriptor binds source
contacts to actual model nodes and cached measurements. A model package has no
raster fallback and is read-only in the apps.

The package has no committed `board.json`. The board document is generated from
the FCStd's `HangTenBoardManifest` property plus validated generated
`assets/suspension.json` at build time (package validation, iOS and Android
staging), and the validator rejects an on-disk copy. Cord topology, dimensions,
solver settings, evidence, pose rotations/cameras, and optional
`offsetXZ: [x, z]` live in document-level `App::PropertyString`
`HangTenSuspensionAuthoring`; optional simulation inputs live in
`HangTenRopePhysics`. Hashes, settled heights, and generated routes are outputs.
Change the metadata as in "Board metadata" in `Tools/HangboardCAD/README.md`. To author a
new CAD-backed board, follow
[the CAD authoring guide](../Tools/HangboardCAD/README.md).

## 4. Author and review native geometry

Author the exact revision's Sketcher profiles, native body, and contact regions
directly from approved primary evidence. Keep disconnected pieces bound to the
same physical contact when appropriate and mirror genuinely symmetric products.
Set the document contract and explicit node/contact bindings described in the
CAD guide. The saved FCStd must build independently of any temporary authoring
script. Ship unbound meshes without materials or textures.

Record published facts separately from estimated display dimensions. The
hash-bound [depth audit](../Tools/HangboardCAD/display_depth_audits.json) retains
the reviewed Beastmaker metadata/display differences; it does not authorize
changing those sources or weakening depth validation for other boards.

For every geometry change, build exports from both the prior committed source
and the changed source, render front/side/top views side by side, and review the
result in the app. Preserve that evidence before reporting completion.

### Supported raster geometry

The schema also supports raster presentations. For those packages, author every
canonical path directly in `board.json`; the apps
only read packages and have no in-app editor. Deliberately draw and review
every canonical path against manufacturer evidence. Prefer
exact left/right mirroring only when the product is actually symmetric. Use a
human-selected circle, oval, pill, rounded rectangle, or rectangle constraint
for a genuinely regular contact; use freeform paths otherwise.

The saved path is the sole rendering, highlighting, and hit-testing source.
Constraints preserve editing intent only. Never use image segmentation,
detection, generated contours, source registration, vectorization, automatic
simplification/cropping, or proposal/refine/promote geometry pipelines.

The Trango Rock Prodigy Pivot is a structural precedent, not a coordinate
template. Review the product's shape against primary evidence and a comparable
catalog board.

## 5. Validate and bundle

```sh
rtk git lfs pull
rtk proxy bash scripts/build-runtime-assets.sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData
```

Xcode's staging script validates and copies complete direct-child packages; it
generates bundled `board.json` and does not create a registry or convert older
schemas. For CAD-only iteration, `scripts/build-board-assets.sh --package <slug>`
rebuilds that board. CI uses a producer artifact from the pinned native build;
consumer jobs download it before validation or staging. Generated files stay
ignored. See [generated artifacts](GENERATED_ARTIFACTS.md).

## Completion checklist

- Every factual field maps to cited primary evidence; unsupported fields are absent.
- The package is schema v3 with exact declared assets and one default presentation.
- Native geometry, board metadata, and authored cord/simulation inputs are retained
  in the flat FCStd; generated files are ignored.
- Contact facts appear only in `contacts[]`; raster paths appear only in
  `media.contactGeometry` and model bindings only in the descriptor.
- Every raster path was directly authored and human reviewed; no geometry was inferred.
- Model assets/descriptors are hash-bound and model packages have no fallback.
- Package validation, direct staging, full tests/build, and owned-simulator review pass.
