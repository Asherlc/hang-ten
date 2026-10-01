I checked the plastic metadata proof and it holds up. My geometry recommendations stand as given.

**What the proof shows** (`metadata-preservation.json`)
- Status is pass, and the script exited cleanly.
- Only `Document.xml` changed inside the FCStd. All 387 BRep entries and every other archive entry are byte-identical to the `8fa07c…` source, and it reports `geometryChanged: false`.
- The only changed manifest field is `/presentations/0/media/display/surfaceFinish`, now `"plastic"`. The model (`c87d2acf…`) and descriptor (`3aba3cf5…`) are unchanged. All 30 contacts, the other manifest fields and the 203 other package files are unchanged.
- It says plainly that mint is the app's palette, not a manufacturer color, which is the right label.

**Things to watch in the follow-up**
1. **The plastic tag has to survive the geometry fix.** The fix will change the FCStd, model and descriptor hashes again. Please confirm the corrected source still has `surfaceFinish: "plastic"`, and that the geometry fix and the tag are the only changes from `3c516ec2…`.
2. **Use the corrected geometry for the final frames.** Colored frames of the current `c87d2acf` model would show the tented dome and the join dents. They'd be useful for judging color, but they shouldn't serve as the final review.
3. **Clear the old geometry checks for the new model.** The proof carries the `8fa07c` checks forward only because the BRep is byte-identical. That stops being true once the geometry is corrected, so the face size, the 27 depth checks and all 30 contacts should be checked again against the new model.

**What I'll judge when the final filenames arrive**
- **#14 dome:** a round top at full width, near-vertical sides, pocket #15 sitting well inside, and any blend only as a concave fillet at its base. This is the blocker.
- **Joins between zones 2 and 3:** no pinched dip in the front outline, and no V-notches in the top view or dents in the oblique and raking views. The 55/65 mm depth change should be a long, gentle blend.
- **Outer-jug saddles:** still matching the source. The faceting on the jug lobes is an old limitation, not part of this change.
- **Color:** every board surface mint with no grey left over (only attachment parts stay neutral), the red highlight easy to see, and mint restored when a hold is deselected. I'll also look for banding on the blends and check whether the dark sliver near the left #1/#2 join is still there.

I didn't edit, create or delete anything; my one shell command started with `rtk proxy`.
