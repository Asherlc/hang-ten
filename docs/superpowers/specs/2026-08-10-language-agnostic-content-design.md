# Language-Agnostic Plan and Board Content Design

## Goal

Make Hang Ten's factual training content portable across programming languages by storing board metadata, hold metadata, and plan definitions in documented, versioned JSON while keeping SwiftUI-specific rendering code in Swift.

## Scope

This migration covers:

- board identity and manufacturer metadata;
- physical dimensions and normalized board aspect ratio;
- stable hold IDs and factual hold metadata;
- normalized fallback hold frames;
- semantic hold features used by plan resolution;
- versioned plan-library content and its board mappings;
- decoding, validation, migration, and regression tests.

This migration does not serialize `BoardDesign` rendering behavior. SwiftUI paths, gradients, shadows, palettes, highlight treatments, and interaction rendering remain platform-specific Swift code.

## Current State

`PlanLibrary.json` is already a schema-versioned runtime document. `PlanLibraryStore` decodes, validates, migrates schema version 2 documents, resolves board mappings, and exposes runtime `TrainingPlan` values. The remaining Swift plan seed definitions act as an export fixture and DEBUG drift oracle.

Board metadata is different: `BoardCatalog` constructs `TrainingBoard` and `BoardHold` values directly in `TrainingModels.swift`. Plan validation and resolution receive `BoardCatalog.all` by default. The visual layer separately maps board IDs to `BoardDesign` values and draws them with SwiftUI's `GraphicsContext`.

## Design

### Content boundaries

The content layer will be split into two independently versioned documents:

```text
Boards.json
  board metadata, holds, normalized fallback frames, semantic features

PlanLibrary.json
  plan metadata, reusable blocks, steps, targets, and plan ordering
```

Stable board and hold IDs are the only cross-document references. Plans continue to target semantic IDs where possible; board-specific resolution turns those semantic IDs into physical hold IDs at runtime.

The first migration keeps `BoardDesign` in Swift. `TrainingBoard` remains the runtime value type consumed by views and services, but its production values come from `BoardLibraryStore` rather than from hard-coded catalog literals.

### Board document shape

The canonical board document has this shape:

```json
{
  "schemaVersion": 1,
  "metadata": {
    "id": "hang-ten.boards",
    "version": "1.0.0",
    "title": "Hang Ten board catalog",
    "generatedAt": "2026-08-10",
    "notes": []
  },
  "boards": [
    {
      "id": "metolius.wood-grips-compact-ii",
      "manufacturer": "Metolius",
      "name": "Wood Grips Compact II",
      "subtitle": "A compact FSC-certified wood board for everyday strength work.",
      "dimensions": "24\" × 6.2\"",
      "aspectRatio": 3.88,
      "productURL": "https://example.com/product",
      "photoAssetName": "CompactBoardIllustration",
      "holds": [
        {
          "id": "edge-19-left",
          "name": "Left 19 mm edge",
          "shortLabel": "19E",
          "detail": "Small edge",
          "kind": "edge",
          "gripType": "openHand",
          "fingerCapacity": 4,
          "cueStyle": "slot",
          "frame": { "x": 0.035, "y": 0.620, "width": 0.160, "height": 0.245 },
          "sizeMillimeters": 19,
          "features": ["mediumEdge", "smallEdge"]
        }
      ],
      "semanticHolds": {
        "edge-19": { "holdIDs": ["edge-19-left", "edge-19-right"] }
      }
    }
  ]
}
```

The existing display-oriented `dimensions` string is preserved for compatibility. The schema does not infer physical values from display labels. If numeric dimensions are needed later, they can be added as new optional fields without changing the first migration.

`semanticHolds` is board-owned because it describes how a board fulfills the shared plan vocabulary. The plan document will remain able to read its current `boardMappings` field during migration; newly generated content will use the board-owned mappings and the loader will normalize them into the existing runtime resolution path.

### Plan document shape

The existing `PlanLibrary.json` structure remains the canonical plan shape:

- `schemaVersion` identifies the document schema;
- `metadata` identifies the library and default plan;
- `blocks` contains reusable workout steps;
- `plans` references blocks and contains plan metadata;
- `boardMappings` remains accepted for backward compatibility and is normalized against board-owned mappings when present.

The migration will not change the runtime `WorkoutStep`, `WorkoutSegment`, or target resolution semantics. JSON uses language-neutral strings for enum values, seconds for durations, explicit `null` for absent optionals, and arrays where ordering matters.

### Runtime loading

Introduce a `BoardLibraryStore` parallel to `PlanLibraryStore`:

1. Decode `Boards.json` into Codable definitions.
2. Validate schema version, required metadata, unique board IDs, unique hold IDs per board, finite normalized frames, valid aspect ratios, valid finger capacities, and valid references in semantic mappings.
3. Resolve definitions into `[TrainingBoard]`.
4. Make `PlanLibraryStore` and `CustomRoutineStore` receive the available boards explicitly.
5. Keep a narrow fallback for command-line/test environments that lack bundled resources, but make the fallback load the same checked-in JSON fixture rather than rebuilding production content from Swift literals.

`BoardDesignCatalog` continues to use board IDs to select SwiftUI artwork. A DEBUG assertion will continue to verify that every factual hold ID has corresponding rendered geometry for boards with bespoke designs.

### Error handling and compatibility

Board loading will use typed errors for decoding, unsupported schema versions, validation failures, missing boards, and duplicate IDs. Existing plan-library errors remain intact unless a shared board-loading error is required at the boundary.

The migration will preserve:

- the current Compact II board ID and every hold ID;
- the current normalized frames and metadata values;
- all current plan IDs, step ordering, timing, targets, and resolved hold IDs;
- the existing custom-routine persistence format;
- the `BoardCatalog` API temporarily as a compatibility facade for tests and runtime callers that are not yet dependency-injected.

After all callers use the store, the facade may be reduced or removed in a later cleanup. That cleanup is not required for this migration.

### Validation and tests

Tests will establish a red-green migration boundary before production changes:

- decode the checked-in board document and assert the Compact II board and hold inventory;
- round-trip board definitions through `JSONEncoder` and `JSONDecoder`;
- reject duplicate board IDs, duplicate hold IDs, invalid frames, invalid aspect ratios, invalid finger capacities, and unknown semantic hold IDs;
- resolve the existing plan library using JSON-loaded boards;
- compare resolved plan IDs, step IDs, step numbers, timing, targets, and board hold IDs with the pre-migration behavior;
- verify that the existing bespoke `BoardDesign` still covers every loaded Compact II hold ID;
- verify custom routines against explicitly supplied JSON-loaded boards;
- run the export/check command so checked-in plan JSON remains deterministic.

The test suite will continue to use small in-memory board definitions for unit tests that exercise isolated runtime behavior. Those fixtures will conform to the same Codable schema and will not depend on the production catalog singleton.

## Alternatives Considered

### JSON metadata only — selected

Move factual content to JSON while leaving rendering code in Swift. This delivers language portability for plans and board data without coupling the content schema to SwiftUI or inventing a cross-platform path language.

### Serialize visual paths as JSON

This would make board artwork more portable, but it would require defining and versioning a geometry command language, palette semantics, shading behavior, and interaction rules. It adds substantial scope without being necessary for content portability.

### One combined plans-and-boards document

This simplifies one-time distribution but makes independent board and plan updates less useful, increases document size, and couples otherwise reusable catalogs. Separate documents provide cleaner ownership and stable cross-document IDs.

## Non-Goals

- Replacing SwiftUI rendering with a cross-platform renderer.
- Changing workout behavior, timing, plan selection, or custom-routine UX.
- Adding a remote content service or network updates.
- Changing the existing plan schema beyond the board-mapping normalization needed for board-owned semantics.
- Automatically generating factual hold metadata from images or model output.

## Acceptance Criteria

The migration is complete when:

1. The shipped Compact II board metadata and holds are loaded from checked-in JSON.
2. The shipped plans resolve to the same runtime plans and physical hold IDs as before.
3. Plan and board JSON can be decoded by an implementation that does not use Swift-specific serialization features.
4. Invalid content fails validation with actionable paths and messages.
5. Existing SwiftUI board artwork and hold highlighting remain unchanged.
6. Unit tests and the full iOS build pass.
