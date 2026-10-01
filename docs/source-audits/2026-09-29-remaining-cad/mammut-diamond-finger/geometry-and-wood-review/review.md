# Mammut Diamond Finger: geometry and runtime wood review

The revised Mammut Diamond Finger geometry and reused runtime wood finish have passed final export, installed-app checks and post-promotion test suites. The exported surface matches the expected native facets, is watertight and consistently wound, and remains unbound without materials or textures. **Human review #6 remains pending.** [Current validation](runtime-validation.json) binds the final identities and results; the earlier native diagnostics and reviews remain historical evidence.

Review the [actual app before/after comparison](app-before-after.png), [final front/side/top comparison](front-side-top-comparison.png), [compiled raking comparison](compiled-previews/comparison-raking.png), and [native section diagram](native-final/previews/native-central-and-lateral-sections.png). The shared wood finish is golden tan, not a calibrated factory colour; cavity depths and floor slopes remain display estimates.

The [copy manifest](retained-evidence-manifest.json) records original workspace paths, sizes and SHA-256 values for the retained raw artifacts. The original 35 historical copies remain byte-identical. Every copy was checked byte-for-byte. Raw reports retain their original status and scratch references; this review supplies the later status without rewriting that evidence. Large mesh JSON, candidate CAD files, author programs, debug sources and revision-1 preview duplicates are deliberately omitted.

## Primary evidence and supported geometry

The [full manufacturer press document](sources/manufacturer-press-release.docx), [extracted text](sources/press-release-text.txt), three complete embedded images and [source provenance](sources/press-provenance.json) are retained together. The publisher is Mammut; the original [press DOCX](https://cdn.uc.assets.prezly.com/da46d83b-e3f0-484b-b349-2047c1a0da6c/-/inline/no/202003_Mammut_DiamondFingerHangboard.docx) has SHA-256 `7312bb772da797aca3cfa7f6368761cb5a9c97cfda00f19537888fa2ac7fcc1f`. Its product facts state 85 cm width and walnut wood. Additional manufacturer research was user-authorized. The embedded product picture repeats the retained front view; it does not supply a manufacturer side view.

The exact-revision [manufacturer product photograph](https://static.mammut.com/master/2060-00020-7458_main_75743.jpg) and [manufacturer manual](https://static.mammut.com/file/2060-00020_man_en_070420_DiamondFingerHangboard_Manual.pdf) remain the visual evidence referenced in [source reasoning](native-author/source-reasoning.md). Their already-retained hashes are respectively `d08c0f36233171789ff450f4429646079f67ca2506da2f794ecf61089982014f` and `0ada1438277dae39cf96e45dc72f9d0aabe383502718368f143212bf8e51b024`.

The sources support flatter machined terraces and straight chamfers, narrower upper ends, three lower lobes with straight-sided notches, horizontal pill-shaped openings and slots, Z-shaped lateral shelves, an angular central tray with a lower dip, upper inset steps, and a central sloper. These features were deliberately authored as native geometry; no pixels were measured, traced or registered.

Only the 850 mm overall width is manufacturer-backed here. The 196 mm height, 78 mm thickness, whole side profile, cavity depths, floor slopes, wall tapers, bevel widths and round radii are operator-selected display estimates. The 42 mm mono depth, 0.8 mm rounds and specific floor angles are not manufacturer specifications. The sampled tray/shelf recess depths in the diagnostic reports describe the authored CAD, not a measured physical board. The central and lateral floors deliberately tilt toward the front; the sources do not establish that angle. This choice must be disclosed during human review.

## Native revision and diagnostic comparisons

Opus reviewed native revision 2 with source SHA-256 `695845291f92314d7ddc6369f663d25312eb52c7c75283b75e2b9e1f7a29ffa4`. The before mesh is prior committed USDZ `c79b5561c618bf7f1f819218d325db54ddf59de38a5000b0e42f5131e0457e54`.

- [Front comparison](native-author/previews/comparison-front.png), [side comparison](native-author/previews/comparison-side.png), [top comparison](native-author/previews/comparison-top.png).
- [Oblique comparison](native-author/previews/comparison-oblique.png), [raking comparison](native-author/previews/comparison-raking.png), [central and lateral sections](native-author/previews/native-central-and-lateral-sections.png).
- [Authored design](native-author/authored-design.json), [native verification](native-author/native-verification.json), [sampled native-versus-mesh ray proof](native-author/native-mesh-ray-proof.json), [original revision-2 proof manifest](native-author/revision-2-proof-manifest.json).

The retained native report records one valid solid, 39 fully constrained sketches, all 16 existing contacts on the wood boundary, no positive-area contact overlap, zero bilateral symmetric-difference volume and preserved embedded board metadata. A mono-depth edit propagates to both mirrored contacts and restores without material difference. The 12 sampled native/diagnostic-mesh first-hit comparisons agree within 4.32e-9 mm. This is sampled proof of the candidate recesses, not official export validation. OpenCascade conservative face bounds overrun the authored extent; the diagnostic tessellation is 850 × 78 × 196 mm.

Official compiler checking subsequently identified a central-rail contact clipping boundary at X ±165 mm that crossed unsplit body triangles. The native seam correction is now retained under `native-final/` and passes the unchanged compiler check described below. The historical revision-2 diagnostics remain separate from that later proof.

## Independent Opus review

The retained raw responses are [review 1](opus/review-response.md), [review 2](opus/review-response-2.md) and [review 3](opus/review-response-3.md); their corresponding raw activity exports are [activity 1](opus/activity.json), [activity 2](opus/activity-2.json) and [activity 3](opus/activity-3.json). The advisor provider was `claude/claude-opus-5-5` (agent `b5c60ebf-8de3-4db4-a22d-44bb8ba2db5e`). Earlier findings are historical and preserved unchanged.

Review 3 clears the hash-pinned revision-2 geometry for **app and human review only**. It does not approve manufacturing accuracy or substitute for human acceptance. It asks the app reviewer to inspect both rail-to-ledge corners for dark slivers, judge the subtle edge rounding with wood enabled, and consider the unsupported floor slopes. The section graphic's red “floor” labels measure back-wall depth at those sampled heights; the raw image is retained without silently changing its labels. The nine reported zero-area contact touch pairs are touching boundaries, not positive-area overlap.

## Reused runtime wood system

The requested wood appearance reuses the existing finish system from commit `6126228e8c44c5832982acc09e10ce47809f50c0`, including the existing procedural wood shader. Package-owned `media.display.surfaceFinish: "wood"` selects it; no new appearance schema or separate wood renderer is introduced. This is the existing generic wood display finish, not a calibrated walnut grain or stain reproduction. USDZ meshes must remain unbound, without materials or textures; wood is applied by the app renderer.

The retained [finish metadata proof](wood/finish-metadata-proof.json) and [setter log](wood/manifest-edit.log) show the historical pre-seam runtime copy `dee7bbda64ccc3025dc919e31f301b35439491c0cb747ce31aea7ff63bbf3681` changed only the embedded `surfaceFinish` from the reviewed `695845…` candidate. Other board fields and archive members were preserved. This proof predates the native seam correction. The later seam-corrected finish proof is retained under `wood-final/`, as described below; neither historical hash is asserted to be the final published source.

## Seam-corrected native proof

The [partition proof manifest](native-final/partition-proof-manifest.json) binds seam-corrected source `5e06a1e7ae4f6bee8391605f61395ff86807e4234a54d6b8b2d46c015fa4ddd8`. The [partition fix proof](native-final/partition-fix-proof.json) records zero forward and reverse native body difference and zero forward and reverse differences for every contact compared with the Opus-reviewed revision. The new seams and native face binding correct export partition boundaries; they do not change the physical shape. The final [authored design](native-final/authored-design.json), [native verification](native-final/native-verification.json), [ray proof](native-final/native-mesh-ray-proof.json) and [source reasoning](native-final/source-reasoning.md) are retained separately from the original revision-2 records.

The isolated unchanged compiler `--check` passed all ten checks in 385.29 seconds; [invocation](native-final/partition-compile-check/invocation.json), [raw log](native-final/partition-compile-check/raw.log) and [report](native-final/partition-compile-check/report.json) retain the exact command and output. It reports model `736b9390c36ba8dfadbc8d272db42a3c79a8f61d64d9142167fc67faa2eddd12`, 106,272 triangles, 17 nodes and the same 16 contacts. Its `published: false` remains significant: this is an isolated source check, not final runtime publication.

Updated diagnostic [front](native-final/previews/comparison-front.png), [side](native-final/previews/comparison-side.png), [top](native-final/previews/comparison-top.png), [oblique](native-final/previews/comparison-oblique.png) and [raking](native-final/previews/comparison-raking.png) comparisons are retained. The [corrected section diagram](native-final/previews/native-central-and-lateral-sections.png) labels the sampled values “recess depth”. These are still native diagnostics, not final app screenshots. All floor-angle and dimensional estimate qualifications above continue to apply.

The [final finish metadata proof](wood-final/finish-metadata-final-proof.json) and [setter log](wood-final/manifest-edit-final.log) bind the seam-corrected source to runtime wood source `06fb78ae8190d4ee90fdc343889940df1a33ddc552e5b866242eb55fae2158fe`. Only the embedded `surfaceFinish: "wood"` field changes; all other board fields and archive members are preserved. Final runtime export, promotion and installed delivery have passed, as recorded below.

## Final runtime export verification

The final runtime source compiled through all ten unchanged compiler stages, including source reopen/recompute, surface partitioning, exported-asset reopen, descriptor derivation and staged package validation. Its exact identities are:

| Artifact | SHA-256 |
| --- | --- |
| Runtime native source | `06fb78ae8190d4ee90fdc343889940df1a33ddc552e5b866242eb55fae2158fe` |
| Exported USDZ | `736b9390c36ba8dfadbc8d272db42a3c79a8f61d64d9142167fc67faa2eddd12` |
| Exported descriptor | `3129a1de3753f36df977336fc2979cd3a579981d5a8938f76c5415704bdd1099` |

The fresh native-only and wood-metadata-only compiles produce the same USDZ bytes. The final asset contains 17 meshes, 16 logical contacts and 106,272 triangles. Comparison against the expected native tessellation matches every facet, with zero duplicate facets, using 1e-12 m coordinate-noise quantization and a 2e-12 m matching tolerance; the maximum matched coordinate difference is approximately 1e-12 m. The merged surface has 53,138 vertices, is watertight and consistently wound, and has Euler number 2. Thus the seam correction preserves the native surface through export without the earlier clipping gap.

The USDZ archive contains only `stage.usdc`: zero material prims, zero shader prims and zero material bindings. Its runtime bounds are approximately X ±0.425 m, Y −0.096 to 0.100 m and Z 0 to 0.078 m. These validate the authored display extent; they do not turn estimated height, thickness, depths or slopes into manufacturer measurements. The app supplies the reused procedural wood finish; the installed-app and runtime tests below verify contact highlighting/restoration and scene isolation.

The durable [export verification](runtime-proof/export-verification.json), [final compiler report](runtime-proof/compile-final.json), [raw compiler log](runtime-proof/compile-final.log) and [promotion report](runtime-proof/promotion-report.json) retain the exact proof. The final compiler report's `published: true` refers to its scratch export destination `runtime-assets-final/`, while the earlier isolated check retains its original `published: false`. Subsequent installed delivery is verified separately below; historical raw reports remain unchanged.

## Renderer and schema evidence

[Schema verification](wood-schema/verification.json), [upstream adoption proof](wood-schema/upstream-adoption-proof.json), raw decoder red/green logs, the expanded Python red log and the relevant Python collection log are retained under `wood-schema/`. They document the implementation-stage checks; they are not a claim that the final promoted package has completed all integration tests.

The [renderer adoption proof](wood-renderer/renderer-adoption-proof.json) records reuse of the existing shader and finish factories. The raw [independent review](wood-renderer/independent-renderer-review.md) found a hierarchical selector issue. Its original pending status and the subsequent [implementation review](wood-renderer/selector-fix/implementation-review.json) are preserved unchanged. The separate [review closure](wood-renderer/review-closure.md) links the actual failing and passing iOS results: the nested selector regression changes from one failing test to one passing test. Initial wood/highlight/restoration and scene-isolation checks likewise change from two failing tests to two passing tests. This closes those focused findings. The subsequent final package and app results are recorded below; human acceptance remains pending.

## Final app and integration verification

The [installed-app provenance](integration/installed-app-provenance.json) confirms the built and installed binaries are byte-identical, with SHA-256 `db97d82b316e68750a8d70726fc48df6e6fffa4523a903399508732cfcb78315`, bound to the final native source above. The [app validation](app/after-app/validation.json) and [real-drag record](app/after-app/extra-validation.json) retain full simulator frames and accessibility evidence. Two actual drag orbits changed projected contact positions while preserving the selected Upper inset step right contact.

- Actual app: [unselected wood](app/after-app/wood-unselected.png), [left jug](app/after-app/jug-left.png), [central tray](app/after-app/center-tray.png), [right inset](app/after-app/inset-right.png), [first orbit](app/after-app/wood-orbit-left.png), [second orbit](app/after-app/wood-orbit-right.png).
- Prior app: [left jug](app/before-app/jug-left.png), [central tray](app/before-app/center-tray.png), [right inset](app/before-app/inset-right.png). The [comparison provenance](app-comparison-provenance.json) identifies the before/after composition.
- Official exported geometry: [front](compiled-previews/comparison-front.png), [side](compiled-previews/comparison-side.png), [top](compiled-previews/comparison-top.png), [oblique](compiled-previews/comparison-oblique.png), [raking](compiled-previews/comparison-raking.png), with [compiled-preview provenance](compiled-previews/provenance.json).

The full post-promotion iOS run reports **1,278 passed, 3 skipped, 0 failed** ([summary](integration/ios-summary.json), [raw log](integration/ios-tests.log)). The relevant full Python collection reports **706 passed, 10 skipped, 0 failed** ([report](integration/python-test-report.json), [raw log](integration/python-tests.log)). [Delivery parity](integration/delivery-parity.json) passes for 64 bundled packages, 58 model packages and 60 model assets; shared canonical Apple/Android staging matches source. This checkout has no Android app runtime, so this is staging parity, not an Android rendering test. Other packages and unrelated board fields remain unchanged according to [current validation](runtime-validation.json).

## Final Opus app review and human review #6

[Opus review 4](opus/review-response-4.md) and its [raw activity](opus/activity-4.json) review the final app frames and compiled comparisons at the current source/model/descriptor hashes. It finds no source-supported blocker and recommends presenting #6 for human review. The earlier three reviews remain unchanged as the history of the native revisions and their resolved concerns.

In the actual app, Opus finds clean rail-to-shelf corners and upper lip through both orbit views. The jagged slivers seen in offline previews do not appear as app defects and are consistent with preview draw ordering. This is not a claim that subpixel flicker has been excluded: the reviewer should still orbit slowly on a device and inspect both corners.

The shared finish is golden tan with subtle grain; it is not a factory-colour or walnut-grain match. Lighting makes some recesses appear shallow even though the native sections and exported geometry establish real cavities. Height, thickness, all cavity depths, floor tilts, wall tapers, rounds and the side profile remain operator-selected display estimates. Only the 850 mm width and walnut material are manufacturer-backed numerical/material facts here. The inherited subtitle referring to 21 surfaces versus 16 selectable contacts remains unresolved; no additional grips were invented.

**Human review #6 is pending.** The reviewer should judge the revised terraces, openings and silhouette, the generic wood colour, and the estimated depths/floor slopes using the app and comparison links above. Technical validation and Opus review do not constitute human acceptance or a claim of manufacturing accuracy.

Packet assembly used workspace-owned files only and started no external resources.
