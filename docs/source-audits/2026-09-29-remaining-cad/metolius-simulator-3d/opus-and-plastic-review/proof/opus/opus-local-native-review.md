## Native export gate for #8: pass, okay to export

Both fixes hold up in the native section data, not just the renders. I found no source-supported blocker, and the user's two functional fixes are still in place. I used the five comparison images, the nine-panel section plot, the high-front and rear views, and `native-sections.json`. Every number below comes from the CAD section data, not from pixels.

### N1 (step on the dome face above #15): fixed
- At X = 0, 30 and 46 mm, every section reaches the front at Y = −94, and none has a horizontal step at the front anymore. The old 6.3 mm shelf at Z = 187 is gone.
- **X = 0:** the cap curves down to Z ≈ 182.8 with a rounded front edge (roughly 5 mm radius from a rough fit). It then turns directly into the roof of pocket #15. There is no groove or overhang.
- **X = 30 and 46:** the cap runs down into a near-vertical front face, then back into the existing face relief. Your join report puts the angle change at these joins at about 2° or less.
- In the front and high-front views, the line across the dome face is gone. The dome reads as a rounded cap rolling into #15's mouth, which matches both sources.
- #15 keeps its 50 mm depth. The pocket's upper lip is thin right at the front, but it thickens quickly as the cap rises behind it.
- The fixes from the earlier round are unchanged: the crest runs left to right about 66 mm from the wall, with the rear slope falling toward the wall. The rear-center view still shows a smooth hump.

### N2 (sharp front edge on the flat sloper): fixed
- At X = 185.1, 210 and 235 mm, the sharp point is now a real rounded edge. A rough fit gives about 2.6–3.5 mm radius, against about 4.6 mm on the round sloper (X = 95). The straight top behind it is unchanged.
- That keeps the two slopers distinct: the flat one has a straight top and a tighter front edge, and the round one has a convex top. The roll sizes are your labeled display adaptations; the sources don't give a radius.
- The contact bands are still anchored at the front: flat from Y −94 to −39 (55 mm), round from −94 to −29 (65 mm). The join at X = 148.1 is still a clean in-between shape.
- In the oblique and raking views, the roof now rolls over the whole front edge with no crisp line.

### Contacts
- X = 46 now belongs to #14, with the exact split at X = 47 that your report confirms.
- Your independent reports keep all 30 contacts non-overlapping and all 27 depths passing.

## Things to inspect in the final colored app frames (not blockers)
1. **Front edge near the outer-jug saddles (X ≈ 238–278 mm):** the top view still shows small dark marks there, and they survived the roll fix. No section covers this zone. In a close front or high-front orbit, look for a dent or crease where the flat sloper's front edge meets the outer jug's rounder front. If it shows, add one or two native sections there and smooth it locally.
2. **Flat sloper front edge:** it should read as a rolled edge in color, not a crisp line. If it still reads as an edge, the next step is a larger roll, again labeled as an adaptation.
3. **Dome face over #15:** from the front and high-front, check for any dark band or line across the dome, and that #15's upper lip doesn't look like a knife edge.
4. **Faint dark lines on the flat back face** in the rear-oblique view. These are unchanged from before. In any orbit that shows the back, make sure there's no visible seam or sliver.
5. **Rear-leaning orbit:** the #14 hump and its rear slope should be smooth, with no ridge or shading break.
6. **Highlights:**
   - #2 and #3 should light only their front 55 and 65 mm bands, and reach the front edge.
   - #14 should light its cap down to the front edge, but not #15.
   - #1 should light its whole top.
   - Deselecting a hold should bring mint back everywhere.
7. **Plastic finish (later):** every board surface mint, with no grey left over and no banding or faceting on the new curved surfaces. Faceting on the outer-jug lobes is inherited from the original. Also confirm the exported USDZ has no materials and the plastic manifest is unchanged.

I didn't edit, create or delete any files, and every shell command started with `rtk proxy`.
