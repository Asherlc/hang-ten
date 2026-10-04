# Post-Main workout presentation and first-start repair

Workout contacts could remain red during Rest or blue during the following Hang in the iOS Simulator, even after the application updated the selected materials. The first Hang could also begin before the board or hands were available. This candidate extends Main’s existing Simulator drawable-presentation policy to display-only board hosts and both hand hosts, and waits for the current mounted board/hand synchronization before arming the existing initial countdown. It keeps that initial hand host mounted, visually hidden during countdown, and retires preparation reporting when countdown starts. Preparation can be canceled; stale or superseded readiness cannot restart it. Readiness is a CPU setup/synchronization milestone, not proof of a GPU-presented frame.

The production candidate retains the live RealityView hosts, authored hand poses, finger materials, orthographic hand camera, orbit/zoom, board interactions, per-hand task/cursor behavior, and Main live-physics rendering. The disabled BoardFrame experiment and its four experimental cache tests are removed. Simulator presentation configuration uses the existing public CAMetalLayer policy only on a unique matching drawable; unrelated or ambiguous layers are left untouched. No temporary per-tick probe, camera nudge, or diagnostic presentation switch remains in this candidate. The canonical six native packages and all human review records are byte-preserved.

## Fresh validation

The source frozen in [raw/clean-candidate-source-reference.json](raw/clean-candidate-source-reference.json) produced installed Debug dylib SHA-256 `97f7f90cc61f594cb75c4fe17e68dade07ffa90173cad7d3b3b986944fd69453`. Source, built, and installed package/Mach-O parity passed all 22 checks before and after each full workflow. This is after Main merge `a314f39c03121465b493da6f45e49fa7c928b1cc`, containing Main `d53c019c43319a70b32e6dc654814de29e87ab89`.

- **Evo:** [58 individually reviewed whole images](raw/clean-evo-whole-visual-review.json). First Hang red, first Rest blue, following Hang after the natural 180-second Rest red, following Rest blue, with both hands and legible wood geometry throughout all Hang/Rest captures.
- **Pro:** [58 individually reviewed whole images](raw/clean-pro-whole-visual-review.json), same binary and passive normal route; the same full color/hand sequence passes.
- **Portrait, audio enabled:** [25-image startup smoke](raw/clean-portrait-audio-whole-visual-review.json). This verifies visible startup and first Hang/Rest behavior; it does not capture or certify spoken countdown output or a long-Rest transition.
- **Tests:** 86 readiness, actual hosted-view preference, drawable-isolation, and workout timeline tests pass; another 47 workout session/state/audio-policy tests pass. Exact result bundles are archived with member hashes before deletion. Red readiness tests and the initially failing real-host propagation test remain retained separately.

These captures use the normal Train→workout deep link, default live orthographic hands, no route unmount or camera override, natural Main timing, and no AX/taps/Skip after entry. The full landscape runs use muted audio. The fixed external screenshot deadlines establish observation times, not exact application phase-mutation times; no CPU brackets or continuous-frame guarantee is inferred. The Simulator-only drawable policy makes no physical-device claim; no iPhone is available. The earlier full-suite Main live-physics pause timeout remains unresolved and is not represented as a passing full suite.

## Evidence and ownership

Every earlier post-Main failure, invalid trial, startup stall, source-timing qualification, and raw `PENDING_WHOLE_IMAGE_REVIEW` status remains unchanged in `raw/`. Separate whole-image reports provide the visual verdicts. The candidate’s success does not retroactively turn the earlier board-only or hand-policy comparisons into passes, and does not establish RealityKit’s internal cause. [Final validation summary](raw/final-validation-summary.json), [native/package preservation audit](raw/final-preservation-audit.json), and [independent source review](raw/readiness-clean-final-source-review.json) bind their exact inputs.

The workspace owns boards #16–21 only. The exact owned Simulator `E0AC7F37-369F-414E-B407-353435A0BE03`, DerivedData, and result-bundle paths were deleted and independently verified absent; manifests were consumed. [Cleanup proof](raw/ios/independent-final-cleanup.json) is retained. The workspace and agents remain available. Parent-owned tests/geometric helper and all out-of-scope packages are unchanged. No parent/Main integration or new human board acceptance is implied.

## Review #20

[First Hang](raw/clean-evo/elapsed-006s.png) · [Rest preview](raw/clean-evo/elapsed-015s.png) · [Following Hang](raw/clean-evo/elapsed-195s.png).

The native shape is unchanged from the retained [original/native front-side-top comparison](../individual-review-2026-10-01/comparison-final/comparison-front-side-top.png). Runtime review of #20 remains pending the user’s reply. #21 is prepared, and will be presented for human review after #20.
