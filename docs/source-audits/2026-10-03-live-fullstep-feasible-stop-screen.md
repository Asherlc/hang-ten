# Full-step feasible stopping fails pose accuracy at step three

The deliberate revisit failed the 20-step necessary screen at **step 3**: propagated pose error was **115.263059 µm**, above the unchanged 50 µm reference gate. It stopped immediately. No GREEN step-140 timing, full trajectory, simulator or adoption followed.

The candidate required a freshly accepted full step and used the original physical strain .005 and material error .0005 m for nonquiet termination. Actual quiet candidates retained original strain .0002 and raw norm<speed-limit×dt. Original prediction/objective/contact/merit/mesh checks/CCD and actual velocity/history settling were unchanged. Strict same-input comparisons passed the first two steps; step three failed the independent-current gate before its strict reference was run. Feasibility and a full accepted step did not establish force convergence.

Historical first-feasible stopping already had alpha1 on 19 of its first20 terminations, including its failed20. This continuation explicitly retained that adverse evidence. New guards changed propagation but did not provide the required accuracy. Material threshold and quiet-vs-arrival eligibility also differed, so the experiment was never a test attributable solely to alpha1.

Behavioral RED kept the mode inert and failed the one-QP step140 fixture. GREEN implemented only eligibility and failed the registered cheap propagated discriminator. All four new private groups were independently verified absent. Companion JSON binds complete partial result/source/proposal/resource provenance. Product code, assets and seated cords were unchanged. This closes the revisit without threshold tuning or a failed-screen expansion.
