# Hangboard batch source-audit template

Use this document to record the primary evidence and field decisions for one
directly authored batch. It is documentation, not package content.

## Models and primary sources

Record the review date and exact model-specific sources. Prefer the current
manufacturer product page, a straight-on image, an oblique/side image, and any
official hold diagram, depth chart, or manual.

| package slug | checked | product page | front image | oblique image | hold guide/manual |
| --- | --- | --- | --- | --- | --- |

Do not substitute another model's source. Record contradictions and choose only
facts that can be tied to the exact product.

## Physical inventory

Freeze the logical hold inventory before drawing. A continuous contact is one
hold even when it needs multiple disconnected geometry pieces; distinct
contacts are distinct holds.

| hold ID | name | required kind | source/visible justification | symmetry or multi-piece note |
| --- | --- | --- | --- | --- |

Every hold needs `id`, `name`, `kind`, and nonempty `geometry`. Product identity,
presentation path, aspect ratio, and the four required hold properties must be
valid.
Measurements, depth ranges, finger capacity, grip posture, and feature tags are
optional: cite them when supported and omit them when unknown.

## Direct geometry authoring

Author each normalized closed path deliberately in `board.json`, then refine it
in Workbench against the primary evidence. Mirror a reviewed side exactly when
the product is symmetric. If the current schema supports constraints, select a
regular preset only when the hold is genuinely regular; otherwise keep the path
freeform. Constraints are human-selected editing metadata, and the canonical
path remains the rendering and hit-testing truth.

Do not use image-driven detection, segmentation, masks, contour extraction,
registration, vectorization, generated path proposals, or automatic cleanup.

## Package and review result

Each batch member must be committed as a complete flat package:

```text
Hangboards/<slug>/
  board.json
  assets/
    primary.png
```

Record package-validator output and the visual reviewer/date. Inspect normal
paths in Workbench and active/highlight alignment in the app on an owned
simulator.

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
```

| package slug | validator result | Workbench review | app highlight review | unresolved omissions |
| --- | --- | --- | --- | --- |
