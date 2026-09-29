# Whetstone geometry rationale and estimate table

The approved evidence is Whetstone1.png (manufacturer front), Whetstone5.jpg (right oblique), and Whetstone6.jpg (left oblique), with exact URLs and hashes in review.json. Geometry was deliberately authored as analytic sketches, cubic curves, native lofts, fillets and booleans. No image geometry extraction was used. The source kind `native-parametric-measured-profile` is the retained compiler enum; this board is directly authored from manufacturer evidence, not a measured display mesh.

| Geometry | Value | Status |
|---|---|---|
| Overall x width / z height / y thickness | 635 / 152.4 / 50.8 mm | Published 25 × 6 × 2 in |
| Edge contact depth inventory | 40, 30, 25, 20 mm | Published |
| Center incut | 10° | Published; interior floor slope is 10° after mouth relief |
| Two-finger pocket depth | 40 mm | Published |
| All contact IDs, kinds, finger capacity, source metadata | Preserved | Live prior schema-v3 inventory |
| Upper long slot extents | x -248…-80 and 80…248 mm, z 88…120 mm | Operator display estimate |
| Upper slot depth division | x -164 and 164 mm | Operator display estimate; left-to-right 40 then 30 on each side follows manufacturer printed labels |
| Lower long slot extents | same x extents; z 14…45 mm | Operator display estimate |
| Lower slot depth division | same split x; 25 then 20 on each side | Operator display estimate; ordering follows printed manufacturer labels |
| Upper front / lower front / rear | y -50.8 / -42 / 0 mm | Thickness published; lower-row recession 8.8 mm is display estimate |
| Center slot mouth | x -58…58, z 54…86 mm | Operator display estimate |
| Two-finger mouths | centers x ±286, x width 42, z 64…119 mm | Operator display estimate |
| Two-finger shoulder relief | outer upper corner dropped up to 9 mm | Operator display estimate from visible oblique shoulder shape |
| Long-slot mouth corner radius | 8 mm (analytic cubic quarter circle approximation) | Operator display estimate |
| Center / pocket mouth corner radius | 13 mm (analytic cubic quarter circle approximation) | Operator display estimate |
| Mouth transition | 3 mm into depth; 2 mm inwards on exposed profile sides | Operator display estimate |
| Lower wing perimeter round | 3 mm native fillet | Operator display estimate |
| Jug silhouette | Inner bumps x ±145, outer bumps x ±265 mm; center plateau and end turns | Deliberately drawn operator display estimate; mirror-symmetric |
| Transverse jug sections | y -50.8, -46, -36, -23, 0 mm with drops 15, 5, 0, 2, 16 mm | Operator display estimate; smooth native loft |
| Jug envelope normalization | Top silhouette translated down 0.22201794368326 mm | Native tessellation-derived adjustment to meet published overall height; not image-derived |
| Both board and presentation aspect ratios | 635 / 152.4 | Derived from authored envelope |

The historical raster mapped the right-side depth halves as a mirror of the left, while the approved manufacturer front photograph prints 40→30 and 25→20 left-to-right on both sides. The migration preserves logical IDs and source facts, correcting physical node assignment: right 40/25 is the inner segment, right 30/20 is the outer segment. Exact left/right silhouette mirroring is preserved; the depth assignment is intentionally not mirrored.

The upper body is a smooth five-section loft, with two recessed lower wings joined behind it. Split cavities use ruled native loft tools. Each semantic cavity uses its own lofted open walls and native rear face, clipped with a native Common against the final solid. Each rear sketch face is oriented wood-outward by a native Part::Reverse; the lateral loft walls already face outward. A retained boundary-normal regression failed on the initial un-reversed rear faces and passes on the corrected source. Native boolean Refine=False retains coplanar boundaries between depth halves so compiler triangles do not cross logical contact boundaries. The jug uses a native SubShapeBinder of the actual upper loft's 16 top faces; these are native loft faces, not fillet-face references. The self-contained FCStd contains no Python feature proxies, mesh source, external links, materials or textures.

Mounting holes, screws, hardware and engraved labels are omitted from the display geometry. This does not imply their absence from the physical product. No suspension is authored for this wall-mounted product.

Validation reports: geometry-report.json records body validity, bounds and all contact depths; native-edit-validation.json verifies all contact surfaces against the body shell, then edits the center rear-section depth by +0.5 mm and the jug section height by +0.5 mm in memory. The body and corresponding contacts follow each edit, an unrelated pocket remains fixed, and the original source bytes are never changed. Native optimal bounds include OCCT numerical tolerance: 635.0000002 × 50.8000002 × 152.4001422 mm. Mesh bounds are reported by the retained compiler.

The model camera is an operator-selected orthographic display estimate: viewDirection [0, -0.3420201433, -0.9396926208] (20° elevation), up [0,1,0], fitPadding 0.08. It is not a manufacturer dimension. The comparison sheet uses native front/side/top projections; the scratch renderer corrects painter depth ordering for positive-axis side/top cameras. The separately rendered elevated front uses the same 20° model presentation estimate.
