# Native iOS acceptance evidence — batch-02 model migration

## Scope

Acceptance ran against current source `fb1135c04ec769a66bb97b7deab1d7ebf828f4c4`
(`fix: address batch-02 review follow-ups (ODR tags, symmetry, ledger, frozen tests)`),
the current `HEAD` of branch `migrate-hangboards-batch-02`. It covers the six
newly migrated model-first packages:

| App ID | Package ID | Presentation | Contacts |
| --- | --- | --- | ---: |
| `escape-beta-22` | `escape-beta-22` | `primary` | 22 |
| `mammut.diamond-finger` | `mammut.diamond-finger` | `primary` | 16 |
| `metolius.foundry` | `metolius.foundry` | `front` | 18 |
| `nature.stoak-board-iii` | `nature.stoak-board-iii` | `primary` | 7 |
| `soill.iron-palm-2` | `soill.iron-palm-2` | `primary` | 8 |
| `soill.split-palm` | `soill.split-palm` | `primary` | 14 |

All six packages declare a `model` presentation (`media.type == "model"`) with
an `assets/primary.usdz` ODR asset and a bundled descriptor. Contact counts are
read directly from each `Hangboards/<package>/board.json`.

## Environment/build

| Field | Recorded value |
| --- | --- |
| Acceptance date | 2026-09-16 |
| Acceptance commit | `fb1135c04ec769a66bb97b7deab1d7ebf828f4c4` |
| Workspace owner token | `legit-puma` |
| Xcode | 27.0 (27A266a) |
| Dedicated simulator | iPhone 17 Pro, iOS 26.5 (23F77) |
| Simulator name | `Hang Ten Paseo legit-puma Review` |
| Simulator UUID | `2B2278F9-4934-4731-960D-3CD99B04914B` |
| Owner manifests | `.context/paseo-pending-simulators`, `.context/paseo-owned-simulators` |
| Bundle | `com.hangten.training` |
| Project / scheme | `HangTen.xcodeproj` / `HangTen` |
| Configuration / destination | Debug / `platform=iOS Simulator,id=2B2278F9-4934-4731-960D-3CD99B04914B` |
| Derived data | `.context/DerivedData` |
| Signing | `CODE_SIGNING_ALLOWED=NO` |
| Result | Build succeeded; all acceptance steps and the tap test succeeded |

Build invocation (bounded, current-source):

```sh
xcodebuild \
  -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination 'platform=iOS Simulator,id=2B2278F9-4934-4731-960D-3CD99B04914B' \
  -derivedDataPath .context/DerivedData CODE_SIGNING_ALLOWED=NO build
```

Recorded result: `** BUILD SUCCEEDED **`. No `SWBBuildService`/compiler-probe
stall occurred, so the deadlock diagnostic path in
`docs/3D_SUSPENSION_AND_ODR.md` was not required.

The selected-contact step used a real touch via a temporary XCUITest class,
`Batch02BoardAcceptanceUITests`, appended to
`HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift` and run with:

```sh
xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination 'platform=iOS Simulator,id=2B2278F9-4934-4731-960D-3CD99B04914B' \
  -derivedDataPath .context/DerivedData CODE_SIGNING_ALLOWED=NO \
  -only-testing:HangTenUITests/Batch02BoardAcceptanceUITests \
  -resultBundlePath .context/legit-puma-batch-02-acceptance/results.xcresult
```

Recorded result: `** TEST SUCCEEDED **` (1 test, 0 failures). The test class was
removed afterwards with `git checkout --` the test file; `git status` is clean
and no source change remains.

Active portrait/landscape captures used the documented `simctl` routes:

```text
HANGTEN_REVIEW_BOARD_ID=<app id>
HANGTEN_REVIEW_BOARD_DETAIL=1
HANGTEN_REVIEW_LANDSCAPE=1     # landscape active captures only
```

## Board evidence table

Screenshot filenames are relative to
`docs/source-audits/2026-09-16-hangboard-3d-batch-migration/screenshots/`. Portrait captures are
1206x2622; landscape captures are 2622x1206 (landscape was emitted natively, so
no rotation was applied).

| App ID | Portrait active | Landscape active | Portrait picked | Selected contact |
| --- | --- | --- | --- | --- |
| `escape-beta-22` | `escape-beta-22-portrait-active.png` | `escape-beta-22-landscape-active.png` | `escape-beta-22-portrait-picked-hold-01-left.png` | `hold-01-left` (Left Thin Pinch) |
| `mammut.diamond-finger` | `mammut.diamond-finger-portrait-active.png` | `mammut.diamond-finger-landscape-active.png` | `mammut-diamond-finger-portrait-picked-mam-jug-l.png` | `mam-jug-l` (Jug left) |
| `metolius.foundry` | `metolius.foundry-portrait-active.png` | `metolius.foundry-landscape-active.png` | `metolius-foundry-portrait-picked-pinch-1-left.png` | `pinch-1-left` (Left #1 variable pinch) |
| `nature.stoak-board-iii` | `nature.stoak-board-iii-portrait-active.png` | `nature.stoak-board-iii-landscape-active.png` | `nature-stoak-board-iii-portrait-picked-top-jug.png` | `top-jug` (Full-width top jug) |
| `soill.iron-palm-2` | `soill.iron-palm-2-portrait-active.png` | `soill.iron-palm-2-landscape-active.png` | `soill-iron-palm-2-portrait-picked-sloper-left.png` | `sloper-left` (Left sloper) |
| `soill.split-palm` | `soill.split-palm-portrait-active.png` | `soill.split-palm-landscape-active.png` | `soill-split-palm-portrait-picked-left-top-jug.png` | `left-top-jug` (Top jug left) |

Model vs fallback: for all six boards the model path loaded. The tap test
enumerated descriptor-bound `boardModel.contact.<id>` accessibility elements on
every board and `boardModel.unavailable` was absent, so the raster/fallback path
was never shown. Picking resolved a real descriptor-bound contact on every board
and the `boardDetail.selectedHold.<id>` card appeared after the tap.

## UI/picking observations

- Every board used `HANGTEN_REVIEW_BOARD_ID=<app id>` with
  `HANGTEN_REVIEW_BOARD_DETAIL=1`, which routes Train straight to `BoardDetailView`
  (`Hold specs`) for that board.
- The rendered surface is the SceneKit model (smooth shaded geometry with
  specular highlights), not a raster image. The model-only presentation is the
  only surface the detail route can select for these packages.
- `BoardDetailView` pre-selects the first default contact, so a selected-hold
  card is often already visible on load. The explicit tap test nevertheless
  tapped a specific descriptor-bound contact and confirmed the matching card,
  which is stronger evidence than the default preselection alone.
- Landscape launches requested `HANGTEN_REVIEW_LANDSCAPE=1`; the compact-height
  layout placed the model in the map card with the root tab bar hidden. Some
  boards (Iron Palm 2.0, Split Palm) render large in landscape and the lower
  rows continue below the visible viewport; the board remains framed and the
  detail page is a scroll view. No clipping into the tab bar was observed.
- `soill.iron-palm-2` and `soill.split-palm` portrait picked captures show the
  tapped contact highlighted (orange) and the selected-hold card carrying the
  tapped contact's name and kind.

## Behavior matrix

| Behavior | Evidence | Observed coverage |
| --- | --- | --- |
| Six-board detail routing | Review environment + UI test snapshots | All six app IDs opened their `Hold specs` board detail route |
| Model (not raster/fallback) | Six active + six picked captures; `boardModel.contact.*` enumerated, `boardModel.unavailable` absent | Loaded 3D model on every board in both orientations |
| Portrait framing | Six `*-portrait-active.png` captures | Model visible and framed for every board |
| Landscape framing | Six `*-landscape-active.png` captures | Model visible; compact-height layout, root tab bar hidden |
| Contact picking | Six real taps in `Batch02BoardAcceptanceUITests` | Listed contact selected; selected-hold card appeared for every board |
| Descriptor binding | Selected contacts are all entries in each `board.json` `contacts[]` and exposed as `boardModel.contact.<id>` | Picking resolved a real descriptor-bound contact, not a legend or guess |

## Screenshot hash table

The following verified SHA-256 values identify every referenced screenshot.
Screenshot binaries remain workspace-owned and were not added to Git.

| Screenshot | Dimensions | SHA-256 |
| --- | --- | --- |
| `escape-beta-22-portrait-active.png` | 1206x2622 | `f9aaf566d524947aba8d334c2b5a0af03a4101a6add638ecfb5d24c379a4b985` |
| `escape-beta-22-landscape-active.png` | 2622x1206 | `cd1b9cab2f5316c836f0f9b65584c7d7127fbd8447288194ee3d875c491af6c2` |
| `escape-beta-22-portrait-picked-hold-01-left.png` | 1206x2622 | `768db0532dd22179613782e3c5af3727131688a3fd729be3b019b278f18cd17d` |
| `mammut.diamond-finger-portrait-active.png` | 1206x2622 | `e96064c685e3d2e6861ab9aec155ad82d313e5b291f2f8fda4ee26967e682447` |
| `mammut.diamond-finger-landscape-active.png` | 2622x1206 | `e45d762ec3d8ce235e9b06fa79ef05ef89f2226d1768adf1c99526280628c89b` |
| `mammut-diamond-finger-portrait-picked-mam-jug-l.png` | 1206x2622 | `cb395587abd3f612829c887e34324bdbe61b5f89aeca07ae91577edaeafe8d7f` |
| `metolius.foundry-portrait-active.png` | 1206x2622 | `893eaa1e293d9a80115db7f0cd580b8a9b5605cd999cddbec470f56f8215ecf4` |
| `metolius.foundry-landscape-active.png` | 2622x1206 | `c807b35ad20e22febd8d877b8bf7b4f14cedd08ab74741db3e85a76e772cfbe7` |
| `metolius-foundry-portrait-picked-pinch-1-left.png` | 1206x2622 | `2cafb5e2fcb881b3241315a37e89a2f820842ebaf72dbd3e77ef194d98fb9801` |
| `nature.stoak-board-iii-portrait-active.png` | 1206x2622 | `b315310a4dd7d1f591495320b39e4cfd62cd3a2d85340ce604606e1ffe7a6fd2` |
| `nature.stoak-board-iii-landscape-active.png` | 2622x1206 | `d285516e4f0ff09eb6af8566ef113b295e7d7b72d37fc1569c731966bb963578` |
| `nature-stoak-board-iii-portrait-picked-top-jug.png` | 1206x2622 | `e97b65bea6778617ce955536652a21ff50f3a0355b5b946944cda0a4bbf6c680` |
| `soill.iron-palm-2-portrait-active.png` | 1206x2622 | `bb6914300fc550b2a27b5e19a96ec32851a895ba5be2b6156fe4f998cb87d626` |
| `soill.iron-palm-2-landscape-active.png` | 2622x1206 | `c3f242290e06535807d7b3c205b50cd4c684f181f5b0150400988d4b6656fee8` |
| `soill-iron-palm-2-portrait-picked-sloper-left.png` | 1206x2622 | `42b0958ab3114cf3c98dd73a72c5703b7f14eed835daa27d764ada0cda3bb1c1` |
| `soill.split-palm-portrait-active.png` | 1206x2622 | `2dec6afff4f2a22809fb6ab0a3db163a6514d4f943ff3ecf61e00ce133c5139d` |
| `soill.split-palm-landscape-active.png` | 2622x1206 | `6d8114258b1b1862a6a624b3830b12d7b7d17b05ea3ae74819d115e106112a8f` |
| `soill-split-palm-portrait-picked-left-top-jug.png` | 1206x2622 | `425edc4649ecea7c4c941f191603535a937c6965195a9b1e73292e34ca69fba1` |

## Cleanup statement

Resource ownership followed `docs/IOS_SIMULATOR_VALIDATION.md` and the cleanup
section of `docs/3D_SUSPENSION_AND_ODR.md`. Exactly one simulator was created,
named `Hang Ten Paseo legit-puma Review`, and its UUID
`2B2278F9-4934-4731-960D-3CD99B04914B` was written to
`.context/paseo-pending-simulators` before the owned manifest and before any
boot or build. Every command targeted that explicit UUID; `booted` and shared
devices were never used.

Cleanup used `scripts/paseo-resource-cleanup.sh archive` with
`PASEO_WORKTREE_PATH` set to this workspace. Verified afterwards:

- The owned simulator UUID is absent from `xcrun simctl list devices`.
- `.context/paseo-owned-simulators` and `.context/paseo-pending-simulators` are
  empty (the archive consumed the recorded UUIDs).
- `.context/DerivedData` is absent.
- The result bundle `.context/legit-puma-batch-02-acceptance/results.xcresult`
  and the derived export staging `.../exported` are absent.
- Retained workspace-owned evidence: the 18 screenshots and build/test logs
  under `.context/legit-puma-batch-02-acceptance/`.

No shared Xcode/CoreSimulator resource was deleted, no global
`~/Library/Developer/Xcode/DerivedData` purge was performed, and no shared
process was killed.

## Limitations/conclusion

Evidence is simulator-only; no physical-device run was performed, and simulator
captures establish app integration rather than guaranteed physical-device PBR
parity. The acceptance covers the six board routes, portrait and landscape
framing, model (not raster/fallback) rendering, and one real descriptor-bound
contact tap per board at source `fb1135c0`. It makes no global collision-free or
all-contact picking claim; coverage is limited to the documented route checks
and the selected contact taps listed above. All six boards are
`model` presentations; whether the bundled packages are model-only in production
is enforced by the separate package/descriptor validation lanes, not by these
screenshots.
