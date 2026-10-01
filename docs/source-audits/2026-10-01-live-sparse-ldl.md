# Sparse scalar contact factor checkpoint; live speed still fails

Base `9fcac4926`, branch `feat/live-hangboard-physics`. This checkpoint adds an opt-in `--sparse-ldl` backend to the isolated native contact tool. It uses the original coupled CSC Newton matrix, including length equalities, board height and nonlocal contacts. Production app sources, seated cords, physical acceptance gates, regularization, refinement and iteration/admission caps are unchanged. The independent displacement comparison remains mandatory.

The corrected same-source cold pair took **48.403 ms** with Apple's default numerical factor and **30.206 ms** with the scalar factor. Both independently pass the original full-matrix residual checks and agree with the separate active-KKT oracle within **1.692 nm**. These are single host observations, without a statistical or device claim. Both fail the immutable **2 ms** cold gate. The current scalar-kernel performance line is stopped; it is not adopted in the app.

## Diagnostic attribution and hypothesis

The previous profiler was rejected under its fixed bit-identity rule. A new bounded discriminator reused the exact same current-task binary without recompiling: two unprofiled runs took 47.761/48.758 ms and differed by 5.53e−18 m. Only after observing that variation did it run one profile (50.691 ms), whose difference was smaller, 4.45e−18 m. All three pass the unchanged original KKT and 1 µm oracle comparison. This establishes that unprofiled backend variability also exists; it does not establish bit identity, statistical reproducibility or runtime readiness. The profile is used only for diagnostic attribution.

That profile put 23.111 ms in numerical refactors and 7.105 ms in solves over 15 iterations. Removing bookkeeping alone therefore could not close the cold gate. The next bounded hypothesis was an original-matrix scalar LDL factor using Apple's existing computed symbolic ordering, while preserving original-matrix refinement and final original-factor recovery.

The implementation uses its own elimination tree, sorted predecessor pattern and left-looking arithmetic. No SuiteSparse code was copied or imported. Real-arithmetic quasi-definite factor existence under symmetric permutations is established by [Vanderbei's paper](https://epubs.siam.org/doi/abs/10.1137/0805005); it is separate from finite-precision stability, as discussed by [Gill, Saunders and Shinnerl](https://web.stanford.edu/group/SOL/papers/sqdSIMAX1996.pdf). This tool does not claim general stability. Invalid dimensions/patterns/permutations, excessive fill, zero rows, nonfinite arithmetic and zero/wrong-sign pivots reject. The existing full original residual and displacement checks remain the acceptance authority.

## Ordering integration error and regression

The first pilot passed numerical checks but took **4.208 seconds**, with 1,566,668 scalar factor entries. It failed the fixed speed stop. A separate symbolic-only integration discriminator, without a numerical scalar solve or IP continuation, found 18,904 entries when the SDK order was inverted. An independent graph elimination later confirmed that count.

A small test against Apple's actual `SparseSubfactorP` operator establishes the direction: for SDK user order `[2,0,3,1]`, multiplying labels `[0,1,2,3]` by P gives `[2,0,3,1]`. The SDK array maps original indices to permuted indices; the scalar factor's gather array maps permuted indices to original indices. A validated inverse adapter now connects them. The conversion fixture was observed RED with a direct-order scaffold, then GREEN with inversion, malformed-input checks and an involution check. The initial failed pilot and its compiled source snapshots are retained.

The same integration error existed in the preceding `--end-cluster-order` experiment. Its retained 137.444/114.859 ms pair did **not** test the intended interior-first elimination order. The earlier conclusion about that intended ordering is withdrawn. The flag now converts the deliberately authored gather order to the SDK direction; there is no new cold end-ordering run or performance claim. The old evidence remains immutable.

## Corrected cold checkpoint and stop

| Diagnostic measurement | Apple factor | Scalar factor |
| --- | ---: | ---: |
| Full cold QP / source checks | 48.403 ms | 30.206 ms |
| Newton dimension / stored lower entries | 5,707 / 14,864 | 5,707 / 14,864 |
| Iterations / admitted rows / admissions | 15 / 836 / 1 | 15 / 836 / 1 |
| First numerical factor | 2.419 ms | included below |
| Numerical refactors | 21.074 ms / 14 | 5.075 ms / 15 |
| Numerical solves | 6.759 ms / 30 | 3.444 ms / 46 |
| Original-matrix refinement solves | 0 | 16 |
| Original CSC residual products | 1.371 ms / 30 | 1.954 ms / 46 |
| CSC pattern construction | 4.080 ms | 4.149 ms |
| Scalar symbolic construction / SDK ordering | — | 2.937 ms |

Original-factor preparation is 0.953 ms and final recovery 0.407 ms in the scalar pilot. Its 25.655 ms IP total includes these nested factor/pattern/solve/product costs; they must not be added twice. The remaining IP bookkeeping has no precise internal cost split. Source hashes, frozen input and oracle hashes match across the corrected pair after generated paths are normalized.

The scalar factor's **5.075 ms numerical refactors alone exceed 2 ms**. The predeclared kernel continuation stop therefore applies, even though it improves this one host observation. No further iteration/cap/tolerance tuning, 50-run expansion, nonlinear trajectory or app adoption follows this checkpoint.

An independent graph elimination on the actual first Newton pattern confirms 18,904 L+D entries, 24,423 left-looking scatter updates per numerical refactor, 13,197 lower entries per triangular solve and maximum lower column length 30. These are arithmetic counts, not latency evidence. They support investigation of implementation overhead but do not establish that a complete cold solve can reach 2 ms.

## Original geometry, tests and limits

Fresh executions of the current-task-owned original triangle checker evaluated both the initial and corrected scalar pilots. Each has 2,858 signed point/whole-link queries, minimum clearance 3.603605 mm, radius margin 103.605 µm, zero swept wood blocks and 16.070 µm maximum difference from the facet correction. Strict and isolated wood-clearance diagnostics pass.

The correction still has **16.798447% maximum local strain and 1.578428 mm material-length error**. It is not an accepted nonlinear timestep. General channel certification, topology, nonlinear self/intercord clearance, complete swept acceptance, healthy/jug verification, full geometry speed, trajectory stability and iPhone performance remain unproved.

Core factor fixtures were first RED with a rejecting scaffold (24 assertion failures), then passed the hand-derived coupled matrices and changed-value refactors. Coverage now includes non-self-inverse ordering, equality/height/nonlocal terms, malformed patterns, zero/wrong-sign pivots, nonfinite inputs and valid → numerical failure → rejected solve → valid recovery. Validation-only rejection preserves the previous valid factor, matching the wrapper contract.

Final reviewed native scalar/parity/profile suite: **28 passed**, exit 0. Corrected SDK end-order branch: **28 passed**, exit 0. Default: **26 passed, 2 explicitly skipped parity-only cases**, exit 0. Global batch/profile: **28 passed, 1 explicitly skipped primal-only case**, exit 0. One intermediate all-28-passing suite nevertheless exited 1 because its expected-count guard remained 27; that failed checkpoint is retained, and the count/lifetime fixes were verified in the final runs.

Full Python prototype suite: **61 passed, 3 failed**, the same absent historical solver cases. No copied historical executable was restored or run, and the intentionally failing untracked catalog inventory test was untouched. Scoped read-only review found the expected-count guard issue (Important) and a permutation-subfactor lifetime issue (Minor); both were fixed and verified. General stability/performance/adoption were outside the review's claim.

One actual Claude Opus 5.5 / high advisor, launched using the [Paseo Advisor skill](/Users/asherlc/.agents/skills/paseo-advisor/SKILL.md), recommended a packed numerical-primitive cost-ceiling discriminator before rebuilding the full IP implementation. Its throughput/architecture estimates are inference, not measured impossibility proofs. The next isolated check will retain operation order, guards and bit-identity comparisons, include workspace first touch, measure both 15-refactor/30-solve/30-product and 15/46/46 schedules, and use a predeclared 1 ms cutoff for continuing the packed implementation. It excludes mandatory full-QP work, so passing cannot establish the 2 ms cold gate.

Evidence lives under `.context/strong-owl-live-physics-sparse-ldl` and `.context/strong-owl-live-physics-same-binary-profile`. The companion summary binds captured sources, RED/rejected checkpoints, paired replays, independent checks, advisor analysis, original-mesh results and current resource receipts. All 34 current compiler/probe groups and 14 drivers were cleaned and verified absent. The exact advisor was archived and its guard exited; shared and historical resources were untouched. No server/simulator/device resource was created. The task remains active and unfinished.
