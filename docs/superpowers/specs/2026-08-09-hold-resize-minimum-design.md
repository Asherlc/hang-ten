# Hold Resize Minimum Design

## Goal

Prevent a hold highlight in the browser Hold Editor from collapsing into an
effectively zero-width or zero-height sliver while it is being resized.

## Root cause

`resizeContour` currently clamps each resize scale to `0.05`. That percentage
is applied to the original local bounds, so small highlights can still become
only a few pixels wide. The editor then persists that collapsed contour when
the resize ends.

## Design

Keep the existing normalized, rotated resize algorithm and opposite-edge
anchoring. Replace the percentage-only lower bound with a fixed minimum of 6
canvas pixels for each active axis. The value matches the existing minimum
meaningful drag size used when creating primitive highlights.

For side handles, only the dragged axis is clamped. For corner handles, both
axes are clamped. When Shift preserves aspect ratio, the shared scale must
still produce at least 6 canvas pixels on both axes; normal resizing must not
become a path around the minimum.

No persistence schema, rendering, pointer-event, or UI changes are needed.

## Verification

Add pure model regression tests covering:

- an east-side resize dragged past the opposite edge, which must retain at
  least 6 px of width;
- a corner resize dragged inward on both axes, which must retain at least 6 px
  in both dimensions;
- the existing normal side, corner, and aspect-ratio resize behavior.

Run the focused Node test suite for `Tools/hold-highlight-editor` and inspect
the final diff. Because this is a browser tool rather than the iOS app, Hang
Ten simulator validation is not applicable to this change.
