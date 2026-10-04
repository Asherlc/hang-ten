# Majorizer-conditioned physical residual stop — CLOSED

2026-10-03, base `0afd515b3`. Native-only; user authorized all experiments, original physical limits unchanged.

Registered separately from closed first-feasible and original-H residual-only experiments: retain positive moving-fraction wood curvature as the poststep residual preconditioner; use fresh original objective/constraint residuals and raw accepted QP multipliers, complete unique source-feature correspondence, updated compression signs, all fresh affine-row checks, actual alpha1 and original phase estimate norm (50 µm turning / 4.167 µm arrived). A successful estimate may replace auxiliary numerical strain0.0002 with ORIGINAL physical strain0.005/material error0.5mm. No estimate position/multiplier is applied; no added majorizer physical force. All final mesh/topology/self/CCD/speed/settle/rollback checks remain. This norm is an estimator, not a proved nonlinear pose bound.

Astra reviewed the mathematical proposal and found no fatal algebra/model problem, with the above qualifications. The unchanged auxiliary-strain composition was already closed from the prior trace and was not built.

Fixed140 first, required **one QP**. RED disabled residual: actual2, correctly failed the one-QP work assertion. Enabled GREEN candidate also **2 QPs**, **zero eligible residual estimates**, **zero residual stops**. Thus **FAIL**, close without tuning. No3/109/full-trajectory/timing expansion or simulator adoption.

Both accepted corrections had alpha1, first strain0.0002136764 and movement158.580µm, second strain9.7323e-7 and movement2.810µm. Physical feasibility alone therefore did not make the stricter residual checks eligible. The screen did not record which guard rejected each estimate; do not attribute failure to a particular correspondence, stationarity or affine check.

Current difference1.722µm; strict same-input0.138µm; original-mesh/material checks pass; caps/retries0. Single candidate6.223ms/control5.595ms is diagnostic only, with extra native feature provenance on both paths; seven pairs were correctly not run after the work failure. No real-time or video result.

One whitespace source-transform mismatch and an out-of-scope inherited inactive Armijo expression were setup/build failures, not RED evidence. The isolated screen explicitly uses original merit; every required composed source marker is asserted. Enabled/disabled runs reproduce all139 prior numerical trace steps, and produce the same accepted candidate state as the retained majorizer alone at140.

Five exact private groups created by these runs were cleaned and independently verified absent. Adjacent JSON retains source/output hashes and the rejected result. Product solver, CAD, materials, seated cords and inventory WIP remain unchanged.
