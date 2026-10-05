**Recommendation:** replace the two same-face rear stitches with a crossed graph at each end. Present it as an *inferred display adaptation*: it depends on the current authored bores, and hidden continuity and contact order stay unverified. Don't hold for a far-side view. The current stitch is the only arrangement the maker evidence actually rules out. I edited nothing and ran no solves.

## 1. "Through the wood" is two separate problems
- **Preview artifact (finding A).** The first previews sorted triangles by average depth, so hidden cord and back faces were drawn over nearer wood. The matched-depth renders of the same triangles don't show this. This only fixes the review images; it says nothing about threading.
- **Wrong cord graph (finding B).** The current setup is four leads on the three-well face (F) plus a 14 mm straight stitch between the two mouths on the two-well face (B) at each end. Every source contradicts that stitch, so the cord would still look wrong with correct depth.
- **Runtime appearance.** The app's RealityKit appearance is unverified because the Simulator didn't boot. Don't claim it either way.

## 2. What the whole images show
- **Four free legs, two per end.** This is clearly visible in t1p5, t2 and t2p5. The left pair runs straight to the carabiner; the right pair is knotted above the board. No knot or joint sits on the board in any frame or photo.
- **Every end view shows cord going around the barrel, not a straight stitch.** This holds in FlashBoard1, 3 and 4, video t1p5–t2p5, and t4. FlashBoard2 settles the F face: at each end, both F mouths carry parallel strands that wrap the same edge, with no stitch between them.
- **On the B face, the outer mouth feeds a direct leg and the inner mouth feeds the shoulder wrap.** That is the independent reviewer's reading at about 3.96 s. My whole-frame reading of t1p5 and t2p5 is consistent with it, but I can't confirm it independently at that resolution.
- **"Impressively resistant to rotation"** (product page) fits a crossed layout, with one leg leaving each face at each end. It doesn't fit the current both-legs-from-F graph. This supports the reading but doesn't prove it.

## 3. Is F_outer ↔ B_inner established?
No. It isn't manufacturer fact, and it isn't unknowable either. It's a conditional inference, labeled as an inferred display adaptation. It follows only if four assumptions hold:
- **P1:** the four straight F↔B bores in the current shape. These are inherited, authored display estimates, not approved geometry or threading.
- **P2:** one continuous cord per end, with both ends free and no joint on the board. The footage supports this.
- **P3:** minimal winding: one exterior pass, no extra turns.
- **P4:** the B-face roles above (outer is a leg, inner is the wrap).

If those hold, the pairing is forced:
1. The B_outer bore exits at F_outer, and the B_inner bore exits at F_inner.
2. The wrap leaving B_inner must land on an F mouth.
3. Landing on F_inner would make B_inner → bore → F_inner → wrap → B_inner a closed ring with no free ends, which a cord can't be.
4. So the wrap lands on F_outer, and F_inner is the second leg.

The alternatives fall away:
- A stitch on the B face (the current graph) or on the F face contradicts the observed wraps.
- The mirror-image crossing contradicts P4.

If the bores or the mouth roles change, the pairing has to be worked out again.

## 4. Has root over-constrained the evidence requirement?
Partly. AGENTS.md forbids presenting invented hidden connectivity as sourced; it doesn't forbid an explicitly labeled inference. The boundary:

**Allowed with honest labels:**
- The crossed pairing, labeled "inferred from visible B-face roles under the current authored bore estimates; internal passage, continuity and contact order not observed".
- Display estimates such as radius, anchor offset and lengths.
- The segment's rest length. A segment is drawn as the native shortest path between its two stations (`native_cord_routes.py:756`), so rest length doesn't change how it looks; it only has to make the feasibility ratio come out at or below 1 at the base pose (lines 790–802).
  - Use the solved length plus a small margin, labeled "tight-wrap display estimate".
  - Drop the "130–150 mm experiment" framing. My rough expectation is about 105–110 mm: about a 149° arc over the crown at roughly a 40 mm offset radius.

**Not allowed:**
- Calling the pairing, internal passage or over/under order sourced.
- Adding surface waypoints or extra stations.
- Forcing a wrap side that the geometry doesn't produce.

## 5. Smallest faithful graph
Per end, mirrored left and right. Keep the four poses, 12 transitions, seven contact IDs, FCStd, USDZ, anchor and radius unchanged.
- **Lead at B_outer:** left (.017, .048, .0013393944404); right (.483, …).
- **Lead at F_inner:** left (.031, .048, .0746606055596); right (.469, …).
- **Segment F_outer → B_inner:** left (.017, …, F) → (.031, …, B); right (.483, …, F) → (.469, …, B).
  - Plane normal about [.982254610884, 0, ±.187552337754]. That plane passes through both real mouths and contains body +Y; check the sign at each end.
  - This is attachment metadata, not a drawn route.
- **Remove** `left-rear-return` and `right-rear-return`. Rewrite the provenance strings with the label from section 4, and record P1–P4 and the deduction in `geometry-authoring-notes.md`.
- **Leave the descriptor alone.** This is a suspension-only change with FCStd, USDZ and contacts unchanged, so don't rewrite the descriptor artificially.

**The wrap side comes from the geometry, not from authoring.** The authored bores sit 10 mm toward +Y, so the shortest path between opposite mouths goes over the +Y crown (about 149°, versus about 211° the other way).
- In two-edge-upright (identity rotation, support at +Y), that puts the wrap on the support side, which matches the hanging footage.
- The segment is solved once in body space, so the wrap stays on the same side of the wood in every pose, as a captured cord would.
- In three-edge-upright the crown faces down. FlashBoard2 is consistent with that, but loaded footage doesn't show it.

## 6. What to do if the existing solver can't handle it
- **If the solve passes** the clearance, tube-intersection and settle checks, accept it as a display approximation.
- **If it fails with `native cord tubes intersect`** (a leg crossing the wrap near the crown), the missing piece is a strand-over-strand contract: a lead allowed to rest on a certified segment's tube.
  - That would mean extending `reserve_tube`, which today only handles parallel collar tubes, to oblique segment tubes, with an explicitly labeled bearing order. Build it as a tested solver extension.
  - Don't nudge stations, add waypoints, shorten the wrap or go back to stitches to get around the failure.
- **Planar caveat:** in an oblique plane the segment is an ellipse arc rather than the true helical shortest path. Over a 14 mm offset the difference is negligible, but report it as a planar approximation.

## 7. Next steps for root
1. Implement the section 5 graph with the labels from section 4.
2. Run `solve_threaded_rope.py --apply`, then `--check --report <owned path>` for all four poses. Confirm the segments pass over the +Y crown, the length ratios are below 1, and there's no solid or tube intersection.
3. Render whole matched-depth front, side, top and reverse-oblique previews for each pose next to the prior committed asset, and show them before reporting done.
4. Keep shape acceptance, hidden continuity, contact order and runtime appearance explicitly pending.
