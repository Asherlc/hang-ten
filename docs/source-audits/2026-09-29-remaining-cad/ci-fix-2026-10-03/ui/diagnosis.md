# UI CI diagnosis

Run 37151709739, job 111286912623 fails only `OwlClimbPokerBoardMapInteractionUITests.testLandscapeMultiPresentationSquareBoardDetailKeepsMapInViewport` at line 231. The test successfully opens Stone Hanger Mini and validates its map, then fails waiting for `boardDetail.presentationSelector`.

The fixture is stale. Mini’s current embedded native manifest has one `primary` 3D presentation. `BoardMapView.swift:421` deliberately emits the segmented presentation picker only when `board.presentations.count > 1`. This is not a layout timeout or wrong-board route.

The proposed minimal patch uses Plateau Lifting Edge, whose native manifest contains the 18, 15 and 10 mm presentations, and removes the obsolete “Square” test-name qualifier. All existing picker, viewport and timeout checks remain unchanged. The separate square-board viewport test remains untouched.

`stale-presentation-fixture.patch` is ready for root acknowledgment. No tracked files were edited and no build, simulator or external resource was started. Exact CI rerun is still required; native metadata checks are not a UI pass claim. Complete job log, failure excerpt and manifest hashes are adjacent.
