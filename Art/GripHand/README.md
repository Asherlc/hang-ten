# Blender grip hand

`GripHand.blend` is the editable 3D hand used by Hang Ten. It derives from the
MIT-licensed generic right-hand asset in WebXR Input Profiles, copyright 2019
Amazon. The unmodified source is bundled as `SourceHand.glb`; the full license is
in `LICENSE.md` and the repository third-party notices.

- [Source GLB](https://raw.githubusercontent.com/immersive-web/webxr-input-profiles/main/packages/assets/profiles/generic-hand/right.glb)
- [Assets license](https://github.com/immersive-web/webxr-input-profiles/blob/main/packages/assets/LICENSE.md)

## Authoring and reproduction

Requires Blender 5.2. Rebuild from the included source without downloads:

```sh
blender --background --factory-startup --python Art/GripHand/build_hand.py
python3 Art/GripHand/validate_export.py
```

The rebuild replaces edits in `GripHand.blend`. To preserve manual edits, open
that document, select `GripHandRig`, enter Pose Mode, and choose the named action
in the Action Editor. Each action contains its pose at frame 1. Edit the
`GripHandSurface` cage or source deform weights as needed, retaining the
post-armature subdivision modifier and the five `highlight_*` point attributes.
Export the edited document directly:

```sh
blender --background Art/GripHand/GripHand.blend --python Art/GripHand/export_hand.py
python3 Art/GripHand/validate_export.py
blender --background --factory-startup --python Art/GripHand/review_grips.py
```

The review script renders the actual exported surfaces under the current
workspace's `.context/<workspace>-xr-grip-surface-sheet.png`.

## Surface and runtime contract

The source has 1,360 vertices and a flat list of 25 joint transforms. The build
adds parent chains while preserving those transforms and supplied skin weights.
Welding coincident import seams yields 1,159 cage vertices. Compatible triangle
pairs become 1,141 quads plus 32 remaining triangles. A wrist-cut crease preserves
the flat end. Two Catmull-Clark levels run **after** the armature, smoothing the
localized joint bends without bending whole finger segments like rubber.

The exporter evaluates each action through that complete modifier stack. Schema
2 stores shared triangle indices, digit IDs, highlight strengths, and each
pose's positions and normals: 18,642 vertices, 37,280 triangles, 21 poses. The app
uses these surfaces directly; no runtime skinning approximation is required.
Fixed polygon-fan diagonals keep triangulation identical across actions.
The JSON also embeds source attribution and the complete MIT notice so they
travel with the geometry in the app bundle.

Coordinates are Y-up along the fingers, negative X toward the thumb, and
positive Z toward the palm, approximately 4.2 units tall. The reflected coordinate
conversion reverses triangle winding and transforms normals. Digit IDs are
0 palm, 1 thumb, 2 index, 3 middle, 4 ring, 5 pinky. Highlight weights subdivide
from supplied phalanx influences; a final smoothstep from .35 to .95 confines
color to fingers while preserving a soft transition into the neutral palm.

Actions are `Neutral`, `OpenHand`, `HalfCrimp`, `FullCrimp`, `Sloper`, and
`Pocket0` through `Pocket15`. Pocket bits are index=1, middle=2, ring=4, pinky=8.
A nonempty selection keeps those fingers open and curls only unused fingers.
Pocket contact controls are independent from the `OpenHand` illustration, so
refining its index bend does not change any pocket selection.
`Pocket0` uses the all-open surface for unknown metadata, with no highlighted
fingers supplied by the app. Pocket count never implies a particular finger pair.
All thumb bones remain relaxed at their supplied rest transforms in every pose.

## Pose evidence and limits

Page 11 of [Lattice's home-adaptation guide](https://latticetraining.com/app/uploads/2020/03/Lite-Guide-to-home-adaptations.pdf)
informs the broad open-hand and half-crimp shapes. The open-hand illustration
adds a gentle, visible index middle-joint bend requested during visual review;
this is an explicitly illustrative adaptation of the source, whose index is
described as straight or nearly straight. The half-crimp uses bent PIP joints
on all four fingers and a relaxed thumb.
Index/middle/ring retain the reviewed prototype's fitted pad positions. The pinky
uses a visibly bent illustrative posture requested during review, with its base
rotation adjusted to meet the same support plane. Numerical rotations include the
source bind orientation and are **illustrative adaptations**, not anatomical
measurements or training prescriptions. The prototype's common support-plane
fit is a visual construction, not a contact simulation.

`FullCrimp` is an illustrative tighter finger posture with the thumb deliberately
relaxed to match the requested presentation. More closed middle joints and
modest distal extension create a lower fingertip profile, distinguishing it from
the half-crimp's flatter shelf. It does not reproduce the thumb
wrap in Lattice's full-crimp photograph. Sloper and pocket poses are also
illustrative shape adaptations for existing app grip types. No routine metadata,
exercise prescription, or coaching text is added by this asset.

This is a schematic hand with limited nail and crease detail. Automated checks
validate topology, normals, all finger combinations, and stable selected distal
segments; they do not establish anatomical accuracy or user visual acceptance.
