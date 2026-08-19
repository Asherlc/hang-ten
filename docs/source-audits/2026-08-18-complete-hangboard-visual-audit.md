# Complete hangboard source, metadata, and geometry audit

Reviewed 2026-08-18. This audit covers all 34 completed direct-child packages
discovered under `Hangboards/`: 359 ordered logical holds, 363 geometry pieces,
and 1,890 editable path points at the branch-base baseline. The final generic
primitive pass preserves those inventories while reducing editable points to
1,180. No primary-only draft exists and no package was promoted.

The manufacturer sources establish only the fields explicitly mapped below.
Product photos are presentation evidence, not hold-boundary, capacity, grip,
or training-semantic evidence. Required `id`, `name`, `kind`, and `geometry`
fields therefore remain in blocked packages even where the current inventory
is not authoritative. Only selected matrix-approved unsupported optional
semantics are removed. Other blocked semantics remain explicitly identified—
including Tension Honestone's retained `fourFingerPocket`—rather than being
silently removed or replaced with an image inference.

## Retained BEFORE evidence

The unchanged branch-base packages were captured through the Workbench API and
the unchanged `#editor-svg` rendering path before any package edit. The capture
manifest has 34 unique board IDs, exactly equal to the 34 IDs discovered from
the completed `board.json` documents, and every manifest filename exists.

[Labeled BEFORE contact sheet](assets/2026-08-18-complete-hangboard-visual-audit/before-contact-sheet.png)

The 34 full-resolution labeled PNGs are retained in
[`assets/2026-08-18-complete-hangboard-visual-audit/before/`](assets/2026-08-18-complete-hangboard-visual-audit/before/).
The exact filename inventory appears in the board table below. Each capture was
inspected individually in addition to the contact sheet.

## Retained AFTER evidence

The final packages were recaptured with the same Workbench API, unchanged
`#editor-svg` rendering path, fixed viewport, and catalog-generic harness. The
ordered 34-ID AFTER manifest is exactly equal to the retained ordered BEFORE
manifest; every manifest entry has one full-resolution PNG.

[Labeled AFTER contact sheet](assets/2026-08-18-complete-hangboard-visual-audit/after-contact-sheet.png)

The 34 full-resolution labeled AFTER PNGs are retained in
[`assets/2026-08-18-complete-hangboard-visual-audit/after/`](assets/2026-08-18-complete-hangboard-visual-audit/after/).
Both 3150-pixel-wide contact sheets and every full-resolution BEFORE/AFTER pair
were visually inspected.

## Complete catalog disposition and baseline inventory

`H/P/pts` is the exact branch-base logical-hold count, geometry-piece count,
and editable-point count. The hash is Task 2's canonical coordinate-free
audited-inventory hash over board ID, ordered non-geometry hold metadata, and
piece counts. `crop` means the catalog-generic presentation normalizer applies
an exact pixel crop and coordinate reprojection; it does not resample pixels or
change geometry relative to the source image.

| board / BEFORE capture | primary source | H/P/pts; before inventory hash | metadata disposition | geometry and presentation disposition |
| --- | --- | --- | --- | --- |
| [`beastmaker-1000`](assets/2026-08-18-complete-hangboard-visual-audit/before/beastmaker-1000--4fee18798954.png) | [Beastmaker](https://www.beastmaker.co.uk/products/beastmaker-1000-series) | 22/22/395; `1adee9f0b858ae2ab0afced03be09ae9710c67ff931bf85786b9afde796ae441` | Retain sourced 580 × 150 mm face dimensions; withhold thickness because the Tulipwood page says 5 mm while 58 mm is documented only for a separate Beech variant; no per-pocket remap. | Keep 22 audited paths; simplifier no-op; no crop. Numbered depth/capacity map is missing. |
| [`beastmaker-2000`](assets/2026-08-18-complete-hangboard-visual-audit/before/beastmaker-2000--305c473cc719.png) | [Beastmaker](https://www.beastmaker.co.uk/products/beastmaker-2000-series) | 25/25/339; `b7a4ef0b87ae9396361feda57c61a3884b1d00c908db3372edbf838a699030f3` | Board dimensions and aggregate kinds retained; individual sizes/capacities not remapped. | Keep 25 audited paths; simplifier no-op; no crop. Numbered map is missing. |
| [`dewoodstok-woodbord`](assets/2026-08-18-complete-hangboard-visual-audit/before/dewoodstok-woodbord--e40376735372.png) | [deWoodstok](https://www.dewoodstok.nl/product/hangboard-woodbord/) | 17/17/255; `693a82e93054069b80a36b67b53031978919bc1db57bc956fdf381ca9fcc472a` | Dimensions and 1+16 aggregate retained; published pocket depths are not assigned to IDs. | Keep 17 audited paths; simplifier no-op; no crop. Depth-to-position map is missing. |
| [`escape-beta`](assets/2026-08-18-complete-hangboard-visual-audit/before/escape-beta--dd6fe9b3a8dc.png) | [current Escape Beta Board](https://escapeclimbing.com/products/ec72100) | 6/6/0; `cb9d1a8ddf83fe9d8dae5b8aa32767cde205dca2498650a3375d2303c260817a` | Legacy model identity, dimensions, and six-target facts remain unverified and unchanged. | Six broad regions visibly omit cavities; no materialization; exact crop 1536×1024 → 1503×394. |
| [`escape-beta-22`](assets/2026-08-18-complete-hangboard-visual-audit/before/escape-beta-22--245680ffb240.png) | [Escape](https://escapeclimbing.com/products/ec72100) | 22/22/274; `69329433b14e01a2ed1640bf29b7f2d91492fe6468ec448d33cdc7a33018ce8a` | Dimensions retained; secondary 11-family facts are not promoted. | Keep audited paths; 11 visible cavities versus 22 logical targets is unresolved; no crop. |
| [`escape-unlimited`](assets/2026-08-18-complete-hangboard-visual-audit/before/escape-unlimited--19831f6dfe62.png) | [Escape](https://escapeclimbing.com/products/ec72000) | 6/6/0; `0c772e2845e61bc8cf08d0cf62753a51a3f80f9c0d0a42764c53a3c35083748a` | Correct dimensions to 23.5 × 6 in; replace the unsupported three-row subtitle with the sourced four descending finger-pad levels. | Source says four levels but package has three pairs; no materialization; exact crop 1774×887 → 1678×553. |
| [`evolv-kilter-basic-long`](assets/2026-08-18-complete-hangboard-visual-audit/before/evolv-kilter-basic-long--ac4049aa3a2d.png) | [Evolv](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105) | 4/4/0; `528f2d02b5a792d4ca31b842360a3b0444170f45ead810a5cf1999d03da7e511` | Correct dimensions to 79 × 16 × 6 cm; do not infer which region is the sourced jug. | Four generic bands do not prove jug+three-edge topology; no materialization; exact crop 1537×1023 → 1406×332. |
| [`frictitious-doormount-pro-7`](assets/2026-08-18-complete-hangboard-visual-audit/before/frictitious-doormount-pro-7--8a23c5cc8dca.png) | [Frictitious](https://frictitiousclimbing.com/en-ca/products/doormount-pro) | 8/8/0; `8b32c935192d394edbff49ae8e11371811ca12737f0edf98df7acf2637fa7c92` | Correct dimensions to 25.5 × 4.5 × 2.25 in and repair the product URL; remove unsupported optional per-hold mappings while retaining eight schema-required records. | Official seven-hold aggregate cannot identify a record to delete; lower regions cross bays; no materialization; exact crop 1774×887 → 1688×353. |
| [`frictitious-megalith`](assets/2026-08-18-complete-hangboard-visual-audit/before/frictitious-megalith--33de4ccadb0c.png) | [Frictitious](https://frictitiousclimbing.com/products/megalith) | 9/9/0; `57d38ec00d5195c04b5bc229ab3b6370635791e2f21e5c6d1f1c1bbeb408e3d3` | Correct dimensions to 26.75 × 6.5 × 2.25 in; aggregate edge/pocket facts are not assigned to IDs. | Mono count and 40-mm pocket boundary are unresolved; no materialization; exact crop 1536×1024 → 1453×411. |
| [`lattice-triple-rung`](assets/2026-08-18-complete-hangboard-visual-audit/before/lattice-triple-rung--98ec533951a6.png) | [Lattice](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | 3/3/57; `b6e54cc95849a0bcff0d169fb7d918f3b6829bb6c49cfe52e342028d2f0a2fd7` | Dimensions and three sourced edge sizes retained. | Three continuous audited paths align; simplifier no-op; no crop. Optional capacity remains unsupported. |
| [`metolius-climbers-edge`](assets/2026-08-18-complete-hangboard-visual-audit/before/metolius-climbers-edge--1e84e2649b1d.png) | [Metolius](https://www.metoliusclimbing.com/products/climbers-edge-board) | 11/11/0; `dd117715ba58f5c6a90b08f1635cdc69303c5cc0727a9e5d1ef9a39e553b39fd` | Current-page dimensions are not applied until package model/version is proven. | Floating/broad regions omit sourced slopers and depths; no materialization; exact crop 1717×916 → 1644×722. |
| [`metolius-contact`](assets/2026-08-18-complete-hangboard-visual-audit/before/metolius-contact--ec276e428883.png) | [product](https://www.metoliusclimbing.com/products/contact-training-board), [numbered diagram](https://www.metoliusclimbing.com/cdn/shop/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170) | 10/10/0; `3f9a3607c2c7a608fd50b12b6c6e77b50ae4d4da66a29dd1461a51108866b675` | Correct dimensions to 32.5 × 11 × 2.625 in; remove unsupported optional all-edge semantics while preserving required records. | Ten broad zones cross many cavities and omit categories; grouping contract incomplete; no materialization; exact crop 1774×887 → 1719×629. |
| [`metolius-project`](assets/2026-08-18-complete-hangboard-visual-audit/before/metolius-project--5007e676de90.png) | [Metolius catalog](https://www.metoliusclimbing.com/pdf/Climbing-Hold-Catalog.pdf) | 8/8/0; `89544f2545f5bd4fa4d7a8a3d5f318ff90ec6026d162d20ef97273476f93eb31` | Correct dimensions to 24.5 × 6 in; generic inventory remains explicitly non-authoritative. | Broad regions cross visible breaks; no complete field map; no materialization; exact crop 1774×887 → 1639×486. |
| [`metolius-simulator-3d`](assets/2026-08-18-complete-hangboard-visual-audit/before/metolius-simulator-3d--ad3f6e0bbb16.png) | [guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide), [catalog](https://www.metoliusclimbing.com/pdf/Metolius_2010.pdf) | 7/7/0; `e28bbc5af27d9605f2c721f6e9095fecec797165db972ea775ad25f2cfb49875` | Correct dimensions to 28 × 8.75 in; remove unsupported optional seven-region mappings while preserving required records. | Broad zones omit slopers/3F families and cross cavities; no materialization; exact crop 1614×975 → 1583×571. |
| [`metolius.wood-grips-compact-ii`](assets/2026-08-18-complete-hangboard-visual-audit/before/metolius.wood-grips-compact-ii--ecd2a502a9db.png) | [Metolius](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) | 19/19/78; `f4d0bf85865b150704af1bb8bf1eb78d9c39abb5e7461abbd827ebffd16cd966` | Dimensions and aggregate inventory retained. | Strong audited match; simplifier no-op; no crop. Individual field provenance remains incomplete. |
| [`moon-armstrong`](assets/2026-08-18-complete-hangboard-visual-audit/before/moon-armstrong--3e59a2c3ad25.png) | [Moon](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | 11/11/0; `37ec77e11f4efe36def477c955f5ee0b6aed8c417ff1b2281a792be3576dc29b` | Correct dimensions to 65 × 16.5 × 5.5 cm; do not remap aggregate features. | Artwork/layout likely wrong model and misses sourced slopers/monos; no materialization; exact crop 1672×941 → 1538×471. |
| [`nature-stoak-board-iii`](assets/2026-08-18-complete-hangboard-visual-audit/before/nature-stoak-board-iii--23853bedbe8d.png) | [Nature](https://natureclimbing.com/products/stoak-board-iii-beech) | 6/6/0; `4cba6504a798e3921c5effd1ab9f384080f7a5346fd5e586dbc054592c862cf5` | Correct dimensions to 57 × 12 × 5.5 cm; do not choose an insert state or map depths. | Current topology conflicts with adjustable product; no materialization; exact crop 1774×887 → 1677×445. |
| [`soill-iron-palm-2`](assets/2026-08-18-complete-hangboard-visual-audit/before/soill-iron-palm-2--eb1bcad6f0bc.png) | [So iLL](https://soillholds.com/products/iron-palm-2-0) | 6/6/0; `68d4c854170cef6bf6004619fd760eb707bd463f87bf548e18a9125b21c792d0` | Repair product URL and correct the manufacturer model name to Iron Palm 2.0; unsupported dimensions and current completeness remain audit blockers. | Large discs/rails do not expose pinches, slopers, or thumb catches; no materialization; exact crop 1536×1024 → 1492×699. |
| [`soill-split-palm`](assets/2026-08-18-complete-hangboard-visual-audit/before/soill-split-palm--cc07b6832b7c.png) | [So iLL](https://soillholds.com/products/split-palm) | 2/2/0; `ce8d12b68182f9f099a7f34132585d982531026056711df4f5d622ddd44e650c` | Repair product URL; no current manufacturer dimensions/inventory are claimed as verified. | Two large zones cover multiple branches; authoritative inventory absent; no materialization; exact crop 1254×1254 → 1244×616. |
| [`soill-training-tiles`](assets/2026-08-18-complete-hangboard-visual-audit/before/soill-training-tiles--073b9c42fd16.png) | [So iLL](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin) | 4/4/0; `0a16960e26aadb4b31bafcaf798f4b29afd4c9546690a4d90dd1362c1cb8bf7f` | Repair product URL; dealer dimensions/depths are not promoted. | Four zones omit the documented secondary edge progression; no first-party map; no materialization; exact crop 1536×1024 → 1514×529. |
| [`target10a-linebreaker-base`](assets/2026-08-18-complete-hangboard-visual-audit/before/target10a-linebreaker-base--83a10cb8e4e0.png) | [target10a](https://www.target10a.com/magazin/2017/01/01/linebreaker-base/) | 11/11/0; `db9b63f4bc5ec6a03f79c40e4186ab20c74348606d4c0444bb0f52d14f2f96dc` | Dealer dimensions/capacities are not promoted; package facts remain explicitly unverified. | Floating/broad zones omit apparent jugs/slopers; no first-party map; no materialization; exact crop 1448×1086 → 1332×626. |
| [`tension-grindstone`](assets/2026-08-18-complete-hangboard-visual-audit/before/tension-grindstone--4c704daf13a7.png) | [Tension](https://tensionclimbing.com/products/grindstone) | 7/7/0; `94ebbce4675be869a8ba1121ae5d9e1e321d57045b89a1fa5da4141025e05c0b` | Correct dimensions to 22 × 6 × 2.75 in; do not assign published depths to IDs. | Seven broad regions flatten full-width jug and edge progression; no map/materialization; exact crop 1672×941 → 1651×478. |
| [`tension-honestone`](assets/2026-08-18-complete-hangboard-visual-audit/before/tension-honestone--223e0ec49199.png) | [Tension](https://tensionclimbing.com/products/honestone) | 7/7/0; `3309bf4db94ffb5a5e3104b74bd225d913b84169b860f9c8d732be82982eab81` | Remove contradicted end-pocket `fingerCapacity=4`; dimensions and replacement mono mapping remain withheld. | Image/regions omit sloper-led source profile; no materialization; exact crop 1672×941 → 1646×400. |
| [`tension-whetstone`](assets/2026-08-18-complete-hangboard-visual-audit/before/tension-whetstone--c085c83b3df1.png) | [Tension](https://tensionclimbing.com/products/whetstone) | 7/7/0; `ef15d19b7998b14c8d6a6ce19e7b892567380f137a49af50d9090d0601228a73` | Correct dimensions to 25 × 6 × 2 in; remove contradicted four-finger grip/capacity without inventing a per-ID 2F map. | Broad rails do not express four depths; no materialization; exact crop 1536×1024 → 1517×384. |
| [`trango-rock-prodigy-forge`](assets/2026-08-18-complete-hangboard-visual-audit/before/trango-rock-prodigy-forge--3524ced1ecba.png) | [product](https://trango.com/products/rock-prodigy-forge), [depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887) | 12/12/0; `f264fa8447cff7a4d3d3de09f131ab3fd7f2a678f0bc34f45f463f04040fbf92` | Supported dimensions retained; non-exhaustive guide is not expanded into per-ID facts. | Primitive regions miss source positions/closed crimp topology; no complete map/materialization; exact crop 1536×1024 → 1511×363. |
| [`trango-rock-prodigy-natural`](assets/2026-08-18-complete-hangboard-visual-audit/before/trango-rock-prodigy-natural--7f4ed5768d6a.png) | [product](https://trango.com/products/rock-prodigy-natural), [Quick Start](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Natural_Consumer_Quick_Start_Final_Digital_9.21.21.pdf?v=1656514361) | 12/12/0; `db85e6fc8727c8e78cbc0f73dfc8359e1a3e4fac83bd7c0e1dafe55853decfaa` | Correct dimensions to 7.5 × 6 × 1.5 in each board; non-comprehensive guide is not remapped. | Current Forge-like topology omits jug/pinches/variables; no materialization; exact crop 1536×1024 → 1452×584. |
| [`trango-rock-prodigy-pivot`](assets/2026-08-18-complete-hangboard-visual-audit/before/trango-rock-prodigy-pivot--7cf9f33e474c.png) | [product](https://trango.com/products/rock-prodigy-pivot), [Quick Start](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507) | 10/10/0; `410209dc8eaf85d9f54f867d605c0112ed4f0e7a7501f5c3fbb5276c5ee17892` | Unsupported dimensions and fixed inventory remain blocked, not replaced. | One view cannot model four orientations/22 positions; product contract required; no materialization; exact crop 1774×887 → 1733×491. |
| [`trango.rock-prodigy-training-center`](assets/2026-08-18-complete-hangboard-visual-audit/before/trango.rock-prodigy-training-center--54f0d57dd133.png) | [product](https://trango.com/products/rock-prodigy-training-center), [manual](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Mounting_Instructions_no_screws_v2.pdf?v=1587749856) | 24/28/492; `89cdac2919138d203b3dcbd83cc30f8760142691ebb6a03259fbf3abfa2155d5` | Dimensions and broad types retained; 24 records are not claimed to exhaust 30+ positions. | Preserve four multi-piece pinches and audited paths; simplifier no-op; no crop. Variable-position contract unresolved. |
| [`yy-verticalboard-evo`](assets/2026-08-18-complete-hangboard-visual-audit/before/yy-verticalboard-evo--52da4a0e33ab.png) | [YY Vertical](https://www.yyvertical.com/en/products/verticalboard-evo) | 7/7/0; `84c45aa3249065600f6beafcdf382f5f5d8564381af97c9857146760bf9dce4f` | Correct dimensions to 65 × 14 × 5.5 cm; remove contradicted 3F grip/capacity without guessing 2F/mono IDs. | Seven broad regions versus 19 grips; no complete map/materialization; exact crop 1774×887 → 1690×417. |
| [`yy-verticalboard-first`](assets/2026-08-18-complete-hangboard-visual-audit/before/yy-verticalboard-first--8a369008547e.png) | [YY Vertical](https://www.yyvertical.com/en/products/verticalboard-first) | 7/7/0; `5f5302045b97e5d69d383bbcbf371ebbf96f7012b2f938158da6b93e4998e503` | Correct dimensions to 54 × 13 × 5 cm; remove unsupported 3F grip/capacity. | Seven broad regions versus ten grips; no complete map/materialization; exact crop 1774×887 → 1640×448. |
| [`yy-verticalboard-light`](assets/2026-08-18-complete-hangboard-visual-audit/before/yy-verticalboard-light--8f078a49c3e1.png) | [YY Vertical](https://www.yyvertical.com/en/products/verticalboard-light) | 7/7/0; `418032357405f96e7bf34fc94943a89a29d31b300df519a01ef52d4ec5ebae05` | Correct dimensions to 54 × 9 × 5 cm; center-jug identity remains withheld. | Seven-count may match but center/notch map is absent; no materialization; exact crop 1774×887 → 1720×392. |
| [`yy-verticalboard-one`](assets/2026-08-18-complete-hangboard-visual-audit/before/yy-verticalboard-one--53c8899c8937.png) | [YY Vertical](https://www.yyvertical.com/en/collections/training/products/verticalboard-one) | 7/7/0; `21e4aee42cdb823a729e79b60b79dd63a5f94b879c1eb626e267f1e60d8d35b5` | Correct dimensions to 62 × 13 × 5.5 cm; remove contradicted 3F grip/capacity without guessing 2F IDs. | Seven broad regions versus 15 grips; no complete map/materialization; exact crop 1774×887 → 1715×398. |
| [`zlagboard-evo`](assets/2026-08-18-complete-hangboard-visual-audit/before/zlagboard-evo--e51ac1a87bfb.png) | [Zlagboard](https://www.zlagboard.com/hangboards) | 14/14/0; `f766f144aca85811374d937d8710a4c494b05f7f3f5c656d071f81de6acf5078` | Secondary dimensions and current all-2F claims are not replaced without a model map. | Cavities align broadly but jugs/slopers and model dimensions are unresolved; no materialization; exact crop 2081×755 → 2015×436. |
| [`zlagboard-pro`](assets/2026-08-18-complete-hangboard-visual-audit/before/zlagboard-pro--af6b10e747d3.png) | [hangboards](https://www.zlagboard.com/hangboards), [app/version evidence](https://www.zlagboard.com/app) | 21/21/0; `16905bc9553d0f9ab553176ab6d290133f5764bb30501d350be8541e24624547` | Dimensions/capacities remain blocked until Pro 1.0 versus 2.0 is identified. | Primitive grid cannot establish generation or sourced jugs/slopers; no materialization; exact crop 2112×745 → 2044×503. |

## Authoritative field mappings applied

| changed field | before → after | authoritative source role |
| --- | --- | --- |
| Escape Unlimited `dimensions`; `subtitle` | `600 × 300 mm` → `23.5 × 6 in`; three-row claim → `Four descending finger-pad depth levels.` | Manufacturer dimensions and four-level description; `subtitle` is schema-required. |
| Evolv Basic Long `dimensions` | `580 × 110 mm` → `79 × 16 × 6 cm` | Manufacturer product dimensions. |
| Frictitious Pro 7 `dimensions`; `productURL` | `700 × 140 mm` → `25.5 × 4.5 × 2.25 in`; stale `frictitious.com` URL → `https://frictitiousclimbing.com/en-ca/products/doormount-pro` | Manufacturer product dimensions and current model product page. |
| Frictitious Megalith `dimensions` | `580 × 150 mm` → `26.75 × 6.5 × 2.25 in` | Manufacturer product dimensions. |
| Metolius Contact `dimensions` | `26 × 13 in` → `32.5 × 11 × 2.625 in` | Manufacturer product dimensions. |
| Metolius Project `dimensions` | `26 × 8 in` → `24.5 × 6 in` | Manufacturer catalog dimensions. |
| Metolius Simulator 3-D `dimensions` | `34 × 9 in` → `28 × 8.75 in` | Manufacturer legacy catalog dimensions. |
| Moon Armstrong `dimensions` | `620 × 250 mm` → `65 × 16.5 × 5.5 cm` | Manufacturer product dimensions. |
| Nature Stoak III `dimensions` | `600 × 300 mm` → `57 × 12 × 5.5 cm` | Manufacturer product dimensions. |
| Tension Grindstone `dimensions` | `580 × 150 mm` → `22 × 6 × 2.75 in` | Manufacturer product dimensions. |
| Tension Whetstone `dimensions` | `580 × 150 mm` → `25 × 6 × 2 in` | Manufacturer product dimensions. |
| Trango Natural `dimensions` | `5.25 × 12.75 in (per side)` → `7.5 × 6 × 1.5 in (each board)` | Manufacturer product/Quick Start dimensions. |
| YY Evo/First/Light/One `dimensions` | shared `600 × 300 mm` → 65×14×5.5, 54×13×5, 54×9×5, and 62×13×5.5 cm | Each model's manufacturer product dimensions. |
| So iLL three `productURL` fields | stale `soill.com` URLs → current `soillholds.com` product URLs | Current manufacturer product identity pages. |
| So iLL Iron Palm `name` | `Iron Palm 2` → `Iron Palm 2.0` | Current manufacturer model identity. |
| Contact, Pro 7, Simulator optional hold semantics | mapped `gripType`/`fingerCapacity`/`features` → omitted | Sources contradict completeness and do not map the retained schema-required records. |
| YY Evo/First/One pocket semantics | `threeFingerPocket`, `fingerCapacity=3` → omitted | Manufacturer aggregate inventories contradict 3F and do not identify replacement IDs. |
| Tension Whetstone end-pocket semantics | `fourFingerPocket`, `fingerCapacity=4` → omitted | Manufacturer says 2F at board level; no per-ID boundary map supports writing 2. |
| Tension Honestone end-pocket capacity | `fingerCapacity=4` → omitted | Manufacturer says mono at board level; no per-ID boundary map supports writing 1. |

## Geometry gates and inventory preservation

The generic candidate derivation completed for all 34 images as a read-only,
image-only report with SHA-256
`5316c10ae7cab909b044ceeab3649a5e5c4777bbeb519cd7a727cbe8f206d393`.
It emitted seven unlabeled candidates across only four boards, 4,704 rejected
components, and zero verified symmetry pairs. No candidate report had the
separate authoritative inventory, candidate topology, complete coordinate-free
accepted mapping, and verified symmetry/multi-piece policy required for
materialization. Therefore zero candidate contours were written. This is a
fail-closed result, not a claim that the current coarse geometry is accurate.

The initial generic path simplifier found no safe path-to-path reductions. The
follow-up catalog-generic path-to-primitive pass then accepted exactly 45
`path` → `roundedRect` replacements: 18 on Beastmaker 1000, 17 on Beastmaker
2000, and 10 on Rock Prodigy Training Center. It removed 710 editable points,
so the complete catalog is **1,890 → 1,180 editable points**. All accepted
pieces preserve hold identity, piece order, frame, treatment, and every
non-shape value.

The independent explicit-revision audit renders both documents through the
Workbench codec and reports a maximum exact bidirectional boundary deviation
of **0.999501671 px** and maximum full-canvas 4× symmetric-difference ratio of
**0.000160231660** (0.016023166%). The maximum-error pair is Training Center
`pocket-index-middle-deep-left/right`; its full-resolution and enlarged
BEFORE/AFTER inspection found no visible edge discontinuity or symmetry drift.
The maximum symmetric-difference pair is Beastmaker 1000
`pocket-bottom-outer-left/right`. Every accepted value is below the 1 px and
0.25% gates.

The generic presentation dry run found one catalog-wide crop policy applicable
to 27 packages. Each accepted write is an exact subset of the prior PNG pixels,
uses the documented 1% padding policy, and reprojects every piece frame to the
same native source pixels. It preserves all 359 ordered hold IDs, all 363 piece
counts/types/order, every path command, every rounded-rectangle parameter, and
all geometry treatments. The seven already-normalized packages are unchanged.

The final before/post comparison confirms the same 34 boards, 359 ordered
holds, and 363 ordered pieces; only the 45 audited shape values differ. The
fresh simplifier dry run reports zero changed boards/pieces at 1,180 points,
and the presentation dry run reports zero changes. All inventory hashes remain
identical except the eight intentionally stripped optional-semantic groups:

| board | before inventory hash → after inventory hash |
| --- | --- |
| Frictitious Pro 7 | `8b32c935192d394edbff49ae8e11371811ca12737f0edf98df7acf2637fa7c92` → `c6b341554bce75162b4c0d30522085ee7b988a0aa6cfaea11fb38d71f83063e6` |
| Metolius Contact | `3f9a3607c2c7a608fd50b12b6c6e77b50ae4d4da66a29dd1461a51108866b675` → `53e31c5301de05f4fe8abb2895d37573f7f0b94de0c76f3f2909e1190cac2f2c` |
| Metolius Simulator 3-D | `e28bbc5af27d9605f2c721f6e9095fecec797165db972ea775ad25f2cfb49875` → `77e2b520ddd0b3022f4095f90ab55ad58a7c6f3f3f93e6139741d8573ce98299` |
| Tension Honestone | `3309bf4db94ffb5a5e3104b74bd225d913b84169b860f9c8d732be82982eab81` → `fc52992b94166cffea9c8c2b65da17690dd492052cd0d0273f0b0579d7701cdf` |
| Tension Whetstone | `ef15d19b7998b14c8d6a6ce19e7b892567380f137a49af50d9090d0601228a73` → `15551de41e29288aa3d15fec00c1cd6db8d70cc06822fe3ccd0869612aab16fe` |
| YY Evo | `84c45aa3249065600f6beafcdf382f5f5d8564381af97c9857146760bf9dce4f` → `21ce4cbfb3685b3755b07640e53541bc6b446b9f1061c61f9b7290827d374fed` |
| YY First | `5f5302045b97e5d69d383bbcbf371ebbf96f7012b2f938158da6b93e4998e503` → `77c98de984c8b358e291f8b7dd111b4f2a7908b09d324beb414ca099665fbf9c` |
| YY One | `21e4aee42cdb823a729e79b60b79dd63a5f94b879c1eb626e267f1e60d8d35b5` → `45a3ff2ed2008a43d6a33f50168c48f064cfb5c1a53b89fe58978d136132e5b8` |

## BEFORE visual findings

Every capture contains its expected manifest region count and no region is
clipped by the SVG canvas. The seven previously audited packages—both
Beastmakers, deWoodstok, Escape Beta 22, Lattice Triple Rung, Metolius Wood
Grips Compact II, and Rock Prodigy Training Center—retain visibly aligned,
source-comparable paths. The other 27 captures expose blockers rather than
safe geometry writes: broad rectangles cross several cavities, float outside
the contact surface, omit documented grip families, or represent only one of
several product configurations/orientations. The most severe examples are
Escape Beta, Metolius Contact, Moon Armstrong, So iLL Split Palm/Training
Tiles, Pivot, and the four YY boards. Those packages remain geometrically
unchanged except for exact presentation crop/reprojection.

## AFTER per-board visual verdicts

`H/P/pts` below is the final logical-hold, geometry-piece, and editable-point
inventory. “Clear” means every manifest piece is present and the SVG canvas
clips none of it. Symmetry is judged only where the source and package present
a paired design; a symmetric render does not resolve an absent authoritative
hold map.

| board / AFTER capture | H/P/pts and clipping | outline/highlight alignment and symmetry | source agreement, blockers, and visible change |
| --- | --- | --- | --- |
| [`beastmaker-1000`](assets/2026-08-18-complete-hangboard-visual-audit/after/beastmaker-1000--4fee18798954.png) | 22/22/110; clear. | All 18 redesigned pieces remain on their recesses/sloper; paired pockets stay mirrored with no visible drift. | Strong image agreement; numbered depth/capacity map remains absent. Primitive change is visually indistinguishable at catalog and full resolution. |
| [`beastmaker-2000`](assets/2026-08-18-complete-hangboard-visual-audit/after/beastmaker-2000--305c473cc719.png) | 25/25/104; clear. | All 17 redesigned pieces preserve row alignment and left/right pairing; no highlight discontinuity. | Strong image agreement; numbered source map remains absent. Primitive change is not visibly distinguishable. |
| [`dewoodstok-woodbord`](assets/2026-08-18-complete-hangboard-visual-audit/after/dewoodstok-woodbord--e40376735372.png) | 17/17/255; clear. | Recess outlines remain consistently seated and symmetric. | Strong image agreement; depth-to-position map remains absent. No visible change. |
| [`escape-beta`](assets/2026-08-18-complete-hangboard-visual-audit/after/escape-beta--dd6fe9b3a8dc.png) | 6/6/0; clear. | The six broad zones stay paired but cross/omit visible cavities. | Legacy/current-model agreement remains blocked. Exact crop enlarges the unchanged coarse geometry. |
| [`escape-beta-22`](assets/2026-08-18-complete-hangboard-visual-audit/after/escape-beta-22--245680ffb240.png) | 22/22/274; clear. | Audited contours remain aligned and mirrored. | Strong visible agreement, but 11 cavities versus 22 logical targets remains unresolved. No visible change. |
| [`escape-unlimited`](assets/2026-08-18-complete-hangboard-visual-audit/after/escape-unlimited--19831f6dfe62.png) | 6/6/0; clear. | Three paired broad bands remain symmetric but do not express four sourced levels. | Source topology still disagrees. Exact crop and sourced metadata change only. |
| [`frictitious-doormount-pro-7`](assets/2026-08-18-complete-hangboard-visual-audit/after/frictitious-doormount-pro-7--8a23c5cc8dca.png) | 8/8/0; clear. | Paired upper zones are symmetric; lower zones still span multiple bays. | Official seven-hold aggregate cannot resolve the eighth record. Exact crop; geometry unchanged. |
| [`frictitious-megalith`](assets/2026-08-18-complete-hangboard-visual-audit/after/frictitious-megalith--33de4ccadb0c.png) | 9/9/0; clear. | Paired bands remain symmetric; center/mono boundaries remain coarse. | Mono count and 40 mm mapping remain blocked. Exact crop; geometry unchanged. |
| [`evolv-kilter-basic-long`](assets/2026-08-18-complete-hangboard-visual-audit/after/evolv-kilter-basic-long--ac4049aa3a2d.png) | 4/4/0; clear. | Four full-width bands are aligned but cannot distinguish jug from edges. | Jug/three-edge identity remains blocked. Exact crop; geometry unchanged. |
| [`lattice-triple-rung`](assets/2026-08-18-complete-hangboard-visual-audit/after/lattice-triple-rung--98ec533951a6.png) | 3/3/57; clear. | All three continuous edge contours remain parallel and source-aligned. | Strong source agreement; optional capacity unsupported. No visible change. |
| [`metolius-climbers-edge`](assets/2026-08-18-complete-hangboard-visual-audit/after/metolius-climbers-edge--1e84e2649b1d.png) | 11/11/0; clear. | Broad/floating rectangles remain symmetric but omit slopers and depth boundaries. | Package version and complete map remain blocked. Exact crop; geometry unchanged. |
| [`metolius-contact`](assets/2026-08-18-complete-hangboard-visual-audit/after/metolius-contact--ec276e428883.png) | 10/10/0; clear. | Paired zones remain symmetric but cross multiple numbered cavities. | Numbered source confirms incompleteness, not a safe mapping. Exact crop; geometry unchanged. |
| [`metolius-project`](assets/2026-08-18-complete-hangboard-visual-audit/after/metolius-project--5007e676de90.png) | 8/8/0; clear. | Symmetric broad regions still cross visible breaks. | Complete authoritative field map absent. Exact crop; geometry unchanged. |
| [`metolius-simulator-3d`](assets/2026-08-18-complete-hangboard-visual-audit/after/metolius-simulator-3d--ad3f6e0bbb16.png) | 7/7/0; clear. | Broad paired zones remain balanced but omit sloper/3F families. | Source inventory still exceeds modeled topology. Exact crop; geometry unchanged. |
| [`metolius.wood-grips-compact-ii`](assets/2026-08-18-complete-hangboard-visual-audit/after/metolius.wood-grips-compact-ii--ecd2a502a9db.png) | 19/19/78; clear. | Surface, shelf, deep, and shallow pieces remain tightly aligned and mirrored. | Strong aggregate source agreement; per-ID provenance remains incomplete. No visible change. |
| [`moon-armstrong`](assets/2026-08-18-complete-hangboard-visual-audit/after/moon-armstrong--3e59a2c3ad25.png) | 11/11/0; clear. | Existing regions remain symmetric but miss apparent cavities and slopers. | Artwork likely depicts the wrong model; source agreement remains blocked. Exact crop. |
| [`nature-stoak-board-iii`](assets/2026-08-18-complete-hangboard-visual-audit/after/nature-stoak-board-iii--23853bedbe8d.png) | 6/6/0; clear. | Paired bars stay symmetric; adjustable insert states are not represented. | State/depth mapping remains blocked. Exact crop; geometry unchanged. |
| [`soill-iron-palm-2`](assets/2026-08-18-complete-hangboard-visual-audit/after/soill-iron-palm-2--eb1bcad6f0bc.png) | 6/6/0; clear. | Large discs/rails remain symmetric but omit pinches, slopers, and thumb catches. | Current product completeness remains blocked. Exact crop; header now shows sourced “2.0” identity. |
| [`soill-split-palm`](assets/2026-08-18-complete-hangboard-visual-audit/after/soill-split-palm--cc07b6832b7c.png) | 2/2/0; clear. | Two mirrored zones cover multiple branches rather than physical contacts. | Authoritative inventory/map absent. Exact crop; geometry unchanged. |
| [`soill-training-tiles`](assets/2026-08-18-complete-hangboard-visual-audit/after/soill-training-tiles--073b9c42fd16.png) | 4/4/0; clear. | Large mirrored zones remain balanced but omit secondary edge progression. | First-party per-contact map absent. Exact crop; geometry unchanged. |
| [`target10a-linebreaker-base`](assets/2026-08-18-complete-hangboard-visual-audit/after/target10a-linebreaker-base--83a10cb8e4e0.png) | 11/11/0; clear. | Paired rectangles stay symmetric but float outside/cross multiple contacts. | First-party inventory map remains absent. Exact crop; geometry unchanged. |
| [`tension-grindstone`](assets/2026-08-18-complete-hangboard-visual-audit/after/tension-grindstone--4c704daf13a7.png) | 7/7/0; clear. | Paired broad rails remain symmetric but flatten the edge progression. | Published depths cannot be assigned to IDs. Exact crop; geometry unchanged. |
| [`tension-honestone`](assets/2026-08-18-complete-hangboard-visual-audit/after/tension-honestone--223e0ec49199.png) | 7/7/0; clear. | Paired regions remain balanced but omit the sloper-led source profile. | Mono mapping and retained blocked grip semantic remain unresolved. Exact crop. |
| [`tension-whetstone`](assets/2026-08-18-complete-hangboard-visual-audit/after/tension-whetstone--c085c83b3df1.png) | 7/7/0; clear. | Paired rails stay symmetric but do not express four sourced depths. | Per-ID 2F map remains absent. Exact crop; geometry unchanged. |
| [`trango-rock-prodigy-forge`](assets/2026-08-18-complete-hangboard-visual-audit/after/trango-rock-prodigy-forge--3524ced1ecba.png) | 12/12/0; clear. | Mirrored primitive zones remain balanced but miss source positions/closed crimp topology. | Non-exhaustive guide cannot complete the map. Exact crop; geometry unchanged. |
| [`trango-rock-prodigy-natural`](assets/2026-08-18-complete-hangboard-visual-audit/after/trango-rock-prodigy-natural--7f4ed5768d6a.png) | 12/12/0; clear. | Paired regions remain symmetric but still resemble Forge and omit jug/pinch variables. | Model topology remains contradicted by source. Exact crop; geometry unchanged. |
| [`trango-rock-prodigy-pivot`](assets/2026-08-18-complete-hangboard-visual-audit/after/trango-rock-prodigy-pivot--7cf9f33e474c.png) | 10/10/0; clear. | The one-view paired geometry stays symmetric but cannot express four orientations. | 22-position/orientation contract remains blocked. Exact crop; geometry unchanged. |
| [`trango.rock-prodigy-training-center`](assets/2026-08-18-complete-hangboard-visual-audit/after/trango.rock-prodigy-training-center--54f0d57dd133.png) | 24/28/302; clear. | All 10 redesigned deep/shallow/crimp pieces remain seated and mirrored; the 0.999501671 px max-error deep pair has no visible drift at 2× inspection. | Strong visible agreement for modeled contacts; variable 30+ position contract remains unresolved. Primitive change is visually indistinguishable. |
| [`yy-verticalboard-evo`](assets/2026-08-18-complete-hangboard-visual-audit/after/yy-verticalboard-evo--52da4a0e33ab.png) | 7/7/0; clear. | Seven broad paired zones stay symmetric but cover 19 sourced grips. | Complete map remains absent. Exact crop; geometry unchanged. |
| [`yy-verticalboard-first`](assets/2026-08-18-complete-hangboard-visual-audit/after/yy-verticalboard-first--8a369008547e.png) | 7/7/0; clear. | Broad paired zones remain symmetric but cannot express ten grips. | Complete map remains absent. Exact crop; geometry unchanged. |
| [`yy-verticalboard-light`](assets/2026-08-18-complete-hangboard-visual-audit/after/yy-verticalboard-light--8f078a49c3e1.png) | 7/7/0; clear. | Seven-count layout stays mirrored, but center/notch boundaries remain coarse. | Center-jug identity/map remains blocked. Exact crop; geometry unchanged. |
| [`yy-verticalboard-one`](assets/2026-08-18-complete-hangboard-visual-audit/after/yy-verticalboard-one--53c8899c8937.png) | 7/7/0; clear. | Seven broad paired zones remain symmetric but cover 15 grips. | Complete map remains absent. Exact crop; geometry unchanged. |
| [`zlagboard-evo`](assets/2026-08-18-complete-hangboard-visual-audit/after/zlagboard-evo--e51ac1a87bfb.png) | 14/14/0; clear. | Grid cavities align broadly and symmetrically; jugs/slopers are not modeled. | Model dimensions and per-ID types remain unresolved. Exact crop; geometry unchanged. |
| [`zlagboard-pro`](assets/2026-08-18-complete-hangboard-visual-audit/after/zlagboard-pro--af6b10e747d3.png) | 21/21/0; clear. | Primitive grid remains symmetric but cannot establish generation-specific jugs/slopers. | Pro 1.0 versus 2.0 remains blocked. Exact crop; geometry unchanged. |

## Validation

```sh
rtk env CONDUCTOR_WORKSPACE_NAME=audit-hangboard-fidelity python3 \
  Tools/HangboardWorkbench/capture_catalog.py \
  --repository-root "$PWD" \
  --output-root "$PWD/.context/all-board-audit/task-5-after" \
  --chrome-path '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --port 4195
# {"boards": 34, ...}; 34 full-resolution PNGs plus contact sheet

rtk diff -u \
  <(rtk jq -r '.boards[].board_id' .context/all-board-audit/task-3-before/manifest.json) \
  <(rtk jq -r '.boards[].board_id' .context/all-board-audit/task-5-after/manifest.json)
# exit 0; ordered BEFORE and AFTER board IDs identical

# From Tools/HangboardPipeline:
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=../../.context/task-2-pythonpath python3 -m pytest \
  tests/test_board_presentation.py tests/test_board_path_simplification.py \
  tests/test_board_shape_change_audit.py tests/test_board_catalog_cli.py \
  tests/test_board_geometry_derivation.py -q
# 70 passed in 22.63s

rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  Tools/HangboardWorkbench/tests/test_board_geometry.py \
  Tools/HangboardWorkbench/tests/test_board_package.py \
  Tools/HangboardWorkbench/tests/test_capture_catalog.py -q
# 84 passed in 2.03s

rtk node --test Tools/HangboardWorkbench/tests/workbench*.test.js
# 44 passed, 0 failed

rtk scripts/hangboard-tools.sh packages validate --root Hangboards
# 34 completed packages; zero drafts

rtk scripts/hangboard-tools.sh packages simplify-hold-paths --root Hangboards
# 34 boards; changed=false for every board; 1,180 editable points retained

rtk scripts/hangboard-tools.sh packages normalize-presentations --root Hangboards
# 34 boards; changed=false for every board

rtk env PYTHONPATH=.context/task-2-pythonpath python3 -m \
  hangboard_vectorizer.board_shape_change_audit \
  --repository-root . \
  --before-ref 011d718133274c2f8a948f4475a64d27dc443445 \
  --after-root .
# 34 boards / 359 holds / 363 pieces / 45 changed pieces / 710 points removed

rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' -quiet
# exit 0
```

The final shape audit reproduces maximum exact deviation 0.999501671 px and
maximum symmetric difference 0.000160231660. Both generic catalog dry runs are
post-write idempotent.

### Owned simulator visual validation

`CONDUCTOR_WORKSPACE_NAME=audit-hangboard-fidelity` was set for the complete
lifecycle. The recipe installed `EXIT`, `INT`, and `TERM` archive traps before
each create, appended the validated UUID to the pending manifest before the
owned manifest, and used only that exact UUID for boot, readiness, signed
Debug build, install, launch, container lookup, screenshot, shutdown, and
deletion. It never addressed `booted`.

The decisive run used iPhone 16 Pro / iOS 26.5 and exact UUID
`4B419042-039B-42A2-B8D7-A4E937D84274`:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=4B419042-039B-42A2-B8D7-A4E937D84274' \
  -derivedDataPath .context/DerivedData -quiet build
# xcodebuild: ok; signing enabled

rtk xcrun simctl install 4B419042-039B-42A2-B8D7-A4E937D84274 \
  .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app
rtk xcrun simctl get_app_container \
  4B419042-039B-42A2-B8D7-A4E937D84274 com.hangten.training app
# exact installed app container returned
```

The simulated entitlement contains
`com.apple.developer.healthkit = true`. The installed Info.plist prints the
non-empty read description “Hang Ten reads your Apple Health workout history
to restore your progress on a new device.” and the non-empty write description
“Hang Ten saves completed hangboard sessions to Apple Health.” Built and
installed app binaries had identical SHA-256
`e0a6a93d31d4535e3901b26c9f5d4c9a47b97ec99a3d3e7cd17c1296229f133d`.

Full-resolution runtime screenshots were retained during review under
`.context/all-board-audit/task-5-simulator/` for the zero-selection home board,
inactive rest/next-preview state, surface/jug highlight, shelf/edge highlight,
combined deep/shallow recess highlight in portrait, and the same recess state
in landscape. The landscape runtime emitted a native portrait pixel buffer;
the retained review copy was rotated 270 degrees. Inspection found exact-path
highlight alignment, consistent left/right mirroring, distinct surface/shelf/
deep/shallow treatments, and no board, timer, cue, or control clipping.

Two earlier evidence-refinement runs used UUIDs
`37B6FBF3-91CC-4EE1-AE91-86FC4415D6B7` and
`21BD6232-0A9D-401B-ACBE-F71F6770AA8A`. All three lifecycle commands exited 0.
Fresh `simctl list devices` lookup found none of the three exact UUIDs. The
pending manifest is absent, the owned manifest contains zero bytes, and the
required `.context/DerivedData`, `.context/workout-raw.png`, and
`.context/workout-landscape.png` artifacts are absent.

### Remaining limits

Simulator inspection validates rendering, orientation, signed entitlement
wiring, and deterministic DEBUG routes. It does not validate physical-device
touch/hit testing, spoken audio and audio-session interaction, real HealthKit
authorization/write metadata, cross-device Health restoration, or Bluetooth
sensor behavior. Those remain physical-device checks before release. The 27
source/geometry blockers called out in the board tables also remain deliberate
fail-closed limitations; the audit does not present their coarse geometry as
authoritative.
