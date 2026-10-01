# Isolated U-channel contact representation: rejected speed checkpoint

User authorized trying the Opus channel-core proposal on `feat/live-hangboard-physics`, based on `cd5232156`. This is an experimental tool change only. Existing app physics, seated cords, geometry assets and the accepted CAD PR are unchanged.

The fixed production checkpoint went from **119,953 contact source rows to 2,123** (56.5× fewer), but the native cold global-Schur Mehrotra solve took **433.150 ms**, failing the unchanged **2 ms** gate. Building response/compliance took **319.340 ms**; the contact Newton factorizations took **30.829 ms**. There were **836 working responses**, 21 Newton factorizations and one admission with no added rows. Fewer source rows did not produce a fast working system. This line stops before nonlinear trajectory expansion, general region certification, device benchmarking or product adoption.

## Representation and fixed inputs

The exploratory concentration test placed 119,747 of the 119,953 original contact supports inside two U-shaped channels. This was geometric classification, not a facet provenance certificate. The trial replaces selected one-particle wall rows and whole-link wall rows with point-to-core inequalities. It retains the original equality constraints and all other frozen state verbatim, every self/intercord row (172), and original mouth/portal-crossing rows. The retained and removed original row IDs partition the original rows.

Channels use the retained analytic patches 13–14: core bend radius 6 mm, wall tube radius 3.7 mm, centres (±63, 24, 33) mm. Rope radius remains 3.5 mm. The original 0.1 mm clearance must also be subtracted: available radial motion is 0.1 mm before the patch envelope and link allowance, rather than the advisor's initial 0.2 mm. The lower semicircle joins two straight legs continuously, allowing axial sliding. On-core points have no arbitrary contact normal. Long/invalid links and supports outside the candidate domain keep original rows. The mouth domain ends 0.2 mm before the real portal plane at z = 66 mm.

The chord restriction includes endpoint offsets and the existing 0.5% strain limit. Each incident endpoint receives the maximum link allowance, plus the retained wall-envelope bounds (11.061 and 16.319 µm). This is ordinary floating-point proposal arithmetic, **not** a directed region proof. Complete wall-ring coverage, foreign-wood separation, sign and general swept acceptance remain unproved. Every proposed correction therefore requires the original mesh checks. The authorised 0.10 mm experiment does not change the app's 0.05 mm physical limits.

The summary JSON binds the following exact retained inputs and all final evidence with SHA-256:

- `.context/strong-owl-live-physics-execution/mini-production-frozen/frozen-qp.json`
- `.context/strong-owl-live-physics-parametric-tiles/proof-hundred-micrometre-first/tiles.json`
- `.context/strong-owl-live-physics-handoff/mini-seven-mm/candidate.physics.json`
- `.context/strong-owl-live-physics-native-contact/replay-global-schur-reviewed-production/replay.json`

## Results and limits

Authoritative final evidence is `.context/strong-owl-live-physics-channel-screen/checkpoint-reviewed-production`. The offline Python builder took 31.672 ms and scanned the already generated frozen rows; it does **not** measure native geometry generation. It removed 118,508 original rows and added 678 tube rows, with 676 eligible whole links. Candidate contact count passed the fixed ≤3,000 screen.

The native clock covers cold equality construction/factorisation, row construction/discovery, solve and full affine numerical validation. Frozen JSON decoding, geometry generation and mesh verification are excluded. It used unchanged caps, regularisation and residual tolerances, exactly one cold run. It reports no p95, 50-run, iPhone or real-time result. The previous facet control's 158 responses and 208.762 ms were measured on earlier sources and are contextual, not a paired speed comparison. The candidate's larger working set is a measured consequence of this representation.

Independent checks on the **new** matrix passed: stationarity 2.0870e−22, regularised equality 6.6093e−20, complementarity 8.4518e−19, all-row violation 6.0611e−16, zero dual/slack violation. A separate SciPy sparse active-KKT oracle agreed within **0.031351 µm** (710 oracle-active rows). Its force threshold selects the oracle active set only; full residual checking still includes every new row. The candidate also passed all original frozen affine inequalities with minimum gap 4.1989e−13 m. This is a fixed-candidate diagnostic, not a nonlinear-to-old-affine certificate.

The original signed triangle collider checked every point and complete link, **2,858 queries** per correction:

| Fixed correction | Minimum clearance | Margin above 3.5 mm rope radius | Original wood sweep blocks | Maximum local strain | Maximum material-length error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Channel candidate | 3.603605 mm | 103.605 µm | 0 | 16.798447% | 1.578431 mm |
| Original-facet control | 3.603182 mm | 103.182 µm | 0 | 16.798447% | 1.577961 mm |

The maximum primal component difference from the retained facet correction was **16.073 µm**, passing the fixed ≤100 µm comparison. Both wood-clearance flags (50 µm and isolated 100 µm) passed. **Neither correction is an accepted nonlinear frame:** strain and length are above the final physical gates. No settled trajectory, bearing/topology, nonlinear self/intercord or general CCD acceptance is claimed. Verification time was not screened against the ≤1 ms healthy/jug gate. Complete geometry still needs 50× speedup, and eventual simulation plus cord mesh still needs iPhone 16 Pro p95 <4 ms.

The first checkpoint exposed a post-main-update native compile dependency on `RopeContactWorkingSet`. The native launcher now captures that exact authoritative declaration from `RopeDynamicsSolver.swift`, retains its full source hash, and compiles it in the tool snapshot. The subsequent pre-review run took 457.659 ms (322.692 ms response/compliance); it remains retained. The final reviewed run above is authoritative. No numerical tuning occurred between these runs.

## Verification, review and ownership

Nine new physical row/domain tests were observed failing against the unimplemented API and then passing. One scoped final code review found no Critical issue and two Important runner issues: a nested-process cleanup race and mutable evidence references. Both received observed failing regression tests and one fix pass. The native checkpoint now shares the coordinator process and refuses pre-existing native labels; complete native source/log/JSON evidence is copied with relocated snapshot references. The final full Python prototype suite reports **61 passed, 3 failed**. The three failures require the absent historical `.context/frantic-kiwi/rope-build/rope_solver`; they are not green acceptance gates and no old binary was restored or executed. Native global-Schur fixtures passed **20/20**, default native fixtures **19/19**.

Ruling: discriminate row-count/cold-QP viability before spending on general region certification. Original-mesh checks are authoritative for the single retained correction. Cost if wrong: rejecting the isolated prototype, with no app change. Minor review item deferred: the physical checker command does not distinguish failed physical flags from an otherwise completed nongreen performance screen in its exit status. JSON explicitly reports those flags; every completed experiment returns nongreen status 3 and cannot become a green product gate.

All new child/driver resources were immediately registered and cleaned by their owning coordinator/EXIT traps; absence was independently verified. The first full pytest suite used its framework-default external `pytest-437` base, which lacked the owner name. Its exact ownership was proved by the retained suite log, registered, and only that exact new directory was deleted and verified absent. Subsequent launcher tests force a workspace-owned `.context` basetemp. Shared/historical pytest roots, copied lifecycle records and historical binaries were left alone. Immutable cleanup receipts accompany the summary hashes. No server or simulator was started.

The measured next cost target is globally coupled response/compliance construction. This failed experiment does not justify dropping coupling, changing the physical tolerances, raising solver caps or adopting the unproved channel domain.
