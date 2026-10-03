# Contact-inclusive sufficient-decrease checkpoint

The native-only solver keeps the complete original QP, objective, global merit,
trust bound, backtrack/correction caps, dt, physical convergence, original mesh,
CCD and rollback. It intersects original acceptance with Armijo sigma=0.1.
Length absolute-value and wood/portal max/hinge directional derivatives include
their one-sided kinks. Supports remain fixed; attachments and wood coordinates
follow the coupled height. Inside/zero-distance, singular portal, multi-cord,
self-pair and non-descent cases retain the original rule.

The first prototype passed locally but review identified discarded tied primitive
witnesses. **That prototype's pass is superseded, not adopted.** An ambiguity-only
fallback then never activated enough to pass the <=5-QP work gate. The corrected
required output carries all equal-best primitive fractions/normals through each
merit query and equal-depth face merge. Only merit outputs collect this metadata;
original row/point witnesses and arithmetic remain unchanged. A parallel-face
fixture moves the old winning endpoint away while moving the other toward wood;
both tied fractions survive and agree with an independent one-sided distance
query. Unique-point, max-tie, hinge, length-kink and binding fixtures pass.

On unchanged original prefix108 / fixed step109, the corrected result:

- uses **4 QPs versus 11**; a new sufficient-decrease rejection chooses half
  before the repeated tail;
- passes uncached original-mesh physical metrics and material/binding checks;
- differs from current by **0.2315 µm** and from a converged strict reference by
  **0.0929 µm**, with no strict retry;
- agrees with independently queried one-sided merit slopes at alpha=1e-5 to
  at most **1.386e-11** merit units/alpha;
- passes seven alternating complete-step pairs, median ratio **0.4460**.

**Bounded local checkpoint PASS; no product adoption.** Complete native candidate
steps still take about 10–13 ms in this run, above 4 ms. This tail-specific result
does not prove a general derivative certificate, complete trajectory stability,
real-time behavior or iPhone performance. Full trajectory/false-settle checks
are next. No new recording is claimed. A tied-output build first failed Swift
exclusivity and was corrected using a local immutable normal, without changing
physics or the gates. Exact owned process groups were independently verified
absent; adjacent JSON binds final and superseded evidence.
