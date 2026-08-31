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

## 2026-08-31 Tension Grindstone Pro deterministic presentation repair

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
deliberately asymmetric spacing. The independent 2017
[Climbing product photo](https://www.climbing.com/gear/sponsor-content-climbing-holiday-gift-guide-tension-climbing-grindstone-pro-hangboard/)
publishes the complete three-tier wooden front face, including the two top
openings, center pocket family, lower five edges, Tension mark, and engraved
depth labels. The catalog asset is the established simplified, unbranded
render of that exact topology: wood material, silhouette, opening count,
relative placement, and the asymmetric front working face conform. It is
genuinely head-on to that working face, with parallel horizontal tiers and no
visible side plane. Its existing uniform soft, pale-wood smoothing treatment
also conforms; no smoothing or product-pixel filter was applied.

The original asset was 1654 × 951 pixels with SHA-256
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
  independent NUG/Port review reports poplar while the current official pages
  specify beech; the review is therefore used only for identity, grip inventory,
  and cord corroboration, while the current official species claim governs
  Phase 2 and the unresolved species conflict remains recorded.
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
- All four Flash Board orientations are `regenerate`. The current official page calls
  the smallest contacts `Small Crimps` and separately names 8/10/15/20 mm; the
  audit no longer attributes 6 mm to Tension. The manufacturer demonstration
  establishes the intended flipped surfaces, while each current asset omits or
  crops the adjustable cord and knots from the source-confirmed topology and
  the three-edge-inverted asset also uses a transparent cutout.
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
