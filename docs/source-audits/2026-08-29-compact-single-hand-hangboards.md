# Compact single-hand hangboards and lifting edges: source audit

Reviewed 2026-08-29.  This is the admission record for the compact-board
import.  It is deliberately conservative: an item is included only when its
own manufacturer page identifies a current compact, one-hand portable board,
lifting edge/block, or no-hang device, and its gallery plus text identify a
reviewable physical revision.  A conventional wide board does not qualify just
because it can be loaded one arm at a time.

`Included` below is an audit gate, not a claim that package artwork or manual
paths already exist.  The linked product-page gallery is the first-party visual
evidence to inspect before drawing.  Exact source wording is retained where it
is the only safe inventory statement; no missing hold, depth, or grip posture
is inferred from a marketing photograph.

## Included product revisions

| Manufacturer | Revision to import | Primary evidence and reviewable inventory | Disposition |
| --- | --- | --- | --- |
| Nature Climbing | Stone Hanger Mini (Beech, Oak, and Smoked Oak finishes) | [product](https://natureclimbing.com/products/stone-hanger-mini-beech): 10 x 6 x 2.5 cm; 15 mm granite edge, 15 mm incut wood edge, 60 mm pinch, and smooth pull-up jug.  The three stated wood choices are explicitly the same design/performance, so they are one package. | included |
| Nature Climbing | Stone Hanger Mini x KARMA8A | [product](https://natureclimbing.com/products/mini-hanger): 10.5 x 6 x 3 cm; two 15 mm edges and a 60 mm pinch block.  This is a distinct inventory from the standard Mini and must remain a separate revision. | included |
| Lattice | Mini Bar | [2025 catalogue, p. 8](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf): expressly Lattice's *single-hand portable hangboard*, 15.5 cm long, with 10 mm and 20 mm edges, ergonomic jug, and mini pinch. | included |
| Lattice | MXEdge Lift Small | [2025 catalogue, p. 3](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf): small is a distinct SKU; MX18, MX14, MX8 and 25 mm mono. | included |
| Lattice | MXEdge Lift Large | [2025 catalogue, p. 3](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf): large is a distinct SKU; MX22, MX16, MX12 and 28 mm mono. | included |
| Plateau | Lifting Edge base kit | [product](https://www.plateauclimbing.com/products/plateau-lifting-edge): current add-to-cart compact aluminium body, 18 mm Oak-or-Pine edge, and supplied 15/10 mm blocker.  Separate aftermarket inserts only when their own current page provides a complete direct visual inventory. | included |
| Frictitious | The NUG | [product](https://frictitiousclimbing.com/products/the-nug): 130 x 60 x 40 mm; 40 mm jug, 60 mm pinch, and 8/13/20/25 mm edges. | included |
| Captain Fingerfood | POCKET (two-depth revision, including Lines cosmetic edition) | [product](https://captainfingerfood.rocks/en/products/das-hangboard-fur-die-hosentasche): 110 x 66 x 29 mm, 15/20 mm bars, their rotated two-finger uses, open/undercut pinch, and open/undercut jug. [Lines edition](https://en.captainfingerfood.rocks/products/lines-hangboard) names the same original two-depth inventory and is therefore artwork only. | included |
| Captain Fingerfood | POCKET+ | [product](https://en.captainfingerfood.rocks/Products/The-hangboard-for-your-pocket): distinct 110 x 66 x 35 mm revision with 6/10/15/20 mm bars, listed rotated two-finger uses, open/undercut pinch, and open/undercut jug. | included |
| Captain Fingerfood | UNLEVEL | [product](https://en.captainfingerfood.rocks/products/unlevel-hangboard): 12 x 7 x 3 cm, two curved rung depths (20/25 mm). | included |
| Captain Fingerfood | DUAL | [product](https://en.captainfingerfood.rocks/products/dual-hangboard): 12 x 7 x 3 cm, one straight and one curved 20 mm edge. | included |
| Aelith | Cyclops Portable Hangboard (current SKU 1001-011, Blue x Black) | [current product](https://aelithequipment.com/product/011-blue-x-black-cyclops-portable-hangboard/): product is in stock and add-to-cart. The complete selectable inventory is one 20 mm mono edge; the lanyard and carabiner hole are suspension hardware, not contacts. Other grip postures named on the page use that same mono edge and are not separate holds. | included |
| Crimptonite | Helium Mobile | [product](https://crimptonite.com/product/helium-mobile/): current portable 125 g board; 14 mm, 22 mm, 10/18 mm centre hold, top jug, and a back jug/sloper are explicitly described. | included |

### Package hand-off notes

- Do not create a second package for the Nature Mini wood choices or the
  Captain Fingerfood Lines edition.
- Each MXEdge size is a different physical inventory.  Do not merge it into a
  single size-selectable package.
- Plateau's body plus supplied edge/blocker is the included revision.  The
  product claims compatibility with inserts but does not make unnamed future
  inserts part of this audited package.

### Frozen package and physical-contact IDs

The package implementation uses the following stable IDs.  These are a direct
mapping of the inventory in the inclusion table, not additional product
claims.  A named rotated use of the same physical edge is not duplicated as a
second hold: Captain Fingerfood's two-finger uses reuse the corresponding edge,
and its open/undercut routing changes reuse the board's pinch body or outer jug
rim.  The Plateau blocker's two sourced faces remain separate contacts.

| Package slug | Board ID | Exact physical hold IDs |
| --- | --- | --- |
| `nature-stone-hanger-mini` | `nature.stone-hanger-mini` | `granite-edge-15`, `wood-edge-15-incut`, `pinch-60`, `pull-up-jug` |
| `nature-stone-hanger-mini-karma8a` | `nature.stone-hanger-mini-karma8a` | `granite-edge-15`, `wood-edge-15`, `pinch-60` |
| `lattice-mini-bar` | `lattice.mini-bar` | `edge-10`, `edge-20`, `ergonomic-jug`, `mini-pinch` |
| `lattice-mxedge-lift-small` | `lattice.mxedge-lift-small` | `edge-18`, `edge-14`, `edge-8`, `mono-25` |
| `lattice-mxedge-lift-large` | `lattice.mxedge-lift-large` | `edge-22`, `edge-16`, `edge-12`, `mono-28` |
| `plateau-lifting-edge` | `plateau.lifting-edge` | `edge-18`, `blocker-edge-15`, `blocker-edge-10` |
| `frictitious-nug` | `frictitious.nug` | `edge-8`, `edge-13`, `edge-20`, `edge-25`, `jug-40`, `pinch-60` |
| `captain-fingerfood-pocket` | `captain-fingerfood.pocket` | `edge-15`, `edge-20`, `pinch-body`, `jug-outer-rim` |
| `captain-fingerfood-pocket-plus` | `captain-fingerfood.pocket-plus` | `edge-6`, `edge-10`, `edge-15`, `edge-20`, `pinch-body`, `jug-outer-rim` |
| `captain-fingerfood-unlevel` | `captain-fingerfood.unlevel` | `curved-edge-20`, `curved-edge-25` |
| `captain-fingerfood-dual` | `captain-fingerfood.dual` | `straight-edge-20`, `curved-edge-20` |
| `aelith-cyclops-011` | `aelith.cyclops-011` | `mono-20` |
| `crimptonite-helium-mobile` | `crimptonite.helium-mobile` | `edge-14`, `edge-22`, `center-edge-10`, `center-edge-18`, `top-jug`, `back-jug-sloper` |

## Excluded candidates

| Manufacturer | Candidate / catalog result | Primary URL checked | Disposition and reason |
| --- | --- | --- | --- |
| Nature Climbing | Stone Hanger All-you-need | [bundle](https://natureclimbing.com/products/stone-hanger-all-you-need) | excluded — bundle of the deferred Stone Hanger and accessories, not a physical-board revision. |
| Nature Climbing | Raw Hanger | [product](https://natureclimbing.com/products/raw-hanger) | deferred — current first-party prose names 20/15/10/6 mm edges but only says “more than 10” grip/pinch positions. It does not freeze every visible canonical contact in a reviewable inventory, so this audit cannot safely hand it to package work. |
| Nature Climbing | Stone Hanger (Granite, Beech, and Smoked editions) | [product](https://natureclimbing.com/products/stone-hanger-1) | deferred — current first-party prose names 20/15/10/6 mm edges but only says “over 10” positions. The material/finish editions do not cure the missing frozen contact inventory. |
| Lattice | Mega Bar | [catalogue, p. 8](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf) | excluded — manufacturer explicitly calls it the two-handed counterpart to the single-hand Mini Bar. |
| Lattice | Quad Block, My Pinch, Heavy Roller, Lifting Pin, and Pin Grip | [catalogue](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf) | excluded — pinch/grip implements or loading hardware, not a compact board/lifting edge in this catalog. |
| Max Climbing | One Finger Trainer Hangboard | [product](https://www.maxclimbing.com/products/one-finger-trainer) | excluded — although marketed for one hand at a time, its stated 62 x 13 x 7 cm multi-grip board is a conventional full-width board and is outside the taxonomy. |
| Tension | Flash Board | [product](https://tensionclimbing.com/collections/hangboard-collection/products/flash-board-2) | excluded — excellent category match but manufacturer marks it “Unavailable”; no current product is admitted. |
| Tension | The Block | [product](https://tensionclimbing.com/products/the-block-2) | excluded — first-party page marks it “Unavailable.” |
| Tension | The Pod | [product](https://tensionclimbing.com/products/the-pod) | excluded — current source describes a no-hang tool, but the available primary result does not establish an in-stock product or a complete all-sides inventory. |
| Metolius | Light Rail 2.0, Rock Rings 3D, and current fixed boards | [current hangboard catalogue](https://www.metoliusclimbing.com/collections/training-boards) | excluded — no current compact single-hand product located; the previously audited Light Rail/Rock Rings are multi-surface/two-unit devices outside this import, and fixed boards are not unilateral compact boards. |
| Captain Fingerfood | 180° Hangboard | [product](https://en.captainfingerfood.rocks/products/180-hangboard) | excluded — 45 cm / about 650 g broad portable board, not a compact one-hand board under the defined distinction. |
| Captain Fingerfood | ROCKER Hangboard | [product](https://captainfingerfood.rocks/en/products/rocker-hangboard) | excluded — manufacturer calls it a two-handed mobile board. |
| Captain Fingerfood | 360° Hangboard | [product](https://captainfingerfood.rocks/en/products/hangboard-360-togo) | deferred — current product page gives dimensions and an aggregate “12 different grip options,” but does not enumerate every edge, pinch, jug, and rotated contact. A package-ready inventory would require us to invent the mapping from unsourced labels. |
| Problemsolver | Motion | [product](https://www.problemsolver.rocks/shop/problemsolver-motion) | excluded — manufacturer marks it “sold out”; no current product is admitted. |
| Problemsolver | Robot | [product](https://www.problemsolver.rocks/shop/robot) | excluded — manufacturer marks both Training and Rehab variants “sold out.” |
| Problemsolver | Griptool set, Triangle, and Monolit | [catalogue](https://www.problemsolver.rocks/hangboards) | excluded — Griptool is a pair; Triangle is a paired/ring-style system; Monolit's linked product page is unavailable.  None supplies a current qualified single-board revision. |
| Two Stones | Portable Hangboard HB2401 | [product](https://www.twostonesclimbing.com/products/portable-rock-climbing-hangboard-hb2401) | excluded — current manufacturer page says “Sold out”; it is sold as a pair, not a single compact board revision. |
| Zodiac | Dual Edge Block and variants | [product](https://zodiac-holds.com/products/no-hang-dual-edge-block) | excluded — category match, but the direct manufacturer product page is marked “Sold out”; no current product is admitted. |
| Zodiac | 22VXE and 22RXE | [22VXE](https://zodiac-holds.com/products/dual-edge-block-vxe), [22RXE](https://zodiac-holds.com/products/dual-edge-block-22rxe) | excluded — both direct manufacturer pages are marked “Sold out.” |
| AEVORN | Full-Size Grip Training Hangboard | [product](https://theaevorn.com/full-size-hangboard) | excluded — manufacturer calls it a wider two-hand platform (19.69 in), explicitly outside the category. |
| AEVORN | Portable Wooden Hangboard Block | [product](https://theaevorn.com/portable-hangboard) | deferred — primary text gives 6/15/20 mm depths but calls the rest “multiple grip orientations”; it does not enumerate which physical contacts/orientations form the complete inventory. |

## Manufacturer coverage and verification

This acceptance check is intentionally mechanical: every named manufacturer
has a disposition word and a direct primary URL.  “No current product” means
that the checked manufacturer catalogue produced no current eligible item;
`excluded` includes an unavailable or out-of-scope named candidate.

| Checked manufacturer | Disposition | Primary URL |
| --- | --- | --- |
| Nature Climbing | included | https://natureclimbing.com/collections/compact-hangboards |
| Lattice | included | https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf |
| Plateau | included | https://www.plateauclimbing.com/products/plateau-lifting-edge |
| Frictitious | included | https://frictitiousclimbing.com/products/the-nug |
| Max Climbing | excluded | https://www.maxclimbing.com/products/one-finger-trainer |
| Tension | excluded | https://tensionclimbing.com/collections/hangboard-collection/products/flash-board-2 |
| Metolius | no current product | https://www.metoliusclimbing.com/collections/training-boards |
| Captain Fingerfood | included | https://captainfingerfood.rocks/en/collections/hangboards |
| Problemsolver | no current product | https://www.problemsolver.rocks/hangboards |
| AEVORN | excluded | https://theaevorn.com/portable-hangboard |
| Aelith | included | https://aelithequipment.com/product/011-blue-x-black-cyclops-portable-hangboard/ |
| Two Stones | no current product | https://www.twostonesclimbing.com/collections/portable-hangboard |
| Zodiac | no current product | https://zodiac-holds.com/collections/training |

## Prescription audit

The search explicitly included weighted one-hand pulling/lifting-edge work.
For admission a routine must state the load, sets/repetitions, work/rest,
and laterality/order.  Mentions of weights, a product use-case, a video course,
or generic guidance do not meet that bar.

| Source and candidate | Evidence checked | Disposition |
| --- | --- | --- |
| Lattice MXEdge Lift instructions: four training sessions | [official instructions](https://latticetraining.com/app/uploads/2024/05/MXEdge-Lift-Instructions-Artwork-PRINT-READY-28-03-24-PDF.pdf) specify 30% max: 5 x (18 x 7 s work/3 s rest), 4 min between sets; 50%: 6 x (12 x 7:3), 4 min; 70%: 6 x (5 x 7:3), 3 min; and 85%: 6 x (1 x 10 s), 2 min. | excluded — no side order/laterality is prescribed for those sessions, so an app routine would fabricate it. |
| Lattice MXEdge Lift max-load test | [official instructions](https://latticetraining.com/app/uploads/2024/05/MXEdge-Lift-Instructions-Artwork-PRINT-READY-28-03-24-PDF.pdf) says up to eight progressively heavier 7 s lifts on each arm, alternating every 90 s, 3 min between repeats on the same arm, with increments up to 2 kg. | excluded — first side and exact starting load are deliberately user-selected; it is a self-assessment, not a fully ordered reproducible timer prescription. |
| Lattice historical My Pinch/edge test instructions | [official instructions](https://latticetraining.com/app/uploads/2022/04/105x115mm-Instructions.pdf) gives the same 7 s/max-eight/alternating structure and example increments. | excluded — this is a test for a different grip block and also leaves starting side/load user-selected. |
| Frictitious NUG / Progression Lab link | [product](https://frictitiousclimbing.com/products/the-nug) links to resources and says the NUG can attach to weights, a foot, or Tindeq. | excluded — the product page does not state a complete prescription. |
| Captain Fingerfood Fingerkraft Stunde Null | [course page](https://captainfingerfood.rocks/products/fingerkraft-stunde-null) identifies equipment and that course/download materials exist. | excluded — no complete runner-visible sequence is published on the primary page. |
| AEVORN training library | [training page](https://theaevorn.com/training) has beginner/intermediate/pro prose. | excluded — it omits loads, set/repetition counts, timed work/rest, and side order. |
| Tension, Nature, Plateau, Max, Aelith, Crimptonite, Problemsolver, Two Stones, Zodiac, and Metolius product/catalog pages | Product/catalogue URLs above were checked for a complete weighted unilateral prescription. | excluded — no publicly stated complete prescription found. |

**Routine result: no training plan is admitted in this task.**  Task 3 must add
no plan seed or test unless a later first-party source fills every missing field
without adaptation.

## Sources checked

All URLs in the inclusion, exclusion, coverage, and prescription tables were
checked.  The following primary catalogue/index pages were additionally used
to ensure the review did not depend on a retailer or search-result claim:

- https://natureclimbing.com/collections/mini-hangboards
- https://www.plateauclimbing.com/collections/all
- https://frictitiousclimbing.com/en-ca/products/the-nug
- https://www.maxclimbing.com/collections/all-training-products
- https://tensionclimbing.com/pages/hangboards
- https://captainfingerfood.rocks/en/collections/hangboards
- https://www.problemsolver.rocks/hangboards
- https://theaevorn.com/
- https://aelithequipment.com/
- https://www.twostonesclimbing.com/collections/all
- https://zodiac-holds.com/
- https://crimptonite.com/product/helium-mobile/

## Verification

Run from the repository root:

```sh
test -f docs/source-audits/2026-08-29-compact-single-hand-hangboards.md
rg -n 'Nature Climbing|Lattice|Plateau|Frictitious|Max Climbing|Tension|Metolius|Captain Fingerfood|Problemsolver|AEVORN|Aelith|Two Stones|Zodiac' docs/source-audits/2026-08-29-compact-single-hand-hangboards.md
```

Expected: the first command exits `0`; the second returns at least the thirteen
coverage rows above, each with a disposition and direct primary URL.

### Recorded command results

Before this file was created, `test -f docs/source-audits/2026-08-29-compact-single-hand-hangboards.md` exited `1`, as required by the acceptance test.  The final commands and their actual output are recorded in the task report.
