# Transgression integration validation — 2026-09-29

Both revisions are new packages; no prior committed asset exists for a before
comparison. [Front, side and top views](review/both-revisions-front-side-top.jpg)
show both final exported models. Independent OpenUSD Hydra renders were used to
check the actual USDZ surfaces alongside the native diagnostic previews.
[2011 oblique](review/2011-oblique.png) and
[2013 oblique](review/2013-oblique.png) show the rails and round jug.
No material or texture is authored in either runtime asset.

## Native and package checks

- Pinned FreeCAD 1.1.3 / OCCT 7.8.1 recompilation of each new package produces
  byte-identical USDZ and descriptor. Both models have 2,376 triangles, ten
  semantic nodes and nine independently selectable contacts. Published rail
  depths are reproduced within 0.001 mm in the tessellated descriptor checks.
- The two packages pass all five `test_transgression_packages.py` checks,
  including actual native reopen and parameter-edit propagation. The full
  staging test file passes all 28 cases, including both new simulator fixtures
  and all live Xcode resource tags.
- Whole-catalog package validation passes with `--final-inventory`.
- [Delivery verification](review/delivery-lock-check.json) passes for 52 models.
- [Android staging and material audit](review/material-and-android-staging.json)
  confirms exact inline runtime assets, byte-identical generated metadata and
  exclusion of native sources from staged output.
- [iOS staging](review/ios-staging.json) confirms exact bundled metadata and
  descriptors, exact USDZ in each separate tagged asset pack, no USDZ in the
  ordinary package and no FCStd anywhere in the app.

The broader Python selection passes 474 tests with one existing collection skip.
The one whole-catalog reproducibility test was deselected; both changed packages
were instead checked explicitly with `verify_reproducible.py --package`.
Fourteen existing simplifier tests initially failed because local dependency
libraries were absent. Installing the repository-pinned Python dependencies and
meshoptimizer v1.0 made all fourteen pass, with no source changes. See the
[combined result](review/python-tests.json).

## App review

The signed Debug app was built and tested on workspace-owned iPhone 17 Pro,
iOS 26.5, simulator `52DBE53C-3DCC-41BF-AA8D-EF3B5E1B3E27`.
The full `HangTenTests` target passes: 1,238 passed, three skipped, zero failures
([xcresult summary](review/ios-unit-tests.json)). An initial run had a timeout
in the existing asynchronous Apple Health history test; that test passed alone,
and the subsequent full target passed without changes to its code.

Commands used the explicit UUID, `-parallel-testing-enabled NO` and workspace
`.context/DerivedData`: `xcodebuild -project HangTen.xcodeproj -scheme HangTen
-configuration Debug -destination 'platform=iOS Simulator,id=<owned UUID>'
-derivedDataPath .context/DerivedData build-for-testing`, followed by
`test-without-building -only-testing:HangTenTests` with the same options.

The final visual build additionally uses `CI=true` to stage the existing Debug
simulator fixtures. The simulator's download service remained pending in early
captures. The fixture build bypasses that service for visual review only; Release
still uses the separate ODR tags. [Installed byte checks](review/installed-ios-assets.json)
prove the reviewed fixture USDZ and descriptors equal the validated sources.
This review checks packaged resources and rendering, not a production network
ODR download.

Both neutral Train boards and all nine contact highlights per revision were
inspected. Each selected ID is captured in the [route results](review/highlight-route-results.json).
[2011 highlights](review/2011-all-contact-highlights.jpg) and
[2013 highlights](review/2013-all-contact-highlights.jpg) show that only the
selected shelf/nose or top jug receives the app's transient highlight.
The published depths appear in the specs cards; the jug has no invented depth.
The grey appearance and red selection come from the renderer, not USDZ materials.

Physical coordinate taps on the jug, 18 mm rail and 6 mm rail of each revision
changed selection to the correct ID independently of the hold map. The
accessibility overlay disables hit testing; these taps exercise RealityKit
picking. [Tap coordinates and selected IDs](review/direct-tap-results.json)
record all six successful checks. Thin rail lips occupy only a small screen area
in this front view, so taps must land precisely on the visible lip.

Both [2011 landscape](review/2011-app-landscape.png) and
[2013 landscape](review/2013-app-landscape.png) render the whole board with
its 18 mm rail highlighted and the complete revision title. The specs and hold
map remain in the scrollable content below the model.

The EXIT cleanup trap deleted the exact owned simulator and removed workspace
`.context/DerivedData`, `workout-raw.png` and `workout-landscape.png`. A subsequent
`simctl list devices --json` lookup confirms the UUID is absent and ownership
records are consumed ([cleanup proof](review/resource-cleanup.json)). Shared
simulators and workspaces were left alone.
