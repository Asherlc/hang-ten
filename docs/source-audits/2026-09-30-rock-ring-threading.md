# Rock Ring connected cord passages, 2026-09-30

The owner requested cords through the side holes and two displayed instances
of one ring model. They confirmed one continuous cord per ring, with two
strands meeting overhead, and that the connection between the side openings
runs through the solid body behind the upper pocket. These explicit owner
corrections supersede the prior clipped paired-lead presentation. No knot or
mounting hardware is added.

## Retained evidence

- Metolius product photo, https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg
  (product page: https://www.metoliusclimbing.com/products/rock-rings-3d).
  Retained `2026-09-30-rock-ring-threading/manufacturer-pair.jpg`, SHA-256
  `d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c`.
  Supports two independent rings, each with two rising strands and top exits.
- Original owner/resale side close-up,
  https://i.ebayimg.com/images/g/KQkAAOSwjmJmDzoE/s-l1600.webp.
  Retained `2026-09-30-rock-ring-threading/owner-side.webp`, SHA-256
  `df263e67395aa17a2f4df263ca74e4cbbfb7bfcf9c75e0dfa611d352ad3d3cba`.
  Supports the oval lateral access opening with cord visible inside. This is
  secondary exact-product evidence; it does not establish factory bore metrology.
- Owner review in this session establishes continuity and the hidden connection
  behind the upper pocket. Manufacturer photos alone do not establish that route.

## CAD and metadata mapping

The previous roof bores ended at model Y=84 mm; lateral recesses were centered
at Y=48 mm, and were disconnected. `ContinuousCordChannel` is a native boolean
union of cylinders and spherical elbow clearances, with a linked ordered
`ContinuousCordSpine`. It is subtracted through the existing `Recesses`/`Body`
feature chain. The imported single-ring node/contact-slot inventory is retained.

The reconstructed spine runs from each existing top exit at X=±62 mm, Y=91 mm,
through the side recesses at X=±66 mm, Y=48 mm, and across behind the upper
pocket at Z=-20 mm. Exact intermediate stations, elbow treatment, and the 4 mm
channel radius are **display estimates**, not measured factory geometry. They
implement the owner-confirmed connection while retaining the established
external envelope and contact geometry. The hidden channel is native CAD void,
not a rendered hole decal. Its measured spine length is 259.298221 mm.

`threadedLoopCord` represents one loop with two top mouths, rather than adding
another physical loop to satisfy the historical two-branch schema. It reuses
the internal-loop solver/renderer with one ordered passage pair. Its complete
CAD-spine points are transient cord geometry: the opaque board occludes the
interior portion and exposes it only at the real openings. USDZ contains no
cord, materials, or textures. Schema-2 `suspension.json` binds both instance
suspensions to the one descriptor hash. No generated `board.json` is committed.

Cord radius 2 mm, total loop rest length 520 mm, invisible anchor offset 98 mm
above the model bounds, camera padding/direction, and ±105 mm instance spacing
are display estimates. The direct-leg solve determines the hanging height from
measured channel length and loop rest length. It samples free spans and the
interior spine every 0.5 mm against the exact native solid; any collision fails.
The winding entries are retained topology metadata; direct unobstructed legs
need no surface winding or manually placed bearing contacts.

Both default and selected displays clone the same single-ring USDZ. Selection
composes the instance placement with the solved pose and frames the union of
both rings and their cords. All eight physical contacts keep their independent
left/right identities; transient cord entities have no picking or accessibility
bindings.

## Verification

- Package/manifest suite: 485 tests passed. Three new single-loop solver tests
  pass, including rejection of a path through the solid and an undersized cord.
- Full package inventory validation and existing native CAD checks pass.
- Native channel measurement matches 259.298221 mm. The applied and checked
  solve reports 520.000000 mm total cord length and 3.685190 mm minimum
  centerline clearance against the exact CAD solid for each instance. Native
  inside-solid samples are explicitly rejected as negative clearance.
- Prior/changed front, side, and top renders were reviewed and retained at
  [CAD comparison](../pr-screenshots/rock-ring-threading/cad-comparison.png).
- iOS Debug build passed using `xcodebuild -project HangTen.xcodeproj -scheme
  HangTen -configuration Debug -destination 'platform=iOS Simulator,id=AD913955-2A20-478F-B18C-DBDA574F5DA8'
  -derivedDataPath .context/DerivedData build`. XCTest bundles compiled, but
  execution and app visual review could not complete: the isolated iOS 26.5
  simulator stalled at boot, and a controlled iOS 26.4 retry
  (`D2619ED2-1C49-437B-8DFC-D26E9E36299C`) stalled during data migration and
  app launch. No app screenshot is claimed as validation. Both owned simulators
  were cleaned up; shared simulators were left alone.
