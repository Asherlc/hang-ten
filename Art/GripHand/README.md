# Blender grip hand

`GripHand.blend` is the editable 3D hand used by Hang Ten. It derives from the
MIT-licensed generic right-hand asset in WebXR Input Profiles, copyright 2019
Amazon. The unmodified source is bundled as `SourceHand.glb`; the full license is
in `LICENSE.md` and the repository third-party notices.

- [Source GLB](https://raw.githubusercontent.com/immersive-web/webxr-input-profiles/main/packages/assets/profiles/generic-hand/right.glb)
- [Assets license](https://github.com/immersive-web/webxr-input-profiles/blob/main/packages/assets/LICENSE.md)

## Authoring and reproduction

The app's `HangTen/Resources/GripHand/hand-mesh.json` is an ignored build output.
Export the retained editable source with pinned Blender 5.2.0:

```sh
rtk proxy bash scripts/export-grip-hand.sh
```

The full `scripts/build-runtime-assets.sh` entrypoint runs this export together
with native board compilation and Swift plan export. CI delivers the generated
JSON in its runtime artifact. Commit the editable Blender source and evidence,
not the exported JSON; `SourceHand.glb` and its license remain retained inputs.

To deliberately rebuild the editable source from the included upstream asset:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 --python Art/GripHand/build_hand.py
rtk python3 Art/GripHand/validate_export.py
```

The rebuild replaces edits in `GripHand.blend`. To preserve manual edits, open
that document, select `GripHandRig`, enter Pose Mode, and choose the named action
in the Action Editor. Each action contains its pose at frame 1. Edit the
`GripHandSurface` cage or source deform weights as needed, retaining the
post-armature subdivision modifier and the five `highlight_*` point attributes.
Export the edited document directly:

```sh
rtk proxy bash scripts/export-grip-hand.sh
rtk proxy blender --background --factory-startup --python Art/GripHand/review_grips.py
```

The review script renders the actual exported surfaces under the current
workspace's `.context/<workspace>-xr-grip-surface-sheet.png`.

## Surface and runtime contract

The authoring script reconstructs finger parent chains while preserving the
upstream joint transforms and skin weights, welds coincident seams, and smooths
the cage with post-armature subdivision. The exporter evaluates every action
through that modifier stack. Schema 2 retains shared triangle indices, digit
IDs, highlight strengths and each pose's positions/normals; the app uses these
surfaces directly. Fixed polygon-fan diagonals keep triangulation identical
across actions.
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
`Pocket0` and `Pocket15` share the all-open surface. The app uses explicit finger
metadata when present and an assumed four-finger display otherwise, labeled
`4 fingers (assumed)`. That default does not change routine or recording
metadata. Pocket count never implies a particular finger pair.
All thumb bones remain relaxed at their supplied rest transforms in every pose.

## Pose evidence and limits

Page 11 of [Lattice's home-adaptation guide](https://latticetraining.com/app/uploads/2020/03/Lite-Guide-to-home-adaptations.pdf)
informs the broad open-hand and half-crimp shapes. The open-hand illustration
adds a gentle index middle-joint bend as an illustrative adaptation; the source
describes that index as straight or nearly straight. The half-crimp bends the
PIP joints of all four fingers and keeps the thumb relaxed. Pad placement and a
common support plane are visual constructions for legibility. Numerical
rotations include the source bind orientation and are not anatomical
measurements, training prescriptions or a contact simulation.

`FullCrimp` is an illustrative tighter finger posture with the thumb deliberately
relaxed as a display adaptation. More closed middle joints and
modest distal extension create a lower fingertip profile, distinguishing it from
the half-crimp's flatter shelf. It does not reproduce the thumb
wrap in Lattice's full-crimp photograph. Sloper and pocket poses are also
illustrative shape adaptations for existing app grip types. No routine metadata,
exercise prescription, or coaching text is added by this asset.

This is a schematic hand with limited nail and crease detail. Automated checks
validate topology, normals, all finger combinations, and stable selected distal
segments; they do not establish anatomical accuracy or user visual acceptance.
