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

## Static mode

To use the editor without filesystem Save support:

```bash
rtk python3 -m http.server 4173 --directory Tools/hold-highlight-editor
```

Any Stage 1 image and compatible `stage-2-regions.json` can be loaded through the toolbar or by dropping both files onto the canvas. If a `demo/` directory is supplied, the editor loads it automatically.

Regions can be drawn as freeform polygons, smooth freeform curves, rectangles, rounded rectangles, arced rectangles, ellipses, or capsules. Every shape is stored as ordinary contour points for compatibility with the existing pipeline.

Selected regions expose object-level rotate and bend handles. Individual contour points remain available behind the **Edit points** toggle for fine correction.

Both export buttons remain available in server and static modes as recovery paths. Unsaved browser edits are lost when the page closes.
