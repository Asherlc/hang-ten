# Accurate primal contact checkpoint; live speed remains open

Base `9df13f132`, branch `feat/live-hangboard-physics`. User asked to continue implementation and consult Opus if needed. This work adds isolated native-tool flags for primal convergence/recovery, diagnostic timers and one rejected symbolic-ordering experiment. App sources and seated cords remain unchanged. No production acceptance limit, material model, coupling, collision requirement, regularization or iteration cap changes.

The useful result is an accurate sparse-primal correction on the smaller channel row set: one cold replay took **48.582 ms**, versus **315.037 ms** for the instrumented batched Schur checkpoint. These are individual observations, not a statistical speedup or device result. The unchanged **2 ms** cold gate still fails. The retained correction remains a single Newton step, not accepted settling.

## Accuracy discriminator

The original primal backend took 46.893 ms on the same 2,123-contact candidate, with 836 admitted rows and one admission. Full residual checks passed, but its primal differed from the accurate Schur reference by **3.674 µm**, failing the mandatory 1 µm comparison. It stopped at complementarity's acceptance floor rather than the tighter internal convergence rule already used by Schur.

An independent SciPy solve of the original equality/height matrix with exactly the primal backend's multipliers removed only **0.049 µm** of this difference. The remaining **3.625 µm** came from the multipliers. Recovery alone was therefore rejected as the fix. Full recovered residuals passed; that fact alone could not certify displacement accuracy.

Using the Paseo Advisor skill, one actual **Claude Opus 5.5 / high** advisor recommended this discriminator first, then the existing Schur internal `1e-18` complementarity rule if multiplier error remained. The advisor also rejected more inverse-response kernel work as sufficient to reach 2 ms. Its reports distinguish measurements from estimates; the latter are not performance evidence.

`--primal-parity` now uses that existing internal rule and recovers the accepted multipliers through the original coupled band/equality/height factor. The final certificate preserves the original ordered contact arithmetic, repeated references, physical equalities, stationarity, all contact gaps, complementarity and multiplier signs. Source contacts remain complete, and the admission layer still checks every original source row. Regularization stays `1e-8`, refinement stays at most three corrections with the existing scaled `1e-12` residual criterion, and the 50-iteration/20-admission caps remain unchanged. The original experimental primal backend remains the default.

The corrected replay agrees with the Schur reference within **0.029660 µm**. A separate sparse active-KKT solve, using 710 active contacts and then checking all 2,123 original rows, agrees within **0.001692 µm**. It has nonnegative forces and all-row gap at least −5.68e−19 m. Native full-matrix stationarity is about 2e−22, regularized equality about 4e−20 and complementarity 4.55e−20. No tolerance was tuned to make the comparison pass.

## Cost experiments and stop decisions

The batch-response instrumentation checkpoint is bit-identical to the prior batch result. Its 315.037 ms cold cost includes 191.775 ms responses, 5.317 ms compliance and 32.817 ms Newton factors. The response batch contains 73.213 ms band solves, 27.410 ms border work and 57.586 ms residual work; the 43.513 ms original-product time is a subset of residual work. This distributed cost ruled out a band-kernel-only successor.

The subsequent primal stage profiler **failed its fixed bit-identity condition**: about 6.71e−18 m difference from the earlier accurate result and 5.85e−18 m from a same-source unprofiled control. Both numerical comparisons pass, but the timing breakdown is rejected and cannot rank the next optimization stages. Its 148.151 ms total is retained as rejected evidence. There was no further profiler expansion.

One bounded symbolic-ordering successor instead tested the independently observed graph structure: nonlocal contacts involve rope-end variables, while height connects broadly. `--end-cluster-order` eliminates interior variables first, retaining all 132 nonlocal working variable indices and height until last. It changes only the symbolic permutation of the same CSC matrix. Numeric factorization still uses Apple's default scaling and pivot/zero tolerances, threshold pivoting, unchanged numeric refactorization and original-matrix refinement. Apple's installed SDK documents the reference-counted symbolic factor lifetime used by this branch.

| Same-source cold pair | Default ordering | End-cluster ordering |
| --- | ---: | ---: |
| Cold QP and full source checks | 137.444 ms | 114.859 ms |
| Symbolic factor storage | 691,276 bytes | 3,197,308 bytes |
| Newton dimension / stored lower entries | 5,707 / 14,864 | 5,707 / 14,864 |
| Iterations / working rows / admissions | 15 / 836 / 1 | 15 / 836 / 1 |

The pair's compiled source hashes match after normalizing generated snapshot paths. Factor storage grew **4.63×**, and the cold gate failed. This ordering approach is closed; it remains opt-in to reproduce the rejected experiment. The variation between the first 48.582 ms accurate run and later 137.444 ms default-order control prevents claiming stable latency or a reliable ordering speedup. No 50-run expansion, new factor kernel, trajectory or app adoption follows these failed screens.

## Original geometry and physical limits

A freshly compiled, workspace-owned original triangle checker evaluated both the accurate primal result and ordering pilot. Each has **2,858 signed point/full-link queries**, minimum clearance **3.603605 mm**, radius margin **103.605 µm**, zero swept wood collision blocks and **16.070 µm** maximum primal difference from the retained facet correction. Strict 50 µm and isolated 100 µm wood-clearance diagnostics pass.

Both still have **16.798447% maximum local strain and 1.578428 mm total material-length error**. They fail final physical acceptance and are not complete nonlinear timesteps. General channel eligibility, topology, nonlinear self/intercord clearance, complete CCD acceptance, healthy/jug verification timing, complete geometry speed, trajectory stability and iPhone performance remain unproved. No app acceptance gate is green from this work.

## Verification, review and ownership

A soft clear-wall regression was observed RED at complementarity 6.25e−17 against the existing internal 1e−18 requirement, then GREEN with convergence/recovery parity. Final native parity/order/profile fixture execution: **24 passed**. Default backend: **22 passed, 2 explicitly skipped parity-only cases**. Global batch/BLAS/profile backend: **24 passed, 1 explicitly skipped primal-only case**. The original ordered-gap cancellation fixture now also exercises primal recovery and contains repeated variable references.

Full Python prototype suite: **61 passed, 3 failed**, the same absent historical solver cases (`test_rope_settles_around_outside_of_round_bar`, `test_wrong_wrap_topology_is_rejected`, `test_fresh_simulations_are_repeatable`). The earlier wrong-interpreter attempt failed collection because numpy/pxr were absent; the corrected owned-venv run is authoritative. No historical binary was restored or executed. The intentionally failing untracked catalog inventory test was untouched.

One scoped read-only review found no Critical or Important issue. Both Minor findings were addressed: dimensions/nonzeros/storage/last iterations are gauges rather than admission sums, cumulative timing snapshots are labelled, and the ordered-arithmetic fixture is available to primal parity. Declined-to-judge rulings: primary accepts numerical/test/mesh facts only from directly completed logs; pending benchmarks were subsequently completed; general convergence/device/adoption and historical inventory work remain outside this checkpoint, with no claim that they passed.

All evidence is retained under `.context/strong-owl-live-physics-response-diagnosis`; the companion summary hashes captured compiled sources, labelled replay results, rejected runs, advisor reports, original-mesh checks and cleanup receipts. The exact Opus advisor was archived and verified closed; its owned EXIT guard exited. Compiler/probe groups and drivers were cleaned and their exact absences verified. No server, simulator or device installation was started, and no historical/shared resources were touched.

The task remains active and unfinished. The accurate primal formulation is a useful experimental baseline; neither further symbolic-order tweaking nor the rejected profiler establishes a viable live backend. The next performance discriminator must establish dependable cost attribution before another kernel, while retaining the independent displacement comparison and full original-matrix/mesh checks.
