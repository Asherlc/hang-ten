## Native export gate for #8: not yet, two small fixes first

The new geometry fixes both problems the user raised, but the correction introduced two small, local defects that the sources contradict. Both are cheap to fix natively, so I'd fix them before the costly export rather than after.

### The two user blockers: resolved

**Center jug #14: the rear ridge is gone.**
- In the X = 0 and X = 30 mm sections, the highest line now runs left to right at about Y = −66 mm. It's 222 mm high at the center and 215 mm at X = 30, falling to about 192 mm at the base (X = 46).
- Behind the crest, the top drops roughly 35 mm at the center (about 27 mm at X = 30) into a shallow trough, then runs level to the wall. Fingers coming over the crest land on a surface that falls toward the wall, which is a positive grip.
- The crest sits about 66 mm from the wall, so fingers can reach behind it.
- The rear-center and rear-oblique views show a smooth rounded hump with no front-to-back spine.

**Dome width and pocket #15: kept.**
- From the front, the dome is still the full-width round cap: same 222 mm top, same base width.
- Its shoulders at X = 30 are a few mm lower than the original curve. It still reads as the sourced rounded dome.
- #15's roof is intact at Z = 180.5 mm and runs back to Y = −44, so it's still 50 mm deep from the front.

**Slopers: they now reach the front.**
- The roof reaches Y = −94 across the whole width, flush with the jugs and the dome. The top view now shows one straight front edge.
- The contact areas are anchored at the front, as I recommended:

  | Hold | Contact span (Y, mm) | Depth |
  |---|---|---|
  | Flat sloper #2 | −94 to −39 | 55 mm |
  | Round sloper #3 | −94 to −29 | 65 mm |

- Both depths are measured from the front edge, as recommended, and the remaining roof behind each band isn't tagged.
- The flat and round slopers still differ. The flat one has a straight top falling about 10° toward the front. The round one has a convex top with a rolled front edge.
- The join section at X = 148 mm sits cleanly between the two shapes, and the front view shows one continuous roof line.

**Contact coverage:**
- #14 and both #1 jugs are tagged across their whole top, from front to wall.
- Your independent reports pass non-overlap and keep all 30 contacts, the 27 depths and the 711 × 222 mm face.

### New blocker N1: a step across the dome face above #15

I confirmed this in the section data, not just the plots:
- At X = 0, 30 and 46 mm, the new cap's front ends in a vertical lip about 3 mm tall (Z 190 → 187).
- Under it, a horizontal shelf at Z = 187 runs back about 6.3 mm (Y −94 → −87.7) to the old dome face.
- At X = 30 the old face then comes forward again to Y −93.8 by Z = 172. That leaves a groove under an overhanging lip across the full width of the dome.

The cap was set on top of the old dome face without being blended into it. Both sources show the dome face rolling smoothly from #15's rim up over the top. It also shows as a horizontal line across the dome in the front comparison and probably causes the dark specks at the dome base in the high-front view. This is exactly the kind of "jagged" detail the user first complained about.

**Fix:** carry the cap's front surface down to meet the existing face smoothly, somewhere between about Z = 172 and 187, with no shelf and no undercut. Keep #15's 50 mm depth and the material above its roof.

### New blocker N2: the flat sloper's front edge is a sharp wedge

- At X = 210 mm, the flat top (falling about 10° toward the front) meets the front face (going back and down at about 39°) at one sharp point at (−94, 152.55). That makes a wedge of about 49°, with no rounding.
- The round sloper has a rolled front edge. The flat one's 55 mm contact now ends right at that sharp edge, so in practice it grips like an edge, not a "flat sloper."
- The diagram and photo show the top band rolling into the face.
- It may be inherited from the old front face, since the original side view had a forward "beak." But it only became the sloper's grip edge with this change.

**Fix:** round off the flat sloper's front edge, labeled as a display adaptation. Keep the straight top so it still reads differently from the round sloper, and keep the 55 mm contact measured from the front. Also check the joins into the X = 148 blend and the outer-jug saddle. The dark marks on the front edge near the saddles in the top view probably come from this sharp edge meeting the rounded jug front.

### After the two fixes
Re-send sections at X = 0, 30 and 46 (dome face), at 210 plus one each near 185 and 235 (flat front edge), and front and high-front views. Then re-run the 27 depth checks: #15 and the #5/#6 edges sit right under the changed areas. Re-run contact non-overlap too. If those come back clean, I'd pass the native gate without re-reviewing everything else.

### Accepted as labeled adaptations
- **Outer jugs #1:** flat, level tops (Z ≈ 180 at the center, ≈ 174 at the side) with a small slope down at the back. That's a positive hold. The extra manufacturer sources show no cupped top, so this isn't a blocker.
- **Dome shape from the side:** the bell profile, crest position, back slope and thickness are your display adaptations. With no manufacturer view of the back, that labeling is correct.

### Cosmetic watch items
- Faint dark lines on the flat back face in the rear-oblique view. Check it's not a sliver or seam.
- Faceting on the outer-jug lobes, inherited from the original.
- Shading bands on the dome cap in the top view, and the specks noted above.

### Required app checks after export
- Colored frames from the front, high-front, a rear-leaning orbit and an end-on orbit:
  - no line across the dome face
  - the dome reads as a rounded hump from behind
  - the slopers meet the front flush
  - no seams or specks
- Highlights:
  - #2 and #3 light only the front 55 mm and 65 mm bands
  - #14 and #1 light their whole tops
  - deselecting restores mint everywhere
- The USDZ still has no materials. I'm not judging the plastic appearance until the final colored captures.

I didn't edit, create or delete any files; every shell command started with `rtk proxy`.
