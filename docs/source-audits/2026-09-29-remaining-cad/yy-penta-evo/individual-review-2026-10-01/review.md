# #18 Penta Evo individual review

**Human acceptance: pending.** This packet presents the corrected native package for one-by-one review; migration or automated validation does not constitute acceptance.

## Evidence and changes

Reused the user-approved whole manufacturer front/rear product images in [the source register](../source-register.json). The historical binary URLs remain unknown; the product URL is a reference, not a claimed download URL. No image measurements, tracing, cropping, segmentation or registration were used.

The prior CAD rear 10 mm recess crossed the inner and outer perimeter. Four existing `edge_10Section` sketches were rotated 36 degrees about their unchanged native centers to align the recess with the surrounding band, as supported by the whole rear maker image. Its dimensions and 10 mm depth remain unchanged. The other six contact regions have zero native surface-area difference. All seven contact regions lie on the body skin; the result is one valid solid, with all 48 sketches constrained. Native angle and depth edits followed by restoration passed. See [correction](shape-audit/correction-report.json), [editability](shape-audit/editability.json) and [whole original/prior/corrected front, side, top and rear views](comparison/original-prior-corrected-views.png).

Two editable wooden helper regions had been exported as neutral attachments. Their export tags were removed while retaining their native construction; the complete body remainder now includes those surfaces. Eight unbound meshes remain: one body and seven contact slots. The existing `surfaceFinish: wood` renderer metadata supplies the appearance. The committed USDZ contains no materials, shaders, bindings or textures. Fourteen logical contacts and two unreflected instances are preserved.

Each grip now resolves its own pose with its native bearing facing upward: 25 mm, 20 mm, 15 mm, rear 10 mm, mono, duo and tray. Native bearing witnesses and the app test cover all fourteen selections. Camera and pose values are display adaptations, not manufacturer specifications.

## Suspension

The source-supported loop passes through the central opening and around the actual wooden band. No hidden bore or groove was invented. Each pose uses stations measured from the native bearing surface, offset for the estimated 2 mm cord radius. Both instances independently regenerate all seven routes against the final solid. The 0.6 m loop presentation, station clearance and hanging support are labeled display estimates.

A coordinated additive authoring option, `ropeSolver.terminalsByPoseID`, selects a complete station map per pose and keeps the existing global map as fallback. It is stripped before runtime staging. Validation checks every map and rejects combining it with `grooveGuides`; solving isolates each map before either cache. [Coordination](solver-draft/coordination.json) and [independent code review](solver-extension-checks/production-code-review.json) are retained. At any later explicit merge, preserve the parent's separate `source_metadata` and `grooveGuides` changes and this rejection.

The final conservative minimum clearance certificate is 1.9902571767736617 mm for a 2 mm radius, within the existing 10 micrometre tolerance; this is not a claim of a positive air gap. Astra reviewed whole front, side and oblique cord/body renders for all seven poses: [visual review](shape-audit/cord-review/visual-review.json). These are constrained static display routes, not unrestricted sliding physics, friction or equilibrium certification.

## Export and verification

Final hashes and principal reports are listed in [verification-index.json](verification-index.json). The native compiler exported the corrected geometry once. A subsequent manifest-only edit restored the required nine-decimal zero spellings for instance translations; every geometry archive member and ObjectData remained byte-identical. The compiler's original source hash is preserved, with [explicit final-source provenance](final-source/lexeme-fix-provenance.json) and an independent metadata-only bridge, rather than rewriting the compiler proof or repeating an unchanged export.

- Focused production Python validation: 92 tests passed, including real closed-solid Dijkstra/A* loops, override/fallback and cache isolation.
- Native edit/restore, source-backed parsing, actual USD inspection, fourteen cord regenerations, iOS/Android staging and final delivery checksum validation passed.
- Initial fresh isolated Simulator build and two targeted XCTest cases passed; after the workout resolver correction, a second clean build passed all 93 tests in the full ContactResolverTests and WorkoutActivityRecordingTests suites plus the two Penta cases. The runtime record retains all fourteen contact selections, all seven poses on both instances, gentle orbit views, physical picking/reset, cord non-pickability and the existing bilateral 20 mm workout checks. The first workout attempt exposed a pre-existing reusable-instance pair-resolution failure; its missing highlights are retained as a failure, and the fix/retry are documented separately below.
- [Runtime record](ios/final-runtime-validation.json), [app review](ios/app-review.png), [full selections](ios/review-montages/selections.png) and [full orbits](ios/review-montages/orbits.png).

Raw reports, logs and screenshots retain their original bytes. Earlier failures and superseded output remain separately recorded: draft regression failures, station/route clearance failures, compiler invocation failure, staging/lexeme failures, the first comparison's incorrect rear camera, and delivery verification started before the checksum update completed. The corrected comparison is `original-prior-corrected-views.png`; the similarly named first-attempt sheet is superseded and must not be used for review.

The original 226.6 × 30 × 230 mm display envelope and rounding are estimates; overall dimensions are not published in the retained evidence. Wood grain, cord presentation, cameras and orientations are display adaptations. No manufacturing, ergonomic or safety accuracy is claimed. No other board package or review decision changed.

## Workout pairing boundary

The first fresh workout reached the active and rest states but highlighted no
contacts. The reusable model loader already maps slot IDs to logical contact
IDs; however, both physical units retain the same native slot frame. The
spatial pair selector incorrectly required these two local frames to straddle
the presentation midpoint. The failed screenshots and original route-only
status are retained, with a separate visual-failure finding.

The coordinated fix handles exactly two candidates on exactly two reusable
instances through their explicit equipment-object and corresponding-slot
mappings, retaining the existing equality checks for contact facts. Invalid
pairs in that branch fail closed; other cases retain spatial selection. The
regressions cover the real existing max-hangs routine, both logical 20 mm
contacts and selected pose, plus different slots, the same instance and
unequal facts. No routine content or package fact was changed. The fresh
rebuild/retry record, rather than the earlier failing run, determines workout
validation status.

The retry passed 93 XCTest cases and visually shows both 20 mm contacts in the
correct loading pose during the active hang. The immediate rest screenshot
captures the highlight transition; a separate later rest frame shows the
settled blue bilateral next-hold preview. Both raw frames are preserved.
