# Frictitious native migration, 2026-09-20

This record covers DoorMount Pro **7** and the current three-tier Megalith.
The exact approved evidence is D1/D2/D3/D4 and M1/M2/M3 in the adjacent
[evidence manifest](../evidence/manifest.json), with original URLs and hashes.
D4 supports only the **lower Pro 7**; its upper Pro 5 is excluded. M3 is a
**side profile**, not an oblique view. Delivery references M4/M5 were not used
as authority. [Human approval](../human-approval.json) covers evidence and the
cord exclusions, not native model acceptance. No routines were changed.

## Physical inventory and facts

[D1](https://frictitiousclimbing.com/products/doormount-pro) and D2/D3 establish
five edge depths (35/25/20/15/10 mm), the full-width jug, nested pockets, and the
Pro 7 identity. All 13 pre-migration DoorMount contact objects, fields and order
are unchanged. Opaque historical IDs retain their physical meaning:

| Delivered node after `hold--` | Stable app ID |
| --- | --- |
| jug | top-jug |
| left-edge-35 / right-edge-35 | edge-35-left / edge-35-right |
| left-edge-25 / right-edge-25 | mixed-25-pocket-left / mixed-25-pocket-right |
| left-pocket-2finger / right-pocket-2finger | hold-7 / hold-6 |
| left-edge-20 / right-edge-20 | hold-12 / hold-13 |
| left-edge-15 / right-edge-15 | hold-11 / hold-8 |
| left-edge-10 / right-edge-10 | hold-10 / hold-9 |

[M1](https://frictitiousclimbing.com/products/megalith) explicitly identifies the
nested two-finger pocket on the 40 mm edge, mono pockets, seven paired edge
depths (8/10/12/15/20/30/40 mm), center 25 mm edge and full-width jug. Approved
M2 shows the symmetric physical regions. The older 18-contact package bundled
the nested pocket into each 40 mm edge. The deeper pocket wall/floor is a
separately usable contact within a shared cavity, so it now has its own identity:
`pocket-2finger-left/right`, kind pocket, fingerCapacity 2. **No pocket or mono
depth is asserted**. These additions are a physical inventory reconciliation,
not a prescription or a blind adoption of the delivery's count.

All 18 prior Megalith IDs and source-backed fields remain. The old
`edge-40-pocket-left/right` IDs still designate the 40 mm ledges; their names now
say “Left/Right 40 mm edge” to distinguish pocket selection. Every other existing
contact field and the original ordering remain unchanged; the two pocket
contacts append to that inventory. Jug maps to `top-jug`; center-edge-25 stays
itself; left/right-mono maps to mono-left/right; paired source edge nodes map to
`edge-<depth>-<side>` except the preserved 40 mm IDs above. The explicit complete
mappings are in each native directory; all source nodes are accounted for.

D1's 25.5 × 4.5 × 2.25 in and M1's 26.75 × 6.5 × 2.25 in dimensions remain.
Cavity spacing, radii, tier sections, rear simplification and small-pocket depth
are **display estimates**. Delivery estimates (DoorMount pocket 40 mm, Megalith
pocket 46 mm, mono 28 mm) stay in source provenance only, never canonical facts.
No gripTypes, training cues, exercise counts or durations were added.

## Explicit geometry preparation

[prepare_frictitious.py](prepare_frictitious.py) verifies the immutable original
GLB hashes, applies the imported world matrix once, and removes transform-only
empties. GLB is already metres/+Y up/+Z front; Blender uses +Z up/front−Y.
The source world-vertex displacement from baking is zero. There is no second
axis conversion, scaling, image tracing, contour work, source registration,
automatic geometry simplification, or repair inside the production tools.

The retained [analytic authoring excerpts](frictitious-source-authoring-excerpts.txt)
record `products.py` and `Unit.hole/front_hole` with their original file hashes.
These, each source `mounting-interface.json`, and D2/M2 distinguish mounting
openings from real contact cavities. Per the migration contract and the user's
explicit request to omit screw holes, the preparation removes **one DoorMount
central mounting opening** (source X0/Z11 mm, radii7/10 mm) and **six Megalith
screw openings** (X±290/Z8, X±130/Z−43, X±62/Z11 mm, radius3.8 mm).

For each known opening only, it deletes the authored 96 body-tube triangles
and fills its two known 48-segment elliptical boundary loops with 96 triangles
on the original analytic front and rear support planes. It retains all existing
coordinates and restores the plane normals at the filled mouth. GLB split-normal
duplicate vertices are handled by exact position groups for these known rings;
no image or geometric hole detection is used. The central DoorMount relief,
Megalith tiering, monos, stepped edges and nested pockets remain. This is a
**display omission**, not a claim that the physical products have no holes.

The source Megalith bottom right 15/20 mm seam had a separate **identity** defect.
The source's inclusive range test gave the 229 mm-centered strip to the first
right-hand range (20 mm), whereas the mirrored left strip belonged to15 mm.
Its final AABB mismatch was 0.003429932 normalized (about2.33 mm). After an
expected failing mirror regression, preparation explicitly transfers those
18 triangles from `hold--right-edge-20` to `hold--right-edge-15`. Coordinates,
triangle winding and corner normals are unchanged. It drops the transferred
triangles' now-unreferenced vertices from the source node so descriptor bounds
cover the actual remaining contact. All bilateral contact bounds now match
within 1e-6 normalized, without widening the tolerance. Original ownership
counts (left15=720/left20=702; right15=702/right20=720), transfer coordinates and
final triangle sets are retained and checked.

The material adaptation is the preceding Zlagboard pattern: explicitly encode
constant linear source RGBA as one PNG RGBA8 sRGB texture, quantifying channel
error below0.004. No generated wood grain or source image texture is involved.

## Native texture-coordinate correction

Native SceneKit validation exposed white/grey reconstructed surfaces even though
the exported substrate PNG and PBR parameters were correct. The original GLBs
have texture coordinates; the mounting-closure reconstruction dropped the body
UV layer on both boards, and the ownership reconstruction dropped it on Megalith's
right 15/20 mm meshes. The other imported meshes retained their coordinates.
Increasing texture size did not fix the white body. A candidate with only explicit
UV coordinates restored the intended beige in native front and oblique controls
for both boards, using the same one-pixel PNG, renderer and materials.

Preparation now deliberately assigns `st=(0.5,0.5)` to every loop of those four
reconstructed meshes, sampling the center of the constant image. This is texture
transport metadata, not inferred geometry or generated grain. Original coordinates
on every other mesh remain unchanged. Each `uv-transport-verification.json` binds
old/new USDZ hashes and records that the canonical `usdcat` layer is byte-identical
after removing only the `st` and `st:indices` attributes; existing UV arrays and
embedded PNG bytes match exactly. Thus vertices, topology, winding, corner normals,
materials, bindings and transforms are unchanged. Descriptors differ only in their
model hash. Contact identities, original GLBs, screw closures and the 18-triangle
ownership ruling are preserved.

The retained verifier now clean-reimports the actual USDZ, requires a finite UV
for every loop and validates every used material's diffuse-image binding plus
roughness 0.78 and metallic 0. Before correction, this verifier failed on the
DoorMount body; the native regression independently failed on all four meshes.
The corrected native candidate test passes. Full app acceptance remains separate.

Technical references: [Blender USD material export](https://docs.blender.org/manual/en/4.4/files/import_export/usd.html)
supports the simple Principled/image/UV network used here.
[OpenUSD's primvar reader](https://openusd.org/release/spec_usdpreviewsurface.html)
defines a missing-coordinate fallback, but actual SceneKit controls demonstrated
that this asset needs explicit UVs. [Apple's physically based material documentation](https://developer.apple.com/documentation/scenekit/scnmaterial/lightingmodel-swift.struct/physicallybased)
states that diffuse, roughness and metalness govern this shading model; its
`specular` property is ignored. No runtime material substitution or lighting
change was used to fix these packages.

## Ledge diagnosis and exact export review

The original GLBs and exact exported USDZs were independently imported into
empty Blender5.2 scenes and rendered front, oblique and with ledge closeups.
The narrow dark bands at tier setbacks and depth transitions are already in
the source geometry/shading. The actual export did not introduce torn ledges,
new jagged selection boundaries or extra dark seams. The curved cavity lips
and deeper pockets remain coherent against D2/M2/M3. No broad smoothing or
shape-changing repair was justified or applied. Read-only verification confirms
that the union of every contact triangle is unchanged and quantifies the tiny
source-to-USDZ corner-normal roundtrip delta. The identity correction changes
selection ownership, not visual shading.

[verify_frictitious.py](verify_frictitious.py) independently compares source and
exact USDZ contact triangle multisets after the explicit ownership ruling,
checks imported inventory/materials/triangles/canonical descriptor and hashes,
and fires front/back rays through each omitted bore center. All seven now hit
the expected body support planes. Reports reside beside each mapping. Render
paths and exact USDZ/image hashes are retained in `frictitious-render-review.json`;
images and regenerable blends remain workspace `.context`.

Native importer and compiler are unchanged. Run preparation in Blender with
workspace config/cache/tmp, then call `import_contact_model_source.py` with each
native `source-manifest.json`, `contact-mapping.json`, canonical `board.json`,
package ID and fresh owned output directory. The importer calls
`contact_model_package.py`, which clean-reimports the exact USDZ before creating
the sorted hash-bound descriptor. Run `verify_frictitious.py` against the promoted
packages. `preparedSHA256` binds each local derivative; saves may vary by run.

## Shipping and acceptance boundary

Each package has model-only media and no raster/contactGeometry. Each has one
Xcode ODR tag; board metadata and descriptors remain bundled, only the unchanged
USDZ goes into ODR. Approved D1/D3 and M1/M2 exclusion records were added to the
closed cord audit with exact snapshot copies and honest user-approval provenance.
They assert `noDocumentedSuspension`, not universal absence of all accessories.

Current-source iOS materials, all33 nearest-contact picking, highlight isolation
and clear, orbit/reset and unavailable-state checks remain the controller's
all-six acceptance task. These Blender renders do not claim native app acceptance.
