# Task 11 report — YY Vertical portable boards

Completed 2026-08-21 in workspace `giant-pug`.

## Outcome

Created four separate complete schema-v2 packages:

- `Hangboards/yy-travelboard/` — TravelBoard, six physical contacts over two
  presentations.
- `Hangboards/yy-baguette/` — La Baguette, six contacts over two presentations.
- `Hangboards/yy-baguette-evo/` — Baguette Evo, nineteen physical contacts over
  five presentations, preserving the manufacturer's twelve grip types.
- `Hangboards/yy-penta-evo/` — Penta Evo, fourteen contacts across the official
  pair in one presentation.

Each package contains only `board.json` and its declared generated PNG assets.
The shared source audit records official evidence, field-level mappings,
artwork provenance, and manual geometry decisions. Focused approved-inventory,
contact-count, presentation, and mirror tests were added to
`Tools/HangboardPackages/tests/test_approved_board_packages.py`.

## Exact official sources

Only YY Vertical's current official product pages and first-party packshots
were used as evidence.

### TravelBoard

- Product page:
  `https://www.yyvertical.com/en/products/la-travelboard-poutre-dentrainement`
- Packshots:
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-travelboard-1.webp`,
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-travelboard-2.webp`,
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-travelboard-3.webp`, and
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-travelboard-4.webp`.
- Frozen facts: six grips (tray, 25/15/10 mm edges, two monos), two usable
  inclinations, and dimensions `34 × 10 × 3 cm`.

### La Baguette

- Product page:
  `https://www.yyvertical.com/en/products/la-baguette-poutre-escalade`
- Packshots:
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-la-baguette-1.webp`,
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-la-baguette-2.webp`, and
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-la-baguette-3.webp`.
- Frozen facts: six grips (10/15/20/25/30 mm and tray), two inclinations by
  turning, and dimensions `47 × 4 × 4 cm`.

### Baguette Evo

- Product page: `https://www.yyvertical.com/en/products/baguette-evo`.
- Official images:
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_02_FG.webp`,
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_03_FG.webp`,
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_04_FG.webp`,
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_05_FG.webp`,
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_06_FG.webp`,
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_07_FG.webp`,
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_08_FG.webp`, and
  `https://www.yyvertical.com/cdn/shop/files/YY_BAGUETTE_EVO_10_FG.webp`.
- Frozen facts: seven doubled edge types (25/20/15/12/10/8/6 mm), four central
  edges (30/25/20/6 mm), rounded trays, Turn & Pull rotation, and dimensions
  `52 × 5 × 5 cm`.

The manufacturer counts twelve grip *types*. The package has nineteen physical
contacts because each of the seven doubled types is independently selectable
on both sides, while the four central edges and one continuous tray occur once.

### Penta Evo

- Product page: `https://www.yyvertical.com/en/products/penta-evo`.
- Packshots:
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-penta-evo-1.webp`,
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-penta-evo-3.webp`, and
  `https://www.yyvertical.com/cdn/shop/files/yy-vertical-agres-nomades-penta-evo-11.webp`.
- Frozen facts: two independent units, seven enumerated grips per unit
  (25/20/15/10 mm, mono, duo, tray), and 360-degree notched rotation.

The page title says eight grips, but both its feature list and technical list
enumerate the same seven. The repeated enumerated inventory controls. YY
Vertical publishes no Penta Evo dimensions, so the required schema field says
`Not published by YY Vertical`; dimensions from the different older Penta were
not borrowed.

No reseller evidence, inferred dimensions, training instructions, posture
claims, or invented coaching text entered any package.

## Artwork provenance

All accepted images were produced by the built-in image generator as simplified
product illustrations. Official images were visual references; the generated
files are explicitly NON-evidence. Exact prompts, source roles, and correction
history are preserved in the source audit.

| Package asset | Pixels | SHA-256 |
| --- | ---: | --- |
| TravelBoard `primary.png` | 1536 × 1024 | `18047e867d71a5113f9e828b60959e66b58723906f0b489f7ae1864484fa020a` |
| TravelBoard `reverse.png` | 1774 × 887 | `bed470db4496b8cc8c2b1f69e918382850097dd7c6c6b68bae21ef952383e690` |
| La Baguette `primary.png` | 1536 × 1024 | `8fd05bf3dc6460bff7345c5e7f4a4c394e39e2bc171ea113d5d7911486746618` |
| La Baguette `reverse.png` | 1536 × 1024 | `e1ab6cedad15eb577756fabff3f34b5c83baae33493ddb9a5eb223994d57f063` |
| Baguette Evo `primary.png` | 1774 × 887 | `f50f5a5ef3f235b3a07a5d1df16eedc95cb4671cf5c39621bd3ea4711c570509` |
| Baguette Evo `shallow-pairs.png` | 1774 × 887 | `1c419b08dda5cfe4d12d27486f1a3ca4b6a967e1aa82d266919d6ad8b37fa38a` |
| Baguette Evo `central-30-25.png` | 1536 × 1024 | `86f71b252af0c0e09bcb0b260b996a2bfbbeda02b3e9a3e53342cee6d661348f` |
| Baguette Evo `central-20-6.png` | 1774 × 887 | `d06a5f87e436a72621e30151011a314203cb1887d50c4934944a449f2a86dd24` |
| Baguette Evo `tray.png` | 1536 × 1024 | `77237c4b6345c3b385592d159a2f5bd5ee96f43928c4387222413fcc62ad604a` |
| Penta Evo `primary.png` | 1536 × 1024 | `d153f8c4b0842342eee3598b958f8b0b3a48d8b87d6ced80b02e41c327fc430c` |

The files were copied directly from the generator outputs. There was no crop,
registration, detection, segmentation, mask or contour extraction,
vectorization, simplification, or generated-geometry workflow. Penta Evo's
first output contained unsupported lower pockets, and an intermediate edit
incorrectly merged the official upper recesses. The accepted precise-object
edit restores two visibly separate upper recesses per unit while keeping the
unsupported lower pockets absent; its exact prompt and rejected-variant
history are recorded in the audit.

## Presentation and geometry decisions

- TravelBoard separates its official front 25/15/mono/tray face from the
  reverse 10 mm face.
- La Baguette separates its stepped 30/tray/20/25 face from the turned 15/10
  face; unlabelled reverse recess backs were not promoted to contacts.
- Baguette Evo uses five honest orientations so duplicated edges, central
  opposing lips, and the rounded tray are not flattened into a fabricated
  composite image.
- Penta Evo shows both independent units together. Each unit retains distinct
  25 and 20 mm upper recesses separated by solid apex wood. The right canonical
  paths are exact global horizontal mirrors of the left because the official
  pair image shows matching units.

Every canonical path was authored deliberately in normalized coordinates after
the official inventory was frozen. Baguette Evo's documented paired contacts
and Penta Evo's paired units use exact mirrors where appropriate. Constraints
were selected only for visibly regular circles, ovals, pills, rectangles, or
rounded rectangles; they are editing metadata. Saved paths remain the sole
rendering, highlighting, and hit-test source of truth.

Direct Workbench extraction returned:

| Board | Presentations and extracted regions |
| --- | --- |
| TravelBoard | `front-25-15` 5; `reverse-10` 1 |
| La Baguette | `stepped-face` 4; `reverse-face` 2 |
| Baguette Evo | `paired-25-20-15-10` 8; `paired-12-8-6` 6; `central-30-25` 2; `central-20-6` 2; `rounded-tray` 1 |
| Penta Evo | `front-pair` 14 |

The extraction asserted that every presentation had regions and that the
presentation-region total equaled the canonical geometry-piece total.

## Review corrections

- Recentered Baguette Evo's `central-30-25` upper and lower canonical paths on
  the accepted image's visible recess lips; focused bounds now freeze the
  reviewed frames.
- Replaced Penta Evo's merged-upper-cavity art with a 1536 × 1024 source-faithful
  edit containing two separated upper recesses per unit, then manually redrew
  the four upper canonical paths against it.
- Strengthened focused tests to freeze La Baguette and Baguette Evo's ordered
  presentation definitions, default selections, and complete hold-to-surface
  maps. Mirror tests now compare canonical vector segments in global
  coordinates rather than frames alone.

## Verification

- Final-inventory validation — passed with all four board IDs and zero drafts.
- Package status — passed and listed all four YY packages.
- Focused approved-package test file — 24 passed (7 YY-specific tests).
- Full HangboardPackages suite — 92 passed.
- Direct Workbench extraction — all ten presentations and forty-five physical
  holds loaded with every geometry piece accounted for.
- Full Workbench suite — 318 passed. A first sandboxed run had 264 passes and
  54 environment-only failures because localhost socket binding was denied;
  the identical suite passed after socket access was permitted.
- Real staging-script invocation — passed against an isolated Xcode-style
  resource destination; all four YY package manifests were present, and the
  corrected Baguette Evo and Penta Evo staged packages were byte-for-byte
  identical to their sources.

## Limitations and deferred review

Task 11 does not claim the catalog-wide iOS simulator normal/active/hit-test
inspection assigned to Task 12. The generated art is simplified catalog
content, not measurement evidence. Penta Evo's missing published dimensions
and its title/list count discrepancy are deliberately visible in the audit
rather than silently inferred away.

The affected images were reviewed at original resolution and the corrected
documents were extracted through Workbench. An interactive Workbench browser
pass was attempted, but no in-app or extension browser was connected to this
workspace; the temporary listener was stopped and its port verified closed.

## Cleanup

- The isolated `.context/giant-pug-task11-staging` resource tree was removed by
  its EXIT trap and verified absent.
- Workspace-owned official source downloads and rejected generator-review
  material under `.context/giant-pug-task11-yy` and
  `.context/giant-pug-task11-review` were removed after review.
- Official source images are not package artifacts and were not committed.
- No Workbench listener, simulator, container, or other external resource
  remained active.
