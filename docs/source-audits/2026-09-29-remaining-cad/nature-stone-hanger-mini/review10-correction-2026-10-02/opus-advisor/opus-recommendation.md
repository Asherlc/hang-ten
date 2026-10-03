# Stone Hanger Mini #10: jug coverage and cord fixes (second opinion)

**Recommendation:**
- Bind the jug to the existing top-rail faces. Share those faces with the pinch instead of taking them away from it.
- Put the jug back on the identity `front-upright` pose and delete `jug-open-up` together with its cached routes.
- Keep the current cord path, which the photos support. Change only the seating so the cord sits in the groove, and fix the misleading 40 mm segment length.
- Don't force the existing groove-guide solver onto this board. It doesn't fit without new geometry.
- I found maker evidence that this is a lifting edge with the load hanging below. That conflicts with the anchor-above setup and is the largest open cord question.

I edited no files. One side effect: the web-fetch tool automatically cached the maker images I viewed into the Claude session's tool-results folder. That folder is outside the worktree.

## 1. Jug coverage against the pinch's top faces

**What the pinch owns now.** `nature_pinch` is bound to six `FinalSolid` faces (23, 30, 31, 43, 44, 69), and its depth axis is the 60 mm vertical span. Its area (4679.47 mm²) and bounds (x ±42, full height, full thickness) match exactly:
- the top and bottom flats (84 × 20 mm each), plus
- the four straight 2.5 mm edge rounds (front and back on top and bottom).

So the pinch currently owns the entire straight top rail, including the top-back round. I worked this out from area and bounds; I didn't query the faces directly.

**What the jug should cover.**
- Split the pinch's top flat and top-back round into a new contact node. Make `pull-up-jug` its primary contact and `pinch-60` an additional contact on the same node (the `AdditionalContactIDs` mechanism in `Tools/HangboardCAD/compile_board.py:192` and `Tools/HangboardCAD/README.md:277`). Mini contact nodes use the v1 `ContactID` style, so this is allowed.
- The pinch keeps the bottom flat, both bottom rounds and the top-front round. Its highlight still covers all six faces.
- The compiler measures a shared contact's depth across all its member surfaces. Measured on the vertical axis, top to bottom is still 60 mm, so the pinch depth check passes. The jug declares no depth.
- With the jug as primary, tapping the top rail selects the jug, which matches what the user decided.

**What to leave out:**
- The 8 mm end-corner rounds (|x| > 42). They stay body: that's where the upright leads exit, so the jug highlight stays clear of the cord.
- The whole back face. It's one large face, and highlighting it would mislabel the back. Splitting it would mean new geometry.
- The old recess back wall (Face6). Return it to the body, or to the wood edge only if there's evidence for that.

**One side effect to check.** A top-only contact projects onto the front view as a thin strip at the very top. That only matters if any 2D fallback highlight is still used.

## 2. Pose

Assign the jug to `front-upright` alongside the granite, as in the original `native-cord-evidence.json`. Then remove `jug-open-up`. Separately, `pinch-side` has the same rotation and translation as `front-upright`. That's out of scope here, but worth noting.

## 3. Cords

**What the photos show** (approved images, whole and qualitative):
- **Oblique photo:** each end face has two full-height vertical grooves and a mid-height groove running front to back. The cord comes down one vertical groove, turns 90° into the cross groove, and disappears into a dark round opening.
- **Front and reverse photos:** both show the mid-height notches.
- **Knot:** one lead carries a multi-wrap knot with a cut tail.
- **Not visible anywhere:** where the cord goes after the opening.

**Extra maker images** (linked from the saved product page, not in the approved set):
- `Oakminihanger8.jpg` (close-up of one end): the cord comes down the groove nearer the pocket face, then turns toward the back along the cross groove. That matches the current lead plus cross-return path.
- `Oakminihanger6.jpg` (pack shot) is consistent with the approved photos.

**What contradicts the current cords:**
- **`jug-open-up` routes are physically wrong.** With a fixed 110 mm lead and a fixed anchor, the solver soaked up the slack by running each lead about 26–30 mm sideways along a horizontal groove. The left lead ends at the front corner and the right at the back corner, so the two sides are asymmetric. Under near-vertical load, a cord would lift straight out of an open groove that runs across the pull. Deleting this pose removes the problem.
- **The cord isn't seated in the groove.** The groove cylinders have a 1.7 mm radius and their axes lie on the end-face plane (x = ±50), so the groove floor is at |x| = 48.3 mm. A seated 1 mm cord would be centred at |x| ≈ 49.3 mm. The cached terminals and segments are at |x| = 50, and the leads at about 49.9. That leaves the cord about 0.7 mm proud, half outside the groove. The existing clearance certificate doesn't detect this.
- **The cross-return length is misleading.** It's declared as 40 mm but the actual cached span is 12.5 mm. Set it to the real span or label it clearly as an allowance.

**Smallest fix:**
- Keep the current topology, with independent leads ending at the visible opening and no hidden continuation.
- Move the terminals and the cross-return onto the groove floor, derived from the actual groove geometry rather than nudged by eye.
- Re-solve the remaining three poses.
- Note in the provenance that the knot is omitted.

**Why the groove-guide solver doesn't fit unchanged.** It needs an existing bore feature in the CAD (`boreFeature`), and the Mini CAD has none ("No closed internal passages supported"). It also routes one groove into one opening, while the Mini cord makes an L-turn from the front groove through the cross groove to an opening at the back groove. Adding an opening would change the accepted body. Its position and diameter would be estimates, and there's no owner confirmation for the Mini (that was given only for review 9).

## 4. New maker evidence

- **The product page calls the Mini a lifting edge.** The saved page says "The Stone Hanger Mini lifting edge packs real granite…". The generated `board.json` subtitle also says "Compact lifting edge".
- **There is a hand demonstration.** `https://natureclimbing.com/cdn/shop/files/MiniHanger-86.jpg` is linked from the saved page but isn't approved. The board is upright, a hand wraps the upper rail, and both leads run **down** to a carabiner on a loading pin. That contradicts the earlier claim that no source shows a hand. It supports the top-rail jug identity, and it contradicts the current anchor-above setup.
- **Precedent:** `Hangboards/plateau-lifting-edge` uses a downward support (`supportDirection: -1`).
- **Why I wouldn't flip it in this fix:** in lifting use, the load-bearing edges face down. That would swap which pose shows the granite and which shows the wood, so it's not a cord-only change. It needs its own explicit decision.
- **Other board versions:** blog photo `EKTAR100-5.jpg` shows a beech Mini with holes through the face near the ends and no visible end grooves. That's a different version, so don't use it for Oak routing.

## Still unresolved

- Which way the load hangs (up vs down), and the pose↔contact assignments that follow from it.
- Where the cord goes after the visible opening, and the opening's exact position and diameter.
- Cord radius, the 110 mm lead length and the knot geometry. All are display estimates.
- The current page lists 105 × 60 × 30 mm, while the accepted body is 100 × 60 × 25. Leave the body as is.
- Approval status of the extra images (`MiniHanger-86`, `Oakminihanger6`/`8`).
- No app screenshots of the current asset exist, and the jug highlight's appearance in the app is unverified.
