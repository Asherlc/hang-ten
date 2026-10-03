# Frozen active-KKT initializer adds a fresh QP at the ordinary checkpoint

The new initializer failed its fixed step-140 work gate: **three fresh authoritative QPs versus two original**, rather than the required one. It closes before seven-pair timing or trajectory expansion. No rotated-frame extension or app adoption followed.

The initializer captured the existing equality factor, active contact responses and Cholesky factor from the actual last pre-update linearization of accepted step139. It froze the entire matrix/layout/H/J/regularizers, anchor and residuals, required unchanged orientation/dt/material bindings, and solved a new affine load at the unchanged free predictor. The resulting point was only a starting guess; no estimated forces/tensions/velocities were committed. The ordinary full geometry, globally coupled QP, merit, convergence, mesh/material/CCD and transaction checks remained authoritative. Capturing the next operator was included in candidate work.

The retained operator passed an independent dense 5×5 mixed equality/contact/height oracle with changed loads and repeat-load bitwise immutability. Behavioral RED failed actual operator capture. GREEN preserved prefix trace identity and the complete persisted physical checkpoint at priming step139, and applied the initializer in 0.246167 ms. The subsequent correction norms were 43.138421 µm (half step), 21.807252 µm (full) and .233149 µm (full). A frozen previous operator did not bring the nonlinear next-step problem close enough to remove the initial fresh pass.

Final current pose difference was 1.741613 µm, strict same-input difference 75.520918 nm, with original physical acceptance and zero caps/retries. Accuracy does not rescue the failed work gate. Absolute unpaired timings are retained but not treated as a paired speed result.

All four new private groups were independently verified absent. Companion JSON binds source/results/proposal/resource provenance. Product solver/CAD/assets/seated cords were untouched. No simulator/video/readiness claim follows.
