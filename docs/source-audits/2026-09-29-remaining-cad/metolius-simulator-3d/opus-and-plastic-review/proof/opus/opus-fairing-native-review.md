## Native shape gate for b722: okay to export

The repeated bands are gone. The front-fairing fix doesn't regress the front, dome or slopers, and I see no source-supported blocker. There is one new mark on the back face to check during export (item 1 below). I'm not giving app or plastic acceptance, and human acceptance of #8 is still the user's call.

### The "wavy" bands: resolved
- **Profile and lean plots (from source coordinates):**
  - The previous version's lean swung from about 0° to about 30° at every profile point between Z 147 and 0 mm.
  - The new version stays a near-steady 18–23° from about Z 125 down, passing through the same points.
  - Lean is continuous where the new lower curves meet the protected upper zone at Z 135.
- **Side view:** the lower face silhouette is now a smooth straight taper. The staircase wiggles are gone. Silhouette is the shading-independent proof.
- **Front, oblique and raking views:** the full-width horizontal stripes are gone. The hold layout is unchanged; the frozen 3ff3 and b722 front views match hole for hole.
- **Sources:** this now matches the manufacturer diagram's smooth tapering face, with holds following the board's arc and no terraces crossing the rows.

### Hold rims: nothing lost, one old limit
The rounded mouth shapes are unchanged. The mouth edges were never rounded off in this CAD, and that's true of 9449 and 3ff3 as well. The old bands made the holds look like they sat on ribs. Without them the holds read as cleaner slots in a smooth face, which is more faithful.

The diagram shows a soft bevel around each hold, so missing mouth-edge rounding remains an inherited limit, not a regression. If the user later finds the holds too plain, a small rounding on the mouth edges, labeled as an adaptation, is a separate follow-up.

### The one remaining band below the sloper fronts: acceptable
- It's the protected 170→147 mm undercut below the sloper fronts, plus one vertical point at Z 147.
- In the native front view it shows as a darker band under the roll, with a faint light line just above the top row of holds. It's most visible as a lens shape under the dome.
- The sources show one transition there: the 2/3 sloper band turning down into the face above #5–#7. A single band there is credible. The repeated ones weren't.
- **App check:** confirm the faint light line at Z 147 reads as the underside of the roll, not a crease. If it reads as a crease, re-smooth that point later, but only with fresh grip and depth checks, because the zone is protected.

### Front, dome and slopers: preserved
- The new grip sections match the accepted 3ff3 sections:
  - forward crest about 66 mm out, with the rear slope falling toward the wall
  - #14's cap rolling into #15's 50 mm mouth
  - #2 and #3 bands anchored at the front (55 and 65 mm)
  - rolled front edges on both slopers
  - the cut between #14 and #3 exactly at X = 47
- Front, high-front and the rear-center view of the dome are unchanged.
- Your report finds no difference above Z 135 when comparing the old and new upper geometry in both directions. The 3.7 mm³ difference in the raw volume totals, with no actual geometric difference, is calculation noise at about one part in a million of the board's volume. Keeping it on record is correct.
- The per-pocket void check is the right guard against the pocket #13 fill that the rejected probes hit silently.

### The 7.16° normal mismatch: sound disposition
- I checked the diagnosis myself. The corner sits on the flat sloper's front roll near X −174. It's about 0.013 mm behind the front-most line and about 0.33 mm below it.
- The triangle belongs to face 53 (index 52), the face that generated it. That corner lies inside face 53 and projects back onto it essentially exactly.
- The old heuristic picks face 26 (index 25) instead, because the triangle's centroid sits closer to the two faces' shared edge. The corner sits 0.2 mm off face 26, so its normal snaps to that edge, where the surface faces straight forward.
- On a roll of roughly 3 mm radius, a point 0.33 mm below the front line should face about 6–7° downward. So the face-53 normal of 7.16° is physically right, and the old heuristic is wrong here.
- At the two corners that sit on the shared edge, both faces give identical normals. So the faces meet smoothly there, which rules out the earlier genuine C0-knot/inverse-side bug.
- **The fix is sound:**
  - Keep the raw mismatch on record.
  - Add a strict check comparing each corner against the analytic normal of the face that actually generated its triangle, requiring the corner to project back onto that face with near-zero error.
  - Add this exact triangle as a regression case.
  - Don't treat agreement with the old heuristic as proof of correctness when it picks a different face. Keep all thresholds unchanged.
- **Visual note:** this triangle is a long, very thin sliver along the flat sloper's front edge. With correct normals it should shade fine. In the colored frames, check for a hairline along the flat sloper fronts.

### Checks for export and the app (not native blockers)
1. **Back face:** a dark triangular mark now appears near the bottom center of the flat back in the rear-oblique view. It wasn't in 3ff3's rear-oblique. The faint dark lines from before also remain. The mesh is watertight and consistent, so this is probably a thin triangle in the preview. Still, check the back face in the export (one flat face, every normal pointing to the wall side) and in a rear orbit in the app.
2. The faint line at Z 147 under the slopers and dome, from the section above.
3. Hairline shading along the flat sloper front edges.
4. Re-run all seven watch items on the new export.
5. The highlight teeth stay a separately documented cosmetic limit.

**Remaining labeled estimates:** the profile points and lower lean, thickness, the edge rolls, how far forward things sit, the jug cap and its rear slope, the missing mouth-edge rounding, and the mint palette.

I didn't edit, create or delete any files, and every shell command started with `rtk proxy`.
