# Bounded batch active-KKT discriminator: rejected

The frozen smooth-channel contact problem still needs more than three direct
active-KKT factors. The fixed screen stopped after the third factor with
negative contact forces, violated inactive rows and a **7.170569 mm** difference
from the independent reference. No fourth factor, damping rescue, native
implementation or app adoption followed.

This count-only SciPy experiment starts at `06526289d` on
`feat/live-hangboard-physics`. It uses the same 2,123-row channel candidate
(`1397e7a50e451a1fad6961cbba403c744f3d72de8464d57ac4bfb600e1f38719`),
both material chains, board-height coupling, all nonlocal rows and epsilon
`1e-8`. One unconstrained equality factor initializes the correction. Every
violated source row is then admitted; each pass solves the original sparse
coupled active KKT matrix, releases every negative contact force and admits
every violated inactive row. It uses no contact-response inverse, warm active
set or reference-derived initialization. The independent reference is read
only after all pass decisions. Strict force-sign rejection and original-matrix
refinement remain required.

The fixed stop is three active factors or a repeated active status. Initial
admission contains 850 rows; the native IP's 836 grouped representatives are
a different admission procedure. No source row is omitted in this screen.

| Active factor | Active rows | Released | Admitted | Minimum force | Minimum regularized gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 850 | 73 | 135 | −109,595.81 | −0.076958 mm |
| 2 | 912 | 114 | 380 | −20,669.94 | −0.564691 mm |
| 3 | 1,178 | 229 | 45 | −3,794.71 | −0.596039 mm |

No repeated status occurred within these three passes. The required next pass
violates the predeclared budget, so this line stops. Final stationarity
`1.23e-11` and regularized equality `4.53e-19` do not compensate for invalid
contact forces, gaps or the failed 1 micrometre reference comparison. No
accepted QP or nonlinear step is produced. Python elapsed time is not native
performance evidence; the unchanged 2 ms cold-QP gate was not measured here.

The first attempt failed before any active contact factor because it treated
`factor_system`'s return tuple as a callable. The corrected attempt unpacks
the closure in both locations. Both sources, logs and the integration error
are retained separately. The three-pass numerical failure is the corrected
attempt's result. A native candidate and its known cycling-fixture tests were
conditional on this screen passing; neither was built after failure.

Actual Opus advisor `27112130-8814-402f-82ca-d15778938ae4` reviewed the rule
before the screen and the failed trace afterward. Its recommendation is to
close this pass-reduction line and return to frame-level geometry and row
assembly. Its broader algorithm and convergence estimates are advice, not
measured impossibility bounds. The earlier packed-primitive and sparse-LDL
results remain immutable. No cap, tolerance, cold-budget definition or physical
model changes are authorized by this result.

The companion summary binds the fixed inputs, experiment sources, complete
trace, advisor response and cleanup receipts. Both owned probe groups, both
driver processes and the advisor guard are verified absent; the advisor is
archived and closed. No server or simulator was created. Seated cords and the
intentional failing live-inventory WIP remain unchanged.
