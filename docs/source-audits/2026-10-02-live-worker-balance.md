# Fixed-four worker balance ceiling

Current-source step 140 matches an independent unchanged control through the
139-step actual-seed prefix and seven complete checkpoint pairs, including the
two corrections and zero cap/retry schedule. The only timed instrumentation
writes per-worker durations and face counts into disjoint initialized slots;
the driver reads them after the original joins. Arithmetic and scheduling are
unchanged. A missing Foundation import caused the first compile to fail before
any measurement; the corrected capture is retained separately.

All three evaluations concentrate candidate work in the middle two jobs:
[0, 2567, 2411, 0] faces. The optimistic sum of maximum minus mean narrowphase
worker duration is **0.7875ms**, or **18.235%** of the paired **4.319ms** unchanged
complete step. Instrumented wall time is 4.411 ms. Even perfect distribution
misses the preregistered 20% necessary ceiling before scheduling overhead.

The fixed-four round-robin narrowphase candidate was therefore not implemented.
This scheduling line is closed without parity activation, job width, schedule,
fixture or threshold rescue. It is a host-only one-step cost discriminator,
not an iPhone performance distribution or proof that no accurate solver exists.
The adjacent JSON binds plan, result, captured sources and exact process-group
cleanup verification. App source is unchanged; real-time performance is unmet.
