# Live Clavellium runtime recording

A fresh optimized Debug build on an isolated iPhone 16 Pro / iOS 26.3
simulator displays the physical solver turning Clavellium 30 degrees and
returning upright. The fixed camera receives no gestures. Reviewed decoded
frames show intermediate outgoing and returning orientations, the 30-degree
destination, upright again, and the attached cord throughout.

The [18-second demonstration](https://github.com/Asherlc/hang-ten/releases/download/strong-owl-live-physics-live-motion-20261002t225330z/strong-owl-live-physics-clavellium-demonstration.mp4)
uses native `simctl recordVideo`, followed by AVFoundation passthrough trimming
of startup and idle tail. All 1,122 compressed video samples in the clip match
source samples. Their presentation timestamps differ by one constant offset;
the maximum relative timestamp error is 2.23e-15 seconds. Playback speed is
unchanged. Encoded B-frame order is not presentation order; the first attempted
monotonicity check was therefore not an appropriate verification.

## Component evidence

Optional DEBUG tracing, enabled by
`HANGTEN_REVIEW_LIVE_ROPE_DIAGNOSTICS=1`, records selection, activity, controller
ticks, worker batches and delivery identity. It writes directly to stderr so
the trace does not depend on stdout buffering. This changes no solver equations,
physical gates, scheduling rules, material lengths or cord dimensions.

The recording run returned 83 deliverable batches with no runtime failures,
reached 30 degrees, returned to zero and delivered two settled frames. Batch
duration ranged from 61.614 to 743.816 ms, with a median of 111.579 ms. Each
batch advances several fixed physical steps; these are not per-step timings
or physical-device performance measurements. The performance target remains
unmet.

The previous stationary recording had no component trace. Its cause is still
unestablished. The fresh build works without a behavioral fix, so this result
does not justify claiming that the previous failure was a paused scene or a
slow solve. Clavellium package metadata and physics payload are byte-identical
between the two builds.

## Verification and limits

The signed build command was `xcodebuild -project HangTen.xcodeproj -scheme
HangTen -configuration Debug -destination 'platform=iOS Simulator,id=7396060C-E3CF-4634-892C-42F4977609F1'
-derivedDataPath .context/DerivedData SWIFT_OPTIMIZATION_LEVEL=-O build`.
It passed. Four existing schedule and delivery-identity test bodies passed in
a native assertion adapter. This does not establish an iOS XCTest suite pass;
direct host XCTest compilation attempts failed because the test framework and
Swift overlay were not configured. The installed executable hash was not
captured before cleanup; the build hash is retained separately.

The first video inspector used deprecated synchronous asset loading and found
no track. Async loading succeeded. Early timestamp checks also mishandled GOP
preroll and duplicate compressed samples. The final check matches each sample
and its presentation time against the source using one common offset.

Evidence is under
`.context/strong-owl-live-physics-runtime-debug/20261002T225330Z/`.
The exact owned simulator was deleted and verified absent, private command
groups were released and verified, and generated DerivedData was removed.
No Mini or catalog profile was promoted. Seated cords remain available.

[Retained evidence summary and hashes](2026-10-02-live-rope-runtime-recording.json).
