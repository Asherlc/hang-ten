# Rock Ring cord evidence and CAD mapping

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

`ContinuousCordChannel` is a native boolean
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

`threadedLoopCord` represents one loop with two top mouths, with one physical loop per ring. It uses
the internal-loop solver/renderer with one ordered passage pair. Its complete
CAD-spine points are transient cord geometry: the opaque board occludes the
interior portion and exposes it only at the real openings. USDZ contains no
cord, materials, or textures. The flat source `Hangboards/metolius-rock-rings-3d.FCStd` stores both instance
setups in its schema-2 `HangTenSuspensionAuthoring` property. The build generates
`assets/suspension.json`, checks its source and descriptor hashes, and merges it
into bundled `board.json`. Neither generated JSON file is committed.

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

## Review and regeneration

The retained [front, side, and top comparison](../pr-screenshots/rock-ring-threading/cad-comparison.png)
shows the connected channel revision. Regenerate resources and check the
current native routes using the [CAD build guide](../../Tools/HangboardCAD/README.md)
and [cord authoring guide](../HANGBOARD_CORD_AUTHORING.md). Change the authored
CAD parameters and rebuild; keep computed heights and cord paths out of source.
