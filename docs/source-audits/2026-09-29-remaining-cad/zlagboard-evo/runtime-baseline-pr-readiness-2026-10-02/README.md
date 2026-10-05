# Evo baseline workout observation — 2026-10-02

The unchanged baseline app reproduced the workout defect in landscape: bilateral 20 mm pockets were red during the first active hang, blue during rest, and incorrectly still blue during the next active hang at 00:06. The existing `research.max-hangs` routine was unchanged. This is a failed workflow check, not a renderer fix or new human acceptance; prior geometry acceptance remains unchanged.

[The local record](baseline-workflow.json) identifies all three whole screenshots and their exact SHA-256 hashes. Raw screenshots, AX, command streams, build/package/executable provenance and startup evidence are retained once in the [shared baseline Pro appendix](../../zlagboard-pro/runtime-baseline-pr-readiness-2026-10-02/README.md). Its [Evo visual review](../../zlagboard-pro/runtime-baseline-pr-readiness-2026-10-02/ios/baseline-evo-workout-landscape/visual-review.json) records the failure. Earlier Evo failure packets are unchanged.
