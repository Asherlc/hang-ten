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

Selected regions expose object-level rotate and bend handles. Individual contour points and per-edge curve handles remain available behind the **Edit points** toggle for fine correction.

## Edit individual edges

Enable **Edit points**, then drag an edge handle to bow that segment without moving its vertices. Turn on **Snap edges** when the image boundary is useful; hold Alt during the drag to bypass snapping. If the curve is too aggressive, undo the gesture to restore the prior edge in one step.

## Fast tracing workflow

1. Draw one side of a repeated or symmetric hold layout.
2. Use the eight frame handles to resize, the circular handle to rotate, and the diamond handle to bend. Hold Shift while resizing a corner to preserve aspect ratio.
3. Use **Simplify curve** when a smooth outline has too many controls; undo immediately if the reduction is too aggressive.
4. Use **Mirror copy** to create a new symmetric region, or **Mirror onto…** and select an existing counterpart to replace only its geometry.
5. Enable **Snap edges** when direct point, curve-handle, or resize placement benefits from the image boundary. Hold Alt during a drag to bypass snapping.
6. Save the reviewed run.

Shortcuts outside text fields:

- `[` / `]`: previous or next region
- `M`: mirror copy
- `E`: toggle detailed point editing
- `S`: toggle edge snapping
- `Space`: pan

Edge snapping is a local contrast aid, not automatic segmentation. It affects only point, curve-handle, and resize drags and never changes a region during load, move, rotate, bend, mirror, or save.

Both export buttons remain available in server and static modes as recovery paths. Unsaved browser edits are lost when the page closes.
