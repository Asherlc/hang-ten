# All-board metadata and physical-hold audit

**Checked:** 2026-08-19  
**Scope:** all 34 direct-child `Hangboards/*/board.json` packages present on the
checked date.

This audit is the release gate for the board library. A package may remain
discoverable only when its product identity and complete physical-hold inventory
can be tied to current manufacturer evidence (with a clearly limited secondary
source only where noted). A source may support a product-level fact without
supporting a per-hold mapping; this audit does not promote such a fact into
individual hold metadata.

The 2026-08-19 audit superseded earlier readiness conclusions where the
single-file schema made optional metadata omissible. Omitting an unsupported
optional field is necessary, but it does not make an incomplete, grouped, or
invented physical-hold map shippable. Seven packages were corrected and
retained. The 27 incomplete generated drafts were subsequently removed in full;
they are not inputs to future work. Their manufacturer research remains below
for reuse when each complete package is directly authored from primary evidence
under `docs/ADDING_A_BOARD.md`.

## Retain after correction

### `beastmaker-1000`

- **Sources:** [Beastmaker 1000 Series](https://www.beastmaker.co.uk/products/beastmaker-1000-series);
  [Beastmaker FAQ](https://www.beastmaker.co.uk/pages/faq);
  [Beech variant](https://www.beastmaker.co.uk/products/beastmaker-1000-beech)
  (cross-variant corroboration for the 58 mm depth only).
- **Current JSON holds:** 22.
- **Source-backed expected physical count:** 22.
- **Verified facts:** generic/Tulipwood Beastmaker 1000; `580 × 150 × 58 mm`.
  The separate Beech page corroborates only the shared 58 mm depth, not this
  package's product identity.
- **Discrepancy:** the physical-region count is aligned, but current per-pocket
  millimetre fields are not mapped one-to-one by the manufacturer.
- **Action:** `correct` — retain the 22 regions and omit those unsupported
  per-pocket measurements.

### `beastmaker-2000`

- **Source:** [Beastmaker 2000 Series](https://www.beastmaker.co.uk/products/beastmaker-2000-series).
- **Current JSON holds:** 25.
- **Source-backed expected physical count:** 25.
- **Verified facts:** Beastmaker 2000; `580 × 150 × 58 mm`. The grouped source
  inventory supports hold kinds; the clearly central lower edge is the official
  22 mm middle edge.
- **Discrepancy:** current image-derived millimetre values are not mapped
  one-to-one by the manufacturer.
- **Action:** `correct` — retain 25 regions, preserve only the clearly mapped
  22 mm fact, and remove unsupported derived values.

### `dewoodstok-woodbord`

- **Source:** [deWoodstok Woodbord](https://www.dewoodstok.nl/product/hangboard-woodbord/).
- **Current JSON holds:** 17.
- **Source-backed expected physical count:** 17.
- **Verified facts:** deWoodstok Woodbord; `590 × 148 × 40 mm`; solid,
  certified bamboo. The source does not support the more specific
  `FSC-certified` wording.
- **Discrepancy:** the hold inventory is aligned, but the material certification
  wording overstates the source.
- **Action:** `correct` — retain 17 regions and use only the source-backed
  bamboo wording.

### `escape-beta-22`

- **Sources:** [Escape Beta Board](https://escapeclimbing.com/products/ec72100);
  [Beta Board review](https://strengthclimbing.com/beta-board-from-escape-climbing-hangboard-review/)
  (used only for its enumerated hold-family/depth description).
- **Current JSON holds:** 22 logical holds / 22 geometry pieces.
- **Source-backed expected physical count:** 19.
- **Verified facts:** Escape Beta Board; official identity, dimensions, and
  dual texture are current. The limited secondary source conflicts internally
  on the smallest central sloper-edge depth: its section header says `11 mm`,
  while the body says `1/2 in`.
- **Discrepancy:** three continuous central cavities were split into left/right
  logical holds, yielding 22 holds rather than 19 physical regions.
- **Action:** `correct` — combine each central pair into one hold with two
  geometry pieces; retain the 22 total pieces, name `hold-11-center` without a
  numeric depth, and omit its exact `sizeMillimeters` value.

### `evolv-kilter-basic-long`

- **Source:** [Evolv Basic Training Board (Long)](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105).
- **Current JSON holds:** 4.
- **Source-backed expected physical count:** 4.
- **Verified facts:** Evolv **Basic Training Board (Long)**, a Kilter
  collaboration; resin; `79cm × 16cm × 6cm`; one rounded jug followed by
  rounded 20, 15, and 10 mm edges.
- **Discrepancy:** current manufacturer/name, dimensions, and row taxonomy are
  stale or generic.
- **Action:** `correct` — retain four rows and map them in official top-to-bottom
  order.

### `lattice-triple-rung`

- **Source:** [Lattice Triple Rung Wooden Hangboard](https://latticetraining.com/product/triple-rung-wooden-hangboard/).
- **Current JSON holds:** 3.
- **Source-backed expected physical count:** 3.
- **Verified facts:** Lattice Triple Rung; `55 × 13 × 5 cm`. The product allows
  arbitrary hand width and finger selection.
- **Discrepancy:** a fixed `fingerCapacity: 4` claims a constraint that the
  source expressly does not establish.
- **Action:** `correct` — retain the three edges and omit fixed capacity and
  other derived tags.

### `metolius-wood-grips-compact-ii`

- **Sources:** [Metolius Wood Grips II Training Boards](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards);
  [official depth image](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg).
- **Current JSON holds:** 19.
- **Source-backed expected physical count:** 19.
- **Verified facts:** Metolius Wood Grips Compact II; `24” × 6.2”`; FSC
  certification. The source supports the current 56/29/19 mm mapping and the
  visible hold kinds and cavity capacities.
- **Discrepancy:** inventory, mapped depths, visible kinds, and capacities are
  sound. Generic `gripType` posture prescriptions for jugs, edges, and slopers
  are not established by the manufacturer sources and remain omitted.
- **Action:** `correct` — retain all 19 distinct regions, including separate
  side rails, use the factual `FSC-certified wood training board` subtitle,
  and retain the sourced kind/depth/capacity facts. Pocket-only
  `twoFingerPocket`, `threeFingerPocket`, and `fourFingerPocket` grip semantics
  are retained because they are a structural one-to-one encoding of each
  source-backed visible pocket capacity and preserve custom-routine semantics;
  they are not manufacturer coaching prescriptions. The `features` arrays are
  app semantic-routing adaptations derived from those sourced or visible hold
  kinds, sizes, and shapes; they are not manufacturer claims or grip
  prescriptions. In particular, each 19 mm edge maps to both `mediumEdge` and
  `smallEdge` target classes for app compatibility. This follows the Compact II
  target-mapping treatment documented in the
  [plan cue provenance audit](2026-08-10-plan-cue-provenance.md), which labels
  those board targets as app choices/adaptations.

## Removed incomplete packages awaiting direct authoring

The incomplete package directories and their presentation assets were removed.
“Unknown” below is deliberate: it means the cited sources did not establish a
count that could be mapped safely to the old records. A future package must be
created complete, with its geometry directly authored and visually reviewed;
none of the removed art may be restored as a starting point.

### `escape-beta`

- **Source:** [Escape Beta Board](https://escapeclimbing.com/products/ec72100).
- **Current JSON holds:** 6.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** current official identity is Escape Beta Board; no
  historical-variant dimensions or material are established here.
- **Discrepancy:** stale URL/name and an incompatible layout prevent a safe
  mapping.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `escape-unlimited`

- **Source:** [Escape Unlimited](https://escapeclimbing.com/products/ec72000).
- **Current JSON holds:** 6.
- **Source-backed expected physical count:** 6.
- **Verified facts:** current Escape Unlimited product; current URL and
  dimensions in JSON are not supported by the cited source.
- **Discrepancy:** unsupported dimensions and no defensible tier-to-record
  mapping.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `frictitious-doormount-pro-7`

- **Sources:** [Frictitious Doormount Pro](https://frictitiousclimbing.com/en-ca/products/doormount-pro);
  [doorway collection](https://frictitiousclimbing.com/collections/doorway-mount-and-accessories).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** 7.
- **Verified facts:** current Frictitious Doormount Pro identity;
  `25.5 × 4.5 × 2.25 in`; poplar wood hangboard with aluminum and steel mounting
  components.
- **Discrepancy:** the current grouping cannot be mapped to the official seven
  holds.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `frictitious-megalith`

- **Source:** [Frictitious Megalith](https://frictitiousclimbing.com/products/megalith).
- **Current JSON holds:** 9.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** current Frictitious Megalith identity;
  `26.75 × 6.5 × 2.25 in`; poplar.
- **Discrepancy:** the source establishes at least 10 functional targets (seven
  edge sizes, centre hold, full-width jug, and pocket targets), so the official
  exact physical count is unknown; current JSON under-models that inventory and
  has wrong dimensions.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `metolius-climbers-edge`

- **Source:** [Metolius Climber’s Edge Board](https://www.metoliusclimbing.com/products/climbers-edge-board).
- **Current JSON holds:** 11.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Metolius Climber’s Edge; `23.6” × 6.3”`; material is not
  established here.
- **Discrepancy:** the source shows at least 14 features (ten edge slots,
  round/flat slopers, and plural jugs), but does not establish an exact physical
  count; current JSON misses features and has wrong dimensions and a stale URL.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `metolius-contact`

- **Sources:** [Metolius Contact Training Board](https://www.metoliusclimbing.com/products/contact-training-board);
  [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide).
- **Current JSON holds:** 10.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Metolius Contact; `32.5” × 11” × 2.625”`; material is not
  established here.
- **Discrepancy:** the official guide documents 18 numbered positions, rather
  than an exact physical-region count; current JSON misses jugs, slopers, and
  pinches, and its dimensions and URL are stale.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `metolius-project`

- **Source:** [Metolius Project Training Board](https://www.metoliusclimbing.com/products/project-training-board).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Metolius Project; `24.5” × 6”`; material is not
  established here.
- **Discrepancy:** approximately 10 regions are visible, including two small
  centre-adjacent pockets absent from JSON; that observation is not an exact
  count, and dimensions and URL are stale.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `metolius-simulator-3d`

- **Sources:** [Metolius Simulator Training Board](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board);
  [Simulator 3-D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Metolius Simulator 3-D; `28” × 8.75”`; material is not
  established here.
- **Discrepancy:** the official guide documents 18 numbered positions, rather
  than an exact physical-region count; the current inventory is materially
  grouped/omitted and dimensions are wrong.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `moon-armstrong`

- **Sources:** [Moon Armstrong Fingerboard](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html);
  [Moon Armstrong product note](https://moonclimbing.com/News/post/the-moon-armstrong-fingerboard).
- **Current JSON holds:** 11.
- **Source-backed expected physical count:** 19.
- **Verified facts:** Moon Armstrong Fingerboard Beech; `65 × 16.5 × 5.5 cm`.
- **Discrepancy:** invented three-finger pockets and missing jugs, slopers,
  monos, and centre edges; dimensions and URL are stale.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `nature-stoak-board-iii`

- **Source:** [Nature Stoak Board III](https://natureclimbing.com/products/stoak-board-iii).
- **Current JSON holds:** 6.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Nature Stoak Board III; official edge is 22 mm;
  `57 × 12 × 5.5 cm`; FSC-certified oak or beech with granite.
- **Discrepancy:** at least eight cavities (and nine semantic contacts) are
  visible, but that is not an exact physical count; the current grouped and
  incomplete hold map omits top rails and mis-maps the centre jug.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `soill-iron-palm-2`

- **Source:** [So iLL Iron Palm 2.0](https://soillholds.com/products/iron-palm-2-0).
- **Current JSON holds:** 6.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** current So iLL Iron Palm 2.0 identity; dimensions and
  material are not established here.
- **Discrepancy:** roughly 10 targets are visible, but no exact count is
  evidenced; slopers and pinches are missing, identity/URL are stale, and
  dimensions are unsupported.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `soill-split-palm`

- **Source:** [So iLL Split Palm](https://soillholds.com/products/split-palm).
- **Current JSON holds:** 2.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** current So iLL Split Palm identity; dimensions and
  material are not established here.
- **Discrepancy:** at least 12 regions are visible, but no exact count is
  evidenced; JSON is severely under-modeled.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `soill-training-tiles`

- **Sources:** [So iLL x Meagan Martin Training Tiles](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin);
  [Training Tiles workouts](https://soillholds.com/pages/meagan-martin-training-tiles-workouts).
- **Current JSON holds:** 4.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** So iLL x Meagan Martin Training Tiles; dimensions and
  material are not established here.
- **Discrepancy:** roughly 10 regions are visible, but no exact count is
  evidenced; JSON is severely under-modeled with stale identity/URL.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `target10a-linebreaker-base`

- **Sources:** [Target10a product archive](https://www.target10a.com/magazin/category/produkte/);
  [Linebreaker Base review](https://chalkr.de/linebreaker-base-trainingsboard.html)
  (used only for visible-inventory corroboration).
- **Current JSON holds:** 11.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Target10a Linebreaker Base; `58 × 15 × 5.5 cm`; material
  is not established here.
- **Discrepancy:** at least 19 recesses plus sloper surfaces are visible, but no
  exact count is evidenced; grouped pockets are false, top holds are
  misclassified as edges, and the inventory is incomplete.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `tension-grindstone`

- **Sources:** [Tension Grindstone](https://tensionclimbing.com/products/grindstone);
  [Tension hangboards](https://tensionclimbing.com/pages/hangboards).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Tension Grindstone; `22” × 6” × 2.75”`.
- **Discrepancy:** the official material establishes a full-width top jug and a
  50 mm one-arm edge, but not a one-to-one mapping for the seven grouped
  records; a nonexistent centre jug replaces that edge, so this needs
  reauthoring, not relabeling.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `tension-honestone`

- **Source:** [Tension hangboards](https://tensionclimbing.com/pages/hangboards).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 9.
- **Verified facts:** Tension Honestone; `25” × 6” × 2.5”`.
- **Discrepancy:** end pockets are 25 mm monos, the centre is a 25 mm incut
  edge, and two top slopers are missing.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `tension-whetstone`

- **Source:** [Tension hangboards](https://tensionclimbing.com/pages/hangboards).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 8.
- **Verified facts:** Tension Whetstone; `25” × 6” × 2”`.
- **Discrepancy:** end pockets are 40 mm two-finger pockets, the centre is a
  40 mm incut edge, and the top ergo-bump jug is missing.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `trango-rock-prodigy-forge`

- **Source:** [Trango Rock Prodigy Forge](https://trango.com/products/rock-prodigy-forge).
- **Current JSON holds:** 12.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Trango Rock Prodigy Forge; lower rails are 7.5 mm closed
  crimps, top rails vary 7–20 mm, and pinch blocks have three depths.
- **Discrepancy:** current JSON has 12 broad groups, while the official depth
  groups cannot be mapped one-to-one; those broad groups collapse source-backed
  physical depth targets and semantics.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `trango-rock-prodigy-natural`

- **Source:** [Trango Rock Prodigy Natural](https://trango.com/products/rock-prodigy-natural).
- **Current JSON holds:** 12.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Trango Rock Prodigy Natural; each half is
  `7.5” × 6” × 1.5”`.
- **Discrepancy:** 12 current groups cannot safely be reconciled with the
  official narrower pocket semantics; dimensions are wrong and those semantics
  are too broad.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `trango-rock-prodigy-pivot`

- **Source:** [Trango Rock Prodigy Pivot](https://trango.com/products/rock-prodigy-pivot).
- **Current JSON holds:** 10.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Trango Rock Prodigy Pivot identity; dimensions/material
  are not established here.
- **Discrepancy:** the documentation lists 22 grip positions, not an exact
  physical-region count; dimensions are unsupported and orientations collapsed.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `trango-rock-prodigy-training-center`

- **Sources:** [Trango Rock Prodigy Training Center](https://trango.com/products/rock-prodigy-training-center);
  [RPTC use instructions (PDF)](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155).
- **Current JSON holds:** 24 logical holds / 28 geometry pieces.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Trango Rock Prodigy Training Center identity; exact
  finger-pair labels in JSON are not supported.
- **Discrepancy:** official material exposes more than 30 grip positions, not
  an exact physical-region count; current inventory is short of those positions
  and asserts unsupported exact finger-pair labels. Earlier source audit records
  this blocker.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `yy-verticalboard-evo`

- **Sources:** [YY Vertical VerticalBoard Evo](https://www.yyvertical.com/products/verticalboard-evo);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 19.
- **Verified facts:** YY Vertical VerticalBoard Evo; `65 × 14 × 5.5 cm`.
- **Discrepancy:** false symmetric/three-finger mapping and wrong dimensions.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `yy-verticalboard-first`

- **Sources:** [YY Vertical VerticalBoard First](https://www.yyvertical.com/products/verticalboard-first);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 10.
- **Verified facts:** YY Vertical VerticalBoard First; `54 × 13 × 5 cm`; no
  centre jug or pockets.
- **Discrepancy:** current centre jug/pockets are fictitious and dimensions are
  wrong.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `yy-verticalboard-light`

- **Sources:** [YY Vertical VerticalBoard Light](https://www.yyvertical.com/products/verticalboard-light);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 7.
- **Verified facts:** YY Vertical VerticalBoard Light; `54 × 9 × 5 cm`; no
  centre jug.
- **Discrepancy:** the current centre jug is fictitious despite a matching
  count; dimensions are wrong.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `yy-verticalboard-one`

- **Sources:** [YY Vertical VerticalBoard One](https://www.yyvertical.com/en/products/verticalboard-one);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 15.
- **Verified facts:** YY Vertical VerticalBoard One; `62 × 13 × 5.5 cm`.
- **Discrepancy:** false pockets/centre jug, wrong dimensions, and stale URL.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `zlagboard-evo`

- **Sources:** [Zlagboard hangboards](https://zlagboard.com/hangboards);
  [Vertical-Life Zlagboard Evo listing](https://shop.vertical-life.info/it/zlagboard-evo-incl.-piano-di-allenamento-di-6-mesi)
  (used only as limited secondary corroboration).
- **Current JSON holds:** 14.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Zlagboard Evo identity; official text includes jugs and
  slopers absent from JSON. Dimensions/material are unsupported or conflicting.
- **Discrepancy:** stale URL, missing source-described kinds, and no defensible
  complete inventory.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

### `zlagboard-pro`

- **Source:** [Zlagboard hangboards](https://zlagboard.com/hangboards).
- **Current JSON holds:** 21.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Zlagboard Pro identity; dimensions/material are not
  established here.
- **Discrepancy:** stale URL and unsupported dimensions; the apparent count is
  not sufficient evidence for the physical map.
- **Action:** removed incomplete package; directly author a complete replacement from the cited primary evidence.

## Decision summary

| decision | packages |
| --- | ---: |
| `correct` and retain as complete packages | 7 |
| removed incomplete package awaiting direct authoring | 27 |
| total audited package slugs | 34 |

Adding any removed model requires a complete source-backed physical inventory,
direct manual path authoring, current package validation, and human visual
review under `docs/ADDING_A_BOARD.md`.
