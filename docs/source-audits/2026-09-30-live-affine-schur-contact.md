# Affine certificates and global contact condensation — 30 September 2026

This checkpoint retains two bounded successors to the contact experiments in
the [complementarity audit](2026-09-30-live-complementarity-contact.md). Neither
is selected by the application. Seated cords and the frozen accepted CAD work
remain available; no board geometry or package metadata changes.

The optional `--regions` hierarchy groups frozen rows by their identical
ordered variable support. Coefficient and residual intervals enclose every
original row. Outward rounding follows the original sparse arithmetic order,
including duplicate indices and the regularized multiplier term. A node is
skipped only when its entire interval, including intermediate arithmetic,
proves finite and feasible. Uncertain nodes descend to original exact rows.
Height, opposing facets, multiplier signs and admitted-row violations remain
part of the certificate. The hierarchy bounds its storage and retains complete
source coverage.

Seven certificate fixtures pass, following six expected failures against the
empty implementation. Every query in the fixed hard and full-production frozen
replays agrees with a complete packed-row scan; independent full-matrix checks
also pass. However, hard hierarchy construction takes 11.381 ms and production
construction 35.182 ms, exceeding the entire 2 ms cold-QP budget. Queries are
also slower than a flat packed scan: hard 0.39–1.97 ms versus 0.13–0.57 ms;
production 0.76–0.81 ms versus 0.57–0.59 ms. The latter certifies 119,781 of
119,953 rows initially and 119,949 finally. The construction checkpoint rejects
this post-generation hierarchy without expanding to 50 runs or tuning caps.
It does not avoid geometry or row generation and supplies no 50× geometry proof.

The experimental `--global-schur` backend computes contact compliance through
the original globally coupled chain, length-equality and height factor. A
session caches exact Jacobian responses only within that immutable frozen
factor. Both ropes, nonlocal contacts and height remain coupled. The changing
contact Newton system uses this compliance; final recovery checks the original
physical matrix, every working row and every frozen source inequality.
Regularization, material resolution, contact radii and all acceptance limits
remain unchanged. Array, dimension, nonlocal, iteration and admission caps
still apply. This is a numerical condensation, not a separate solve per rope.

The first condensed Fischer–Burmeister method passes the original 19 fixtures
but rejects the hard replay at admission five, iteration 22, at its existing
20-trial line-search bound. Retained diagnostics independently reproduce an
accurate Newton direction; safe descent requires a step near 2^-25 as almost
inactive contacts close. That globalization remains explicitly reproducible
with `--schur-fb`; the trial cap was not increased.

The successor uses simultaneous positive-force/slack Mehrotra iterations on
the same compliance. Initially stopping at the acceptance complementarity
floor yielded a 5.144486 µm oracle error and was rejected. An internal 1e-18
barrier stopping criterion, stricter than the unchanged 1e-14 acceptance limit,
brings the hard replay within the existing 1 µm oracle gate. Iterations per
working QP remain below 50.

Focused review identified cancellation when recovering original contact gaps
from condensed values. A regression reproduced acceptance of an invalid
original complementarity certificate. Final certification now evaluates
`C + Jx` and `C - epsilon * multiplier + Jx` separately, in original sparse
order; it also checks original stationarity order. The regression fails before
the correction and passes afterward, requiring a valid original certificate or
rejection. The Schur fixture suite passes 20/20; the default suite passes 19/19
and region suite 7/7. Review's effective packed-source reporting and validator
snapshot findings are also addressed.

The final reviewed hard replay retains and independently checks **all 50 cold
solutions**, not just the last. Each run includes equality assembly/factor,
source construction/packing, response/cache construction, all Newton work,
admission and original numerical/affine certificates. Posthoc independent
Python/oracle checks and output serialization are outside the clock; native
acceptance certificates are inside. Compiled source, driver and independent
validator bytes are captured before compilation and used from those snapshots.

| Final hard replay | Result |
| --- | ---: |
| Frozen source rows | 22,641 |
| Admission passes / final working rows | 9 / 409 |
| Independently certified cold runs | 50 |
| Maximum stationarity residual | 3.79806e-20 |
| Maximum regularized equality residual | 8.35774e-20 |
| Maximum complementarity residual | 3.13745e-19 |
| Maximum physical inequality violation | 1.06614e-13 m |
| Maximum primal difference from oracle | 0.249096 µm |
| Cold-QP p95 | **374.019 ms** |

The fixed 2 ms cold-QP gate fails; replay exits `3`. Pre-review 320.557 ms is
retained but is not the final reviewed result. Shared-host timings do not
establish a controlled improvement over the earlier 487.418 ms or device speed.
Contact factorization alone takes 44.67–76.30 ms per cold hard replay; other
construction and scalar work remain substantial.

The reviewed full-production first frozen QP retains both 715-particle loops,
1,428 equalities, height and all 119,953 source rows. Its one cold run takes
208.762 ms, with 158 working rows and independent original-matrix checks
passing. Response/compliance construction takes 82.363 ms; 20 contact factors
take 0.575 ms. There is no production oracle, p95, initialization, trajectory or
settled-frame proof. This run also exits `3` and cannot authorize adoption.

The focused Python numerical and lifecycle suites pass 28 tests. The complete
prototype suite has 42 passes and three legacy integration failures because
its hardcoded `.context/frantic-kiwi/rope-build/rope_solver` executable is absent:
round-bar settling, wrong-wrap rejection and repeatability. That historical
resource was not recreated or touched. The intentionally failing live catalog
inventory WIP remains untouched and is not counted as a passing gate.

The [evidence manifest](2026-09-30-live-affine-schur-contact-summary.json) binds
immutable tested-source snapshots, retained inputs, red/green results, rejected
diagnostics, final replay outputs and static ownership records. Exact owned
compiler/probe/driver cleanup was verified. No server, simulator or device
installation was created. Complete geometry, CAD error, physical motion,
visual/device performance and catalog promotion gates remain open.

The user subsequently noted the small display may not require perfect visible
detail. Rendering and physical error limits are separate decisions; this
checkpoint retains the original limits. The next geometry successor must avoid
creating most source rows, with a conservative bridge to original affine
inequalities, rather than construct another expensive hierarchy afterward.
