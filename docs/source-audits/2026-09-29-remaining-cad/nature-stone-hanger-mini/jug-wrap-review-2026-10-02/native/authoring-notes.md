# Mini upper-jug crown correction — scratch candidate

Owner: `placid-badger`. Canonical package remains untouched by this worker.

The user requested that the jug wrap all the way around. The prior correction selects the outside top flat and upper-back round only. Native geometry inspection identifies the missing upper-front roll as FinalSolid Face30. The complete rounded crown consists of Faces28/29/30/41/42/43/59/65/69. These are actual existing outer faces; no body solid, hidden geometry, contact overlay or duplicate faces were created.

The shared jug binder now contains Faces30/43/69 with primary contact `pull-up-jug` and additional contact `pinch-60`. The existing pinch-only binder keeps Faces23/31/44. A new jug-only native SubShapeBinder, `nature_jug_ends`, contains Faces28/29/41/42/59/65. Those six faces are the continuous top end rounds, bounded by their native z=22 mm tangent edges. Recessed cord-groove walls remain body; front frame18, rear panel70, recessed wall6, lower frame and lower corners are excluded. No arbitrary vertical band or native face split was added.

Shared crown area is 2339.7344572538564 mm². Jug-only end area is 614.6956123014903 mm². Total jug area is 2954.4300695553466 mm². Logical pinch remains the exact original six-face union23/30/31/43/44/69, area4679.468914507713 mm² and native Z span60 mm. Existing wood/granite15 mm contacts are identical. The embedded manifest, four factual contacts, canonical contact order and all three position memberships are byte-identical. The authored default wood finish applies to the new node; only nature_stone is a granite exception.

Evidence: retained whole exact-revision Nature Climbing photographs NS-2/NS-3 in `docs/source-audits/2026-09-29-remaining-cad/nature-stone-hanger-mini/sources.json` show the outer rounded upper shoulders. The prior human identification establishes that the smooth jug is this outside rail. The exact contact highlight extent is a deliberate display interpretation of those surfaces and the new user request, not a manufacturer grip-depth measurement. No pixel measurements, source registration, tracing, masks, vectors or crops were used.

Source URLs:
- https://natureclimbing.com/products/stone-hanger-mini-oak
- https://natureclimbing.com/cdn/shop/files/Oakminihanger1.jpg?v=1774539696
- https://natureclimbing.com/cdn/shop/files/Oakminihanger2.jpg?v=1774539697

Pinned FreeCAD1.1.3 / OCCT7.8.1 / OpenUSD26.8. `run-owned.py` records ownership before process creation, installs interrupt handling and a finally cleanup trap, terminates the exact owned process group when needed, removes each exact owned config/cache/tmp directory and verifies absence. No simulator or server was created. Actual app appearance remains unverified. Root owns candidate review/promotion, sidecar hash integration and cord revalidation.
