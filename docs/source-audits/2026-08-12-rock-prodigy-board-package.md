# Rock Prodigy Training Center source-evidence audit

Originally checked 2026-08-10; re-audited 2026-08-13 against the direct-source
package contract. The board is not registered or bundled. Its directory is an
unregistered image candidate containing only `assets/primary.png`.

## Direct manufacturer sources

- Product page: <https://trango.com/products/rock-prodigy-training-center>
- Use instructions: <https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155>
- Main product image: <https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750&width=1946>

The product page supports the product identity, two-piece construction,
symmetry, variable edge rails, and per-piece dimensions. The product image
supports visible silhouette and contact placement. The official use guide
names seven broad training grips: warm-up jug, large open-hand edge, deep
two-finger pocket, small semi-closed crimp, shallow three-finger pocket, wide
pinch, and sloper.

## Registration blocker

### `trango-rock-prodigy-training-center`

The former 26-hold runtime model included exact rail ranges, pocket depths,
pinch sizes, normalized frames, finger capacities, and logical contacts. Those
details were mapped to a depth guide hosted by a third-party retailer and to
pre-migration Swift data. Neither source satisfies the requirement that every
factual hold field map to direct official manufacturer evidence.

The official sources above do not exhaustively establish the detailed 26-hold
model. Therefore its three package sidecars and board-specific runtime plan were
removed. No reduced or inferred package was substituted. Registration can be
reconsidered only when Trango publishes a direct exhaustive hold guide that
supports every required field, normalized hold frame, semantic target, and
asset.

There is no package `review/` directory, approximate outline, README, or
separate presentation declaration. The retained `assets/primary.png` is an
unregistered catalog image and is not staged into the app.
