# Native iOS acceptance evidence

## Scope

Acceptance ran against current source `f68cbbd7f6b31ac09e67622bd0d1f74ebe920db0` (`chore: finalize hangboard migration audit records`). This report retains already collected evidence for six migrated hangboards. No new build or validation run was initiated to write this report. The report commit is documentation only; it does not change production packages, source records, tests, or runtime behavior.

## Environment/build

| Field | Recorded value |
| --- | --- |
| Acceptance date | 2026-09-16 |
| Dedicated simulator | iPhone 17 Pro, iOS 26.5 |
| UUID | `24871C34-8ACA-443F-A22E-EF4C5708D044` |
| Simulator name | `Hang Ten Paseo infamous-sheep Review` |
| Bundle | `com.hangten.training` |
| Owner record | `.context/infamous-sheep-native-acceptance/OWNER` |
| Build/run tool | XcodeBuildMCP |
| Project / scheme | `HangTen.xcodeproj` / `HangTen` |
| Configuration / destination | Debug / iOS Simulator |
| Derived data | `.context/DerivedData` |
| Build setting | `CODE_SIGNING_ALLOWED=NO` |
| Result | Build succeeded; app ran on the dedicated simulator |

No physical-device run was performed.

## Board evidence table

All screenshot filenames in this report are relative to `.context/infamous-sheep-native-acceptance/screenshots/`. Portrait active and portrait picked captures are 1206x2622; landscape active captures are 2622x1206.

| App ID | Package ID | Contacts | Portrait active | Landscape active | Portrait picked | Selected contact |
| --- | --- | ---: | --- | --- | --- | --- |
| `dewoodstok-woodbord` | `dewoodstok-woodbord` | 17 | `dewoodstok-portrait-active.png` | `dewoodstok-landscape-active.png` | `dewoodstok-woodbord-portrait-picked-front-upper-2.png` | `front-upper-2` |
| `escape.unlimited` | `escape-unlimited` | 7 | `escape-unlimited-portrait-active.png` | `escape-unlimited-landscape-active.png` | `escape-unlimited-portrait-picked-edge-45-right.png` | `edge-45-right` |
| `evolv-kilter-basic-long` | `evolv-kilter-basic-long` | 4 | `evolv-kilter-basic-long-portrait-active.png` | `evolv-kilter-basic-long-landscape-active.png` | `evolv-kilter-basic-long-portrait-picked-edge-15.png` | `edge-15` |
| `metolius.wood-grips-deluxe-ii` | `metolius-wood-grips-deluxe-ii` | 26 | `metolius-wood-grips-deluxe-ii-portrait-active.png` | `metolius-wood-grips-deluxe-ii-landscape-active.png` | `metolius-wood-grips-deluxe-ii-portrait-picked-sloper-12-round-center.png` | `sloper-12-round-center` |
| `moon.armstrong` | `moon-armstrong` | 21 | `moon-armstrong-portrait-active.png` | `moon-armstrong-landscape-active.png` | `moon-armstrong-portrait-picked-sloper-right.png` | `sloper-right` |
| `target10a.linebreaker-base` | `target10a-linebreaker-base` | 23 | `target10a-linebreaker-base-portrait-active.png` | `target10a-linebreaker-base-landscape-active.png` | `target10a-linebreaker-base-portrait-picked-sloper-32-right.png` | `sloper-32-right` |

## UI/picking observations

Every board route used `HANGTEN_REVIEW_BOARD_ID` set to its app ID and `HANGTEN_REVIEW_BOARD_DETAIL=1`. The UI snapshot exposed `boardModel.map` and the relevant `boardModel.contact.<id>`. An actual tap selected each contact listed above, and the selected contact card appeared.

Portrait and landscape active captures show the loaded 3D model and its framing. Separate package/descriptor checks enforce model-only production packages; screenshots alone do not establish that property. The selected contacts and native tests demonstrate the documented picking cases, without a claim of global collision freedom.

## Behavior matrix

| Behavior | Evidence | Observed coverage |
| --- | --- | --- |
| Six-board detail routing | Review environment and UI snapshots | All six app IDs loaded their board detail route |
| Portrait/landscape framing | Twelve active captures in the board table | Loaded 3D model visible in both orientations for every board |
| Contact picking on each board | Six portrait picked captures and actual taps | Listed contact selected and selected contact card shown for each board |
| Orbit and orientation reset | Two targeted orbit/orientation tests | Complete azimuth rotation; orientation selection resets orbit and permits suspension at runtime |
| Highlight clear/restore | Targeted cloned-material test and workout rest captures | Materials restore across generic views; rest clears highlight while the model remains present |
| Front-most native picking and accessibility | Two targeted descriptor-bound tests | Closest native hit resolves the front contact; accessibility enumerates descriptor-bound contacts only |
| Workout selection/model preview/rest transition | Three Evolv workout captures and Start routine interaction | Selected routine preview shown; countdown followed by observed Step 2 rest with model present |

## Native tests

On 2026-09-16, XcodeBuildMCP `test_sim` reran these exact `BoardModelTests` against current source `f68cbbd7f6b31ac09e67622bd0d1f74ebe920db0`, using `CODE_SIGNING_ALLOWED=NO`:

| Test | Behavior covered |
| --- | --- |
| `testOrientationSelectionResetsOrbitAndAllowsSuspensionAtRuntime` | Orientation selection resets orbit and allows suspension at runtime |
| `testOrbitAllowsACompleteAzimuthRotation` | Orbit permits a complete azimuth rotation |
| `testHighlightsRestoreClonedMaterialsAcrossGenericViews` | Highlight clearing restores cloned materials across generic views |
| `testClosestNativeHitResolvesOnlyTheFrontDescriptorBoundContact` | Front-most native picking resolves only the front descriptor-bound contact |
| `testModelAccessibilityEnumeratesOnlyDescriptorBoundContacts` | Accessibility exposes only descriptor-bound contacts |

Result: **5 passed, 0 failed, 0 skipped**.

Previously collected full native `xcodebuild test` evidence recorded **1,145 HangTenTests with 2 skipped and 0 failures**, **24 HangTenUITests with 0 failures**, and **TEST SUCCEEDED**. The targeted tests above were rerun on `f68`; the full native suite was not rerun for this report.

## Workout evidence

The recorded workout launch used:

```text
HANGTEN_REVIEW_BOARD_ID=evolv-kilter-basic-long
HANGTEN_REVIEW_BOARD_DETAIL=1
HANGTEN_REVIEW_WORKOUT=1
HANGTEN_REVIEW_PLAN_ID=research.max-hangs
HANGTEN_REVIEW_LANDSCAPE=1
```

The setup recorded free workouts **0**, step **1**. These observations retain visible UI labels, not new training prescriptions.

| Screenshot | Observed state |
| --- | --- |
| `evolv-kilter-basic-long-workout-step-1.png` | Pre-start: Session, Step 1 of 9, Max hang set 1, half-crimp, Start routine, and Evolv 3D preview |
| `evolv-kilter-basic-long-workout-step-1-active.png` | Step 2 of 9, Rest, 180s rest, plain model |
| `evolv-kilter-basic-long-workout-step-1-hang.png` | Step 2 of 9, Rest, 180s rest, plain model |

Tapping Start routine produced a countdown and advanced to the latter two captures. Despite their filenames, both document rest, not an active hang. They show the model remains present while the highlight clears. All three workout captures are 2622x1206.

## Screenshot hash table

The following verified SHA-256 values identify every referenced screenshot. Screenshot binaries remain workspace-owned and ignored at `.context/infamous-sheep-native-acceptance/screenshots/` and were not added to Git.

| Screenshot | SHA-256 | Dimensions |
| --- | --- | --- |
| `dewoodstok-portrait-active.png` | `7190068dabb4cc08dabea238e3ce180e92f90d13d694f3ceb46a762e6ce1c4fd` | 1206x2622 |
| `dewoodstok-landscape-active.png` | `9cee3dff9df01884e9831bc97f579639b25d9bf736dd9298af390b69504e0929` | 2622x1206 |
| `dewoodstok-woodbord-portrait-picked-front-upper-2.png` | `384107265b70bfb63e47547d8cddc6ed055b23e638fc907670396bb2b0b71b84` | 1206x2622 |
| `escape-unlimited-portrait-active.png` | `775a92fdd97777edeb4d6028bafe5d6fece45b64f58ded60acb41f9b7efc20b3` | 1206x2622 |
| `escape-unlimited-landscape-active.png` | `f9d248551379c2554d0b55a044d33907292eccac554ad82cd32f1141f97cc39b` | 2622x1206 |
| `escape-unlimited-portrait-picked-edge-45-right.png` | `824099ff18fb73c25fa29b4d34d62aa31db3c953f59fe0a7cc9b102195841eab` | 1206x2622 |
| `evolv-kilter-basic-long-portrait-active.png` | `b1ed5862f938c273de0ffe0323d775fea3eb23fbc3c7eb1117d9c77a7dc89ec2` | 1206x2622 |
| `evolv-kilter-basic-long-landscape-active.png` | `da22842fa95f8d1ae1732e24c99540e7d84f278e4bdb822bfa77bcd9c396013c` | 2622x1206 |
| `evolv-kilter-basic-long-portrait-picked-edge-15.png` | `118e7242047cc3606e16485739803fab32aea701414858f6218d36c1fbd9086f` | 1206x2622 |
| `evolv-kilter-basic-long-workout-step-1.png` | `b3459775d6d85108fec1c8e1bf7a1b1c61b06c708c01df590c00b83342821e62` | 2622x1206 |
| `evolv-kilter-basic-long-workout-step-1-active.png` | `63f4b9edd8c5b84d4dfd14e86307b249f65fb62f733adba0b38f3dc62007a96e` | 2622x1206 |
| `evolv-kilter-basic-long-workout-step-1-hang.png` | `1dd157a4bace471fd0bda08748762c924125106c318ad47d1f5b4729ae38cce6` | 2622x1206 |
| `metolius-wood-grips-deluxe-ii-portrait-active.png` | `761d1c7d65f88994fb5ee9612fd491c0873ad89bec33979dbe60e77dc6bf7ec7` | 1206x2622 |
| `metolius-wood-grips-deluxe-ii-landscape-active.png` | `8bb439ddd1c477ec424598181db10e13ba6d0258ae119f232d7be760582b6b8f` | 2622x1206 |
| `metolius-wood-grips-deluxe-ii-portrait-picked-sloper-12-round-center.png` | `8de5ed5d069f052deee84a201706710db535df28ecf8afdd3693d91b50321cd7` | 1206x2622 |
| `moon-armstrong-portrait-active.png` | `64433f93d5c0de10809730fdde6afede7bb21ee7be338bf30e621b9e4fbe4cde` | 1206x2622 |
| `moon-armstrong-landscape-active.png` | `14c2fc8ab6f9eb9aaa05e086e46eb985233de7c1805cd138b55c6bb2e7a83355` | 2622x1206 |
| `moon-armstrong-portrait-picked-sloper-right.png` | `5c5259d3eeecb7da40d5bc2d3e2bfb2fea54c6e55336f32cb66c9de97e3a76a5` | 1206x2622 |
| `target10a-linebreaker-base-portrait-active.png` | `17ced4e1129bce8fbe46d4cee0302c26d2f9f49d22d2bda98f3b60c0335e054b` | 1206x2622 |
| `target10a-linebreaker-base-landscape-active.png` | `16a86d6b656660b662e9ca12bcddc8b4adc36857e58ccbf237264f780bfc16c8` | 2622x1206 |
| `target10a-linebreaker-base-portrait-picked-sloper-32-right.png` | `daafd97b227e7d7ba6987ba915d7912843c70f464463c3ca36a16bf10e87d522` | 1206x2622 |

## Prior validation

The following evidence was previously collected; these checks were not all rerun for this report:

| Check | Recorded result |
| --- | --- |
| Package validator | Exit 0 |
| Full package pytest | 614 passed |
| Model-tool unittest | 19 passed |
| Cord audit | Exit 0; 26 model IDs / 18 excluded / 8 represented |
| Descriptor/USDZ/source hash checks | Pass |
| Six ODR triplet checks | Pass |
| Six production packages | Model-only, with exact contact inventories and hashes |

## Limitations/conclusion

Evidence is simulator-only; no physical-device run was performed. Escape's retained GLB has a documented AABB symmetry exception. Evolv retains a source/CDN byte provenance limitation. All six boards are `noDocumentedSuspension` per the cord audit.

Acceptance supports the six-board routes, orientation framing, documented contact selections, targeted native behaviors, and workout preview/rest transition at the stated source revision. It makes no global collision-free claim: coverage is limited to documented selected pairwise/native checks. The full suite and prior package validation remain previously collected evidence, with only the five targeted native tests identified here as rerun on `f68`.
