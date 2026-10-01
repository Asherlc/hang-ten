# NUG shorter visual cord

At the user's request, the visible per-lead display estimate changes from **300 mm to 110 mm**, with the support offset reduced from **100 mm to 50 mm**. Fresh native routes and hanging heights place the support **54.185507 mm above the posed board's top**, compared with **262.422559 mm** before, for every one of the six poses. Cord diameter remains **6 mm**.

- [Default/inverted front, side and top overview](default-inverted-cord-overview.png)
- [Full default front comparison](front-25-front-full.png)
- [All 36 full/detail comparisons](index.html)
- [Route, source and image provenance](render-provenance.json)
- [Visual inspection](inspection-report.json) and [overview provenance](overview-provenance.json)
- [Compact before snapshot](before/snapshot-provenance.json)
- [Accepted pinch geometry review](../pinch-contact-review/README.md)

Before is the genuine committed package at `b3b5fe2b588c74bcb3ddd2d7b43478308f5a5ffb`, with model `1dc1b6c1198a71e62477dc1bbf7b6404d19324d06d438b5a4c60958636bf017f` and sidecar `4f2971de05766f9d20f6eb8dde0cd311d03d5c0c6845b586725af0d689aa1ef3`. After uses the accepted seamed pinch model `9b24f881059a7d79afd3b676da6324b3d0d65fb0977e2eab100b88bfa5a5e800` and promoted shorter-cord sidecar `d34a007dacf5d8718c67e68a605d3496097e26e87539aa804d4903cee3255472`.

The source remains `03ae5ecea7a1836b7c3aa695d1bd9618c0f5e36af3d05bba1cc62bebf45e7208`; the descriptor remains `c6ecc298e414726f5b543de89d7e22ee6d6180ff56dd71777f71a95624db3a9e`. The accepted pinch geometry, published130×60×40mm dimensions, logical contacts, native attachment graph, mouth endpoints, six pose rotations/cameras, and6mm radius-derived diameter are unchanged. Cord lengths/support placement are user-requested display estimates, not new manufacturer measurements.

The renderer independently imports both actual USDZs. It transforms exact cached native routes and reconstructs the fixed support using the repository suspension convention; capped cylinders follow the repository's per-segment `makeCordEntity` construction, with technical24-sided tessellation. No hand-authored routes or joint spheres are introduced. Each before/after pair uses the same camera and body scale, with body-centered comparison framing. The native z-buffer handles occlusion. Final labels reuse the exact rendered candidate pixels after its sidecar hash was confirmed identical to the promoted file.

The durable snapshot retains only four genuine committed baseline files, the accepted pinch capture-time8a3f sidecar, and13specific prior app PNG/AX/validation files. Other accepted pinch proofs remain in the linked sibling packet. No accepted history was overwritten. The capture-time sidecar is historical, not the current shortened setup.

All36paired-image hashes, the overview hash,18retained-before files, and current source/model/descriptor/sidecar hashes were checked. Representative default, inverted, reverse, jug and pinch views were physically inspected. Tight cylinder joints can show small fan-like gaps in enlarged side projections; the routes remain exact and unedited. These are technical previews, not new Simulator screenshots or native clearance certificates. Root owns those proofs. **Human acceptance of this shorter cord remains pending.**
