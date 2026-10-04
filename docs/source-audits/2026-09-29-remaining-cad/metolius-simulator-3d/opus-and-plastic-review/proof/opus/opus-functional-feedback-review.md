## Native geometry gate for board #8: fail

The new human feedback reverses my previous pass, and I agree with it. There are two blockers, each backed by the manufacturer's labels or images plus the user's hands-on report. The images alone can't show the back of the center jug, so I've separated what they show from what needs native sections.

My previous pass was too narrow. I checked #14's front outline and its width from above against the sources, and confirmed the slopers' 2/3 joins were smooth. I didn't check whether the jug's depth profile can actually be gripped, or how far forward the slopers reach. The fixes from that pass still stand: the round full-width dome front, the smooth 2/3 joins, the outer saddles and the lower outline.

### Blocker 1: center jug #14 can't be gripped (inherited, not caused by the recent fixes)

**What the current native renders show:**
- **Side:** the dome's top climbs from its front toward the wall and is highest at the back plate. A hand coming over the top meets a surface that slopes down toward the climber.
- **Top:** the dome's lit upper face is wide at the front and narrows toward the wall. Steep dark sides run the full depth.
- **Oblique and raking:** the dome's round front outline looks like it was carried straight back to the wall. That makes the top a rounded crest running front-to-back, rising as it goes back, which matches the user's "ridge going down the back."
- **Original 9449:** its side view has the same rising dome profile. So this came from the original migration, not from Opus's corrections. The rejected 8fa version made it worse.

**What the sources support:**
- The diagram legend calls #14 a "center jug" and puts the 50 mm 3-finger pocket (#15) in its face. A jug is a positive hold you wrap your fingers over. A spine that rises toward the wall works against that, so the requirement has a source behind it.
- Both images are taken from the front. Neither shows #14's top or back.

**What the images can't settle:**
- Whether the crest is a sharp crease or a rounded one.
- How steeply the top rises toward the wall.
- Whether any finger room exists behind the crest.
- What the real jug looks like at the back: a level rounded top, an incut lip, or a recess behind.

**Native sections that would settle it:**
1. **Front-to-back cuts at the dome's center, partway out and near its edges:** where is the highest point (front or wall)? Does the top rise toward the wall? Is there a crease along the centerline?
2. **Side-to-side cuts at several depths from front to wall:** does the arch stay a full-width rounded top, or pinch into a peak toward the back?
3. **Surface-angle check along the dome's centerline:** a crease or near-crease here confirms a ridge.
4. **Finger room:** after any fix, does a band of top surface running left to right exist that is level or slopes down toward the wall? Does #14's contact area sit on that band rather than on a crest?
5. **#15 regression check:** the 50 mm depth of pocket #15 still holds.

**Fix (must be labeled as an adaptation):**
- Keep the sourced front outline.
- Rework the depth profile so the top's highest line runs left to right near the front, and the top is level or falls toward the wall.
- Don't present any incut size as sourced.

Before choosing the profile, retain and inspect more manufacturer evidence. The product page links three items that aren't in the retained sources: `Training-Board-instructions.pdf`, `Training-Board-comparison.jpg` and a video thumbnail. Any of them might show a side or back view.

### Blocker 2: slopers #2 and #3 stop short of the front

**Sources:**
- In the diagram, the 2/3 top band rolls straight down into the face above the 5/6/7 edges, with no ledge or setback.
- In the photo, the swirl pattern flows unbroken from the top band over the front.
- The jugs rise above the roof in height, but nothing in either image shows the slopers recessed behind them.
- The user confirms the slopers should reach the front.

**Current model:**
- The design record measures the 65 mm round and 55 mm flat "support depths" outward from the wall.
- In the top view, the slopers' front edge sits visibly behind the front of the outer jugs and the dome.
- The oblique and raking views show a crease where the roof meets the steep face, and the deeper round zone stands forward of the flat zone as a block (now blended over X 110–185 mm).
- So with a ~94 mm display thickness, the front part of the board's top isn't sloper surface.

**Reconciling the published depths with the user's feedback:**
- The 55 mm and 65 mm figures are sourced and must not change.
- Three things are not sourced: the ~94 mm thickness, the front setback, and measuring from the wall.
- A hand meets a sloper at its front edge, so the grip depth should be measured from the front edge backward.
- **Recommended:**
  - Carry the sloper surface forward until it's flush with the front of the jugs and dome, with no step or crease.
  - Measure the 55/65 mm depth from that front edge back along the top.
  - Put #2/#3's contact areas on that front-anchored band.
  - Record this as a labeled interpretation in the source audit.
- The alternative is shrinking the sloper zones so wall-to-front equals 55/65 mm. That keeps the slopers behind the jugs, which is the setback the user objects to, and nothing in the sources supports it.

**Native sections needed:**
1. **Front-to-back cuts in the middle of the flat zone, the middle of the round zone, and the 110–185 mm transition:** compare the sloper's front edge with the front of the jugs and dome and with the face directly below. Check for a ledge or crease, and that the flat and round shapes still differ.
2. **Depth measurements:** 55 and 65 mm measured from the front edge backward.
3. **Edge depths:** recheck the 25, 19 and 36 mm depths of edges #5, #6 and #7, since the face above them moves.
4. **Contact areas:** confirm #2/#3 cover the front-anchored band.

### Watch item, not a blocker yet
The outer jugs (#1) look like rounded lobes in the native views. In the photo, the left lobe might have a cupped top, but the swirl pattern makes that impossible to judge. Since they're also jugs, run the same grip sections on #1.

### Material
The plastic tag is authorized, and the mint is only the app's display color. The product page names color variants (White/Black and White/Blue Swirl) but no material chemistry, so the audit shouldn't claim one. I'm still not judging app appearance.

**Next gate:** the rear oblique view plus the dome and sloper sections above, showing #14 with a grippable top and finger room and the slopers flush to the front with front-anchored 55/65 mm depths. After that, the 30 contacts and all 27 depth checks need rebuilding and checking again.

I didn't edit, create or delete any files, and every shell command started with `rtk proxy`.
