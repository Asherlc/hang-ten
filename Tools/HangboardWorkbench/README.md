# Hangboard Workbench

Hangboard Workbench edits direct board packages through a human-operated,
schema-v3 raster editor. The packaged macOS app edits a chosen local checkout; hosted
deployments use authenticated GitHub storage. Model presentations are visible
for catalog review but are deliberately read-only.

## Contact-first boundary

`board.json.contacts[]` owns sourced physical facts: contact identity, name,
kind, equipment object, side and pairing, measured dimensions or depth,
capacities, grip types, and documented features. Workbench edits those facts in
the contact inspector and writes each change only to the matching contact.

A raster presentation owns its authored media geometry at
`presentations[].media.contactGeometry[contactID]`. Editor regions contain only
the contact/presentation/piece identity plus the canonical path, frame,
treatment, and optional human-selected shape constraint. They never duplicate
contact facts. Each piece has one closed, contiguous contour. The saved path is
the only rendering, highlighting, and
hit-testing geometry; Workbench does not infer a path or constraint from pixels.

Model presentations own a USDZ and hash-bound descriptor instead of raster
contact geometry. Workbench will not save, delete presentations from, or
otherwise edit a model package.

## Run and build

The checked-in `app.js` is generated from `src/` and required by both local and
hosted workflows:

```sh
cd Tools/HangboardWorkbench
npm ci
npm run build
npm run check:bundle
```

The repository does not require a running server for validation. To operate the
hosted editor, launch `server.py` with `--allow-remote`, GitHub OAuth credentials,
and a session secret. HTTPS termination is required. Each hosted save creates a
commit on the selected GitHub branch; branch creation and pull-request creation
are also authenticated as the signed-in GitHub user. The macOS app instead
writes an atomic local package change for normal Git review.

Save validates the complete package and is fail-closed. It validates the entire schema-v3 document, declared asset
inventory, decoded raster dimensions, and all contact geometry before replacing
the package. A stale GitHub revision returns a conflict, and interrupted or
invalid writes leave the previous package unchanged.

## Direct path editing

Freeform anchors, Bézier controls, segments, selection state, guides, and
transforms have editor-local identities that are never serialized. The
canonical `displayPath` is serialized back into the media-owned frame and path.

The outline picker supports Custom, Oval, Circle, Pill, Rounded rectangle, and
Rectangle. Choosing a regular constraint is an operator decision. It persists
only editing intent (`shape` and normalized `rotationDegrees`); it does not
replace or outrank the canonical path.

## Run the Apple Silicon macOS release

Download the workbench ZIP and checksum from a release, verify and extract it,
then open the app:

```sh
curl -LO https://github.com/Asherlc/hang-ten/releases/download/<release>/hangboard-workbench-macos-arm64.zip
curl -LO https://github.com/Asherlc/hang-ten/releases/download/<release>/hangboard-workbench-macos-arm64.sha256
shasum -a 256 -c hangboard-workbench-macos-arm64.sha256
unzip hangboard-workbench-macos-arm64.zip
open "Hangboard Workbench.app"
```

On first launch the native window asks you to **Choose Local Repository…**.
The app remembers the last valid checkout and uses the selected checkout on
later launches. Choose **Choose Another Local Repository…** from the app menu
to switch. Edits remain ordinary local Git changes for normal Git review.

Local users can continue to use the packaged app; hosted deployment uses the
same Workbench codebase in its opt-in `--allow-remote` mode.

## Catalog capture

The capture command launches its own short-lived loopback process and headless
Chrome session, captures each raster presentation, and terminates both children:

```sh
rtk python3 Tools/HangboardWorkbench/capture_catalog.py \
  --repository-root /absolute/path/to/hang-ten \
  --output-root /absolute/path/to/catalog-captures \
  --chrome-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --contact-id-labels
```

`--contact-id-labels` overlays the canonical contact ID at the union center of
that contact's rendered pieces. Labels exist only in the capture page and never
alter package data.

## Verification

```sh
(
  cd Tools/HangboardWorkbench
  npm ci
  npm test
  npm run build
  npm run check:bundle
  .venv/bin/python -m pytest -q
)
swift test --package-path Tools/HangboardWorkbench/macos
```
