# YY Vertical Board Evo, First, Light, and One source audit

Checked 2026-08-12. This document records the first-party material reviewed
for these four generated-image candidates. It is an audit record, not runtime
content or package state. Each candidate remains unregistered with only its
existing `assets/primary.png`; that generated presentation image was not used
to establish hold facts.

## Official source sets

| slug | catalog ID | official product and dimensions | official front/oblique material | official hold documentation |
| --- | --- | --- | --- | --- |
| `yy-verticalboard-evo` | `yy.verticalboard-evo` | [VerticalBoard Evo product page](https://www.yyvertical.com/en/products/verticalboard-evo) — 65 × 14 × 5.5 cm; 19 grips; named size/category summary | [Evo product gallery](https://www.yyvertical.com/en/products/verticalboard-evo) | The product page’s technical-details and feature sections only; no separate numbered hold guide, manual, or dimensioned hold drawing was published. |
| `yy-verticalboard-first` | `yy.verticalboard-first` | [VerticalBoard First product page](https://www.yyvertical.com/en/products/verticalboard-first) — 54 × 13 × 5 cm; named size/category summary | [First product gallery](https://www.yyvertical.com/en/products/verticalboard-first) | The product page’s technical-details and feature sections only; no separate numbered hold guide, manual, or dimensioned hold drawing was published. |
| `yy-verticalboard-light` | `yy.verticalboard-light` | [VerticalBoard Light product page](https://www.yyvertical.com/en/products/verticalboard-light) — 54 × 9 × 5 cm; named size/category summary | [Light product gallery](https://www.yyvertical.com/en/products/verticalboard-light) | The product page’s technical-details and feature sections only; no separate numbered hold guide, manual, or dimensioned hold drawing was published. |
| `yy-verticalboard-one` | `yy.verticalboard-one` | [VerticalBoard One product page](https://www.yyvertical.com/en/products/verticalboard-one) — 62 × 13 × 5.5 cm; named size/category summary | [One product gallery](https://www.yyvertical.com/en/products/verticalboard-one) | The product page’s technical-details and feature sections only; no separate numbered hold guide, manual, or dimensioned hold drawing was published. |

The [YY Vertical comparison page](https://www.yyvertical.com/en/collections/poutres-escalade)
is also first-party, but it is not a per-model hold diagram. It cannot turn a
category list or gallery image into an exhaustive physical-hold inventory.

## Source-backed facts and evidence-key readiness

A registered package needs exact evidence maps for every board field, every
physical-hold field and frame, semantic target, and retained asset. The product
pages support the model-level facts in the table below, but they do not identify
individual contact regions. Consequently the required per-hold and semantic
evidence-key sets are all unknown rather than
empty; no package sidecars may be authored from these sources.

| candidate | source-backed product facts | published grip summary | required evidence-key coverage available | readiness |
| --- | --- | --- | --- | --- |
| Evo | identity, material, overall dimensions/weight, magnetic inserts, central handle | 19 grips; 25/20/18 mm edges with inserts; two jugs; 43°/38°/30° slopers; mono-, two-finger, and inclined grips | board-level subset and `assets/primary.png` only; no `holds.*` or `semantics.*` key set can be mapped | blocked |
| First | identity, material, overall dimensions/weight, central notch, insert compatibility | 45/33/25/22/20 mm edges; 35°/20° slopers; two jugs | board-level subset and `assets/primary.png` only; no `holds.*` or `semantics.*` key set can be mapped | blocked |
| Light | identity, material, overall dimensions/weight, central notch, insert compatibility | 20/25/45 mm edges; 40 mm central hold; 30°/20° slopers; two jugs | board-level subset and `assets/primary.png` only; no `holds.*` or `semantics.*` key set can be mapped | blocked |
| One | identity, material, overall dimensions/weight, magnetic inserts, central handle | 18/25/30/35/45 mm edges; 20°/35° slopers; 30/50 mm vertical two-finger holds; broad jugs | board-level subset and `assets/primary.png` only; no `holds.*` or `semantics.*` key set can be mapped | blocked |

## Exact blockers

### `yy-verticalboard-evo`

YY Vertical identifies the Evo’s aggregate count and grip categories, but
does not publish a labeled, exhaustive map of the 19 physical contacts. In
particular, no source assigns each contact a boundary, grip type, finger
capacity, depth/size, cue, feature set, semantic target, or normalized frame.
Product-gallery images are not evidence for those non-visible fields. Keep the
candidate primary-only and unregistered until YY Vertical publishes a
model-specific numbered hold diagram or equivalent data sheet.

### `yy-verticalboard-first`

YY Vertical publishes the First’s overall dimensions and a category/size
summary, but not an exhaustive individual-hold inventory or labeled physical
boundaries. The page does not establish the required per-contact capacity,
grip classification, cue, feature, semantic target, or normalized frame.
Keep the candidate primary-only and unregistered until an official,
model-specific hold diagram or data sheet supplies those facts.

### `yy-verticalboard-light`

YY Vertical publishes the Light’s overall dimensions and grip categories, but
not an exhaustive, labeled inventory of its physical contact regions. The
product images and category list cannot establish the full per-hold records,
semantic targets, or normalized hold frames required by the package
schema. Keep the candidate primary-only and unregistered until an official,
model-specific hold diagram or data sheet supplies them.

### `yy-verticalboard-one`

YY Vertical publishes the One’s dimensions and summarized edge, sloper,
two-finger, jug, and handle categories, but no exhaustive individual-contact
map. It therefore does not establish each hold boundary or every required
per-hold field, semantic target, and normalized frame. Keep the candidate
primary-only and unregistered until YY Vertical publishes a model-specific
numbered hold diagram or equivalent data sheet.

## Required follow-up

For each model, obtain a manufacturer-issued, model-specific source that maps
every physical contact region and boundary to its measurements, finger
capacity, grip classification, and documented training target. Then author all
three canonical sidecars and add exactly that ready model to `catalog.json` in
one change. Do not use another YY Vertical model, the generated primary image,
or visual similarity as a substitute.
