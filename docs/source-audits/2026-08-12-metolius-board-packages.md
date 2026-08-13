# Metolius board-package evidence audit

Checked 2026-08-12. This audit covers the four generated-image candidates in
`Hangboards/`. The candidate raster is not manufacturer evidence for a package:
it remains a presentation-only `assets/primary.png` until a complete package can
be authored. No candidate below is registered in `catalog.json`.

The package schema requires a source for every physical hold field, including
`gripType`, `fingerCapacity`, `cueStyle`, and `features`. The Metolius material
below labels visible hold groups and, where stated, depth and pocket-finger
counts. It does not, however, establish an evidence map for every individual
physical cavity and every required app field. A picture supports reviewed
artwork normalization, but cannot supply unsupported `cueStyle` or `features`.
In particular, the Wood Grips Compact II diagram and manual are model-specific
and were not used for any conclusion here.

| Candidate | Dedicated official sources reviewed | What the documents establish | Exact source-backed package blocker | Result |
| --- | --- | --- | --- | --- |
| `metolius-climbers-edge` | [Climbers Edge product page](https://www.metoliusclimbing.com/products/climbers-edge-board); [shared training-board manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826) | Product identity and published overall size; the marketing list names six edge depths, a round sloper, a flat sloper, and jugs. | No Climbers Edge numbered hold guide, depth/layout diagram, or product-specific training guide is published. The product page does not map the six depths to individual physical hold boundaries or state required grip/finger/cue/feature fields. The shared manual has no model hold map. | Keep `assets/primary.png` only; unregistered. |
| `metolius-contact` | [Contact product page](https://www.metoliusclimbing.com/products/contact-training-board); [Contact numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170); [Contact training guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Product size, symmetric numbered layout, labeled variable pinches, outer jugs, round and flat slopers, 11 labeled pocket families with stated size/finger counts, and four labeled central-edge depths. | The sources label hold groups, but do not publish a canonical one-to-one record for every physical cavity with the package's required field coverage. In particular, no source supports the app-specific `cueStyle`/`features` values, and the product calls the pinches "variable" without values that can be assigned to individual physical pinch holds. Supplying those fields would be inference. | Keep `assets/primary.png` only; unregistered. |
| `metolius-project` | [Project product page](https://www.metoliusclimbing.com/products/project-training-board); [Project numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/project-depth.jpg?v=1762201307) | Product size, symmetric numbered layout, labeled outer jugs, 55 mm flat slopers, 53 mm round sloper, six numbered pocket families with stated depth/finger counts, and three numbered edge depths. | The diagram labels repeated hold groups but does not establish package evidence for every individual physical cavity and required field. It does not support the app-specific `cueStyle`/`features` values for jugs, slopers, pockets, or edges; the product page's generic training-guide link is not a Project semantic map. | Keep `assets/primary.png` only; unregistered. |
| `metolius-simulator-3d` | [Metolius 2010 catalog](https://www.metoliusclimbing.com/pdf/Metolius_2010.pdf); [Simulator 3D numbered depth diagram](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/sim-num-dep.jpg?v=1759460619); [Simulator 3D training guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | The catalog gives the 28 in × 8.75 in board dimensions; the diagram labels the symmetric hold groups and stated depth/finger-count pocket and edge groups; the guide names routine targets. | The numbered diagram and guide identify groups, not a canonical physical-hold record with every package field. They do not support the app-specific `cueStyle`/`features` values for the labeled jugs, slopers, pockets, and edges. Reviewed artwork normalization can trace visible boundaries to the diagram, but cannot manufacture the missing semantic field evidence. | Keep `assets/primary.png` only; unregistered. |

To move any of these candidates into the runtime catalog, Metolius must publish
model-specific material that maps every physical hold and explicitly supports
the missing required fields, or the package schema must be redesigned to make
those fields genuinely optional with a separate approved evidence contract.
