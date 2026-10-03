# Bounded busy-clock scheduling experiment

The controller discarded display elapsed time while its worker was busy, then
waited for another tick after completion. A DEBUG-only review switch accrues at
most eight pending 1/240-second steps and drains them after valid delivery or stale
result handling. Default DEBUG and Release behavior remain unchanged. Physics,
maximum batch size, target validity, cancellation, pause/sleep and stop stay intact.

Native clock RED/GREEN and 98 selected simulator tests passed, including busy-clock
draining and independent exact worker-state comparisons across a target change.
Review caught a deferred drain crossing an error handler; that was corrected
before capture. The first build was interrupted, cleaned, and retained without
timing; the corrected fresh simulator supplied both recordings from one binary.

Both normal-speed recordings accepted 350 steps and 1,108 QPs, with identical
per-phase targets/work counts, two delivered settled states, zero caps/retries,
maximum strain 0.000197318 and minimum clearance margin +99.2566 µm. Nine-second
clips preserve compressed sample payloads and timestamp spacing; no speedup or
interpolation was applied. Sampled frames show the turn and return with the cord.

End-to-end time fell from 3,660.311 to 2,971.183 ms, ratio **0.811730**, failing the
registered ≤0.80 gate. Worker solver execution was 2,838.537/2,901.969 ms for
1,458.333 ms of simulated motion. Individual-step p95 was 15.110/14.600 ms, failing
the separate <4 ms target. Diagnostic writes are included in the post-worker
bucket; inter-batch time includes delivery and target transition. This is simulator
evidence, not device evidence or accepted real-time performance.

**FAIL/CLOSED; not adopted.** No scheduling or timing rescue. The review flag and
measurement tools remain isolated evidence. Exact owned simulators, DerivedData
and process groups were deleted and independently verified absent. The adjacent
JSON records measurements and SHA-256 evidence hashes.
