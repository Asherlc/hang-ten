# 3-D board orientation evidence packet

Reviewed 2026-09-11 at commit `6e24dece` (Task 6, Step 3 evidence-only
preparation). This document does not change a board package, USDZ, descriptor,
hold inventory, contact grouping, rotation, or quaternion. It is the cheap
evidence packet for the four model packages currently discovered by the live
catalog. The final Nature and YY Vertical Baguette Evo position partitions and
quaternion judgment remain **pending Astra**.

## Decision and review gate

The web evidence supports proceeding to a human/Astra orientation review for
all four packages. Beastmaker 1000 and Metolius Compact II have a complete
manufacturer front plus a materially different commerce-gap oblique view in
the prior retained packet. Nature Stone Hanger and Baguette Evo have multiple
materially distinct views in their current manufacturer galleries (front,
oblique/profile/reverse-use views). This establishes a review set, not a claim
that every hidden surface or machining dimension is known.

The current checkout does not retain the ignored source-image bytes referenced
by the earlier `.context/shaky-rat-*` packet ledgers; those paths, hashes and
page links are reproduced below so a reviewer can recover the exact approved
set. No search thumbnail, generated render, legacy raster asset, or board
asset is used as a second physical view. A human must approve the exact
multi-angle set before Astra authors orientation metadata. If the approved
source bytes cannot be recovered, stop at that gate rather than infer a view.

The following decisions are deliberately out of scope here:

* no authored `orientation` object or quaternion;
* no final `front`/`reverse`/Turn & Pull contact grouping for Nature or
  Baguette;
* no rotation of a USDZ, descriptor, board asset, or presentation camera;
* no new physical contacts inferred from product-use photographs.

## Live inventory and baseline

Discovery at execution time finds exactly these four complete model packages.
Each currently has one `primary` model presentation, no explicit authored
positions, and no orientation or suspension metadata. The loader therefore
materializes the legacy effective position `primary`, containing the board's
ordered hold IDs. `boardBounds` is explicitly `null` in every checked-in
descriptor; the normalized hold face-plane AABB union below is a descriptor
diagnostic, not a physical board bound.

| package ID | package / presentation | current effective position | holds | model SHA-256 | descriptor SHA-256 |
| --- | --- | --- | ---: | --- | --- |
| `beastmaker-1000` | `Hangboards/beastmaker-1000`, `primary` | `primary` (legacy, all holds) | 22 | `19fb5895575792fb69e82aa3c8a04fa14a6bd40a8a97f486bc16be014e546f3d` | `ee095c463804312cbd6ed08f5113019793b934ab6806a6fb343be939ff8a68d3` |
| `metolius.wood-grips-compact-ii` | `Hangboards/metolius-wood-grips-compact-ii`, `primary` | `primary` (legacy, all holds) | 19 | `addf2cd2ddd34f18f311ccc1413ca94644df0d2f3d56020b68edf25625bc664a` | `a652b1a184ec15432126502514d11db2b02768df7c3c0a892c62031f381c0c7f` |
| `nature.stone-hanger` | `Hangboards/nature-stone-hanger`, `primary` | `primary` (legacy, all holds) | 8 | `366e6833403d8877b62b2403ce98683e4c27f9ce76c1d9e9abaa24e50ba382e4` | `eb2a83c035d1a80e172f196c68210b4b0556a897f367ebd3ddcd27b196237fa8` |
| `yy.baguette-evo` | `Hangboards/yy-baguette-evo`, `primary` | `primary` (legacy, all holds) | 19 | `e006aad2dfac8e5a3911d1e3e0944830056856d45d757fc76c360e339c76f91b` | `e73f56e2f9ae903583896f88067f03f9f3d9bb1065b8febddd825fcd98b4532c` |

The hashes are exact bytes at this review point. They are a baseline for the
future Astra orientation pass; changing a USDZ or descriptor invalidates the
corresponding baseline and requires a fresh audit.

## Coordinate and bounds convention

The four descriptors use schema version 1 normalized image-plane values:
`center = [x, y]`, `facePlaneAABB.min/max = [x, y]`. The table records the
union of all hold face-plane AABBs in descriptor order, with no rounding beyond
the stored nine-decimal values. These values are suitable for checking that a
future position partition references the complete descriptor inventory; they
do not establish body thickness, recess depth, or a rotation.

| package | `boardBounds` | descriptor hold-AABB union (`min` → `max`) | source/model bound context |
| --- | --- | --- | --- |
| Beastmaker 1000 | `null` | `[0.026206898, 0.054666682]` → `[0.973793173, 1.000000000]` | Manufacturer face is 580 × 150 mm; prior model packet qualifies a 58 mm shared-layout depth view, but the current Tulip page also says `5 mm`; neither publishes complete body sections. |
| Metolius Compact II | `null` | `[0.000000000, 0.042771465]` → `[1.000000000, 1.000000000]` | Manufacturer Compact is 610 × 157 mm (24 × 6.2 in); the 56 mm labels are sloper callouts, not body thickness. Existing model depth is an authored display estimate. |
| Nature Stone Hanger | `null` | `[0.092380923, 0.128571409]` → `[0.907619077, 0.858095244]` | Retained integration evidence gives combined model bounds X/Z ±0.0525 m and Y ±0.0175 m; manufacturer publishes 105 × 105 × 35 mm. Fine sections, cord routing and port depth remain unknown. |
| Baguette Evo | `null` | `[0.076923064, 0.000000000]` → `[0.923076936, 1.000000000]` | Retained README gives a 520 × 50 × 50 mm round envelope and origin at its center; machining profiles, bore dimensions and small-edge offsets are estimates. |

## Ordered hold IDs and current descriptor positions

The following is the exact current `board.json` order. It is the order the
legacy loader puts in the effective `primary` position today. A future
multi-position model must preserve each position's relative order and form an
exact, non-overlapping partition of these IDs.

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

Current effective position: `primary` → all IDs below. Current model
orientation: none. Physical candidates are the two usable faces identified in
the retained source packet: `front` and `reverse`, with upper/lower contact
halves changing with inversion. The exact partition of these eight IDs into
those positions is intentionally not authored here.

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
one logical ID, not two contacts. The final multi-position authored grouping
is intentionally pending Astra.

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
orientation candidates, not the final ID partition.

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
active in each physical face. Final multi-position grouping, position names,
and canonical quaternions are explicitly **pending Astra**.

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
| Nature Stone Hanger | [manufacturer product page](https://natureclimbing.com/products/stone-hanger-1); gallery artifacts `GRANITE1_2_1024x.png`, `GRANITE1_1024x.png`, `GRANITE2_2_800x.png`, `GRANITE2_1024x.png` linked from that page | exact selected product family, oak/granite, 105 × 105 × 35 mm, 20/15/10/6 mm families, multiple front/oblique/reverse-use views; retained technical drawing and mapping establish eight named contacts | complete cord route, hidden bore/sleeve, exact contact sections, final front/reverse partition or quaternion |
| Baguette Evo | [manufacturer English product page](https://www.yyvertical.com/en-eu/products/baguette-evo); [manufacturer product page](https://www.yyvertical.com/en/products/baguette-evo); gallery artifacts `YY_BAGUETTE_EVO_02_FG.webp`, `YY_BAGUETTE_EVO_07_FG.webp`, `YY_BAGUETTE_EVO_03_FG.webp`, and the use image `yy-vertical-escalade-agres-nomade-entrainement-nomadic-tool-gear-equipment-training-baguette-evo-utilisation-22.webp` linked from the page | exact round Evo identity, 520 × 50 × 50 mm, named paired/central depths, rounded option, Turn & Pull and multiple product/use views | exact milling profiles, fillets, bore dimensions, hidden cord route, final face grouping or quaternion |

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
they are not an Astra-approved app position partition.

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
or a reversible/continuously adjustable tool. That is enough to prepare an
Astra review candidate, but not enough for this cheap worker to choose final
groupings or quaternions. Their final grouping and quaternion judgment remain
**pending Astra**.

## Astra handoff checklist

Before any metadata promotion, Astra/human review must:

1. approve exact retained source snapshots and their hashes for each package;
2. verify the declared board coordinate frame against the actual USDZ;
3. author a complete ordered position partition for Nature and Baguette with
   no guessed or duplicated hold IDs;
4. choose canonical quaternions about `modelBoundsCenter` only after visual
   review of front/reverse/inclined poses;
5. rerun descriptor/package validation and refresh the four model/descriptor
   baseline hashes if any model bytes change.

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

Discovery now finds fourteen complete model packages: the four above plus
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

### Tension Flash Board — `three-edge` / `two-edge`

Grouping is source-backed: the batch-01 research ruling confirms five cavity
zones retaining their existing IDs and declares the two legacy small-crimp
IDs unresolved and unbound (no selectable geometry fabricated for them), so
the positions partition the 5-contact inventory exactly once (3+2).

Descriptor model bounds: `[-0.241300002, 0.0, 0.0]` →
`[0.241300002, 0.076200001, 0.076200001]`. Pivot: `modelBoundsCenter`.

| position | hold IDs (canonical board order) | quaternion | basis |
| --- | --- | --- | --- |
| `three-edge` | `three-edge-left`, `three-edge-center`, `three-edge-right` | `[0, 0, 0, 1]` | identity = delivered base pose; source-backed three-edge broad face |
| `two-edge` | `two-edge-left`, `two-edge-right` | `[1, 0, 0, 0]` | authored display estimate: 180° about X exposes the opposing two-edge broad face (batch-01 ruling: face registration approximately 180°, an authored estimate) |

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

### Verification (this pass)

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
