# Hold Region Editor

A dependency-free local browser editor for hangboard grip-region artifacts.

## Edit and save an onboarding run

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --run-dir /absolute/path/to/onboarding-run
```

Then open `http://localhost:4173`. The server loads the run's unique `stage-1-auto-rgba.png` and `stage-2-regions.json`. **Save** atomically writes these review artifacts beside the Stage 2 proposal:

- `stage-2-regions.edited.json`: complete edited region artifact.
- `stage-2-human-corrections.json`: added, modified, and deleted regions relative to the automatic proposal.

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

## Static mode

To use the editor without filesystem Save support:

```bash
rtk python3 -m http.server 4173 --directory Tools/hold-highlight-editor
```

Any Stage 1 image and compatible `stage-2-regions.json` can be loaded through the toolbar or by dropping both files onto the canvas. If a `demo/` directory is supplied, the editor loads it automatically.

Regions can be drawn as freeform polygons, smooth freeform curves, rectangles, rounded rectangles, arced rectangles, ellipses, or capsules. Every shape is stored as ordinary contour points for compatibility with the existing pipeline.

Selected regions expose object-level rotate and bend handles. Individual contour points remain available behind the **Edit points** toggle for fine correction.

## Fast tracing workflow

1. Draw one side of a repeated or symmetric hold layout.
2. Use the eight frame handles to resize, the circular handle to rotate, and the diamond handle to bend. Hold Shift while resizing a corner to preserve aspect ratio.
3. Use **Simplify curve** when a smooth outline has too many controls; undo immediately if the reduction is too aggressive.
4. Use **Mirror copy** to create a new symmetric region, or **Mirror onto…** and select an existing counterpart to replace only its geometry.
5. Enable **Snap edges** when direct point or resize placement benefits from the image boundary. Hold Alt during a drag to bypass snapping.
6. Save the reviewed run.

Shortcuts outside text fields:

- `[` / `]`: previous or next region
- `M`: mirror copy
- `E`: toggle detailed point editing
- `S`: toggle edge snapping
- `Space`: pan

Edge snapping is a local contrast aid, not automatic segmentation. It affects only point and resize drags and never changes a region during load, move, rotate, bend, mirror, or save.

Both export buttons remain available in server and static modes as recovery paths. Unsaved browser edits are lost when the page closes.
