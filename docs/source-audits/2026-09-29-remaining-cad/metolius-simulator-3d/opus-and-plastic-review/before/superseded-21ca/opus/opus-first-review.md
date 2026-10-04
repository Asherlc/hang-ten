## Board #8 (Metolius Simulator 3‑D): not ready for human review yet

My verdict is **corrections needed**. I can't give the plastic appearance judgment until the colored captures arrive.

I compared the two manufacturer images (`product-01.jpg`, `product-03.jpg`) and the product page against all five native before/after pairs, the combined front/side/top sheet, and the fresh app frames (deep-pocket, flat-left-orbit and round-center-orbit before and after, plus the combined jug-left-orbit sheet). I only looked at whole images; nothing was measured or traced.

### Blocker: the center jug (#14) has the wrong shape
- **Source:** both manufacturer images show #14 as a dome that is round on top and keeps its full width. Its sides drop almost straight down into the roof, and the 50 mm pocket (#15) sits well inside it.
- **Before (ca5024c3):** the jug matched that: a clean half-circle from the front.
- **After:** from the front it now looks like a peaked tent. The sides slope at roughly 45°, the rounded top is about as wide as pocket #15, and the jug looks pointed. The top view agrees: its upper face has narrowed into a pointed trapezoid. The app confirms it: in the after deep‑pocket frame the jug is clearly peaked, where the before frame shows a rounded hump.
- **Cause:** the new shoulder bridges appear to climb up the jug's sides instead of ending at its base.
- **Why it's a regression:** this is new in the change and contradicts the source. Nothing in the validation files checks the jug's shape; the "rounded outline joins 0°" proof covers the outline joins only.
- **Fix:** restore the round dome. Keep any blend as a concave fillet at the bottom of the dome. Pocket #15 and contact IDs shouldn't need to change.

### Recommended correction: the joins between sloper zones 2 and 3
- **Source:** in the diagram, the top edge over the flat slopers (2) and round slopers (3) is one continuous arc; only the shading changes. The photo also shows an unbroken roof. The 55 mm vs 65 mm depth difference is real, so some transition is justified.
- **After:** the old 17–18 mm vertical steps are gone, which is a real improvement. But each join now has a short pinched dip:
  - a kink in the front outline;
  - dark V notches along the back edge in the top view;
  - clear dents in the oblique and raking views, and in the app's flat-left and round-center orbits.
- The board still reads as notched, which is likely what "Jagged" was about. Nothing in the sources shows a dip there.
- **Fix:** spread the depth change over a longer, gentle blend. I'm moderately confident on this one: the source doesn't give the exact transition length, so I'd treat it as a correction rather than a hard blocker.

### Improvements to keep
- The concave curves from the outer jugs (#1) down into the slopers (#2) now match the curved saddle in both source images. The old boxy steps and sharp edges are gone.
- The front face is unchanged from before: the 30 contacts, the hold grid and the side profile.

### Cosmetic limits not caused by this change
- The outer jug lobes show coarse faceting in both the before and after renders.
- The 94.12 mm thickness is a display estimate.
- The CPU preview's dark bands are a renderer issue; the app is the authority.
- In the after oblique there is a small dark sliver near the left join between #1 and #2. It may be a tiny surface defect, so please check it in the colored frames.

### Plastic appearance: groundwork only, judgment after the new captures
- **The approach fits policy.** `BoardModelRealityTypes.swift` maps `display.surfaceFinish` to `plasticMaterial` at runtime: mint, roughness 0.78, and a faint stipple that fades out at small sizes. The USDZ stays unbound, as required.
- **The sourcing is reasonable.** The product page lists only "White/Black Swirl" and "White/Blue Swirl" colors and never names a material. The photo shows a molded, cast-hold surface, so "plastic" fits as a finish category. The code already labels the mint as the app's palette, not the product's color. The swirl itself can't be shown, because textures aren't allowed.
- **What I'll check in the colored frames:**
  1. Every board surface turns mint, with no leftover grey parts (only attachment parts should stay neutral).
  2. The red highlight stands out against mint, and deselecting a hold brings the mint back.
  3. How the jug and the 2/3 joins look in color. Colored shading will probably make them more visible, not less.
  4. No banding or faceting on the bridges, and whether the dark sliver near the left #1/#2 join is a real flaw.
  5. Only the finish metadata changed: the model SHA should still be `c87d2acf…`, with the change confined to the FCStd manifest and descriptor.

I didn't edit any files or run any tools that build or test. The queue is unchanged: #1–7 accepted, #8 pending.
