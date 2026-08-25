# Rock Prodigy Training Center source-evidence audit

Originally checked 2026-08-10; re-audited 2026-08-13 and directly authored
2026-08-19. The former incomplete package and art were removed and were not
used as authoring inputs. The replacement paths were drawn directly under
`docs/ADDING_A_BOARD.md`.

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

## Completed authoring interpretation

### `trango-rock-prodigy-training-center`

The former 26-hold model mixed third-party depth claims with pre-migration data;
none of its data or paths were restored. The current front view resolves 12
logical contacts per symmetric half: four guide-corroborated contact surfaces
(warm-up jug, sloper, large open-hand edge, and wide pinch), two variable rails,
one lower outer edge, one lower inner pocket, one upper outer compound pocket,
one upper inner pocket, one bottom outer compound pocket, and one bottom inner
pocket. Each compound pocket is a single physical contact with two visibly
disconnected lobes, giving 24 logical holds and 28 geometry pieces.

The guide's deep two-finger, shallow three-finger, and small semi-closed-crimp
terms describe selected training positions, but it does not provide a
one-to-one location/depth map for every visible cavity. The package therefore
keeps its stable historical IDs as identity only and omits depth, capacity,
posture, and feature metadata from every individual cavity. The IDs' legacy
finger-pair words are not treated as evidence. “More than 30 grip positions”
describes variable locations and grip combinations on the continuous rails and
pockets; it is not a count of separately selectable physical contacts.

The product page establishes `12.1 × 9.1 in` per side and says the design is
perfectly symmetric. The official square JPEG was converted to PNG without
cropping, registration, or geometric alteration. The left-side paths were
authored directly from that image and the right side was mirrored exactly.
Only the visibly regular inner pockets use operator-selected oval constraints;
the sculpted rails, compound pockets, and contact surfaces remain freeform.
All six constrained pieces pass the production `+1 px` resize invariants. A
zero-distance save can reserialize decimal precision, so they are verified for
oval consistency and no visible snap rather than claimed as byte-exact.

## 2026-08-25 per-contact metadata ledger

The stable-ID capture at
`.context/hangboard-metadata-backfill-icky-cow/trango/trango.rock-prodigy-training-center--54f0d57dd133.png`
was reviewed against the current first-party product image and both pages of
the use guide. The 24 logical contacts / 28 geometry pieces still reconcile;
no geometry or identity changed.

All 24 `kind` values are source-verified. Only four unique source-to-contact
optional mappings remain populated on each mirrored side:

- `sloper-*` uses the exact `sloper` posture;
- `jug-*` uses the literal `jug` feature;
- `edge-large-vder-*` maps “Large Open-Hand Edge” plus the product page's
  variable-edge-rail wording to `openHand` and `largeOpenHandRail`;
- `pinch-wide-*` uses the literal `widePinch` feature.

The use guide has no positional hold diagram. Consequently its generic “Deep
2 Finger Pocket” and “Shallow 3 Finger Pocket” exercises cannot be assigned to
any of the five physical pocket contacts on a half. All ten pocket
`fingerCapacity`, `gripType`, and `features` values were removed and recorded
as unavailable. The same evidence gap leaves `thinCrimp` and `mediumPinch`
features blank: Trango says “small semi-closed crimp” and “wide pinch,” not
that those schema tags apply to the corresponding stable IDs. Trango publishes
no per-contact depths or maximum simultaneous hand capacities, so all such
fields remain blank with exact reasons in
`2026-08-25-hangboard-metadata-ledger.json`.
