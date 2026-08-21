# Complete Hangboard Catalog Design

## Goal

Add every product identified in the 2026-08-20 catalog audit as a complete,
source-backed Hang Ten package.  Extend the package format and Workbench so a
portable, reversible, or suspended device can represent every documented
usable surface without fabricating a single-front layout.

## Scope

### New fixed-board packages

- Metolius Foundry Training Board
- Metolius Prime Rib
- Metolius Wood Grips II Deluxe
- The Hangboard

### New portable or multi-surface packages

- Tension Flash Board
- Metolius Light Rail 2.0
- Metolius Rock Rings 3D
- YY Vertical TravelBoard
- YY Vertical The Baguette
- YY Vertical Baguette Evo
- YY Vertical Penta Evo

The Wood Grips II Deluxe package is separate from the existing Compact II
package because the manufacturer presents them as different physical variants.
Flash Board remains in scope even though its official store currently marks it
unavailable: it has a current manufacturer product page and must be labelled
only with facts that page supports.

## Source and asset contract

Each package receives a source audit under `docs/source-audits/` that records:

1. the official product URL and review date;
2. official straight-on image URLs for every visual surface;
3. official oblique, manual, or hold-guide URLs used to distinguish a recess,
   shelf, or continuous contact;
4. a field mapping for the product identity, dimensions, hold inventory, and
   only those measurements or finger capacities explicitly published; and
5. a surface-to-hold mapping that makes the complete physical inventory
   reviewable.

The app-facing primary image follows the existing catalog convention: it is a
clean AI-created simplified illustration of the product, not a manufacturer
photograph. The primary manufacturer's imagery is supplied to the image model
as reference for the documented layout, then a human compares the generated
illustration against those sources before accepting it. The source audit
retains the manufacturer URLs; generated images are never presented as source
evidence.

Each accepted illustration is saved as a PNG without later crop, registration,
segmentation, contour extraction, vectorization, or automatic geometry
operation. An operator deliberately draws every canonical closed path and
manually chooses a supported shape constraint only when the actual product
surface is genuinely regular. Geometry is checked against primary manufacturer
evidence as well as the accepted simplified illustration; image generation
never creates, proposes, or validates geometry.

## Package format

`schemaVersion` advances from `1` to `2`.  Version 1 packages remain valid
and retain their exact `presentation.assetPath` and unscoped holds.

Version 2 replaces the single presentation with a nonempty `presentations`
array. Each entry has an identifier, a concise source-backed display name, and
an asset path beneath `assets/` for its AI-created simplified illustration.
One entry is marked `default: true`.
Every hold has a required `presentationID`, which identifies the one surface
on which its canonical normalized geometry is drawn.  A physical contact
shared across multiple views is represented once, against one canonical
surface; a second view may only exist as supporting evidence unless it shows a
different usable contact.

This keeps the existing flat hold model, stable plan references, and
highlighting semantics while letting the app and Workbench filter holds to the
visible surface.  It also prevents a reversible rail or cylinder from having
contacts overlaid on an unrelated photograph.

Asset validation expands from exactly `assets/primary.png` to exactly the set
declared by the package.  All declared presentation assets must be regular,
non-symlink PNGs.  Each image's aspect ratio must agree with the selected
surface canvas; package-level product dimensions remain product facts rather
than inferred image measurements.

## App behavior

`TrainingBoard` retains its globally stable hold IDs and product identity, and
adds ordered presentation metadata. `BoardMapView` receives an optional
selected presentation ID; it shows that presentation's accepted AI-created
simplified illustration and only the holds whose `presentationID` matches. It
defaults to the package default presentation. Existing callers preserve their
current behavior.

The plan and activity UI exposes a compact, accessible presentation selector
only when a board has more than one presentation.  Selecting a hold from a
plan changes to its presentation before drawing its active highlight.  A plan
never silently highlights a hold on the wrong surface.

## Workbench behavior

The Workbench returns each presentation's image URL and records each region's
presentation ID.  It adds a presentation selector beside the canvas controls.
Switching the selector changes the image and filters regions, selection, and
guides to that presentation.  Saving preserves unselected presentations
byte-for-byte except for deliberately changed document fields.  New holds are
created on the selected presentation.

## Tests and verification

Add fail-closed package-loader tests for both schema versions, duplicate and
missing presentation identifiers, undeclared or missing assets, and a hold
assigned to an unknown presentation.  Add Swift decoding/store tests for the
same failures and board-map tests proving the selected image and its matching
holds are used.  Add Workbench controller/UI tests for surface filtering and
save preservation.

For every completed package, run final-inventory validation, staging tests,
and the targeted package tests.  Inspect every presentation in Workbench and
inspect normal, active, and hit-test alignment in the app on an owned iOS
simulator.  The source audit records this review rather than treating a
passing parser as visual proof.

## Non-goals

- No automatic hold detection or image-derived geometry.
- No new training routines or unsourced cue text.
- No generic product category, accessory, mounting board, or device added
  without a specific product package and primary evidence.
- No inference of depth, finger capacity, grip posture, or material claims
  from photographs.
