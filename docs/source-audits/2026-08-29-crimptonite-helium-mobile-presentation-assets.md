# Crimptonite Helium Mobile presentation assets

Review date: 2026-08-29  
Workspace owner: `pretty-impala`

This audit fixes the physical revision and presentation chain for
`crimptonite.helium-mobile`. The current manufacturer product is the slender
400 × 58 × 24 mm board with exactly three routed cavities. The former
nine-cavity gallery image is a different, previous Mobile Nano and is not
authority for this package.

## Current first-party evidence

Product page:
https://crimptonite.com/product/helium-mobile/

| Local evidence | Current first-party URL | Exact role | SHA-256 |
| --- | --- | --- | --- |
| `.context/pretty-impala-regenerated-gaps/inputs/helium-6543.jpg` | https://crimptonite.com/wp-content/uploads/2026/01/DSCF6543-1.jpg | Oblique current-board view: one slender board, three cavities, 22/14 mm opposing outer lips, 18/10 mm opposing center lips, end cord holes, and usable outer top surface. | `86fc66364f841ffc2256bc71fc540e846556254d2757b8618c45b4abb4db058c` |
| `.context/pretty-impala-regenerated-gaps/inputs/helium-6544.jpg` | https://crimptonite.com/wp-content/uploads/2026/01/DSCF6544-1.jpg | Straight current-board view and engraved depth mapping for the same three cavities. | `ed289d263a0116bfa8a12872dba6371b929558d8daaf26e336fc268ec4e8f89c` |
| `.context/pretty-impala-regenerated-gaps/inputs/helium-6545.jpg` | https://crimptonite.com/wp-content/uploads/2026/01/DSCF6545-1.jpg | Smooth back surface, rounded ends, and two end cord holes. | `7621b0427c279ce1bdc101814bb6a7a81edbb7a953234ce218b1e28c0931b217` |
| `.context/pretty-impala-regenerated-gaps/inputs/helium-6546.jpg` | https://crimptonite.com/wp-content/uploads/2026/01/DSCF6546-1.jpg | Current board end/profile corroboration for the 24 mm thickness and rounded outer surface. | `33de984a8bf61553e11512be67f2a062c7c05ee7aad9b394fc4c1ed5ec74915f` |

The manufacturer copy supplies the 14 mm, 22 mm, and reversible 10/18 mm
center depths, the top jug, back jug/sloper, current dimensions, and product
identity. The images freeze the three-cavity physical topology and the side on
which each contact is visible. No measurement or contact was inferred from the
generated raster.

## Accepted presentation run

The unchanged per-run record, including the exact prompts and the four
first-party input mappings, is
`.context/pretty-impala-helium-current-generation/run-data.json` (SHA-256
`1dbebf7cdec1dcc9f73d6ae7d581241828ebbeff2eb78a340beee98ee80f1ae1`).
Both outputs were accepted as opaque 3:2 catalog presentations and copied
byte-for-byte into the package:

| Presentation | Unchanged candidate and package destination | Pixels / ratio | SHA-256 |
| --- | --- | --- | --- |
| `primary` | `.context/pretty-impala-helium-current-generation/helium-mobile-primary.png` → `Hangboards/crimptonite-helium-mobile/assets/primary.png` | 1536 × 1024 / `1.5` | `681012158ff5c5b7bc162533340acedcfdfe2ddb0c237d45fe56f0173c5245bd` |
| `reverse` | `.context/pretty-impala-helium-current-generation/helium-mobile-reverse.png` → `Hangboards/crimptonite-helium-mobile/assets/reverse.png` | 1536 × 1024 / `1.5` | `7891bca6703fbbeded4505bd29ee6bd69cd9ac95d6acb15c7e4fdbc62ecccd3a` |

No crop, resize, mask, registration, segmentation, vectorization, automatic
cleanup, or other pixel postprocessing was performed. The presentation render
omits manufacturer engraving and branding as catalog styling only; the exact
contact count and layout remain those established by the current first-party
images.

## Explicitly rejected prior-revision artifacts

`DSCF6535-2.jpg` (SHA-256
`20be9e956a6a4997dcfe9846762aee27f82f6a52e2c836ebf0f1106bce4addab`)
is the previous Mobile Nano shown for comparison in the mixed gallery. Its nine
cavities and approximately 26/20/16/12/40 mm engravings do not describe the
current Helium Mobile package.

The old generation record mistakenly treated that image as Helium Mobile
authority. Its nine-cavity `primary` (`cd029cbe36412265036aa68fe7dc97df94d2cec32cf00199bc3bfa890177420b`),
paired `reverse` (`0fe539c39f5cfcd193bf4fc82c26bfd5e6eada7dd8461e729b3a082110f7ff10`),
and invented `top` (`1becb8764016341de8b3cbb937e55098b3b4c39c1d0ace76b23c5f37bf8b4d35`)
are audit-only rejected artifacts. None is a package asset or geometry source.
The unsupported `top` presentation and `assets/top.png` were removed.

## Direct manual path mapping

All canonical paths were deliberately authored against the accepted renders;
no pixels were segmented, traced, detected, registered, or vectorized. The
source establishes bilateral symmetry, so the reviewed outer-cavity geometry
is mirrored exactly.

| Stable hold ID | Presentation | Manual mapping |
| --- | --- | --- |
| `edge-22` | `primary` | Two pieces: the upper/inner opposing lip in each symmetric outer cavity. |
| `edge-14` | `primary` | Two pieces: the lower/opposing lip in each symmetric outer cavity. |
| `center-edge-18` | `primary` | The upper/inner lip of the center cavity. |
| `center-edge-10` | `primary` | The lower/opposing lip of the center cavity. |
| `top-jug` | `primary` | The continuous usable top outer band, stopping before the rounded end cord holes. |
| `back-jug-sloper` | `reverse` | The complete smooth usable wooden back face, bounded to the product and excluding the surrounding cord/background. |

Workbench review evidence is retained under
`.context/pretty-impala-helium-current-overlays/` as normal, all-active, and
hold-ID-label captures for both presentations.

