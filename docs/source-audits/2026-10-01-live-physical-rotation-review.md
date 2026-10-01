# Clavellium physical rotation recording

The user requested seeing the board rotate through intermediate poses. The
[published 46.2-second recording](https://github.com/Asherlc/hang-ten/releases/download/strong-owl-live-physics-rotation-2026-10-01/strong-owl-live-physics-clavellium-rotation.mp4)
shows the existing solver driving a 90-degree turn and return to upright with
a fixed viewing direction. This is actual app capture at unchanged playback speed.
Startup and trailing idle time were trimmed with AVFoundation's passthrough
export; no interpolated frames or cached-path animation were added.

## Correcting the earlier recording's interpretation

Clavellium's delivered package has one presentation and one canonical physical
pose, `front`, with identity rotation. Its implicit position inventory includes
every contact. Selecting the top pinch and crimp therefore keeps the same
physical target. The contact tap resets the camera; `updateCameraTransform`
currently assigns its final transform even when `animated` is true, because its
animation branch is empty. The earlier hold-change recording consequently did
not test a physical turn or return. Describing its final view as a stalled
physical return was an incorrect inference, withdrawn here and in the public
recording notes. This review does not change that camera implementation.

## Capture and verification

The recorded source is `0da36b44144ed8adfece6455e3949d50e87d1210`. A signed
Debug build with `SWIFT_OPTIMIZATION_LEVEL=-O` succeeded on an isolated iPhone
16 Pro / iOS 26.5 simulator. The built and installed executable hashes match;
the runtime sources and packages were unchanged. The existing DEBUG controls
request `HANGTEN_REVIEW_ROPE_ROTATION_DEGREES=90` and
`HANGTEN_REVIEW_ROPE_ROTATION_SEQUENCE=0`. The latter changes target only after
an accepted settled frame. No camera gestures or hold taps occur during capture;
normal camera refitting at accepted rest remains enabled.

AXe recorded the display and finalized the MP4 on SIGINT. AVFoundation decoded
the raw capture and the trimmed 1206-by-2622 video. Reviewed decoded frames show
upright, intermediate outward rotations, the quarter-turn, intermediate return
rotations, and upright again. An anonymous download matches the published
asset's SHA-256 and all 3,808,620 bytes.

Evidence is retained under
`.context/strong-owl-live-physics-rotation-recording/`. Failed display readiness,
the much slower unoptimized capture, and an optimized-build verification
harness failure are retained separately. The harness had assumed Debug dylibs
that this optimized build does not emit; the final check hashes the executable
and the dylibs actually present. Every created simulator was deleted, all exact
owned command groups were released and verified, and DerivedData was removed.
The published video is a requested persistent deliverable. GitHub rejected
adding it to the earlier immutable release, so it was uploaded to a new draft
media prerelease, verified, then published.

## Limits

This is visual evidence of the current Clavellium transition, not a new contact
backend or catalog promotion. Live simulation still advances slower than real
time. The physical-device simulation-plus-mesh p95 gate, complete geometry and
contact performance gates, and the earlier incomplete iOS test run remain
open. Physics limits, material lengths, cord diameter, sliding passages,
coupling, collision checks, and seated cords were unchanged.

[Retained evidence hashes](2026-10-01-live-physical-rotation-review-summary.json).
