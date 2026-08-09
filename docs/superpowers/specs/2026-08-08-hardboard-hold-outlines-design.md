# Generated Hardboard Hold Outlines Design

## Goal

Create hand-editable vector hold outlines for every individual generated hardboard image in `docs/hangboard-generative-catalog/`, excluding the composite `contact-sheet-primary.png` and existing onboarding fixtures.

## Scope

- Process the 32 individual catalog PNGs.
- Produce one JSON outline document per source image in `docs/hangboard-generative-catalog/outlines/`.
- Represent hold boundaries as editable vector paths rather than dense pixel contours.
- Keep the source image dimensions and normalized `0...1` coordinates in every document.
- Preserve uncertainty explicitly instead of presenting visual guesses as factual manufacturer metadata.

## JSON shape

Each board document will contain:

```json
{
  "schemaVersion": 1,
  "sourceImage": "../board-name.png",
  "canvas": { "width": 1536, "height": 1024 },
  "coordinateSpace": "normalized",
  "references": [
    {
      "title": "Manufacturer product or hold-layout source",
      "url": "https://example.com/product",
      "hints": ["two jugs", "three edge depths"]
    }
  ],
  "outlines": [
    {
      "id": "hold-001",
      "label": "upper-left-edge",
      "kind": "edge",
      "confidence": "approximate",
      "bounds": { "x": 0.12, "y": 0.21, "width": 0.19, "height": 0.06 },
      "path": {
        "closed": true,
        "commands": [
          { "command": "M", "to": [0.12, 0.21] },
          { "command": "L", "to": [0.31, 0.21] },
          { "command": "C", "controls": [[0.30, 0.26], [0.14, 0.27]], "to": [0.12, 0.21] }
        ]
      },
      "notes": "Visual estimate from generated raster; review before runtime use."
    }
  ]
}
```

`M`, `L`, and cubic `C` commands are sufficient for GUI editing and avoid the ambiguity of a free-form SVG string. All path points use normalized coordinates, while the `canvas` object preserves the source pixel frame for round-tripping and review overlays. `bounds` is redundant by design: it supports selection handles and quick GUI layout without reparsing the path.

`references` is advisory provenance. Manufacturer sources can guide hold counts, broad layout, and likely grip categories when the generated raster is ambiguous, but they must not override the visible raster or turn an estimate into verified geometry. Documents without a useful source use an empty array.

## Vectorization approach

Use deterministic local image processing to propose candidate hold regions and simplify their contours into mixed line/cubic paths. Prefer long straight runs for board rails and edges, smooth cubic curves for rounded pockets and sculpted holds, and preserve concave corners where they are visually meaningful. The generator must not invent manufacturer semantics; `label`, `kind`, `confidence`, and `notes` are editable visual annotations.

Before finalizing candidates, consult the maintained source hints for matching product names. Use official manufacturer pages, manuals, and hold-layout guides first; record the URL and only the broad facts that help identify or arrange visible holds. Community or retailer references may be used only as low-confidence orientation hints.

The generated JSON is a starting point for hand correction. It is not runtime interaction geometry and must not be wired into `BoardDesign` or hit testing by this change.

## Validation

- Exactly one outline JSON exists for each of the 32 individual catalog PNGs.
- Every JSON file parses and has `schemaVersion: 1`, a matching source image, positive canvas dimensions, and normalized coordinates within `0...1`.
- Every path is closed, has a valid command sequence, and has a non-empty bounding box containing all path coordinates.
- Generation is deterministic: running the generator twice yields byte-identical JSON.
- A rendered review overlay is produced for representative boards so contours can be visually checked against their source rasters.
- The composite contact sheet is not processed.

## Out of scope

- Adding Swift board models or registering boards in `BoardCatalog`.
- Claiming manufacturer-verified hold depth, finger count, or grip semantics.
- Replacing the accepted `Tools/HangboardOnboarding` pipeline.
- Adding runtime highlighting or hit testing from these raster-derived outlines.
