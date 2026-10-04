## Native geometry gate for #8: pass, okay to export

Both blockers I raised are fixed in the corrected native renders, and I see no remaining blocker the sources would justify. I judged the five three-column comparison images by eye against `product-01.jpg` and `product-03.jpg`, without measuring anything.

### 1. Center jug #14: fixed
- **Front:** the dome is a half-circle again, with near-vertical sides dropping into the roof. It matches the original 9449 outline and both source images. The pointed tent from the rejected 8fa version is gone.
- **Top:** the dome's upper face is back to the original wide trapezoid, not the narrow pointed one from 8fa.
- **Oblique and raking:** the dome looks rounded, with a slight curve only at its base. The bridges no longer run up its sides.
- **Side:** the outline matches the original, with no peak.

### 2. Joins between flat (2) and round (3) slopers: fixed
- **Front:** the roof from each outer-jug saddle to the dome is now one gently rising line, matching the single arc in `product-03`. There's no kink and no step.
- **Top:** the back edge is continuous. The dark V notches from 8fa are gone, and the 2→3 depth change is a long, shallow blend.
- **Oblique and raking:** the pinched dents are gone, and the roof reads as one continuous surface, close to the photo.
- The longer blend span is a reasonable choice. Its exact extent is your display estimate, and the sources neither support nor contradict it.

### 3. Things that should be kept: kept
- The outer-jug curves into #2 are unchanged from the accepted 8fa version and still match both sources.
- The rounded lower outline, the face grid and the hold layout look unchanged.

## Watch items (cosmetic, not source-based blockers)
- **Faint dashed lines on the roof (front view):** they run along the roof on both sides of the dome, roughly where the new blends are. They look like seams or very thin faces in the mesh rather than intended shape.
- **Dark specks and a diagonal shading streak (oblique and raking):** small dark specks sit along the front edge of the roof near the left saddle and the dome base. A faint diagonal streak or crease crosses the right roof, and the raking view shows a mild shading change near the dome's base on the left.

These may just be the CPU preview's faceting, which already showed dark bands before. Check them in the exported mesh and the colored app frames. If they show up there as visible creases or sharp lines, that's a smoothing fix to make before human review, not a source correction.

## Still needed before I'd call #8 ready for human review
- The 30 contacts rebuilt, plus fresh independent checks of the 27 depths, the 711 × 222 mm face, the thickness estimate and the outline. The `8fa` geometry checks don't carry over, because the BRep changed.
- Confirmation that the canonical FCStd still has `surfaceFinish: "plastic"` and that only geometry changed from `3c516ec2…`. The probe file is scratch, so this needs checking once the change is canonical.
- The exported model with the CPU-preview items above checked, and the colored app frames. I'm not judging the app appearance yet, as you asked.

I didn't edit, create or delete any files, and I didn't run any shell commands this round.
