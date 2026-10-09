# 3D grip hand model

The editable source is `Art/GripHand/GripHand.blend`, a stylized schematic hand adapted from the Immersive Web [WebXR Input Profiles generic right hand](https://github.com/immersive-web/webxr-input-profiles/tree/main/packages/assets/profiles/generic-hand). The upstream asset is MIT licensed, copyright Amazon.com, Inc. or its affiliates, 2019. See [the asset README](../Art/GripHand/README.md) and [third-party notices](../THIRD_PARTY_NOTICES.md) for the source, attribution, and reproducible Blender workflow.

`HangTen/Resources/GripHand/hand-mesh.json` is generated and ignored by Git.
`scripts/export-grip-hand.sh` exports the retained editable source using pinned
Blender 5.2.0; `scripts/build-runtime-assets.sh` includes that step before app
builds, and CI delivers the JSON in its producer artifact. Commit the editable
source, upstream provenance and licenses. See
[generated artifacts](GENERATED_ARTIFACTS.md).

The app displays finite 3D surfaces evaluated in Blender after posing and smoothing. This preserves the authored joint shapes without approximating Blender's modifier stack through runtime linear skinning. The surfaces remain fully rotatable 3D geometry; they are not rendered images. The thumb stays relaxed beside the hand in every illustration.

Only `HangTen/Resources/GripHand/hand-mesh.json` ships in the app. `GripHandModelView` validates and shares the decoded asset, creates geometry as a pose is requested, and caches at most three surfaces per view. Missing or corrupt assets show “3D hand unavailable.” The renderer mirrors the left mesh's positions, normals, and triangle winding so both sides keep the same material lighting. The paired view angles the hands in opposite directions to reveal finger curl and spaces them from the current pose's bounds so the thumbs stay apart. The default camera fits the actual displayed pose, including the short wrist. Tapping a compact workout card opens an inspector with rotation, zoom, and reset, using side-by-side controls in landscape.

## Export contract

The JSON uses `schemaVersion: 2`. Shared `indices` contain triangle vertex indices. Each vertex has a `digitIndices` label (`0` palm, `1` thumb, `2` index, `3` middle, `4` ring, `5` pinky) and a `highlightWeights` value from zero to one. Four one-hot vertex channels and a selected-finger shader uniform preserve exact membership while interpolating smooth colors. Palm and thumb remain neutral.

`poses` maps each name to an object with flat XYZ `positions` and `normals` arrays. Every surface uses the same vertex count and triangle topology. Y is upward along the fingers, X is lateral with the thumb negative, and positive Z is palmward. There are no exported bone transforms or runtime skin weights in this contract.

Required surfaces are `Neutral`, `OpenHand`, `HalfCrimp`, `FullCrimp`, `Sloper`, and `Pocket0` through `Pocket15`. Pocket names encode membership: index is bit 1, middle bit 2, ring bit 4, and pinky bit 8. For example, `Pocket6` keeps middle and ring available and tucks the unused index and pinky. `Pocket0` and `Pocket15` share the all-open surface. Runtime pose selection uses exact fingers when supplied. A count-only configuration leaves every finger neutral and uses the all-open pocket surface; a count does not select a particular subset. An omitted configuration retains the four-finger display default. Other postures use one surface regardless of highlight selection.

The loader rejects unsupported schema versions, missing required poses, inconsistent position/normal lengths in any pose, out-of-range triangle/digit indices, non-finite values, and missing or out-of-range highlight weights before GPU upload.

## Visual interpretation and source boundary

The model is a schematic illustration, not anatomical measurement or new training guidance. The primary visual reference is Lattice Training's [A Lattice Guide to Home Training](https://latticetraining.com/app/uploads/2020/03/Lite-Guide-to-home-adaptations.pdf), PDF page 11, comparing open, half-crimp, and full-crimp positions. The finger relationships inform the authored open and crimp shapes. All numeric angles, mesh dimensions, smoothing, camera placement, sloper curvature, and pocket rendering are illustrative adaptations chosen for legibility. Keeping the thumb relaxed in the full-crimp illustration is an intentional display adaptation; it does not reproduce the reference's thumb placement.

The source does not prescribe arbitrary finger subsets, numerical model angles, or the model's pocket/sloper shapes. `GripHandPose` reads a routine's `GripType` and `FingerConfiguration`. Exact `{engagedFingers: [...]}` configurations control highlights. Custom routines can instead store `{count: N}` for one to four fingers without specifying identities; these configurations show the athlete’s count with neutral highlights. The decoder rejects empty exact sets, out-of-range counts, and payloads containing both representations. An omitted configuration displays all four fingers and labels them `4 fingers (assumed)`. This display default is not a sourced training prescription and does not fill the omitted routine or recording field. The thumb is never highlighted because the finger-configuration schema has no thumb member.

## Validation

`GripHandCueCardTests` checks explicit finger subsets, count-only captions and neutral highlights, pocket bit selection, the display default, posture selection independent of highlights, left/right labels, evaluated surfaces, and rejection of damaged schema-v2 buffers. A passing contract test does not establish anatomical realism or user visual acceptance.

In DEBUG builds set `HANGTEN_REVIEW_GRIP_MODEL=1` to inspect both hands. Optional `HANGTEN_REVIEW_GRIP_POSE` uses a `GripType` raw value and `HANGTEN_REVIEW_GRIP_FINGERS` is a comma-separated list (`index,middle,ring,pinky`); an empty string demonstrates the assumed four-finger display. The controls alter this isolated fixture. Review open, half, full, sloper, an explicit two-finger pocket and a pocket with omitted fingers; rotate and reset the model, then review compact cues in portrait and landscape workouts.
