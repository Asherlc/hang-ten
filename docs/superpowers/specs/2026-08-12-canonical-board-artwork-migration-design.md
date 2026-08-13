# Canonical Board Package and Direct-Bundle Design

## Status

Approved in conversation on 2026-08-12. This supersedes the generated-runtime-
artifact direction in the Board Content Pipeline Cleanup design and its
implementation plan. It retains their evidence, package, and Workbench goals.

## Goal

Make `Hangboards/` the one editable board store, import the existing generated
catalog as clearly non-authoritative drafts, and bundle only approved packages
unchanged into the iOS application. The application loads its board JSON and
presentation PNGs directly from the app bundle; it does not require generated
Swift, generated board JSON, or generated Xcode image assets.

## Registry and lifecycle

`Hangboards/catalog.json` is the single registry for every board's package
path and lifecycle. It has exactly two statuses:

- `draft`: incomplete or imported review material. Draft content is never
  bundled into the application.
- `approved`: a complete evidence-backed package eligible for direct iOS
  bundling.

Status is never encoded in a folder name. All packages use the same flat
layout: `Hangboards/<board-slug>/`. There is no `draft.json` file and no
`onboarding` or `shipped` lifecycle value. Evidence/review progress is
represented by package content and Workbench workflow, not lifecycle state.

An illustrative registry entry is:

```json
{
  "id": "beastmaker-1000",
  "path": "beastmaker-1000",
  "status": "draft"
}
```

## Package contracts

An approved package contains all of the following:

```text
board.json       identity, physical metadata, presentation declaration, holds
evidence.json    source, field, semantic, artwork, and asset audit coverage
semantics.json   semantic target IDs mapped to physical hold IDs
artwork.json     normalized silhouette, layers, paths, and treatments
assets/          package-owned image files
```

Approved JSON and assets are authoritative, with no app-side defaults. A
presentation PNG may be a labeled adaptation, but it cannot establish physical
facts, hold identity, semantic mappings, or vector geometry.

A draft package has no package manifest: the registry provides identity, path,
and status, while the package contains its retained images and optional
approximate-outline review material. Its README labels each asset's original
catalog location and `unreviewed-generated-catalog` provenance. Draft images
and outlines are never treated as evidence, physical metadata, runtime
artwork, or hold truth.

## Catalog import

Import all existing primary catalog images, flat variants, AI-v2 variants, and
approximate outline JSON files into one flat draft package per catalog board.
Preserve each input byte-for-byte using `git mv` when possible. The 32 primary
images, their matching approximate outlines, and available visual variants are
review material, not product claims. The existing catalog-source URLs/hints may
be recorded only as unverified leads; they do not satisfy approved-package
evidence requirements.

## Direct iOS bundling and runtime

The Xcode project copies the exact approved package directories from
`Hangboards/` into a `Hangboards` resource directory in the app bundle during
the build. This is packaging, not content generation: no checked-in output is
created and no JSON/image bytes are transformed.

Generic Codable loaders read `catalog.json`, locate only approved entries, and
decode each approved package's `board.json`, `semantics.json`, and
`artwork.json` directly from `Bundle.main`. A generic SwiftUI renderer
interprets `artwork.json` at runtime. Presentation images load by their
package-relative paths rather than Xcode asset names. The app fails clearly in
DEBUG if an approved package is incomplete, malformed, or refers to a missing
resource; the build-time validator prevents this in normal development and CI.

The app never reads a draft package, and no application source contains a
second board inventory, semantic mapping, artwork coordinate, asset mapping,
or lifecycle override. `BoardLibrary.json`, generated board Swift catalogs,
generated board design catalogs, and generated board imagesets are removed.

## Compact II presentation asset

The Compact II approved package retains a byte-identical manufacturer reference
image plus a new `CompactBoardIllustration.png` presentation adaptation. The
adaptation removes only visible screw/mounting holes while preserving its
canvas, crop, background treatment, silhouette, board scale, wood color, hold
openings, and all non-fastener detail. It is mapped with
`external-generative-adaptation` and is visually reviewed before approval.

## Verification

Tests validate both lifecycle contracts: drafts may be incomplete but cannot
be bundled or decoded by the app; approved packages require every package file,
evidence coverage, and referenced asset. Tests also validate deterministic,
byte-preserving approved-resource staging, generic runtime decoding, and no
handwritten/generated board definitions in app code.

Verification includes a complete import inventory test, package validator,
build-resource test, iOS unit tests, and visual validation of approved board
normal/highlight states. The Compact II presentation review confirms all screw
holes are absent without altered hold boundaries or silhouette.
