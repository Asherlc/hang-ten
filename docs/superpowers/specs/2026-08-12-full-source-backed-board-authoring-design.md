# Full source-backed board authoring design

## Decision

The 31 unregistered generated-image directories under `Hangboards/` will be
authored into complete, source-backed board packages. A board is added to
`Hangboards/catalog.json` only after every runtime field, semantic mapping,
and artwork element is traceable to manufacturer evidence and the existing
fail-closed package validator accepts it. Git branches are the sole
work-in-progress mechanism: packages and the app contain no lifecycle,
review, confidence, approximation, or onboarding state.

This is a content-authoring effort, not a photo-recognition effort. A missing
manufacturer fact is an evidence blocker, not permission to derive a hold
type, depth, finger capacity, or physical-hold boundary from an image.

## Canonical shape and delivery

Each completed board has one flat, slug-named package in `Hangboards/`:

```text
Hangboards/
  catalog.json
  manufacturer-model/
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/
      primary.png
      source-photo.jpg               optional, original source image only
```

`board.json`, `evidence.json`, `semantics.json`, and `artwork.json` are the
only JSON sidecars. Geometry belongs in `artwork.json`: its silhouette,
layers, and hold pieces are the authoritative normalized geometry. Do not add
`outline.json`, `outline.approx.json`, a `review/` directory, a board README,
or any other parallel representation. The removed approximate-outline files
cannot be renamed into factual data because they do not carry the evidence
coverage required by the package schema.

`assets/primary.png` is the one generated image retained for a board. It is a
presentation asset only and must be listed in `evidence.json.assetEvidence`.
No alternate generated PNGs, flat renderings, previews, or image variants are
kept in the package. An optional source photograph may remain as an unmodified
source asset (with its original filename and extension) when its licence and
repository policy allow it; it too has an `assetEvidence` entry. The source
photograph is evidence for visible shape and placement only. It is never the
sole evidence for a non-visible physical or training fact.

The catalog remains schema version 1, with one `{ "id", "path" }` entry per
complete package. It records neither a status nor review state. Entries are
unique by ID and path, point to a single direct child directory, and require
the package's `board.json.id` to match. Unregistered directories are not app
content and are never staged.

The iOS app remains a direct package consumer. The Xcode staging script copies
the catalog and registered package directories into the bundle, and
`BoardPackageStore` decodes the JSON and resolves `primary.png` directly from
those resources. There are no board-specific Swift definitions, generated
runtime catalogs, asset-catalog imagesets, or app-side transformations.

## Source-evidence contract for every board

Before authoring a package, collect and preserve HTTPS source URLs in
`evidence.json.sources`, with a real `checkedAt` date. For each board, the
minimum research set is:

1. An official manufacturer product page establishing the product identity,
   manufacturer, name, product URL, and published dimensions.
2. A straight-on official image establishing silhouette, overall layout, and
   visible hold placement.
3. An official oblique/side image where it is needed to distinguish the
   visible shape of shelves, jugs, slopers, or recesses.
4. An official numbered hold guide, depth diagram, manual, or manufacturer
   measurement that supports each hold's count, size/depth, finger capacity,
   and grip classification.

The word “official” means material published by the manufacturer or its
authorized documentation host. A retailer image, user photograph, third-party
review, generated image, previous app data, or current unregistered
`primary.png` may help locate a product or visually compare artwork, but may
not establish a factual hold field. If manufacturer documentation explicitly
does not provide a field, omit it only where the current schema permits
`null`; do not replace it with an estimate or a value copied from an
unsourced rendering.

The existing `evidence.json` schema is an exact audit map, not a bibliography.
It must contain nonempty HTTPS `sources` and exact coverage maps for:

- every factual field in `board.json` (`fieldEvidence`);
- every field of every physical hold (`holdEvidence`);
- every semantic mapping (`semanticEvidence`);
- the artwork silhouette, every artwork layer, and every hold piece
  (`artworkEvidence`); and
- every file below `assets/` (`assetEvidence`).

Each mapping names declared source IDs and, when it is an adaptation, one of
the validator's explicit methods: `manufacturer-measurement`,
`reviewed-human-authored-normalization`, or
`external-generative-adaptation`. The adaptation method explains how a source
was represented; it does not upgrade unsupported source material into a fact.
In particular, `external-generative-adaptation` is permitted for
`assets/primary.png` and cannot be cited as evidence for hold semantics,
measurements, finger capacity, or authoritative geometry.

## Authoring a board

For a board whose source set satisfies the contract:

1. Confirm the physical product and manufacturer URL; record facts only from
   the collected official sources. Create a stable identifier and flat slug
   before writing any package sidecar.
2. Author `board.json` with the current schema: product facts plus a nonempty
   set of physical holds. Give every hold an ID, name/label/detail, kind,
   normalized interaction frame, size/depth (or permitted `null`), grip type,
   finger capacity, cue style, and feature list only when that exact value is
   source-backed.
3. Author `artwork.json` against the official front/side imagery. Its hold IDs
   must exactly equal the physical hold IDs in `board.json`; every path, layer,
   and hold piece must have a matching artwork-evidence key. Drawn boundaries
   are a reviewed normalization of the cited visual evidence, not a recovered
   measurement.
4. Author `semantics.json` as the source-backed mapping from routine-facing
   semantic IDs to physical hold IDs. Each mapping must be nonempty, contain
   no duplicate hold IDs, and cite its own evidence. Do not create semantic
   names merely because a hold looks familiar.
5. Create `evidence.json` last enough to prove exact coverage, then inspect it
   as an audit table. Its board ID must equal all three sibling documents and
   every map key must correspond to the authored content.
6. Retain exactly one generated presentation asset at `assets/primary.png`.
   If a source photo is retained, keep only that original source-photo file as
   the additional asset; remove all alternate generated assets before
   validation. Set `board.json.presentation.assetPath` only when the app should
   present `primary.png`.
7. Add the catalog entry only after package validation passes. A package that
   is being researched, edited, or awaiting review stays unregistered on its
   Git branch rather than gaining a status flag or review folder.

## Evidence blockers and batching

Author the 31 boards in small batches organized by manufacturer documentation
availability, not by visual similarity. Each batch follows this fixed flow:

1. Inventory the candidate slugs and capture their official source URLs with
   the date checked.
2. Triage each candidate as **ready** only when all required hold facts and
   artwork references have manufacturer support. Record a concise source-gap
   note outside the package, in the batch's PR description or issue, for every
   blocked candidate.
3. Author and validate only the ready packages. Do not create partial JSON
   sidecars, placeholder holds, provisional catalog entries, or in-app state
   for blocked boards.
4. Submit the batch for factual review. On acceptance, commit its packages and
   catalog entries together; on rejection, keep corrections on the branch.

The expected inventory is these 31 current image-only directories:

```text
beastmaker-1000
beastmaker-2000
dewoodstok-woodbord
escape-beta
escape-unlimited
evolv-kilter-basic-long
frictitious-doormount-pro-7
frictitious-megalith
lattice-triple-rung
metolius-climbers-edge
metolius-contact
metolius-project
metolius-simulator-3d
moon-armstrong
nature-stoak-board-iii
soill-iron-palm-2
soill-split-palm
soill-training-tiles
target10a-linebreaker-base
tension-grindstone
tension-honestone
tension-whetstone
trango-rock-prodigy-forge
trango-rock-prodigy-natural
trango-rock-prodigy-pivot
yy-verticalboard-evo
yy-verticalboard-first
yy-verticalboard-light
yy-verticalboard-one
zlagboard-evo
zlagboard-pro
```

The list contains 31 slugs. Batches may span multiple pull requests. No batch
is required to complete all 31 before an individually complete board can be
registered and shipped, but every registered board must satisfy the same
contract.

## Verification and provenance

For each batch, run the package validator against the full catalog:

```sh
scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
scripts/hangboard-tools.sh catalog status --catalog Hangboards/catalog.json
```

Add focused validator tests for each newly enforced invariant or regression:
duplicate/unknown evidence keys, missing evidence for a retained asset,
nonmatching physical/artwork hold IDs, semantic references to unknown holds,
and unsafe or unregistered package paths. Extend the generated-catalog import
test so every remaining unregistered candidate has exactly
`assets/primary.png`, no README, no review directory, no alternate generated
image, and no catalog entry. Convert or retire that test case only when the
last candidate becomes a registered, complete package.

Run the package-store tests and a generic iOS Simulator build after each batch
to prove Xcode staged only catalog packages and that the app reads their JSON
and PNG resources directly. Inspect normal and active hold rendering in
portrait and landscape on the owned validation simulator before merging a
batch that changes artwork or presentation assets.

Commit provenance with the content: source URLs and date live in the package;
the PR describes the batch, exact boards accepted, and exact source gaps for
boards deliberately left unregistered. This preserves an auditable path from
every shipped field and pixel to its source without encoding temporary review
state in the app.

## Non-goals

- Inferring a complete board definition from an existing generated PNG or a
  source photo.
- Treating user/community photos or generated imagery as primary measurement
  evidence.
- Reintroducing `draft`, `approved`, `shipped`, `onboarding`, `review`, or
  confidence state into catalog entries, package paths, package documents, or
  app runtime.
- Reintroducing a second generated image, a parallel outline document, board
  README, app-side board generator, or board-specific Swift source.
