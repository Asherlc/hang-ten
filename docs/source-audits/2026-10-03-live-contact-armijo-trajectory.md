# Contact Armijo trajectory: accuracy passes, real time fails

The corrected native-only sufficient-decrease experiment completed the fixed
540-step Clavellium turn240/return300 trajectory. The independently propagated
original control matches all prior correction counts, alphas, movements and
strains exactly. Every candidate step passes uncached original-mesh geometry,
material and binding checks. Sampled oracle runs match the timed candidate's
persisted physics checkpoint and decisions; transient caches and experiment flags
are not serialized. No product source or seated cord was changed.

Maximum propagated pose difference is **18.934 µm**, below 50 µm. Forty-six
same-input strict references converge without caps/retries; maximum difference
is **5.828 µm**. Both final quarter-second tails remain settled. Strict extra
steps from each first declared settle also satisfy the original history-based
settling condition. Both complete trajectories have zero caps and retries.

Performance fails: **4.765 seconds** of candidate engine work versus **5.004
seconds** of control, for **2.25 simulated seconds**. Candidate p50/p95 are
**6.852/13.754 ms**, versus control p95 **17.112 ms**. The candidate uses
1,528 QPs versus 1,657, but the total time ratio is **0.9522**. The earlier
single-checkpoint speedup does not establish a useful full-motion speedup.
**Closed as a performance successor; no app adoption or working-video claim.**

The first trajectory attempt stopped at the derivative oracle on step6.
Term-by-term queries reproduced a near winner switch on wood link139: endpoint
depths differ by 3.3966e-15 m, and their rates differ by 4.9563e-6 m/alpha. The
switch occurs at alpha approximately 6.853e-10, below all finite samples.
The unique winner's derivative at zero was correct; the finite secant had
already changed branches. Portal and length terms did not explain the plateau.

A near-tied plane fixture failed the old single-derivative finite model, then
passed a piecewise branch-envelope model. The repaired oracle retains all six
primitive branch outputs, including faces discarded by merges, only in disposable
verification copies. It separately requires analytic slope parity at zero and
queried-versus-linearized-envelope secant error at alpha1e-7, both <=1e-8.
Maximum observed last secant error is 5.000e-9. The last perturbation must remain
below the 10 nm activation buffer in board-relative motion and preserve portal
crossing segments; larger unsupported samples are reported separately.
No contact tie epsilon, solver slope, merit acceptance or error limit changed.
This remains a numerical screen, not a universal floating-point geometry proof.

Review also corrected the strict false-settle test to require its actual settled
condition and history displacement, and made oracle failures retain their samples.
Two compile-only errors (a duplicate fixture variable and a Swift operator/newline
spacing error) are retained separately from the expected RED fixture. All exact
newly owned process groups were cleaned and independently verified absent.
The adjacent JSON binds successful and failed evidence by SHA-256.
