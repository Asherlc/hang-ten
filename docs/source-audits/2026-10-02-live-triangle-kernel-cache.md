# Immutable triangle kernel cache: closed

This isolated experiment caches triangle edges and the fixed parity ray's cross product, determinant and inverse. It retains the original Double narrowphase arithmetic, BVH, contact candidates and manifold order. App source at 597333b47 is unchanged. The incidental cached normal does not reopen the earlier normal-only or packed-layout experiment.

The registered checkpoints passed all 934 contact queries and 2,802 swept witnesses/TOI bit for bit, including the RED controls. Twenty paired strict steps retained physical checkpoint identity, independently checked clearance lower bounds and invalid-step rollback. These strict comparisons use the pinned original solver, so their timing difference includes already adopted app optimizations and is not evidence of this cache's performance.

The decisive comparison rebuilt independent current-source control types in the same binary. Both solvers propagated the same actual upright-to-30-degree trajectory through 139 steps; every complete physical checkpoint and correction/cap/retry schedule matched. Seven alternating copies then measured complete step 140, with two corrections, zero caps and zero retries. The median candidate/control ratio was **0.935111**, failing the pre-registered maximum **0.80**. One control run was a timing outlier; all seven pairs remain in the report. No expanded runs, changed fixtures or gate tuning followed.

The line is closed, unadopted. This saves about 6.5% on this host checkpoint and does not establish real-time app or iPhone performance. The current simulator recording's timing failure remains unchanged. Compile/run process groups were owned, reaped and verified absent.

Retained evidence:

- `.context/strong-owl-live-physics-triangle-kernel-cache/PLAN.md`
- `.context/strong-owl-live-physics-current-cached-kernel-queries/native/run.log`
- `.context/strong-owl-live-physics-current-cached-kernel-strict/native/result.json`
- `.context/strong-owl-live-physics-cached-kernel-complete-step/native/result.json`
- The adjacent provenance and resources manifests retain source hashes and exact cleanup records.

The next permitted step is a current-source complete-step cost split. The suggested previous-factor preconditioner was ruled out before implementation: even eliminating both factorizations would save approximately 0.27 ms in the detailed retained profile, below the roughly 1.04 ms required by the complete-step 20% discriminator, before residual/refinement costs. No new factor-reuse implementation or performance claim follows from that inference.
