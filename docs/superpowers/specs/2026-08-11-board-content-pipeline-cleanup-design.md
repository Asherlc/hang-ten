# Board content pipeline cleanup design

## Status

Approved, with the single-source amendment accepted on 2026-08-11. This
document supersedes the earlier decision to keep board-specific presentation,
semantic mappings, and vector artwork in `HangTen/`. The first two cleanup
tasks (evidence sidecars and tool-root consolidation) remain valid completed
foundations; downstream work must implement the stronger architecture below.

## Problem

The repository currently mixes three concerns:

- source-audited board packages under `Hangboards/`;
- checked-in application delivery artifacts and handwritten board definitions
  under `HangTen/`;
- historical image-generation experiments, approximate geometry derivation,
  and their tooling under `docs/hangboard-generative-catalog/` and the board
  tools.

The first cleanup design made `board.json` canonical only for physical facts.
That leaves several editable second sources of truth:

- app-only fields and semantic mappings are preserved from
  `HangTen/Resources/BoardLibrary.json` by `scripts/export-board-library.py`;
- Compact II subtitle and asset-name overrides live in
  `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`;
- Compact II and Rock Prodigy geometry live in
  `HangTen/Views/MetoliusCompactIIDesign.swift` and
  `HangTen/Views/RockProdigyTrainingCenterDesign.swift`;
- Rock Prodigy physical metadata is handwritten in
  `HangTen/Models/TrainingModels.swift` instead of a board package;
- built-in semantic mappings are repeated in `HangTen/Models/PlanStorage.swift`
  and exported into `HangTen/Resources/PlanLibrary.json`.

That split makes drift possible even when the existing export checks pass,
because some exporters read the old output to recover fields that are absent
from `Hangboards/`.

The experimental tools also do not programmatically create an accurate
hangboard from manufacturer evidence. The original catalog images and
incomplete AI-v2 set were created generatively. The flat renderer merely
simplifies existing images and approximate outlines, and experimental recess
detection recognizes only visible dark candidates. Neither may be represented
as a board-generation or authoritative hold-discovery workflow.

## Canonical architecture

Every board shipped by Hang Ten must be registered in `Hangboards/catalog.json`
and must have exactly one editable package under `Hangboards/<board-slug>/`.
The package owns every board-specific fact or representation. `HangTen/`
contains generated board artifacts and generic consumers only.

```text
Hangboards/
  catalog.json                         global registry and library metadata
  metolius-wood-grips-compact-ii/
    board.json                         identity, lifecycle, presentation, holds
    evidence.json                      sources and fact/artwork audit mappings
    semantics.json                     semantic target -> physical hold IDs
    artwork.json                       reviewed normalized vector geometry
    assets/                            optional board-owned source media
  trango-rock-prodigy-training-center/
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/                            optional; omit when unused

HangTen/
  Models/
    GeneratedBoardCatalog.swift        generated TrainingBoard definitions
    GeneratedBoardSemantics.swift      generated semantic mappings for export
  Resources/
    BoardLibrary.json                  generated runtime board library
    PlanLibrary.json                   generated plan artifact using semantics
    Assets.xcassets/                   generated board asset imagesets only
  Views/
    BoardDesignLanguage.swift          generic renderer and geometry types
    GeneratedBoardDesignCatalog.swift  generated BoardDesign definitions/index

Tools/
  HangboardPipeline/                   schema validation, promotion, generation
  HangboardWorkbench/                  human review/editor UI and packaging

scripts/                               thin validate/generate/check entry points
docs/
  ADDING_A_BOARD.md                    supported source-backed workflow
  history/tooling/                     retired experiment rationale
```

`Hangboards/catalog.json` advances to schema version 2 and contains global
library metadata plus package paths, not duplicated board IDs or lifecycle
values. Its shape is:

```json
{
  "schemaVersion": 2,
  "metadata": {
    "id": "hangten.board-library",
    "title": "Hang Ten Board Library",
    "version": "1.0.0",
    "defaultBoardID": "metolius.wood-grips-compact-ii",
    "generatedAt": "2026-08-10",
    "notes": []
  },
  "packages": [
    "metolius-wood-grips-compact-ii",
    "trango-rock-prodigy-training-center"
  ]
}
```

Package paths are unique, relative directory names with no traversal. The
validator obtains the board ID and lifecycle only from each package's
`board.json`. `defaultBoardID` must resolve to exactly one registered package.

### `board.json`: physical and presentation definition

`board.json` advances to schema version 2. It retains the existing source-
audited identity, physical dimensions, lifecycle, and hold fields, and absorbs
the board-owned presentation fields that currently live in generated output or
Python overrides:

```json
{
  "schemaVersion": 2,
  "id": "metolius.wood-grips-compact-ii",
  "manufacturer": "Metolius",
  "name": "Wood Grips Compact II",
  "subtitle": "A compact FSC-certified wood board for everyday strength work.",
  "productURL": "https://example.invalid/product",
  "dimensions": "24\" × 6.2\"",
  "aspectRatio": 3.88,
  "lifecycle": "shipped",
  "presentation": {
    "generatedSymbol": "compactII",
    "photoAsset": {
      "name": "CompactBoardIllustration",
      "path": "assets/CompactBoardIllustration.png"
    }
  },
  "holds": []
}
```

The example URL is schematic only; production content retains its audited
manufacturer URL. `generatedSymbol` is a stable delivery identifier and must
be a unique valid Swift lower-camel identifier. `photoAsset` is optional. When
present, its relative path must resolve inside the package, its file must be
regular and non-symlinked, and its provenance must be mapped in
`evidence.json`. Per-hold `cueStyle`, depth range, size, grip type, finger
capacity, features, normalized interaction frame, and review `regionId` all
belong here when supported. The generator must not infer or preserve any of
these fields from an existing runtime artifact.

### `evidence.json`: truth and adaptation audit

The already implemented schema-version-1 evidence sidecar remains a valid
foundation. The single-source migration advances it to schema version 2 by
retaining `boardID`, `checkedAt`, `sources`, and exact `holdEvidence`, then
adding exact coverage maps:

```json
{
  "schemaVersion": 2,
  "boardID": "metolius.wood-grips-compact-ii",
  "checkedAt": "2026-08-01",
  "sources": [],
  "fieldEvidence": {
    "manufacturer": ["product-page"],
    "dimensions": ["product-page"]
  },
  "holdEvidence": {},
  "artworkEvidence": {
    "silhouette": {
      "sourceIDs": ["product-page"],
      "method": "reviewed-human-authored-normalization"
    },
    "layers.top-plane": {
      "sourceIDs": ["product-page"],
      "method": "reviewed-human-authored-normalization"
    },
    "holdPieces.jug-left-top-cap": {
      "sourceIDs": ["product-page"],
      "method": "reviewed-human-authored-normalization"
    }
  },
  "assetEvidence": {
    "assets/CompactBoardIllustration.png": {
      "sourceIDs": ["product-page"],
      "method": "external-generative-adaptation"
    }
  }
}
```

Every factual board field and physical hold ID must map to one or more declared
sources. `artworkEvidence` keys must equal the artwork silhouette plus the exact
layer and hold-piece IDs. `assetEvidence` keys must equal optional package asset
paths. Each mapping records both source IDs and a method selected from an
explicit allow-list such as `manufacturer-measurement`,
`reviewed-human-authored-normalization`, or
`external-generative-adaptation`. A generative illustration may be retained as
a labeled presentation asset, but it is never evidence for hold facts or
authoritative geometry. Unsupported claims, geometry, assets, or mappings are
omitted rather than invented.

### `semantics.json`: board vocabulary

Semantic mappings move out of `BoardLibrary.json`, `PlanStorage.swift`, and
promotion overrides into this schema-version-1 sidecar:

```json
{
  "schemaVersion": 1,
  "boardID": "metolius.wood-grips-compact-ii",
  "semanticHolds": {
    "outer-jugs": {"holdIDs": ["jug-left", "jug-right"]}
  }
}
```

Semantic IDs and physical hold IDs are unique identifier-shaped strings. Every
mapping is non-empty, contains unique hold IDs, and refers only to holds in the
sibling `board.json`. A semantic ID may intentionally select the same physical
hold as another semantic ID. Plan-specific vocabulary may refer to these IDs,
but it must not redefine their physical mapping. `evidence.json` also contains
`semanticEvidence`, keyed exactly like `semantics.json`, so every mapping is
traceable to declared sources and an explicit audit method.

### `artwork.json`: reviewed normalized vector geometry

`artwork.json` is a declarative serialization of the existing generic
`BoardDesign` vocabulary, not a photo-to-vector output. It has this exact
top-level shape:

```json
{
  "schemaVersion": 1,
  "boardID": "metolius.wood-grips-compact-ii",
  "canvasFrame": {"x": 0.025, "y": 0.005, "width": 0.95, "height": 0.965},
  "palette": "sculptedWood",
  "silhouette": {"type": "path", "commands": []},
  "layers": [],
  "holdPieces": []
}
```

Frames and all path points are finite normalized values. A shape is either
`{"type":"roundedRect","cornerRadiusFraction":number}` or
`{"type":"path","commands":[...]}`. Path commands are discriminated objects:
`move`/`line` contain `to: [x,y]`, `quad` contains `to` and `control`, `curve`
contains `to`, `control1`, and `control2`, and `close` has no points. A layer
has a unique `id`, `frame`, `shape`, and one of the generic renderer's supported
roles. A hold piece has a unique `id`, a sibling `board.json` `holdID`, `frame`,
`shape`, and one treatment: `surface`; `shelf` with `rimInsetFraction`; or
`recess` with `rimInsetFraction` and `depth` (`deep` or `shallow`).

Canonical JSON stores the fully expanded final geometry. Convenience concepts
such as `addPair` or horizontal mirroring may be editor operations, but the
saved package may not depend on code execution to determine its final paths.
Every physical hold has at least one hold piece, and every hold piece resolves
to a physical hold. The validator compares the union of both sets exactly.

## Generator and validator responsibilities

The retained pipeline is the only writer of app board artifacts. A single
`generate` operation validates the complete registry and every package before
rendering any output. It then atomically writes, or checks byte-for-byte, this
closed output set:

1. `HangTen/Resources/BoardLibrary.json` from catalog metadata plus each
   package's `board.json` and `semantics.json`.
2. `HangTen/Models/GeneratedBoardCatalog.swift` from each `board.json`,
   including stable accessors defined by `presentation.generatedSymbol`.
3. `HangTen/Models/GeneratedBoardSemantics.swift` from each `semantics.json`,
   used by the built-in plan exporter instead of handwritten dictionaries.
4. `HangTen/Views/GeneratedBoardDesignCatalog.swift` from each `artwork.json`,
   containing the board-ID lookup and declarative `BoardDesign` values.
5. Board-owned imagesets under `HangTen/Resources/Assets.xcassets/` from
   optional package assets; stale generated imagesets are removed only from an
   explicit generator-owned manifest.
6. `HangTen/Resources/PlanLibrary.json` through the existing plan export,
   sourcing board mappings from generated semantics rather than Swift literals.

Generation is deterministic, transactional, and independent of its outputs:
it must never read `BoardLibrary.json`, generated Swift, `PlanLibrary.json`, or
asset-catalog contents to fill missing canonical fields. `--check` renders into
a temporary directory and reports missing, stale, and unexpected owned outputs
without modifying the tree. A checked-in generated-file header identifies its
canonical input and says not to edit it manually.

Validation fails closed for malformed schemas, unknown fields, duplicate IDs,
catalog/package mismatch, bad references, non-finite or out-of-range geometry,
unmapped evidence, unsupported renderer enum values, missing artwork for a
shipped board, missing semantic hold targets, asset path escapes, or generated
symbol collisions. Draft packages may omit incomplete content only when the
schema explicitly permits it; `approved` and `shipped` packages require the
complete four-file contract.

The Workbench remains supported as a human editor and reviewer. It opens and
saves the canonical package files, displays evidence alongside semantic and
geometry edits, and invokes the same validator/generator. It does not become a
second persistence format and does not claim to infer faithful geometry from a
product photograph.

## Application boundary

`BoardDesignLanguage.swift` remains application code because it defines generic
rendering behavior, palette tokens, highlighting, and geometry primitives. It
must not contain board IDs, hold IDs, board dimensions, or board-specific path
coordinates. `BoardMapView` may call the generated design lookup.

After migration, these handwritten definitions are removed:

- `BoardCatalog.rockProdigyTrainingCenter` and all physical holds in
  `TrainingModels.swift`;
- the Python `_SWIFT_BOARD_OVERRIDES` table;
- `MetoliusCompactIIDesign.swift` and
  `RockProdigyTrainingCenterDesign.swift`;
- built-in semantic hold dictionaries in `PlanStorage.swift`;
- exporter behavior that preserves board fields from current generated JSON.

Small handwritten convenience aliases may reference generated values, but may
not repeat a board ID, hold ID, mapping, presentation field, or coordinate.

## Retired workflow

Retire the non-runtime generative-catalog workflow as one unit:

- `docs/hangboard-generative-catalog/`, including generated source images,
  AI-v2 variants, flat variants, outline JSON, and contact sheets;
- catalog-outline and flat-preview command-line entry points, implementations,
  tests, and catalog-specific documentation;
- the experimental recess-detection/photo-to-SVG path and related language
  implying generic automatic board conversion;
- active documentation that instructs operators to use these mechanisms.

Historical plans and specifications explaining this retired work move to
`docs/history/tooling/`. Git history remains the record for retired generated
binary assets. Any presentation asset intentionally retained by a live board
package is copied into that package with explicit provenance before the old
catalog is deleted.

## Migration rules

- Preserve the completed evidence-sidecar and supported-tool relocation work;
  evolve it rather than reverting it.
- Migrate Compact II from all current sources into its four-file package
  without changing reviewed content.
- The existing runtime inventory is exactly Compact II and the handwritten
  `BoardCatalog.rockProdigyTrainingCenter`. Create a Rock Prodigy package before
  deleting the latter. Its allowed evidence is limited to the sources recorded
  in `docs/TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md`: the Trango product page
  (`https://trango.com/products/rock-prodigy-training-center`), manufacturer
  manual (`https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155`),
  depth guide (`https://www.mountainexperience.it/risorse/Rock_Prodigy_Training_Center_Depth_Guide.pdf`),
  and product image (`https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750&width=1946`).
  If those sources cannot support any existing field, semantic mapping, or
  geometry mapping, exclude Rock Prodigy from this migration and retain its
  current implementation until a separately reviewed evidence-backed package
  is approved; never invent missing evidence to satisfy this cleanup.
- Compare generated artifacts and rendered designs against the pre-migration
  runtime to prove content preservation before removing handwritten sources.
- Use `git mv` for retained assets and historical documents when appropriate.
- Update CI, release, package, script, Xcode project, and documentation paths in
  the same task that changes their contract.
- Remove a tool only after its callers, tests, CI wiring, and documentation are
  removed or rewritten.

## Verification and acceptance criteria

The cleanup is complete when:

- `Hangboards/catalog.json` registers every board in `BoardCatalog.all`, and
  every approved/shipped package passes the four-file and evidence contract;
- changing any canonical metadata, semantic mapping, normalized geometry, or
  package asset makes the corresponding generated-artifact `--check` fail;
- deleting or editing only a generated artifact is repaired by regeneration
  and never changes canonical input;
- no handwritten Swift or Python table contains a second board definition;
- generated Compact II and Rock Prodigy model values, semantic mappings,
  interaction frames, and vector renderings match their pre-migration values;
- plan-library generation resolves semantic targets from generated board
  semantics;
- the iOS unit tests and application build pass with both current boards;
- the retained Workbench edits canonical package files and its release workflow
  resolves the supported tool paths;
- no runtime, CI, release, or supported-document path references the retired
  catalog, flat renderer, outline generator, or experimental detector;
- active documentation describes evidence-backed, human-reviewed board
  creation without claims of programmatic faithful image generation;
- retired rationale is available only under `docs/history/tooling/`.

## Non-goals

- Recreating the retired image catalog in a new directory.
- Automatically generating, detecting, or tracing new board artwork.
- Inventing evidence, physical facts, semantic mappings, or normalized geometry
  to make a package appear complete.
- Changing routine tasks, counts, durations, grip prescriptions, or coaching
  copy during the board-source migration.
- Changing the generic Swift rendering style or replacing the Workbench merely
  because its persistence contract is being corrected.
