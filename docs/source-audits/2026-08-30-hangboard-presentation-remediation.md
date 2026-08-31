# Hangboard Presentation Remediation Phase 1 Source Audit

## 2026-08-31 Evolv/Kilter Basic Training Board (Long) material correction

This correction covers every declared presentation of
`evolv-kilter-basic-long`: `board.json` declares exactly one presentation,
`primary` (`Primary`, default), at `assets/primary.png`. There is no reverse,
side, alternate mounting position, or other selectable orientation in this
package. The one asset remains orthographic to its own front working surface;
its four horizontal contact bands are parallel, its two ends are equally
foreshortened, and no side plane or angled installation view is visible.

Live evidence was searched and reopened on 2026-08-31. Evolv's current
[official Basic Training Board (Long) page](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105)
explicitly specifies `Color: BLACK`, resin material, 79 x 16 x 6 cm long-board
dimensions, and the complete four-contact inventory: rounded jug plus 20, 15,
and 10 mm rounded edges. Its published straight-on and detail images show a
dark, subtly mottled resin body with the same top jug and three full-width
lower edge bands. The independent
[Backcountry product listing and gallery](https://www.backcountry.com/evolv-basic-training-board)
independently publishes the black resin/Kilter Grip treatment, the same
four-band silhouette in straight-on and oblique photos, and the distinct long
31 x 6.25 x 2.25 inch size. The independent ended
[eBay long-board listing](https://www.ebay.com/itm/326431990533) additionally
identifies the exact long Evolv product and its black exterior. The original
catalog geometry and head-on composition therefore conformed, but its white
material color contradicted both official and independent published evidence.

The original 1537 x 1023 RGBA asset had SHA-256
`b9c91bc7f4e31db5883a8025b407851c25fd3b6d16a9b9e0e9e41d2a64302bfc`.
The corrected 1537 x 1023 RGBA asset has SHA-256
`c4bf068b612398b6243928dbafbfd42d32e0bf5ceab036f08e44f160ab790d13`.
The bounded deterministic transform decoded the existing premultiplied-sRGB
pixels, used the authored alpha channel as the sole product boundary, and
applied one global neutral-black tone mapping to every nontransparent authored
pixel: `round(6 + 42 * luminance^1.55)`. It then source-over composited those
remapped product pixels and their unchanged authored alpha edges onto the
shared `#F6F2EA` studio background and flattened the result. This preserves
the original silhouette, soft cast shadow, rounded resin relief, fine surface
texture, four-contact topology, rail separation, framing, and head-on geometry
while correcting white material to the source-published charcoal-black resin.
There was no resize, crop, padding, warp, perspective correction, blur,
denoising, segmentation, generated mask or contour, registration, redraw,
replacement geometry, or generated product pixel.

`board.json` remained byte-identical at SHA-256
`e5b3f56250ad09b9565d56c04a940d7ddb8fcb6c936da850dec086e3822bbe5f`.
The final owned headless Workbench capture
`evolv-kilter-basic-long--ac4049aa3a2d.png` visibly aligns all four labeled
canonical paths (`jug-rounded`, `edge-20`, `edge-15`, and `edge-10`) with their
corresponding contact bands. Both `scripts/hangboard-packages.sh validate
--root Hangboards --final-inventory` and `scripts/hangboard-packages.sh status
--root Hangboards` passed with 61 complete packages and zero drafts. The
machine remediation manifest is intentionally unchanged for the later
consolidated lifecycle pass.

## 2026-08-31 Tension Grindstone Pro deterministic presentation repair — evidence blocked

This repair covers every declared presentation of `tension.grindstone-pro`:
`board.json` declares exactly one presentation, `primary` (`Primary`, default),
at `assets/primary.png`. There is no reverse, side, mounting-orientation, or
other selectable presentation in this package, and this finding makes no claim
about the original Grindstone, Mk2/current Grindstone, or another Tension
model.

Live evidence was searched and reopened on 2026-08-31. Tension's current
[official hangboards page](https://tensionclimbing.com/pages/hangboards)
confirms the manufacturer's wood-board family treatment, signature rounded
edge profiles, and asymmetric spacing approach; the exact historical
`https://www.tensionclimbing.com/hangboards/grindstone-pro` route is no longer
available. The contemporaneous [Power Company interview with Tension founders
Will Anglin and Ben Spannuth](https://www.powercompanyclimbing.com/blog/2017/7/5/episode-49-a-better-strip-of-wood-with-tension-climbing)
identifies the 2017 Grindstone Pro's 35/20/15/10 mm progression, 30 and 22 mm
center edges, mono and two-finger pockets, 7 mm incut, phone slot, and
deliberately asymmetric spacing. It is a third-party editorial host for
first-party founder testimony, not independent photographic evidence.

The 2017 [Climbing product
page](https://www.climbing.com/gear/sponsor-content-climbing-holiday-gift-guide-tension-climbing-grindstone-pro-hangboard/)
does publish the exact Pro's complete wooden front face and 4/7/5 contact-row
topology. However, the page is explicitly titled `Sponsored`, is bylined
`Tension Climbing`, and appears in Climbing's holiday guide as `Sponsored:
Tension Climbing Grindstone Pro Hangboard`; its photo is therefore classified
as manufacturer/sponsored evidence, not independent or unofficial evidence.
The independent [Gear Institute launch
coverage](https://gearinstitute.com/sneak-peek-the-climbing-gear-that-won-t-be-at-outdoor-retailer/)
and [Gripped Magazine comparison](https://gripped.com/indoor-climbing/three-of-the-best-hangboards-for-at-home-training/)
corroborate the exact historical Pro in editorial text, but the former does not
publish a visible exact-board photo and the latter embeds Tension Climbing's
own Instagram post. Climbing's independent [Team USA training-lab
feature](https://www.climbing.com/competition/olympics/inside-training-lab-team-usa/)
states that a Grindstone Pro is installed and credits its photographs to Jess
Talley/Louder Than 11, but inspection of the three published article photos
found that none shows the hangboard. Bounded exact-name searches of reviews,
owner discussions, used listings, gym installations, and image results found
no accessible, genuinely independent published photo in which this exact
4/7/5 Pro revision is visible.

Against the available manufacturer/sponsored photograph, the catalog asset's
wood material, silhouette, opening count, relative placement, and asymmetric
front working face conform. It is genuinely head-on to that working face,
with parallel horizontal tiers and no visible side plane, and its uniform
soft, pale-wood smoothing treatment conforms; no smoothing or product-pixel
filter was applied. The independent/unofficial published-picture requirement
is nevertheless unsatisfied, so full acceptance is **BLOCKED** pending a
genuine independent photograph of this exact 2017 Pro revision.

The parent-commit asset was independently re-extracted and verified as 1654 ×
951 pixels with SHA-256
`9c252286a19c379236574e703b61ec8b92b5443b54f9c9bce5dcb774a901e1de`.
The accepted asset remains 1654 × 951 pixels and has SHA-256
`6682e9a2f019ac6ca345cfa7aca376a988b15bb408664e15dbd0ee181c3e23d1`.
The sole deterministic transform decoded the current PNG as premultiplied sRGB
and source-over composited its existing alpha onto `#F6F2EA`; every output
pixel is opaque. There was no resize, crop, padding, warp, perspective
correction, registration, segmentation, inferred mask, redraw, replacement
product pixel, sharpening, denoising, or other filter. `board.json` remained
byte-identical at SHA-256
`75182723b4a04ffdacecd51722dd0c1ee6f28d3f639ee0c420b69053978585c4`.

Both `scripts/hangboard-packages.sh validate --root Hangboards
--final-inventory` and `scripts/hangboard-packages.sh status --root Hangboards`
passed with 61 complete packages and zero drafts. The normal Workbench catalog
capture was exercised against the changed checkout; a target-only follow-up in
a minimized symlink repository exited during server startup, so no new
target-specific labeled screenshot or interactive active/hit-test result is
claimed. Because the canvas dimensions, presentation aspect ratio, and
`board.json` geometry bytes are unchanged, this alpha-only composition cannot
move a canonical path relative to any product pixel. The machine remediation
manifest is intentionally unchanged for the later consolidated lifecycle pass.
The deterministic PNG may remain in place, but this section does not claim
that the Tension presentation has passed the full official-plus-unofficial
evidence requirement; its acceptance state is **BLOCKED**.

## 2026-08-31 Beastmaker 1000 deterministic presentation repair

This narrowly scoped, user-approved deterministic exception repairs only
`beastmaker-1000/primary`; it makes no claim about another Beastmaker model,
revision, variation, or orientation. Live evidence was reopened on 2026-08-31:
the [official Beastmaker 1000 Series product page](https://www.beastmaker.co.uk/products/beastmaker-1000-series)
identifies the current wood board, its jugs, slopers, pocket families, and six
installation screws; the independent [The Hangboard review](https://thehangboard.com/blogs/news/beastmaker-1000-review)
corroborates the 580 × 150 × 58 mm wood layout, identical beech/tulipwood hold
layout, and symmetric front face. Those sources and side-by-side review with
`Hangboards/beastmaker-2000/assets/primary.png` confirm this package's one
Primary presentation is already head-on to its own front working surface.

The original asset was 1000 × 259 pixels with SHA-256
`8d89a500122aac4d5bb4bb03c47202f881fd8cf66f9a321b620507dccad36289`.
The accepted asset is the same 1000 × 259 canvas with SHA-256
`3327fe6ab4527b16003861b17c23fca07de402fb46672555a67221aa03dfb7d7`.
The exact deterministic command was
`swift .context/sincere-otter-beastmaker-1000-deterministic/repair.swift Hangboards/beastmaker-1000/assets/primary.png <product-exact.png> <candidate.png>`.
It uses the existing source alpha only for Core Image source-over compositing
of the exact current product pixels onto the uniform catalog field `#F6F2EA`.
No resize, crop of source pixels, padding, warp, perspective correction,
registration, geometry inference, redraw, replacement product pixels, or
source-photo substitution occurred. The accepted transform has **no image
filter** (zero passes). A single allowed trial of `CINoiseReduction`
(`inputNoiseLevel = 0.002`, `inputSharpness = 0.0`) was rejected because it
changed source alpha. The accepted path compares the full decoded RGBA product
buffer and alpha bytes before compositing; that passed, preserving the
silhouette, all six mounting openings, hold/recess topology, wood grain
direction, and head-on geometry.

Workbench's owned loopback server and headless catalog capture completed with
all 22 Beastmaker 1000 hold paths visibly aligned in the normal labeled capture.
The environment exposed no controllable browser window, so manual all-active,
individual interactive activation, and hit-testing could not be exercised and
are explicitly not claimed. `board.json` remained byte-identical. Passed checks:
`scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`,
`scripts/hangboard-packages.sh status --root Hangboards`, and the direct
19 keep-hash audit against each `currentAsset.sha256`, plus
`uv run --with pytest --with Pillow python -m pytest -q Tools/HangboardPackages/tests/test_beastmaker_depth_metadata.py`
(4 passed). The broader presentation/approved-package pytest selection was
stopped without a result after prolonged silence and is not recorded as passed.
The machine remediation manifest was deliberately not changed, so its full
Phase 2 lifecycle audit correctly remains pending and rejects this newly
accepted on-disk edit as an action without recorded completion. This repair
follows rejection of the prior topology-drifting image-generation candidates;
no image-generation tool was used here.

## Scope and result contract

This audit covers the 61 current packages and 85 declared presentation PNGs. Phase 1 records live-web evidence and a remediation decision only; it changes no PNG and no board.json.

## Evidence method

Search each exact manufacturer/product/revision independently. Open and cite direct official and independent HTTPS pages, inspect straight-on and oblique published pictures, and record only claims those pages establish. Local documentation and current package metadata are navigation aids, not evidence.

## Decision legend

- `keep`: current bytes conform, or remain explicitly evidence-blocked without a final acceptance claim.
- `edit`: verified topology is suitable for a bounded Phase 2 material, perspective, or treatment correction.
- `regenerate`: verified silhouette, revision, or working-surface topology requires a new Phase 2 render.
- `removeUnsupportedPresentation`: sources establish that a declared presentation is not a usable surface; removal waits for Phase 2.
- `splitPhysicalRevision`: sources establish distinct physical revisions that cannot truthfully share one package; splitting waits for Phase 2.

## Lane completion

| Lane | Packages | Assets | Status |
| --- | ---: | ---: | --- |
| A — Aelith through Mammut | 20 | 27 | Complete — 20 packages / 27 assets |
| B — Metolius through So iLL | 19 | 24 | Complete — 19 packages / 24 assets |
| C — target10a through Zlagboard | 22 | 34 | Complete — 22 packages / 34 assets |

## Revision, source-conflict, and unsupported-surface resolutions

Resolutions are added only when direct live sources establish the named revisions or surface use.

- `aelith.cyclops-011/primary` remains an evidence-blocked `keep`: the exact
  manufacturer product URL is stale and returns 404, and fresh exact-model
  searches found no live independent review, retailer page, or owner view that
  proves the #011 Blue x Black physical revision.
- `dewoodstok-woodbord/primary` remains an evidence-blocked `keep`: a live
  independent retailer establishes the bamboo Woodbord and its hold inventory,
  but fresh manufacturer-domain, manual, catalog, and archive searches found no
  live or archived first-party page for the exact physical revision. The
  retailer also shows five mounting positions and supplied screws that the
  current image omits, so component topology remains explicitly uncertain.
- Both `crimptonite.helium-mobile` presentations are `edit`. The official
  gallery establishes that the primary's three recesses realize the current
  edge inventory, while the reverse contains the published jug/sloper but does
  not resolve it head-on. A verified owner measured the nominal 22 mm edge at
  20 mm and the 14 mm edge near 13 mm, and reported rough side finishing with
  smooth finger contacts; that specimen-level depth/finish conflict remains a
  Phase 2 source constraint rather than a universal production claim.
- DUAL primary/reverse, POCKET primary, UNLEVEL primary/reverse, and both NUG
  faces are `regenerate`: although their wood contacts are recognizable, the
  source-confirmed portable component topology includes suspension rope that
  the current assets omit. Escape Unlimited is also `regenerate` because four
  published mounting positions and associated hardware are omitted. DoorMount
  Pro 7 remains `regenerate` because the complete metal/rubber clamp assembly
  is absent. Mammut Diamond Finger is `regenerate` because its mounting plate,
  published phone mount, and complete product topology must be restored.
- Beastmaker 1000, all three Port-A-Board faces, and both MXEdge Lift variants
  are Phase 2 edits: their verified geometry is preserved, but
  transparent/photo-like, labeled, branded, or cropped treatments do not
  satisfy the simplified unbranded studio contract.
- Exact independent product coverage for NUG and Port-A-Board now comes from
  The Hangboard's direct portable-hangboard review instead of the generic
  Shop.app seller storefront. Evolv Long uses an exact Backcountry variant
  listing, and Escape Unlimited uses an exact retailer listing whose product
  imagery and customer reports establish mounting positions and screws. The
  independent NUG/Port review reports poplar. The current official regional
  pages conflict: the US storefront specifies beech, while the Canadian
  storefront specifies durable poplar. The review is therefore used only for
  identity, grip inventory, and cord corroboration; this package follows the US
  beech listing and exact US official assets for the represented variant, while
  the live regional species conflict remains unresolved and recorded.
- `lattice.mini-bar/end` is `removeUnsupportedPresentation`: Lattice and an
  independent retailer identify four lengthwise grips selected by flipping the
  bar, while the declared end cap is not a usable working surface. Removal is a
  Phase 2 action; this audit changes no package inventory.
- Lane A classification: 6 `keep` records (2 evidence-blocked), 10 `edit`,
  10 `regenerate`, and 1 `removeUnsupportedPresentation`.
- Climber's Edge, Contact, Foundry, Project, and Simulator 3-D are
  `regenerate`: current broad silhouettes may be recognizable in places, but
  the cited exact revisions establish different rail, pinch, pocket, sloper,
  jug, mounting-hole, or material topology. The exact Dick's Climbing Foundry
  listing, rather than the earlier generic Backcountry material attribution,
  supplies the explicit resin claim; Metolius supplies the exact geometry but
  does not name the chemistry. Prime Rib and Wood Grips II Deluxe
  are accepted `keep` baselines. Compact II is `regenerate` because the
  source-confirmed production mounting points are absent from its topology.
- The Light Rail 2.0 15 mm side remains an `edit`: its source-confirmed working
  surface is orthographic and legible, but its suspension cord is cropped. The
  nominal 20 mm side is `regenerate` because Metolius's current 20 mm label and
  REI's 19/26 mm production depth list leave its exact topology uncertain. Both
  sources otherwise agree on a four-position reversible FSC-wood rail. Rock
  Rings 3D is also `regenerate` because both complete cords and knots are
  missing from the source-confirmed topology and its polyester-resin treatment
  is false.
- Armstrong Beech SKU 60-112-BEC is `edit`: exact first-party and retailer
  sources prove the current hardwood geometry, but the current asset is an
  underscaled branded, depth-labeled photograph rather than the unbranded
  studio treatment.
- Stoak Board III Oak is `regenerate` because its source-confirmed mounting and
  magnetic component topology must be restored while preserving FSC oak and
  visibly real recycled Norwegian granite; its independent evidence is the
  exact 2026 Grimpeez Stoak Board III Oak comparison rather than the generic
  Loox storefront. The evidence-complete
  KARMA8A collaboration remains the unique accepted mixed-material
  multi-orientation cohort and uses its own current presentation as the style
  baseline. Stone Hanger Mini Beech primary and its 60 mm pinch side are
  accepted `keep` records: the exact canonical official page and the live exact
  Varun retailer listing corroborate Beech, real granite, the rope-adjusted
  portable assembly, both 15 mm lengthwise edges, and the 60 mm pinch end. Both
  use accepted KARMA8A only as a same-material, same-form-factor style baseline.
- All four Poker working faces were independently checked against the exact
  four-face grip inventory and pass the strict head-on topology test. The audit
  retains the visibly supported flat-center, deep-sloper, shallow half-round,
  and deep rounded-recess topologies. Local face IDs A–D are analyst mappings
  to published gallery views, not manufacturer numeric face labels; the
  published 25/20/15/10 mm outer-slot and 40/30/25/20 mm mono/bi sequences;
  its central area is only a 15–30 mm range. Oliunìd, not Owl, publishes the
  exact 30/25/20/15 mm center-depth sequence. All remain board-level
  specifications and are not
  assigned to those local face IDs. Each is `edit` only for the engraved Owl
  mark. The direct first-party route again timed out during final-review
  re-opening, while the live indexed Owl page and cited 2026-05-17 Owl Climb
  archive snapshot both publish 660 × 100 × 100 mm and separately say supports
  or brackets are supplied. Oliunìd labels 68 × 14 × 12 cm as hangboard
  dimensions. Neither source states whether its dimensions cover only the bar
  or the installed/supported assembly. Bar-only versus installed/supported-
  assembly scope may explain the difference; this is an analyst inference and
  does not alter face geometry.
- Plateau Lifting Edge is `regenerate`: the aluminum body and oak insert are
  recognizable, but the cited 3D-printed 15/10 mm blocker and complete 6 mm
  Edelrid PES cord are omitted from the source-confirmed product topology.
  Fresh exact-model searches found no independent direct review,
  retailer, or owner page proving this Oak configuration, so the independent
  evidence gap remains explicit.
- Iron Palm 2.0 is `regenerate`: So iLL publishes 40/35/15 mm rails while
  Backcountry publishes 40/25/15 mm for the same exact product, leaving its
  exact topology uncertain in addition to the transparent-cutout defect. Only
  Backcountry is used for the urethane claim because the So iLL Canada page
  does not name the material. Split Palm and the So iLL x Meagan Martin
  Training Tiles are `regenerate`, not accepted keeps: both current renders
  omit source-confirmed production mounting points and hardware context. Split
  Palm's urethane claim comes from the exact So iLL US
  page's urethane-items disclaimer, while Klatredepot supports only its direct
  topology and dimensions. Training Tiles' Canada page supports topology,
  dimensions, and hardware, while OutdoorGearLab supplies the independent
  urethane claim. No ready accepted urethane split-fixed-board comparator
  remains for either Phase 2 repair.
- Lane B classification: 5 `keep`, 6 `edit`, and 13 `regenerate` records. The
  validated lane report contains 19 packages and 24 presentations; all five
  keeps are accepted current assets, all nineteen repairs remain pending Phase
  2, and Plateau primary is the lane's only evidence-blocked asset.
- Linebreaker BASE is an accepted `keep`: the opened exact target10a
  manufacturer article establishes Yellow Poplar and the complete BASE layout.
  Basislager independently corroborates the layout, individual grip depths,
  58 cm length, 15 cm height, and 1.7 kg weight. Its erroneous 55 cm
  product-depth field is excluded; the correct 5.5 cm depth and Yellow Poplar
  species are supported only by target10a.
- Flash Board remediation completed 2026-08-31. The current
  [Tension product page](https://tensionclimbing.com/products/flash-board-2)
  identifies a compact cylindrical board, calls the smallest contacts `Small
  Crimps`, and separately names 8/10/15/20 mm; no 6 mm claim is retained. Its
  live first-party
  [`FlashBoard2.png`](https://tensionclimbing.com/cdn/shop/files/FlashBoard2.png?v=1726542491&width=2048)
  supplies the straight-on three-edge face and confirms pale wood, the rounded
  cylinder, paired end cord passages, and the over/under cord wrap. The current
  [Mad Rock distributor page](https://madrock.com/products/tension-climbing-flash-hangboard)
  independently republishes that same straight-on three-edge product shot and
  repeats the cylindrical construction and five named edge classes. The
  published So iLL retailer asset
  [`809198`](https://soillholds.com/cdn/shop/products/tension-flash-board-so-ill-so-ill-809198_2000x.jpg?v=1677258525)
  supplies the straight-on two-edge/logo face with the complete adjustable cord
  loop, visible knot, tails, four passage points, and lower end wraps; its former
  product page now returns 404, so it is treated as archival image evidence and
  not as current metadata. The independent
  [Treeline tested review](https://www.treelinereview.com/gearreviews/best-hangboards-for-climbing)
  corroborates wood, edges on both faces, eight usable edge positions, and the
  adjustable dual-cord routing through and around the cylinder. By explicit
  product-presentation choice, all four catalog rasters are board-only views:
  the suspension cord and hardware are omitted so each orientation is
  unambiguous and no inverted view shows physically misleading dangling cord.
  These are therefore faithful catalog renders of the verified wooden body and
  working-surface topology, not complete-assembly photographs. The upright
  three-edge and two-edge base rasters retain their verified head-on geometry,
  material, lighting, and framing; bounded edits at the four end-cord regions
  reconstruct continuous natural wood and the empty passage holes. The package
  represents all four working orientations independently: three-edge upright,
  its exact 180° decoded-pixel rotation, two-edge upright, and its exact 180°
  decoded-pixel rotation. All four share the same smooth studio treatment and
  off-white background.
- The 2017 base Grindstone is `regenerate`, not a background-only edit. The
  launch-period founder interview describes jugs plus paired
  35/30/25/20/15 mm edges and central 50/22 mm edges, and explicitly reserves
  mono/two-finger pockets and increased row offset for the Pro. The current
  pocket-heavy PNG therefore has the wrong physical-revision topology. The
  unsubstantiated Reddit owner-photo mapping was removed. The separate
  Grindstone Pro remains the lane's sole `edit`, for its transparent cutout;
  both discontinued
  revisions retain explicit first-party gaps. Current Grindstone Mk2,
  Honestone, and Whetstone remain accepted `keep`s, with Honestone now backed by
  the opened direct Climbing hands-on review rather than the unavailable Yahoo
  syndication URL.
- The Hangboard is an accepted wood-board `keep`. Forge, Natural, all four
  Pivot orientations, and the Rock Prodigy Training Center are `regenerate`
  because their source-confirmed component or working-surface topology is
  incomplete. Natural needs its complete cleat/fastener assembly and studio
  background. Forge, Pivot, and Training Center also need controlled relief
  shading appropriate to molded polyurethane because the current
  white-on-white recess depth is materially weak. Pivot's quick-start guide
  separately establishes all four rotations and the quad-cleat assembly.
  Training Center must restore body mounting-point/installed context without
  depicting screws as supplied; Trango explicitly excludes mounting hardware.
- Baguette Evo's rounded-tray view and both classic La Baguette faces remain
  accepted `keep`s. The other four Baguette Evo surfaces, Penta Evo, and both
  TravelBoard faces are `regenerate` because their source-confirmed portable
  component topology includes complete cords that the current assets omit. The
  earlier/different
  5 mm/12–5 mm/415 g Max Climbing configuration was replaced by an opened exact
  current Varuste Evo listing that corroborates 6–30 mm, 52 cm, and 550 g;
  YY Vertical governs exact surface distribution. The stale classic Varuste
  redirect was replaced by Lockwoods' opened exact La Baguette page. Current YY
  documentation supplies polyester cord, and the untraceable polyamide claim
  was removed. Penta Evo's current page separately conflicts between an
  eight-grip heading and seven-technical-grip body copy; the audit preserves
  that count conflict instead of assigning either number to the presentation.
- All four VerticalBoard models are `regenerate`, with revision-specific
  component topology. Evo must preserve two included -10 mm magnetic wedges, their integrated
  side storage, and hidden-anchor/inserts six-screw mounting without invented
  front holes. First includes four wall screws while magnetic inserts are
  optional and not included. Light's raw official page was not parseable, so
  its claim is limited to the exact same-URL first-party extraction plus the
  opened Rock+Run support for seven grips and four-point installation. One must
  preserve its two included wedges, integrated storage, hidden inserts, and
  four-screw system. TravelBoard separately retains the source conflict between
  introductory `beech` and detailed first-party/independent recycled
  rubberwood claims.
- Zlagboard.Evo and Zlagboard.Pro 2.0 are `regenerate`: the current bare wood
  rails omit the source-published electronic/metal assembly, including steel
  support, plates, phone interface, and fasteners, so the physical topology and
  mixed-material identity are not repairable as a bounded edit. Current
  Zlagboard copy calls all Zlagboards noble lime, while an undated exact
  Sestogrado Evo listing describes alder on a steel frame. The listing does not
  establish that alder belongs to the same current revision, so the manifest
  preserves the mixed construction without choosing a species. BananaFingers
  is used only for the compact Evo, silicone phone mount, and three eye bolts;
  metal support/components come solely from official evidence.
- Lane C classification: 8 `keep`, 1 `edit`, and 25 `regenerate` records. The
  validated lane report contains exactly 22 packages and 34 presentations; all
  eight keeps are accepted current assets, and all twenty-six repairs remain
  pending Phase 2.

## Final classification totals

The reconciled validator report covers 61 packages and 85 presentations:

| Decision | Count |
| --- | ---: |
| `keep` | 19 |
| `edit` | 17 |
| `regenerate` | 48 |
| `removeUnsupportedPresentation` | 1 |
| `splitPhysicalRevision` | 0 |
| **Total** | **85** |

The sole removal remains `lattice.mini-bar/end`: direct sources establish that
its declared end cap is not a usable working surface. No record has sufficient
two-revision evidence for `splitPhysicalRevision`; no package inventory changes
in Phase 1.

The validator's explicitly evidence-blocked paths are:

- `Hangboards/aelith-cyclops-011/assets/primary.png`
- `Hangboards/dewoodstok-woodbord/assets/primary.png`
- `Hangboards/plateau-lifting-edge/assets/primary.png`
- `Hangboards/tension-grindstone-original/assets/primary.png`
- `Hangboards/tension-grindstone-pro/assets/primary.png`

All 17 accepted `keep` records have a matching current SHA-256/dimensions,
seven conforming findings, complete official and independent evidence, and a
ready accepted cohort comparator. The two evidence-blocked `keep` records
retain null final output, `blockedEvidence`, an `uncertain` finding, and the
exact evidence gap in their manifest records. The remaining three
evidence-blocked assets are Phase 2 repairs. Every non-keep record has null
final output and either a ready accepted comparator or an explicit repair-only
cohort gap.

## Phase 1 verification

The following Phase 1 checks were run on 2026-08-31 and passed:

```bash
rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q \
  Tools/HangboardPackages/tests
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh audit-presentations \
  --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --final-validation
rtk git diff --name-only 2e74fc8..HEAD -- Hangboards
rtk git diff --name-only -- Hangboards
```

The full package-tool suite passed (383 tests). Final inventory validation
returned successfully with 61 valid packages and no draft inventory. Manifest
validation returned 61 packages and 85 presentations with 19 `keep`, 17
`edit`, 48 `regenerate`, and 1 `removeUnsupportedPresentation` decisions.
Both `Hangboards` diff commands produced no paths, proving that no Hangboards
PNG or `board.json` changed from approved-spec commit `2e74fc8` through this
Phase 1 verification, or in the working tree.

## Phase 2 lifecycle baseline

Phase 2 baseline SHA: 257287636d2b0c1ac0877b01435a68d61b4a97d2

Schema 2 preserves the Phase 1 record order and every historical identity,
classification, finding, evidence, current-asset, and comparator field. It adds
a separate Phase 2 action/evidence/comparator lifecycle. The initial ledger has
19 factual `notRequired` keep actions and 66 pending actions: 17 edits, 48
regenerations, and the one sourced Mini Bar end-presentation removal. The 17
source-supported keeps retain their accepted hashes and dimensions; only the
Aelith Cyclops #011 and deWOODSTOK Woodbord keeps retain null accepted values
and `blockedEvidence`. All five historical evidence-gap strings remain Phase 1
history and do not count as Phase 2 action blocks.

## Phase 2 transient resource contract

Copied source inputs, built-in outputs, and disposable capability artifacts are
temporary resources. Their literal paths and SHA-256 values are verified while
bytes exist, then their passed byte-verification records remain durable after
cleanup. Untouched PNG signature and IHDR facts are the only image-byte facts
the validator reads. Post-processing is always `none`; capability artifacts are
always `capabilityProbeRejected`, production-forbidden, separately recorded,
and deleted. Their hashes and both returned/transient paths are globally
disjoint from production inputs, candidates, comparators, final hashes, and
accepted assets in preflight, partial, and final validation.

## Phase 2 comparator contract

The Phase 1 `comparator` object is unchanged classification history. Production
generation uses the separate `phase2Comparator`: either an accepted singular
baseline from order zero or a strictly earlier completed repair, or the exact
production-only nine-seed bootstrap table. Singular dependencies are acyclic
and style-only. Bootstrap axes separately govern composition/framing/scale and
material texture/lighting, explicitly list unavailable axes, and become a
cohort baseline only after evidence, visual, Workbench, and package review all
pass. Temporary gaps and disposable preflight references never authorize a
production generation.

## Exact-canvas preflight baseline

The initial preflight contains 20 unique canvas classes that partition all 65
edit/regenerate record keys and 22 behavior probes (separate edit/generate
probes for the two mixed-mode classes). Its only optional composition references
are the accepted Beastmaker 2000 primary and Lattice Mini Bar primary assets;
the material axis is unavailable for every probe and live evidence plus the
closed material contract governs the disposable subject. All classes and probes
begin pending with zero capability artifacts. This preflight tests only whether
the built-in tool can return untouched exact IHDR dimensions; it makes no
likeness, material, Workbench, promotion, or cohort-baseline claim.

## Initial Phase 2 validation state

The schema-2 preflight and partial validators report 61 packages, 85 historical
and current presentations, 19 keeps, 65 pending image repairs, one pending
removal, two historical evidence-blocked keeps, zero Phase 2 blocks, 20 canvas
classes covering 65 repair keys, and zero capability artifacts. Mini Bar primary
retains its historical primary self-baseline; the pending removal does not alter
its PNG, `board.json`, presentation inventory, or `mini-pinch` assignment.

## Owl Climb Poker four-face disposition correction (2026-08-31)

The complete `owl-climb-poker` presentation set was freshly re-reviewed as one
atomic four-face product on 2026-08-31. The manufacturer identifies Poker as a
660 x 100 x 100 mm tulipwood (`Toulipier`) bar whose four working faces are
selected by rotating the bar in its brackets. The independent WOGU review also
describes the same parallelepiped board as usable on all four faces, with the
outer slots and one-/two-finger pockets changing depth by face and with two
35-degree planes plus two 100 mm half-rounds in the center. Oliunìd's current
listing independently corroborates the four rotations, tulipwood construction,
outer edge depths, mono/bi-finger depth sequence, center one-arm feature, and
supplied black brackets. Its published four-view gallery shows the light wood,
black end brackets, centered owl engraving, outer slot/pocket groups, and the
four different center treatments. The face letters below remain local analyst
mappings; neither publisher labels the rotations A-D.

Freshly opened evidence:

- Owl Climb manufacturer page:
  <https://owlclimb.com/index.php/en/prds-2/poker/>
- Oliunìd product listing and four-view published gallery:
  <https://www.oliunid.com/owl-climb-poker-climbing-hangboard>
- Oliunìd independent product review (2020-03-18):
  <https://www.oliunid.it/blog/ti-presentiamo-il-trave-poker-di-owl-climb-oliunid-is-recensione-prodotto/>
- WOGU independent Owl Climb review (2019-04-17):
  <https://woguclimbing.com/review-owl-climb-accesorios-entrenamiento-escalada/>
- Published retailer face images inspected at original resolution:
  <https://www.oliunid.com/media/catalog/product/o/w/owlclimb_poker19_0.jpg>,
  <https://www.oliunid.com/media/catalog/product/o/w/owlclimb_poker19_1.jpg>,
  <https://www.oliunid.com/media/catalog/product/o/w/owlclimb_poker19_2.jpg>, and
  <https://www.oliunid.com/media/catalog/product/o/w/owlclimb_poker19_3.jpg>.

All four declared presentations were enumerated from `board.json` and reviewed
independently against their own working surface. Each asset is a 1980 x 300,
8-bit RGB, sRGB PNG with no alpha channel. Every face is orthographic to its own
front working plane: the long axis and top/bottom edges remain horizontal, the
end brackets have equal vertical treatment, paired outer contacts remain
bilaterally aligned, and no face uses a three-quarter or oblique product view.
The four assets use one consistent pale-tulipwood grain, recessed-hold lighting,
black-bracket treatment, off-white studio field, and smoothing level. Their owl
engravings are product-faithful: the engraving is present across the published
gallery, so removing it to satisfy the earlier internal `unbranded studio`
reason would conflict with the user's published-likeness requirement.

| Presentation | Declared asset | Scoped holds | Material / likeness / head-on finding | Old SHA-256 | New SHA-256 | Dimensions | Exact transform |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| `face-a` — flat center (default) | `assets/face-a.png` | 7 | Tulipwood; source-faithful four-face Poker layout and engraving; independently head-on to face A | `ddadd81e2fff9b4ca467d0320d53a496035b2131e905f76e0231c7ea2dc45028` | same | 1980 x 300 | none (accepted no-op) |
| `face-b` — deep slopers | `assets/face-b.png` | 9 | Tulipwood; published deep-plane center treatment, outer contacts, brackets, and engraving; independently head-on to face B | `5b33ce95315224a37fa13d83062cfbdab27d514d8922b65d06c0368bcd1523de` | same | 1980 x 300 | none (accepted no-op) |
| `face-c` — shallow half-rounds | `assets/face-c.png` | 9 | Tulipwood; manufacturer-described half-round center treatment with published outer contacts and engraving; independently head-on to face C | `e4f9990a71eced298dfb3f2c881ee7c3b29bfe76a191e751d632fb6f159e45dd` | same | 1980 x 300 | none (accepted no-op) |
| `face-d` — deep rounded recesses | `assets/face-d.png` | 9 | Tulipwood; source-faithful rounded center treatment, outer contacts, brackets, and engraving; independently head-on to face D | `ee9f4d928416a008b9a784631549d15ce675e32fb6771ad5bf67ad2627024e02` | same | 1980 x 300 | none (accepted no-op) |

No raster mutation was justified. The files are opaque, so the approved
existing-alpha composite cannot apply; a blur/noise filter would alter product
pixels without correcting material, likeness, perspective, or consistency.
No crop, resize, padding, warp, mask, segmentation, registration, redraw,
generated pixel, or re-encoding-only image diff was made. `board.json` remains
byte-identical at SHA-256
`808236bdef4826ae2db59c261b67440042c9d446adec208ec0ca2630d1b2452c`.
This source-backed correction accepts all four presentations together as
no-ops under the user's material, published-likeness, head-on, and uniform
smoothing requirements; the schema-2 machine manifest is intentionally not
updated in this bounded pass.

## Crimptonite Helium Mobile four-position repair (2026-08-31)

The complete Helium Mobile was freshly re-researched and repaired as one
atomic two-surface, four-position product on 2026-08-31. Crimptonite's current
page identifies a 400 x 58 x 24 mm, approximately 125 g wooden mobile board
with 14 mm, 22 mm, 10/18 mm center edges, a top jug, and a back usable as a
jug or sloper. Its current gallery publishes the front, back, and end profile.
The 9c Bouldering listing independently publishes the same front/back product,
dimensions, four edge sizes, suspension system, and back jug/sloper use. Its
customer review independently reports that the edge angle changes with the
hang configuration. The front engravings themselves establish the mutually
exclusive rotations: 14/10 mm read upright in one position and 22/18 mm read
upright after a 180-degree rotation. The published end profile and broad back
face establish the two opposite rear-edge treatments: rounded/sloping edge
upright and sharper jug edge after inversion.

Freshly opened evidence:

- Crimptonite official product page:
  <https://crimptonite.com/product/helium-mobile/>
- Current official front, back, and end-profile gallery inputs:
  <https://crimptonite.com/wp-content/uploads/2026/01/DSCF6544-1.jpg>,
  <https://crimptonite.com/wp-content/uploads/2026/01/DSCF6545-1.jpg>, and
  <https://crimptonite.com/wp-content/uploads/2026/01/DSCF6546-1.jpg>.
- 9c Bouldering independent listing, gallery, and customer image/review:
  <https://9cbouldering.com/products/helium-mobile-hangboard>,
  <https://9cbouldering.com/cdn/shop/products/Helium--mobile-hangboard-by-Crimptonite_06.jpg?v=1704979580>,
  <https://9cbouldering.com/cdn/shop/products/Helium--mobile-hangboard-by-Crimptonite_08.jpg?v=1704979580>, and
  the listing's `_05`, `_07`, and `_09` published gallery views at the same
  CDN/version.

The two inherited candidate renders were generated before this geometry
takeover from the following explicit prompts and published inputs:

- Reverse call 1 used official `DSCF6545` back, official `DSCF6544` front,
  and the old primary/reverse assets: `strict 3:2 straight-on orthographic
  back working face; broad face parallel to image plane; horizontal parallel
  long edges; equal ends/holes; no visible thickness/foreshortening; exact
  pill pale-beech silhouette; exactly 2 far-end cord holes; authentic centered
  Cr+IMPTONITE laser mark; red-white cord below; #F6F2EA; no recesses/extra
  topology/angle/props.`
- Front call 2 used official `DSCF6544`, the independent 9c product image, the
  old primary, and the accepted reverse: `strict 3:2 straight-on orthographic
  front; exact pill silhouette, exactly 3 equal rounded nested-depth recesses,
  exactly 2 holes, red-white cord; authentic labels L 22mm upside-down + 14mm
  upright, C 18mm upside-down + 10mm upright, R 22mm upside-down + 14mm
  upright; #F6F2EA; no angle/thickness/extra topology.`

Both accepted canonical assets are 1536 x 1024, 8-bit RGB PNGs. They preserve
the source-published pale beech, pill silhouette, three front recesses, two
empty end passage holes, and engraved depth labels/logo. By explicit user
choice, every raster now follows a board-only convention: the red-white
suspension cord is omitted while the real through-holes remain, so inverted
positions do not show a gravity-defying dangling accessory. Both are strictly
head-on to their own working plane: their long axes and long edges are
horizontal, their ends and holes are bilaterally matched, and neither exposes
perspective thickness or foreshortening. They share the same off-white studio
field, pale-beech grain, soft recess lighting, edge softness, and smoothing.
The two base views were source-constrained cord-removal edits of the accepted
front and reverse renders. Original-resolution review found continuous natural
wood/background and no patch rectangles, seams, altered holds, or altered
markings. The two additional assets are exact 180-degree pixel rotations of
those cord-free canonical sources.

| Presentation | Asset | Canonical hold inventory | Old SHA-256 | New SHA-256 | Dimensions | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `primary` — front, 14/10 mm upright (default) | `assets/primary.png` | `edge-14` (2 pieces), `center-edge-18` (1), `edge-22` (2), `center-edge-10` (1), `top-jug` (1) | `7283a9e58ca9e1176fb5517061fb9a78e611e7af9fcd6943a021edcb70c56b7c` | `aaca10de93a6899a6ba3520ea722524d97d08aae45488beb280191a7f14092fc` | 1536 x 1024 | accepted board-only head-on canonical front |
| `front-inverted` — front, 22/18 mm upright | `assets/front-inverted.png` | alias of all 7 `primary` pieces | absent | `7b04a27032e2f4f140b2b38ebe7fb936d6cc622620c07112c761db2cd43cc057` | 1536 x 1024 | exact 180-degree primary rotation; `sourcePresentationID: primary`, `isInverted: true` |
| `reverse` — back, sloper upright | `assets/reverse.png` | `back-jug-sloper` (1 piece) | `74804c611a453220579c5728ac7964d3ab6956ebfbd197871b3bf881a0612429` | `a42c5a9c9252d7cadc336b2baa1ef1da75ee434342b4bf6b9a094b6f36b292ee` | 1536 x 1024 | accepted board-only head-on canonical back |
| `reverse-inverted` — back, jug upright | `assets/reverse-inverted.png` | alias of the 1 `reverse` piece | absent | `40813b47d90a4bc2e6782eb7c82e40d302cdafa730b134e866724cbc6a05f341` | 1536 x 1024 | exact 180-degree reverse rotation; `sourcePresentationID: reverse`, `isInverted: true` |

The checked-in orientation-alias schema and Tension Flash package precedent
allow each inverted presentation to reuse one canonical surface and its stable
physical hold IDs. This avoids duplicating physical contacts while rotating
the canonical render, highlight, and hit-testing path in both Workbench and the
app. The former reverse `back-jug-sloper` path retained its stable hold ID,
kind, treatment, equipment object, and single-piece inventory. Its stale
oblique frame `(0.178, 0.406, 0.648, 0.176)` and diagonally biased seven-curve
outline were deliberately replaced with frame `(0.178, 0.412, 0.648, 0.156)`
and a symmetric horizontal four-corner path (four lines, four cubic rounded
corners, close). An operator-selected `roundedRectangle` constraint at zero
degrees records the genuinely regular contact; the saved path remains the
rendering and hit-testing truth. All seven front pieces are byte-for-byte
unchanged within `board.json`. The board hash changed from
`69823a96c38fa709ff21a3e856249b2d4ac960230b2681e5fc06fbb4d83de376`
to `11b753ff43c178b547cc00dd451660182d5d23436e9c3e2ed780bf9a55a590a6`.

Workbench loaded and visually inspected all four presentation IDs. Normal and
all-active captures passed independently. `primary` and `front-inverted` each
rendered all 7 front pieces; `reverse` and `reverse-inverted` each rendered the
single horizontal back piece. All-active counts were 7, 7, 1, and 1. Every one
of the 16 presentation-scoped path checks was clicked individually and became
the sole selected hit target. The inverted bounds were the expected 180-degree
counterparts of their canonical paths. Final-inventory package validation and
package status completed successfully with 61 packages and no drafts.

## Escape Beta Board presentation repair (2026-08-31)

Escape's current product page and gallery were freshly reopened on 2026-08-31,
along with the independent StrengthClimbing owner review/front image and Power
Company Climbing's original-owner review. The official page publishes the
current 26 x 6 x 2 in molded-resin Beta Board in Gray 1810 and identifies its
dual texture. The independent photos confirm the same 11-opening topology,
ten recessed mounting bores, plastic/resin construction, and rough contact
areas transitioning to smooth glossy margins.

Fresh evidence:

- Escape Climbing product page:
  <https://escapeclimbing.com/products/ec72100>
- Escape official straight-on red and gray publication images:
  <https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_01-02.jpg?v=1700454580>
  and
  <https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_04-02.jpg?v=1700454580>
- StrengthClimbing owner review and straight-on hold-layout photo:
  <https://strengthclimbing.com/beta-board-from-escape-climbing-hangboard-review/>
- Power Company Climbing owner review/photos:
  <https://www.powercompanyclimbing.com/blog/2011/03/review-v512-hangboard-from-detroit-rock.html>

The package declares exactly one presentation, `primary`, and the repaired
asset remains an independently head-on 1503 x 394 view. Its silhouette,
aspect, shadows, and alpha-derived edge coverage are unchanged. Review of the
first accepted gray candidate found that three lower through-openings had
incorrectly remained opaque gray: the symmetric lower-outer pair and the
lower center-right opening. Only eight of the source-backed 11 openings
exposed the shared background. The first correction reopened the lower-outer
pair, producing a 10-opening intermediate that still left the lower
center-right rounded region opaque. Ten source-backed
recessed mounting bores were drawn
at manually reviewed top-origin pixel centers: upper `(327,82)`,
`(751.5,86)`, `(1176,82)`; outer-side `(79,201)`, `(1424,201)`; and
lower/center `(283,309)`, `(516,261)`, `(751.5,231)`, `(987,261)`,
`(1220,309)`. The accepted bore outer/core radii are 8.8/3.3 px. The symmetric
positions reflect the symmetric molded product; no image detection,
registration, mask, contour, crop, resample, warp, or edge movement was used.

The accepted gray-resin transform is the monotonic luminance mapping
`0.12 + 0.58 * luminance^1.50`, tinted by `(0.98, 1.00, 0.99)` and composited
through the source's unchanged alpha coverage onto `#F6F2EA`. It preserves
the existing high-frequency gritty contact texture, recessed shadows, and
specular rim highlights without blur, yielding the official rough-contact /
glossy-margin dual finish. No branding was added: the current official gray
photo resolves a subtle molded mark, but the independent straight-on image
does not establish it clearly enough to justify inventing pixels.

Candidate 1 (`ba1224d0b338fece178e6ccbb3f34bd8903e392e409c74274640ec0adcc39cdf`)
was rejected as too pale to read as published gray resin. Candidate 2 was
accepted for color and finish, then corrected in two bounded passes for the
three-opening omission. The asset changed from
`f55fa7cf1e86cf050cd774d3068da37d02534da830eea6442c8e5038f22c3c90`
through intermediate
`2cbd1e4cb54d2447379ff2801fe0b918139b2681d6749624aa1448a8952b78d1`
and first-correction
`c02f7f3d23aaa158b359fdd41f47315a4077bbde1b7a2879927f1902133c6f59`
to `f7d79b4777b99c81688a64e8e83b6d4c52fd082e893e10cd44cc4e9a9af9a342`;
all four are 1503 x 394 PNGs. `board.json` remains byte-identical at
`eb27ddc4b9f92332e1133db6ade1ce1a81de92edf7896a7790bbe3bfc1310873`.

The first correction directly authored the two rounded-pill interiors within
top-origin review bounds approximately `x=171...345, y=203...276` and
`x=1146...1320, y=203...276`. Their centers expose opaque `#F6F2EA`, with a
narrow manually shaded inner edge matching the other through-openings; the
gray molded perimeter remains the physical rim, not a plug. Pixel comparison
against the intermediate candidate found 11,183 changed pixels, all inside
the two declared review boxes, zero changes elsewhere, and 5,550 exact
background pixels across the two openings. This was a direct symmetric raster
drawing: no detection, segmentation, generated mask, vectorization, crop,
resize, registration, warp, or image generation was used.

The final rereview correction directly authored the remaining center-right
rounded-pill opening inside the single declared top-origin review box
`x=774...947, y=204...276`, using the neighboring center-left opening as the
manual symmetry reference. Its center exposes opaque `#F6F2EA`; two restrained
interior edge strokes preserve the recessed shading while leaving the molded
gray perimeter intact. Exact decoded-pixel comparison against the
first-correction image found 7,632 changed pixels bounded by
`x=783...944, y=211...272`, with zero changes outside the declared box. The
result was inspected at original detail and contains all 11 background-visible
through-openings plus all 10 mounting bores. This was direct deliberate path
drawing, with no detection, segmentation, generated mask, vectorization,
crop, resize, registration, warp, or image generation.

Workbench rendered the single presentation with all 22 canonical geometry
pieces and hold-ID labels aligned to their physical openings; the
same byte-identical paths remain the hit-testing source of truth. The repaired
image therefore passes the one-presentation/all-positions requirement,
head-on view, gray plastic/resin material, published 11-opening/10-bore
topology, and catalog smoothing/background checks. Final-inventory validation
and package status passed with 61 packages and no drafts. This deterministic
recolor/manual-bore repair is the user-approved exception to image generation;
the schema-2 machine manifest is intentionally unchanged in this bounded pass.

### Escape lower center-right opening shading follow-up (2026-08-31)

The official Escape product page, its current straight-on gray publication
image, StrengthClimbing's independent owner review, and Power Company
Climbing's original-owner review were freshly reopened before this follow-up.
They continue to establish the gray molded-plastic/resin body, dual-texture
finish, 11 through-openings, ten recessed mounting bores, and a restrained
shadow transition from each molded rim into the open background:

- <https://escapeclimbing.com/products/ec72100>
- <https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_04-02.jpg?v=1700454580>
- <https://strengthclimbing.com/beta-board-from-escape-climbing-hangboard-review/>
- <https://www.powercompanyclimbing.com/blog/2011/03/review-v512-hangboard-from-detroit-rock.html>

Original-detail rereview found the previously reopened lower center-right
opening had the right footprint but an overly thick, bright inner band along
its upper-left and lower edges. That band read as a pasted inset rather than
the same open recess shown by its neighbors. Two manually parameterized
shading candidates retained the exact established opening path and 1503 x 394
canvas. Both used a four-stop linear falloff from neutral gray through a muted
middle gray and near-white to the exact `#F6F2EA` opening center. Candidate 1
used edge/middle sRGB values `(0.50, 0.51, 0.50)` and
`(0.79, 0.78, 0.75)` at locations `0.00, 0.22, 0.48, 1.00`; candidate 2 used
`(0.55, 0.56, 0.55)` and `(0.83, 0.82, 0.79)` at locations
`0.00, 0.18, 0.43, 1.00`. Candidate 1 was accepted because its restrained
inner-wall depth matches the neighboring lower center-left opening without a
bright outline; candidate 2 was rejected as slightly too light.

The prior asset SHA-256 was
`f7d79b4777b99c81688a64e8e83b6d4c52fd082e893e10cd44cc4e9a9af9a342`.
Candidate 1 and the accepted asset are
`84d413b55d8ada97f6af5f0cc32312314da923d7ba87558f7436236b03ddfdd6`;
rejected candidate 2 was
`77a3d5941e2800ed2807bd7b6b7a4a018766b8a5007120c25094607951390894`.
Decoded-pixel comparison found 6,384 changed pixels, bounded exactly by the
top-origin box `x=783...944, y=211...272`, with zero changed pixels outside.
The accepted image remains 1503 x 394 RGBA and visibly retains all 11 open
background regions and all ten mounting bores. `board.json` remains
byte-identical at
`eb27ddc4b9f92332e1133db6ade1ce1a81de92edf7896a7790bbe3bfc1310873`.
No hold, silhouette, opening footprint, perspective, material texture, canvas,
or geometry changed. The correction was direct deliberate raster shading,
without image-driven detection, segmentation, generated masks, contours,
vectorization, registration, crop, resize, warp, or image generation.

## Metolius Light Rail 2.0 two-position repair (2026-08-31)

The complete current-revision Light Rail 2.0 was freshly re-researched and
repaired as one atomic reversible product on 2026-08-31. Metolius identifies
the product as a 18 x 3 x 1.5 in, 0.54 kg portable FSC-certified wooden rail
whose reversible design yields four holds. The current official product image
shows one rounded timber body, one long routed channel, a complete blue cord
with pink flecks and a left knot, upright 40/20 mm markings, and the inverse
40/15 mm markings. Those four labeled contacts require exactly two physical
suspension positions: 40/20 mm upright and the same rail inverted in its cord
with 40/15 mm upright. There is no separate rear working face or third
mounting position in the current evidence.

Freshly opened evidence:

- Metolius official product page:
  <https://www.metoliusclimbing.com/products/light-rail>
- Current official product image:
  <https://www.metoliusclimbing.com/cdn/shop/files/Light-Rail-2-PT.jpg?v=1767727616>
- Metolius official training-board manual, whose suspended-device section
  explicitly covers Light Rails:
  <https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826>
- Treeline Review's independent 2026 hands-on comparison:
  <https://www.treelinereview.com/gearreviews/best-hangboards-for-climbing>
- Treeline's published straight-on product view and its genuine tested-at-the-
  crag owner/reviewer photograph:
  <https://images.squarespace-cdn.com/content/v1/5b4544e485ede17941bc95fc/b4f8b087-e046-4231-bcbd-f070bb3c85ec/metolius-light-rail-20.jpg>
  and
  <https://images.squarespace-cdn.com/content/v1/5b4544e485ede17941bc95fc/452f6e96-37f1-454d-a405-e801658501a5/metolius-light-rail-1.jpg>.

Treeline independently confirms wood construction, single-cord suspension,
four contacts, and the same one-channel silhouette. Its table reports measured
edge values that differ slightly from Metolius's current 15/20/40 mm copy;
the package keeps the manufacturer's current specification and the depth
markings visibly published on both official and independent photos. Older
38/18/13 mm images with metal end brackets are a prior revision and were
explicitly excluded from the current 2.0 render.

The built-in image tool produced one source-constrained candidate for each
distinct operating position. The 20 mm prompt required the exact current
single-piece rounded FSC-wood rail, one routed channel, complete blue/pink cord
loop and left knot, upright 40/20 mm and inverse 40/15 mm markings and Metolius
marks, a straight-on orthographic working face, no metal brackets, and a warm
off-white studio field. The 15 mm prompt used the official image and accepted
20 mm candidate as references, kept the cord above the rail, and required the
wooden body to be physically inverted so 40/15 mm reads upright while the
40/20 mm markings read upside-down. Both prompts prohibited crop, perspective,
extra grooves, extra holes, hardware, hands, walls, and watermarks. Both first
candidates passed; no second iteration was used.

| Presentation | Declared asset | Scoped holds | Old SHA-256 / dimensions | New SHA-256 / dimensions | Result |
| --- | --- | --- | --- | --- | --- |
| `20mm-side` — 40/20 mm upright (default) | `assets/primary.png` | `jug-40-20mm-side`, `edge-20` | `da320b5673289e1aa15e226d0fe55a13d2fde7625c10bd9f8c10442d04caa7f2` / 1536 x 1024 RGBA | `1fa7bccc1ba6406fad3a6700ae826ea170fe2e4deb592f40cf84b42deef79b8d` / 1254 x 1254 RGB | accepted canonical 20 mm suspension position |
| `15mm-side` — 40/15 mm upright | `assets/15mm-surface.png` | `jug-40-15mm-side`, `edge-15` | `7b365965bb7d3c7b6f1fcd8c2503c5a77ddba8cc75084294c5a7766a90ef3705` / 1672 x 941 RGB | `c5e2a5edde3e5b0eebea601fac588e332d1bcfdee1adcb10f5bc58d66fe7aa78` / 1254 x 1254 RGB | accepted matched inverted-rail suspension position |

The accepted outputs were already the same square canvas, so they were copied
without resize, crop, padding, stretch, perspective warp, mask, segmentation,
registration, or local filtering. Each presentation is independently head-on
to its active working surface: the rail and routed channel edges are horizontal
and parallel, left/right ends have equal scale, and neither exposes side-depth
foreshortening. Both include the complete suspension loop, knot/tail, and lower
cord return. They share one pale natural-wood treatment, subtle grain, soft
recess lighting, off-white field, edge softness, and smoothing level. A
side-by-side catalog check against the head-on Frictitious Port-A-Board wood
presentation confirmed compatible wood texture, recessed shading, cord detail,
and studio treatment.

Because the new canvases changed the board's placement, the four existing
rounded-rectangle paths were deliberately repositioned without changing hold
IDs, kinds, depths, equipment ownership, path command topology, constraints,
or presentation assignments. Both 40 mm frames are now
`(0.041, 0.624, 0.916, 0.041)`; the 20 mm channel frame is
`(0.079, 0.674, 0.842, 0.070)` and the 15 mm channel frame is
`(0.079, 0.674, 0.842, 0.067)`. Presentation and board aspect ratios changed
to `1.0` to match the decoded 1254 x 1254 PNGs. `board.json` changed from
`4ec3fd03e6753466a66dc9fa3044d6ac962071bfd47f58d764bbe3fe3d229077`
to `1fd7f4ccb04fe572ffb0db5cc11dbd473a0403e1cb562091c2c5495116463303`.

Workbench loaded both presentation IDs and showed the normal image plus both
active paths aligned on each position. All four scoped paths were clicked
individually and became the expected selected hit target. Final-inventory
package validation and package status passed with 61 packages and no drafts;
the focused Workbench package suite passed 173 tests. The repair therefore
passes the all-presentations/all-positions requirement atomically. The
schema-2 machine manifest is intentionally unchanged in this bounded pass.

## Frictitious Port-A-Board corrective five-position audit (2026-08-31)

This entry supersedes the generated-image and completeness claims in the
earlier Port-A-Board repair. Fresh review of Frictitious's current regional
product metadata found an unresolved material conflict. The current US
[product page](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard)
specifies **beech** and 5 x 5.5 x 1.8 inches (128 x 140 x 48 mm), while the live
[Canadian storefront](https://frictitiousclimbing.com/en-ca/products/the-port-a-board-portable-and-mountable-portable-hangboard)
specifies **durable poplar wood** and 5.5 x 5 x 1.6 inches. The canonical
rasters are source-constrained board-only derivatives of current US official
shots, and this package therefore follows the US beech listing and assets for
the represented variant. The US page's
published [front](https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840),
[back](https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840),
and [side](https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840)
photos establish the same eight 30/open, 30, 25, 20, 15, 12, 10, and 8 mm
contacts, branding, black-rimmed passage holes, grain, and framing. By explicit
user choice, the rated cord is omitted from every raster while the two real
eyelets remain as empty through-holes. This board-only convention keeps the
front, back, inverted, and pinch positions readable without a gravity-defying
dangling accessory.

The material evidence is revision- and region-sensitive. The live Canadian
poplar specification is current regional metadata and is not characterized as
an older revision. The archived first-party image
`PAB-1_2aea9215-8656-4c3a-b51a-e37fdc246a09.jpg`, the independent
[Hooper's Beta comparison](https://www.hoopersbeta.com/edge-chart), and the
[portable-board review](https://thehangboard.com/blogs/news/portable-hangboards)
also describe Port-A-Boards as poplar, so the US-versus-Canada species conflict
cannot be resolved from publication date alone. Frictitious's older
[manufacturer manual mirror](https://manuals.plus/m/5cffc637e35befbac3738553e529f0eb508e575af7073cf198b9592e35a4a5c0)
documents a different seven-edge product (6, 8, 10, 12, 15, 20, and 25 mm,
plus a bonus 35 mm contact). That manual establishes an older/other physical
revision, but it does not resolve the two live storefronts' material conflict
for the photographed eight-edge product. The independent [Frictitious owner-review
feed](https://loox.io/s/E1bdwTzdzp) contains both seven-contact owner reports
and current product photos, further supporting the need not to merge revision
claims.

The front, back, and pinch-side bases were edited from the official images with
a narrow cord-removal instruction, then normalized to the existing 1400 x
1400 package canvas. Original-resolution review found continuous beech grain,
clean background, empty eyelets, and no patch rectangles, seams, changed
labels, or changed hold topology. The inverted assets are exact 180-degree
rotations of the cord-free front and back bases. Current hashes are `primary`
`6caacd3a5fc173aab8851de421ef32cb9c532756cf27ffcf47f396b89ee1b52e`,
`front-inverted`
`65fc9c6a376c845c66c43e7103d89950e1b790cbf3c0c54287ecb5c2266281b8`,
`back` `c742848ff831ded24249cc3a26c0ecab2de2a4f33155087fa54ad9a4b2c7927d`,
`back-inverted`
`011abca96fcf2522cd4d22a9ca2b3e9779273fd92faf688aa145806677947ebe`,
and `side` `e7e23884e3815decb74b8658bebd9c94ff0f89ae623f6849cb1196e0118de6a6`.
No crop, perspective warp, detection, segmentation, or image-derived geometry
was used. All five assets share one head-on studio and smoothing treatment.

`front-inverted` and `back-inverted` are now schema aliases of `primary` and
`back` with `isInverted: true`. The physical `edge-20` and `edge-15` records
remain canonically owned by their source faces at their previously reviewed
frames `(0.314, 0.401, 0.378, 0.067)` and
`(0.316, 0.401, 0.376, 0.101)`; Workbench performs the exact 180-degree path
transform for the alias views. No hold ID, kind, depth, path command,
constraint, or other physical fact changed. `board.json` changed from
`1260faa04c3032ed725906e78910d968b75a57106e9412badfe7984c7beba4b3`
to `dfd69600b01be66d9c50a57a2fbe4fbe7b92394cdf1cc39e6d44133de9a68206`
in the five-position correction, then to
`f72fe73da584187800f2802cc341c805f260d37f665f7609e5d80e25e4adf6d7`
when the sourced option-4 presentation alias was added.

The six verified head-on views are Front Upright, Front Inverted, Cord Option 4
— 20 mm In-cut, Back Upright, Back Inverted, and Pinch Side. A fresh 2026-08-31
review of the older manufacturer manual confirms that it separately enumerates
mounted mode and four portable routes: option 1 is a longer flat-edge setup,
option 2 is for pinch training, option 3 is a shorter flat-edge/no-cheat setup,
and option 4 creates an in-cut 20 mm edge. Options 1 and 3 do not require
duplicate face presentations when their working surface and pitch are the same;
option 2 is represented by Pinch Side.

`cord-option-4-20mm-incut` is an explicitly labeled adaptation of the older
manufacturer's cord-routing instruction to the current eight-edge beech
revision. The manual establishes only the manufacturer-defined option-4
semantics; the live product page and official photos remain the truth for the
current board pixels and hold inventory. Option 4 changes suspension routing
and the resulting board pitch, not the current board's machined front face.
Once the camera is kept exactly head-on to that 20 mm working surface, the
orthographic board-only face is pixel-identical to Front Inverted: routing and
pitch are intentionally omitted with the accessory and cannot be shown without
abandoning the head-on board-only convention. The presentation therefore
reuses the exact `assets/front-inverted.png` bytes
(`65fc9c6a376c845c66c43e7103d89950e1b790cbf3c0c54287ecb5c2266281b8`,
1400 x 1400 RGB), aliases canonical `primary` with `isInverted: true`, and
introduces no raster, hold, or geometry duplication. Workbench resolved its
source-owned regions and included the transformed `edge-20-piece-0` hit target.

Final-inventory validation and package status passed with 62 packages and no
drafts. The focused approved-package test passed and explicitly checked the
option-4 alias, exact reused asset path, inversion metadata, and 20 mm region.

## Lattice MXEdge Lift Large and Small three-position repair (2026-08-31)

The two current MXEdge Lift sizes were freshly reviewed as distinct physical
revisions and then repaired as one source-backed family. The manufacturer
identifies both as beech lifting edges with the same 20 x 11 x 5 cm form and
cord system, but the contact inventories remain size-specific: MXLarge has
MX22, MX16, MX12, and a 28 mm mono; MXSmall has MX18, MX14, MX8, and a 25 mm
mono. The original 1000 x 1000 images are the current manufacturer gallery's
straight-on front photographs. Their pale beech body, routed recesses,
authentic `MXL` / `MXS` marks, and size labels remain the product truth. By
explicit user choice, every raster follows the board-only convention: the
external blue/yellow cord and knot are omitted while all board contacts and
working rotations remain.

Freshly opened evidence:

- Lattice's current [MXEdge Lift product
  page](https://latticetraining.com/product/mxedge-lift/) and its first-party
  gallery, specification, and size-specific contact list.
- Lattice's published [How to use the MXEdge Lift
  video](https://latticetraining.com/app/uploads/2024/05/MXEdge-Lift-How-to.mp4).
  Its labeled in-use frames establish Large at 0:16, Medium at 0:28, Mono at
  0:36, and Small at 0:50.
- Lattice's current [product catalogue
  PDF](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf),
  which independently enumerates the MXLarge and MXSmall contact sets and
  specifies beech.
- The independent retailer galleries from [Up and
  Under](https://upandunder.co.uk/lattice-training-mxedge-lift-h_34246) and
  [Needle
  Sports](https://www.needlesports.com/Catalogue/Climbing/Bouldering-Training-Sport/Training-Equipment/Lattice-MXEdge-Lift),
  plus [Max Climbing's retailer
  review](https://www.maxclimbing.com/en-nl/products/lattice-mxedge-lift-portable-finger-strength-lifting-edge).
  These corroborate the production beech body, cord, both labeled sizes, and
  the same current face; none establishes a separate rear working surface.

The official use video resolves four contacts into three distinct physical
orientations per size, not four duplicate presentations. Large and Medium use
the same board orientation, 180 degrees from the existing catalogue front,
with different contacts and cord routing. Small uses the catalogue front at
0 degrees. Mono uses that face at 90 degrees counterclockwise. A fourth
quarter-turn would not represent another published working position and was
not invented.

| Package | Presentation | Scoped holds | Asset SHA-256 / dimensions |
| --- | --- | --- | --- |
| `lattice.mxedge-lift-large` | `primary` — Small Edge Position, 0 degrees | `edge-12` | `e3e4fe908dc4d28d0dc8298c5a33bcf44680c45d0ff8b04002fd84db6894b59c` / 1000 x 1000 RGB |
| `lattice.mxedge-lift-large` | `large-medium-edge-position` — 180 degrees | `edge-22`, `edge-16` | `878b6636850c632d41a5c0d67cd669da33f01c4a7c89357fa2cd1cab7fcf683f` / 1000 x 1000 RGB |
| `lattice.mxedge-lift-large` | `mono-position` — 90 degrees counterclockwise | `mono-28` | `de6818e6d28b50b67ce56f3709ab96b8ca43cbf2a26ecbea4ddaebaa999650d0` / 1000 x 1000 RGB |
| `lattice.mxedge-lift-small` | `primary` — Small Edge Position, 0 degrees | `edge-8` | `e18410cf14375e9dcfb2a2aec22aa01c29f98a1d8f41fd5f94dcd6a39bbf1f16` / 1000 x 1000 RGB |
| `lattice.mxedge-lift-small` | `large-medium-edge-position` — 180 degrees | `edge-18`, `edge-14` | `2ab477d5152b7b4bc7e88e14e0f6896cfedf308a30345f8d69f56aa85183c18e` / 1000 x 1000 RGB |
| `lattice.mxedge-lift-small` | `mono-position` — 90 degrees counterclockwise | `mono-25` | `c962b21d82b0b4cb19d112822f75fb1a3cfa3a2d6436378e6ab0f2a445831c62` / 1000 x 1000 RGB |

Each size's source-constrained base edit removes the external cord/knot, keeps
the published board topology and markings, and is normalized back to the 1000
x 1000 package canvas. The 180-degree and 90-degree assets are exact pixel
rotations of that cord-free base. Original-resolution review found no seams,
halos, rectangular patches, altered contacts, or altered labels. No crop,
detection, segmentation, registration, perspective warp, or image-derived
geometry was used. Every position remains independently head-on, and both
sizes share one beech, off-white, lighting, edge-softness, and smoothing
treatment.

The existing hold paths were deliberately reassigned without duplicating hold
identity or changing physical metadata. Direct Workbench review placed the
MXLarge frames at `edge-22 (0.35, 0.329, 0.405, 0.11)`, `edge-16 (0.29,
0.552, 0.46, 0.066)`, and `mono-28 (0.58, 0.252, 0.09, 0.09)`. MXSmall uses
`edge-18 (0.365, 0.385, 0.39, 0.11)`, `edge-14 (0.29, 0.585, 0.45, 0.06)`,
and `mono-25 (0.55, 0.28, 0.10, 0.10)`. The Small frame remains unchanged on the
default source image. The schema's inversion alias cannot safely scope only a
subset of source holds and has no quarter-turn mode, so these are explicit
presentation assets and direct presentation-scoped paths. Large `board.json`
changed from
`680b7a01d6145300c42783db326f3e7aa24d61c49290761f097537dcec0dd3de`
to `12e7971d6bc3d9743475e57057b9afa2e0592e23cd071656a8ea2bb9d9903604`;
Small changed from
`e017d237e187d731851c2c1fbf9419cff2efb8437e8442e75b6a0ad7cce5cd55`
to `73926b56f59250bcb9cddd6fff714513cff66dd82163fb439101286c0b01867a`.

Workbench loaded all six presentation surfaces. Normal/all-path overlays
aligned to the visible Small edge, both shared inverted edges, and each mono.
Every hold was clicked individually and returned the expected hit target:
`edge-12`, `edge-22`, `edge-16`, `mono-28`, `edge-8`, `edge-18`, `edge-14`,
and `mono-25`. Final-inventory package validation and package status passed
with 62 packages and no drafts. The focused Workbench package suite passed 159
tests; the approved-package subset passed 13 tests with the concurrently owned
Port-A-Board assertion intentionally deselected. The schema-2 machine manifest
is intentionally unchanged in this bounded pass.

## Moon Armstrong Beech presentation acceptance (2026-08-31)

The current Moon Armstrong Beech was freshly checked against Moon Climbing's
[current product page](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html),
its [published main Beech product
image](https://moonclimbing.com/media/catalog/product/cache/d6cc8bf5bd96a83606fc1c516f2f9600/6/0/60-112-bec_moon_armstrong_fingerboard_bec_01.jpg),
and Moon's first-party [design
history](https://moonclimbing.com/News/post/the-story-behind-the-armstrong-fingerboard).
Independent corroboration came from the current retailer galleries and product
descriptions at
[Klimwinkel](https://www.klimwinkel.nl/moon-climbing-armstrong-fingerboard),
[Rock+Run](https://rockrun.com/products/moon-armstrong-fingerboard), and
[Goodbouldering](https://goodbouldering.com/?pid=169014527), including their
published customer/owner reviews. These sources establish the same offset
silhouette, central jug and 22/18 mm edges, paired jugs and 35-degree slopers,
25/20/15/10/8 mm slots, 22 mm two-finger and mono pockets, pulley points,
authentic Moon medallion, engraved depth labels, and `train hard climb harder`
slogan. The exact package revision is Beech SKU `60-112-BEC`; Moon specifies it
as 100% sustainably sourced Beech. Ash and Sycamore are sibling material SKUs,
not additional working positions of this Beech package.

There is one declared presentation: `primary`, the upright front working face
containing all 21 scoped holds. That intended upright presentation is supported
by Moon's published product imagery and its 2022 [Armstrong Advice & Tips /
installation
guide](https://www.klimwinkel.nl/assets/pdfs/shop1/Moon_Armstrong_Guidelines.pdf),
which requires the Armstrong to be mounted level and instructs the supplied
short ropes to be attached to the board's bottom edge for pulley loops. In that
orientation, the bottom-edge pulley function, readable depth labels, medallion,
slogan, and offset hold layout agree with the official product image and the
independent retailer galleries. The guide's separate warning, `Never hang
upside down on a fingerboard`, addresses the climber's body orientation during
use; it does not state that the board itself must not be mounted upside down.

Fresh searches of Moon's product and design publications, the installation
guide, and the cited independent retailer sources found no published Armstrong
installation or working presentation with the board inverted. The available
evidence therefore supports retaining the documented upright presentation and
does not support adding an inverted presentation. This is a cautious
evidence-based inference and an evidence gap, not a claim that inverted mounting
is physically impossible or explicitly prohibited by Moon. Mounting above a
door, on a beam, or on a free-standing frame changes location rather than the
documented working surface.

The existing 1697 x 1200 RGBA PNG is the same clean, published head-on Beech
product view used by Moon. Its usable front face is orthographic: horizontal
features remain parallel, both ends have equal scale, and the recesses show no
side-depth foreshortening. The complete body is visible, uncropped, and nearly
fills the canvas width. Its tall bright field is the manufacturer's own product
framing; cropping it or removing the authentic logo, depth labels, or slogan
would reduce published-source fidelity. A side-by-side check with the
Metolius Wood Grips Deluxe II wood-board comparator confirmed compatible pale
hardwood, soft studio lighting, restrained natural grain, recessed shadowing,
rounded-edge softness, and smoothing. No denoise or stylization is warranted.

This is therefore an accepted no-op. `assets/primary.png` remains
`f81b2d306afe070177eeda2464a9b4019e505916641ebdb9399141e19e129fa3`
(1697 x 1200 RGBA), and `board.json` remains
`50c1a5752dc5a0d2bb59cc3c77c4e5d3de25ae688c48531827d10852d138c20b`.
No image pixels, paths, hold assignments, dimensions, aspect ratios, or package
metadata changed. Direct visual inspection confirmed the normal image and all
21 visible contacts; final-inventory package validation and package status
passed with 61 packages and no drafts. The schema-2 machine manifest is
intentionally unchanged in this bounded acceptance pass.

## YY Vertical Baguette Evo five-position repair (2026-08-31)

The current Baguette Evo was freshly re-researched as a distinct physical
revision before accepting its repaired presentation set. YY Vertical's live
[product page](https://www.yyvertical.com/en/products/baguette-evo) establishes
the rounded portable body, 52 x 5 x 5 cm dimensions, approximately 550 g
weight, rubberwood construction, paired 25/20/15/12/10/8/6 mm edges, central
30/25/20/6 mm edges, rounded trays, and the continuously variable Turn & Pull
system. Current independent listings at
[Outside](https://www.outside.co.uk/y-y-baguette-evo.html),
[Varuste](https://varuste.net/en/p135968/yy-vertical-baguette-evo), and
[Up and Under](https://upandunder.co.uk/yy-vertical-la-baguette-evo-2)
corroborate the photographed rounded revision, 52 cm length, approximately
550 g weight, and recycled rubberwood construction. Varuste independently
corroborates the 6--30 mm range, while Up and Under reproduces YY's current
paired and central edge inventory exactly.

The evidence also contains two conflicts that were preserved rather than
silently combined. YY's older
[2025/2026 catalog](https://graniteoutdoor.net/wp-content/uploads/YY_Leaflet-2026-Catalog-2025.pdf)
calls the Baguette Evo rubberwood in its body copy but `Poplar Plywood` in its
composition field. That catalog and Outside's currently live listing also name
the third central edge as 12 mm, while YY's current first-party page and the
current Up and Under listing name it as 20 mm. The package follows the current
live manufacturer specification and photographed revision: recycled
rubberwood with central 30/25/20/6 mm edges. It does not import the older
catalog's poplar-plywood field or the conflicting 12 mm center claim.

The finished package has exactly five finite, independently head-on,
board-only presentations:

| Presentation ID | Working surface | Scoped regions |
| --- | --- | ---: |
| `paired-25-20-15-10` | paired 25/20/15/10 mm edges | 8 |
| `paired-12-8-6` | paired 12/8/6 mm edges | 6 |
| `central-30-25` | central 30/25 mm edges | 2 |
| `central-20-6` | central 20/6 mm edges | 2 |
| `rounded-tray` | rounded tray | 1 |

Turn & Pull changes pitch continuously; it does not create a sixth discrete
machined face, so no extra presentation was invented for an arbitrary tilt.
By explicit user choice, the external suspension cords are omitted from every
catalog raster so no position depicts gravity-defying or misleading cord
routing. The authentic cord eyelets remain visible in the wooden body. This is
a board-only catalog convention, not a claim that the production product ships
without cords.

All five assets use the same 1774 x 887 studio canvas, straight-on orthographic
framing, recycled-rubberwood treatment, off-white background, lighting,
edge softness, and smoothing approach. Every canonical region was directly
reviewed against its visible contact surface; no image-derived geometry was
used. Final-inventory package validation and package status passed, and the
focused Workbench package suite passed 173 tests. The schema-2 machine
manifest is intentionally unchanged in this bounded repair.
