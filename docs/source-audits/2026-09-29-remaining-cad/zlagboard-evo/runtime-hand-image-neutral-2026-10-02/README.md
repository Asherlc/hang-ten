The on-demand hand-image prototype now produces upright, readable paired half-crimp cues on cream and black backings. This is a bounded static feasibility result with a declared neutral-lighting appearance adaptation. It is not visually equivalent to the live renderer, workout validation, a production fix, or new human acceptance.

| Retained run | Technical result | Whole-image judgment |
| --- | --- | --- |
| Orientation-only image-c | Pass | Upright, but near-black regions obscure finger detail: visual failure retained. |
| Fixed neutral image-d | Pass | Upright, four selected red fingers readable on each hand; darker/warmer shading than live-d. |
| Same neutral image on dark backing-e | Pass | Readable cues and no apparent opaque rectangular backing. Generated PNG bytes equal cream-d output. |

Compare the complete [live-d screen](raw/hand-image-static-live-d/whole-app.png), [neutral cream screen](raw/hand-image-static-image-d/whole-app.png), [neutral dark screen](raw/hand-image-static-image-dark-e/whole-app.png), and [historical orientation-only failure](raw/hand-image-static-image-c/whole-app.png). Exact generated PNGs and every published revision are retained with hashes; no image crops, pixel measurements, registration, or color sampling were used.

The fixed vertical conversion normalizes the Metal output into an upright CGImage/PNG. A subsequent, separately tested adaptation supplies an analytic constant white environment through the public iOS18 EnvironmentResource initializer at intensity exponent0. Existing mesh, custom material, authored lights, camera and color pipeline are preserved. This does not reconstruct Apple's unspecified system lighting or establish the sole cause of the earlier dark output. The independent primary-source color audit did not establish duplicate gamma decoding and recommended no color correction.

The [independent cream findings](analysis/hand-image-neutral-review/findings.json), [additive dark findings](analysis/hand-image-neutral-review/dark-backing-findings.json), and [aggregate](analysis/hand-image-neutral-review/aggregate-findings.json) preserve distinct judgments. The original cream report remains immutable. The dark diagnostic's black text lacks contrast; that backing is a composition test, not a proposed app theme.

Raw build, application, source snapshots, helper versions7–9, release records, installed/build/package parity, complete JSONL, PNGs and exact app cleanup are under `raw/` and `analysis/`. Each app PID was verified absent; existing Simulator/DerivedData remain owned by the workspace root controller for continuing work. No app bundle is duplicated here. The source files stored inside this docs packet are diagnostic evidence, not a production source change.

[Earlier setup, inverted-output failures and versions1–6](../runtime-hand-image-static-2026-10-02/README.md) remain in the unchanged prior packet committed at f19fccc8c. `retention-manifest.json` records exact historical references, source-to-copy hashes, and scratch-only full Apple documentation exclusions. Public API conclusions and URLs are retained; full copyrighted documentation is not republished.

Actual workout-size cues, active/rest board transitions, other hand poses, single-hand rendering, rapid revisions, gesture/reset behavior and sustained energy cost remain unvalidated. A separate bounded workout comparison is the next evidence boundary; this packet authorizes no runtime actions and makes no repair claim.
