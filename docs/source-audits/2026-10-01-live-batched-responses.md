# Batched globally coupled responses: bounded cold gate still fails

User requested continuing the measured response-construction work. Base `76b3fcd86`, branch `feat/live-hangboard-physics`. This adds an **opt-in native experimental tool**, `--batch-responses`, requiring `--global-schur`; scalar responses remain the default. App sources, seated cords, CAD geometry, source contacts, coupling and physical/numerical limits remain unchanged.

The same-source scalar control took **432.729 ms** and the batch pilot **324.734 ms** on the exact retained 2,123-contact frozen candidate. Response construction fell from **286.290 to 199.371 ms**. This is one sequential control/pilot pair, an indicative observed reduction of about 25% cold and 30% in responses, not a statistical or device result. The unchanged **2 ms** cold gate and optional 20 ms diagnostic milestone still fail. No trajectory, general region certification, 50-run expansion or product adoption follows this failed screen.

## Implementation

The tool extension calls `DGBTRS` and `DGETRS` with independent RHS columns, reading the original immutable pivoted band and Schur-border factors. It retains every border variable and recovers each RHS with the original inverse border columns. No approximation, regularisation adjustment or per-rope decoupling is introduced. The pilot combines batching with the previously measured `--blas-product` original-matrix product; both flags are explicitly captured in provenance and default off.

Batch refinement checks the original coupled matrix separately for each column with the existing scaled `1e-12` criterion and at most three correction solves. Converged columns are frozen; unconverged columns retain their own RHS norm and residual. Invalid shapes, nonfinite values or excessive batches reject. Temporary batches are limited to **64 RHS columns and 500,000 combined entries** per buffer. Existing persistent response-cache and working-array budgets remain unchanged.

The contact session collects uncached unique Jacobians in source order and processes bounded chunks. Identical Jacobians share only responses, while every original contact residual remains in the QP. Earlier successfully cached responses remain valid if a later batch fails because they depend only on the immutable factor and Jacobian; failure still prevents an accepted correction.

## Evidence

Authoritative evidence is `.context/strong-owl-live-physics-batched-response`; the companion summary binds fresh copied native sources and relocated snapshot references, plans, observed RED/GREEN logs, fixed inputs, replay/oracle/physical results and exact cleanup receipts with SHA-256. Sources are the bytes compiled for each labelled run, not pointers to later repository files.

| Fixed cold measurement | Scalar control | Batch pilot |
| --- | ---: | ---: |
| Total solve and full affine checks | 432.729 ms | 324.734 ms |
| Contact-response construction/cache | 286.290 ms | 199.371 ms |
| Compliance construction and finite scan | 9.253 ms | 5.023 ms |
| Contact Newton factorisations | 39.378 ms | 33.251 ms |
| New/cached working responses | 836 | 836 |
| Batches / Newton factors / admissions | 0 / 21 / 1 | 14 / 21 / 1 |

No admission added rows. The clock includes cold equality construction/factorisation, row construction/discovery, solve and full affine checks; frozen JSON decoding, geometry generation and original mesh checking are excluded. Exactly one scalar and one batch cold replay ran, sequentially with no concurrent task benchmarks. The changed timing of untouched compliance/factor work illustrates why these are single-run observations rather than proven speedup ratios. The 199 ms response cost remains dominant, and even the measured 33 ms contact factors alone exceed the total gate.

All **4,279 primal components are bit-identical** between the same-source control and batch. Independent full new-row checks pass: stationarity 2.0370e−22, regularised equality 4.8448e−20, complementarity 8.4518e−19, all-row violation 6.0611e−16, zero dual/slack violation. The independent sparse active-KKT oracle agreed within **0.031351 µm**, with every new row checked after recovery. The original frozen affine-gap minimum was 4.1989e−13 m for this one correction; this does not certify the generic nonlinear channel-to-facet representation.

A freshly compiled original triangle checker performed **2,858 point/full-link queries**, reporting minimum clearance **3.603605 mm**, radius margin **103.605 µm**, zero original wood sweep blocks and **16.073 µm** difference from the retained original-facet correction. Strict 50 µm and isolated 100 µm wood-clearance flags pass. This remains a single Newton correction: **16.798447% strain and 1.578431 mm material-length error fail the final physical gates**. Neither candidate nor facet control is an accepted nonlinear timestep. No topology, bearing, nonlinear self/intercord, general CCD, verification-time or settled-trajectory acceptance is claimed.

## Verification and review

New hand-derived pivoted/no-border/two-border batch cases and input validation were observed RED (10 assertions against an empty scaffold), then GREEN. A shared-Jacobian/different-residual cache test was observed RED before batch integration and GREEN afterward. Native fixtures passed **24/24 with batch plus BLAS enabled** and **22/22 on the default scalar path**. Full Python prototype suite: **61 passed, 3 failed**, with the same absent historical solver dependency:

- `test_rope_settles_around_outside_of_round_bar`
- `test_wrong_wrap_topology_is_rejected`
- `test_fresh_simulations_are_repeatable`

These require the absent `.context/frantic-kiwi/rope-build/rope_solver`; no historical binary was restored or executed and no failure was turned into a green gate.

One fresh scoped final review found **no Critical or Important issue**. It independently checked captured source hashes, current source correspondence, same-source scalar/batch snapshots, fixture logs and identical primal components. Minor deferred: tests do not independently exercise the 500,000-entry rejection below the 64-column cap or mixed columns needing different refinement counts; both guards and masking were inspected as correct. No fix pass or re-review was needed.

Rulings, with costs if wrong:

- Retain the owner-named evidence/ledger rather than delete skill scratch state: user handoff and retained-input requirements take precedence. Cost: additional ignored disk evidence, no product change.
- Accept only the subsequently completed, directly read default-fixture and fresh mesh logs where the reviewer declined pending results. Cost: reject the experiment if those diagnostics are wrong, app unchanged.
- Keep broader trajectory/device acceptance unclaimed: those gates did not run and this correction fails final strain/length. Cost: an unadopted prototype, no product behaviour change.
- Keep statistical speedup unclaimed: one sequential control/pilot pair does not establish reproducibility or p95. Cost: repeat the performance screen if the observation is misleading.

All 25 new/current recorded child or driver absences were verified after owner cleanup. Generated outputs and pytest temporary bases are workspace-owned; shared and historical resources were untouched. No server or simulator was started. The earlier channel trial's deferred physical-flag versus nongreen exit-status distinction remains documented in its audit; every failed experimental performance screen remains nongreen.
