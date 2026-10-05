# Automated review follow-up: selection and configured depth

Owner: placid-badger; reviewer seat: premerge_code_review.
Reviewed production revision: 184e4a70bd320922a4083b581ed2757490ad20c5.
Input: ../combined-runtime-final-2026-10-03/automated-review-184e.json (indexes 2, 4, 11, 12).

## Valid findings, tests first

Index 2, thread PRRT_kwDOTqZRe86ouX8n, comment 4175949110:
`WorkoutHighlightResolver.presentationID` accepts a selection with no prescribed
contacts. On a board with effective depths, the generic resolver selects the first
compatible position even for an empty requirement list. The modern nil-target task
path also removes its placeholder contact while retaining that position ID.
`WorkoutView` passes this result as `BoardMapView.selectedPresentationID`.
Returning nil for an empty contact selection preserves the distinction between
a prescribed configuration and work where the athlete chooses the hold.

Regression: `WorkoutTimelineTests.testSelfSelectedWorkDoesNotRequestAConfiguredPresentation`.
It calls the production resolver for both legacy selfSelected work and a modern
nil-target hand task on a two-presentation configured fixture, and expects no
highlight or requested presentation.

Index 4, thread PRRT_kwDOTqZRe86ouX8q, comment 4175949115:
`CustomRoutineBoardPreview.toggle` finds the first position for a presentation,
discarding the position that actually resolved the target. With one physical edge,
18 mm first and 10 mm second, both using presentation front, a selected 10 mm
target cannot be removed by tapping 10 mm; tapping 18 mm incorrectly clears it.
The editor's `toggleHold` calls this production method, and model tap callbacks
pass contacts from the selected position. `BoardRevision.contacts(inPosition:)`
returns that position's effective depth, so the selected resolved contact supplies
the correct comparison directly without guessing another position.

Regression: `CustomRoutineDraftTests.testConfiguredDepthToggleUsesResolvedPositionWithinSharedPresentation`.
It checks removal of the selected 10 mm configuration, changing to 18 mm, and
removing the newly selected 18 mm configuration while preserving physical ID edge.

Both regressions were added before preparing the fix. Production is unchanged
pending root's actual red test run. Prepared implementation:
`selection-and-depth-fixes.patch`; read-only `git apply --check` passed.
The patch changes only the presentation guard in WorkoutTimeline.swift and the
resolved-depth lookup inside CustomRoutineBoardPreview.toggle.

## Invalid findings, no production edits

Index 11, thread PRRT_kwDOTqZRe86ouYTY, comment 4175951360:
The claimed composition mismatch does not exist. The native renderer constructs
the base about the source bounds center (`BoardModelRealityTypes.swift:694-695,
1680-1703`) and passes it to the CAD adapter. The CAD solver applies pose * base
(`SuspendedBoardPresentation.swift:349-360,482`). Base rotation and reflection
fix the bounds center c, so base * c = c + baseTranslation. The resolver computes
pose * (c + baseTranslation) (`WorkoutActivityRecording.swift:506-517`), exactly
pose * base * c. The review itself describes the same composition on both sides.
No model, contact identity, ordering, or camera change is justified by this claim.
Existing `BoardTargetSubstitutionTests.testExactPentaTasksUseAuthoredUnitPlacementInsteadOfInstanceArrayOrder`
covers source-native paired-unit ordering for both instance-array and task-side orders.

Index 12, thread PRRT_kwDOTqZRe86ouYTa, comment 4175951362:
The comment describes another view's implementation. BoardMapView has no externally
bound selectedPositionID or updateSelectedPosition method. Its body derives a local
selectedPositionID from content.presentation.id on every evaluation
(`BoardMapView.swift:670-681`), then passes that same value to the model at 751,
the configured contact callback at 756-758, and aspectRatio at 766. Its presentation
picker changes presentationSelection at 802-804. The proposed local derivation is
already present. BoardDetailMapView's separate binding does not establish the
reported BoardMapView state-lag failure. No UI edit is justified.

## Verification and scope

No tests, builds, simulators, browser resources, commits, pushes, or GitHub replies
were performed by this seat. Root owns red/green testing on its Simulator. Test
fixtures are synthetic and do not change manufacturer facts, packages, routines,
or canonical geometry. Drawable discovery sections belong to the separate test
agent and were not edited by this seat.
