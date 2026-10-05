# Invalid prestart-hand suppression action

This action produced **zero qualified workout-phase captures** within its 300-second capture bound. It cannot establish displayed colors, suppression correctness, or a production fix. The original findings, checker failure/not-evaluable result, protocol, command timings, complete 152-record trace, and initial image remain exact.

The same diagnostic binary was used as the preceding control (`f98a07f4383af14396d8442581a330f4d3523d0c9854436420b67bf14b681d97`). Prelaunch/final code and package parity passed; the external readiness check passed. Neither supplies the missing phase captures. The original amended timing checker was not run because its required actual phase evidence was absent.

## Additive interpretation correction

The separate `raw/prestart-hand-action-timeline-correction.json` qualifies the historical report without rewriting it. The pair constructor occurred about 20.139 seconds after the pre-autostart marker, not immediately afterward. The same workout scene later received selected preview, active, then preview CPU inputs/material updates. This is compatible with a workout advancing past an uncaptured initial interval; absence of a recorded positive countdown does not establish that the workout remained unstarted. The child environment predicate at construction was not recorded.

The action's initial screenshot command took about 11.093 seconds, versus 0.477 seconds in the control. That duration and the trace gap do not identify a blocked thread, GPU behavior, scheduling mechanism, or cause. The only whole image is the early Train screen; it establishes no later workout display state. The capture eligibility failure remains invalid for visual comparison.

`analysis/prestart-suppression-source-audit` is a separately hash-bound read-only source assessment. The nil-only predicate ends when the future initial countdown is armed; a coherent positive-countdown render independently excludes hands. A future-initial-deadline guard is discussed only as a semantic possibility, not a selected patch or explanation of this action. Existing startup branches and sparse callback limitations are explicitly qualified.

## Retention and scope

The original 44-file freeze is copied with its original manifest. The additive timing correction and source audit are separately listed in `retention-manifest.json`; `retained-files.sha256.json` binds every retained packet file except itself. Source path mappings remain explicit. Exact shared build/source provenance remains in the preceding [control packet](../runtime-prestart-hand-control-2026-10-02/README.md); this packet does not duplicate an app bundle.

The exact attempted app PID 84460 was terminated and verified absent. The workspace-owned Simulator/DerivedData remained under the root controller for subsequent authorized work; no resource cleanup is claimed here. The separately authorized unchanged repeat is outside this packet and has no outcome here. No native package, acceptance, queue, production source, or prior evidence was changed by this packaging task. Raw log/patch whitespace is preserved; only the new editorial README/index is checked for trailing whitespace.
