# 3-D board orientation evidence packet

Reviewed 2026-09-11 at commit `6e24dece` (Task 6, Step 3 evidence-only
preparation), promoted at `ca27fbdc` (Nature/Baguette orientation metadata),
and extended on origin/main for a fifth model package. The initial sections
retain that five-package snapshot, including the historical Flash Board
single-cord suspension disposition. They do not describe the complete current
catalog. The Batch-01 / batch-02 promotion record below covers the current
fourteen model packages at that promotion and supersedes the Flash snapshot with five contacts,
four authored orientation positions, and no suspension block. The Nature and
YY Vertical Baguette Evo groupings and quaternions are recorded in the
Promotion record. This document does not itself change package or model bytes.

## September 15 collection extension

The model inventory now contains twenty-seven packages. The seven added fixed boards
below each retain one canonical `primary` position covering their entire
ordered contact inventory, with no orientation quaternion, pivot override,
or suspension. Their current model bounds are compiled from their USDZ
triangles into each package's descriptor. Author and evidence decisions,
source URLs, geometry limitations, and promoted hashes are recorded in the
[collection import audit](2026-09-15-hangboard-collection-model-imports.md).

| Package ID | Contact count | Position |
| --- | ---: | --- |
| `metolius.climbers-edge` | 15 | `primary` |
| `metolius.contact` | 33 | `primary` |
| `metolius.simulator-3d` | 29 | `primary` |
| `soill.training-tiles` | 20 | `primary` |
| `clavellium-training-block` | 10 | `primary` |
| `the-hangboard.the-hangboard` | 15 | `primary` |
| `trango.rock-prodigy-training-center` | 24 | `primary` |
| `dewoodstok-woodbord` | 17 | `primary` |
| `escape.unlimited` | 7 | `primary` |
| `evolv-kilter-basic-long` | 4 | `primary` |
| `metolius.wood-grips-deluxe-ii` | 26 | `front` |
| `moon.armstrong` | 21 | `primary` |
| `target10a.linebreaker-base` | 23 | `primary` |

These six fixed single-position packages have no orientation quaternion or
pivot override. Counts and position/presentation names are taken from the
shipped `board.json` and `primary.model.json` descriptors/package metadata;
source/evidence facts and limitations come from the retained source-audit
records and migration evidence. No additional rotation, contact grouping,
bound, dimension, or physical claim is implied.

## Batch-02 collection extension (2026-09-16)

The model inventory now contains thirty-two packages. The six batch-02
additions below each retain one loader-materialized position covering their
entire ordered contact inventory, with no orientation quaternion, pivot
override, or suspension block. `metolius.foundry` keeps the `front`
presentation/position name carried by its migrated package; the other five
materialize the legacy `primary` position. Their current model bounds are
compiled from their USDZ triangles into each package's descriptor. Author and
evidence decisions, source URLs, geometry limitations, and promoted hashes are
recorded in the retained batch-02 migration evidence.

| Package ID | Contact count | Position |
| --- | ---: | --- |
| `escape-beta-22` | 22 | `primary` |
| `mammut.diamond-finger` | 16 | `primary` |
| `metolius.foundry` | 18 | `front` |
| `nature.stoak-board-iii` | 7 | `primary` |
| `soill.iron-palm-2` | 8 | `primary` |
| `soill.split-palm` | 14 | `primary` |

These six fixed single-position packages have no orientation quaternion or
pivot override. Counts and position/presentation names are taken from the
shipped `board.json` and package descriptors; source/evidence facts and
limitations come from the retained batch-02 migration records. No additional
rotation, contact grouping, bound, dimension, or physical claim is implied.

## Batch-04 Helium promotion (2026-09-20)

`crimptonite.helium-mobile` has one model presentation and one canonical
`primary` position. The package declares six ordered hold IDs:
`edge-14`, `center-edge-18`, `edge-22`, `center-edge-10`,
`back-jug-sloper`, and `top-jug`. It declares no orientation quaternion or
pivot override. The package's model bounds and descriptor remain the
model-package sources of truth; this inventory entry adds no orientation,
geometry, or physical claim.

## Batch-04 Metolius Light Rail 2.0 promotion (2026-09-20)

`metolius.light-rail-2` is one physical reversible Light Rail 2.0 unit with
one v1 model presentation and exactly two canonical positions:
`20mm-side` and `15mm-side`. The two positions expose the four ordered contact
IDs `jug-40-20mm-side`, `edge-20`, `jug-40-15mm-side`, and `edge-15` without
duplicating physical contacts. `20mm-side` is the identity upright pose;
`15mm-side` is the physical 180-degree inversion around the front/view axis.
The identity and inversion quaternion, and the per-position contact guides,
are authored display estimates selected to show the two source-backed working
sides; they are not manufacturer angle or metrology claims.

The model's `pairedLeadCord` route is restricted to the same two evidenced
exterior entry regions (`left_upper_entry_001` and `right_upper_entry_001`,
corresponding to `cord-passage-1` and `cord-passage-2`). No underside mouth,
hidden vertical bore, or other connection is represented. Cord geometry is
transient and non-pickable; model bounds and descriptor data remain the
model-package sources of truth. Evidence: the retained manufacturer Light
Rail 2.0 product view and exact archived Treeline field view recorded in the
[Batch-04 source register](2026-09-20-batch-04-3d-source-register.json) and
[source-to-contact audit](2026-09-20-batch-04-source-to-contact-audit.md).

## Batch-04 Metolius Rock Rings 3D promotion (2026-09-20)

`metolius.rock-rings-3d` uses one schema-v3 model presentation with one
canonical physical ring unit (descriptor-v2 slots `jug`, `pocket-40`,
`pocket-32`, and `pocket-25`) instantiated exactly twice. The `left-ring` and
`right-ring` instances are the same unit presentation: both use the identity
base rotation `[0, 0, 0, 1]`, have no reflection, and differ only by their
placement translations. The canonical `primary` position is therefore the
same physical orientation for both units; no handed or mirrored orientation
is authored. The exact slot-to-contact maps are, respectively:

* `jug` -> `jug-left` / `jug-right`;
* `pocket-40` -> `pocket-40-four-left` / `pocket-40-four-right`;
* `pocket-32` -> `pocket-32-three-left` / `pocket-32-three-right`;
* `pocket-25` -> `pocket-25-two-left` / `pocket-25-two-right`.

Each instance owns an independent `pairedLeadCord` document and invisible
anchor. The retained route preserves the visible roof exits and lateral
windows only; it does not claim a concealed route, inter-unit connection, or
central through-bore. Cord geometry remains transient and non-pickable. The
descriptor's model bounds and hash remain the model-package sources of truth;
no physical dimensions or hidden attachment geometry are inferred here.

The approved evidence set is the Metolius numbered depth guide
([Rock-Ring-Depts.jpg](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Ring-Depts.jpg?v=1762201543)),
the manufacturer black/white product view
([Rock-Rings-black-white.jpg](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123),
SHA-256 `d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c`),
and the retained owner front/rear and lateral views
([front/rear](https://i.ebayimg.com/images/g/xaEAAOSwFtFmDzoB/s-l1600.webp),
SHA-256 `b510bd192bb6fe54c6e4dcfa98c9d684a2db7582cbfd3682cebb6e031494a8f0`;
[lateral](https://i.ebayimg.com/images/g/KQkAAOSwjmJmDzoE/s-l1600.webp),
SHA-256 `df263e67395aa17a2f4df263ca74e4cbbfb7bfcf9c75e0dfa611d352ad3d3cba`).
These sources support the physical unit identity, visible exits/windows, and
contact-depth labeling; the authored placement and cord curves are display
estimates, not factory metrology.

## Batch-04 Owl Climb Poker promotion contract (2026-09-20)

`owl-climb.poker` is one schema-v3 model presentation for one continuous
660 × 100 × 100 mm Poker beam. The four usable source-backed faces retain the
canonical position IDs `face-a`, `face-b`, `face-c`, and `face-d`; each position
selects only its same-face contacts (7, 9, 9, and 9 respectively). Face D
contains exactly the two approved restored contacts
`face-d-left-deep-rounded-recess` and `face-d-right-deep-rounded-recess`.
No contact is collapsed across faces.

The descriptor-v1 model orientation uses `modelBoundsCenter` and rotates about
the long model X axis in the source-photo cycle: `face-a` identity
`[0, 0, 0, 1]`, `face-b` +90° `[0.707106781, 0, 0, 0.707106781]`, `face-c`
180° `[1, 0, 0, 0]`, and `face-d` −90° `[-0.707106781, 0, 0,
0.707106781]`. These quaternions are authored display estimates used to keep
each retained manufacturer face upright; they are not manufacturer metrology.

The model package is model-only: it has one `primary.usdz`, one hash-bound
`primary.model.json`, no raster/contactGeometry/fallback state, no suspension,
and no brackets, screws, mounting holes, fasteners, cleats, or other hardware.
The approved source set is the Owl Climb manufacturer page and its four exact
retained manufacturer photographs recorded in the [Batch-04 source
register](2026-09-20-batch-04-3d-source-register.json). The delivered GLB is
retained evidence only; the two Face D recesses are the only approved manual
restoration.

## Decision and review gate (initial five-package snapshot)

The web evidence supports proceeding to a human/Astra orientation review for
all five packages. Beastmaker 1000 and Metolius Compact II have a complete
manufacturer front plus a materially different commerce-gap oblique view in
the prior retained packet. Nature Stone Hanger and Baguette Evo have multiple
materially distinct views in their current manufacturer galleries (front,
oblique/profile/reverse-use views). This establishes a review set, not a claim
that every hidden surface or machining dimension is known. The Tension Flash
Board is a suspended portable board whose shipped single-cord suspension
metadata establishes four hanging poses; orientation is not applicable to it
by mutual exclusivity, so it receives a disposition record but no rotation
review.

The current checkout does not retain the ignored source-image bytes referenced
by the earlier `.context/shaky-rat-*` packet ledgers; those paths, hashes and
page links are reproduced below so a reviewer can recover the exact approved
set. No search thumbnail, generated render, legacy raster asset, or board
asset is used as a second physical view. A human must approve the exact
multi-angle set before Astra authors orientation metadata. If the approved
source bytes cannot be recovered, stop at that gate rather than infer a view.

The following decisions were deliberately out of scope in the Step-3 draft;
the Promotion record below resolves all of them for Nature and Baguette,
while the Flash Board needs none of them (suspension path):

* no authored `orientation` object or quaternion;
* no final `front`/`reverse`/Turn & Pull contact grouping for Nature or
  Baguette;
* no rotation of a USDZ, descriptor, board asset, or presentation camera;
* no new physical contacts inferred from product-use photographs.

## Initial five-package inventory and baseline (historical)

Discovery at that review point found these five complete model packages.
Each has one `primary` model presentation. Beastmaker 1000 and Metolius
Compact II keep the legacy effective position `primary` with no orientation
or suspension metadata. Nature Stone Hanger and Baguette Evo declare
authored positions with an orientation block (see the Promotion record).
The Tension Flash Board declares four legacy suspension poses with a
single-cord suspension block and no orientation. `boardBounds` is explicitly
`null` in every checked-in descriptor; the normalized hold face-plane AABB
union below is a descriptor diagnostic, not a physical board bound.

| package ID | package / presentation | effective position at review | holds | model SHA-256 | descriptor SHA-256 |
| --- | --- | --- | ---: | --- | --- |
| `beastmaker-1000` | `Hangboards/beastmaker-1000`, `primary` | `primary` (legacy, all holds) | 22 | `19fb5895575792fb69e82aa3c8a04fa14a6bd40a8a97f486bc16be014e546f3d` | `ee095c463804312cbd6ed08f5113019793b934ab6806a6fb343be939ff8a68d3` |
| `metolius.wood-grips-compact-ii` | `Hangboards/metolius-wood-grips-compact-ii`, `primary` | `primary` (legacy, all holds) | 19 | `addf2cd2ddd34f18f311ccc1413ca94644df0d2f3d56020b68edf25625bc664a` | `a652b1a184ec15432126502514d11db2b02768df7c3c0a892c62031f381c0c7f` |
| `nature.stone-hanger` | `Hangboards/nature-stone-hanger`, `primary` | `front` + `reverse`, exact partition | 8 | `366e6833403d8877b62b2403ce98683e4c27f9ce76c1d9e9abaa24e50ba382e4` | `eb2a83c035d1a80e172f196c68210b4b0556a897f367ebd3ddcd27b196237fa8` |
| `yy.baguette-evo` | `Hangboards/yy-baguette-evo`, `primary` | 5 authored positions, exact partition | 19 | `e006aad2dfac8e5a3911d1e3e0944830056856d45d757fc76c360e339c76f91b` | `e73f56e2f9ae903583896f88067f03f9f3d9bb1065b8febddd825fcd98b4532c` |
| `tension.flash-board` | `Hangboards/tension-flash-board`, `primary` | 4 legacy suspension poses, full inventory each | 7 | `ea4d014f1af63300561c8ad4ec6e78710ebc519c0811630502aba4e33d62c25b` | `b7a31d182e1f8a07b27f0fa2157f9733969d1e0ff55aa8cc78f744e028cf2c58` |

The hashes record the bytes at that review point, not a current-catalog
verification. The Flash model and descriptor were subsequently replaced as
recorded in the batch promotion below; its historical hashes and bounds must
not be used to validate the current package.

## Coordinate and bounds convention (initial snapshot)

The five descriptors use schema version 1 normalized image-plane values:
`center = [x, y]`, `facePlaneAABB.min/max = [x, y]`. The table records the
union of all hold face-plane AABBs in descriptor order, with no rounding beyond
the stored nine-decimal values. These values are suitable for checking that a
future position set covers the complete descriptor inventory; they
do not establish body thickness, recess depth, or a rotation.

| package | `boardBounds` | descriptor hold-AABB union (`min` → `max`) | source/model bound context |
| --- | --- | --- | --- |
| Beastmaker 1000 | `null` | `[0.026206898, 0.054666682]` → `[0.973793173, 1.000000000]` | Manufacturer face is 580 × 150 mm; prior model packet qualifies a 58 mm shared-layout depth view, but the current Tulip page also says `5 mm`; neither publishes complete body sections. |
| Metolius Compact II | `null` | `[0.000000000, 0.042771465]` → `[1.000000000, 1.000000000]` | Manufacturer Compact is 610 × 157 mm (24 × 6.2 in); the 56 mm labels are sloper callouts, not body thickness. Existing model depth is an authored display estimate. |
| Nature Stone Hanger | `null` | `[0.092380923, 0.128571409]` → `[0.907619077, 0.858095244]` | Retained integration evidence gives combined model bounds X/Z ±0.0525 m and Y ±0.0175 m; manufacturer publishes 105 × 105 × 35 mm. Fine sections, cord routing and port depth remain unknown. |
| Baguette Evo | `null` | `[0.076923064, 0.000000000]` → `[0.923076936, 1.000000000]` | Retained README gives a 520 × 50 × 50 mm round envelope and origin at its center; machining profiles, bore dimensions and small-edge offsets are estimates. |
| Tension Flash Board | `null` | `[0.1096, 0.213252436]` → `[0.890399992, 0.848684193]` | Manufacturer Flash Board 2 page; model bounds X 0–0.5 m with Y/Z ±0.076 m (origin at one end, not centered). No complete body sections published. |

## Ordered hold IDs and position history

The following is the exact `board.json` hold order for the initial audit set.
Where a section is explicitly labeled as a pre-promotion assessment, its
position prose records the historical Step-3 state; the Promotion records
describe subsequent states. Authored multi-position models must cover every
descriptor hold at least once and preserve canonical hold order within each
position. Intentional overlaps are allowed when the same hold is usable from
multiple positions. Select among overlapping candidates by closest view
quaternion, breaking equal-distance ties by authored position order. The
exact-once statements below apply only to the named board-specific
configurations that intentionally remain disjoint.

### Beastmaker 1000 — 22 holds

Current effective position: `primary` → all IDs below. Current model
orientation: none. Physical candidate: fixed mounted front display only;
there is no source-backed selectable reverse face.

| order | hold ID | descriptor center | descriptor face-plane AABB min → max | USDZ node |
| ---: | --- | --- | --- | --- |
| 1 | `jug-left` | `[0.121551725, 0.878868043]` | `[0.043103450, 0.757736086]` → `[0.200000000, 1.000000000]` | `BeastmakerBody_024` |
| 2 | `jug-right` | `[0.878448296, 0.878868043]` | `[0.800000000, 0.757736086]` → `[0.956896592, 1.000000000]` | `BeastmakerBody_025` |
| 3 | `sloper-35-left` | `[0.285775865, 0.854215216]` | `[0.200000000, 0.708430431]` → `[0.371551730, 1.000000000]` | `BeastmakerBody_043` |
| 4 | `sloper-35-right` | `[0.714224135, 0.854215216]` | `[0.628448270, 0.708430431]` → `[0.800000000, 1.000000000]` | `BeastmakerBody_044` |
| 5 | `sloper-center` | `[0.500000000, 0.884921739]` | `[0.371551730, 0.769843478]` → `[0.628448270, 1.000000000]` | `BeastmakerBody_045` |
| 6 | `pocket-top-outer-left` | `[0.108620692, 0.699993394]` | `[0.033103451, 0.608000035]` → `[0.184137932, 0.791986752]` | `BeastmakerBody_040` |
| 7 | `pocket-top-outer-right` | `[0.891379344, 0.700000024]` | `[0.815862081, 0.608000035]` → `[0.966896607, 0.792000014]` | `BeastmakerBody_041` |
| 8 | `pocket-top-left` | `[0.431034508, 0.700000024]` | `[0.373620705, 0.608000035]` → `[0.488448311, 0.792000014]` | `BeastmakerBody_039` |
| 9 | `pocket-top-right` | `[0.568965531, 0.700000024]` | `[0.511551740, 0.608000035]` → `[0.626379321, 0.792000014]` | `BeastmakerBody_042` |
| 10 | `pocket-middle-outer-left` | `[0.101724139, 0.446666672]` | `[0.026206898, 0.354666670]` → `[0.177241379, 0.538666673]` | `BeastmakerBody_037` |
| 11 | `pocket-middle-mid-left` | `[0.232758624, 0.446666672]` | `[0.190862068, 0.354666670]` → `[0.274655179, 0.538666673]` | `BeastmakerBody_035` |
| 12 | `pocket-middle-inner-left` | `[0.346551730, 0.446666672]` | `[0.288275869, 0.354666670]` → `[0.404827591, 0.538666673]` | `BeastmakerBody_033` |
| 13 | `pocket-middle-center` | `[0.500000026, 0.446666672]` | `[0.419310364, 0.354666670]` → `[0.580689687, 0.538666673]` | `BeastmakerBody_032` |
| 14 | `pocket-middle-inner-right` | `[0.653448309, 0.446666672]` | `[0.595172435, 0.354666670]` → `[0.711724183, 0.538666673]` | `BeastmakerBody_034` |
| 15 | `pocket-middle-mid-right` | `[0.767241415, 0.446666672]` | `[0.725344872, 0.354666670]` → `[0.809137958, 0.538666673]` | `BeastmakerBody_036` |
| 16 | `pocket-middle-outer-right` | `[0.898275910, 0.446666672]` | `[0.822758647, 0.354666670]` → `[0.973793173, 0.538666673]` | `BeastmakerBody_038` |
| 17 | `pocket-bottom-outer-left` | `[0.181034482, 0.146666678]` | `[0.098620692, 0.054666682]` → `[0.263448273, 0.238666673]` | `BeastmakerBody_030` |
| 18 | `pocket-bottom-mid-left` | `[0.317241389, 0.146666678]` | `[0.274482763, 0.054666682]` → `[0.360000015, 0.238666673]` | `BeastmakerBody_028` |
| 19 | `pocket-bottom-inner-left` | `[0.431034508, 0.146666678]` | `[0.373620705, 0.054666682]` → `[0.488448311, 0.238666673]` | `BeastmakerBody_026` |
| 20 | `pocket-bottom-inner-right` | `[0.568965531, 0.146666678]` | `[0.511551740, 0.054666682]` → `[0.626379321, 0.238666673]` | `BeastmakerBody_027` |
| 21 | `pocket-bottom-mid-right` | `[0.682758637, 0.146666678]` | `[0.640000010, 0.054666682]` → `[0.725517263, 0.238666673]` | `BeastmakerBody_029` |
| 22 | `pocket-bottom-outer-right` | `[0.818965556, 0.146666678]` | `[0.736551727, 0.054666682]` → `[0.901379385, 0.238666673]` | `BeastmakerBody_031` |

### Metolius Wood Grips Compact II — 19 holds

Current effective position: `primary` → all IDs below. Current model
orientation: none. Physical candidate: fixed mounted front display only; the
source supports a single usable face, not a selectable reverse presentation.

| order | hold ID | descriptor center | descriptor face-plane AABB min → max | USDZ node |
| ---: | --- | --- | --- | --- |
| 1 | `jug-left` | `[0.087077364, 0.927438940]` | `[0.000000000, 0.854877881]` → `[0.174154728, 1.000000000]` | `Wood_Grips_Compact_II_024` |
| 2 | `sloper-flat-left` | `[0.247665959, 0.900421902]` | `[0.172140531, 0.859960031]` → `[0.323191387, 0.940883774]` | `Wood_Grips_Compact_II_036` |
| 3 | `sloper-round-center` | `[0.500000000, 0.909000795]` | `[0.319597740, 0.856218226]` → `[0.680402260, 0.961783363]` | `Wood_Grips_Compact_II_038` |
| 4 | `sloper-flat-right` | `[0.752334041, 0.900421902]` | `[0.676808613, 0.859960031]` → `[0.827859469, 0.940883774]` | `Wood_Grips_Compact_II_037` |
| 5 | `jug-right` | `[0.912922636, 0.927438940]` | `[0.825845272, 0.854877881]` → `[1.000000000, 1.000000000]` | `Wood_Grips_Compact_II_025` |
| 6 | `edge-29-left` | `[0.089324972, 0.624203832]` | `[0.007338455, 0.433121028]` → `[0.171311489, 0.815286636]` | `Wood_Grips_Compact_II_022` |
| 7 | `pocket-29-three-left` | `[0.247540985, 0.560509533]` | `[0.187704915, 0.458598691]` → `[0.307377054, 0.662420374]` | `Wood_Grips_Compact_II_032` |
| 8 | `pocket-29-two-left` | `[0.362295084, 0.560509533]` | `[0.318852463, 0.458598691]` → `[0.405737705, 0.662420374]` | `Wood_Grips_Compact_II_034` |
| 9 | `pocket-29-four-center` | `[0.500000000, 0.560509533]` | `[0.415573772, 0.458598691]` → `[0.584426228, 0.662420374]` | `Wood_Grips_Compact_II_031` |
| 10 | `pocket-29-two-right` | `[0.637704916, 0.560509533]` | `[0.594262295, 0.458598691]` → `[0.681147537, 0.662420374]` | `Wood_Grips_Compact_II_035` |
| 11 | `pocket-29-three-right` | `[0.752459015, 0.560509533]` | `[0.692622946, 0.458598691]` → `[0.812295085, 0.662420374]` | `Wood_Grips_Compact_II_033` |
| 12 | `edge-29-right` | `[0.910675028, 0.624203832]` | `[0.828688511, 0.433121028]` → `[0.992661545, 0.815286636]` | `Wood_Grips_Compact_II_023` |
| 13 | `edge-19-left` | `[0.110875568, 0.217245604]` | `[0.034046221, 0.042771465]` → `[0.187704915, 0.391719743]` | `Wood_Grips_Compact_II_020` |
| 14 | `pocket-19-three-left` | `[0.263934436, 0.184713376]` | `[0.207377062, 0.082802547]` → `[0.320491810, 0.286624206]` | `Wood_Grips_Compact_II_027` |
| 15 | `pocket-19-three-right` | `[0.736065564, 0.184713376]` | `[0.679508190, 0.082802547]` → `[0.792622938, 0.286624206]` | `Wood_Grips_Compact_II_028` |
| 16 | `pocket-19-two-left` | `[0.368032788, 0.184713376]` | `[0.330327871, 0.082802547]` → `[0.405737705, 0.286624206]` | `Wood_Grips_Compact_II_029` |
| 17 | `pocket-19-two-right` | `[0.631967212, 0.184713376]` | `[0.594262295, 0.082802547]` → `[0.669672129, 0.286624206]` | `Wood_Grips_Compact_II_030` |
| 18 | `pocket-19-four-center` | `[0.500000000, 0.184713376]` | `[0.415573772, 0.082802547]` → `[0.584426228, 0.286624206]` | `Wood_Grips_Compact_II_026` |
| 19 | `edge-19-right` | `[0.889124432, 0.217245604]` | `[0.812295085, 0.042771465]` → `[0.965953779, 0.391719743]` | `Wood_Grips_Compact_II_021` |

### Nature Stone Hanger — 8 holds

Historical pre-promotion state: the effective position was `primary` → all
IDs below, with no model orientation. The retained source packet identified
`front` and `reverse` as the two usable faces, with upper/lower contact halves
changing with inversion, but the exact partition was not yet authored. Current
promoted state: `front` and `reverse` have an orientation block and the exact
four-hold-per-face partition documented in the Promotion record below.

| order | hold ID | descriptor center | descriptor face-plane AABB min → max | USDZ node |
| ---: | --- | --- | --- | --- |
| 1 | `edge-front-15mm-incut` | `[0.500000000, 0.793095241]` | `[0.092380923, 0.728095239]` → `[0.907619077, 0.858095244]` | `edge_front_15mm_incut_mesh_001` |
| 2 | `edge-front-15mm-flat` | `[0.500000000, 0.667396390]` | `[0.092380923, 0.599047622]` → `[0.907619077, 0.735745158]` | `edge_front_15mm_flat_mesh_001` |
| 3 | `edge-front-20mm-wood-flat` | `[0.500000000, 0.373571426]` | `[0.092380923, 0.283333331]` → `[0.907619077, 0.463809522]` | `edge_front_20mm_wood_flat_mesh_001` |
| 4 | `edge-front-20mm-granite` | `[0.500000000, 0.190476174]` | `[0.119047616, 0.128571409]` → `[0.880952384, 0.252380940]` | `edge_front_20mm_granite_mesh_001` |
| 5 | `edge-reverse-10mm-incut` | `[0.500000000, 0.789285724]` | `[0.092380923, 0.728095239]` → `[0.907619077, 0.850476209]` | `edge_reverse_10mm_incut_mesh_001` |
| 6 | `edge-reverse-10mm-flat` | `[0.500000000, 0.671207145]` | `[0.092380923, 0.606666666]` → `[0.907619077, 0.735747624]` | `edge_reverse_10mm_flat_mesh_001` |
| 7 | `edge-reverse-06mm-flat` | `[0.500000000, 0.306182134]` | `[0.102857113, 0.248554747]` → `[0.897142887, 0.363809520]` | `edge_reverse_06mm_flat_mesh_001` |
| 8 | `edge-reverse-06mm-incut` | `[0.500000000, 0.196904749]` | `[0.102857113, 0.140952359]` → `[0.897142887, 0.252857138]` | `edge_reverse_06mm_incut_mesh_001` |

### YY Vertical Baguette Evo — 19 logical IDs / 20 selectable mesh pieces

Current effective position: `primary` → all IDs below. Current model
orientation: none. Physical candidates include a primary paired-edge face,
the opposite/reverse contact face, and the continuous Turn & Pull inclination
range. The rounded option has two mesh pieces sharing `rounded-tray`; that is
one logical ID, not two contacts. (Pre-promotion assessment; the final
multi-position grouping and quaternions are authored in the Promotion
record below.)

| order | hold ID | descriptor center | descriptor face-plane AABB min → max | USDZ node(s) |
| ---: | --- | --- | --- | --- |
| 1 | `edge-20-left` | `[0.161538451, 0.599999974]` | `[0.082692306, 0.499999981]` → `[0.240384596, 0.699999966]` | `hold_edge_20mm_left_mesh_001` |
| 2 | `edge-10-left` | `[0.161538451, 0.399999988]` | `[0.082692306, 0.299999996]` → `[0.240384596, 0.499999981]` | `hold_edge_10mm_left_mesh_001` |
| 3 | `edge-25-left` | `[0.314423067, 0.599999974]` | `[0.240384596, 0.499999981]` → `[0.388461538, 0.699999966]` | `hold_edge_25mm_left_mesh_001` |
| 4 | `edge-15-left` | `[0.314423067, 0.399999988]` | `[0.240384596, 0.299999996]` → `[0.388461538, 0.499999981]` | `hold_edge_15mm_left_mesh_001` |
| 5 | `edge-15-right` | `[0.685576933, 0.399999988]` | `[0.611538462, 0.299999996]` → `[0.759615404, 0.499999981]` | `hold_edge_15mm_right_mesh_001` |
| 6 | `edge-25-right` | `[0.685576933, 0.599999974]` | `[0.611538462, 0.499999981]` → `[0.759615404, 0.699999966]` | `hold_edge_25mm_right_mesh_001` |
| 7 | `edge-10-right` | `[0.838461563, 0.399999988]` | `[0.759615404, 0.299999996]` → `[0.917307722, 0.499999981]` | `hold_edge_10mm_right_mesh_001` |
| 8 | `edge-20-right` | `[0.838461563, 0.599999974]` | `[0.759615404, 0.499999981]` → `[0.917307722, 0.699999966]` | `hold_edge_20mm_right_mesh_001` |
| 9 | `edge-12-left` | `[0.314423067, 0.863238063]` | `[0.240384596, 0.726476125]` → `[0.388461538, 1.000000000]` | `hold_edge_12mm_left_mesh_001` |
| 10 | `edge-12-right` | `[0.685576933, 0.863238044]` | `[0.611538462, 0.726476125]` → `[0.759615404, 0.999999963]` | `hold_edge_12mm_right_mesh_001` |
| 11 | `edge-8-left` | `[0.314423067, 0.883238056]` | `[0.240384596, 0.766476111]` → `[0.388461538, 1.000000000]` | `hold_edge_08mm_left_mesh_001` |
| 12 | `edge-8-right` | `[0.685576933, 0.883238037]` | `[0.611538462, 0.766476111]` → `[0.759615404, 0.999999963]` | `hold_edge_08mm_right_mesh_001` |
| 13 | `edge-6-upper` | `[0.156730749, 0.923238032]` | `[0.082692278, 0.846476101]` → `[0.230769220, 0.999999963]` | `hold_edge_06mm_left_mesh_001` |
| 14 | `edge-6-lower` | `[0.843269237, 0.923238032]` | `[0.769230780, 0.846476101]` → `[0.917307694, 0.999999963]` | `hold_edge_06mm_right_mesh_001` |
| 15 | `edge-central-30` | `[0.500000000, 0.599999974]` | `[0.423076922, 0.499999981]` → `[0.576923078, 0.699999966]` | `hold_central_30mm_mesh_001` |
| 16 | `edge-central-25` | `[0.500000000, 0.399999988]` | `[0.423076922, 0.299999996]` → `[0.576923078, 0.499999981]` | `hold_central_25mm_mesh_001` |
| 17 | `edge-central-20` | `[0.500000000, 0.691557015]` | `[0.423076922, 0.424961519]` → `[0.576923078, 0.958152512]` | `hold_central_20mm_mesh_001` |
| 18 | `edge-central-6` | `[0.500000000, 0.825936649]` | `[0.423076922, 0.652280658]` → `[0.576923078, 0.999592640]` | `hold_central_06mm_mesh_001` |
| 19 | `rounded-tray` | `[0.500000000, 0.136502368]` | `[0.076923064, 0.000000000]` → `[0.923076936, 0.273004737]` | `hold_rounded_left_mesh_001`, `hold_rounded_right_mesh_001` |

### Tension Flash Board — 7 holds (historical suspension package)

Four legacy suspension poses (`three-edge-upright`, `three-edge-inverted`,
`two-edge-upright`, `two-edge-inverted`), each materializing the complete
ordered inventory below. The single-cord suspension block is established and
mutually exclusive with orientation, so no rotation review applies.

| order | hold ID | descriptor center | descriptor face-plane AABB min → max | USDZ node(s) |
| ---: | --- | --- | --- | --- |
| 1 | `three-edge-left` | `[0.224000003, 0.487840751]` | `[0.1096, 0.255944657]` → `[0.338400006, 0.719736844]` | `flash_board_body_012` |
| 2 | `three-edge-center` | `[0.500000015, 0.487840751]` | `[0.385600001, 0.255944657]` → `[0.614400029, 0.719736844]` | `flash_board_body_011` |
| 3 | `three-edge-right` | `[0.775999993, 0.487840738]` | `[0.661599994, 0.255944632]` → `[0.890399992, 0.719736844]` | `flash_board_body_013` |
| 4 | `two-edge-left` | `[0.254000001, 0.44017887]` | `[0.132599995, 0.213252436]` → `[0.375400007, 0.667105303]` | `flash_board_body_014` |
| 5 | `two-edge-right` | `[0.745999992, 0.44017887]` | `[0.624599993, 0.213252436]` → `[0.867399991, 0.667105303]` | `flash_board_body_015` |
| 6 | `small-crimp-left` | `[0.328000009, 0.810526313]` | `[0.264400005, 0.772368433]` → `[0.391600013, 0.848684193]` | `flash_board_body_009` |
| 7 | `small-crimp-right` | `[0.671999991, 0.810526313]` | `[0.608399987, 0.772368433]` → `[0.735599995, 0.848684193]` | `flash_board_body_010` |

## Physical disposition candidates and uncertainty

### Beastmaker 1000

The manufacturer's product page describes a wood 1000 Series board, a
580 × 150 mm face, two jugs, 35° and 20° slopers, and grouped pocket families.
The official straight-on Tulip image establishes the visible front layout. The
prior packet's FluxPerfect image is an elevated three-quarter view and reveals
the top plane, rounded end, and outer side/depth, but it is commerce-gap
evidence and does not establish a reverse usable face. The current model's
single fixed position is therefore the conservative disposition. It has no
orientation quaternion and no front/reverse grouping.

Limitations: no manufacturer numbered guide, per-ID depth assignment, cavity
section, back profile, or exact radius. The grouped marketing quantities do
not reconcile to all 22 visible contacts; the prior metadata audit explicitly
keeps the 22 stable IDs. Do not use the oblique image to promote a visual
estimate into physical metadata.

### Metolius Wood Grips Compact II

The current manufacturer page identifies Compact II as 610 × 157 mm (24 ×
6.2 in), FSC-certified wood, and a large assortment of jugs, slopers, edges
and pockets. Its compact front image and depth diagram establish the visible
lower Compact layout and the 29/19 mm edge and pocket labels; the upper Deluxe
layout is excluded. The retained Bergfreunde image supplies a distinct
elevated front oblique and top/side rollover view as a commerce gap. It does
not establish hidden back geometry or a second usable face. The one fixed
`primary` position and absent orientation are consequently intentional.

Limitations: the diagram's 56 mm numbers describe slopers, not board/body
thickness; no complete manufacturer section, back profile, or exact aperture
profile is available. Existing model depth is an authored display estimate.

### Nature Climbing Stone Hanger

The current Granite Stone Hanger page identifies FSC oak and Norwegian
granite, 105 × 105 × 35 mm, and 20/15/10/6 mm edge families. Its manufacturer
gallery includes distinct front product views and oblique/reverse or use
views. The retained integration packet identifies two physical lateral cord
passage markers (front-view left/right) and eight named edge contacts split by
front/reverse source semantics. These establish two physical usable faces as
orientation candidates, not the final ID grouping.

The two candidates are `front` (front face, with its upper/lower contacts) and
`reverse` (block inverted to expose the reverse face). A future orientation
object may use `modelBoundsCenter` as its pivot only after Astra verifies the
actual export and chooses canonical quaternions. The current packet does not
choose those quaternions or assign all eight IDs to the two positions.

Limitations: product-use and gallery photographs do not expose a complete
sectional cord route, four passage endpoints, cord geometry, hidden sleeve
depth, or exact incut profiles. The two marker mouths support visible lateral
openings only. No additional pinch, jug, notch, route, or contact is inferred.

### YY Vertical Baguette Evo

The current manufacturer page identifies the round Baguette Evo Turn & Pull
version, 520 × 50 × 50 mm, rubberwood, seven paired depths (25/20/15/12/10/8/6
mm), four central depths (30/25/20/6 mm), and rounded trays. The manufacturer
gallery contains distinct product/front, reverse and use/oblique views. The
retained source README describes the physical paired/reverse disposition and
the continuous Turn & Pull inclination; its supplied mapping binds 20
selectable mesh pieces to 19 logical IDs because both rounded pieces share
`rounded-tray`.

The candidates are a paired-edge primary face, the opposite/reverse contact
face, and intermediate Turn & Pull inclinations. The existing descriptor
centers/AABBs are a spatial inventory only; they do not prove which IDs are
active in each physical face. The reviewed five-position grouping and
canonical quaternions are authored in the Promotion record below.

### Tension Flash Board (historical suspension disposition)

Portable suspended board with a shipped single-cord suspension block
(`type`, `attachment`, `anchor`, `cord`, four `canonicalPoses`) and four
legacy positions (`three-edge-upright`, `three-edge-inverted`,
`two-edge-upright`, `two-edge-inverted`), each materializing the complete
seven-hold inventory. Orientation is mutually exclusive with suspension, so
no rotation review applies and no quaternion is authored.

Limitations: this packet did not re-review the Flash gallery or cord route;
it records the shipped suspension disposition only. Hidden bore paths, exact
milling profiles, and body sections remain unpublished.

Limitations: the manufacturer does not publish exact machining profiles,
pocket widths, fillets, bore dimensions, or small-edge offsets. The retained
model README labels those values as photograph-constrained display estimates.
No continuous cord route, anchor, knot, or hidden bore path is inferred from
the use photographs.

## Evidence URLs and retained artifacts

The source tiers below state exactly what each item supports and what it cannot
support. Manufacturer URLs are first tier. Commerce links are gap evidence
only and cannot override a manufacturer claim.

| package | primary URLs / visual artifacts | supports | does not support |
| --- | --- | --- | --- |
| Beastmaker 1000 | [manufacturer product page](https://www.beastmaker.co.uk/products/beastmaker-1000-series); [official front](https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068); [Beech/shared-layout page](https://www.beastmaker.co.uk/products/beastmaker-1000-beech); [FluxPerfect commerce-gap page](https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard) | identity, wood, 580 × 150 mm face, grouped hold families, visible front layout; FluxPerfect `Ansicht_1` adds a complete top/side/rounded-end view | per-ID family/depth map, hidden reverse, cavity sections, exact thickness/radii |
| Metolius Compact II | [manufacturer product page](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards); [official Compact front](https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg?v=1759460952&width=2000); [official depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428&width=2000); [Bergfreunde commerce-gap page](https://www.bergfreunde.eu/metolius-wood-grips-compact-ii-training-board/) | Compact identity/dimensions, front inventory, 29/19 mm and 56 mm diagram labels; commerce view adds top/side rollover | hidden back, complete sections, exact body depth, alternate usable face |
| Nature Stone Hanger | [manufacturer product page](https://natureclimbing.com/products/stone-hanger-1); gallery artifacts `GRANITE1_2_1024x.png`, `GRANITE1_1024x.png`, `GRANITE2_2_800x.png`, `GRANITE2_1024x.png` linked from that page | exact selected product family, oak/granite, 105 × 105 × 35 mm, 20/15/10/6 mm families, multiple front/oblique/reverse-use views; retained technical drawing and mapping establish eight named contacts and the promoted front/reverse partition | complete cord route, hidden bore/sleeve, exact contact sections |
| Baguette Evo | [manufacturer English product page](https://www.yyvertical.com/en-eu/products/baguette-evo); [manufacturer product page](https://www.yyvertical.com/en/products/baguette-evo); gallery artifacts `YY_BAGUETTE_EVO_02_FG.webp`, `YY_BAGUETTE_EVO_07_FG.webp`, `YY_BAGUETTE_EVO_03_FG.webp`, and the use image `yy-vertical-escalade-agres-nomade-entrainement-nomadic-tool-gear-equipment-training-baguette-evo-utilisation-22.webp` linked from the page | exact round Evo identity, 520 × 50 × 50 mm, named paired/central depths, rounded option, Turn & Pull and multiple product/use views; reviewed five-position grouping and quaternions in the Promotion record | exact milling profiles, fillets, bore dimensions, hidden cord route |
| Tension Flash Board | [manufacturer product page](https://tensionclimbing.com/products/flash-board-2) | suspended portable board identity; shipped suspension block and four hanging poses; seven named contacts | re-reviewed gallery/cord route, body sections, orientation (not applicable) |

### Existing local audit and packet links

These are the existing package-evidence sources used by this packet; they are
not new source claims:

* [`2026-09-10-imported-model-packages.md`](2026-09-10-imported-model-packages.md)
  records the four promotions, mappings, descriptor/report hashes, and the
  Baguette/Nature fidelity limits.
* [`2026-08-12-beastmaker-board-packages.md`](2026-08-12-beastmaker-board-packages.md)
  records Beastmaker's front/oblique evidence ledger and the exact retained
  artifact hashes. The referenced packet paths are under
  `.context/shaky-rat-beastmaker-1000/` (workspace evidence, not board assets).
* [`2026-08-12-metolius-board-packages.md`](2026-08-12-metolius-board-packages.md)
  records Compact II's manufacturer front/depth diagram and Bergfreunde gap
  view, including retained hashes under
  `.context/shaky-rat-metolius-wood-grips-compact-ii/`.
* Baguette retained evidence: `.context/import-hangboard-model-packages/source-evidence/baguette-evo/YY-Vertical-Baguette-Evo/README.md`,
  `hold-mapping.json`, `validation-report.json`; explicit package mapping:
  `.context/import-hangboard-model-packages/mappings/baguette-evo.json`; final
  verification: `.context/import-hangboard-model-packages/reports/baguette-evo-verification.json`.
* Nature retained evidence: `.context/import-hangboard-model-packages/source-evidence/nature-stone-hanger/nature-stone-hanger/README.md`,
  `integration.json`, `qa/validation.json`; explicit package mapping:
  `.context/import-hangboard-model-packages/mappings/nature-stone-hanger.json`;
  final verification:
  `.context/import-hangboard-model-packages/reports/nature-stone-hanger-verification.json`.

The Baguette README's `Hold IDs and object mapping` and Nature README's `Hold
ID → object mapping` are evidence mappings for the supplied display assets;
they are not an Astra-approved app position grouping.

## Fixed-board rationale

Beastmaker 1000 and Metolius Compact II remain fixed model presentations for
this step. Their retained evidence establishes one intended front display and
does not establish a second selectable physical face, a canonical inversion
pose, or a complete contact-to-face mapping. Adding a guessed reverse position
would turn a visual side/profile observation into unsupported interaction
semantics. The current single `primary` position therefore preserves the
existing ordered inventory and avoids authoring an orientation quaternion that
the evidence cannot justify.

Nature and Baguette differ: the evidence explicitly depicts two usable faces
or a reversible/continuously adjustable tool. Their reviewed groupings and
quaternions are authored in the Promotion record below. The Tension Flash
Board is a third disposition — suspended, not fixed and not orientable —
and keeps its shipped suspension poses with no orientation metadata.

## Astra handoff checklist

The Astra handoff is complete for Nature and Baguette. These historical steps
are recorded in the Promotion record below and are not applicable to the fixed
boards or to the Flash Board (suspension path). Only the synthetic-landscape
presentation anomaly remains open:

- [x] Approved the exact retained source snapshots and hashes.
- [x] Verified the declared board coordinate frame against the actual USDZ.
- [x] Authored complete ordered position partitions for Nature and Baguette
  with no guessed or duplicated hold IDs.
- [x] Selected canonical quaternions about `modelBoundsCenter` after visual
  review of front/reverse/inclined poses.
- [x] Reran descriptor/package validation; no model or descriptor bytes
  changed, so the recorded baseline hashes remain current.
- [ ] Verify Nature on a physical device genuinely rotated to landscape; the
  synthetic-landscape harness still renders its 3D card blank.

## Promotion record (orientation metadata authored)

The Astra review below promoted the two pending packages. No USDZ or
descriptor bytes changed; only `board.json` `positions` and
`media.orientation` were added. Quaternions are `[x, y, z, w]` unit values in
the descriptor `hang-ten-board-v1` frame, applied about `modelBoundsCenter`.
Every angle is an authored display estimate: it was deliberately chosen from
the retained manufacturer evidence and model geometry so that selecting a hold
rotates the shared model to expose that hold's usable face. No angle is a
manufacturer-published training prescription. Author: Muse Spark (Astra-class
review), 2026-09-11.

### Nature Stone Hanger — `front` / `reverse`

Grouping is source-backed: the manufacturer technical drawing and retained
README map the four `edge-front-*` contacts to the front face and the four
`edge-reverse-*` contacts to the reverse face (upper contacts on each face are
used with the block inverted; the position is the face, not the inversion).

| position | hold IDs (canonical board order) | quaternion | basis |
| --- | --- | --- | --- |
| `front` | `edge-front-15mm-incut`, `edge-front-15mm-flat`, `edge-front-20mm-wood-flat`, `edge-front-20mm-granite` | `[0, 0, 0, 1]` | identity = delivered base pose; source-backed front face |
| `reverse` | `edge-reverse-10mm-incut`, `edge-reverse-10mm-flat`, `edge-reverse-06mm-flat`, `edge-reverse-06mm-incut` | `[0, 1, 0, 0]` | authored display estimate: 180° about vertical exposes the reverse face |

### Baguette Evo — five reviewed groupings

Position IDs restore the five pre-migration legacy surfaces
(`e09aa982`), whose contact families match the retained README
`source_feature` mapping (`front_outer`/`front_inner`,
`small_inner`/`small_outer`, `central_reverse`, `central_small`,
`rounded_warmup`). The bar's long axis is X with left/right stable under
X-axis roll, so all non-identity quaternions roll about X. Each angle is an
authored display estimate reviewed against the manufacturer front/reverse/use
gallery and the local Blender review renders
(`.context/royal-anaconda/task6-astra-evidence/`).

| position | hold IDs (canonical board order) | quaternion | basis |
| --- | --- | --- | --- |
| `paired-25-20-15-10` | `edge-20-left`, `edge-10-left`, `edge-25-left`, `edge-15-left`, `edge-15-right`, `edge-25-right`, `edge-10-right`, `edge-20-right` | `[0, 0, 0, 1]` | identity = delivered base pose showing the primary stepped recess (photos 04/06) |
| `paired-12-8-6` | `edge-12-left`, `edge-12-right`, `edge-8-left`, `edge-8-right`, `edge-6-upper`, `edge-6-lower` | `[0.707106781, 0, 0, 0.707106781]` | authored display estimate: +90° about X looks down into the top small channels (12 front-facing, 8 rear-facing walls of one channel family) |
| `central-30-25` | `edge-central-30`, `edge-central-25` | `[1, 0, 0, 0]` | authored display estimate: 180° about X exposes the reverse central recess (photo 05), left/right stable |
| `central-20-6` | `edge-central-20`, `edge-central-6` | `[0.5, 0, 0, 0.866025404]` | authored display estimate: +60° about X, top-inclined view into the small top recess showing its front (20) and rear (6) walls |
| `rounded-tray` | `rounded-tray` | `[-0.707106781, 0, 0, 0.707106781]` | authored display estimate: −90° about X brings the rounded lower cylinder contact to the front |

The 19 logical IDs partition exactly once (8+6+2+2+1); `rounded-tray`
remains one logical ID over two mesh pieces. No new contacts were inferred.

### Verification

- `test_model_orientation_inventory.py`: 26 passed (was 23 passed + 3 RED).
- `test_model_first_packages.py` + `test_approved_board_packages.py`: all pass.
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`: exit 0, 0 drafts.
- Beastmaker 1000 and Metolius Compact II untouched: single `primary`
  position, no orientation block (fixed/front-only disposition confirmed).

## Batch-01 / batch-02 promotion record (2026-09-11/12, Muse Spark)

Discovery now finds fourteen complete model packages: the original four
(Beastmaker 1000, Compact II, Nature, and Baguette) plus
`beastmaker-2000`, `lattice-triple-rung`, `metolius.prime-rib`,
`metolius.project`, `tension.flash-board`, `captain-fingerfood.dual`,
`captain-fingerfood.pocket`, `captain-fingerfood.unlevel`,
`lattice.mxedge-lift-large`, and `lattice.mxedge-lift-small`. No USDZ or
descriptor bytes changed in this pass; only `board.json` `positions` and
`media.orientation` were added by the conversion. Quaternions are `[x, y, z,
w]` unit values in the descriptor `hang-ten-board-v1` frame, applied about
`modelBoundsCenter`. The `board.json` schema rejects provenance keys, so this
document is the labeling vehicle: every non-identity angle below is an
authored display estimate, deliberately chosen from the retained manufacturer
evidence and model geometry so that selecting a hold rotates the shared model
to expose that hold's usable face. No angle is a manufacturer-published
training prescription. Author: Muse Spark, 2026-09-11/12.

### Fixed boards — single legacy `primary` position, no orientation block

These four boards keep the full logical inventory in one loader-materialized
`primary` position (no explicit `positions`, no `orientation` block). The
physical basis in each case is a single fixed front face: the retained
manufacturer evidence shows the front product view and no source-backed
selectable second face.

| package ID | holds | descriptor model bounds (`min` → `max`) | pivot | evidence basis |
| --- | ---: | --- | --- | --- |
| `beastmaker-2000` | 27: `top-sloper-1..4`, `front-upper-1..2`, `front-middle-1..9`, `front-lower-1..9`, `hold-26`, `hold-27`, `hold-28` | `[-0.289999992, 0.0, 0.0]` → `[0.289999992, 0.150000006, 0.057999998]` | none (no orientation block) | Beastmaker 2000 series page (`https://www.beastmaker.co.uk/products/beastmaker-2000-series`); batch-01 research preserves the 27-contact inventory exactly |
| `lattice-triple-rung` | 3: `edge-45`, `edge-10`, `edge-20` | `[-0.275000006, 0.0, 0.0]` → `[0.275000006, 0.129999995, 0.050000001]` | none (no orientation block) | Lattice Triple Rung page (`https://latticetraining.com/product/triple-rung-wooden-hangboard/`); batch-01 research corroborates the mounted front disposition and records no manufacturer back/underside orthographic |
| `metolius.prime-rib` | 3: `edge-38`, `edge-23`, `edge-15` | `[-0.254000008, 0.0, 0.0]` → `[0.254000008, 0.106679998, 0.0381]` | none (no orientation block) | Metolius Prime Rib page (`https://www.metoliusclimbing.com/products/prime-rib`); batch-01 research records no exact-revision reverse/back view |
| `metolius.project` | 17: `jug-1-left`, `round-sloper-8-center`, `jug-1-right`, `flat-sloper-2-left`, `flat-sloper-2-right`, `pocket-3-left/right`, `edge-4-left/right`, `pocket-5-left/right`, `pocket-6-left/right`, `pocket-7-left/right`, `edge-9-center`, `edge-10-center` | `[-0.311150014, 0.0, 0.0]` → `[0.311150014, 0.152400002, 0.075999998]` | none (no orientation block) | Metolius Project page plus the official numbered depth diagram (`https://www.metoliusclimbing.com/cdn/shop/files/project-depth.jpg?v=1762201307`), which distinguishes the paired #2 55 mm flat slopers (new `flat-sloper-2-left/right` IDs) from the #8 53 mm center round sloper |

### Tension Flash Board — upright / inverted `three-edge` and `two-edge`

Grouping is source-backed: the batch-01 research ruling confirms five cavity
zones retaining their existing IDs and declares the two legacy small-crimp
IDs unresolved and unbound (no selectable geometry fabricated for them), so
the two face inventories jointly cover all five descriptor contacts. The
upright and inverted positions for a face intentionally overlap with identical
hold IDs because both orientations expose the same physical contacts.

Descriptor model bounds: `[-0.241300002, 0.0, 0.0]` →
`[0.241300002, 0.076200001, 0.076200001]`. Pivot: `modelBoundsCenter`.

| position | hold IDs (canonical board order) | quaternion | basis |
| --- | --- | --- | --- |
| `three-edge-upright` | `three-edge-left`, `three-edge-center`, `three-edge-right` | `[0, 0, 0, 1]` | identity = delivered base pose; source-backed three-edge broad face upright |
| `three-edge-inverted` | `three-edge-left`, `three-edge-center`, `three-edge-right` | `[0, 0, 1, 0]` | authored display estimate: half-turn about Z presents the same three-edge face inverted |
| `two-edge-upright` | `two-edge-left`, `two-edge-right` | `[0, 1, 0, 0]` | authored display estimate: 180° about Y exposes the opposing two-edge face while preserving its up axis |
| `two-edge-inverted` | `two-edge-left`, `two-edge-right` | `[1, 0, 0, 0]` | authored display estimate: 180° about X exposes the same two-edge face inverted |

### Captain Fingerfood — four single-contact positions each

Each board's four positions partition its four-contact descriptor inventory
exactly once (1+1+1+1). Groupings follow the batch-02 research contact
inventories (front recess long lips, short-end Pocket end-wall, outer jug
rim); every research `orientationDecision` records `axisProvenance:
authored-estimate` with exact display angle and pivot as authored estimates.
Pivot for all three boards: `modelBoundsCenter`.

#### DUAL — `captain-fingerfood.dual`

Descriptor model bounds: `[-0.059999999, -0.035, -0.015]` →
`[0.059999999, 0.035, 0.015]`. Evidence: DUAL page
(`https://en.captainfingerfood.rocks/products/dual-hangboard`); batch-02
research behavior "contacts are fixed to one board: a single front recess
with opposing long lips plus a separately labeled short-end Pocket".
The model-visible width/height ratio is recorded as `1.7142857`. The official
grip panel depicts one hand using the short-end pocket, supporting
`handCapacity: 1` without asserting an unsupported finger count.

| position | hold IDs | quaternion | basis |
| --- | --- | --- | --- |
| `curved-lip-front` | `curved-edge-20` | `[0.173648148, 0.0, 0.0, 0.984807758]` | authored display estimate: +20° about X onto the curved lip |
| `straight-lip-inverted` | `straight-edge-20` | `[8e-09, 0.173648148, -0.984807758, 4.3e-08]` | authored display estimate: half-turn exposing the inverted straight lip |
| `left-pocket-vertical` | `pocket-end-wall-20` | `[0.122787789, -0.122787789, 0.696364243, 0.696364243]` | authored display estimate: ~92° tilt onto the short end-wall |
| `exterior-jug-back` | `outer-jug` | `[-0.984807767, 0.0, 0.0, 0.1736481]` | authored display estimate: 160° about X onto the exterior jug back |

#### POCKET Lines — `captain-fingerfood.pocket`

Descriptor model bounds: `[-0.055, -0.033, -0.0145]` →
`[0.055, 0.033, 0.0145]`. Evidence: Lines page
(`https://en.captainfingerfood.rocks/products/lines-hangboard`); batch-02
research behavior "single front recess with long grip edges plus separately
labeled short-end Pocket".
The model-visible width/height ratio is recorded as `1.6666667`. The official
`LINESGriffe.jpg` panel labels the short-end contact `15/20mm Pocket` and shows
one-finger, one-hand use, supporting `depthRangeMillimeters` lower/upper
bounds of `15`/`20`, `fingerCapacity: 1`, and `handCapacity: 1`. The package
still declares only
the single `primary` equipment object; this metadata does not make bilateral
steps available.

| position | hold IDs | quaternion | basis |
| --- | --- | --- | --- |
| `edge-20-front` | `edge-20` | `[0.199367862, 0.0, 0.0, 0.979924719]` | authored display estimate: +23° about X onto the 20 mm edge |
| `edge-15-inverted` | `edge-15` | `[9e-09, 0.199367862, -0.979924719, 4.3e-08]` | authored display estimate: half-turn exposing the inverted 15 mm edge |
| `pocket-short-end` | `pocket-end-wall-15-20` | `[0.14097438, -0.14097438, 0.692911411, 0.692911411]` | authored display estimate: ~92° tilt onto the short end-wall |
| `jug-reverse` | `jug-outer-rim` | `[9e-09, 0.979924719, 0.199367862, 4.3e-08]` | authored display estimate: half-turn onto the outer jug rim |

#### UNLEVEL — `captain-fingerfood.unlevel`

Descriptor model bounds: `[-0.059999999, -0.035, -0.015]` →
`[0.059999999, 0.035, 0.015]`. Evidence: UNLEVEL page
(`https://en.captainfingerfood.rocks/products/unlevel-hangboard`); batch-02
research behavior "contacts are fixed to one board: a single front recess
with opposing long lips plus a separately labeled short-end Pocket".
The model-visible width/height ratio is recorded as
`1.7142857142857142`. Official grip panels show one hand using the short-end
pocket, supporting `handCapacity: 1`; finger capacity remains omitted because
the retained panels show different finger pairs rather than one fixed count.

| position | hold IDs | quaternion | basis |
| --- | --- | --- | --- |
| `edge20-front` | `curved-edge-20` | `[0.207911694, 0.0, 0.0, 0.9781476]` | authored display estimate: +24° about X onto the 20 mm curved edge |
| `edge25-inverted` | `curved-edge-25` | `[9e-09, 0.207911694, -0.9781476, 4.3e-08]` | authored display estimate: half-turn exposing the inverted 25 mm edge |
| `jug-reverse` | `outer-jug` | `[9e-09, 0.9781476, 0.207911694, 4.3e-08]` | authored display estimate: half-turn onto the outer jug |
| `pocket-right-end` | `pocket-end-wall-20-25` | `[0.147015774, 0.147015759, -0.691654772, 0.691654831]` | authored display estimate: ~92° tilt onto the short end-wall |

### Lattice MXEdge Lift — lower group plus inverted upper lip

Both boards group the lower lips and mono in one front position and expose
the upper lip inverted (3+1 partition, exact). Groupings are source-backed by
the Lattice MXEdge Lift page, the instruction artwork (S02), and the
front/back weighed views (S04/S05); the batch-02 research classifies both
boards flippable with source-supported upright/inverted displays while
recording that no physical hinge, pivot, or axis is published, so every
numeric angle below is an authored display estimate. Pivot for both boards:
`modelBoundsCenter`. Both descriptors share model bounds
`[-0.083999999, -0.048999999, -0.017000001]` →
`[0.083999999, 0.048999999, 0.017000001]`.
Both packages record the manufacturer product page's `20 × 11 × 5 cm`
technical dimensions rather than reusing these display-model bounds. The
retained source packet separately preserves the manufacturer's conflicting
`16.8 × 9.8 × 3.4 cm` infographic dimensions; neither value is inferred from
the model.

#### Large — `lattice.mxedge-lift-large`

| position | hold IDs (canonical board order) | quaternion | basis |
| --- | --- | --- | --- |
| `lower-lips-front` | `edge-22`, `edge-16`, `mono-28` | `[0.190808995, 0.0, 0.0, 0.981627183]` | authored display estimate: +22° about X onto the lower lips and mono |
| `upper-lip-inverted` | `edge-12` | `[0.0, 0.190808995, -0.981627183, 0.0]` | authored display estimate: half-turn exposing the inverted MX12 upper lip |

#### Small — `lattice.mxedge-lift-small`

| position | hold IDs (canonical board order) | quaternion | basis |
| --- | --- | --- | --- |
| `lower-lips-and-mono` | `edge-18`, `edge-14`, `mono-25` | `[0.156434415, 0.0, 0.0, 0.987688349]` | authored display estimate: +18° about X onto the lower lips and mono |
| `inverted-upper-lip` | `edge-8` | `[7e-09, 0.156434415, -0.987688349, 4.3e-08]` | authored display estimate: half-turn exposing the inverted MX8 upper lip |

### Verification (batch-01 / batch-02 historical pass)

- `test_model_orientation_inventory.py`: `MODEL_PACKAGE_IDS` grows 4 → 14;
  `test_discovered_model_inventory_is_exactly_the_fourteen_current_packages`
  plus the fixed-package single-position contract over all six fixed boards.
- `test_approved_board_packages.py`: prime-rib and flash raster freezes
  replaced with model-package freezes; new project model freeze and
  descriptor-mirror test replace the removed coderabbit project params;
  beastmaker mirrors move to descriptor assertions in
  `test_beastmaker_2000_board_package.py`.
- Metadata ledger: flash small-crimp rows removed (unbound legacy IDs);
  project `flat-sloper-2-left/right` rows added against the official numbered
  depth diagram.
- `scripts/hangboard-packages.sh validate --root Hangboards
  --final-inventory`: exit 0, 0 drafts (rerun in this pass).

### Verification (September 15 collection extension)

- `test_model_orientation_inventory.py`: `MODEL_PACKAGE_IDS` now contains 26
  current model packages, including the six fixed packages in the collection
  extension table above.

### Verification (batch-02 collection extension)

- `test_model_orientation_inventory.py`: `MODEL_PACKAGE_IDS` now contains 32
  current model packages, including the six batch-02 fixed packages in the
  batch-02 collection extension table above.

## Task 7 visual validation (2026-09-11, Muse Spark)

Simulator: owned `Hang Ten Paseo royal-anaconda Review` devices (iPhone 17
Pro / iOS 26.5 UUID `2017D61B` (captures) and `DE1572BF` (live debugging),
iPhone SE 3rd gen for one control), Debug builds, `HANGTEN_REVIEW_BOARD_ID`
+ `HANGTEN_REVIEW_BOARD_DETAIL` + `HANGTEN_REVIEW_HOLD_ID` review routes
(no production UI or package changes). Selecting a hold auto-rotates the
shared model to that hold's canonical position; every screenshot below is
therefore an end-to-end orientation proof, not a posed render.

### Confirmed rendering (real device pixels, reviewed)

| board | position (hold) | result |
| --- | --- | --- |
| Baguette | `paired-25-20-15-10` (`edge-10-left`) | front face, primary recess, red highlight; landscape + portrait |
| Baguette | `paired-12-8-6` (`edge-12-left`) | rolled to top channels, red highlight; landscape + portrait |
| Baguette | `central-30-25` (`edge-central-30`) | rolled 180° to reverse recess, red highlight, left/right stable; landscape + portrait |
| Baguette | `central-20-6` (`edge-central-20`) | top-inclined small recess, red highlight; landscape + portrait |
| Baguette | `rounded-tray` (`rounded-tray`) | rolled to underside, both tray meshes red, Jug card; landscape + portrait |
| Nature | `front` (`edge-front-15mm-incut`) | front face, red incut lip, hold card, legend; portrait |
| Nature | `reverse` (`edge-reverse-10mm-incut`) | reverse all-wood face (no granite), red 10 mm lip; portrait |
| Beastmaker 1000 | `primary` (`jug-left`) | fixed front path, red jug; landscape |
| Compact II | `primary` (`jug-left`) | fixed front path, red jug; landscape |

Framing keeps every board inside its viewport; manual orbit/reset behavior
is covered by the `BoardModelTests`/`SuspendedBoardPresentationTests` suites
(55/55 GREEN on an isolated simulator, including two new permanent
orientation guards); display-only preview policy, workout surfaces, and
physical-device rotation/gesture QA remain recommended follow-ups, as does
an Android SDK-backed JUnit run (no SDK on this machine).

### Open anomaly: Nature 3D card blank under the synthetic landscape flag

With `HANGTEN_REVIEW_LANDSCAPE=1` (a programmatic
`requestGeometryUpdate(.landscapeRight)`, device physically portrait),
Nature's 3D card renders blank while Baguette/Beastmaker/Compact render in
the same harness. Deterministic across 5+ samples and 10–60 s waits.
Eliminated by live-debugger inspection of the running app: view has nonzero
size (682×682), scene/geometry/lights/camera all present and correct
(camera at the expected front framing, model bounds exactly the descriptor
bounds), no crash, no errors, no unavailable state; forced `setNeedsDisplay`,
continuous rendering, and scene re-assignment do not paint geometry, while
setting `scene.background` red DOES composite (so the layer presents but
geometry rasterizes nothing in this configuration). The metadata is
exonerated: the identical scene state renders correctly in portrait, and the
shared renderer proves itself on the other three boards in the same harness.
Suspected harness presentation edge (synthetic rotation + non-continuous
`SCNView` + screenshot compositor), not a package defect — but unproven.
A drawable-size explanation is ruled out: Beastmaker's landscape drawable
(~1.5M px) renders while smaller configurations blank, and shrinking the
Nature drawable via debugger did not restore pixels. Follow-up: verify
Nature on a physical device rotated to landscape, and add an
XCUITest/orbit-tap pass when UI automation is available (this machine
blocks assistive access for scripting).

### Descriptor note (verified, no fix needed)

CPU head-on rays at the descriptor `facePlaneAABB` centers strike body
geometry rather than hold meshes for Nature's recessed contacts. This was
first suspected to be stale descriptor data, but reprojecting every hold
mesh from the shipped USDZ (root X-rotation applied, normalized over model
bounds) reproduces the checked-in AABBs to within 1.5e-8 (float32 text
precision only) — the AABBs are CORRECT patch bounds. The rays simply pass
through the pocket mouth voids and strike recess interior walls, which are
authored as body mesh while only the contact lips are hold meshes (the
portrait renders confirm open pockets with red lips). Tap selection operates
on rendered pixels (proven working above), and legend entries resolve from
the same correct AABBs, so nothing user-visible breaks. The shared
nearest-hit test helper's universal assumption (patch-center ray strikes a
hold) does not cover lip-modeled recessed contacts; the new regression
tests assert binding, selection, and finite framing instead.

### 2026-09-20 Batch 04 orientation-source handoff

Batch 04 package migrations consume the closed source register rather than
reusing historical orientation prose. Pivot is the sole Batch 04 multi-position
exception: its normalized 18 physical contacts retain only selectable `p1`,
`p2`, `p3`, and `p5`; `p4` is manufacturer Orientation 3 Switch transition
evidence only. The 72 retired raster presentation IDs are compatibility
aliases for those 18 physical contacts, not additional selectable contacts.
The exact delivered-ID mapping and manufacturer-photo hashes are retained in
[`2026-09-20-batch-04-3d-source-register.json`](2026-09-20-batch-04-3d-source-register.json).

#### YY Vertical Penta Evo

`yy.penta-evo` is one canonical Penta unit rendered twice as the identical
`left-penta` and `right-penta` instances. Neither instance carries a reflection;
the pair is not a left/right mirror. Both instances expose the same seven slot
IDs (`edge-25`, `edge-20`, `edge-15`, `edge-10`, `mono`, `duo`, and `tray`) and
map those slots to their same-suffixed `-left` or `-right` physical contacts.

The reviewed position inventory is `primary` and `reverse`. The YY Vertical
product page documents rotation of the Penta through its retaining notches;
`reverse` is retained to expose the rear 10 mm edge. The two instances share
the same authored position transform for each position, while their separate
placement and suspension metadata keeps the units physically distinct. This
is display orientation metadata, not a claim of factory angular metrology.

#### Trango Rock Prodigy Pivot

`trango.rock-prodigy-pivot` is one canonical reauthored resin half rendered
twice. The `left-half` instance is unreflected; the `right-half` instance
carries `reflection: "x"` about the unit bounds centre. Unlike Penta, this pair
*is* a left/right mirror, which is why exactly one physical half is exported.
Both instances expose the same nine slot IDs (`upper-sloped-crimp`,
`outer-sloped-crimp`, `variable-edge`, `medium-crimp`, `large-crimp`,
`two-finger-pocket`, `three-finger-pocket`, `outer-wedge-pinch`, and
`lower-sloper`) and map those slots to their same-suffixed `-left` or `-right`
physical contacts, giving 18 physical contacts in total.

The reviewed position inventory is exactly `p1`, `p2`, `p3`, and `p5`. Each
instance owns a complete nine-decimal `positionTransforms` entry for those four
keys and for no others; there is no top-level orientation or suspension
metadata. Each Pivot unit mounts and rotates independently, so a position
rotates each already-placed half about its own bounds centre: `p1` identity,
`p2` a quarter turn about the model Z axis, `p3` a half turn, and `p5` the
opposite quarter turn combined with the manufacturer side switch, which
exchanges the two physical halves through their position translations. The
right instance's rotation is the mirror conjugate of the left instance's, so
the assembled pair stays mirror-symmetric in every position. Physical contact
IDs are stable through every rotation and through the side exchange.

Batch `p4` is manufacturer Orientation 3 Switch transition evidence only and is
deliberately absent from both the package positions and both position transform
maps. Model bounds, quaternions, translations, spacing, pivot choice and camera
are display orientation metadata and `authored display estimate` values, not a
claim of factory angular metrology.

## J Bryant FTG-32 promotion — 2026-09-20

Package `j-bryant.ftg-32`, revision `amazon-b0fzgy19t9-ftg-32-2026-09`,
uses one `primary` model presentation. Descriptor model bounds in metres are
`[-0.052499998, -0.0385, -0.0185]` → `[0.052499998, 0.0385, 0.0185]`.
The pivot is `modelBoundsCenter` in `hang-ten-board-v1`.

| Position | Hold IDs | Exact quaternion `[x,y,z,w]` | Physical meaning |
| --- | --- | --- | --- |
| `edge-25-down` | `edge-25` | `[0,0,0,1]` | Baseline with the deep ledge below the shared front recess |
| `edge-16-down` | `edge-16` | `[0,0,1,0]` | Exact face-plane half-turn with the shallow ledge below the same recess |

Evidence: the retained exact-ASIN gallery attachments 1–4 and 2026-09-20
human topology confirmation recorded in
[`2026-09-20-j-bryant-ftg-32-3d.md`](2026-09-20-j-bryant-ftg-32-3d.md).
Geometry author and deliberate visual reviewer: Astra, Task 2, 2026-09-20.
The sourced envelope and 16/25 mm depths remain product facts; the exact
face-plane half-turn preserves the human-confirmed one-sided presentation.
Every unpublished shape, pose translation, camera, attachment, and cord value
is an **authored display estimate** (`displayEstimate`), with the full numeric
ledger pinned in that audit. The elevated canonical camera is a display choice.

The suspension rotations match these orientation quaternions exactly. One
physical loop passes through two centered holes and around the rear; the
runtime represents its two exterior leads from one shared invisible anchor.
The rear connecting segment is deliberately omitted. No suspension mesh is
included in the three-node USDZ. Orientation keys are stored in canonical
position-ID order; the user-visible position sequence remains 25 mm then 16 mm.

## Batch 05 Zlagboard fixed-front migration (2026-09-20)

Author: Astra, after explicit user evidence approval on 2026-09-20.
[Evidence, mapping and native verification](2026-09-20-hangboards-batch-05-migration/native/README.md)
retain E1/E2/E3 and E1/P2/P3 authority and distinguish estimates from facts.

| Package | Model bounds in metres (min → max) | Position / hold IDs | Pivot / quaternion | Review |
| --- | --- | --- | --- | --- |
| `zlagboard.evo` | (-0.350, -0.060, 0) → (0.350, 0.060, 0.042) | Existing primary; all 21 stable hold IDs, exact mapping retained | Fixed front; no orientation override or authored pivot/quaternion | Empty-scene native USDZ import, materials/bindings/bounds checked; front/oblique preparation renders reviewed; current-source iOS acceptance pending |
| `zlagboard.pro` | (-0.3525, -0.076, 0) → (0.3525, 0.076, 0.042) | Existing primary; all 28 stable hold IDs, Pro 2.0 exact mapping retained | Fixed front; no orientation override or authored pivot/quaternion | Empty-scene native USDZ import, materials/bindings/bounds checked; front/oblique preparation renders reviewed; current-source iOS acceptance pending |

Bounds and orthographic front camera are an authored display estimate, not
published board measurements. +Y is up and +Z faces the athlete; the source GLB
root transform was baked exactly once in native preparation. No suspension is
documented in the approved source set; both exclusions have explicit user approval.

## Frictitious native migration, 2026-09-20

Author: Astra. Approved evidence D1/D2/D3/D4 (lower Pro 7 only), M1/M2/M3 (side profile). Model bounds are mesh-derived; cavity profile/curvature is an authored display estimate.

| Package | model bounds (metres) | position and hold IDs | pivot / quaternion | evidence and review |
| --- | --- | --- | --- | --- |
| `frictitious.doormount-pro-7` | [-0.323850006, -0.057150006, -6e-09] → [0.323850006, 0.05715001, 0.057150006] | Existing primary, all 13 stable/reconciled hold IDs; explicit mapping retained | Fixed front; no orientation override or authored pivot/quaternion | Exact USDZ empty-scene reimport; front/oblique/ledge review retained. Current-source iOS acceptance pending. |
| `frictitious.megalith` | [-0.339724988, -0.082550004, -9e-09] → [0.339724988, 0.082550012, 0.057150003] | Existing primary, all 20 stable/reconciled hold IDs; explicit mapping retained | Fixed front; no orientation override or authored pivot/quaternion | Exact USDZ empty-scene reimport; front/oblique/ledge review retained. Current-source iOS acceptance pending. |

| `trango.rock-prodigy-forge` | Fixed front, split adjustable spacing | F1/F2/F4/F5/F6/F7 approved 2026-09-20; no canonical alternate pose established. |
| `trango.rock-prodigy-natural` | Fixed front, removable cleat mount | N1/N2/N3/N4/N5 approved 2026-09-20; removal/sliding is not a training rotation. |

## Tension Grindstone Mk2 CAD migration (2026-09-26)

`tension.grindstone` became a model package when it gained a native FreeCAD
source (see
`docs/source-audits/2026-09-26-tension-grindstone-cad-provenance.md`). It is a
wall-mounted board with a single fixed front face, so it keeps one
loader-materialized `primary` position with no orientation block and no
suspension.

| package ID | holds | descriptor model bounds (`min` → `max`) | pivot | evidence basis |
| --- | ---: | --- | --- | --- |
| `tension.grindstone` | 14: `top-jug`, `edge-50-center`, `edge-10-left/right`, `edge-8-left/right`, `edge-30-left/right`, `edge-25-left/right`, `edge-20-left/right`, `edge-15-left/right` | `[-0.279399991, 0.0, -0.0]` → `[0.279399991, 0.152400002, 0.069849998]` | none (no orientation block) | Tension Grindstone product page (`https://tensionclimbing.com/products/grindstone`) and its front product image `Grindstone1.png`; the in-use photos show a wall-mounted board with no selectable second face |
