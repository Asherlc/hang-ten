# Hangboards Batch 04 3D Migration Design

**Status:** approved conversational design; written review pending
**Input:** /Users/asherlc/Downloads/hangboards-batch-04

## Shared understanding and success criteria

Migrate Crimptonite Helium Mobile, Metolius Light Rail 2.0, Metolius Rock
Rings 3D, Owl Climb Poker, YY Vertical Penta Evo, and Trango Rock Prodigy
Pivot. Each final package is schema-v3 and model-only: exactly one USDZ and
hash-bound descriptor, with no raster, canonical path, contactGeometry,
fallback geometry, or fallback presentation. Legacy descriptor-v1/model
packages stay byte- and behavior-compatible.

Success preserves source-backed metadata and physical contact identity; it does
not invent geometry, dimensions, cord routes, or training copy. Remove every
mounting/screw hole, screw, cleat, bracket, and mounting-hardware mesh. Retain
finger openings/contact recesses and evidence-backed cord apertures, but treat
them differently: contacts are selectable gripping surfaces; apertures are
nonselectable attachment geometry. Astra is reserved for authoritative final
shape generation and difficult visual judgment; lower-cost workers perform
schema, tooling, runtime, packaging, and validation work.

## Evidence and fidelity

This table is the exact approved evidence set. Copy input source registers and
media manifests into tracked source-audit paths without changing their meaning.
Manufacturer facts win conflicts. Label any visual/display estimate
authored-display-estimate, never factory metrology. A verified retrieval hash
whose temporary bytes are absent is labelled for exact re-retention during
implementation; an actually unknown hash remains unhashed.

| Board | Approved evidence; exact URL; retained hash where available |
| --- | --- |
| Helium | 9c/Crimptonite front _06: https://9cbouldering.com/cdn/shop/products/Helium--mobile-hangboard-by-Crimptonite_06.jpg?v=1704979580, verified retrieval SHA-256 9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40; implementation must retain exact bytes. Reverse _08: https://9cbouldering.com/cdn/shop/products/Helium--mobile-hangboard-by-Crimptonite_08.jpg?v=1704979580, 5d5c18d45ae6d30e6e951aa158a30b303d42d4583d18d4a6d82075ff5de50f6a. Product facts: https://crimptonite.com/product/helium-mobile/. |
| Light Rail | Metolius Light-Rail-2-PT.jpg: https://www.metoliusclimbing.com/cdn/shop/files/Light-Rail-2-PT.jpg?v=1767727616, verified retrieval SHA-256 7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272; implementation must retain exact bytes. Chosen Treeline field photo/page: https://www.treelinereview.com/gearreviews/best-hangboards-for-climbing, verified retrieval SHA-256 93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a; implementation must retain exact bytes. Product facts: https://www.metoliusclimbing.com/products/light-rail. |
| Rock Rings | Metolius numbered guide https://www.metoliusclimbing.com/cdn/shop/files/Rock-Ring-Depts.jpg?v=1762201543 (no numbered-guide hash is asserted); black/white product evidence https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123, verified retrieval SHA-256 d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c; implementation must retain exact bytes. Retained owner front/rear https://i.ebayimg.com/images/g/xaEAAOSwFtFmDzoB/s-l1600.webp, b510bd192bb6fe54c6e4dcfa98c9d684a2db7582cbfd3682cebb6e031494a8f0; lateral https://i.ebayimg.com/images/g/KQkAAOSwjmJmDzoE/s-l1600.webp, df263e67395aa17a2f4df263ca74e4cbbfb7bfcf9c75e0dfa611d352ad3d3cba. |
| Poker | Owl product page https://owlclimb.com/index.php/en/prds-2/poker/ and four manufacturer photos: https://owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_0.jpg, 4bae58b408b3f3a82c524b1101079eafa01cd062c398cb203d4803fce9850eab; https://owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_1.jpg, 0c1d54cb2bc4d8e7fa285f3053b927d7c1a1b3fbafdf0b5d7aface9c82d0dbad; https://owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_2.jpg, 5fbff79f31db8e85d078a74eb629abd069fc276ac128b3d85a84fc15ad9f1c4e; https://owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_3.jpg, ae39598fbf75c0e4e4dfbb599c724ff1e2531ef12ecca84b3504805e7bc3af13. |
| Penta | YY page https://www.yyvertical.com/en/products/penta-evo plus retained YY originals ending -3, 83b95adc297d634659654f6f27bb43ebae1c53b171b747568ac5e022754e6571, and -6, 1107039ef6d2877cd68a293683c72ec93f3166633199d45484f58c13b48aa2fc. Exact binary URLs were not recovered; the page is not claimed to be their binary URL. |
| Pivot | Trango front https://trango.com/cdn/shop/products/22840-501_RockProdigyPivotGrey_MainImage.jpg?v=1755037446&width=1946, verified retrieval SHA-256 339f743c7e5fff0b0619314cf6781d8f602c1545975390f4ab4424aa7461bf5d; dual-board oblique https://trango.com/cdn/shop/products/22840_RockProdigyPivot_AltImage4_DualBoard.jpg?v=1755037446&width=1946, e05deb5c0ea6d3361122926d7b3efee6b72bb9aad0a75fc09663bf599731e3e4; single-board https://trango.com/cdn/shop/products/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg?v=1755037446&width=1946, 7aa2556dec24293e62c2be110fa7dfb6bcf118333ff35693e455a8a7babc67f7; close-up https://trango.com/cdn/shop/products/22840_RockProdigyPivot_AltImage2_CloseUp.jpg?v=1755037446&width=1946, 26cf8d599a1a08bbcbbf688e14c9806d5f2381dc2aecdb608998ab22cee2c1b3. Each is a verified retrieval SHA-256; implementation must retain exact bytes. Retained derived review 6cb36e971d38c190422713d61638b5bc531753d5f73bc4f0aefb71b78e63eaf5; Quick Start https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507; depth guide https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905. |

Author geometry directly and analytically from approved manufacturer evidence.
Never image-trace, segment, vectorize, register/align, auto-contour, auto-crop,
derive masks, or run an automated proposal/refine/promote workflow. References
inform operator judgment only.

## Architecture

board.json remains the sole canonical contact inventory and schema version 3.
Each model presentation has one ODR USDZ and one bundled descriptor; the
descriptor model hash equals the USDZ SHA-256. New reusable-unit packages use
descriptor v2. Its nodes use generic contactSlotID values and top-level
contactSlots declares the complete unit-local inventory. Unit-local modelBounds
remain source geometry bounds, never assembled-board bounds. Descriptor v1 is
untouched.

Model media adds optional instances; this feature requires exactly two entries.
Each has equipmentObjectID, nested baseTransform containing finite
nine-decimal translation, unit [x,y,z,w] rotation, and optional reflection:
"x" about unit-bounds centre, plus exact contactIDsBySlotID. Each instance
owns exactly one pose mechanism: suspension in the existing complete
suspension-document shape, or positionTransforms keyed by every board position
ID, with each value containing translation and rotation. There is no top-level
positionTransforms map. Both Pivot instances carry the same exact position-key
set. Do not allow simultaneous legacy media-level and per-instance
orientation/suspension data.

Transform order is normative. For source point p and bounds centre c, apply F
(identity or x reflection about c), then base B(p) = c + Rbase * (F(p)-c) +
tbase. For position transform, ci = B(c), then W(p) = ci + Rposition *
(B(p)-ci) + tposition. Position transforms therefore rotate and translate the
already placed unit about its bounds centre and can exchange Pivot physical
halves. Quaternion norms must be one within decode tolerance; non-finite,
invalid, or non-nine-decimal transforms fail validation.

Illustrative descriptor-v2/media contract; values are concrete examples, not
product measurements:

~~~json
{
  "schemaVersion": 2,
  "contactSlots": {
    "edge": {
      "center": [0.500000000, 0.500000000],
      "facePlaneAABB": {"max": [0.750000000, 0.600000000], "min": [0.250000000, 0.400000000]},
      "nodeIDs": ["unit-edge"]
    }
  },
  "coordinateFrame": "hang-ten-board-v1",
  "modelSHA256": "8b7b1f928d467a40d569f4e6b3f1d1c7a714a6d32eb0b22f5e4c44a1ce59f620",
  "modelBounds": {"max": [0.090000000, 0.030000000, 0.070000000], "min": [-0.090000000, -0.030000000, -0.070000000]},
  "nodes": [
    {"nodeID": "unit-body", "role": "body"},
    {"contactSlotID": "edge", "nodeID": "unit-edge", "role": "contact"}
  ]
}
~~~

This is a minimal hypothetical fixed pair, not product metrology. It shows the
complete per-instance positionTransforms ownership for the sole declared
position, primary:

~~~json
{
  "instances": [
    {
      "baseTransform": {
        "rotation": [0.000000000, 0.000000000, 0.000000000, 1.000000000],
        "translation": [-0.120000000, 0.000000000, 0.000000000]
      },
      "contactIDsBySlotID": {"edge": "edge-left"},
      "equipmentObjectID": "left-ring",
      "positionTransforms": {
        "primary": {
          "rotation": [0.000000000, 0.000000000, 0.000000000, 1.000000000],
          "translation": [0.000000000, 0.000000000, 0.000000000]
        }
      }
    },
    {
      "baseTransform": {
        "reflection": "x",
        "rotation": [0.000000000, 0.000000000, 0.000000000, 1.000000000],
        "translation": [0.120000000, 0.000000000, 0.000000000]
      },
      "contactIDsBySlotID": {"edge": "edge-right"},
      "equipmentObjectID": "right-ring",
      "positionTransforms": {
        "primary": {
          "rotation": [0.000000000, 0.000000000, 0.000000000, 1.000000000],
          "translation": [0.000000000, 0.000000000, 0.000000000]
        }
      }
    }
  ]
}
~~~

Every instance map's keys equal contactSlots exactly; values are unique across
instances, union to board.json contacts exactly, and each belongs to its
equipmentObjectID. Every per-instance positionTransforms map has keys equal to
package positions exactly; the two maps have the same key set.

## Runtime and data flow

The loader verifies descriptor hash and contract before exposing a model. Load
the USDZ once, deep-clone the unit twice with independent geometry/material
copies, apply reflection/base/selected-position transforms, then translate
cloned node identity from slot IDs to canonical board contact IDs. Picking,
highlighting, workout resolution, and accessibility stay canonical-ID based.
Reflection must preserve outward winding, correct normals, and culling.

Containers/transforms, cord nodes, pose cache, and attachment state are all per
instance. A contact or highlight in one unit cannot mutate its peer. Camera
framing is the union of transformed instances and active cords. The existing
single-model path stays byte/behavior compatible.

## Per-board migration rulings

| Board | Final physical-contact and reusable-unit ruling |
| --- | --- |
| Helium | Six contacts: edge-14, edge-22, center-edge-10, center-edge-18, top-jug, back-jug-sloper. Map both source 14 lips to edge-14, both 22 lips to edge-22, then centre 10, centre 18, top jug, rear jug/sloper. Multiple meshes may bind one contact. |
| Light Rail | Exactly four contacts: jug-40-20mm-side, edge-20, jug-40-15mm-side, edge-15. |
| Rock Rings | Eight contacts, four per unit. One canonical physical asset rendered twice, identical and unreflected. Slots: jug, pocket-40, pocket-32, pocket-25. |
| Poker | Preserve/restore all 34 contacts in Hangboards/owl-climb-poker/board.json. Correct the batch omission of face-d-left-deep-rounded-recess and face-d-right-deep-rounded-recess from approved Owl evidence. |
| Penta | Fourteen contacts, seven per unit. One canonical physical asset rendered twice, identical and unreflected. Slots: edge-25, edge-20, edge-15, edge-10, mono, duo, tray. |
| Pivot | Normalize 72 raster presentation records to 18 physical contacts, nine per half. One canonical half rendered twice; right instance reflected. Retain a tracked compatibility/source audit for retired presentation IDs. |

Rock Rings slot mappings are jug -> jug-left/jug-right, pocket-40 ->
pocket-40-four-left/pocket-40-four-right, pocket-32 ->
pocket-32-three-left/pocket-32-three-right, and pocket-25 ->
pocket-25-two-left/pocket-25-two-right. Penta slot mappings are edge-25,
edge-20, edge-15, edge-10, mono, duo, tray to the identically named
left/right canonical IDs. Poker maps each approved photo face to its same-face
canonical prefix (face-a, face-b, face-c, face-d); every direct batch patch
keeps that ID, while the two missing Face D recesses are manually restored to
the two stated canonical IDs. These mappings, the Helium merge mapping above,
and the Pivot mapping below are the required source-to-slot/contact audit.

Pivot's 14 delivered patches per half map to nine physical identities as
follows, identically for left and right: wing crest plus wing inner map to
outer-wedge-pinch; rail lower, rail upper, rail-end outer, and rail-end inner
map to variable-edge; supported lower to medium-crimp; supported upper to
large-crimp; two-finger top plus side to two-finger-pocket; three-finger top to
three-finger-pocket; top sloped to upper-sloped-crimp; side sloped to
outer-sloped-crimp; lower-wave sloper to lower-sloper. Keep this exact
source-patch-to-slot/contact mapping with the retired-ID compatibility audit.

### Suspension

Cords are transient non-pickable metadata, never USDZ/ODR assets. Each
instanced unit may own independent existing-topology suspension and an
invisible display anchor.

- Helium: pairedLeadCord; two evidence-visible exterior leads/end mouths only.
  Preserve front/reverse apertures; infer neither internal connection nor
  twoBranchCord.
- Light Rail: pairedLeadCord; exterior leads/upper entry regions only.
  Underside-mouth inclusion requires independent full-resolution confirmation;
  no hidden vertical bore. Omit old face screws.
- Rock Rings: two independent per-instance pairedLeadCord systems/anchors.
  Preserve roof exits and lateral windows; omit concealed routes, inter-unit
  connection, and disproved central through-bore.
- Penta: two independent paired exterior loops around upper band through the
  existing central ring. Preserve visible two-sided strands; retired small
  passage holes remain absent; invent no channel or knot.
- Poker and Pivot: noDocumentedSuspension. Pulley-kit ropes are not Pivot
  suspension.

### Pivot reauthoring

Reject the delivered Pivot GLB as production geometry but retain it as audited
source material. Astra found no global front/back/top/bottom/handedness
inversion. The root defect is wrong relief: isolated 14–18 mm-proud
collars/rails on a flat plaque, a narrow fin instead of broad integrated
concave wing, localized wing-root normal defects, and six unwanted fastener
holes.

Manually reauthor one half from approved Trango front, close-up, single-board,
and dual-board photos: continuous molded perimeter/ridges, inward-opening
pockets, connected supported-crimp ridges, broad concave wing blended into
body, correct normals, no fastener openings, and retained actual two-finger
opening plus three-finger end window. Overall envelope/rear are explicitly
authored-display-estimate because primary metrology is unavailable.

Expose four selectable states only: batch p1, p2, p3, p5, with full
per-instance translation plus rotation. Batch p4 is manufacturer Orientation 3
Switch transition evidence only, not selectable. Physical IDs remain stable
through rotations and side exchange.

## Error handling

Fail closed to unavailable; never show a raster stand-in. Reject duplicate
instances, descriptor-version mismatch, invalid transforms/reflection,
incomplete/duplicate/cross-object slot maps, incorrect contact union,
simultaneous legacy/per-instance pose metadata, invalid suspension bindings,
hidden-route claims without evidence, and position-transform keys not exactly
equal to package positions on each instance or not exactly equal between the
two instances.

## Testing and acceptance

TDD is mandatory. Observe each descriptor/compiler/importer Python test, Swift
decode/validation test, and runtime instancing test fail before production code.
Cover descriptor v2, importer/compiler, reflection/winding, canonical
picking/highlight isolation, per-instance position rotation/translation,
independent cords, clearance, accessibility, and union framing.

Full verification runs retained model-tool pytest, package validation/status,
final inventory, cord audit, orientation audit, production cord clearance,
hard-cut scans, Swift tests/build, isolated iOS Simulator validation, and
Astra front/oblique/reverse/every-canonical-pose side-by-side review. Pivot
acceptance: 18 contacts; one half/two instances; four p1/p2/p3/p5 positions;
continuous relief/broad wing matching official photos; no mounting/screw holes
or hardware; real finger windows retained; normal/winding tests pass.

Track source manifests, exact source-to-slot/contact mappings, hashes,
supersession/compatibility rulings, audits, and acceptance reports in
docs/source-audits. Generated Blender/output artifacts go only under an
owner-prefixed .context path using owner learned-giraffe, and are cleaned by
exact name after verification.

## Alternatives

Reject baked duplicate units and separate per-unit assets: they violate the
single-object rule and create storage/runtime inconsistency. Reject static-only
Pivot: it loses four existing orientations.

## Out of scope

No training-routine changes, unsupported contacts, inferred hidden topology or
metrology, multi-model-presentation support, or raster fallback.

## Implementation-impact file areas

- Tools/HangboardModels/contact_model_descriptor.py (NodeBinding,
  ModelDescriptorV1, compile_descriptor) and
  Tools/HangboardModels/contact_model_package.py (validate_tagged_scene,
  compile_model_package) gain v2 reusable-unit support while retaining v1.
- Tools/HangboardModels/import_contact_model_source.py
  (verify_source_manifest, validate_mapping, import_package) owns import/audit
  maps; test_contact_model_descriptor.py, test_contact_model_package.py, and
  test_import_contact_model_source.py get failing-first coverage.
  Tools/HangboardPackages/src/hangboard_packages/board_catalog.py owns matching
  Python package-schema validation.
- HangTen/Models/BoardPackageStore.swift (loadPackage, loadModelDescriptor,
  media/suspension decoding), HangTen/Models/TrainingModels.swift, and
  HangTen/Models/BoardPackageWriter.swift own strict Swift validation,
  serialization, and v1 compatibility.
  HangTen/Views/BoardModelView.swift (BoardModelLoader, BoardModelScene,
  hit testing/highlights) owns one-load/two-clone instancing, reflection,
  identity, state isolation, and framing. HangTen/Views/SuspendedBoardPresentation.swift
  owns per-instance suspension presentation/cord assembly. If
  HangTen/Models/SuspensionProfiles.swift is touched, retain its narrower
  solved-profile calculations; it does not own per-instance runtime state.
- HangTenTests/BoardPackageStoreTests.swift, HangTenTests/BoardModelTests.swift,
  HangTenTests/BoardPackageWriterTests.swift, and
  HangTenTests/SuspendedBoardPresentationTests.swift cover decoder,
  serialization, SceneKit, and suspension-presentation behavior.
  Tools/HangboardPackages/src/hangboard_packages/cord_audit.py plus
  test_model_orientation_inventory.py, test_cord_audit.py,
  test_approved_board_packages.py, and test_model_first_packages.py enforce
  suspension evidence, orientation, inventory, and hard cuts.
- Required audit surfaces are
  docs/source-audits/2026-09-13-model-hangboard-cord-audit.json,
  docs/source-audits/2026-09-13-model-hangboard-cord-audit.md,
  docs/source-audits/2026-09-11-3d-board-orientation-audit.md, and
  docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json.
- Only the six target Hangboards/*/board.json packages/assets and new tracked
  docs/source-audits records receive migration work.
