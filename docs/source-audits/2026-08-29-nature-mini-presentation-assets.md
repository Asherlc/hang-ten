# Nature Stone Hanger Mini presentation assets — source audit

Reviewed 2026-08-29. This audit covers only the final presentation assets and
manual canonical-geometry mappings for `nature-stone-hanger-mini` and
`nature-stone-hanger-mini-karma8a`.

## Frozen product identity and inventory

The current [Stone Hanger Mini product page](https://natureclimbing.com/products/stone-hanger-mini-beech)
states the standard Mini's `10 × 6 × 2.5 cm` dimensions and its 15 mm granite
edge, 15 mm incut wood edge, 60 mm pinch, and smooth pull-up jug. The current
[Stone Hanger Mini x KARMA8A product page](https://natureclimbing.com/products/mini-hanger)
states that distinct revision's `10.5 × 6 × 3 cm` dimensions, two 15 mm edges,
and 60 mm pinch block. This change preserves the stable inventories and IDs
already frozen in
`docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`; it adds no
measurement, contact, or training claim.

## Exact first-party evidence

Every manufacturer image below was downloaded unchanged and is retained under
`.context/pretty-impala-official-asset-sources/candidates/`. These images are
physical-identity and contact-layout evidence; the generated presentation
rasters are not source evidence.

| Revision / view | Exact manufacturer URL | SHA-256 | Dimensions | Evidence role |
| --- | --- | --- | --- | --- |
| Standard Mini front | [Beechminihanger1.png](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Beechminihanger1.png?v=1774526917) | `5bde3f95ced551ba5980deb44222f80b5ddcffd480f71a2c6ca272837b299423` | 3500 × 3500 | Exact first-party front construction, pale-beech finish, stone contacts, and black/yellow cord. |
| Standard Mini broad back | [Beechminihanger2.png](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Beechminihanger2.png?v=1774526917) | `1d851162a1aedce8fb08ba56f38b0c7cd9e67a297fcd2deee8145787554d066d` | 3500 × 3500 | Corroborates the exterior body, but is not the final narrow side view. |
| Standard Mini narrow lateral/end | [Beechminihanger3.png](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Beechminihanger3.png?v=1774526917) | `d71d396bf3611aee1a90a33209e56b83a8b14a3e4a8adb1f9c8043e366765f33` | 3500 × 3500 | Exact first-party authority for body thickness, side silhouette, routed cord channels, and the side-visible pinch surface. |
| KARMA8A front | [Untitled_design_a3abac48-3dbc-4913-bc3e-15c8b2a9e85d.png](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Untitled_design_a3abac48-3dbc-4913-bc3e-15c8b2a9e85d.png?v=1774607004) | `3267c96f30e9576b1b66f769d83722cac6c55322c9ad6491cda82ea3910f7743` | 3500 × 3500 | Exact first-party front construction, smoked-oak finish, purple cord, two edge strips, and complete visible outer body. |
| KARMA8A broad back | [Untitled_design_1.png](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Untitled_design_1.png?v=1774607067) | `412059dc91cb4b564d450b4065fdf467618d1d981c9568cb5346983ae7653de0` | 3500 × 3500 | First-party reverse corroboration only; it is not a lateral/end view. |

The exact URL, downloaded path, dimensions, hash, and view classification are
also recorded in
`.context/pretty-impala-official-asset-sources/official-asset-source-manifest.json`.

## Presentation-generation contract and byte-for-byte integration

The original generation batches used one generic product-mockup prompt
template for all products, with only literal per-run data and source inputs
changing. A later source-faithful material-correction contract retained the
accepted front framing and topology while making the exact first-party image
the physical and material authority. The contracts prohibit crop, resize,
masking, segmentation, registration, vectorization, automatic cleanup, and
manual pixel editing:

- `.context/pretty-impala-generated-lattice-nature/contract.json` and
  `run-data.json` produced the two superseded front candidates used only as
  framing and topology inputs for the final correction.
- `.context/pretty-impala-nature-material-correction/run-data.json` records the
  correction contract, exact per-run inputs, prompts, dimensions, and hashes
  for both accepted fronts.
- `.context/pretty-impala-corrected-visuals/contract.json` and `run-data.json`
  produced the accepted standard Mini narrow side candidate from the exact
  first-party `Beechminihanger3.png` lateral authority.
- `Hangboards/frictitious-megalith/assets/primary.png`, SHA-256
  `6b084b279b2600b15bafb7db6dddcc0ba9ecd2abe4ca480daf3dded7b9f4356f`,
  supplied framing/style only and was never geometry or product evidence.

| Final package / presentation | Accepted candidate copied unchanged | Candidate and tracked SHA-256 | Pixels |
| --- | --- | --- | --- |
| Standard Mini `primary` | `.context/pretty-impala-nature-material-correction/nature-stone-hanger-mini-primary.png` | `013dd268460505601788c6166cba407f02e51262aae0e93de41627ecd1e4f96e` | 1254 × 1254 |
| Standard Mini `side` | `.context/pretty-impala-corrected-visuals/outputs/nature-stone-hanger-mini-side-attempt-1.png` | `9883d48087783386f3791a3dd90d2c0e0f30ff9bea97b9f123d36391418cc40d` | 1254 × 1254 |
| KARMA8A `primary` | `.context/pretty-impala-nature-material-correction/nature-stone-hanger-mini-karma8a-primary.png` | `84942ffd74c854a665a01ca74ddef75a1ca9d453dac9d6416bd4120f6cba2868` | 1254 × 1254 |

Each accepted PNG was copied byte-for-byte to its declared package asset. No
decode/re-encode, crop, resize, retouch, compositing, masking, or other
postprocessing occurred. All final rasters are square, so both board-level and
presentation-level aspect ratios are `1.0`.

Any earlier candidate-review wording that described the original fronts as
accepted is superseded by the exact first-party material comparison in this
audit. The old Standard Mini front at SHA-256
`7174203d48811a03d583ea989a0aa6e6f6a2f22db10c21fbe1bc30fbaa7d3df3`
is rejected because both lower contacts read as separate stone inserts instead
of one integral pale-beech ledge above one granite edge. The old KARMA8A front
at SHA-256
`4064b3350b56f36b127293761143998865f20486361ab39fbdfc6c135502557a`
is rejected because its body reads as light wood instead of source-established
dark smoked oak and its upper contact does not read as an integral smoked-oak
ledge. Neither superseded front may be reused as a final presentation asset.

Both KARMA8A side candidates remain rejected: the generated lattice batch's
candidate is a broad blank back rather than the declared lateral `Side`, while
the corrected batch extrapolates an unseen KARMA8A lateral view from the
standard Mini family. The KARMA8A side presentation and asset are therefore
removed. Its `pinch-60` remains source-visible and is mapped to the complete
outer smoked-oak body on the accepted front.

## Manual canonical-geometry mappings

An operator deliberately re-authored every saved path against the exact final
presentation pixels. No coordinate, contour, mask, segmentation, detection,
alignment, vectorization, or generated-geometry workflow was used. The paths
remain the sole rendering, highlighting, and hit-testing source of truth.

- Standard Mini `primary`: `pull-up-jug` follows the broad wood recess;
  `wood-edge-15-incut` follows the integral pale-beech ledge immediately above
  the granite; and `granite-edge-15` follows the single rough gray granite
  strip.
- Standard Mini `side`: `pinch-60` follows the complete narrow wooden body
  silhouette established by the exact first-party lateral/end evidence. The
  overlying suspension cord and routed cord channels are not extra contacts.
- KARMA8A `primary`: `wood-edge-15` follows the integral dark smoked-oak ledge,
  and `granite-edge-15` follows the single rough gray granite strip. The four
  deliberately separate geometry pieces of `pinch-60` follow the complete
  visible top, left, right, and lower smoked-oak exterior while excluding the
  recess, both edge strips, and side cord openings; they remain one physical
  pinch contact.

## Review evidence

Owned headless Workbench captures for both corrected fronts and the unchanged
accepted standard side are stored under
`.context/pretty-impala-nature-material-fix-overlays/` in normal, all-active,
and hold-ID-label states. The capture workflow owns and terminates its exact
loopback Workbench server, headless Chrome process, and temporary profile.
