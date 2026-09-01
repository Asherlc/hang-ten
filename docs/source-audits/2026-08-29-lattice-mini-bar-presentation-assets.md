# Lattice Mini Bar presentation assets — source audit

Reviewed 2026-08-31. This audit covers the four physical/selectable
presentations and manually authored canonical geometry in
`Hangboards/lattice-mini-bar`.

## Revision, inventory, and presentation mapping

The current [Lattice Mini Bar product page](https://latticetraining.com/product/mini-bar-portable-hangboard/)
and the [Lattice 2025 catalogue, p. 8](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf)
enumerate exactly four grips for this 15.5 cm reversible portable bar: 10 mm
edge, 20 mm edge, ergonomic jug, and mini pinch. They are represented in that
exact order by stable IDs `edge-10`, `edge-20`, `ergonomic-jug`, and
`mini-pinch`. Each presentation maps exactly one same-ID hold; `edge-20` is the
sole default. No fifth contact, measurement, capacity, or training claim was
added.

The gallery images have no captions. Mapping
[Web-7](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-7.jpg)
to the 10 mm edge and
[Web-8](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-8.jpg)
to the 20 mm edge is therefore an explicit visual inference: Web-7 shows the
smaller opposing shoulder in use and Web-8 shows the broader opposing shoulder.
[Web-10](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-10.jpg)
corroborates rotated edge use; it is not a fifth selectable position.
[Web-11](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-11.jpg)
shows ergonomic-jug use. Web-2 and Web-9 establish the end-on mini-pinch
orientation.

Source review corrected an earlier symmetric-notch interpretation. The physical
section is one dominant rounded lobe with one shallow exterior-open
longitudinal concavity offset to one side, separating unequal integral
shoulders. The relief is asymmetric, runs through both flat cut ends, and is
never a centered notch, blind pocket, tunnel, dowel-plus-rail, or two-piece
body. All final descriptions and paths use that corrected topology.

## First-party physical authority

All downloaded gallery inputs were reviewed at their original 1000 × 1000
dimensions. They are physical authority and corroboration, not tracked
presentation pixels.

| Asset | Physical role | SHA-256 |
| --- | --- | --- |
| [Web-1](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-1.jpg) | One-piece long body, flat ends, through relief, pale wood, external suspension | `610cfaa96a95d80ae0d37ef4bbf2b1d881b47d0813d7d0eb4f9db9b5c30270de` |
| [Web-2](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-2.jpg) | Offset asymmetric end section, unequal shoulders, end grain, external bight | `e8b2e366f8e20abc4959019c5c46ae67d53fe4526100f66acf8d3f0e3d66974b` |
| [Web-4](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-4.jpg) | Rounded exterior body, pale timber, coherent suspension | `3194515715cc34c7f42838dceb25e27a78740b8ee6be4d3457a1b36d25a8008e` |
| [Web-7](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-7.jpg) | Visually inferred smaller 10 mm shoulder in use | `f4c0be57535d50abd1a1abf58b187448803d063cf9608033d80d0346cc9c87bb` |
| [Web-8](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-8.jpg) | Visually inferred broader 20 mm shoulder in use | `9a27940c3773f266696e0a91653c4e97de5a84d843ceaab992cc26be32f01570` |
| [Web-9](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-9.jpg) | Mini-pinch end orientation | `36ffcaecd382198473a9803e34e65dab98d79fba9b5387158d6d2b4349542eb5` |
| [Web-10](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-10.jpg) | Corroborating rotated edge use, not another position | `163afb247451330a89469d4423f52c8ca892d51654ac6fc2affcd3ee4d50eb3f` |
| [Web-11](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-11.jpg) | Smooth ergonomic-jug exterior in use | `e17ad0df7b23b6b3f796bd0b5fb1fa219cf341728a90e85a479424ad2d36cfe8` |

## Final raster contract

All four accepted PNGs are byte-for-byte copies of built-in image-generation
outputs. There was no crop, resize, mask, retouch, compositing, source
registration, segmentation, detection, vectorization, automatic path proposal,
or pixel postprocessing.

| Presentation | Accepted built-in output | Tracked asset | Pixels / ratio | SHA-256 |
| --- | --- | --- | --- | --- |
| `edge-10` | `run 01a05b12-8465-70d2-b265-a5d29b2ddedb / output exec-9dbb30b1-d4bb-436f-aae5-3970a67283fc.png` | `assets/edge-10.png` | 1536 × 1024 / `1.5` | `ca255016d3565f14c550f6d14e1b9e8f8f233f3627db1c5c4fef5fca8ea2727d` |
| `edge-20` | `run 01a05b12-8465-70d2-b265-a5d29b2ddedb / output exec-a1eaa538-c0a5-4423-9fce-38a8b5808dab.png` | `assets/edge-20.png` | 1536 × 1024 / `1.5` | `5352c53a330133f856264e2ca824c64ffcd36d4b17126b96170d21f6c28ba431` |
| `ergonomic-jug` | `run 01a05ad6-c3b6-79c0-86be-3c70c5ca35c2 / output exec-ce45a8b1-f09b-426f-8cae-aacef36e3ce8.png` | `assets/ergonomic-jug.png` | 1536 × 1024 / `1.5` | `45cd3830f4deeeaf4b602df1f79e762c4c18845aed167af6215578568483d152` |
| `mini-pinch` | `run 01a05ad6-c3b6-79c0-86be-3c70c5ca35c2 / output exec-b9f1e9a5-e643-48c4-a2c1-90ea3fe652c3.png` | `assets/mini-pinch.png` | 1254 × 1254 / `1.0` | `2ef36a6fa5e6470ce75f708f4d221b9d5a31b95232a9555bd20cff311a788b42` |

## Exact edge-10 built-in lineage

The initial ordered inputs were: accepted end-section anchor `exec-b9f1e9a5...`
(`2ef36a...`), Web-7, Web-8, Web-1, and Web-4. The exact initial prompt was:

```text
Use case: product-mockup
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 10 mm edge position
Primary request: Generate a new clean studio render from the five references, not a photographic collage and not an edit of any single source. Show exactly one reversible solid wooden Lattice Mini Bar with its long axis perfectly horizontal, suspended by one continuous blue rope with small orange flecks.
Input images: Image 1 is the accepted end-on geometry anchor; preserve its single asymmetric softly rounded cross-section and small exterior-open lower concave notch, translating that same cross-section constantly along the full bar length. Image 2 is official 10 mm grip evidence and defines the slim near shoulder to expose. Image 3 is official 20 mm contrast evidence; the selected near shoulder must be clearly slimmer than that broad contact. Image 4 defines the one-bar proportions and complete external suspension topology. Image 5 defines pale fine timber, the smooth rounded exterior, and external rope wrapping at both ends.
Scene/backdrop: uniform warm off-white studio background, no floor horizon and no scenery.
Subject geometry: one uninterrupted solid bar with one constant asymmetric rounded section from left flat cut end to right flat cut end. A shallow exterior-open longitudinal concavity separates unequal shoulders and must visibly continue all the way through both actual flat cut ends. The requested upper/near shoulder is a slim, shallow 10 mm contact band; the opposing shoulder is visibly broader. The recess is a continuous through-length open relief, never a blind or closed pocket.
Camera/composition: strict orthographic head-on front elevation of the selected long side; zero yaw, zero foreshortening, zero roll, long axis level, and both flat cut ends the same apparent height and scale. Center the bar in a clean 3:2 landscape canvas with generous even padding. Keep the entire rope loop, knot, short tail, both external end bights, and the whole bar fully inside the frame and uncropped.
Rope topology: one continuous blue-and-orange braided cord forms complete external bights around both ends of the wood, then rises into a complete suspension loop with one visible knot and short tail. The cord passes around the outside of the wood only. Keep small source-backed lengths of wood visible beyond a wrap only if the longitudinal relief continues through that wood to the true flat end.
Style/lighting/materials: clean simplified premium catalog product render; pale smooth fine-grained tulipwood, softly eased edges, realistic shallow recess, soft diffuse studio lighting, restrained natural shadow, off-white background; no distressed, chipped, rough, oversharpened, or plastic-looking wood.
Hard constraints: exactly one bar; constant cross-section; slim 10 mm near shoulder; continuous open concavity reaching both true flat ends; no blind canoe-shaped pocket; no rounded caps; no terminal ears; no full-height end blocks; no separate end pieces; no bulges; no taper; no perspective; no axial holes; no drilled holes; no carved cord slots or local cord notches; no cord tips cut off by the frame; no closed rope wreath around the product; no hardware; no hands; no people; no text; no logo; no watermark.
```

That draft (`exec-69946e7e...`) was rejected because the section became a dowel
and the cord appeared to enter local slots. Ordered inputs for the next edit
were that draft, `exec-b9f1e9a5...`, Web-7, Web-1, and Web-4:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 10 mm edge position
Primary request: Edit Image 1 only to correct the wooden grip geometry and the two end bights. Keep its strict front elevation, exact 3:2 framing, level horizontal long axis, centered placement, off-white background, pale fine-grained timber, complete uncropped suspension loop, upper apex, knot, and short tail unchanged.
Input images: Image 1 is the edit target and defines the composition, lighting, timber treatment, and complete rope-loop layout. Image 2 is the accepted end-on geometry anchor; extrude its one asymmetric softly rounded section constantly across the full length. Image 3 is official 10 mm contact evidence; it defines the slim near shoulder. Image 4 is official suspension evidence; it defines external bights around the wood rather than cord holes. Image 5 is official exterior/material evidence.
Geometry change: replace the nearly cylindrical front face with one constant asymmetric rounded section. Cut one shallow exterior-open longitudinal concavity into the front-facing lower portion of the bar. Its mouth and softly shaded inner plane must remain visibly continuous from the true left flat cut edge to the true right flat cut edge, interrupting both end silhouettes with the same small open notch. The concavity separates unequal shoulders: a clearly slim upper/near 10 mm contact band and a visibly broader opposing lower shoulder. It is one shallow open relief, not a deep slot.
End and rope correction: remove both dark holes, grommets, drilled entries, and carved cord slots. At each end, show the blue-and-orange cord lying visibly on the exterior front surface, curving continuously under and around the outside lower silhouette as an external U-shaped bight, then rising behind/alongside the wood. No portion of cord may enter the wood. The true flat wood ends remain visible and equal in height; the open longitudinal relief reaches them with no cap, terminal ear, full-height end block, or separate end piece.
Invariants: exactly one uninterrupted bar; same zero-yaw orthographic camera; same scale at both ends; same complete uncropped rope loop, knot, tail, composition, background, lighting, and premium catalog style; smooth pale fine timber; no hands, people, text, logo, watermark, hardware, roughness, chips, plastic finish, perspective, taper, bulges, rounded caps, blind canoe pocket, axial holes, drilled holes, local rope notches, or cropped cord.
```

That iteration (`exec-6c068206...`) fixed the cord and shoulder but retained a
blind canoe-shaped pocket. Ordered inputs for the end-opening edit were that
iteration, `exec-b9f1e9a5...`, and Web-1:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 10 mm edge position
Primary request: Edit Image 1 with one surgical geometry correction only: open the existing shallow lower longitudinal concavity completely through both true flat cut ends. Preserve every other successful element exactly: strict zero-yaw front elevation, 3:2 canvas, bar scale and position, level long axis, equal end scale, off-white background, pale fine timber, existing slim lower 10 mm shoulder, broad opposing upper body, soft lighting, complete uncropped blue-and-orange loop, knot, tail, and external rope bights.
Input images: Image 1 is the edit target. Image 2 is the accepted asymmetric end cross-section: each true flat end of the edited bar must show its same small exterior-open lower concave notch. Image 3 confirms one continuous wooden bar with cord wrapping externally around its ends.
Exact end correction: remove the solid full-height terminal wood that currently closes the left and right ends of the horizontal concavity. Extend the existing concavity's mouth, shaded inner plane, and slim lower lip horizontally all the way to and through the true left flat cut edge and true right flat cut edge. The channel must be visibly open at both ends like an open-ended trough: its inner plane reaches each cut edge, and each cut-end silhouette is interrupted by the same small concave opening shown by Image 2. There is no wooden bridge or cap across the channel at either end and no terminal block after it.
Rope constraint: keep both exterior bights continuous and visible on the outside of the wood. They may overlap the face, but they must not hide the open-ended relief or enter any hole, slot, or local cord notch. Keep the true flat wood edges visible just outside or beside the wraps.
Hard invariants: change only the two terminal portions needed to open the already-existing relief; keep the center geometry and all rope, framing, background, lighting, and material treatment unchanged. Exactly one uninterrupted bar; one constant cross-section; same slim lower 10 mm shoulder for the full length; zero yaw; equal end scale; flat cut ends; no blind canoe pocket; no full-height end blocks; no rounded caps; no terminal ears; no separate end pieces; no holes; no drilled entries; no carved cord slots; no perspective; no taper; no hands; no people; no text; no logo; no watermark.
```

That iteration (`exec-12ca80f8...`) replaced the central relief with solid wood
and isolated end pockets. The successful geometry pass returned to
`exec-6c068206...`, with `exec-b9f1e9a5...` and Web-1:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 10 mm edge position
Primary request: Use Image 1 as the edit target. Preserve its complete 3:2 composition, strict front elevation, exact bar height and center, pale smooth timber, shallow lower channel depth and height, slim lower 10 mm lip, broad upper body, off-white background, full uncropped blue-and-orange suspension loop, apex, knot, and tail. Correct only the longitudinal channel's end termination and the wrap placement needed to reveal it.
Input images: Image 1 is the edit target. Image 2 is the accepted asymmetric end-section anchor. Image 3 is official evidence that small true wood ends can remain visible beyond external cord wraps.
Channel correction: stretch the existing horizontal shallow channel straight outward without changing its depth, vertical position, or height. Its upper edge, shaded interior, and slim lower lip remain parallel and continue uninterrupted behind the cord all the way to the exact left flat cut plane and exact right flat cut plane. At each true cut plane the channel has a flush square-open end: the shaded interior simply reaches the outer vertical cut line. There are no rounded return curves at the left or right and no pale full-height pillar closing the channel. Every transverse slice of wood from the left cut to the right cut has the same asymmetric section shown by Image 2.
Wrap placement: move each exterior rope bight only slightly inboard, roughly five percent of the bar length from its nearest true cut end, so a small source-backed length of wood remains visible beyond it. In each visible overhang the same shallow channel and slim lower lip continue through to the true flat cut. Cord lies over and around the outside surfaces and does not enter the wood.
Visual check: the result must read as one constant-profile wooden extrusion with an open-ended shallow longitudinal relief, not a pocket routed into a capped beam. The channel's shaded band touches both outer cut lines, including behind the wraps; the center is unchanged; the lower lip remains slim and continuous.
Hard constraints: one bar; one constant cross-section; zero yaw and equal end scale; complete uncropped rope and knot; no blind canoe pocket; no rounded channel terminations; no end caps; no terminal blocks; no ears; no projections; no separate end pieces; no holes; no cord slots; no hardware; no perspective; no taper; no hands; no people; no text; no logo; no watermark.
```

The resulting `exec-d50b6faf...` passed geometry but its cord visually stopped at
the wood. The final rope-only edit used that geometry plus Web-1:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 10 mm edge position
Primary request: Edit only the blue-and-orange suspension cord in Image 1. Keep every wooden and background feature unchanged pixel-for-pixel in appearance: the one horizontal bar, exact cut-end positions, constant section, shallow lower channel touching both cut lines, slim lower 10 mm shoulder, broad upper body, zero-yaw orthographic camera, scale, framing, pale timber, lighting, and off-white background are locked. Do not close, shorten, round, or otherwise alter the channel.
Input images: Image 1 is the edit target and locks the approved wood geometry and composition. Image 2 is official evidence for the complete external cord topology.
Cord correction: replace the two visually terminating strands at the bar with a single continuous blue cord with small orange flecks that wraps externally around both ends exactly as a suspension sling. At each side, one front strand descends over the exterior face, curves visibly and smoothly under the outside lower silhouette as a complete U-shaped bight, then rises again behind/alongside the wood as a second parallel return strand. Thus two close parallel rising strands are visible on the left and two on the right. These returns continue upward into one complete tall suspension loop with a rounded apex. Include one compact visible knot on the right-side inner return and a short finished tail. Every cord segment is connected; there are no cut tips near the bar.
Placement: keep each exterior bight slightly inboard from its nearest true flat cut end so a small wood overhang remains visible. The approved shallow channel and slim lower lip continue visibly through each overhang to the true cut edge. The rope lies on and around the exterior only and never enters the wood.
Hard invariants: change rope only; preserve all approved wood geometry exactly; keep the entire doubled loop, apex, knot, short tail, both bights, and bar fully inside the 3:2 frame; no cord endpoints at the wood; no holes; no drilled entries; no carved cord slots; no hardware; no extra rope loops; no closed wreath; no hands; no people; no text; no logo; no watermark.
```

This produced the accepted `exec-9dbb30b1...`.

## Exact edge-20 built-in lineage

Initial ordered inputs were the accepted edge-10 raster, Web-8, Web-10, and
`exec-b9f1e9a5...`:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 20 mm edge position
Primary request: Edit Image 1 into the matching 20 mm presentation of the exact same physical Mini Bar. Preserve the accepted edge-10 family render as aggressively as possible. Change only the axial roll/contact exposure so the broader opposing near shoulder is presented to the viewer. The final must remain a clean 1536×1024 straight-on catalog render, not a collage and not a reconstruction of the source photographs.
Input images: Image 1 is the edit target and absolute family anchor; lock its camera, canvas, bar size, outer silhouette, material, background, lighting, grain character, rope placement/topology, knot, tail, and complete framing. Image 2 is official 20 mm contact evidence and defines only the broader opposing usable edge. Image 3 corroborates official edge use and external cord routing. Image 4 defines the invariant asymmetric softly rounded physical cross-section; roll that same section to expose its opposing shoulder rather than redesigning it.
Single allowed change: represent the same bar axially rolled to its 20 mm orientation. At card scale, the newly exposed near contact shoulder must read as approximately 1.7–2.0 times the usable depth of Image 1's slim 10 mm near shoulder. Make that difference obvious but restrained. Within the unchanged bar height, shift the same shallow through-open relief only as required by the axial roll so a single broader near shoulder is visible; compensate within the existing broad face rather than enlarging the bar. Preserve exactly one shallow relief with the same apparent opening height and depth.
Geometry invariants: the bar keeps Image 1's exact overall length, overall height, zero-yaw orthographic front elevation, level long axis, equal flat cut ends, and constant asymmetric section. The shallow exterior-open longitudinal relief remains fully visible and continuous to both true outer cut lines, including through the small wood overhangs beyond the cord wraps. Keep the same end silhouettes and softly eased outer corners. Do not deepen, enlarge, shorten, hide, cap, round off, or duplicate the relief. Do not add a second groove, rail, shelf, lip, step, bevel, or separate part.
Rope and pixel-character invariants: preserve Image 1's blue-and-orange doubled loop as nearly pixel-identically as possible: same two parallel rising strands on each side, same exterior U-bights slightly inboard of the cut ends, same apex, same compact right-side knot, same short finished tail, same cord thickness/weave, and the same fully uncropped placement. The cord remains entirely outside the wood with no holes or carved slots.
Style/composition invariants: preserve the exact 3:2 framing, off-white background, bar/rope scale and positions, pale fine timber, grain direction, soft diffuse lighting, restrained shadow, and catalog cleanliness of Image 1. No hands, people, source-photo logo, text, watermark, hardware, roughness, chips, oversharpening, or plastic finish.
Hard avoid: do not enlarge or shrink the body; do not change bar height or length; do not change cut-end positions or silhouettes; no yaw, pitch, perspective, taper, bulges, rails, caps, terminal blocks, ears, stepped profiles, blind canoe pocket, hidden groove, additional recess, holes, cord slots, cropped cord, extra loop, or closed rope wreath. The only visible family difference is the broader opposing 20 mm contact exposure at approximately 1.7–2.0 times the edge-10 usable depth.
```

`exec-fec39e29...` was rejected because it remained indistinguishable from 10
mm. The depth-amplification edit used that raster, accepted edge-10, Web-8, and
`exec-b9f1e9a5...`:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 20 mm edge position
Primary request: Use Image 1 as the edit target and make one unmistakable card-scale correction only: expose the broader opposing 20 mm near shoulder. Keep the entire family render unchanged in appearance except for the axial-roll/contact exposure described below. Image 2 is the accepted 10 mm comparison, not an edit target.
Input images: Image 1 locks the 1536×1024 canvas, zero-yaw camera, outer bar silhouette, exact cut ends, rope, knot, tail, framing, timber, grain, lighting, background, and single open-through relief. Image 2 shows the slim 10 mm near shoulder whose usable depth is the comparison baseline. Image 3 is official evidence for the broader 20 mm contact. Image 4 locks the same asymmetric physical cross-section.
Single geometry change: make the pale lower near contact shoulder in Image 1 visibly approximately 1.8 times the vertical usable depth of Image 2's slim pale lower shoulder. At this resolution, the slim lower band in Image 2 reads about 18 visual pixels from the bottom edge of the shaded relief to the outer bottom silhouette; the 20 mm result should read about 32–34 visual pixels, clearly different even in a 320-pixel-wide app card. Achieve this only by moving the same unchanged-height shallow relief upward within the unchanged bar silhouette, as the same physical asymmetric section rolls to expose its broader opposing shoulder. Reduce the broad upper face by the corresponding amount; do not increase total body height.
Relief invariants: keep exactly one shallow shaded relief with the same apparent opening height, depth, material, and horizontal geometry as Image 1. Its top edge, inner shading, and bottom edge remain straight and parallel and continue flush to both true flat cut lines, including through both small wood overhangs. Do not make the relief taller, deeper, shorter, hidden, blind, rounded at the ends, capped, stepped, doubled, or converted into a rail/shelf.
Absolute locks: preserve Image 1's exact 1536×1024 framing, outer top and bottom silhouette positions, bar length, cut-end positions and equal height, softened corner character, pale timber, grain texture, background, shadow, and strict orthographic camera. Preserve the complete blue-and-orange cord almost pixel-identically: paired rising strands, exterior U-bights, apex, right knot, finished tail, thickness, weave, and uncropped placement. Cord stays outside the wood.
Hard avoid: no body enlargement or shrinkage; no silhouette change; no yaw, pitch, perspective, taper, bulges, caps, end blocks, ears, extra rails, extra lips, added steps, second groove, hidden groove, blind pocket, holes, carved cord slots, cropped tips, hands, people, text, logo, watermark, or hardware. The only intended visible difference from the edge-10 anchor is one broader lower near shoulder at about 1.8 times the usable depth.
```

`exec-ba43565f...` overshot into a rail-like half-body band. Its midpoint edit
used that raster, accepted edge-10, and Web-8:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 20 mm edge position
Primary request: Use Image 1 as the edit target. Correct only its over-amplified lower contact exposure to a restrained, clearly legible 20 mm midpoint. Preserve the same physical single bar, all exterior rope, framing, camera, ends, material, and background. Image 2 is the accepted edge-10 family/relief reference; Image 3 is official 20 mm contact evidence.
Single correction: reduce Image 1's pale lower near shoulder from its current roughly half-body height to a vertical usable depth of approximately 32–36 visual pixels at 1536×1024. This must remain approximately 1.7–2.0 times Image 2's slim roughly 18-pixel lower near shoulder, but substantially smaller than Image 1's current oversized lower band. Move the existing shallow relief downward only enough to achieve that 32–36-pixel lower shoulder; restore the broad upper body by the corresponding amount. Keep total bar height unchanged.
Relief visibility: restore the one shallow through-open relief to the same clear but restrained shadow contrast and apparent opening height as Image 2. It must remain visibly continuous from the true left flat cut line to the true right flat cut line and through the wood overhangs beyond both wraps. The relief is a smooth exterior-open concavity in one solid rounded extrusion, not a dark seam or gap between two parts.
Single-body appearance: blend the lower shoulder continuously into the same pale timber body with the same grain family and softly eased outer contour. It must read as one broader contact lip on one constant asymmetric section, never as a second rectangular rail, stacked plank, separate dowel, attached shelf, or stepped laminate. Preserve the exact outer cut-end silhouettes and do not add horizontal boundary lines beyond the single concavity.
Absolute locks: preserve Image 1's 1536×1024 canvas, exact bar length/height/position, zero-yaw orthographic camera, equal flat cut ends, grain direction, soft lighting, off-white background, full doubled blue-and-orange loop, paired exterior U-bights, apex, compact right knot, short tail, cord thickness/weave, and uncropped placement. Cord stays outside the wood.
Hard avoid: no body enlargement/shrinkage; no silhouette drift; no yaw, pitch, perspective, taper, bulges, hidden groove, blind pocket, second groove, dark split seam, stacked rails, caps, terminal blocks, ears, added steps, holes, cord slots, hardware, hands, people, text, logo, watermark, roughness, chips, oversharpening, or plastic finish.
```

`exec-1f95ccb8...` was a near-pass but still too subtle. Its final nudge used
that raster plus accepted edge-10:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar 20 mm edge position
Primary request: Apply one final minimal nudge to Image 1 only. Preserve its successful single-body timber appearance, exact 1536×1024 composition, camera, silhouettes, through-open relief shape, rope topology, knot, material, lighting, and background. Image 2 is only the edge-10 comparison baseline.
Only change: translate the entire existing single shallow shaded relief in Image 1 upward by a small visual amount of approximately 9–11 pixels while keeping the relief's exact height, depth, shading, straight horizontal boundaries, and end-to-end extent unchanged. The outer bar top and bottom silhouettes do not move. This increases the pale lower near contact shoulder to approximately 32–34 visual pixels, about 1.7–2.0 times Image 2's slim lower contact shoulder. Reduce the upper broad face by exactly the same small amount.
Continuity: the translated relief must still visibly reach both true flat cut lines and continue behind the two exterior wraps through both small wood overhangs. The lower contact remains an integrated softly rounded shoulder of the same solid extrusion, with matching grain and no separate seam.
Absolute locks: keep Image 1's exact bar length, height, positions, equal flat end silhouettes, zero-yaw camera, one-piece timber blend, grain character, shadow, and off-white background. Keep the entire doubled blue-and-orange loop, paired rising strands, exterior U-bights, apex, right knot, short tail, thickness, weave, and fully uncropped framing unchanged.
Hard avoid: do not change anything except the relief's small upward translation and corresponding contact exposure; no enlargement, shrinkage, hidden groove, taller/deeper groove, rounded terminations, blind pocket, stacked rail, dark split seam, second plank, second groove, extra lip, step, cap, terminal block, hole, cord slot, yaw, perspective, hand, person, text, logo, watermark, or hardware.
```

This produced accepted `exec-a1eaa538...`.

## Exact mini-pinch built-in lineage

The accepted end view ultimately descends from a rejected style-only family
anchor `exec-f6746183...` (`5a906178...`). That anchor was never treated as
physical authority; Web-1, Web-2, and Web-9 control physical facts. The exact
historical upstream prompt for that rejected style anchor was not retained and
is not reconstructed. The first end-view inputs were Web-9, Web-2, and that
style anchor:

```text
Create one clean product-isolation asset for the Lattice Mini Bar mini pinch presentation, viewed true end-on. Ordered reference mapping: Image 1 is the official manufacturer end-view catalog detail and is authoritative for the mini-pinch contact face: a centered compact rounded soft-teardrop wooden end face with a small shallow lower notch/relief; Image 2 is an official manufacturer product photo and corroborates the real Mini Bar body proportions and blue/orange cord; Image 3 is the approved asset family anchor and controls only the pale natural fine-grain wood material, blue/orange rope appearance, neutral off-white background, soft diffuse studio lighting, and product-image finish. Camera must look exactly along the bar's long axis, normal to the end face: the face is centered, undistorted, symmetric left-to-right, and fills the useful central area. The long wooden body collapses directly behind the face and is not visible as a side projection or diagonal cylinder. Show the true mini-pinch face silhouette with gently bulging sides, rounded top, and a small centered concave notch at the bottom—no circular disk, no oval ring, no rectangular block. Rope must appear only as plausible outgoing suspension strands routing behind and upward from the product; do not form a closed wreath, halo, or loop around the face, and do not cross or obscure the wooden contact face. No drilled holes, central hole, eyelets, hardware, hands, person, text, logo, labels, or extra objects. Center the complete end-view product on a square 1:1 off-white canvas with generous even margin, minimal floor cue, and no cast shadow crossing the wood.
```

`exec-0b64aa6d...` was rejected as a flat pendant with longitudinal grain, broad
symmetric cleft, and incoherent suspension. The next ordered inputs were Web-2,
Web-9, Web-1, and that rejected draft:

```text
Regenerate a source-faithful true end-on Lattice Mini Bar mini-pinch product asset. Ordered reference mapping: Image 1 is the primary official manufacturer authority for the real flat cross-cut end face, subtle end-grain rings/pores, softly noncircular rounded/teardrop outline, tight small lower concave relief, narrow integral depth rim, and external blue/orange rope bight wrapping beneath/behind the bar before strands rise; Image 2 is official authority for the mini-pinch end orientation in use; Image 3 corroborates that this face is the cut end of one continuous long body with source-faithful external suspension; Image 4 controls only the clean centered true end-on camera, square off-white catalog framing, pale wood finish, and diffuse lighting, not its incorrect pendant-like topology, grain, broad notch, or rope arrangement. Camera looks exactly along the bar's long axis, normal to the cut end face. Center the undistorted face with symmetric left/right scale. Show a very narrow integral side-depth rim immediately behind the face so it unmistakably reads as the end of the long Mini Bar, not a separate flat pendant, puck, disk, or token; the long body collapses behind this rim and has no diagonal side projection. Use authentic cross-cut/end-grain character—subtle curved growth rings and pores—not straight longitudinal plank grain. The wooden silhouette is compact and softly teardrop/rounded with gently bulging sides and a small tight centered lower concave notch, much narrower and shallower than Image 4's broad heart-like cleft. Rope topology must match Image 1: a coherent external cord bight is visibly cupped beneath and behind the lower/outer body, with the two outgoing blue/orange suspension strands rising behind the left and right sides. The bight may peek below the small notch and outer lower edges but must not cross the wooden contact face or form a wreath/halo. No drilled hole, central hole, eyelet, hardware, logo, markings, text, labels, hands, person, or extra objects. Smooth pale fine-grain tulipwood, neutral off-white square 1:1 canvas, generous even margin, soft diffuse studio lighting, minimal floor cue, no cast shadow crossing the wood.
```

`exec-eabe47e3...` corrected the end grain/rim/bight but retained the stale
centered-notch premise. Its final inputs were that raster, Web-2, and Web-9:

```text
Perform a wood-outline-only source correction to Image 1, the otherwise accepted true end-on Lattice Mini Bar mini-pinch asset. Ordered reference mapping: Image 1 is authoritative for the exact centered true end-on camera, square framing, product scale, cross-cut end-grain rings and pores, narrow integral body-depth rim, pale wood material, off-white background, diffuse lighting, continuous blue/orange bight cupping beneath/behind the bar, and outgoing strands; Images 2 and 3 are official manufacturer authority for the actual asymmetric end section and mini-pinch orientation. Preserve Image 1's camera, face area, grain character, depth rim, rope geometry, background, and lighting. Correct only the wooden silhouette and its relief: replace the centered symmetric heart/apple notch with ONE small shallow OPEN offset/asymmetric concavity positioned toward the lower-left quadrant, separating UNEQUAL integral shoulders/lobes. The large rounded main lobe dominates the right and upper face; the smaller shoulder lies to the lower-left of the relief. The concavity is tight and shallow, not a broad cleft, and visibly opens to the outer silhouette; it is the end of the same longitudinal relief running behind the face. The outline must not be mirror-symmetric and must not look like a heart, apple, circle, pendant, puck, separate disk, blind pocket, tunnel, or two joined pieces. Keep a narrow rim immediately behind the corrected outline so it remains the cut end of one continuous body. Preserve the coherent external rope bight beneath/behind and the two outgoing strands; no new rope ends or dark cut tips. No holes, hardware, logo, markings, text, labels, hands, person, or extra objects. Output one square 1:1 raster matching Image 1 except only for the corrected offset asymmetric wood relief and unequal shoulders.
```

This produced accepted `exec-b9f1e9a5...`. Its slightly taller oval and
smoothed relief are visual stylization, not measurement metadata.

## Exact ergonomic-jug built-in prompt

Ordered inputs were accepted edge-10, Web-11, Web-1, and accepted
`exec-b9f1e9a5...`:

```text
Use case: precise-object-edit
Asset type: Hang Ten catalog presentation image for the Lattice Mini Bar ergonomic jug position
Primary request: Starting from Image 1, change only the bar's roll/contact presentation so the broad smooth convex exterior of the dominant main lobe faces the camera as the sole ergonomic jug contact. Preserve the accepted product family and suspension exactly.
Input images: Image 1 is the final accepted topology/family anchor and locks the exact straight-on zero-yaw orthographic camera, horizontal position/scale, equal flat cut ends, one-piece constant section, pale fine timber, complete external blue/orange bights, doubled suspension loop, apex, knot/tail, 3:2 framing, off-white background, and lighting. Image 2 is official manufacturer evidence for ergonomic jug use and identifies the broad smooth exterior contact. Image 3 is official authority for the actual continuous one-piece bar, flat cut ends, rounded exterior, pale wood, and external suspension. Image 4 is the accepted asymmetric end-section authority; its dominant rounded main lobe must remain the same physical body.
Geometry edit: roll the SAME constant asymmetric solid extrusion around its long axis so the dominant main lobe's broad smooth convex exterior faces front. The longitudinal concavity and unequal edge shoulders rotate to the lower/back side, hidden behind the body or visible only as a very subdued narrow underside transition/shadow. The front-facing wood must be one uninterrupted softly convex surface with diffuse curvature, suitable as a jug; no front-facing slot, shelf, band, lip, pocket, or competing edge contact.
Topology/end invariants: keep one continuous solid extrusion with flat integral cut ends and the source-backed asymmetric relief still physically present on the back/underside. Do not turn it into a cylindrical dowel, rectangular board, pill with rounded caps, separate end pieces, or hollow body. The flat ends remain equal scale and uncapped; small source-backed wood extensions beyond the exterior bights remain integral.
Rope/camera invariants: preserve Image 1's complete connected external bights, doubled rising strands, loop apex, knot, and short tail; no cord enters wood and no holes/hardware appear. Preserve exact zero yaw, no foreshortening, level long axis, full uncropped product, background, overall scale, and lighting.
Material/style: smooth skin-friendly pale fine-grain tulipwood, restrained natural grain, soft diffuse form shading; premium catalog render.
Avoid: any usable front edge; open front trough; blind pocket; rails; separate strip; rough/chipped wood; rounded caps; holes; eyelets; text; logo; hands; people; extra objects; watermark.
Output one 3:2 landscape raster matching Image 1's family.
```

This produced accepted `exec-ce45a8b1...`. The through relief is rotated fully
rearward and occluded in the zero-yaw projection; it was not removed.

## Rejected alternatives outside accepted lineages

Many exploratory side-view drafts were rejected before the independent edge
lineages above. Rejection reasons included oblique/foreshortened cameras,
invented axial or bottom holes, disconnected cord tips, rounded cap-like ends,
blind capsule/canoe pockets, stopped reliefs, centered symmetric notches,
rough/chipped material, indistinguishable 10/20 contacts, oversized rail-like
20 mm bands, missing reliefs, and incomplete/cropped rope loops. The
deterministic comparison render was also rejected because its 20 mm shoulder
read as a second full-height rail and its scale/material/cord differed from the
accepted catalog family. None was copied into the package.

## Manual canonical-geometry and review mapping

Every saved contour was deliberately authored against the final pixels and
first-party evidence. No image-derived coordinates, detection, segmentation,
masks, contours, registration, vectorization, automatic simplification, or
proposal/refine/promote workflow was used.

- `edge-10` follows only the slim pale wooden shoulder between the two visible
  bights. It excludes the dark through relief, body, rope, and background.
- `edge-20` follows only the broader pale lower shoulder below the relief and
  its tonal shadow, between the two bights. It excludes the relief/shadow,
  body, rope, and background.
- `ergonomic-jug` follows only the central visible convex wood between the
  bights. It excludes rope, ends behind rope, background, and shadow. The same
  asymmetric relief remains physically present but is rotated rearward.
- `mini-pinch` follows the visible cross-cut wooden face, including its unequal
  shoulders and turning around the offset open relief. It excludes the relief
  opening, narrow rear rim, surrounding bight, strands, and background.

All four contacts use manually selected freeform paths. The saved paths remain
the sole rendering, highlighting, and hit-testing source of truth. Exact SVG
overlays were rendered at native asset dimensions and independently reviewed
after the final raster promotions. The accepted 10 mm contact is deliberately
slim; the accepted 20 mm contact remains one integrated shoulder and is visibly
about 1.7–2× broader at card scale; the jug shows one smooth exterior; and the
pinch retains the corrected offset/asymmetric relief.
