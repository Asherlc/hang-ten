# Current app recording request and fresh capture failure

The requested [turn-and-return recording](https://github.com/Asherlc/hang-ten/releases/download/strong-owl-live-physics-rotation-2026-10-01/strong-owl-live-physics-clavellium-rotation.mp4)
remains available. It is the previously published 46.2-second capture at
`0da36b44144ed8adfece6455e3949d50e87d1210`, not a fresh recording of the new
nonlinear defect correction. That correction is still a standalone experiment
and has not changed the app solver.

An anonymous download freshly matched SHA-256
`9fe264145f5717365eed42c3f9c81f0102480bae74200b3d0ff325b6a22fa005`
and all 3,808,620 bytes. AVFoundation decoded twelve frames across 46.2 seconds;
reviewed frames show upright, intermediate outward rotation, the quarter-turn,
intermediate return, and upright again. Playback speed and footage were unchanged.
The earlier capture and its limits remain documented in
[the original review](2026-10-01-live-physical-rotation-review.md).

## Fresh attempts

Three newly created, exactly owned iPhone 16 Pro simulators failed before app
launch. The source under review was `957ba2e9f549aea47916e869db9e867849e67389`.

1. On iOS 26.5, the signed optimized Debug build succeeded with the explicit
   UUID destination and workspace `.context/DerivedData`. Built and installed
   executable SHA-256 both matched
   `91a2bd46df79b61e401cf3864be200042bb9335f0abed19b4d4c77adb033bb6b`.
   A successful screenshot command was insufficient readiness evidence: the
   image showed the Apple boot-progress screen. Launch timed out after 150
   seconds. The resulting raw MP4 contains startup, not Hang Ten motion, and
   was not published.
2. A fresh iOS 26.5 device added a bounded complete `simctl bootstatus` check
   before building or recording. Contacts migration made no progress for about
   four minutes. Only the registered bootstatus command group was stopped;
   the exit trap deleted the exact device. No app build or capture followed.
3. A fresh iOS 26.4 device also stalled in `AddressBookLegacy.migrator` and
   reached the 300-second bootstatus timeout. Read-only diagnostics were
   retained; two bounded process-sampling commands also timed out. No app
   build or capture followed.

The build command was `xcodebuild -project HangTen.xcodeproj -scheme HangTen
-configuration Debug -destination platform=iOS\ Simulator,id=<owned-UUID>
-derivedDataPath <workspace>/.context/DerivedData
SWIFT_OPTIMIZATION_LEVEL=-O build`. The intended existing DEBUG route requested
Clavellium, front view, a 90-degree physical target, then upright after accepted
rest. No camera gestures, interpolated frames, tolerance changes, or new solver
integration were introduced. No new release or server was created.

## Source and cleanup verification

The sixteen source hashes in the prior recording's `files` map match the
current sources. All eighty-four files captured for the new build still match
its build manifest. Git diffs between the recorded and current commits are
empty for `HangTen`, `HangTen.xcodeproj`, and the Clavellium package.
The first comparison incorrectly treated the prior manifest's `commit/files`
wrapper as a file map; that check was rejected and corrected. A first cleanup
report also included historical process manifests under the parent evidence
directory; the final report restricts verification to newly created resources.
Neither rejected report establishes acceptance.

The three exact created UUIDs were deleted and rechecked against the current
device list. All 27 command groups created by these capture, diagnostic,
download, decoding, and verification runs were absent. Recipe DerivedData,
owned/pending simulator manifests, and recipe screenshot paths were absent.
Historical ownership manifests and shared devices were not used for cleanup.

Evidence is retained in the three timestamped attempts under
`.context/strong-owl-live-physics-screen-recording/`, with a final
`verification.json`. [Evidence hashes](2026-10-02-live-screen-recording-retry-summary.json)
bind only these fresh outputs and verification files.

This request produced no fresh app motion or new runtime performance evidence.
The full nonlinear correction, physical acceptance, and device performance
gates remain open. The available recording demonstrates the existing slower
solver only.
