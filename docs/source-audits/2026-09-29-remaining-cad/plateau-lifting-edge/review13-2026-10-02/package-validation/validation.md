# Plateau #13 frozen package and generic build validation

**Passed:** 191 measured host tests, all 64 canonical package checks, exact three-presentation Android/iOS delivery, and one generic iOS Simulator build-for-testing. No failing/error/skipped testcase elements were present. Tests stopped after this pass.

| Existing test scope | Raw JUnit testcase elements | Failures/errors/skips |
|---|---:|---:|
| Descriptor/contact-model package | 15 | 0/0/0 |
| Manifest/CAD sidecar/board catalog/pose-camera | 171 | 0/0/0 |
| Selected native-route solid/terminal/clearance/span/loop checks | 5 | 0/0/0 |
| Total host tests | 191 | 0/0/0 |

Raw XML counts were parsed independently after execution and matched the suite counters. [Package result](package-validation.json) retains exact commands, exit codes, per-job raw log/JUnit hashes and cleanup. [Fresh verification](final-verification.json) retains independent raw-result, frozen identity, file scope and cleanup checks. The official CLI's raw JSON contains 64 unique boards and zero drafts.

The frozen [eight-file input](frozen-input.json) binds FCStd `b1c701af3ea5515b73e5b3641612f15953ecc3fb109332e95470bd70f9da7986`, sidecar `b59eab42fe4416ebd42636adbaa88e69fc4b344d588a5a7537906490483b7d80`, and all three USDZ/descriptor pairs. Exact generated manifest SHA-256 is `5aea5c9c3e9bc261ecea2f4ecca442ec512318dd1feb4be45af071d4f4c138d4`. Android staged that exact manifest, three descriptors and three inline models. The actual built iOS app staged the same manifest/three descriptors and the exact three model bytes in ODR. Both exclude native authoring files and merge suspension into generated board.json. Actual built descriptor/ODR copies are retained under `ios-build/built-descriptors/` and `ios-build/built-odr-models/`.

The one generic `build-for-testing` exited 0 in **50.509199208 seconds**. Its [raw log](placid-badger-plateau13-ios-build.log) contains `** TEST BUILD SUCCEEDED **`; SHA-256 `bbef5cc0b8aba9de0736319772af641953ae64cae759fd9decdf81adab4209ec`. [Build provenance](ios-build/build-validation.json) records commit `8b1bbd0858ca3e81bc7c43ad842a80ff9ca2138b`, dirty diff SHA-256 `daa47e94f2e4ef52e20ca0cbb6f1b1e9475d8e1c1af2f4a3bd8319eca269bb9f`, and actual built executable SHA-256 `df835a5cc51ef664913fca7f91a4c6b91a5ad14b8d05f921404c1c342e137fc7`, measured before Derived Data cleanup. The test bundle was compiled; **zero iOS test cases executed**.

Fresh verification confirms all eight canonical frozen files remain exact, all 198 other tracked package files are unchanged, all five reserved shared files are unchanged, and CAD/model/package tools were unchanged. Across this validator and the material authoring lane, **12 exact owned process groups and 17 exact owned temporary/staging/Derived Data paths are freshly absent**. The validator itself owns six groups/eight paths; material authoring owns six groups/nine paths. Raw logs and review artifacts remain; no live resource remains in these lanes.

Current app frames, Simulator guest creation/boot/install/launch, and HTTP resources are all **zero**. Runtime was previously blocked; current finish, cord, picking, and workout appearance remains unverified. These are package/build proofs, not app runtime or human geometry acceptance. Historical captures and historical test totals remain separate. Human acceptance is pending.
