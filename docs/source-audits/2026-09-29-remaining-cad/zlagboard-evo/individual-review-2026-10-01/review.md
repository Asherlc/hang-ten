# #20 Zlagboard.Evo individual review

**Human acceptance: pending.** This review corrects the existing native model's top lips, top-contact coverage, wood finish and viewing angle.

## Evidence and preserved facts

The approved [whole manufacturer image and annotated chart](../sources.json) show seven top contact regions and two rows of seven pockets. The chart supports the 20° and 32° top slopes and 20/25/30/35 mm pocket depths. All 21 contact identities and source-backed metadata are preserved. The 700 × 120 × 42 mm envelope comes from the prior display asset, not a published manufacturing drawing. Unspecified mouth sizes, placements, interior slopes, jug profiles and rounding remain display estimates. No source image was measured, cropped, traced, segmented or registered. Mounting hardware, phone holder and logo remain omitted under the display policy.

## Narrow native corrections

Whole manufacturer photography shows rounded top lips and trough transitions where the initial native export had sharp intersections. Two native `Part::Fillet` features now round six trough transitions by 2 mm and five front lips by 1 mm. Both radii are operator-selected display estimates. The seven existing top profiles, published angles and all fourteen pocket features remain in the native dependency tree.

The original outer jug contact skins omitted their flat crest strips. Both crests, their actual outer rounded top corners and the new adjoining blends now belong to the existing left/right jug contacts. All 21 contact binders reference actual final body faces, with no shared face assignments. All fourteen pocket surfaces retain their previous face geometry and areas. An independent comparison of the saved old/new BREP members found exactly zero added and removed area in both directions, with zero depth change; see `compiler-final/pocket-surfaces.json`. See [authoring and face assignments](shape-audit/candidate-authoring.json).

[Before/after native front, side and top](shape-audit/before-after-front-side-top.png) shows the limited body change. The [native reopen/edit proof](shape-audit/candidate-verification.json) confirms one valid solid, 78 fully constrained sketches and all 21 final-surface bindings. A 2→2.2 mm trough-radius edit changes the solid and all seven top contacts, then restores body volume exactly and contact areas within 9.1e−13 mm²; the saved source bytes remain unchanged by the test. This is an editability check, not a manufacturing tolerance claim.

## Appearance and presentation

The existing renderer receives `surfaceFinish: wood` in the model presentation's display metadata. A camera direction of `[0, -0.35, -1]` looks gently downward at the upright wallboard to expose the usable top surfaces; this approximately 19.3° camera inclination is a display adaptation. No cord or hidden suspension connection is inferred for this fixed wallboard. Committed USDZ meshes remain unbound and texture-free; renderer grain is a display treatment.

## Compiler and package verification

The pinned compiler check and publish passes produced 22 unbound meshes and 36,970 triangles. One fresh official rebuild reproduces the final USDZ and descriptor byte-for-byte without modifying the source. Actual USD inspection, generated metadata parsing, narrow iOS/Android staging, real FCStd Git LFS verification and delivery checksum validation pass. The scope audit preserves all other 20 queue rows, 56 package lock records and 203 other package files, including accepted boards #16–19. Exact proofs are linked from [verification-index.json](verification-index.json).

## Preserved development history

The initial migration proofs and intermediate failures remain exact under `initial/` and `shape-audit/`. Two initial setter calls failed before source mutation (a missing root key and a derived ID passed to the manifest-only setter). An intermediate wood edit then placed its field at an unsupported root key; independent parsing rejected it. Moving the field into the existing presentation display block passed parsing. These rejected intermediate artifacts remain distinct from final validation.

Native fillet trials that failed in OCCT are retained alongside the successful sequential solution. An expensive initial full-shell Boolean probe was stopped; its termination record is retained and is not a pass. Final contact membership is instead established directly from the final native body's face references, followed by passing compiler validation. Fresh runtime validation remains blocked as described below.

Display checks do not establish manufacturing or ergonomic accuracy. Acceptance requires the user's reply to the displayed final review.

## Fresh app validation is blocked

A fresh isolated iOS build succeeded with the frozen final package, but no fresh app review completed. The first attempt retained the actual failed/canceled test result (one failed test reported, zero passed, exit 73); no requested test completed. Direct installation also stalled. Three subsequent fresh devices reused that exact build and remained in first-boot AddressBook migration during bounded attempts across iOS 26.5, 26.4 and 26.3. The final 26.3 attempt had an eight-minute bound and was observed stopped at 08:25 including command/coordination delay. These interruptions do not establish permanent runtime failure.

No fresh app contact captures, picking checks or workout views are represented as passing. The original test failure, installation interruption, boot logs, whole boot-screen screenshot and exact resource cleanup records are retained under `ios/`. All temporary workspace-owned devices, DerivedData, result bundles and preserved build products were removed and independently checked after evidence capture. The persistent workspace remains available.

The next possible recovery step is restarting the shared CoreSimulator service; it has not been performed or authorized because shared resources are outside this workspace's cleanup authority. A reply authorizing that recovery is not acceptance of this board. #20 remains pending until fresh app validation and the user's one-by-one visual review.
