# Repaired-board metadata certification

Reviewed 2026-08-25. This source-audited metadata pass certifies only the three
boards whose physical inventories were separately repaired and reviewed: Moon
Armstrong, Escape Beta Board, and Frictitious Megalith. It changes no geometry,
presentation assets, product identity, or unrelated package.

## Review evidence

| Board | Primary manufacturer evidence | Stable-ID review capture |
| --- | --- | --- |
| `moon.armstrong` | [Moon Armstrong product page](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html), [official front](https://moonclimbing.com/media/catalog/product/cache/8fbd88411911f97522c3f864e19b1b09/6/0/60-112-bec_moon_armstrong_fingerboard_bec_01.jpg), and [official oblique view](https://moonclimbing.com/media/catalog/product/cache/8fbd88411911f97522c3f864e19b1b09/6/0/60-112-bec_moon_armstrong_fingerboard_bec_02.jpg) | `.context/hangboard-metadata-backfill-icky-cow/moon-armstrong-geometry-repair/capture-final/moon.armstrong--45a10ab74773.png` (21 contacts) |
| `escape-beta-22` | [Beta Board product page](https://escapeclimbing.com/products/ec72100), [official numbered breakdown](https://escapeclimbing.com/cdn/shop/products/2020_Website_Editorials_EscapeClimbing_Breakdown.png?v=1700454580&width=1445), and [official front](https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_01-02.jpg?v=1700454580&width=1445) | `.context/hangboard-metadata-backfill-icky-cow/escape-beta-geometry-repair/visible-id-capture/escape-beta-22--245680ffb240.png` (22 contacts) |
| `frictitious.megalith` | [Megalith product page](https://frictitiousclimbing.com/products/megalith), [official engraved front](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front.jpg?v=1780436232&width=3840), and [alternate official front](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front-1.jpg?v=1780436232&width=3840) | `.context/hangboard-metadata-backfill-icky-cow/frictitious-megalith-reconciliation/frictitious.megalith--3f1c176e6ccc.png` (18 contacts) |

The captures are mapping and review aids only. No measurement, capacity, kind,
posture, feature, or path was inferred from their pixels.

## Exact source-to-ID mappings

| Board and stable IDs | Source-backed package values |
| --- | --- |
| `moon.armstrong`: `sloper-{left,right}`; `center-edge-{22,18}` | Mandatory `sloper`/`edge` kinds and the two center scalar depths. The source's 35-degree value remains an angle, not a depth. These exact terms have no supported feature tag. |
| `moon.armstrong`: `jug-{left,right}`; `center-jug` | Mandatory `jug` kinds and exact `features: [jug]`. |
| `moon.armstrong`: paired `edge-{25,20,15,10,8}-{left,right}` | Mandatory `edge` kinds, exact scalar depths, and exact `features: [slot]` from Moon's “slots” inventory term. |
| `moon.armstrong`: `two-finger-pocket-{left,right}` | `kind: pocket`, `sizeMillimeters: 22`, `fingerCapacity: 2`, `gripType: twoFingerPocket`, and `features: [pocket]`. |
| `moon.armstrong`: `mono-{left,right}` | `kind: pocket`, `sizeMillimeters: 22`, `fingerCapacity: 1`, and `features: [pocket]`; the schema has no one-finger-pocket grip enum. |
| `escape-beta-22`: paired positions `hold-01` through `hold-11` | All 22 mandatory kinds and the numbered 38/29/12/50/31 mm scalar depths. `sloper` is the documented closed-taxonomy adaptation of Escape's exact “Sloper Edge” term. |
| `escape-beta-22`: `hold-02-{left,right}`; `hold-03/04-{left,right}`; `hold-05-{left,right}`; `hold-06/07/08-{left,right}` | Exact `widePinch`, `jug`, `incutEdge`, and `flatEdge` feature arrays respectively. “Thin Pinch” and “Sloper Edge” have no exact supported feature tag. |
| `frictitious.megalith`: `top-jug`; `center-edge-25`; `mono-{left,right}` | Exact `jug`, `incutEdge`, and `pocket` feature arrays respectively; `center-edge-25` also has source-stated `handCapacity: 1`; the monos retain `fingerCapacity: 1`. |
| `frictitious.megalith`: paired `edge-{8,10,12,15,20,30}-{left,right}` and `edge-40-pocket-{left,right}` | Mandatory `edge` kinds and separate scalar shelf depths. The integrated two-finger pocket is a subregion of each 40 mm edge, so it does not create a fixed capacity, pocket grip enum, or pocket feature for the whole record. |

## Deliberate blanks

- `depthRangeMillimeters` remains absent from all 61 contacts. The repaired
  inventories map separate fixed-depth contacts; scalar values are not copied
  into manufactured ranges.
- Pocket finger capacity is not applicable to the source-identified non-pocket
  contacts. Moon's four pockets and Megalith's two monos are the only exact
  per-contact finger capacities in this batch.
- `handCapacity` remains absent except for Megalith's explicitly single-hand
  25 mm center contact. One-arm exercise wording, shoulder width, full width,
  or paired placement does not otherwise establish a contact's maximum.
- `gripType` remains absent except for Moon's exact two-finger pockets. The
  manufacturers do not prescribe a supported exact posture for the other
  contacts, and the schema has no one-finger-pocket enum.
- Feature arrays remain absent unless an exact manufacturer term maps to a
  supported tag. Moon's jugs, slots, and pockets receive their exact tags;
  Moon's slopers and center edges remain blank because those source terms have
  no supported feature enum. Kinds are not automatically duplicated into
  features.

## Ledger outcome

| Board | Holds | Verified/populated | Unavailable | Not applicable | Unaccounted |
| --- | ---: | ---: | ---: | ---: | ---: |
| `moon.armstrong` | 21 | 60 | 70 | 17 | 0 |
| `escape-beta-22` | 22 | 54 | 78 | 22 | 0 |
| `frictitious.megalith` | 18 | 40 | 70 | 16 | 0 |
| **Total** | **61** | **154** | **218** | **55** | **0** |

All 427 required seven-field outcomes are explicit in the machine-readable
ledger. This certification preserves the prior operator geometry rulings and
does not reopen or reinterpret the repaired physical inventories.
