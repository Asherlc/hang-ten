# Plateau #13 immutable material partition handoff

Owner: `placid-badger`. Scratch source and all three exported pairs are pinned in [immutable-material-handoff.json](immutable-material-handoff.json) and set read-only. Source SHA-256: `b1c701af3ea5515b73e5b3641612f15953ecc3fb109332e95470bd70f9da7986`. Astra owns the separate final seated-route sidecar, source-bound collision exports, native dimension edit/restore, and whole-view review. This handoff deliberately has no adjacent final sidecar.

Five native `PartDesign::SubShapeBinder` features select Astra's exact final-body metal/blocker faces. Their attachment role makes those surfaces non-pickable. `HangTenUseBodyTriangles=true` exports the body's already classified triangles for exact seams. The unchanged full fused native `plateau_body` still supplies the collision shape; its exported residual surface and `plateau_edge_18` receive the existing wood selector. Metal and the unspecified 3D printed blocker remain neutral. All three displays add only `surfaceFinish: neutral` and `woodNodeIDs: [plateau_body, plateau_edge_18]` through the supported manifest setter.

[Fresh native proof](fresh-native-preservation-proof.json) reopens/recomputes the final scratch source, confirms exact BRep equality for all 47 original native features, and verifies all five binders' support paths, selected original faces, areas and zero native face distance. [Archive/metadata proof](native-preservation-and-finish-proof.json) separately confirms all 75 original non-Document payloads are byte-identical and all 47 original XML object definitions preserve. The raw native save is retained at `raw-native-authoring-save.FCStd`: FreeCAD initially reserialized 31 original BRep payloads, which were restored from the immutable baseline before metadata embedding. No byte-identical native-save claim is made.

All three compile reports bind this exact source, retain source bytes unchanged, and measure `edge-18` at 18/15/10 mm. Root's independent exported mesh/descriptor check passed at `../root/independent-export-validation.json`: exact prior/current physical triangle union and contact triangles, no duplicate triangles, exact fresh descriptor reconstruction, finite unit normals, and unbound meshes. Node triangles are:

| Presentation | Oak body | Oak contact | Neutral metal | Neutral blocker | Total |
|---|---:|---:|---:|---:|---:|
| 18 mm | 72 | 66 | 786 | 0 | 924 |
| 15 mm | 74 | 66 | 790 | 18 | 948 |
| 10 mm | 74 | 66 | 790 | 18 | 948 |

All source-backed facts, contact identity/regions, and three effective-depth positions are unchanged. There were no canonical/shared renderer/solver changes, Simulator operations, HTTP resources, broad tests, generic builds, current app frames, or iOS test cases in this lane. [Cleanup/scope proof](full-cleanup-and-scope-proof.json) freshly verifies six owned process groups and nine exact TMP/export-staging paths absent; all eight canonical files and five reserved shared files stayed unchanged at that checkpoint. Human acceptance and current app appearance remain unverified.
