> Superseded BEFORE review: the user subsequently corrected "there are no grooves".
> The current correction is recorded in `../groove-removal-review/review.md`.
> This packet preserves the initial wood-finish-only run and its rejected groove interpretation.

# #16 La Baguette — individual review, 2026-10-01

Human acceptance: **pending**. User asked why the bottom notches exist and
said there should be cords. Neither message accepts the board.

The bottom interruptions at the two ends are the existing estimated exterior
cord groove bands. The approved manufacturer's front/rear/oblique photographs
show exterior end wraps; they do not establish exact groove widths, depths,
or corner radii. The native source estimates 4 mm bands, 1.5 mm deep, centered
at x ±220 mm. The assembled fresh-app screenshots expose their relationship
to the cord. These details remain open to human review; no new hidden channels
or connections were inferred.

The only package change is `presentations[0].media.display.surfaceFinish =
"wood"`, embedded using `Tools/HangboardCAD/set_board_manifest.py`. The
[retained manufacturer description](../evidence/product.html) calls the board
soft wood, and the [approved source register](../sources.json) supplies its
URL and SHA-256. This maps directly to the existing renderer's wood finish;
its procedural appearance is a display adaptation, not a scanned texture.
The exact source is
<https://www.yyvertical.com/en/products/la-baguette-poutre-escalade>.

[Archive proof](finish-metadata-archive-proof.json) establishes that only the
manifest field changed. Every native geometry archive member, all other
Document.xml content, contact facts, USDZ, descriptor, suspension, pose,
camera and route remain unchanged. The USDZ remains unbound with no material,
shader, texture or binding prims; [inspection](usd-inspection.json) imports
the actual shipped asset. No canonical `board.json` was created.

New FCStd SHA-256:
`9e56cec4e8494d26bc97629c8a73a11dc7b4adf9e5071a0963eafe3827c95d52`.
The prior source hash `10aa957bda4790fff4dc119b1eddf2178eb78a4f33daf71fd0a488fdae76eb57`
remains in the untouched historical export/recompute/cord proofs. Those raw
proofs have not been rewritten to claim the new source identity. Byte
preservation bridges their geometry result to this metadata-only revision;
expensive unchanged geometry exports were not rerun.

The existing suspension is `cadRoutedCord`: two exterior end wraps generated
against the native solid, with no hidden bores. Its 0.9 m per-loop length and
1.2 mm radius are display estimates. Cords render separately from the USDZ;
the gray native comparison views deliberately show only the board. The
[historical continuous-clearance proof](../cord-continuous-clearance.json)
retains the exact unchanged route certificate and its tolerance.

[Original/native comparison](original-native-comparison.png) lays out the
complete prior committed raster faces next to the byte-unchanged native
front/rear/side/top views. There was no prior native side or top asset. This
is a labeled presentation of whole images, with no cropping, tracing,
registration, pixel measurement or geometry inference. Original images
remain byte-identical.

[Fresh app views](app-review.png) show the wood appearance, front/rear contact
selection, and an actual oblique orbit with both cord legs visible.
[All six selections](six-contacts.png) cover the three canonical poses:
front 20/25 mm; reverse 10/15/30 mm; and the upper tray. The fresh app was built
from baseline `9399160729fcc418cedf47344b41163d244b5d96` plus the recorded
wood-manifest edit on isolated simulator
`40D4FEF9-1824-49A7-A31E-D08E20DB90F7` (iPhone 17 Pro, iOS 26.5), named for
`placid-badger-cad-second-half`. Exact commands, raw images, accessibility
snapshots, build/installed binary checks, additional runtime probes and
cleanup verification are retained in `ios/`.

The initial tap-on-active-contact probe did not reset the orbit. Its raw
`projectedFramesChangedAfterTap: false` remains preserved; it is not counted
as a passing reset test. Package/schema, all eight source hashes, actual USD
node inventory and the [delivery lock](delivery-validation.json) pass.
No compiler, renderer, solver or out-of-scope package was changed.

Limits: this is an estimated display model, not manufacturer CAD or a claim
of manufacturing, ergonomic, safety or dynamic-physics accuracy. The native
views are retained exact-asset renders; the iOS views are freshly captured.
The review queue remains pending until the user accepts the shown revision.
