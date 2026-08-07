# Hold Region Editor

A dependency-free local browser editor for hangboard grip-region artifacts.

## Run the guided local workbench

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --workspace-root /absolute/path/to/workbench-workspace
```

Open `http://localhost:4173`. Enter the exact commercial product name, choose
an HTTP(S) image URL or local image upload, and select **Create board**. The
image bytes, run manifests, approvals, drafts, and revisions stay under the
explicit workspace root. Existing boards appear in **Recent runs** after a
refresh or server restart.

Creation publishes Stage 0 and stops for review. **Approve & continue** binds
the displayed checkpoint to its hashes, runs the next installed stage, and
stops at the next review automatically. **Retry** publishes a new immutable
attempt for the current stage without overwriting its earlier evidence.

Stage 2 edits the pixel-aligned contour inventory that produces the label map.
Stage 3 edits the vector display paths that become the final interactive grip
geometry. Both editors autosave validated drafts to the active revision;
approval materializes the newest draft as a new checkpoint attempt. Undo/redo
history is browser-local, and an unsaved same-browser recovery draft can be
restored after refresh. Published attempts and approvals remain immutable on
disk.

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

At Stage 4, **Save locally** only selects the complete, current, non-stale
revision in `board.json`. It does not copy artifacts into the Hang Ten app,
modify the app's product catalog, or synchronize anything remotely. Hang Ten
synchronization is a separate future command and is outside this workbench.

## Edit and save one existing Stage 2 run

```bash
rtk python3 Tools/hold-highlight-editor/server.py \
  --run-dir /absolute/path/to/onboarding-run
```

Then open `http://localhost:4173`. The server loads the run's unique
`stage-1-auto-rgba.png` and `stage-2-regions.json`. **Save** atomically writes
these review artifacts beside the Stage 2 proposal:

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

Both export buttons remain available in server and static modes as recovery
paths. In legacy/static mode, unsaved browser edits are lost when the page
closes; guided workbench mode keeps a same-browser recovery draft and restores
it only for the matching board, revision, and stage.
