# Force-scaled merit screen: closed on work count

User authorized all isolated experiments. This native-only screen changed only
merit weighting, keeping original240Hz integration, coupled solve, material,
full original triangles, CCD, trust and physical convergence limits. Astra checked
rho=max(previous,2*max(max absolute equality lambda,sum absolute contact lambda)),
reset per advance. Contact summation conservatively covers grouped maximum-depth
merit terms. This is a dual-scale rationale, not a convergence theorem for the
actual deadzoned, regularized frozen-facet model. Units are kg*m; no dt² conversion.
Primary exact-L1/SQP context: https://publications.syscop.de/Diehl2016.pdf.

The scalar curved-equality fixture failed with the original unit floor (RED), then
passed with the force scale, grouped-multiplier and envelope/reset checks (GREEN).
The first snapshot assertion rejected an ambiguous anchor before any process was
started; the anchor was scoped to advance's prediction/cache reset pair.

The exact108-step control prefix passes. At step109, rho falls from the original
unit floor to0.00070055–0.00070335, but all accepted alphas, movements and strains
remain bit-identical. Both candidate and control use11 QPs, failing the fixed≤5
work gate. Final pose matches exactly; strict same-input difference is0.147µm,
physical checks pass and strict reference converges without retry. This refutes
merit scaling as a cure for this measured tail. No formula tuning followed.

Seven-pair timing and trajectory stages were not reached. No app change, simulator
recording, p95 or performance gain is claimed. Adjacent JSON binds evidence and
independently verified absent owned process groups.
