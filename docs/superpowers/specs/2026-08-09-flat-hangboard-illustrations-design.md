# Flat Hangboard Illustration Catalog Design

## Goal

Create a preview-only illustration pass for every individual board image in
`docs/hangboard-generative-catalog/`. The new images should make each board
recognizable while replacing the current semi-realistic product-render look
with a flattened, symbolic visual language that is easier to trace by hand.

## Scope

- Cover the 32 individual PNG board renders currently in the catalog.
- Keep the existing realistic renders and normalized outline JSON unchanged.
- Save the new images as a sibling preview set under
  `docs/hangboard-generative-catalog/flat-illustrations/`.
- Do not add or modify Swift assets, `BoardDesign`, `BoardCatalog`, hit testing,
  or runtime app rendering.
- Do not treat generated pixels as authoritative interaction geometry.

## Visual design

Each illustration uses a small warm palette: parchment background, light wood
or clay board planes, one darker warm contour/shadow color, and a restrained
accent for cavity depth where useful. The board is centered with generous
padding in a consistent landscape canvas. The illustration is front-facing or
near-front-facing, with a clean outer silhouette and simplified flat shapes for
the major ledges, pockets, rails, shelves, and recesses.

The batch must avoid photographic grain, wood pores, glossy highlights,
realistic cast shadows, mounting hardware, logos, product text, hands, wall
scenes, and decorative objects. Depth may be suggested with a few nested flat
regions, but every region should remain visually separable and traceable.

## Generation and naming

Use the existing board PNG as a reference image for each new generation. Use
one prompt per board so the board-specific silhouette and hold arrangement can
survive the simplification. Name each result with the existing source stem plus
`-flat.png`, preserving the catalog's stable stems.

The pilot should use one representative board with mixed geometry before the
remaining batch is generated. If the pilot loses the silhouette or collapses
important hold groups, adjust the shared prompt once and regenerate the pilot
before continuing.

## Review contract

Before accepting the batch, inspect the pilot and the final contact sheet for:

1. recognizable outer silhouette and orientation;
2. preserved major hold rows, rails, pockets, or paired structures;
3. consistent warm palette and flat treatment across boards;
4. no accidental text, branding, texture, hands, or photorealistic lighting;
5. sufficient padding and contrast for manual tracing.

This pass is successful when all 32 source stems have a corresponding flat
preview PNG and the images are useful as visual tracing references, even where
their geometry still requires later manual correction.
