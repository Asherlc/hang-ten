# Lattice Mini Bar presentation assets — source audit

Reviewed 2026-08-29. This audit covers only the final presentation replacement
and manual canonical-geometry review for `Hangboards/lattice-mini-bar`.

## Revision and inventory source

The current [Lattice Mini Bar product page](https://latticetraining.com/product/mini-bar-portable-hangboard/)
identifies the product as a reversible 15.5 cm portable bar with four grips: a
10 mm edge, a 20 mm edge, an ergonomic jug, and a mini pinch. The same frozen
inventory is stated in the [Lattice 2025 catalogue, p. 8](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf).
This change preserves the stable hold IDs `edge-10`, `edge-20`,
`ergonomic-jug`, and `mini-pinch`; it does not add a contact, measurement, or
training claim.

The product page's complete official gallery was reviewed. In particular, it
shows the smaller and larger opposing longitudinal lips of one routed channel,
the usable rounded exterior body, and the end-on pinch profile. The bar is
rotated between grips; the evidence does not establish four simultaneous
front-facing contacts.

## Manufacturer authority and final generated contract

The following exact first-party images are the physical authority for the final
renders. They are inputs and corroboration, not the tracked presentation
pixels.

| Role | Exact first-party asset | Dimensions | SHA-256 |
| --- | --- | --- | --- |
| Lengthwise topology, material, and suspension | [Mini-Bar-Web-1.jpg](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-1.jpg) | 1000 × 1000 | `610cfaa96a95d80ae0d37ef4bbf2b1d881b47d0813d7d0eb4f9db9b5c30270de` |
| End profile, lower relief, material, and suspension | [Mini-Bar-Web-2.jpg](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-2.jpg) | 1000 × 1000 | `e8b2e366f8e20abc4959019c5c46ae67d53fe4526100f66acf8d3f0e3d66974b` |

The shared presentation-generation baseline is recorded in
`.context/pretty-impala-corrected-remaining/contract.json` (SHA-256
`b4003b6b42f01bfa2550b7bfc0a820324cacbce00aac6f9e75c1cb17865c546f`).
It requires a clean Hang Ten catalog product render, treats manufacturer images
as the sole physical authority, prohibits text, labels, logos, people, walls,
props, altered contact topology, and product-specific pipeline behavior, and
forbids crop, resize, masking, registration, segmentation, vectorization, or
manual pixel postprocessing.

The accepted end correction is recorded in
`.context/pretty-impala-lattice-mini-final-correction/run-data.json`
(SHA-256 `a6de1323761bd0a06b7c0707ca9080580ca7151e2610a00b54abf7033668b520`).
The accepted tighter lengthwise generation, both rejected tighter attempts,
the root source checkpoint, the exact final prompt, input roles, output
dimensions, and cleanup verification are recorded in
`.context/pretty-impala-lattice-mini-tight-primary/run-data.json` (SHA-256
`e4782da581cd0ec6d29df6517c53f2e5637ef739c4a42f138d2399621e297b87`).
Its final populated prompt is
`.context/pretty-impala-lattice-mini-tight-primary/final-prompt.txt` (SHA-256
`893f4b3b3c2f59e190194f0ef71f59c59e486824b97eed67b43a619f105b4151`).
Each accepted raster was copied byte-for-byte into the package:

| Presentation | Accepted generated output | Tracked asset | Pixels / ratio | SHA-256 |
| --- | --- | --- | --- | --- |
| `primary` — Lengthwise | `.context/pretty-impala-lattice-mini-tight-primary/lattice-mini-bar-primary.png` | `Hangboards/lattice-mini-bar/assets/primary.png` | 1536 × 1024 / `1.5` | `db351c7c617420b84550e64d6685c8c98e60da9529feb3697bd7435af5f751fc` |
| `end` — End | `.context/pretty-impala-lattice-mini-final-correction/lattice-mini-bar-end.png` | `Hangboards/lattice-mini-bar/assets/end.png` | 1254 × 1254 / `1.0` | `e89852ee79199b957ba8f85d1555898f6fdb1f8cc56e9a0876f8f179159cc676` |

There was no post-generation crop, resize, retouch, compositing, masking,
registration, alignment, segmentation, detection, vectorization, automatic
path proposal, or automatic path authoring.

## Explicitly superseded presentation candidates

The exact 1000 × 1000 manufacturer packshots previously tracked at
`assets/primary.png` (SHA-256
`fbd9a1e94ebf1fbb93d7a73b667d4e70598670202001c3692c12be980ac9031f`)
and `assets/end.png` (SHA-256
`ce2559a04e75bc609fe2651e8c3d3137416b917e43caa4e7147c46c25d914e17`)
remain source evidence but are rejected as final presentation assets. Their
rope-dominant oblique framing obscures the lengthwise body, and the official end
packshot does not provide the same clean catalog framing as existing Hang Ten
boards. The exact-pixel promotion and its former geometry are superseded.

The marked or structurally incomplete attempts beneath
`.context/pretty-impala-corrected-remaining/rejected/` also remain rejected:

- `lattice-mini-bar-primary-attempt-1.png` exposed an extra routed surface and
  a visible mark.
- `lattice-mini-bar-primary-attempt-2.png` retained a prohibited visible maker
  mark. It was used only as a composition input to the source-controlled final
  cleanup; it is not itself an accepted asset.
- `lattice-mini-bar-end-attempt-1.png` cropped the suspension. It was used only
  as a composition input to the source-controlled final end correction; it is
  not itself an accepted asset.
- `lattice-mini-bar-end-attempt-2.png` was neither a complete nor a true end-on
  presentation.

The first apparently cleaned square lengthwise correction at
`.context/pretty-impala-lattice-mini-final-correction/lattice-mini-bar-primary.png`
(1254 × 1254, SHA-256
`9f26e413887dc47789ee94a6512f487c389207df5753ed998868f7e8d34b9445`)
also remains rejected. Its wooden bar occupied only about 18% of the square's
height while a tall rope triangle dominated the frame, so the narrow edge
surfaces were not comfortably legible at normal catalog-card scale.

The first two tighter 1536 × 1024 attempts are likewise rejected and retained
only in `.context/pretty-impala-lattice-mini-tight-primary/`:

- `rejected-attempt-1.png` (SHA-256
  `b54295a63fdf01337fba67336b3063ac5e8e6565bc6e7b969dee73113a7eb0d2`)
  improved hierarchy but flattened the board below the source-backed rounded
  cross-section and staged an oversized rope bundle.
- `rejected-attempt-2.png` (SHA-256
  `a4204b522d1b36149d98ae803767e0271fd8b9462efd8242587c1be0df3d50dd`)
  cleaned the rope but retained a flat plank-like silhouette inconsistent with
  the official end-on evidence.

The final revised-contract pass restores the rounded/cylindrical silhouette,
keeps one continuous channel and a compact source-faithful rope loop, and makes
the wooden product the clear catalog subject. Only the two hashes in the
accepted table are promoted.

## Manual canonical-geometry mapping

Every saved path was deliberately drawn and reviewed by an operator against
the final pixels and first-party evidence. No coordinates, contours, masks, or
geometry proposals were extracted from an image.

- `edge-20` follows the upper opposing lip of the one visible longitudinal
  channel.
- `edge-10` follows the lower opposing lip of that same channel.
- `ergonomic-jug` uses multiple deliberately authored pieces to cover the
  complete visible and usable exterior wooden body around the channel while
  excluding rope and background.
- `mini-pinch` follows the complete clean wooden end face and its concave lower
  relief, excluding the surrounding rope, background, and the relief opening.

The irregular perspective surfaces use freeform paths. The saved paths remain
the sole rendering, highlighting, and hit-testing truth; the Trango Rock
Prodigy Pivot package was used only as the precedent for economical smooth
closed paths, not as product geometry.

## Review evidence

Owned headless Workbench captures are beneath
`.context/pretty-impala-mini-nug-final-overlays/`. They include normal,
per-hold active, and stable-ID label states for both Mini Bar presentations,
plus the final review contact sheet. The active overlays stay on the source-
mapped wooden surfaces and omit rope, background, and the end relief opening.
The capture runner terminated its exact loopback server and Chrome process,
deleted its exact owned profile, and verified that no owned resource remained.
