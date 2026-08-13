# Hangboard Vectorizer

`hangboard-vectorizer` converts a clean, front-facing commercial hangboard
photo into a uniform interactive SVG and a JSON geometry manifest. For a
known product, a reviewed template defines every usable grip and a packaged,
reviewed canonical product render supplies the visible board layer. The input
photo supplies board geometry and alignment diagnostics; the caller asserts
the product identity and verifies it in the preview. The photo is not restyled
into a run-specific illustration.

## Run the Apple Silicon macOS workbench release

Download both assets from a release directory, verify the ZIP, extract it, and
launch the native app:

```bash
curl -LO https://github.com/Asherlc/hang-ten/releases/download/<release>/hangboard-workbench-macos-arm64.zip
curl -LO https://github.com/Asherlc/hang-ten/releases/download/<release>/hangboard-workbench-macos-arm64.sha256
shasum -a 256 -c hangboard-workbench-macos-arm64.sha256
unzip hangboard-workbench-macos-arm64.zip
open "Hangboard Workbench.app"
```

On first launch, the native window asks you to choose the root folder of a
valid Hang Ten checkout. The app remembers the last valid checkout and opens
it on later launches. To work in another checkout, choose **Choose Hang Ten
Checkout…** from the app menu.

The editor appears only in the native window. All local saves write directly
to the selected checkout, where they remain ordinary changes for normal Git
review. If the selected folder is invalid or startup fails, the native window
explains the problem and offers **Choose Another Checkout…** so you can retry.

Remote hosting is not yet shipped; it remains a future deployment option.

The release is Developer ID signed and notarized, so it is accepted by
Gatekeeper without a Finder override.

For source development, use the Python workbench command documented below.

## Install

Python 3.11 or newer is required. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Convert an identifiable product

List the built-in commercial products:

```bash
hangboard-to-svg --list-products
```

Convert a local image or HTTP(S) image URL by supplying its product ID:

```bash
hangboard-to-svg photo.jpg \
  --product beastmaker-1000 \
  --output board.svg \
  --manifest board.json \
  --preview diagnostic.png
```

Generated paths are resolved beneath `.context/hangboard-onboarding` by
default. Set `--workspace-root` (or `HANGBOARD_WORKSPACE_ROOT`) to another
explicitly owned root; absolute paths and `..` components may not escape it.

`--product` is a caller assertion that the photo is the exact named model and
revision; the converter does not recognize commercial products automatically.
Alignment confidence measures how well the isolated board geometry aligns to
the asserted template, not whether that product assertion is correct. Review
the diagnostic preview to verify both identity and alignment.

The Beastmaker 1000 template exports a self-contained SVG with an exact,
packaged transparent PNG beneath 22 independently addressable vector paths:
17 pockets, 2 corner jugs, and 3 sloper surfaces. The center sloper is one
continuous double-width region (`sloper-center`) with no visual or semantic
divider. It emits no detected `opening` paths. The SVG and manifest contain
the same stable, ordered region IDs, and each manifest region has
`source: "template"` and a nullable `openingId`. The embedded PNG provides
the approved visible material and depth; the vector paths provide stable
semantic identity, hit testing, highlighting, and measurement.

The diagnostic preview overlays every template region on the canonically
aligned photograph. Inspect it whenever onboarding a new photo, especially for
cropping, occlusion, or the wrong product selection. Generated outputs are
published transactionally, so a conversion or validation failure does not
leave partial SVG or manifest files.

## Alignment confidence

The selected template's canonical aspect ratio controls the output canvas.
Alignment confidence is based on the photographed board's relative
aspect-ratio error:

- At or below 5%: `high` confidence and no alignment warning.
- Above 5% through 15%: `low` confidence with a warning in the manifest and
  diagnostic preview.
- Above 15%: conversion fails.

Use `--allow-low-confidence` with `--product` to explicitly allow an alignment
above the 15% limit. The manifest still records `confidence: "low"`, so callers
can reject or flag it downstream. This flag does not improve a poor alignment;
always review the preview.

## Highlight regions

Every enabled manifest region has the same ID as one SVG `.grip-region` path.
Adding the `active` class highlights only that logical grip:

```js
document.getElementById("pocket-top-left").classList.add("active");
```

Template-backed SVG paths also expose `data-source`, `data-type`, and, where
applicable, `data-side` and `data-label`. The built-in SVG style highlights a
region on hover at lower opacity and an active region at higher opacity.

Product-template coordinates and semantics come from a reviewed, versioned
JSON map, not from photo darkness. This is why non-dark slopers and jugs remain
independently identifiable. The manifest's `product` and `alignment` objects
record the selected template and alignment result. Measurements absent from
the template are omitted rather than inferred from pixels.

## Onboard another commercial product

The canonical package for each board lives under `Hangboards/`:

- `Hangboards/catalog.json` is the package registry.
- `Hangboards/<board-folder>/board.json` is that board’s current source of
  truth.
- Lifecycle values progress as `draft` → `onboarding` → `approved` →
  `shipped`.

Stage output is still written to temporary, ignored run folders first (for
example under `.context/hangboard-onboarding/...`). Registration only accepts
symlink-free `.context` runs, advances lifecycle when appropriate, and never
downgrades a shipped board. Register once a run is intended to be permanent:

```bash
scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
scripts/hangboard-tools.sh catalog status --catalog Hangboards/catalog.json
scripts/hangboard-tools.sh catalog register \
  --catalog Hangboards/catalog.json \
  --board metolius.wood-grips-compact-ii \
  --run .context/hangboard-onboarding/metolius-onboarding-run \
  --run-id metolius-onboarding-run
```

Start a persisted onboarding run from one local image or HTTP(S) source:

For the complete guided local workflow, start the server from the repository
root with its repository and transient-workspace defaults:

```bash
rtk python Tools/HangboardWorkbench/server.py
```

This discovers the checkout, reads complete registered board packages from
`Hangboards/<board-folder>/board.json`, and writes in-progress work
under `.context/hangboard-workbench/`. Automation can select different roots
explicitly:

```bash
rtk python Tools/HangboardWorkbench/server.py \
  --repository-root /absolute/path/to/checkout \
  --workspace-root /absolute/path/to/workbench-workspace
```

Open `http://localhost:4173`, then create a board from either an HTTP(S) image
URL or an image upload. The opening screen also lists valid repository boards;
select one to open its current committed package for editing. The exact
[package and publication contract is documented in the unified repository design](../../docs/superpowers/specs/2026-08-07-unified-hangboard-repository-design.md),
which supersedes the prior repository library design. When a complete revision
is saved, the workbench atomically replaces the canonical board package.
**Save locally** writes those files for normal Git review, but never commits or
pushes them.

CLI and other programmatic workflows are producers of the same contract: pass
a completed run to `RepositoryBoardLibrary.publish()`. The browser never asks
the user to provide a CLI run directory.

The workbench runs Stage 0 immediately, then stops at every checkpoint for
review. **Approve & continue** records the approval and advances to the next
checkpoint; **Retry** regenerates the current checkpoint as a new attempt while
preserving prior files.

Stage 2 is the contour and pixel-label review: add, delete, or correct the
stable region inventory against the registered raster. Stage 3 is the vector
review: refine each retained region's final display path. Valid Stage 2 and
Stage 3 edits autosave as immutable drafts and are materialized only when that
checkpoint is approved.

The workspace store persists `boards/board-NNNN/board.json`, evolving
CLI-compatible `revisions/revision-NNNN/run/` directories, and immutable
per-revision `drafts/stage-N/draft-NNNN.json` files. Published stage attempts,
artifacts, approval evidence, and failure diagnostics inside each run remain
immutable. **Revise upstream** forks a new
revision and marks replaced downstream lineage stale; stale or incomplete
lineage cannot be selected by the final Save. Refreshing or restarting the
server reloads the store, while the browser can also recover its newest
same-checkpoint local draft. Retrying a stage changes the checkpoint identity,
so drafts from an earlier attempt remain immutable but cannot be restored or
approved over the replacement.

## Single-board suite workflow

Use **Onboard** for Stage 0–4 review, **Inspect** to confirm the active revision
and accepted artifacts, and **Validate** for hold-ID, semantic, and plan-library
checks. Final **Save changes** selects the complete revision inside the local
Workbench workspace. It does not publish to `Tools/HangboardPipeline/boards`,
write generated Swift or JSON, or modify app resources.

Canonical publication is a separate fail-closed API operation. A caller submits
a reviewed candidate below repository `.context` to `POST /api/package-candidates`
with its board ID and `draft` or `approved` status. The Workbench copies only to
`Hangboards/<slug>`, updates `Hangboards/catalog.json`, and validates the whole
registry. Invalid candidates roll back both paths. No native source, Xcode asset,
or legacy board-library artifact participates in that transaction.

The Validate tool accepts only a caller-supplied UUID and formats review
commands for it. The browser does not create, delete, boot, erase, or archive
simulators. Create, record, boot, review, and clean up the dedicated simulator
outside the browser according to
[`docs/IOS_SIMULATOR_VALIDATION.md`](../../docs/IOS_SIMULATOR_VALIDATION.md);
never use `booted` or another workspace's device.

Every workbench revision is CLI-compatible. Inspect a UI-created run by using
the same explicit confinement root:

```bash
rtk hangboard-onboard \
  --workspace-root /absolute/path/to/workbench-workspace \
  --output /absolute/path/to/workbench-workspace/boards/board-0001/revisions/revision-0001/run \
  --status
```

CLI-compatible runs remain review inputs. A source-backed package candidate is
assembled below `.context` and goes through the canonical package validator
before it can be registered. The browser never asks for a CLI run directory,
and unfinished runs remain under the ignored `.context/` directory.

The lower-level CLI remains useful for scripted operation. Start a persisted
run from one local image or HTTP(S) source:

```bash
hangboard-onboard --product-name "Metolius Wood Grips Compact II" \
  --source photo.jpg \
  --output .context/hangboard-onboarding/metolius-onboarding
```

Approve the displayed Stage 0 review, then resume the run:

```bash
hangboard-onboard \
  --output .context/hangboard-onboarding/metolius-onboarding \
  --approve stage-0
hangboard-onboard \
  --output .context/hangboard-onboarding/metolius-onboarding \
  --resume
```

Validate and inspect the current state without changing it:

```bash
hangboard-onboard \
  --output .context/hangboard-onboarding/metolius-onboarding \
  --status
```

Replay the accepted Metolius compact semantic cache and write an offline parity
report with zero live model calls:

```bash
hangboard-semantic-benchmark \
  --accepted-run Tools/HangboardPipeline/boards/metolius-wood-grips-compact-ii \
  --output .context/hangboard-onboarding/metolius-parity/report.json
```

The command reports model activity separately from deterministic local work.
See [docs/token-efficient-onboarding.md](docs/token-efficient-onboarding.md)
for the cache identity, escalation rules, and measurement limits.

The shared runner records the caller-asserted product name, preserves the exact
cached source bytes, and publishes every generated checkpoint as hash-bound,
immutable review evidence. CLI and UI operations use the same manifests,
approval state machine, stage runners, and revision directories.

Known products are intentionally curated rather than automatically recognized.
To add one, use an authoritative, clean product photo to create and review a
product template: canonical canvas, silhouette, every selectable grip path,
and its metadata. Produce one reviewed transparent canonical render at that
same canvas size, package it beside the product JSON, and name it with the
template's `renderAsset`. Verify that the SVG embeds those exact bytes and
that its ordered vector region IDs match the manifest. Once approved, every
conversion of that exact model/revision has the same visible product render
and the same selectable regions; a supplied photo supplies alignment evidence,
while the operator verifies the asserted identity in the preview.

The deterministic height-field renderer remains available as a standalone
library operation for profile-based product development. It is not selected
automatically by SVG conversion: a product without a packaged `renderAsset`
uses the existing curated-vector SVG branch, while unknown products can use
the explicitly selected experimental-detection path.

## Evidence-preserving Stage 4 illustration

The onboarding replay can bind an accepted Stage 1 RGBA PNG to accepted Stage
3 paths without consulting a product template or redrawing the board. Stage 4
embeds the supplied PNG byte-for-byte in one selectable SVG, preserves the
ordered region paths in a compact manifest, and derives deterministic normal
and grip-highlight previews from those paths. Publication validates the full
Stage 1 → Stage 2 → Stage 3 hash chain, finalizes candidate hashes before any
manual comparison evidence is read, and writes an acceptance record with a
six-panel review image.

## Override regions

Pass `--overrides overrides.json` to rename, disable, split, merge, or add
regions after template mapping or experimental detection. The version 1 schema
is:

```json
{
  "version": 1,
  "rename": {"pocket-top-left": "warmup-pocket"},
  "disable": ["pocket-top-right"],
  "split": {
    "pocket-middle-center": [
      {"id": "center-left", "xRange": [0.0, 0.5]},
      {"id": "center-right", "xRange": [0.5, 1.0]}
    ]
  },
  "merge": [
    {"ids": ["pocket-top-left", "pocket-top-right"], "id": "top-pair"}
  ],
  "add": [
    {
      "id": "manual-edge",
      "type": "unknown",
      "polygon": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]]
    }
  ]
}
```

Coordinates and `xRange` values are normalized to `0..1`. IDs must begin with
a letter and contain only letters, digits, `_`, or `-`. A source region can be
targeted by only one operation in a document, and all final IDs must be unique.
Reviewed asset-backed products can additionally require their canonical IDs,
order, and grip topology. The Beastmaker 1000 does: any override that renames,
disables, splits, merges, or adds an enabled region is rejected rather than
silently replacing its reviewed highlight geometry with a coarse polygon.

## Experimental recess detection

For an unknown board without a reviewed template, explicitly opt into the
legacy image detector:

```bash
hangboard-to-svg photo.jpg \
  --experimental-recess-detection \
  --output board.svg \
  --manifest board.json \
  --preview diagnostic.png
```

This mode finds visible dark recess candidates only. It cannot find non-dark
slopers, infer whether a surface is a pocket, edge, rail, jug, or sloper, or
guarantee stable IDs across reframing and threshold changes. Engraving, wood
grain, perimeter edges, and shadows may become false positives. It is not a
substitute for a reviewed product template when every usable grip matters.

Only experimental mode uses the detector thresholds. Tune them as follows:

```bash
hangboard-to-svg photo.jpg --experimental-recess-detection \
  --output board.svg --manifest board.json \
  --background-tolerance 24 --contrast-threshold 20 \
  --min-area-ratio 0.001 --rail-aspect-ratio 3.5 \
  --rail-width-ratio 0.20 --row-tolerance-ratio 0.05 --width 1200
```

`--width` and the rail aspect ratio must be positive. Background and contrast
thresholds must be between 0 and 255. Area, rail-width, and row-tolerance
ratios must be between 0 and 1. The semantic and experimental modes are
mutually exclusive; conversion fails if neither mode is selected.

## Input limitations

Use a clean product-style photo containing one fully visible hangboard against
a mostly uniform background, with limited occlusion and glare. Accuracy
depends on selecting the exact commercial model and revision. Unknown
products, severe perspective, cropped boundaries, hands on the board, or a
product revision with changed geometry require a new template or a better
source image. Automatic product recognition is not provided.
