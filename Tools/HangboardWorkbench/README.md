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
rtk python3 Tools/HangboardWorkbench/server.py
```

The server discovers the checkout, reads saved boards from
`Hangboards/`, and keeps in-progress work in
`.context/hangboard-workbench/`. Tests and automation can override those roots:

```bash
rtk python3 Tools/HangboardWorkbench/server.py \
  --repository-root /absolute/path/to/checkout \
  --workspace-root /absolute/path/to/workbench-workspace
```

Open `http://localhost:4173`. The opening screen lists published boards and
work in progress, or lets you create a board from the exact commercial product
name and an HTTP(S) image URL or local upload.

## Correct hold outlines

1. Choose a board.
2. Click a detected hold, adjust its hold type if needed, and drag its outline points on the image.
3. Add a highlight only when detection missed one; delete one when it is wrong.
4. Open **Advanced tools** only for shape, curve, transform, edge snap, mirror, and metadata work.
5. Use **More** for comparison or artifact exports.
6. Save locally; saving does not commit, push, or synchronize changes.

## Command-line and developer workflows

The workflows below are for command-line and developer use, not part of the
editor's main task. They preserve the Stage 2 and Stage 3 artifact, autosave,
history, and local-save behavior for compatible onboarding runs.

### Edit and save one existing Stage 2 run

```bash
rtk python3 Tools/HangboardWorkbench/server.py \
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

### Choose among generated runs

Repeat `--run-dir` to put standard pipeline runs in the board selector:

```bash
rtk python3 Tools/HangboardWorkbench/server.py \
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
rtk python3 Tools/HangboardWorkbench/server.py --catalog /absolute/path/to/catalog.json
```

`image` and `regions` are optional for standard run layouts and must be relative to `runDir`. Catalog and repeated `--run-dir` inputs can be combined. The selector changes only the active browser document; every load and save request names its run explicitly, so separate tabs cannot redirect each other's saves.

### Edit the generative catalog outlines

Catalog-outline mode serves every `*.json` stem in the outline directory whose matching root PNG is in the source directory:

```bash
rtk python3 Tools/HangboardWorkbench/server.py \
  --catalog-source-dir /absolute/path/to/docs/hangboard-generative-catalog \
  --catalog-outline-dir /absolute/path/to/docs/hangboard-generative-catalog/outlines
```

The board selector switches the active catalog document; the selected JSON is the only catalog file changed by Save. Recessed or dark cavities are traced along the inner usable boundary. Raised holds are traced along the outer silhouette. The server adapts normalized catalog paths to the editor's pixel contours, including sampled cubic curves, and maps each source outline ID to a stable positive editor ID.

Catalog Save writes edited or new outlines as closed `M`/`L` paths in normalized coordinates and recomputes their bounds. Outlines whose sampled editor contour is unchanged retain their original path commands—including cubic curves—and bounds exactly. Save preserves the catalog schema, source image, references, and untouched outline metadata, and never writes PNGs. Replacement is atomic through a same-directory temporary file; failed writes clean up that temporary file. The editor's **Export edited regions** and **Export corrections** buttons remain available as browser-download recovery backups if a save is unavailable or an additional local copy is needed.

### Static mode

To use the editor without filesystem Save support:

```bash
rtk python3 -m http.server 4173 --directory Tools/HangboardWorkbench
```

Any Stage 1 image and compatible `stage-2-regions.json` can be loaded through the toolbar or by dropping both files onto the canvas. If a `demo/` directory is supplied, the editor loads it automatically.

Hold highlights can be drawn as freeform polygons, smooth freeform curves, rectangles, rounded rectangles, arced rectangles, ellipses, or capsules. Every shape is stored as ordinary contour points for compatibility with the existing pipeline.

Selecting a hold highlight exposes its canvas handles: contour points and per-edge curve handles for freeform highlights, or resize, rotate, and bend handles for primitive shapes. Open **Advanced tools** for the corresponding shape, curve, and transform actions in the inspector, plus **Snap edges** and other fine controls. Press `E` to open or close **Advanced tools** outside text fields.

### Edit individual edges

Select a hold highlight, then drag an edge handle to bow that segment without moving its vertices. Open **Advanced tools** and turn on **Snap edges** when the image boundary is useful; hold Alt during the drag to bypass snapping. If the curve is too aggressive, undo the gesture to restore the prior edge in one step.

### Fast tracing workflow

1. Draw one side of a repeated or symmetric hold layout.
2. Use the eight frame handles to resize, the circular handle to rotate, and the diamond handle to bend. Hold Shift while resizing a corner to preserve aspect ratio.
3. Use **Simplify curve** when a smooth outline has too many controls; undo immediately if the reduction is too aggressive.
4. Use **Mirror copy** to create a new symmetric hold highlight, or **Mirror onto…** and select an existing counterpart to replace only its geometry.
5. Enable **Snap edges** when direct point, curve-handle, or resize placement benefits from the image boundary. Hold Alt during a drag to bypass snapping.
6. Save the reviewed run.

Shortcuts outside text fields:

- `[` / `]`: previous or next hold highlight
- `M`: mirror copy
- `E`: open or close **Advanced tools** for the selected hold highlight
- `S`: toggle edge snapping
- `Space`: pan

Edge snapping is a local contrast aid, not automatic segmentation. It affects only point, curve-handle, and resize drags and never changes a region during load, move, rotate, bend, mirror, or save.

Both export buttons remain available in server and static modes as recovery
paths. In legacy/static mode, unsaved browser edits are lost when the page
closes; guided workbench mode keeps a same-browser recovery draft and restores
it only for the matching board, revision, stage, and immutable checkpoint
attempt.
