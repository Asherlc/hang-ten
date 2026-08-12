# Hold Editor

A dependency-free local browser editor for hangboard hold-highlight artifacts.

## Run the Apple Silicon macOS release

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

For source development, use the Python command below instead.

## Run the guided local workbench

From the repository root, launch the repository-backed workbench with its
defaults:

```bash
rtk python3 Tools/hold-highlight-editor/server.py
```

The server discovers the checkout, reads saved boards from
`Tools/HangboardOnboarding/boards/`, and keeps in-progress work in
`.context/hangboard-workbench/`. Tests and automation can override those roots:

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --repository-root /absolute/path/to/checkout \
  --workspace-root /absolute/path/to/workbench-workspace
```

Open `http://localhost:4173`. Choose a board, edit its hold highlights, add or
delete highlights, choose each hold type, and save the review. For a new board, enter the exact
commercial product name, choose an HTTP(S) image URL or local image upload, and select **Create board**. The
image bytes, run manifests, approvals, drafts, and revisions stay under the
workspace root. The opening screen separately lists validated **Boards in this
repository**; selecting one opens its current committed version. The exact
[package and publication contract is in the unified repository design](../../docs/superpowers/specs/2026-08-07-unified-hangboard-repository-design.md).
The browser never asks for a CLI run directory.

## Run the single-board tool suite

The persistent sidebar works on one active board revision at a time:

- **Onboard** retains the guided Stage 0–4 review workflow described below.
- **Inspect** shows the active revision, approval/readiness state, Stage 4
  normal and highlight artifacts, hold inventory, and editable **Board info**
  for the current active revision. Board info stays in the active in-browser
  profile until the board or revision changes.
- **Promote to iOS** uses the Board info entered in Inspect and the active
  board's canonical repository ID. Generate a preview first and review its
  grouped **Metadata**, **Geometry**, and **Plans** diffs. A stale revision,
  changed Board info, incomplete package,
  or target changed relative to `main` is a conflict: no promotion file is
  written. **Save locally** regenerates and verifies the preview token, then
  writes all approved native targets atomically for normal local Git review.
- **Validate** runs the local package, hold-ID parity,
  semantic-routine-resolution, and plan-library checks.
  Its simulator field produces copyable commands only after the operator
  supplies the UUID of a dedicated simulator that has already been created,
  recorded, and made ready.

The browser never creates, deletes, boots, erases, or archives a simulator.
It never commits, pushes, or synchronizes remotely. Simulator creation,
ownership, readiness, review, and cleanup stay with the caller under
[`docs/IOS_SIMULATOR_VALIDATION.md`](../../docs/IOS_SIMULATOR_VALIDATION.md);
do not use `booted` or a device owned by another workspace.

Creation publishes Stage 0 and stops for review. **Approve & continue** binds
the displayed checkpoint to its hashes, runs the next installed stage, and
stops at the next review automatically. **Retry** publishes a new immutable
attempt for the current stage without overwriting its earlier evidence.

Stage 2 edits the pixel-aligned hold-highlight inventory that produces the label map.
Stage 3 edits the vector display paths that become the final interactive grip
geometry. Both editors autosave validated drafts bound to the active checkpoint
attempt; approval materializes only the newest draft for that exact attempt.
Undo/redo history is browser-local, and an unsaved same-browser recovery draft
can be restored after refresh only while its checkpoint identity still matches.
Accepted jobs are persisted independently and reconciled after refresh, so
work on separate boards cannot overwrite another tab's recovery record.
Published attempts and approvals remain immutable on disk.

**Revise upstream** creates a new revision at the preceding approved stage and
marks superseded downstream lineage stale. A typical local layout is:

```text
workbench-workspace/
  boards/
    board-0001/
      board.json
      revisions/
        revision-0001/
          run/
          drafts/stage-2/draft-0001.json
          drafts/stage-3/draft-0001.json
```

Each revision `run/` is a CLI-compatible onboarding run. Check one without
changing it by using the same confinement root:

```bash
rtk hangboard-onboard \
  --workspace-root /absolute/path/to/workbench-workspace \
  --output /absolute/path/to/workbench-workspace/boards/board-0001/revisions/revision-0001/run \
  --status
```

At Stage 4, **Save locally** selects the complete, current, non-stale revision
and publishes it to `Tools/HangboardOnboarding/boards/<board-id>/`. Only complete
runs with approved checkpoints through Stage 4 belong there; all unfinished
runs stay under `.context/`. Save writes files for normal Git review, but never
commits, pushes, copies artifacts into the Hang Ten app, modifies the app's
product catalog, or synchronizes anything remotely.
Hang Ten synchronization is a separate future command and is outside this
workbench. CLI and other programmatic callers are producers of the same
contract: they pass a completed run to `RepositoryBoardLibrary.publish()`.

## Edit and save one existing Stage 2 run

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --run-dir /absolute/path/to/onboarding-run
```

Then open `http://localhost:4173`. The server loads the run's unique
`stage-1-auto-rgba.png` and `stage-2-regions.json`. **Save** atomically writes
these review artifacts beside the Stage 2 proposal:

- `stage-2-regions.edited.json`: complete edited hold-highlight artifact.
- `stage-2-human-corrections.json`: added, modified, and deleted hold highlights relative to the automatic proposal.

The generated `stage-2-regions.json` is never overwritten.

The server binds to `127.0.0.1` by default and serves files only from the supplied run. Stop it with `Ctrl-C`.

After saving a reviewed run, generate a read-only comparison artifact without
starting the editor again:

```bash
scripts/hangboard-tools.sh compare \
  --run .context/hangboard-onboarding/example \
  --output .context/compare.html
```

Use the wrapper review flow around that comparison when you are validating a
single run locally:

```bash
scripts/hangboard-tools.sh inspect --run .context/hangboard-onboarding/example
scripts/hangboard-tools.sh lint --run .context/hangboard-onboarding/example
scripts/hangboard-tools.sh preview --run .context/hangboard-onboarding/example --output .context/preview
scripts/hangboard-tools.sh accept --run .context/hangboard-onboarding/example --decision accepted --reviewer local-user --notes "Reviewed all holds"
scripts/hangboard-tools.sh promote --run .context/hangboard-onboarding/example --repository-root "$PWD"
scripts/hangboard-tools.sh release-check --run .context/hangboard-onboarding/example --repository-root "$PWD"
```

`promote` stays in dry-run mode unless you add `--apply` with an explicit
runtime integration profile. If no profile is configured yet, the expected
result is `handoff-required`.

For accepted decisions, `accept` records both the acceptance artifact and the
current `lint-report.json`; the generated Stage 1 image and baseline Stage 2
proposal stay unchanged.

Apply cautiously:

- Run the dry-run `promote` command first and inspect the planned destination.
- Before `--apply`, rely on version control or make your own backup copy of
  the destination file.
- If the applied output is wrong, restore from git or that saved backup; never
  delete blindly.
- After restoring, rerun dry-run `promote` and `release-check` before trying
  `--apply` again.

## Choose among generated runs

Repeat `--run-dir` to put standard pipeline runs in the board selector:

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --run-dir /absolute/path/to/first-onboarding-run \
  --run-dir /absolute/path/to/second-onboarding-run
```

Use a catalog when runs need friendly labels or when historical Stage 1 and Stage 2 artifacts live in different subdirectories:

```json
{
  "runs": [
    {
      "label": "Board label",
      "runDir": "/absolute/path/to/pipeline-run",
      "image": "stage-one/stage-1-auto-rgba.png",
      "regions": "stage-two/stage-2-auto-regions.json"
    }
  ]
}
```

```bash
rtk python3 Tools/hold-highlight-editor/server.py --catalog /absolute/path/to/catalog.json
```

`image` and `regions` are optional for standard run layouts and must be relative to `runDir`. Catalog and repeated `--run-dir` inputs can be combined. The selector changes only the active browser document; every load and save request names its run explicitly, so separate tabs cannot redirect each other's saves.

## Edit the generative catalog outlines

Catalog-outline mode serves every `*.json` stem in the outline directory whose matching root PNG is in the source directory:

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --catalog-source-dir /absolute/path/to/docs/hangboard-generative-catalog \
  --catalog-outline-dir /absolute/path/to/docs/hangboard-generative-catalog/outlines
```

The board selector switches the active catalog document; the selected JSON is the only catalog file changed by Save. Recessed or dark cavities are traced along the inner usable boundary. Raised holds are traced along the outer silhouette. The server adapts normalized catalog paths to the editor's pixel contours, including sampled cubic curves, and maps each source outline ID to a stable positive editor ID.

Catalog Save writes edited or new outlines as closed `M`/`L` paths in normalized coordinates and recomputes their bounds. Outlines whose sampled editor contour is unchanged retain their original path commands—including cubic curves—and bounds exactly. Save preserves the catalog schema, source image, references, and untouched outline metadata, and never writes PNGs. Replacement is atomic through a same-directory temporary file; failed writes clean up that temporary file. The editor's **Export edited regions** and **Export corrections** buttons remain available as browser-download recovery backups if a save is unavailable or an additional local copy is needed.

## Static mode

To use the editor without filesystem Save support:

```bash
rtk python3 -m http.server 4173 --directory Tools/hold-highlight-editor
```

Any Stage 1 image and compatible `stage-2-regions.json` can be loaded through the toolbar or by dropping both files onto the canvas. If a `demo/` directory is supplied, the editor loads it automatically.

Hold highlights can be drawn as freeform polygons, smooth freeform curves, rectangles, rounded rectangles, arced rectangles, ellipses, or capsules. Every shape is stored as ordinary contour points for compatibility with the existing pipeline.

Selected regions expose object-level rotate and bend handles. Individual contour points and per-edge curve handles remain available behind the **Edit points** toggle for fine correction.

## Edit individual edges

Enable **Edit points**, then drag an edge handle to bow that segment without moving its vertices. Turn on **Snap edges** when the image boundary is useful; hold Alt during the drag to bypass snapping. If the curve is too aggressive, undo the gesture to restore the prior edge in one step.

## Fast tracing workflow

1. Draw one side of a repeated or symmetric hold layout.
2. Use the eight frame handles to resize, the circular handle to rotate, and the diamond handle to bend. Hold Shift while resizing a corner to preserve aspect ratio.
3. Use **Simplify curve** when a smooth outline has too many controls; undo immediately if the reduction is too aggressive.
4. Use **Mirror copy** to create a new symmetric hold highlight, or **Mirror onto…** and select an existing counterpart to replace only its geometry.
5. Enable **Snap edges** when direct point, curve-handle, or resize placement benefits from the image boundary. Hold Alt during a drag to bypass snapping.
6. Save the reviewed run.

Shortcuts outside text fields:

- `[` / `]`: previous or next hold highlight
- `M`: mirror copy
- `E`: toggle detailed point editing
- `S`: toggle edge snapping
- `Space`: pan

Edge snapping is a local contrast aid, not automatic segmentation. It affects only point, curve-handle, and resize drags and never changes a region during load, move, rotate, bend, mirror, or save.

Both export buttons remain available in server and static modes as recovery
paths. In legacy/static mode, unsaved browser edits are lost when the page
closes; guided workbench mode keeps a same-browser recovery draft and restores
it only for the matching board, revision, stage, and immutable checkpoint
attempt.
