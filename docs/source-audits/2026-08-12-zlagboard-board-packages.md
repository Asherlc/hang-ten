# Zlagboard Evo and Pro package-source audit

Checked 2026-08-12. This historical audit preserves the official Zlagboard
sources reviewed for Evo and Pro. The old incomplete package art was removed
and is not an input to future work. Future geometry is directly authored from
model-specific primary evidence under `docs/ADDING_A_BOARD.md`.

## Official source sets

| candidate | official product material | official front imagery | official hold documentation |
| --- | --- | --- | --- |
| `zlagboard-evo` (`zlagboard.evo`) | [Zlagboard hangboards](https://www.zlagboard.com/hangboards) identifies the Evo as a compact board with crimps, pockets, slopers, and jugs. | [Evo holds image](https://www.zlagboard.com/assets/web/zlagboard-evo-holds-014x2x-00d8566361fdbbb0740896a8a7805e652d20e09b2fbe54eb2d36b4b7ecb66d10.png) on the official hangboards page. | No manufacturer numbered hold guide, dimensioned hold drawing, or manual assigning values to every contact region was published. |
| `zlagboard-pro` (`zlagboard.pro`) | [Zlagboard hangboards](https://www.zlagboard.com/hangboards) identifies the Pro as a board with varied ergonomic hold shapes and sizes. The [official app page](https://www.zlagboard.com/app) identifies Pro 1.0 and Pro 2.0 as distinct compatible products. | [Pro product image](https://www.zlagboard.com/assets/web/Zlagboard-2019-smaller2x-8011f7e115f3707e78d58c5b3587d3a15fd82b009c421a6c6dbc9f560e50dc1b.png) on the official hangboards page. | No manufacturer numbered hold guide, dimensioned hold drawing, or model-version-specific manual assigning values to every contact region was published. |

The official pages are sufficient to distinguish the product families and to
show their visible layouts. They did not resolve which Pro version the old
candidate represented, nor did they publish a complete physical-hold inventory.
An image does not establish hold capacity, grip classification, boundaries,
cue treatment, or semantic target.

## Evidence-key readiness

A registered package needs exact mappings for every board field, all physical
hold fields and frames, each semantic target, and each presentation asset. The
source sets below only support broad board-level claims and
visible imagery; they cannot supply the required per-hold key set.

| candidate | official facts established | missing required evidence | result |
| --- | --- | --- | --- |
| `zlagboard.evo` | Product identity; compact form factor; aggregate grip categories of crimps, pockets, slopers, and jugs; official front image. | Exhaustive named contact inventory; each contact's boundary/frame, size/depth, finger capacity, grip classification, and cue/feature fields; source-backed semantic targets. | Old incomplete package removed; direct authoring required. |
| `zlagboard.pro` | Product-family identity; general ergonomic-hold description; official front image; evidence that Pro 1.0 and Pro 2.0 are distinct app-compatible boards. | Exact model version of the candidate; exhaustive named contact inventory; each contact's boundary/frame, size/depth, finger capacity, grip classification, and cue/feature fields; source-backed semantic targets. | Old incomplete package removed; direct authoring required. |

## Exact blockers

### `zlagboard-evo`

Zlagboard describes the Evo's aggregate categories but supplies no
model-specific, exhaustive mapping of its physical contact regions. The
official product image is evidence for visible presentation only and cannot
turn those categories into complete per-hold records. No source establishes
the full hold-frame, capacity, classification, or semantic evidence
required by a canonical package.

### `zlagboard-pro`

Zlagboard describes the Pro generally, while its official app page separately
lists Pro 1.0 and Pro 2.0. The existing candidate directory does not identify
which version it represents. More importantly, neither source publishes an
exhaustive individual-hold map or the necessary per-hold measurements and
classifications. No package can be authored without both model identification
and an official complete hold map.

## Required follow-up

Obtain a manufacturer-issued, model-specific numbered hold diagram or data
sheet for Evo and for the exact Pro version. It must map every physical contact
region and its boundary to its measurements, finger capacity, grip
classification, and documented training target. Then directly author and
visually review a complete flat package. Do not use a broad product description
or evidence from one Pro version for another.
