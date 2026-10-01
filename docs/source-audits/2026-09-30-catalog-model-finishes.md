# Catalog model finish assignments — 2026-09-30

All 55 model presentations now opt into the shared material palette. This is
an app display choice: wood uses the existing procedural wood finish, molded
plastic/resin uses mint, and granite uses the granite finish. These choices do
not assert manufacturer colorways or exact polymer chemistry. Raster packages
retain their authored image appearance; runtime model finishes do not recolor PNGs.

## Changes and evidence

The existing package identity, subtitle/contact inventory, descriptor and linked
manufacturer evidence govern each grouping. No geometry, contacts, cords, camera
poses or model bytes change. The two separately sourced Transgression revisions
both use plastic; their polyester/polyurethane distinction remains in their
identities and source audit. Their previous neutral choices are superseded.

| Package | Finish | Evidence and mapping |
| --- | --- | --- |
| `captain-fingerfood-dual` | `wood` | [Package product source](https://en.captainfingerfood.rocks/products/dual-hangboard); All body/contact meshes |
| `captain-fingerfood-unlevel` | `wood` | [Package product source](https://en.captainfingerfood.rocks/products/unlevel-hangboard); All body/contact meshes |
| `mammut-diamond-finger` | `plastic` | [Package product source](https://www.mammut.com/us/en/products/2060-00020/diamond-finger-hangboard); All body/contact meshes |
| `metolius-contact` | `plastic` | [Package product source](https://www.metoliusclimbing.com/products/contact-training-board); All body/contact meshes |
| `metolius-simulator-3d` | `plastic` | [Package product source](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board); All body/contact meshes |
| `nature-stone-hanger` | `wood` | [Package product source](https://natureclimbing.com/products/stone-hanger-1); Oak body/wood contacts; `edge_front_20mm_granite_mesh_001` overrides to granite, bound to `edge-front-20mm-granite` |
| `owl-climb-poker` | `wood` | [Package product source](https://owlclimb.com/index.php/en/prds-2/poker/); All body/contact meshes |
| `surfaces-for-climbing-transgression-2011` | `plastic` | [Package product source](https://en-eva-lopez.blogspot.com/2012/04/transgression-fingerboard-for-high.html); All body/contact meshes; retained revision evidence in `2026-09-29-transgression-cad/sources.json` |
| `surfaces-for-climbing-transgression-2013` | `plastic` | [Package product source](https://en-eva-lopez.blogspot.com/2012/04/transgression-fingerboard-for-high.html); All body/contact meshes; retained revision evidence in `2026-09-29-transgression-cad/sources.json` |
| `tension-flash-board` | `wood` | [Package product source](https://tensionclimbing.com/products/flash-board-2); All body/contact meshes |
| `tension-grindstone-original` | `wood` | [Package product source](https://www.tensionclimbing.com/hangboards/new-board); All body/contact meshes |
| `tension-honestone` | `wood` | [Package product source](https://tensionclimbing.com/products/honestone); All body/contact meshes |
| `tension-whetstone` | `wood` | [Package product source](https://tensionclimbing.com/products/whetstone); All body/contact meshes |
| `trango-rock-prodigy-forge` | `plastic` | [Package product source](https://trango.com/products/rock-prodigy-forge); All body/contact meshes |
| `yy-baguette-evo` | `wood` | [Package product source](https://www.yyvertical.com/en/products/baguette-evo); All body/contact meshes |
| `yy-penta-evo` | `wood` | [Package product source](https://www.yyvertical.com/en/products/penta-evo); All body/contact meshes |
| `yy-verticalboard-evo` | `wood` | [Package product source](https://www.yyvertical.com/en/products/verticalboard-evo); All body/contact meshes |
| `zlagboard-evo` | `wood` | [Package product source](https://www.zlagboard.com/hangboards); All body/contact meshes |
| `zlagboard-pro` | `wood` | [Package product source](https://www.zlagboard.com/hangboards); All body/contact meshes |

Captain Fingerfood uses the wooden product shown in its manufacturer product
presentation; no wood species is asserted. YY Penta Evo explicitly lists poplar
plywood. Nature Stone Hanger explicitly lists oak and granite; its existing
descriptor identifies the granite contact, so no new mesh split is inferred.
Mammut retains the catalog manufactured-surface grouping; its current product
page does not establish exact chemistry. Original Grindstone uses its retained
archival wooden revision evidence rather than asserting a current product.

CAD sources are updated with `set_board_manifest.py`, which changes only embedded
manifest metadata and verifies all non-Document.xml archive members unchanged.
Non-CAD sources are edited directly while preserving authored number lexemes,
including nine-decimal instance translations. Every changed package asset hash
was checked unchanged.

The catalog finish coverage test now loads every model package through the real
package consumer and rejects omitted/neutral board finishes. Legacy neutral
decoding remains supported for external fixtures and attachments.

## Validation

- Expanded catalog finish coverage failed before the metadata edits and passed afterward.
- Full package suite: 461 passed (`python3 -m pytest Tools/HangboardPackages/tests -q`).
- Final-inventory validation and catalog status passed.
- Android staging passed; all 19 changed packages retained their assigned finish.
- All 55 model presentations have a material assignment: 17 plastic, 38 wood;
  mixed wood/granite boards use explicit granite node overrides.
- iOS Debug simulator builds passed on iPhone 17 Pro / iOS 26.5 and iOS 26.3.
  The command was `CI=true xcodebuild -project HangTen.xcodeproj -scheme HangTen
  -configuration Debug -destination 'platform=iOS Simulator,id=<owned UUID>'
  -derivedDataPath .context/DerivedData build`.
- iOS staged metadata was checked for all 19 changed packages before cleanup.
- Visual validation remains incomplete: both installed apps timed out at the
  first simulator launch (40 seconds on iOS 26.5, 60 seconds on iOS 26.3).
  No runtime screenshots or visual success are claimed. Contact and Stone
  Hanger review used identical local USDZ copies in the existing DEBUG simulator
  model directory to avoid relying on simulator ODR delivery.
- Both cleanup traps ran. Owned UUIDs `188BF3A5-EB8E-4127-98C4-F0DF2AC3D80F`
  and `7143E06F-290B-4D8B-8634-C67C39EF4492` were deleted; workspace DerivedData
  was removed. Cleanup was independently verified with the simulator inventory.

## Updated native source hashes

These metadata-only source hashes supersede earlier provenance hashes. All archive
members except Document.xml were compared with the committed LFS objects and
remain byte-identical. Full board documents also compare equal after restoring
the prior display metadata.

| Package | FCStd SHA-256 |
| --- | --- |
| `surfaces-for-climbing-transgression-2011` | `a5042032b5e7b01306608fdc6690ce097ed2bd4bc34bbc84a3313596524b7f67` |
| `surfaces-for-climbing-transgression-2013` | `00990671ccb446a3d6b6293df6cfcc5ca4d63fc98238a49b51d5ebe771ca578d` |
| `tension-grindstone-original` | `f67e4056da41ed3076ff7688a0d3bba4e02e6e880ef2d8cf34c0cecd965ee95f` |
| `tension-honestone` | `9b647d84fc3258c3cf3657c1f045519ac0906669f0d17803c9d14c35d7da2c1e` |
| `tension-whetstone` | `42834773e456df1f97a9e8cac75cbab3313556aa13f14d0f0370cc381ad1ac48` |
| `yy-verticalboard-evo` | `40416fa721ae1f9b89ace5bd20273136ed2678b284f4e51f3bfe12d68dfb18ca` |
