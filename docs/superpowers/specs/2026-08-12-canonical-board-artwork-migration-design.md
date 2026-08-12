# Canonical Board Artwork Migration Design

## Status

Approved in conversation on 2026-08-12. This is the execution-level
artwork-and-assets companion to the approved Board Content Pipeline Cleanup
design. It narrows no requirements from that design.

## Goal

Make each shipped hangboard package the only editable owner of its visual
content, while retaining a faithful, screwless Compact II presentation image
that is visibly an adaptation rather than physical-source evidence.

## Scope

The migration covers every shipped runtime board: Metolius Wood Grips Compact
II and Trango Rock Prodigy Training Center. It includes package-owned source
media, presentation assets, normalized vector artwork, semantic mappings,
generation, validation, and removal of handwritten board-specific app assets
and artwork. It does not change physical hold metadata, routine content,
highlight behavior, or generic Swift rendering.

## Canonical package contract

Each package under `Hangboards/<board-slug>/` owns:

```text
board.json       identity, physical metadata, lifecycle, presentation metadata
evidence.json    source, field, semantic, artwork, and asset audit coverage
semantics.json   semantic target IDs mapped to physical hold IDs
artwork.json     normalized silhouette, layers, holds, shapes, and treatments
assets/          optional package-owned image files
```

`board.json` names optional package assets using paths relative to its package.
The validator rejects paths outside the package, symlinks, missing files, and
assets without exact `assetEvidence` coverage. Board-specific artifacts under
`HangTen/` are generated copies; they never supply defaults to a generator.

## Compact II screwless presentation asset

The Compact II package retains two distinct image roles:

- A manufacturer-source reference image, retained byte-for-byte and mapped to
  the existing official product-page evidence.
- `CompactBoardIllustration.png`, a board-owned presentation adaptation that
  removes the visible screw holes while preserving the board silhouette,
  proportions, material, hold boundaries, and all non-fastener details.

The presentation image is mapped in `evidence.json` with
`external-generative-adaptation`. It is not used to establish physical facts,
hold identity, semantic mappings, or vector geometry. Its generated Xcode
imageset is a direct deterministic copy from the canonical package asset.

## Runtime generation

The package generator must create, and its `--check` mode must verify:

- `GeneratedBoardCatalog.swift` and `BoardLibrary.json` from `board.json`;
- `GeneratedBoardSemantics.swift` and generated plan target material from
  `semantics.json`;
- `GeneratedBoardDesignCatalog.swift` from `artwork.json`;
- board imagesets from the corresponding package assets.

`BoardDesignLanguage.swift` remains a generic, board-ID-free renderer. The
generated design catalog preserves the existing normalized geometry and the
existing hold-ID equality invariant.

## Migration and retirement rules

Existing Compact II and Rock Prodigy runtime behavior must replay exactly
apart from removing screws from the Compact II presentation-only PNG. Existing
source evidence remains the only evidence permitted for each board. The
retired generative catalog remains neither a source nor a fallback. Preserve
source history when retaining assets or files with `git mv` whenever that is
possible; generated app copies may be recreated from package sources.

## Verification

The implementation must add tests for package schema validation, evidence
coverage, path confinement, artifact generation, and stale generated outputs.
It must run the relevant Python and Swift tests, generation `--check`, and
visual iOS validation for inactive and active board states in portrait and
landscape. The Compact II presentation image review must specifically confirm
that the screw holes are absent and that its outline and holds are unchanged.
