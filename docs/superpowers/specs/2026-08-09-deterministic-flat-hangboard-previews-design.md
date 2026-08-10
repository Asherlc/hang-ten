# Deterministic Flat Hangboard Previews Design

## Goal

Replace the generated flat-preview experiment with clean, reproducible warm
illustrations that preserve each board's visible outer body and the existing
hand-editable hold outlines.

## Design

For each of the 32 catalog boards, derive a multi-piece board mask from the
existing source PNG, then render that mask as a solid warm board plane on the
shared parchment background. Draw the corresponding normalized JSON outline
paths as darker flat cavities with a restrained contour. Use no generated
pixels, photographic texture, gradients, branding, hardware, or scene details.

The renderer writes the existing `*-flat.png` paths and rebuilds the labeled
contact sheet. Source PNGs, outline JSON, Swift code, and runtime artwork remain
unchanged. These outputs stay preview references and are not interaction or
highlight geometry.

## Verification

- Exactly 32 source stems map to exactly 32 flat outputs.
- Rendering the same inputs twice is byte-identical.
- Representative single-piece, split-board, and unusual-palm boards preserve
  their board bodies and separate components.
- Every rendered hold path stays inside the canvas and remains visibly darker
  than the board plane.
- The final contact sheet is visually checked for consistent warm flat styling
  and trace-friendly contrast.
