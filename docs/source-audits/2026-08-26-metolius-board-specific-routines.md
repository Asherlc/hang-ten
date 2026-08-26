# Metolius Contact and Simulator 3D routine source audit

Checked 2026-08-26 against Metolius' primary guides: [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide) and [Simulator 3D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide).

Both pages define the ten-minute sequence as the listed task or tasks in each
minute, with **the remaining time used to rest until the next minute**. Each
import therefore has ten 60-second source cycles, no app-created work/rest
split, and `.official` provenance. Contact and Simulator 3D use numbered board
holds, so each plan is board-specific (`metolius.contact` or
`metolius.simulator-3d`) and is not available for another board.

The stable-ID mappings below are the existing source-audited manufacturer-label
map in [the Metolius board-package audit](2026-08-12-metolius-board-packages.md#contact-reviewed-label-map).
`L/R` denotes the mirrored stable-ID pair. The guide's parenthetical numbers
are retained verbatim in the task transcription; where a guide phrase names a
number whose companion adjective conflicts with the catalog's manufacturer
diagram (for example Contact `deep four finger (3)`), the literal number—not a
semantic substitute—selects the catalog target. This records the manufacturer
guide's internal wording conflict without silently rewriting it.

## Contact

Board classification: `metolius.contact` (package slug `metolius-contact`); numbered targets are resolved only
against the Contact package. Target key: `1` pinch L/R; `2` outer jug L/R;
`3` round sloper L/R; `4`–`14` matching `pocket-<n>-left/right`; `15`
`flat-sloper-center`; `16`–`19` matching `edge-<n>-center`.

| Minute | Entry source task(s) → catalog target | Intermediate source task(s) → catalog target | Advanced source task(s) → catalog target |
| --- | --- | --- | --- |
| 1 | 1 pull-up outer jugs (2); 10 s hang center edge (17) → `jug-left/right`; `edge-17-center` | 3 pull-ups outer jugs (2); 20 s dead hang deep three finger pockets (6) → `jug-left/right`; `pocket-6-left/right` | 6 pull-ups round slopers (2); 20 s dead hang deep two finger pockets (4) → `jug-left/right`; `pocket-4-left/right` |
| 2 | 1 pull-up deep four finger edge (4), **stay on**; 10 s bent-arm hang (90°), **stay on**; 1 more pull-up → `pocket-4-left/right` | 10 s bent-arm (elbows at 90°) hang round sloper (2), **stay on**; 2 pull-ups, **stay on**; 10 s bent-arm hang (elbows at 110°) → `jug-left/right` | 15 s bent-arm hang (elbows at 90°) round sloper (2), **stay on**; 4 pull-ups, **stay on**; 15 s bent-arm hang (elbows at 110°) → `jug-left/right` |
| 3 | 2 offset pull-ups (1 arm each) outer jug (2) & deep three finger pockets (6) → `jug-left/right`; `pocket-6-left/right` | 4 offset pull-ups (each arm) outer jugs (2) & deep three finger pockets (6) → `jug-left/right`; `pocket-6-left/right` | 6 offset pull-ups (3 each arm) round sloper (2) & deep two finger pockets (4); 10 s dead hang medium edge (18) → `jug-left/right`; `pocket-4-left/right`; `edge-18-center` |
| 4 | 6 s L-hang on any holds (bend knees if needed); 5 s dead hang pinches (11) → `pocket-11-left/right` | 10 s L-hang on any holds; 10 s dead hang on pinches (11) → `pocket-11-left/right` | 15 s L-hang any holds (**hold good form**); 15 s dead hang on pinches (11) → `pocket-11-left/right` |
| 5 | 10 s dead hang flat sloper (15); 5 knee raises outer jug (2) → `flat-sloper-center`; `jug-left/right` | 10 s offset hang deep center edge (17) & med three finger edge (8), **reverse holds — repeat** → `edge-17-center`; `pocket-8-left/right` | 10 s dead hang extra shallow three finger pockets (13), **stay on**; campus to med three finger pocket (9); campus to round slopers (2); hold 15 s → `pocket-13-left/right`; `pocket-9-left/right`; `jug-left/right` |
| 6 | 16 s offset hang (8 s per side) deep edge (17) & med pocket (7) → `edge-17-center`; `pocket-7-left/right` | 15 s offset hang pockets (4) & (13), **reverse holds — repeat** → `pocket-4-left/right`; `pocket-13-left/right` | 15 s one-arm hang center edge (17); rest 20 s; **repeat other arm** → `edge-17-center` |
| 7 | 3 pull-ups any hold → no numbered target in source | 4 pull-ups deep center edge (17); 10 knee raises any holds → `edge-17-center` | 5 L-sit pull-ups (bend knees if you have to), jugs (1); 20 s bent-arm hang (elbows at 90°), deep two finger pockets (4) → `pinch-left/right`; `pocket-4-left/right` |
| 8 | 10 s bent-arm hang (elbows 90°) deep four finger (3) → `round-sloper-3-left/right` | 15 s dead hang two finger pockets (7); rest 10 s; 10 s hang three finger pockets (9) → `pocket-7-left/right`; `pocket-9-left/right` | 10 s hang center edges (16, 17), **reverse holds — repeat**; 3 power pull-ups (**use weights or helper for resistance; should just be able to complete final rep**) → `edge-16-center`; `edge-17-center` |
| 9 | 1 offset pull-up, jug & pinch (1 & 11), change hands & repeat; 10 s dead hang deep four finger pockets (3) → `pinch-left/right`; `pocket-11-left/right`; `round-sloper-3-left/right` | 10 s one-arm hang jugs (3), **repeat other arm**; 4 pull-ups center edge (17) → `round-sloper-3-left/right`; `edge-17-center` | 20 s slight bent-arm hang two finger pockets (7), **stay on**; bump to round slopers (3); 20 s dead hang → `pocket-7-left/right`; `round-sloper-3-left/right` |
| 10 | 2 pull-ups any hold; dead hang center edge (17) **till failure**; “Fight hard & don't let go!!” → `edge-17-center` | 4 pull-ups flat sloper (15); bump out to round sloper (3) & dead hang **to failure**; “Fight hard!!” → `flat-sloper-center`; `round-sloper-3-left/right` | 8 pull-ups flat sloper (3); bump out to round sloper (3); dead hang **to failure**; “Fight hard!!” → `round-sloper-3-left/right` |

Published totals retained for audit: Entry 12 pull-ups and 1:17 hang time plus
final hang; Intermediate 25 pull-ups and 2:35 plus final hang; Advanced 32
pull-ups and 3:35 plus final hang.

## Simulator 3D

Board classification: `metolius.simulator-3d` (package slug `metolius-simulator-3d`); numbered targets are resolved
only against the Simulator 3D package. Target key: `1` jug L/R; `2` and `3`
share `round-sloper-3-left/right`; `4` pocket L/R; `5`–`7` edge L/R; `8`–`10`
pocket L/R; `11` edge L/R; `12`–`13` pocket L/R; `14` center jug; `15`–`18`
center pockets.

| Minute | Entry source task(s) → catalog target | Intermediate source task(s) → catalog target | Advanced source task(s) → catalog target |
| --- | --- | --- | --- |
| 1 | 10 s dead hang deep flat edge (7) → `edge-7-left/right` | 25 s dead hang medium edge (5) → `edge-5-left/right` | 25 s dead hang shallow edge (6); 5 pull-ups three finger pockets (9) → `edge-6-left/right`; `pocket-9-left/right` |
| 2 | 15 s dead hang + one pull-up outer jugs (1) → `jug-1-left/right` | 20 s dead hang flat slopers (2); 3 pull-ups flat slopers → `round-sloper-3-left/right` | 5 offset pull-ups pockets (15 & 12), **reverse holds repeat** → `pocket-15-center`; `pocket-12-left/right` |
| 3 | 2 offset pull-ups (1 each arm) center jug (14) & deep three finger pockets (4) → `jug-14-center`; `pocket-4-left/right` | 15 s bent-arm hang shallow edge (6); 10 knee raises jugs (1) → `edge-6-left/right`; `jug-1-left/right` | 45 s dead hang extra shallow edges (11) → `edge-11-left/right` |
| 4 | 15 s dead hang extra deep 3 finger pockets (9) → `pocket-9-left/right` | 15 s dead hang flat slope (2); 15 s dead hang round slopers (3) → `round-sloper-3-left/right` | 5 offset pull-ups round sloper (3) & deep pocket (4), **reverse holds repeat** → `round-sloper-3-left/right`; `pocket-4-left/right` |
| 5 | 12 s dead hang flat slopers (2); 5 knee raises outer jugs (1) → `round-sloper-3-left/right`; `jug-1-left/right` | 20 s offset hang jug (1) & shallow pocket (17), **reverse holds — repeat** → `jug-1-left/right`; `pocket-17-center` | 10 s dead hang x-shallow edges (11), **staying on**; campus to three finger pockets (9); campus to shallow edges (6); campus to flat slopers (2); hold 15 s → `edge-11-left/right`; `pocket-9-left/right`; `edge-6-left/right`; `round-sloper-3-left/right` |
| 6 | 16 s offset hang (8 s per side) deep pocket (15) & shallow edge (5) → `pocket-15-center`; `edge-5-left/right` | 15 s offset hang pockets (4 & 9), **reverse holds and repeat** → `pocket-4-left/right`; `pocket-9-left/right` | 15 s one-arm hang round sloper (3); rest 10 s; **repeat other arm** → `round-sloper-3-left/right` |
| 7 | 3 pull-ups outer jugs (1) → `jug-1-left/right` | 4 pull-ups medium edges; 10 knee raises any holds → `edge-5-left/right` | 5 L-sit pull-ups (bend knees if you have to), jugs (1); 20 s bent-arm hang (elbows @ 90), deep two finger pockets (12) → `jug-1-left/right`; `pocket-12-left/right` |
| 8 | 8 s bent-arm hang (elbows @ 90), round slopers (3) → `round-sloper-3-left/right` | 30 s dead hang deep pockets (7) → `edge-7-left/right` | 20 s slightly bent-arm hang shallow 3 finger pocket (8), **stay on**; bump to x-deep three finger pockets; 25 s dead hang → `pocket-8-left/right` |
| 9 | 1 pull-up & then 10 s hang ext-deep 3 finger pocket (9) → `pocket-9-left/right` | 10 s one-arm hang jugs (1), **repeat other arm** → `jug-1-left/right` | 10 s hang center pockets (18 & 17), **reverse holds repeat**; three power pull-ups (**use weights or helper for resistance, should just be able to complete third pull**) → `pocket-18-center`; `pocket-17-center` |
| 10 | Dead hang **to failure**, any holds → no numbered target in source | 5 pull-ups deep edges (7), **without dropping off**, bump up to round slopers (3) & dead hang **till failure** → `edge-7-left/right`; `round-sloper-3-left/right` | 8 fast pull-ups jugs (1) (**keeping form perfect**); dead hang round sloper **to failure** (“fighting hard!”) → `jug-1-left/right`; `round-sloper-3-left/right` |

Published totals retained for audit: Entry 7 pull-ups and 1:26 hang time plus
final dead hang (including the source's feet-on-chair resistance qualification);
Intermediate 12 pull-ups, 20 knee raises, and 3:30 plus final dead hang;
Advanced 33 pull-ups and 3:38 plus final dead hang.
