# Radius-limited planar-union primitive: closed cost screen

This isolated native successor changed the required-output problem from unbounded
polygon minimum distance to radius-limited contact. Same-side endpoint projection
can attain the whole plane lower bound; immutable boundary-edge boxes exclude
pairs beyond the unchanged row radius, with a 1 nm conservative inflation.
Holes, disconnected regions, endpoint ties, exact actual-mesh binding and whole
original-patch fallback remain. Behavioral fixtures observed RED then GREEN.

All four maximum depths match the original exactly on the fixed 3,236-query
chronological nonempty corpus (no inside endpoints). The primitive makes 18,149
region calls, 1,771 boundary pairs versus 269,200 unbounded, and zero fallbacks.
Seven alternating original/unbounded/clipped triplets FAIL both registered cost
gates: median clipped/original 0.723555 exceeds 2/3; clipped/unbounded 0.868038
exceeds 0.80. Final clipped corpus times are about 33.5–35.5 ms, original about
47.0–48.8 ms. Earlier triplets are slower; all seven remain in the result.

Original parity packing and immutable collider/atlas initialization are excluded
equally. Full traversal, membership, boundary work, witness outputs and merges
are timed. This is no complete-step or device result. Geometric maximum-depth
agreement does not prove original rounded merit, forces, old facet affine rows
or nonlinear convergence. No nonlinear, full trajectory, simulator or video
stage opens. No group, radius, threshold, kernel or schedule was tuned after the
failure; this line is closed. Product solver and seated cords remain unchanged.

Six newly owned compile/run groups are independently verified absent. Companion
JSON binds source/result/proposal hashes and retained ownership evidence. A
workable normal-speed simulator video remains outstanding.
