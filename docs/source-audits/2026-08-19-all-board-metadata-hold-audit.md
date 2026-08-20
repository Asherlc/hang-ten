# All-board metadata and physical-hold audit

**Checked:** 2026-08-19  
**Scope:** all 33 direct-child `Hangboards/*/board.json` packages in the final
catalog.

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
retained. The 27 incomplete generated drafts were subsequently removed in full
and were not used as authoring inputs. Twenty-six models were later rebuilt as
complete direct-authored packages under `docs/ADDING_A_BOARD.md`; the stale
duplicate `escape-beta` candidate was not recreated because `escape-beta-22`
is the supported Beta Board package.

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
- **Current JSON holds:** 19 logical holds / 22 geometry pieces.
- **Source-backed expected physical count:** 19.
- **Verified facts:** Escape Beta Board; official identity, dimensions, and
  dual texture are current. The limited secondary source conflicts internally
  on the smallest central sloper-edge depth: its section header says `11 mm`,
  while the body says `1/2 in`.
- **Discrepancy:** resolved; the three continuous central cavities are one
  logical hold apiece with two geometry pieces.
- **Action:** `correct` — retained 19 physical contacts / 22 pieces, named
  `hold-11-center` without a numeric depth, and omitted its conflicted exact
  `sizeMillimeters` value.

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

## Direct-authored replacements and excluded duplicate

The former incomplete directories and presentation assets remained removed.
Every replacement below was authored from current product-specific evidence;
none of the removed art or geometry was restored as a starting point.

### `escape-beta`

- **Source:** [Escape Beta Board](https://escapeclimbing.com/products/ec72100).
- **Current JSON holds:** none; this duplicate slug is absent from the catalog.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** current official identity is Escape Beta Board; no
  historical-variant dimensions or material are established here.
- **Discrepancy:** stale URL/name and an incompatible layout prevent a safe
  mapping.
- **Action:** excluded; `escape-beta-22` is the supported Beta Board package.

### `escape-unlimited`

- **Source:** [Escape Unlimited](https://escapeclimbing.com/products/ec72000).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 7.
- **Verified facts:** current Escape Unlimited product; `23.5 × 6 in`; one
  continuous top sloper and three mirrored edge rows.
- **Discrepancy:** resolved; all seven continuous contacts are represented once.
- **Action:** directly authored and visually reviewed; retain as complete.

### `frictitious-doormount-pro-7`

- **Sources:** [Frictitious Doormount Pro](https://frictitiousclimbing.com/en-ca/products/doormount-pro);
  [doorway collection](https://frictitiousclimbing.com/collections/doorway-mount-and-accessories).
- **Current JSON holds:** 7.
- **Source-backed expected physical count:** 7.
- **Verified facts:** current Frictitious Doormount Pro identity;
  `25.5 × 4.5 × 2.25 in`; poplar wood hangboard with aluminum and steel mounting
  components.
- **Discrepancy:** resolved; the replacement maps the seven official continuous
  contacts without duplicating the mounting hardware as board holds.
- **Action:** directly authored and visually reviewed; retain as complete.

### `frictitious-megalith`

- **Source:** [Frictitious Megalith](https://frictitiousclimbing.com/products/megalith).
- **Current JSON holds:** 10.
- **Source-backed expected physical count:** 10.
- **Verified facts:** current Frictitious Megalith identity;
  `26.75 × 6.5 × 2.25 in`; poplar.
- **Discrepancy:** resolved; the replacement maps the full-width jug, seven edge
  targets, and two pocket/mono targets as ten physical contacts.
- **Action:** directly authored and visually reviewed; retain as complete.

### `metolius-climbers-edge`

- **Source:** [Metolius Climber’s Edge Board](https://www.metoliusclimbing.com/products/climbers-edge-board).
- **Current JSON holds:** 15.
- **Source-backed expected physical count:** 15.
- **Verified facts:** Metolius Climber’s Edge; `23.6” × 6.3”`; material is not
  established here.
- **Discrepancy:** resolved; the replacement maps ten edge slots, two slopers,
  and three continuous jug contacts.
- **Action:** directly authored and visually reviewed; retain as complete.

### `metolius-contact`

- **Sources:** [Metolius Contact Training Board](https://www.metoliusclimbing.com/products/contact-training-board);
  [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide).
- **Current JSON holds:** 33.
- **Source-backed expected physical count:** 33.
- **Verified facts:** Metolius Contact; `32.5” × 11” × 2.625”`; material is not
  established here.
- **Discrepancy:** resolved by reconciling every distinct visible contact with
  the official front and oblique views; the 18 training-guide positions are not
  misused as the physical-region count.
- **Action:** directly authored and visually reviewed; retain as complete.

### `metolius-project`

- **Source:** [Metolius Project Training Board](https://www.metoliusclimbing.com/products/project-training-board).
- **Current JSON holds:** 17.
- **Source-backed expected physical count:** 17.
- **Verified facts:** Metolius Project; `24.5” × 6”`; material is not
  established here.
- **Discrepancy:** resolved; the current package maps all visible symmetric
  jugs, slopers, pockets, and edges in the official product views.
- **Action:** directly authored and visually reviewed; retain as complete.

### `metolius-simulator-3d`

- **Sources:** [Metolius Simulator Training Board](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board);
  [Simulator 3-D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide).
- **Current JSON holds:** 31.
- **Source-backed expected physical count:** 31.
- **Verified facts:** Metolius Simulator 3-D; `28” × 8.75”`; material is not
  established here.
- **Discrepancy:** resolved by mapping every distinct visible contact; the 18
  training-guide positions remain usage positions rather than a physical count.
- **Action:** directly authored and visually reviewed; retain as complete.

### `moon-armstrong`

- **Sources:** [Moon Armstrong Fingerboard](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html);
  [Moon Armstrong product note](https://moonclimbing.com/News/post/the-moon-armstrong-fingerboard).
- **Current JSON holds:** 21.
- **Source-backed expected physical count:** 21.
- **Verified facts:** Moon Armstrong Fingerboard Beech; `65 × 16.5 × 5.5 cm`.
- **Discrepancy:** resolved; the replacement now maps all 21 source-backed
  physical contacts with current dimensions and URL.
- **Action:** directly authored and reviewed a complete replacement from the cited primary evidence.

### `nature-stoak-board-iii`

- **Source:** [Nature Stoak Board III](https://natureclimbing.com/products/stoak-board-iii).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** 8.
- **Verified facts:** Nature Stoak Board III; official edge is 22 mm;
  `57 × 12 × 5.5 cm`; FSC-certified oak or beech with granite.
- **Discrepancy:** resolved; the replacement maps eight continuous physical
  contacts, including the top and gradient rails and the centre contacts.
- **Action:** directly authored and reviewed a complete replacement from the cited primary evidence.

### `soill-iron-palm-2`

- **Source:** [So iLL Iron Palm 2.0](https://soillholds.com/products/iron-palm-2-0).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** 8.
- **Verified facts:** current So iLL Iron Palm 2.0 identity;
  `27 × 11.5 × 4 in`; two slopers, two pinches, one incut top rung, and three
  measured rails.
- **Discrepancy:** resolved; the current 25 mm second rail replaces the stale
  35 mm working value.
- **Action:** directly authored and visually reviewed; retain as complete.

### `soill-split-palm`

- **Source:** [So iLL Split Palm](https://soillholds.com/products/split-palm).
- **Current JSON holds:** 14.
- **Source-backed expected physical count:** 14.
- **Verified facts:** current So iLL Split Palm identity; each piece is
  `16.5 × 11 × 3.875 in`; the manufacturer enumerates seven contacts per piece.
- **Discrepancy:** resolved; each distinct molded contact is represented once.
- **Action:** directly authored and visually reviewed; retain as complete.

### `soill-training-tiles`

- **Sources:** [So iLL x Meagan Martin Training Tiles](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin);
  [Training Tiles workouts](https://soillholds.com/pages/meagan-martin-training-tiles-workouts).
- **Current JSON holds:** 16.
- **Source-backed expected physical count:** 16.
- **Verified facts:** So iLL x Meagan Martin Training Tiles; each tile is
  approximately `14 × 8 in`; the manufacturer enumerates eight contacts per
  tile.
- **Discrepancy:** resolved; grouped size values without a one-to-one location
  mapping remain omitted from individual holds.
- **Action:** directly authored and visually reviewed; retain as complete.

### `target10a-linebreaker-base`

- **Sources:** [Target10a product archive](https://www.target10a.com/magazin/category/produkte/);
  [Linebreaker Base review](https://chalkr.de/linebreaker-base-trainingsboard.html)
  (used only for visible-inventory corroboration).
- **Current JSON holds:** 24.
- **Source-backed expected physical count:** 24.
- **Verified facts:** Target10a Linebreaker Base; `58 × 15 × 5.5 cm`; material
  is not established here.
- **Discrepancy:** resolved; the replacement maps 24 physical contacts,
  including the visible sloper surfaces and individually selectable pockets.
- **Action:** directly authored and reviewed a complete replacement from the cited primary evidence.

### `tension-grindstone`

- **Sources:** [Tension Grindstone](https://tensionclimbing.com/products/grindstone);
  [Tension hangboards](https://tensionclimbing.com/pages/hangboards).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** 8.
- **Verified facts:** Tension Grindstone; `22” × 6” × 2.75”`.
- **Discrepancy:** resolved; the replacement maps the full-width jug, 50 mm
  center edge, and three mirrored continuous stepped edge contacts.
- **Action:** directly authored and visually reviewed; retain as complete.

### `tension-honestone`

- **Source:** [Tension hangboards](https://tensionclimbing.com/pages/hangboards).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** 8.
- **Verified facts:** Tension Honestone; `25” × 6” × 2.5”`.
- **Discrepancy:** resolved; the continuously variable top sloper is one
  contact, alongside the center edge, mirrored monos, and mirrored stepped
  edges.
- **Action:** directly authored and visually reviewed; retain as complete.

### `tension-whetstone`

- **Source:** [Tension hangboards](https://tensionclimbing.com/pages/hangboards).
- **Current JSON holds:** 8.
- **Source-backed expected physical count:** 8.
- **Verified facts:** Tension Whetstone; `25” × 6” × 2”`.
- **Discrepancy:** resolved; the replacement adds the continuous ergo-bump jug
  and maps the center edge, mirrored pockets, and mirrored stepped edges.
- **Action:** directly authored and visually reviewed; retain as complete.

### `trango-rock-prodigy-forge`

- **Source:** [Trango Rock Prodigy Forge](https://trango.com/products/rock-prodigy-forge).
- **Current JSON holds:** 20 logical holds / 20 geometry pieces.
- **Source-backed expected physical count:** 20.
- **Verified facts:** the official chart maps ten named regions per mirrored
  half; the depth guide supports the retained rail and MR measurements.
- **Discrepancy resolved:** three pinch widths are alternate positions on the
  outer contact block, not additional physical regions. Unmapped IM depths and
  optional semantics remain omitted.
- **Action:** directly authored and visually reviewed; retain as complete.

### `trango-rock-prodigy-natural`

- **Source:** [Trango Rock Prodigy Natural](https://trango.com/products/rock-prodigy-natural).
- **Current JSON holds:** 14 logical holds / 16 geometry pieces.
- **Source-backed expected physical count:** 14.
- **Verified facts:** Trango Rock Prodigy Natural; each half is
  `7.5” × 6” × 1.5”`.
- **Discrepancy resolved:** six recessed contacts per half plus the two
  guide-corroborated top jugs are modeled. Conflicting crimp/lower-pocket
  measurements and exact finger-combination semantics remain omitted.
- **Action:** directly authored and visually reviewed; retain as complete.

### `trango-rock-prodigy-pivot`

- **Source:** [Trango Rock Prodigy Pivot](https://trango.com/products/rock-prodigy-pivot).
- **Current JSON holds:** 18 logical holds / 22 geometry pieces.
- **Source-backed expected physical count:** unknown.
- **Verified facts:** Trango Rock Prodigy Pivot identity; dimensions/material
  are not established here.
- **Discrepancy:** the documentation lists 22 grip positions, not an exact
  physical-region count; dimensions are unsupported and orientations collapsed.
- **Action:** completed direct-authored package is the structural precedent; no
  Pivot geometry was changed in this pass.

### `trango-rock-prodigy-training-center`

- **Sources:** [Trango Rock Prodigy Training Center](https://trango.com/products/rock-prodigy-training-center);
  [RPTC use instructions (PDF)](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155).
- **Current JSON holds:** 24 logical holds / 28 geometry pieces.
- **Source-backed expected physical count:** 24 logical holds / 28 visible
  pieces.
- **Verified facts:** Trango Rock Prodigy Training Center identity; exact
  finger-pair labels in JSON are not supported.
- **Discrepancy resolved:** 24 physical contacts are modeled; the four compound
  pockets use two pieces each. Variable positions and combinations are not
  duplicated as physical holds, and unsupported finger-pair/depth labels remain
  omitted.
- **Action:** directly authored and visually reviewed; retain as complete.

### `yy-verticalboard-evo`

- **Sources:** [YY Vertical VerticalBoard Evo](https://www.yyvertical.com/products/verticalboard-evo);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 25.
- **Source-backed expected physical count:** 25.
- **Verified facts:** YY Vertical VerticalBoard Evo; `65 × 14 × 5.5 cm`.
- **Discrepancy:** resolved; the asymmetric Evo sides are authored independently,
  and all separately bounded slopers, jugs, edges, pockets, monos, and center
  contacts are represented.
- **Action:** directly authored and visually reviewed; retain as complete.

### `yy-verticalboard-first`

- **Sources:** [YY Vertical VerticalBoard First](https://www.yyvertical.com/products/verticalboard-first);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 17.
- **Source-backed expected physical count:** 17.
- **Verified facts:** YY Vertical VerticalBoard First; `54 × 13 × 5 cm`; no
  centre jug or pockets.
- **Discrepancy:** resolved; the replacement removes fictitious contacts and
  maps every separately bounded jug, sloper, and edge.
- **Action:** directly authored and visually reviewed; retain as complete.

### `yy-verticalboard-light`

- **Sources:** [YY Vertical VerticalBoard Light](https://www.yyvertical.com/products/verticalboard-light);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 12.
- **Source-backed expected physical count:** 12.
- **Verified facts:** YY Vertical VerticalBoard Light; `54 × 9 × 5 cm`; no
  centre jug.
- **Discrepancy:** resolved; the replacement removes the fictitious center jug
  and represents every separately bounded top surface and edge.
- **Action:** directly authored and visually reviewed; retain as complete.

### `yy-verticalboard-one`

- **Sources:** [YY Vertical VerticalBoard One](https://www.yyvertical.com/en/products/verticalboard-one);
  [YY Vertical hangboards](https://www.yyvertical.com/en/collections/poutres-escalade).
- **Current JSON holds:** 20.
- **Source-backed expected physical count:** 20.
- **Verified facts:** YY Vertical VerticalBoard One; `62 × 13 × 5.5 cm`.
- **Discrepancy:** resolved; the current package maps the sourced pockets,
  center multifunction handle, jugs, slopers, and edges with current dimensions.
- **Action:** directly authored and visually reviewed; retain as complete.

### `zlagboard-evo`

- **Sources:** [Zlagboard hangboards](https://zlagboard.com/hangboards);
  [Vertical-Life Zlagboard Evo listing](https://shop.vertical-life.info/it/zlagboard-evo-incl.-piano-di-allenamento-di-6-mesi)
  (used only as limited secondary corroboration).
- **Current JSON holds:** 21.
- **Source-backed expected physical count:** 21.
- **Verified facts:** Zlagboard Evo identity; lime wood; the official exhaustive
  map establishes seven top contacts and fourteen cavity contacts. The required
  `70 × 23 × 6 cm` dimensions use the limited secondary source documented in
  the model-specific audit.
- **Discrepancy:** resolved; the omitted top jugs/slopers are restored as
  physical contacts and all map labels are assigned one-to-one.
- **Action:** directly authored and visually reviewed; retain as complete.

### `zlagboard-pro`

- **Source:** [Zlagboard hangboards](https://zlagboard.com/hangboards).
- **Current JSON holds:** 28.
- **Source-backed expected physical count:** 28.
- **Verified facts:** current Zlagboard Pro 2.0 identity; lime wood; the official
  exhaustive map establishes seven top contacts and twenty-one cavity contacts.
  The required `70.5 × 25 × 8 cm` dimensions use the limited secondary source
  documented in the model-specific audit.
- **Discrepancy:** resolved; the current model/version and every mapped physical
  contact are explicit.
- **Action:** directly authored and visually reviewed; retain as complete.

## Decision summary

| decision | packages |
| --- | ---: |
| corrected and retained complete packages | 7 |
| direct-authored complete replacement packages | 26 |
| excluded stale duplicate candidate | 1 |
| total audited package slugs | 34 |

The discoverable catalog therefore contains 33 complete packages and no drafts.
