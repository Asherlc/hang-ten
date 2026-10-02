# Owl Climb Poker review 12 preflight — 2026-10-02

Owner: `placid-badger`. Root HEAD: `ad74a51e1c43991145721ab04ff8c0d3c6c51cca`. Read-only preflight; no geometry judgment or approval recorded.

| Canonical file | Bytes | SHA-256 |
| --- | ---: | --- |
| owl-climb-poker.FCStd | 4,122,179 | `b6c53624e8684fb032026b0932c42987e803fdf5a472940a376678bbceeaecd1` |
| primary.usdz | 2,014,725 | `5c471299a7172349ecd1f21fd2d11695a25867ef101aecf0f6c4397054d13874` |
| primary.model.json | 16,813 | `0aa7cd7265bb68e839da70203fffb7804fadea2ed4b133e6941ecf5eb8de19ac` |

Pure-host generated `board.generated.json`: `337c3f6fb5d23b2fc4b155c810d71c36712c8d0257eb63504de1b56b1871656a` (9,984 bytes). Canonical `board.json` remains physically absent. Board ID `owl-climb.poker`, revision `2026-09-contact-first`, presentation `primary`; 660 × 100 × 100 mm and aspect ratio 6.6. All 34 unique contact IDs survive; positions face-a/b/c/d partition them 7/9/9/9 and match the retained metadata diff exactly. Descriptor binds 34 contact nodes plus one body node and has the same contact inventory. Both Face D deep-rounded-recess IDs remain present. The two Face C half-round depth fields remain omitted under the retained authorized diameter/depth correction. Full factual fields and ordered position inventories are in `hash-manifest-report.json` and `board.generated.json`.

`primary.media.display.surfaceFinish` is absent. The exact retained primary A/B photos visibly show wood grain and the source-owned subtitle identifies a wood hangboard. Recommend adding the existing supported **wood** finish selector through `set_board_manifest.py`, preserving every contact fact and the USDZ/descriptor bytes. No wood species is supported by this preflight. USDZ remains unbound; finish metadata must stay outside the asset. Its ZIP contains only `stage.usdc`, without separate texture assets; fresh material-binding validation was not run.

All four registered manufacturer photos match retained hashes/byte counts. The dated audit explicitly states **no documented suspension** and omitted mounting hardware. No suspension field or sidecar exists; do not add cord geometry from appearance or assumption.

Retained native reopen/recompute, single-valid-solid, 34-contact, fully-constrained-sketch, meaningful PocketDepthScale edit/restore, final compile, C/D regression, and independent compile/hash-closure records all name this exact FCStd hash. Compile/hash closure names the exact shipped model hash, and its compiler-report hash verifies. These are historical records; no fresh native run, compile, or test was started. Native archive identity: 427 objects, including 187 Sketcher objects, and `native-parametric-measured-profile`. Authoring prose still contains an earlier 87,518-triangle / 1,958,488-byte export statement; current hash-bound final reports give **90,286 triangles / 2,014,725 bytes**.

Prior app captures use owner `placid-badger`, iPhone 17 Pro / iOS 26.5, simulator `D7168911-6A46-4FED-9019-968CCEFEB9DB`. `default.png` selects `face-a-left-outer-slot`; `contact-selection.png` selects `face-d-left-outer-slot`. Both AX selected-hold IDs agree, and the contact-selection AX inventory contains all 34 current contact IDs. Recorded FCStd/USDZ/descriptor hashes exactly match current assets. Capture date, app build commit, and app bundle hash are absent from `validation.json`; current runtime and renderer behavior remain unverified. Geometry acceptance remains pending the one-by-one review.

Only owner-scoped report files were written. No native/GUI process, temporary external resource, HTTP server, or simulator was created. Canonical packages, dated audits, and reserved shared renderer files were not edited.
