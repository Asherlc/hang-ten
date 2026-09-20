# Forge and Natural native migration

The user's 2026-09-20 approval of the exact 24 captures, 12 PDF views and six
cord exclusions is retained in [human-approval.json](../human-approval.json).
It authorizes evidence-led migration, not model acceptance. F1–F7 and N1–N5
remain the visual authority. Original delivery GLBs and evidence are unchanged.
No routine content, app rendering code, schema or production transporter changed.

## Stable physical identities

All 20 Forge and 14 Natural contact objects, their order and factual fields are
preserved exactly from dispatch base `c441d1a868557bb54f07552f04b22742cb498baf`.
The explicit per-board contact mappings bind actual native mesh pieces. For each
side, the delivered Forge labels map as follows:

| Delivered label | Canonical ID prefix / ruling |
| --- | --- |
| sloper-30, sloper-40 | sloper-30, sloper-40 |
| flat-edge, slopey-crimper | large-flat-edge, slopey-crimper |
| rail, closed-crimp | variable-edge-rail, closed-crimp |
| mr-deep, mr-shallow | mr-deep, mr-shallow |
| imr | Partitioned into im-deep (outer) and im-shallow (inner) |
| pinch-medium, pinch-narrow | Body; preserve the full physical jaws |

F2 labels the deep/shallow IM options on one connected cavity, while F3 gives
only an aggregate IMR depth range. The derivative authors a continuous cavity
with two lower scallops and a depth transition. One explicit local X=153 mm
plane partitions the lower contact surface, clipping crossing triangles and
interpolating their normals. It adds no duplicate shells, interior wall or gap.
Both halves use the same mirrored section. The cut is an estimated display
boundary between labeled physical regions, not a claim of exact finger placement.
No IM depth is added to `contacts[]`: the aggregate 19–31 mm does not establish
an independent depth for each of the existing two-finger contacts.

Natural's delivered jug, rail-upper, rail-lower, closed-crimp, pocket-3finger,
pocket-2finger and pocket-supported map respectively to top-jug,
top-variable-rail, bottom-variable-rail, closed-crimp, upper-pocket,
center-lower-pocket and outer-supported-pocket, each with its stable side suffix.
The extra pinch-thumb meshes become body. N2 p6's wide/medium pinch uses combine
the upper/lower rail with the lower body edge. A thumb-only patch would not be
a complete pinch in the live PhysicalContact schema, which lacks compound-grip
relationships. Forge's three pinch widths similarly combine existing outer-block
surfaces. These uses remain provenance here and in the immutable grip-usage
records; no misleading independent pinch, duplicate mesh, training instruction,
compound schema feature or invented routine is introduced.

The historical Natural manual and current page/marked image disagree on crimp,
center-lower and supported-pocket depths. Their canonical depth fields remain
omitted. Current 10/27/30–27 mm numbers inform **display estimates only**, without
asserting equivalence to the 2021 revision. The 38 mm upper pocket, published
rail ranges and all existing finger/posture facts remain unchanged.

## Explicit derivative geometry

Astra inspected the approved originals, full PDFs and native original-GLB
front/oblique/crimp renders. The source had a rectangular Natural groove with a
computed but unused shoulder, squared Forge crimp/jaw transitions, a flat brow,
zero drafted floors and visible thin jagged crimp edges. These findings required
shape authoring, not importer repair or a material disguise.

[trango-authoring](trango-authoring/) retains the exact original numerical
geometry helper, a verbatim relevant product excerpt, their original whole-file
hashes, and the delivery MIT license. The separate `author_trango.py` and
`authored_geometry.py` are deliberate derivatives. They reconstruct the reviewed
physical features using explicit analytic outlines, sections and mirrored halves.
They never sample, crop, trace, segment, vectorize or register product pixels.
The original GLBs remain immutable inputs and a source-diagnosis comparison.

The final authoring choices include:

- Natural's broad tapered recessed crimp area, rounded triangular lower-edge
  thumb hook, and wide inner return. This is an authored area with an explicit
  rounded section; the rejected first trial's narrow centerline channel was
  insufficient. The crimp area remains open at the outer board edge.
- Natural's supported-pocket floor has two sections with an estimated 3 mm
  step, following the visible N4/N5 form. This is one canonical physical pocket.
- Forge's wider crimp recess/terminal support, arched crimper brow, rounded
  transitions of the projecting jaws, and continuous sloper joins. Purposeful
  flat sloper faces are retained.
- Forge's pockets and rail use an estimated 6° draft and a deliberately selected
  noncircular cubic lip section. F4 and the designer-primary text establish draft
  and a distinct lip profile, but no numerical curve or angle; these are display
  estimates, not recovered manufacturer CAD. The supplementary designer text is
  retained separately, not admitted as a new visual authority.
- Forge's IMR lower surface has two authored shallow scallops and a smooth
  transition between estimated 19 and 31 mm recess depths. Deep/shallow remain
  separate stable selections on this one continuous physical cavity.

The numerical helper's ordinary winding orientation and surface-normal
calculation construct the authored mesh; neither changes the authored outline
or adds a smoothing modifier. Deliberate analytic tessellation uses a 0.025 mm
height-error criterion. A later native seam regression additionally bounds
normal interpolation along the authored straight upper-crimp lips through
64 explicit transverse roll bands, with exact shared flat/roll/floor breaklines
and independent flat-face/transverse-roll verification limited to 0.5 degrees. A rejected
adaptive normal-refinement trial failed its convergence/density review; it does
not ship. Front/back outward normal direction is explicit; it is not
inferred from averaged normals on skinny triangles. No generic mesh decimation,
smoothing or shape repair is
run. Exact triangle accounting from prepared Blender meshes through the final
USDZ proves the unchanged transport boundary.

## Screw omissions and preserved passages

The latest user instruction explicitly removes screw holes from all models.
F4 pp4–5 establishes eight Forge board screws. These eight small holes are
omitted in the derivative; the two larger IMR passages are preserved with
unresolved purpose, as recorded by the delivery. They are not cord attachments.

N2 pp3–4 lists six short screws for the two board cleats; p4 shows three small
upper-rail screw heads per board and a separate large lower opening. The delivery
labels all eight openings `mounting-opening-not-hold`. That classification is
unsupported for the two large lower passages. Six upper screw holes are omitted;
the two larger supported-pocket passages remain unresolved-purpose openings.
The current exact N2 PDF was fetched again on 2026-09-20 and matched the approved
original byte-for-byte. No newly discovered screw function was assumed.

Passage coordinates are display estimates. Natural's original local center
(151,-56) mm moved outward to (162,-56) mm within the supported pocket, following
N5's outer location. Forge's original (157,-47) mm moved to (157,-44) mm so the
large passage remains fully inside the drafted recess, consistent with F5's
upper placement. Radii remain the original 6.3/6.5 mm estimates. Native rays
through all four exact final openings must miss all mesh triangles. Oblique
views can hide most of an opening behind the genuine cavity wall; that is not
closure. No hardware, cleat, wall, screw or suspension cord is baked in.

## Native transport and shipping

Run `trango-authoring/author_trango.py natural forge` with the recorded numpy,
shapely, trimesh, scipy and networkx environment. It writes regenerable arrays
under `.context/hangboards-batch-05-astra-migration/prepared/` and records source
sections, true recess probes, watertightness and winding consistency. Run
`prepare_trango.py` inside Blender with the two full slugs. This verifies the
original GLB hashes, bakes their root matrices once to confirm native Z-up,
front−Y metre coordinates, and installs the explicitly authored derivative in
that same basis. No extra rotation or scale conversion occurs.

Preparation partitions contacts and encodes the source constant linear RGBA
into an explicit constant PNG RGBA8 sRGB image (maximum linear error <0.004),
with no invented grain or product-photo texture. The generated blends stay in
workspace-owned `.context`; the compact authoring/mapping/manifests and hash-bound
reports are retained here. Import them using the unchanged
`import_contact_model_source.py` and `contact_model_package.py`. The compiler
exports, reimports the exact USDZ into an empty scene and validates materials,
triangles, node correspondence, bounds and canonical descriptor hashes.

Both shipped packages are model-only. USDZ bytes alone go to registered Xcode
ODR packs; JSON and descriptors remain bundled metadata. The closed cord audit
contains approved noDocumentedSuspension/excluded records with exact retained
snapshots and consistent per-package exact-revision IDs. Fixed front presentation
is supported; removable cleats or optional pulley kits do not imply suspension.

`verify_trango.py` independently checks prepared-to-exported triangle multisets,
all contact pieces' nearest visible hits with body geometry included, exact screw
closure rays, real open passages, and crimp/stepped-floor sections. Front,
oblique and crimp-closeup renders come from empty imports of the exact final
USDZs. These checks do not establish current-source iOS material, picking,
highlight, clear, orbit/reset or unavailable-state acceptance. Those remain the
controller's separate all-six native task.

## Upper-lip shading regression

The first rounded export checkpoint was not visually accepted: small triangular
marks remained where a tilted roll normal interpolated onto an analytically flat
front face. The actual USDZ triangle at the reviewed Forge pixel (341,304) had one
15.15-degree tilted corner, despite only about 0.013 mm height error. The height
criterion did not constrain the shading field. Shadow-disabled diagnostic renders
retained the marks, excluding cast shadows as the cause. Two mirrored Natural
hook normals were also inverted by the former averaged-normal sign heuristic.

The independent pre-fix regression measured maximum interpolated normal errors of
17.18494 degrees (Forge) and 18.56282 degrees (Natural). Retained technical evidence
is [official Blender smooth-shading documentation](https://docs.blender.org/manual/en/latest/scene_layout/object/editing/shading.html),
with exact capture/hash and diagnosis under `trango-authoring`. This is technical
rendering evidence, not new product shape authority. The correction explicitly
samples the authored lip's analytic normals and declares outward direction.
A 0.5-degree verification limit bounds unit-normal deviation below 0.009; tiny
sample spacing is a numerical shading requirement, not a manufacturer dimension.
No shadow/renderer workaround ships. `verify_trango_lip_normals.py` binds its
independent results to the authored arrays and final model hashes. It preserves
the broader candidate-triangle error separately: Forge7.446 degrees includes
curved-return/jaw transitions outside the diagnosed straight transverse roll,
and no global0.5-degree claim is made. The flat-face scope includes all originally
reviewed Forge lip positions. Native export
verification additionally compares prepared and reimported custom normals.

The final band topology uses295,072 Forge /120,864 Natural authored triangles,
below the earlier rounded checkpoint427,264 /226,996. USDZ sizes are13,876,030
and5,709,194 bytes. Final ray neighborhoods at the originally reviewed locations
(867 rays per product per version) reduce flat-face normal error from18.02156 to
0.03839 degrees Forge and20.71780 to0.04985 degrees Natural. Whole-neighborhood
maxima remain recorded, including9.82669 degrees in Forge's curved terminal;
this is not a global normal-error guarantee. The controller reviewed all six
final desktop renders and accepted the visible geometry on2026-09-20. iOS
acceptance remains separate.

To reproduce the original-location comparison, `probe_trango_lip_locations.py`
runs in Blender with `-- checkpoint` or `-- final`. Checkpoint files use the two
old SHA256 identifiers recorded in `original-location-native-regression.json`,
under the workspace's `trango-seam-checkpoint` directory. They can be copied
read-only from local LFS objects; do not overwrite shipped packages. Then run
`evaluate_trango_lip_locations.py` with the pinned authoring Python environment.
The probe uses one native triangle BVH and the exact review camera, not image
analysis. No shadow-disabled diagnostic setting is applied to final renders.
