# Unilateral portable training source audit

Reviewed 2026-08-28.

## Frictitious Port-A-Board

Primary source: [Frictitious Climbing — The Port-A-Board](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard).

Primary image evidence from the same product page:

- [front](https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840)
- [back](https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840)
- [side](https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840)

| Package field | Source mapping |
| --- | --- |
| `id`, manufacturer, name, product URL | Product title and publisher. |
| one `primary` equipment object | The listing's box contents says `Port-A-Board` singular; this is one board even though it has multiple usable edges. |
| dimensions | Product spec: 5 × 5.5 × 1.8 in (128 × 140 × 48 mm). |
| eight hold IDs and `sizeMillimeters` | Product spec lists exactly: 30, 30 (2 finger and mono), 25, 20, 15, 12, 10, and 8 mm. |
| all hold kinds `edge` | The same spec calls the inventory eight unique edges. No finger capacity, hand capacity, posture, or depth is asserted because the listing does not establish it. |
| `edge-20.features = [mediumEdge]` | App semantic adaptation: the factual 20 mm size is the exact source range's lower bound (20–24 mm), allowing the board-flexible Megos plan to resolve its documented edge. It does not change product metadata. |
| presentations and every path | Deliberately hand-authored, simplified `Primary` (front) and `Back` presentations after direct visual review of the official front/back/side images. Each of the eight documented contacts has a separately authored closed pill path and manually selected `pill` editing constraint. The source photos were evidence only; no source raster, registration, segmentation, tracing, vectorization, contour extraction, or generated geometry was used. |

The product page also says the board can attach to weights, a foot, or the Foot Plate. That establishes supported setup modes only; it does **not** establish a sets/repetitions/rest routine, so this package adds no Port-A-Board training prescription.

## Megos one-arm 7:3 repeaters

Source: [Alex Megos' Finger Training Power-Endurance Protocol](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/) by Eric Hörst, reviewed 2026-08-28. The article reports Megos's protocol as four 7-second / 3-second cycles per arm, then the other arm, followed by two minutes of rest, for six total sets; it describes the working edge as approximately 20–24 mm and separately calls out a half-crimp position.

`research.megos-one-arm-7-3` is marked `adapted`: the source sequence is unchanged, but the app expands each documented work/rest cycle into a discrete timer step so laterality can be recorded.

| App field | Source mapping |
| --- | --- |
| six set loops | "six total sets" |
| left four reps, then right four reps | four cycles per arm; switch to the other arm after completing one arm |
| `activeDuration = 7`, 3-second recovery after every rep | 7 seconds hang, 3 seconds rest, repeated four times |
| 3-second recovery before the side switch | The fourth 7/3 cycle retains its documented 3-second rest before the other arm begins. |
| 120-second recovery after the right arm's fourth 3-second recovery in sets 1–5 | two-minute rest before the next set; no additional post-session recovery is represented after set six |
| `handUse = single`, `side = left/right`, `action = hang` | one-arm hangs and explicit side order |
| target `.mediumEdge`, half-crimp | approximately 20–24 mm edge and the source's half-crimp guidance |

## Omitted incomplete protocols

The [Climbing one-arm lifting-edge article](https://www.climbing.com/skills/crimp-strength-training-safely/) supplies the 20 mm / 70–80% 1RM / three sets of seven lifts / 2–3 days-per-week facts, but does not supply all runner-visible inter-set timing needed for an exact timer routine. It is not imported.

The [Tyler Nelson recruitment-pull interview](https://www.trainingbeta.com/media/tyler-nelson-fingers/) supplies 3–5 reps of 3–5-second isometrics and 60–120-second recovery ranges. Those ranges are not turned into invented exact steps or a built-in routine.
