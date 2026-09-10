# Model-first board packages: Beastmaker 1000 and Wood Grips Compact II

**Status:** approved architecture specification. This replaces all earlier
conflicting design text in this document.

## Scope and principles

Migrate exactly `beastmaker-1000` and `metolius.wood-grips-compact-ii` to a
model-first package. A migrated package owns a USDZ and a generated model
descriptor; it removes its PNG, canonical 2D paths, raster fallback, and any
separate app resource. Unrelated boards retain raster packages and remain
editable in Workbench.

Logical board/hold data is distinct from presentation geometry. A model is the
sole source for its rendering, highlighting, picking, and display-derived
matching geometry. This is display geometry, not manufacturing CAD. Screw
holes, mounting holes, and hardware are deliberately omitted from every model.

For Beastmaker, the 580 × 150 mm face is sourced. The model uses 58 mm depth
from current Beech/shared-layout evidence: the current Tulipwood page's `5 mm`
text conflicts and is not treated as an exact Tulipwood thickness claim. A
generic original pale-wood material is sufficient. Source reports must separate
these facts from estimated positions, radii, cavity sections, and profiles.

## Package schema

The root `board.json` is `schemaVersion: 2`. It contains only logical board and
hold metadata, equipment, positions, transitions, and tagged presentations.
Hold metadata has neither `presentationID` nor render geometry.

Every presentation has common `id`, `name`, `isDefault`, `aspectRatio`, and
`derivation` fields plus `media`. `media.type` is a tagged union:

- `raster`: `assetPath` names a confined PNG; `holdGeometry` maps logical
  `holdID` values to path pieces.
- `model`: `assetPath` names a confined USDZ; `descriptorPath` names its
  generated descriptor; `display` supplies camera configuration.

All packages migrate explicitly. Derived or inverted model media is rejected
until a later typed capability defines it; no renderer infers a safe model
variant from a base presentation.

### Model presentation example

```json
{
  "id": "primary",
  "name": "Beastmaker 1000 3D",
  "isDefault": true,
  "aspectRatio": 3.866666667,
  "derivation": { "type": "original" },
  "media": {
    "type": "model",
    "assetPath": "assets/primary.usdz",
    "descriptorPath": "assets/primary.model.json",
    "display": {
      "camera": {
        "type": "orthographic",
        "viewDirection": [0, 0, -1],
        "up": [0, 1, 0],
        "fitPadding": 0.08
      }
    }
  }
}
```

### Raster presentation example

```json
{
  "id": "primary",
  "name": "Original front",
  "isDefault": true,
  "aspectRatio": 3.861003861,
  "derivation": { "type": "original" },
  "media": {
    "type": "raster",
    "assetPath": "assets/primary.png",
    "holdGeometry": {
      "hold-a": [{ "path": { "commands": [{ "command": "move", "to": [0, 0] }] } }]
    }
  }
}
```

The raster snippet is structural: actual path commands remain package data, and
only raster media may contain them. `display.camera` belongs to the presentation,
not board or hold physical metadata. Runtime derives camera target and scale
from validated model bounds and `fitPadding`.

### Generated descriptor example

```json
{
  "schemaVersion": 1,
  "modelSHA256": "4a50f2b98dd2c0e974ba44bb0514b6a2ccde1faa3ef2b06c5e20173f6ba9d45b",
  "compilerVersion": "hang-ten-model-compiler/1",
  "coordinateFrame": "hang-ten-board-v1",
  "modelBounds": { "min": [0, 0, 0], "max": [0.58, 0.15, 0.058] },
  "nodes": [
    { "nodeID": "Board/Body", "role": "body" },
    { "nodeID": "Board/Hold/JugLeft", "role": "hold", "holdID": "jug-left" }
  ],
  "holds": {
    "jug-left": {
      "facePlaneAABB": { "min": [0.012345678, 0.101234567], "max": [0.145678901, 0.149999999] },
      "center": [0.079012289, 0.125617283]
    }
  }
}
```

`assets/primary.model.json` is generated, never manually edited. It binds the
actual importer-visible USD node IDs to logical identities and indexes
display-derived workout matching data. Every exact importer-visible geometry
node appears once: its role is `body` or `hold`; `hold` requires `holdID`.
Repeated `holdID` values are valid for genuinely disconnected pieces. Every
logical hold has at least one node, all geometry is bound, body is
nonselectable, and no `decoration` role exists. The compiler derives each
per-hold normalized face-plane AABB and center from the union of its mesh
vertices, sorts them by hold ID, and rounds every result to nine decimal
places. Normalization is against the validated `modelBounds` X/Y face plane;
the frame and raw model bounds retain physical metre units.

The canonical USDZ frame is `hang-ten-board-v1`: meters, right-handed, origin
at back-bottom-left when viewing the working face, `+X` right, `+Y` up, and
`+Z` toward the climber. USDZ and descriptor use this frame exactly; importers
and runtime do not normalize names or guess axes.

## Package trees and invariants

Migrated packages have this shape:

```text
Hangboards/beastmaker-1000/
  board.json
  assets/primary.usdz
  assets/primary.model.json
Hangboards/metolius-wood-grips-compact-ii/
  board.json
  assets/primary.usdz
  assets/primary.model.json
```

An unrelated raster package instead retains:

```text
Hangboards/example-raster/
  board.json
  assets/primary.png
```

The parser enforces confined, exact declared assets; a model package cannot
carry an undeclared raster fallback. `descriptor.modelSHA256` must equal the
SHA-256 of the package USDZ bytes, inventory IDs must equal the board's logical hold IDs, and typed
media rules reject malformed, derived, or inverted model presentations. Sync
copies every declared typed asset. Staging copies the validated package
byte-for-byte; it does not substitute a separately bundled model.

## Stage 0: evidence preparation for geometry

Before Astra receives a geometry task, a lower-cost worker creates an owned
evidence packet under `.context/<workspace-owner>-<board-revision>/`. Luna owns
routine source gathering and audit reconciliation; Sol or Terra handle source
conflicts requiring deeper non-geometry reasoning. This stage does not author
geometry. It prepares the evidence Astra needs to make geometry decisions and
to distinguish sourced facts from its estimates.

The packet has a machine-readable `evidence-packet.json` and a corresponding
human-readable evidence brief. Its compact required content is:

```json
{
  "boardRevision": "beastmaker-1000",
  "boardRevisionDate": "2026-09-08",
  "locale": "en-GB",
  "primarySources": [{ "sourceTier": "manufacturer", "url": "https://manufacturer.example/product", "localPath": "references/product.html", "sha256": "..." }],
  "commerceSources": [{ "retailer": "Authorized Retailer", "url": "https://retailer.example/product", "snapshotSHA256": "..." }],
  "logicalInventory": [{ "holdID": "jug-left", "sourceBackedMetadata": { "kind": "jug" } }],
  "sourcedClaims": [{ "claim": "580 x 150 mm face", "citation": "primarySources[0]", "confidence": "high" }],
  "conflictsAndRulings": [{ "conflict": "5 mm versus 58 mm depth", "ruling": "use 58 mm shared-layout evidence", "confidence": "qualified" }],
  "unknownsForAstra": ["cavity sections", "radii", "back profile"],
  "deliberateOmissions": ["screw holes", "mounting hardware"],
  "materialFidelity": "generic original pale wood",
  "requiredReviewViews": ["front", "three-quarter", "clay-detail"]
}
```

The full packet records the exact board revision; authoritative primary URLs;
retained local reference paths and SHA-256 hashes; stable logical hold inventory
and source-backed metadata; sourced dimensions, material/product claims and
citations; conflicts, rulings and confidence; explicit unknowns Astra must
estimate; deliberate screw-hole/hardware omissions; approved material fidelity;
and required review views.

For each board, the packet must retain at least two exact-revision visual image
snapshots before Astra resumes: one complete manufacturer-published image and
one additional complete image from a materially different angle when available
(front plus oblique/side/back/profile preferred). Record each image's local
path, SHA-256, pixel dimensions, retrieval date/locale, exact view-angle label,
source tier, and page linkage, plus the geometric facts that angle can and
cannot support. Authorized retailer/distributor imagery is allowed only to fill
a documented manufacturer gap, must be labeled commerce-gap evidence, and
cannot override manufacturer claims. Crops, duplicates, search thumbnails,
reviews/forums, generated renders, and ambiguous-revision media do not satisfy
this gate. A diagram supplements the packet but is not a distinct-angle
photograph unless it genuinely exposes side/profile geometry.

Manufacturer product pages, manuals, dimension diagrams, and manufacturer media
are authoritative first-party sources. Prefer the current exact board revision
and record its revision, date, and locale. Authorized retailer/distributor
product listings are permitted commerce sources only to fill a first-party gap;
their identity, URL, and snapshot hash are recorded, and they cannot override a
conflicting manufacturer claim without an explicit evidence ruling. Independent
reviews, forums, search snippets, and AI summaries are discovery or
corroboration only, never sole authority for dimensions, inventory, material,
safety/training claims, or geometry facts. Search snippets are not sources: the
packet retains the actual page or media. When only secondary evidence exists,
the claim is marked qualified or unsupported rather than silently elevated.

It must not contain auto-detected, traced, vectorized, or aligned contours;
inferred masks; proposed coordinates, sections, or radii; or any geometry made
by lower-cost workers. Lower-cost workers may identify visibly distinct
features and report evidence-to-render mismatches. Astra alone turns evidence
into shape and fixes physical fidelity defects.

```text
Stage 0 lower-cost evidence packet + brief
  -> human-approved Astra geometry source and review renders
  -> lower-cost deterministic compiler/exporter
  -> package parser, native SceneKit validation, staging and sync
```

## Geometry authoring, compiler, and routing

Astra receives the Stage 0 packet and alone authors or refines physical geometry.
Its owned `.context` output
contains a tagged editable `.blend`, source-versus-estimate report, and
human-approved front/oblique/clay review renders. Geometry mesh objects are
tagged `role=body` or `role=hold`; every hold object carries its canonical
`hold_id`. Astra directly authors silhouette, curved jugs/slopers, and real
recess mouths, walls, and backs; it does not trace, vectorize, or extrude raster
paths. Geometry/fidelity defects return to Astra with visual evidence.

A deterministic lower-cost compiler/exporter consumes only approved source and
the current logical inventory. It transforms to `hang-ten-board-v1`, exports a
fixed package-owned USDZ, generates `assets/primary.model.json`, and never
repairs or redesigns shape. Schema, export, material, packaging, and integration
defects stay with lower-cost workers.

Luna handles routine bounded work. Sol or Terra handle involved non-geometry
work. Astra handles only physical geometry/refinement. Human visual approval is
always required; inventory validation is not fidelity approval.

## Runtime and Workbench data flow

`BoardHold` remains logical. For workout matching it exposes a resolved frame:
raster uses default path geometry; model uses descriptor-projected bounds.
Render and picking geometry remains presentation media and is never copied into
logical hold metadata.

```text
board.json + selected presentation
  -> typed package parser and exact asset/descriptor validation
  -> package-driven renderer cache(boardID, presentationID, modelSHA256)
  -> USDZ nodes matched by exact descriptor nodeID
  -> same hold meshes render, highlight, and nearest-hit pick
  -> descriptor projected bounds resolve logical matching geometry
```

There is one generic package-driven renderer: no board registry and no
board-specific Swift routing. Model cache keys include board ID, presentation
ID, and model SHA. Runtime does not decode USDZ merely to match a workout; it
uses the hash-bound descriptor. Invalid or missing model media displays generic
unavailable UI and never falls back to raster. Body nodes cannot be selected.

Workbench keeps raster presentations editable. It displays model presentations
read-only and explicitly reports that geometry editing is unavailable. It does
not recreate 2D paths from a model.

## Validation and failure handling

Validation is layered:

1. The pure package parser checks schema/tagged union, confinement, exact
   assets, logical inventory, descriptor hash and structure without decoding
   USD.
2. The deterministic compiler reimports its actual export and checks frame
   bounds, exact node names, materials, triangles, bindings, and review renders.
3. Native SceneKit CI/release tests decode the actual USDZ, verify materials and
   nodes, and fire nearest-hit rays for every logical hold.

Ordinary Xcode compilation does not require Blender. Any model failure at parse,
compile, decode, material, node, binding, or hit-test stage is a package defect;
runtime fails closed to the generic unavailable view. Descriptor staleness is
rejected by SHA mismatch. No fallback scene and no partially interactive model
is allowed.

## Migration sequence and component boundaries

0. Prepare and review the lower-cost evidence packet/brief before any Astra
   geometry task; require the retained multi-angle visual gate above and reject
   packets containing geometry proposals or image-derived contours.
1. Define parser/schema v2 and descriptor v1 with fixtures for raster and model
   packages.
2. Rebuild both named packages as model media, retaining logical IDs/metadata
   but removing their legacy PNG/path media and separate app resources.
3. Astra produces reviewed geometry; the compiler produces USDZ + descriptor;
   validators prove the generated package.
4. Route catalog, renderer, picker, matching, Workbench, staging, and sync
   through typed package media.
5. Run parser/compiler/SceneKit tests, then stage the validated package bytes.

Expected boundaries are: package schema/parser and `BoardHold` resolution;
model compiler/export verifier; package staging/sync; generic model renderer and
picking; Workbench mode handling; and parser/compiler/native SceneKit tests.
No standalone app resource, registry, or board-specific renderer belongs in the
target architecture.

After implementation validates this architecture, fold the reusable evidence
packet, model-first, compiler, and validation rules into the
`migrate-hangboard-to-3d` skill. The skill update follows demonstrated package
behavior; it is not a substitute for this implementation specification. This
closeout codification also distills the Stage 0 source hierarchy.

## Acceptance and non-goals

Acceptance requires both named migrated packages to validate as model-first,
their descriptors to hash-bind the staged USDZ, every logical hold to resolve
through exact nodes and native nearest-hit tests, and human approval of the
geometry review renders. Each Astra source must have begun from a complete
Stage 0 evidence packet/brief that contains no geometry proposal or automated
image geometry and records primary/commerce source provenance, conflicts, and
qualified or unsupported secondary-only claims. Unrelated raster boards must
continue to parse, render, and edit as raster packages.

Non-goals: manufacturing geometry, inferred physical measurements, model
editing in Workbench, derived/inverted model variants, migration of other
boards, and a generic decoration-node system. The work does not prescribe
training behavior or change logical hold identities.
