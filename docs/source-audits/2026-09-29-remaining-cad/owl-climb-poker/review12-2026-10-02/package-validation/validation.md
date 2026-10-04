# Owl Climb Poker #12 package validation — 2026-10-02

Owner: `placid-badger`. **Package checks and generic compile/staging pass.** Current appearance and runtime remain unverified. No geometry acceptance was recorded.

| Check | Measured result |
| --- | --- |
| Retained descriptor/package/import/YY tests | 24 passed; zero failures/errors/skips |
| board_manifest/cad_sidecars/board_catalog/pose_camera_facing | 171 passed; zero failures/errors/skips |
| Canonical CLI, final inventory | 64 boards validated; zero drafts |
| Actual Android staging | Generated manifest, descriptor, inline USDZ match exact frozen bytes; FCStd and suspension sidecar excluded |
| Generic iOS Simulator build-for-testing | One attempt, success in 47.92 seconds; test bundle compiled |
| Fresh cleanup verification | All five process groups absent; all seven owned TMP/staging/Derived Data paths absent |

Frozen FCStd: `26476221de9031703c0536e31c7341eb6ba1d6d5176c1c72acd0b06c3d546553`. Frozen USDZ: `1ee84de3f5054d55bd1078e466499cbc508decd11826bd5e626b349a75ba3675`. Frozen descriptor: `b2fd8b5ff18c57b38d48daaa93e613c00061bb3e61e444d741871e8fe10a3032`. Exact generated manifest: `899a998c12fc245f1e2120c666694f38cf2f0d0120ef8fcfdab1cee7df31e2d1`. Both platforms stage that exact manifest and descriptor; Android stages the exact USDZ inline and iOS retains it only in the Poker ODR asset pack. All 34 contacts, four ordered positions and rotations match the baseline; the sole factual-manifest addition is `surfaceFinish: wood`; suspension remains absent. The final frozen files still match after every check and build.

The generic build started at commit `ad74a51e1c43991145721ab04ff8c0d3c6c51cca` with recorded dirty diff `b461e0c0ad7852d124a61849f8b45a9f9bc9f55722e3a1b5ffc3ea0572f739f3`. Built binary SHA-256: `7ba82cd2b3dc7383892f91c8e6308786eb768fe4482850edbb2a433663f6832e`. Exact command, staged file/ODR paths and hashes are retained in [ios-build/build-validation.json](ios-build/build-validation.json); build-start source state is in `ios-build/build-dirty-diff.patch` and `ios-build/git-status-before.txt`.

**Current app frames: 0. iOS unit test cases executed: 0. Simulator guests created/booted: 0. Apps installed/launched: 0.** This compilation does not prove current app appearance, picking, highlighting, orientation behavior or renderer fidelity. The runtime environment was previously blocked; no new guest attempt occurred.

Measured JUnit counts and artifact hashes are in [final-verification.json](final-verification.json). Raw logs: [model tests](placid-badger-poker12-model-tools-pytest.log), [manifest/package tests](placid-badger-poker12-manifest-package-pytest.log), [canonical CLI](placid-badger-poker12-canonical-cli.log), [Android staging](placid-badger-poker12-android-staging.log), [generic iOS build](placid-badger-poker12-ios-build.log). Per-job ownership and cleanup JSON files retain each exact PID group and removed resource path. No canonical, shared renderer or dated audit file was edited by this validation task.
