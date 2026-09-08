# Tension Flash Board dynamic-cord package audit

Reviewed 2026-09-08. This audit covers the existing `tension.flash-board` package's approved presentation and geometry refit; it does not establish a new product revision.

## Manufacturer evidence

Primary product page: <https://tensionclimbing.com/products/flash-board-2>

Official Tension Climbing images:

- <https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard1.png?v=1726542491> (`aa00ab77e04c685acc4dee0e0704d25fd3165810387649a4e924bf3f7bfff148`)
- <https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard2.png?v=1726542491> (`ae84f7d58def1c2f4e3b14c2e98ddf8e332b7f48e6c774312744b792d4ab97b4`)
- <https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard3.png?v=1726542491> (`5753461d938adb19655556e8070f7361a0f9a1697752a861bacde4d240f0f63d`)
- <https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard4.png?v=1726542491> (`7c078225890ae6d6975bff865e706e8858e7a56c3edc8df572637241ca6df200`)

The product page establishes the Tension Climbing Flash Board identity and globally lists 8, 10, 15, and 20 mm edges. The official images establish two usable faces, the 3 + 2 + 2 physical-contact inventory, internal stepped surfaces, and paired cord threading through four holes. They do not map any listed depth to an individual modeled contact, so no per-hold scalar size or depth label is assigned. Unsupported dimensions, capacities, postures, and feature claims remain omitted.

## Package mapping and authorship

The package retains the existing identity, metadata, primary equipment object, and seven stable hold IDs. An operator directly authored and reviewed all hold paths and source-specific cord ports. Each physical face owns one canonical routed rig with the existing shared renderer; each inverted position aliases its canonical raster and rotates board-space geometry 180 degrees around `{x: 0.5, y: 0.7}` while the world apex remains fixed. The four presentations therefore use two canonical RGBA rasters:

- `assets/primary.png`, 2172 × 724: `2911e2ff6ccf1add0ab6519e8a99fa2287747d751eb79b5c4a5aa1c335d1fa59`
- `assets/two-edge-surface.png`, 2172 × 724: `674e6cbc39201f0f80e887dcb7c4cbc391bc4e1081df58bc94e61b97f8c57f61`

These pale-wood, transparent-background presentation renders are user-approved catalog adaptations, not manufacturer photographs.

## Human review proofs

All four standalone Workbench runtime captures were approved by the user on 2026-09-08:

- `review-assets/2026-09-08-flash-board-three-edge-upright-approved.png`: `4df052b4e24a6c0224f9bd50565aa563e095a8b18c1bfcd809f3582465561986`
- `review-assets/2026-09-08-flash-board-three-edge-inverted-approved.png`: `92e61ce0a17bb21ae478bf7065d15de84f83e3b3f223a93b570ee9f09b7160dd`
- `review-assets/2026-09-08-flash-board-two-edge-upright-approved.png`: `77e06b137f8d48afdd6ab54d9f321dea0c8a5b0ef8ce1ea5858dfe512567b60e`
- `review-assets/2026-09-08-flash-board-two-edge-inverted-approved.png`: `a4f08bb639531535ca3a1d286d75f2d461644db856b1f644d390f3f2489bddd1`

The detailed three-edge and two-edge runtime review reports are preserved with the authoring record in `.context/joyful-donkey-cords-tension-flash-board-run-1/`. Promotion verification used exact equality with that reviewed fixture and the hashes above. Per the bounded promotion instruction, no new app or simulator run was performed; focused package validation and the Flash Board package test provide the publication checks.
