# Captain Fingerfood presentation-asset provenance

Reviewed 2026-08-29. This audit records the final presentation assets and
manually authored contact mappings for `captain-fingerfood.dual`,
`captain-fingerfood.unlevel`, and `captain-fingerfood.pocket`. It does not cover
POCKET+.

## Revision identity

- DUAL is the current 120 × 70 × 30 mm / 12 × 7 × 3 cm revision with one
  straight 20 mm lip opposite one single centrally curved 20 mm lip in the
  same cavity, plus the source-charted outer jug.
- UNLEVEL is the current 120 × 70 × 30 mm / 12 × 7 × 3 cm revision with curved
  20 mm and 25 mm faces plus the source-charted outer jug.
- `captain-fingerfood.pocket` remains the stable physical identity for the
  110 × 66 × 29 mm two-depth POCKET revision. Its current presentation is
  explicitly the blue **POCKET Hangboard | Lines Edition** cosmetic colorway.
  The Lines edition retains the same 15/20 mm physical inventory; it is not a
  second physical package. Its one continuous outer edge is one selectable
  contact, not separate pinch and jug holds.

The POCKET package therefore links to the current first-party Lines product
page, `https://en.captainfingerfood.rocks/products/lines-hangboard`, and labels
the cosmetic edition in its display name and subtitle. The previous generic
plain-POCKET naming is not used for the blue raster.

## First-party evidence

All downloaded evidence below is preserved under `.context` and its bytes were
hash-checked before the final package mapping.

### DUAL

Product page: `https://en.captainfingerfood.rocks/products/dual-hangboard`

| Evidence | First-party URL | SHA-256 | Mapping |
| --- | --- | --- | --- |
| Grip chart | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/DualGriffe.jpg?v=1739704755` | `abb3f6eaf74a8e519c1d5eca3120ea026748a42a9dd1d41e9299e5c4652ba37a` | Explicit straight-versus-unlevel 20 mm contact authority and explicit jug use on the top exterior band. |
| Title image | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/DualTitelbild.jpg?v=1739704755` | `f57fb751f63c5258e8cb85a9d0f0ad27f6b9cb5eede94b5e1caccc496ec9468e` | One-piece dark multiplex body, pale end grain, one opening and two cord holes. |
| Gallery P1 | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/DualP1.jpg?v=1739704755` | `b67f397ceefa3054f7d6ac038a8459fe8389753713ebb97274acc1a17a6de5c8` | Straight-face corroboration. |
| Gallery P2 | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/DualP2.jpg?v=1739704755` | `5b9f30b16919157e9017f51cebe979bd5aae99f69b4c48827c7b5fdb1145649b` | Confirms the same cavity has one straight long lip opposite one single centrally bowed lip; it does not have a double-lobed W. |

### UNLEVEL

Product page: `https://en.captainfingerfood.rocks/products/unlevel-hangboard`

| Evidence | First-party URL | SHA-256 | Mapping |
| --- | --- | --- | --- |
| Grip chart | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/UnlevelGriffe.jpg?v=1712754462` | `168c46c08f05d0aa13f9539068d58ae71825cf5fd0dbcb42ac2a736456867556` | Explicit 20/25 mm curved-face authority and explicit jug use on the top exterior band. |
| Title image | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/Titelbild.jpg?v=1739704654` | `7eb711b6b28284a86835b7a460559f5ec80f9816bc691e2823982d98e1b0d813` | Exact body construction and finish. |
| Gallery P1 | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/UnlevelP1.jpg?v=1739708294` | `ad5f5ace4d71475fb9b8f546d52bc63305868953898baf7aef67e966a571475f` | 20 mm face corroboration. |
| Gallery P2 | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/UnlevelP2.jpg?v=1712652284` | `75432a1c60bb6f2c735107551b52fff94fde6f2ae2f0a34a96b90c300ee416e9` | 25 mm face corroboration. |

### POCKET Lines Edition

Product page: `https://en.captainfingerfood.rocks/products/lines-hangboard`

| Evidence | First-party URL | SHA-256 | Mapping |
| --- | --- | --- | --- |
| Lines grip chart | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/LINESGriffe.jpg?v=1712657987` | `b61df73d39bc86828ac8713465d5841d7c93ba9fb978d9f9e6ddeb351b60a99e` | Exact Lines colorway and 15/20 mm two-depth inventory. |
| Lines title image | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/LinesTitelbild.jpg?v=1712656791` | `624ad076ba3ad96e69edbb0e3ab6f60dca44551e68fea143977cf791f5bd773a` | Exact cosmetic identity, compact one-opening/two-hole body and complete silhouette. |
| Lines gallery P1 | `https://cdn.shopify.com/s/files/1/0602/4547/5542/files/LinesP1.jpg?v=1712656801` | `6e4adb26e54fda3bb1ab06eec2d47176098e27f92ad1c0361dcb937173d77563` | The complete 29 mm body and its one continuous outer edge; current Lines copy supports one-arm pulling / fitting a hand, not two independently selectable outer contacts. |

The mixed 6/10/15/20 mm and 35 mm POCKET+ page separately names pinch and
jug uses. That is evidence for the different POCKET+ revision only. It cannot
be used to manufacture separate `pinch-body` and `jug-outer-rim` contacts on
the current 29 mm Lines board, whose own evidence supports one outer edge.

## Generation contracts and accepted bytes

The generated rasters are presentation assets, not physical evidence. Their
physical facts come only from the first-party sources above. The generic
contracts record the prompt template, literal per-run data, source roles and
the rule forbidding crop, resize, masks, segmentation, registration,
vectorization, cleanup and manual pixel edits.

| Record | SHA-256 | Relevant run data |
| --- | --- | --- |
| `.context/pretty-impala-corrected-visuals/contract.json` | `3bc7b6b1710b7adf928cfb68f78d666c2a9e7d8ed98eeb4370577cd42a478094` | Unchanged generic corrected-candidate prompt contract. |
| `.context/pretty-impala-corrected-visuals/run-data.json` | `5a0830080f5a5b1826a494de81134f23a0dc23cfd390e857c43877a438f8b560` | DUAL primary: closest lip strictly straight; DUAL reverse: closest lip visibly smooth and unlevel; both retain the one-opening/two-hole 120 × 70 × 30 mm body. |
| `.context/pretty-impala-captain-topology-fix/contract.json` | `f9bd07ba9b15820be53a2d455649aad879ff8eeb55651997777e86761fe06d7b` | Generic precise-object-edit contract; first-party images remain topology authority and the prior candidates remain style/framing authority. |
| `.context/pretty-impala-captain-topology-fix/run-data.json` | `0bcbdfe3e9ce59a43e09d002171c7918164a151dc7d0403cd3dbbcbdc4a50b41` | DUAL primary and reverse require exactly one straight lip opposite one single centered bow, never a W or repeated wave. |
| `.context/pretty-impala-generated-captain/contract.json` | `4b0bcb889b057575dfde06f331e5b83a5612909d9b4202bf1685594195a5474b` | UNLEVEL 20/25 face run data and exact source-key mapping. |
| `.context/pretty-impala-regenerated-gaps/contract.json` | `b536aed413c964da8a234f54f77001f1c44571da7a374f25d138b90ece952876` | Unchanged generic gap-candidate contract; the literal POCKET run describes the 110 × 66 × 29 mm one-opening/two-hole body and 15/20 face. |
| `.context/pretty-impala-official-asset-sources/official-asset-source-manifest.json` | `69dd53d132d1d0469e3cca6dedf605c01a48e356b05aaacea96b47ad64dcabaa` | Direct first-party URL, dimension, hash and view-confidence ledger. |

The earlier DUAL outputs under `.context/pretty-impala-corrected-visuals`
were superseded after the original-resolution topology audit: one flattened both
lips and the other rendered a double-lobed W. They are not production assets.
The two topology-fix outputs below are the only final DUAL bytes.

The POCKET candidate's historical folder and original decision described a
plain unnamed POCKET package. Independent reconsideration accepted the same
bytes once the package was explicitly identified as the current Lines Edition.
The folder name `rejected/` is therefore historical and does not describe the
final decision for the explicit Lines cosmetic identity.

| Package / presentation | Candidate copied unchanged | Pixels | SHA-256 |
| --- | --- | ---: | --- |
| DUAL `primary` | `.context/pretty-impala-captain-topology-fix/outputs/captain-fingerfood-dual-primary-attempt-1.png` | 1536 × 1024 | `5e411d8ba5cdb88c53afbca4bd79382457b1ddbbd62f03f4d786bdb4ee1f017e` |
| DUAL `reverse` | `.context/pretty-impala-captain-topology-fix/outputs/captain-fingerfood-dual-reverse-attempt-1.png` | 1536 × 1024 | `4006a43154becf5652a5f4f98d5a54f0bc43f538c3e8d552c41b240bbc05513d` |
| UNLEVEL `primary` | `.context/pretty-impala-generated-captain/outputs/captain-fingerfood-unlevel-primary.png` | 1536 × 1024 | `e6f72523d77b20ffd7cd4d9029636d9085f8b76c9936781055adf2156632b17f` |
| UNLEVEL `reverse` | `.context/pretty-impala-generated-captain/outputs/captain-fingerfood-unlevel-reverse.png` | 1536 × 1024 | `5a63511d31a4b991e8e309f2f35360781cbc61c0477d4714f9153af2e5d72cf3` |
| POCKET Lines `primary` | `.context/pretty-impala-regenerated-gaps/rejected/captain-fingerfood-pocket-primary-attempt-2.png` | 1536 × 1024 | `321abde36f5648af6d8aa86feb797de5a1b25d0d571d4f5a5a08855e83058b4b` |

Every final package raster is byte-for-byte identical to its accepted
candidate and declares the exact 3:2 aspect ratio. No final raster received
postprocessing of any kind.

## Final presentation and canonical-path mapping

Every canonical path was deliberately authored against the accepted raster
and the manufacturer evidence. No image-driven detection, segmentation,
masking, contour extraction, registration, vectorization, automated crop or
automatic path simplification was used.

| Package | Presentation | Canonical hold mapping |
| --- | --- | --- |
| `captain-fingerfood-dual` | `primary` | `straight-edge-20` follows the visible straight lower cavity lip; `outer-jug` follows only the narrow top exterior body band, excluding the cavity and edge lip. The opposing far lip has one centered bow. |
| `captain-fingerfood-dual` | `reverse` | `curved-edge-20` follows the one single centrally bowed lower cavity lip; the opposing far lip is straight. |
| `captain-fingerfood-unlevel` | `primary` | `curved-edge-20` follows the visible upper curved contact face; `outer-jug` follows only the narrow top exterior body band, excluding the cavity and edge lip. |
| `captain-fingerfood-unlevel` | `reverse` | `curved-edge-25` follows the visible lower curved contact face. |
| `captain-fingerfood-pocket` | `primary` | `edge-15` and `edge-20` follow distinct opposing cavity lips; `jug-outer-rim` follows the single source-supported continuous U-shaped outer contact. There is no separate `pinch-body`. |

The previous POCKET `outer` presentation and `assets/outer.png` were removed:
that dedicated view was unsupported, while the accepted primary visibly
exposes the source-backed outer body and rounded rim. The sole primary now has
exactly three physical holds: `edge-15`, `edge-20`, and the one continuous
`jug-outer-rim`; the unsupported duplicate `pinch-body` was removed.

## Visual review evidence

Review-only normal, all-active and stable-hold-ID captures for all five final
presentations are recorded under
`.context/pretty-impala-captain-visual-overlays/manifest.json`. The capture used
an isolated workspace-owned Workbench catalog containing only these three
packages; its temporary server, Chrome profile and staging directory were
terminated and deleted after capture. The captures confirm that the same saved
paths provide normal overlay, selected/active fill and hit-region geometry.
The source/candidate/final-overlay comparison is recorded at
`.context/pretty-impala-captain-topology-fix/captain-source-and-overlay-contact-sheet.png`.
It confirms that both DUAL views contain one straight lip opposite one centered
bow, each `outer-jug` remains confined to a distinct top exterior band without
overlapping an edge path, and POCKET has no `pinch-body` overlay.
