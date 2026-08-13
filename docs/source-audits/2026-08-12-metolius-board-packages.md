# Metolius board-package evidence audit

Checked 2026-08-12. This audit covers the four generated-image candidates in
`Hangboards/`. The candidate raster is not manufacturer evidence for a package:
it remains a presentation-only `assets/primary.png` until a complete package can
be authored. No candidate below is registered in `catalog.json`.

The package schema requires a source for every physical hold field, including
`gripType`, `fingerCapacity`, `cueStyle`, and `features`. The Metolius material
below identifies the visible hold groups and many depth/finger-count facts, but
does not state those fields for its jugs, slopers, pinches, and/or edges. A
picture cannot fill that gap. In particular, the Wood Grips Compact II diagram
and manual are model-specific and were not used for any conclusion here.

| Candidate | Dedicated official sources reviewed | What the documents establish | Exact source-backed package blocker | Result |
| --- | --- | --- | --- | --- |
| `metolius-climbers-edge` | [Climbers Edge product page](https://www.metoliusclimbing.com/products/climbers-edge-board); [shared training-board manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826) | Product identity and published overall size; the marketing list names six edge depths, a round sloper, a flat sloper, and jugs. | No Climbers Edge numbered hold guide, depth/layout diagram, or product-specific training guide is published. The product page does not map the six depths to individual physical hold boundaries or state required grip/finger/cue/feature fields. The shared manual has no model hold map. | Keep `assets/primary.png` only; unregistered. |
| `metolius-contact` | [Contact product page](https://www.metoliusclimbing.com/products/contact-training-board); [Contact numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170); [Contact training guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Product size, symmetric numbered layout, variable pinches, jugs, 63 mm round slopers, 53 mm flat sloper, 11 pocket families with stated size/finger counts, and four named central-edge depths. | The diagram and guide do not state `gripType`, `fingerCapacity`, `cueStyle`, or allowed `features` for each physical pinch, jug, sloper, or edge. They also do not map the product's "variable" pinch widths into required physical-hold field values. Supplying those values would be inference. | Keep `assets/primary.png` only; unregistered. |
| `metolius-project` | [Project product page](https://www.metoliusclimbing.com/products/project-training-board); [Project numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/project-depth.jpg?v=1762201307) | Product size, symmetric numbered layout, jugs, 55 mm flat slopers, 53 mm round sloper, six numbered pocket families with stated depth/finger counts, and three numbered edge depths. | The diagram does not state the schema-required `gripType`, `fingerCapacity`, `cueStyle`, and `features` for every jug, sloper, and edge; the product page's generic training-guide link is not a Project hold map or semantic mapping. | Keep `assets/primary.png` only; unregistered. |
| `metolius-simulator-3d` | [Metolius 2010 catalog](https://www.metoliusclimbing.com/pdf/Metolius_2010.pdf); [Simulator 3D numbered depth diagram](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/sim-num-dep.jpg?v=1759460619); [Simulator 3D training guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | The catalog gives the 28 in × 8.75 in board dimensions; the diagram gives the symmetric numbered layout and stated depth/finger-count pocket and edge groups; the guide names routine targets. | The official material does not state the required `gripType`, `fingerCapacity`, `cueStyle`, and `features` for each jug, sloper, and edge. It also does not supply a source for converting numbered picture regions into the schema's individual physical-hold boundary frames beyond reviewed artwork normalization. | Keep `assets/primary.png` only; unregistered. |

To move any of these candidates into the runtime catalog, Metolius must publish
model-specific material that maps every physical hold and explicitly supports
the missing required fields, or the package schema must be redesigned to make
those fields genuinely optional with a separate approved evidence contract.
