# #17 Baguette Evo: rounded native cavities and bearing-up poses

The [human review record](../human-review.json) records acceptance of the shown rounded cavities, wood finish, native-solved cords, nineteen contacts and nine bearing-up poses. The rounding radii remain display estimates.

## Source and correction

The [approved whole manufacturer images and page](../source-register.json)
show a wooden cylindrical bar, rounded cavity ends, opposed depth rails, four
independent cord bores and exposed rear returns. No pixels were measured,
traced, segmented, cropped or registered.

The initial native migration made the cavity terminations too square. Ten
editable native `Part::Fillet` features now round the existing cavity tools.
The shared front opening retains a curved internal deeper step, without an
added bridge. The existing 2.5 mm lip roundover remains. Front/back end radii
9 mm and top end radii 8.5 mm are explicitly operator-selected **display
estimates**, not manufacturer dimensions. Native sketches, factual depths,
bore features, contact IDs and the embedded nine-pose manifest are retained.

The eighteen non-tray contact surfaces are clipped to the rounded cutters.
Native subtraction separates shallow and deep surfaces at the new curved
step. All twenty contact regions for nineteen logical IDs lie on the final
external skin; shallow/deep overlap is zero. Both tray regions remain intact.
[Native construction and limitations](rounded-ends/authoring-notes.md) and
[independent checks](rounded-ends/independent-audit/summary.json) retain details.

The existing procedural wood appearance is enabled with `surfaceFinish: wood`.
The exported USDZ remains unbound, without materials, shaders, textures or cords.

## Orientation and cords

The previous five shared poses left ten flat bearings pointing down. Nine
groups now orient all eighteen source-depth witness rails upward and turn
the tray's curved bearing surface upward. Five original position IDs remain
for their original representative contacts; four opposing poses are added.
All contact names, kinds and depths remain unchanged.

Exact rotations and camera inclinations are display adaptations from measured
native bearing normals, not manufacturer angles. The camera directions are
stored in model coordinates, using the inverse pose to obtain the intended
world view. This correction retains the original minimum-height test rather
than weakening it. See the [normal audit](orientation-audit/recommendation.json)
and [camera correction](package-checks/framing-review/actual-camera-sidecar-check.json).

The legacy `edge-6-upper/lower` names refer to mirrored left/right native
U-grooves; their contact regions include sidewalls and floor. Their identities
are preserved. Their two measured depth-bearing normals use the same pose.

The four bores, front-entry axes, two visible rear returns, support and cord
size/length estimates remain unchanged. Native-solid routes are regenerated
for all nine poses with the existing solver and supported A* search. No hidden
U-channel, knot, connection or hand-authored route is introduced. This is a
static constrained display approximation, not a friction/dynamic simulation
or a manufacturing, ergonomic or safety specification.

## Verification and comparisons

Independent native checks preserve all eighteen exact depth witnesses, four
bores, constrained sketches and tag identities. A native radius edit 8.5→8.0 mm
changes the final solid and restores its volume within 0.0000016 mm³ while
remaining valid. The saved source bytes are unchanged by that test.

Separate compiler check and publish runs reproduce the same actual USDZ.
Source: `0ce8b0b9ce39637f9b6d4b2c29618ef09430b200513b5548f54d97e83804a448`.
Model: `c28fb4c06a512da920c2b61c6dcd219b5e0f20af5b3672103815c312518838cf`.

- [Prior committed CAD versus corrected CAD, front/side/top](prior-rounded-front-side-top.png).
- [Original display mesh versus corrected CAD, front/side/top](rounded-original-native-front-side-top.png).
- [Native before/after views](rounded-ends/before-after-front-side-top.png).

The final [source-bound cord check](rounded-export/cord-check.json) reproduces
all nine routes/heights. Minimum conservative centerline clearance is
1.992752 mm for a 2 mm display radius, within the existing 10 micrometre
certificate tolerance; this is not a strictly positive surface-gap claim.
The final sidecar hash is
`4d0aa10c8914bd41fd79cc825d094ffc5a785aae64aef5406ade19778102a282`.

[Original/prior/corrected whole front-side-top comparison](original-prior-corrected-front-side-top.png)
combines the separately retained whole rendered frames.

## App views of the accepted revision

The [runtime record](ios/final-runtime-validation.json) records the source-bound contact selections, canonical poses, picking and workout checks for these captures.

- [Three whole app views](app-review.png).
- [All nineteen contact selections](all-19-contacts.png).
- [All nine canonical poses](nine-poses.png).
- [Settled active workout](ios/workout-settled/active-settled.png).
- [Following rest](ios/workout-settled/following-rest.png).

The physical left 20 mm contact appears on the viewer's right after the board
flips to load its opposite bearing. Board-local contact identity is preserved;
the image is not reflected to change its handedness. Some aggressive orbit
captures clip a tip and remain retained; the additional gentle oblique review
frames show the whole board. This is a Simulator display review, not physical
manufacturing or ergonomic validation.
