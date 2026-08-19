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
candidate represented. Official images support visible boundaries, but not
unlabeled capacity, posture, or measurement facts.

## Current authoring interpretation

- Evo: reconcile its official holds image with the stated crimp, pocket, sloper,
  and jug families, then directly author every visible contact.
- Pro: identify the exact current Pro version before authoring. The app page
  proves Pro 1.0 and Pro 2.0 are distinct, so never mix their imagery or facts.

Omit unsupported measurements, capacity, and posture. Validate and visually
review each complete flat package against the exact model-specific images.
