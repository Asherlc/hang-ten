# Board content pipeline cleanup design

## Status

Approved for planning. This document defines the intended repository layout
and supported board-content workflow; it does not itself remove or relocate
files.

## Problem

The repository currently mixes three different concerns:

- canonical, source-audited board content under `Hangboards/`;
- the application runtime and its generated board-library artifacts;
- historical image-generation experiments, approximate geometry derivation,
  and their tooling under `docs/hangboard-generative-catalog/` and
  `Tools/HangboardOnboarding/`.

The experimental tools do not programmatically create an accurate hangboard
from manufacturer evidence. The original catalog images and incomplete AI-v2
set were created generatively. The flat renderer merely simplifies existing
images and approximate outlines, and experimental recess detection recognizes
only visible dark candidates. Neither may be represented as a board-generation
or authoritative hold-discovery workflow.

## Supported architecture

```text
Hangboards/                         canonical, versioned board content
  catalog.json                      board registry and lifecycle
  <board-id>/
    board.json                      audited physical board and hold metadata
    evidence.json                   source URLs, dates, and field/hold mappings

HangTen/
  Resources/                        runtime JSON and app image assets
  Models/                           runtime decoding and generated catalog bridge
  Views/                            SwiftUI and source-backed vector artwork

Tools/
  HangboardPipeline/                board validation, import review, and export
  HangboardWorkbench/               human review/editor UI, macOS wrapper, packaging

scripts/                            stable, thin entry points for supported operations

docs/
  ADDING_A_BOARD.md                 active, factual add-board guide
  ADDING_A_ROUTINE.md               active routine guide
  history/tooling/                  retired plans, specs, and experiment rationale
```

`Hangboards/` is the sole editable source of truth for physical-board
metadata. The runtime resources remain generated delivery artifacts, while
Swift vector artwork remains source-backed application code rather than an
output inferred from pixels.

## Retained board-content pipeline

The retained pipeline has a deliberately narrow purpose:

1. Validate canonical board manifests and their lifecycle registry.
2. Preserve source evidence and validate schema/ID/semantic consistency.
3. Export canonical metadata to the checked-in runtime board library and
   generated Swift catalog.
4. Verify generated artifacts and release readiness in CI.
5. Support human review of source-backed board data and artwork through the
   Workbench, if the Workbench remains useful after cleanup.

It does **not** claim to create a faithful board image, identify every hold
from a photograph, or turn approximate pixel regions into runtime interaction
geometry. New boards require manufacturer evidence and reviewed, deterministic
vector artwork.

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
`docs/history/tooling/`. They remain available as context but must not appear
in active navigation or supported-workflow documentation. Git history remains
the record for retired generated binary assets.

## Migration rules

- Move files with `git mv` wherever their history is worth preserving.
- Update all CI, release, dependency, package, script, and documentation paths
  in the same change that relocates a supported tool.
- Remove a tool only after its callers, tests, CI wiring, and user-facing
  documentation are removed or rewritten.
- Preserve the current `Hangboards/catalog.json` validation and app export
  contract throughout the migration.
- Do not move app runtime assets into `Hangboards/`; `Hangboards/` holds facts
  and evidence, while the app owns its shipping assets and vector renderer.
- Add `evidence.json` before migrating new board content. Do not fabricate
  evidence fields for existing content; derive them only from the already
  recorded Compact II primary sources.

## Verification and acceptance criteria

The cleanup is complete when:

- no runtime, CI, release, or supported-document path references the retired
  catalog, flat renderer, outline generator, or experimental detector;
- `Hangboards/catalog.json` validation and board-library export checks pass;
- the iOS application builds with its existing Compact II board;
- the retained Workbench release and CI workflows resolve only the new,
  supported tool paths;
- active documentation describes evidence-backed, human-reviewed board
  creation without claims of programmatic faithful image generation;
- retired rationale is available only under `docs/history/tooling/`.

## Non-goals

- Recreating the retired image catalog in a new directory.
- Automatically generating or tracing new board artwork.
- Changing Compact II hold facts, existing routine content, or runtime vector
  artwork as part of the structural cleanup.
- Deleting source evidence or altering the shipped board lifecycle.
