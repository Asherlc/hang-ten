# Whole-module simulator recording

A fresh, exact-workspace-owned iPhone 16 Pro iOS 26.3 simulator ran the same 95
selected tests with zero failures. The HangTen compiler command contains -O and
-whole-module-optimization, retains DEBUG and excludes -incremental. Product
physics remains 597333b47; no app source or convergence setting changed.

The normal-speed app recording turns the Clavellium 30 degrees and returns upright.
It accepts 350 steps at 1/240 s, uses 1108 corrections, settles twice, and reports zero
failed batches, correction caps or retries. Maximum strain is 0.0197318% and
minimum original-mesh clearance margin is +0.099257 mm. These aggregate physical
values and step/correction counts match the previous incremental recording.
They do not substitute for a bytewise per-step compiler comparison.

Logged controller batch wall time is**2.684715s**, versus**3.146131s** in the
historical incremental recording. That includes actor scheduling and logs. The
batch schedule differs (86 versus 85), so 14.7% lower total time is evidence of this
build's observed performance, not a controlled attribution to compilation.
Batch-mean step p95 is 10.6663 ms. Those 350 steps simulate only 1.458333 s:
**real-time performance remains failed**. Neither recording establishes
individual-step p95 or physical-iPhone performance. Release already uses WMO;
there is no compiler-mode product change to adopt or rescue.

The 9-second clip uses AVFoundation passthrough trim only. All 559 nonempty
compressed sample payloads match the raw recording at one constant 4.186667 s
timestamp offset; maximum relative error is 8.88e-16 s. Four additional reader
samples have no compressed payload. Decode-order B-frame PTS are not monotonic;
this is retained explicitly and is not evidence of retiming. Frames show turn,
intermediate return and final upright state. No interpolation or speed change.

Exact recorder child received SIGINT and completed writing before its reserved
process group was cleaned. All invocation-owned groups were deleted and verified.
The exact simulator and DerivedData were deleted and independently verified;
shared DeviceHub and unknown resources were untouched. The adjacentJSON binds
source hashes, build/test log, runtime, timestamp proof, video and cleanup.

Video: https://github.com/Asherlc/hang-ten/releases/download/strong-owl-live-physics-wmo-20261003t024300z/strong-owl-live-physics-clavellium-wmo.mp4
