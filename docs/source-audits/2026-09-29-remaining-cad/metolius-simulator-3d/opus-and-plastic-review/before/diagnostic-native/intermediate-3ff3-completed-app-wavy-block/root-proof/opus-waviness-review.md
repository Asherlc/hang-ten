Status: I've finished reading the shell code and the app frames, and the side silhouettes confirm the waviness is real geometry. Here is the full diagnosis.

## Verdict: not ready for human acceptance

There is one geometry blocker: the "wavy" bands. It's a real, inherited flaw in the CAD side profile, not a lighting effect, and nothing in the sources supports it. The fix is small and localized. The seven watch items mostly pass, but the app shows small jagged edges on some highlights. I'm not accepting the board on the user's behalf.

## 1. What causes the waviness

**It's real geometry, created by how the side profile was drawn.** In `shell()`, each segment between two profile points is a cubic whose control points sit straight above and below its endpoints (same depth). So the face goes exactly vertical at every point, leans furthest back midway between points, then goes vertical again at the next point. Working from your profile points (not from pixels):
- Below Z = 147 mm, each segment recedes 10–14 mm over 28–33 mm of height. That's an average lean of roughly 18–23°.
- Within each segment, the lean swings from 0° at each point to roughly 27–32° in the middle (1.5× the average), then back to 0°.
- From Z = 170 to 147 the swing is about 0° → 50° → 0°.

As a result, the face's lean swings back and forth about every 30 mm, at Z = 147, 117, 87, 59 and 29 mm. The surface itself sits only about ±1–1.4 mm away from a smooth taper. The angle swings are what catch the light.

**Why it's geometry, not lighting or normals:**
- The end-on silhouettes show matching wiggles in the native side view (all three columns, original 9449 included) and in the app's end-on frame. Silhouettes can't come from shading.
- The bands are perfectly straight, constant-height lines across the whole width, matching the profile being extruded across X. They don't follow triangle edges, UV seams, or the curve of the hold rows.
- The flat-shaded CPU previews show the same bands, so the UV-node normal setting isn't causing them. It just reports the real curvature accurately. The matte mint finish and the light from above-front make it more visible, but don't create it.

**It's inherited, not caused by recent fixes.** Original 9449 has the same staircase silhouette, and none of the grip fixes touched the lower face.

**The sources don't support it.**
- The manufacturer's diagram shows a smooth, tapering face. Each hold has its own rounded rim, and the rows follow the board's arc.
- The photo's ridges are hold lips that follow the arc too.
- Neither image shows straight horizontal terraces cutting across the curved rows. In the app, the bands cross the rows near the ends of the board, and that's the "wavy" look the user noticed.
- The profile points themselves are display estimates. The zero-lean rule at each point is a drawing artifact, not a design choice.

## 2. Smallest fix

- **Keep all nine profile points exactly as they are.** Only change the rule for the curve between them: instead of forcing the face vertical at each point, run one smooth curve through them that never doubles back on itself.
- **Leave two places vertical:**
  - Z = 170, the most forward point (pocket #15's centre height, just under the slopers' front edges). The face is genuinely vertical there.
  - The top and bottom ends.
- **Expected effect:**
  - The face moves by about 1.4 mm at most.
  - The lower face's lean becomes nearly steady at about 18–23°.
  - The overall taper, thickness, outline and 711 × 222 mm face stay the same.
- **Optional, to leave the grip fixes completely untouched:** keep the 170→147 segment as it is and smooth only from Z = 147 down. That leaves one soft band just under the top row. The full fix also gently changes the undercut below the outer jugs and the dome. The sloper and dome grip tops don't use this profile.
- **Don't** invent a factory side profile, add rib shapes that follow the rows, or remove the taper. Label the change as fixing a drawing artifact; the points stay display estimates.
- **The pockets** are cut separately (the same mouth sizes and corner radii), so their rounded rims carry over. But the floors are measured from the face, so the face moving by up to ~1.4 mm means everything needs re-checking:
  - all 27 published depths
  - all 30 contacts and their non-overlap
  - fresh grip sections at X = 0, 30, 46, 95, 148, 185, 210 and 235 mm
  - a native side view (the silhouette should be a smooth taper)
  - export, then the same app frames again (front, both orbits, end-on)

## 3. The seven watch items in the mint app frames

I looked at: unselected, jug-left-orbit, jug-to-flat-restored-mint, flat-left, round-center-orbit, deep-pocket, shallow-edge, and all four center-jug frames. I didn't open the after-captures versions of jug-left, jug-left-orbit, flat-left-orbit and round-center, or the finish-checks jug-left.

1. **Outer saddles and front crease: passes, with a limit.** The saddles read as smooth curves. A faint shading crease shows where each saddle meets the front edge in the front and high-front frames. It's small and not a blocker.
2. **Flat sloper front edge: passes.** It reads as a soft rolled edge with darker shading under it, not a knife edge.
3. **Dome above #15: passes.** There's no line across the dome face. In deep-pocket, #15's highlight is a clean rounded rectangle and its upper lip looks fine.
4. **Back seams and rear ridge: passes.** In the rear-leaning frame the back is uniform with no visible seams, and #14 is a smooth hump with no ridge. The end-on frame shows the crest-then-rear-slope profile.
5. **55 and 65 mm sloper highlights: band placement passes, but the edges have teeth.**
   - #2 and #3 light front bands that reach the front edge.
   - The flat band's inner end, near the X = 148 split, has a small stepped notch (jug-to-flat frame).
   - The round band's outer ends are jagged like a saw (round-center-orbit).
   - #14's lower edge looks ragged at the front (end-on frame).
   - These look like the edge following coarse triangles in the blend zones. They're cosmetic, but visible whenever those holds are selected. Given the earlier "Jagged" feedback, I'd fix them if it's cheap, for example with finer tessellation of the blend or a split that lines up with a surface boundary. They're not a blocker on their own.
6. **#14 cap excludes #15: passes.** In high-front and the center view, only the cap is red and #15 stays mint.
7. **Mint everywhere, restored after deselection: passes.** Every surface is mint with no grey patches, and #1 returns to mint after switching to #2 on the same screen.

The edge highlight on #11 (shallow-edge) is clean.

## Remaining limits once the face is fixed

- The highlight teeth above, unless fixed.
- The faint creases at the saddles.
- Inherited faceting on the outer-jug lobes.
- Display estimates throughout: thickness, the profile points, how far forward things sit, the rolls, the rear slope behind the crest, and the jug cap.
- Mint is the app's palette. The real product is a white/black or white/blue swirl, and its material isn't stated.

**The next gate** is the smoothed face: a native side view, the re-run checks, and fresh app frames showing no horizontal bands. After that, the board goes to the user for their own acceptance.

I didn't edit, create or delete any files, and every shell command started with `rtk proxy`.
