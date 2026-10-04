# Review findings 1, 5, 6, 7 and 8

Three valid test weaknesses are corrected. Both Plateau and Mini workout UI tests require a meaningful (>30 points in each dimension) intersection with the app viewport at paused Hang and naturally reached Rest. The drawable helper uses a bounded property predicate instead of a fixed delay, with an inverted expectation for the ambiguous case. The transformed-route test checks sample counts before zipping. Existing source tasks, timers, settling timeouts, identifiers and assertions remain intact.

The two allegedly impossible `boardModel.3d` lookups are valid. `WorkoutView.swift:506` (portrait) and `:729` (landscape) omit `onHoldTap`; `BoardMapView.swift:649` defaults it to nil; optional `.map` at `:754` preserves nil; `BoardModelView.swift:79–80` attaches the identifier. The separate `isDisplayOnly` flag is false in normal workouts: lack of contact selection must not be confused with that flag.

The retained actual `final-natural-workflows.xcresult` was read with `xcresulttool get test-results tests`, proving both exact tests passed before these new assertions (32.9306 and 29.9896 seconds). Archive SHA-256 is `2dfd1d8273bce790dd8018aa23d80f1384fdad59791c031eb32639704435e4a8`; the tool output is `previous-green-tests.json`. This refutes the claim that either lookup can never succeed. It does not validate the new assertions.

Only `WorkoutDrawablePresentationTests.checkPresentation(ambiguous:)` was changed in the shared WorkoutTimelineTests file. The proposed name `testSimulatorDrawableGateScopesPolicyToMarkedHostSubtree` does not exist in this revision. Other agents’ test methods were untouched.

`git diff --check` passes. Root owns the new Simulator run using the five filters in `only-testing.txt`. No production changes, builds, Simulator operations, commits or review replies were performed. Extracted historical result copy was removed after saving its query; no external resource was created.
