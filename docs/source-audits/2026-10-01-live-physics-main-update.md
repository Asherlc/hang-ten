# Live physics branch update from main

The user requested updating `feat/live-hangboard-physics` with main while
retrying a screen recording. The source update combines branch HEAD
`34277172440614be9b698e26afc42ea81ad09d61` with main
`d8f23d28c` and retains the existing experiments and runtime trust calculation.
It does not promote an experimental contact backend or another live board.

Main contains the accepted PR #529 as a squash, followed by review fixes.
Using the original ancestry as a content base produced dozens of duplicate
add/add conflicts. The content merge instead uses its frozen accepted source,
`52c3595b5`, with `git merge-tree --write-tree --merge-base=52c3595b5`.
The merge commit retains the actual branch HEAD and main as its parents.
An independent path comparison confirms that all 71 differences from main,
before this audit, are paths already changed by the live physics branch.
The original workspace and branch were not edited.

Two content conflicts required combining changes:

- `LiveRopeMesh.swift` retains main's capacity for the new end-cap vertices
  and the branch's cached ring sine/cosine values.
- `RopeDynamicsSolverTests.swift` retains all six relative-displacement trust
  tests and main's rollback, cancellation and invalid-duration tests.

The solver merge also retains main's bounded topology recovery and cancellation
handling. Physical diameters, material lengths, sliding passages, coupled
degrees of freedom, collision acceptance and transactional rollback remain
required. The isolated 0.10 mm experiment authorization does not change app
physics limits. Seated cords remain available.

## Verification and limits

Evidence is under `.context/strong-owl-live-physics-main-update` and
`.context/strong-owl-live-physics-screen-recording/2026-10-01-retry`.

- Signed Debug build succeeded on an owned iPhone 16 Pro / iOS 26.5 simulator.
- Six merged trust tests passed against captured current Swift sources in an
  optimized native XCTest executable.
- Python prototype suite: 50 passed, three deselected legacy tests requiring
  the absent historical `frantic-kiwi/rope-build/rope_solver`. The intentionally
  failing untracked live catalog inventory test remains untouched.
- Package physics, exterior-rope and rectangular-channel suites: 59 passed
  with the missing geometry test dependencies installed in the existing
  workspace-owned virtual environment. Earlier dependency failures and skips
  are retained separately.
- The iOS run completed 21 passing tests and one failing test before a bounded
  interruption. `testReduceMotionDeliversOnlyAcceptedSettledFrame` exceeded
  its existing 30-second wait and recorded three failed assertions. A subsequent
  asymmetric-material settling test ran for more than four minutes of wall
  time before interruption. The full selected iOS run is incomplete and is
  not a green acceptance gate. No timeout or physical gate was increased.

The remaining live settling performance problem is open. These checks do not
establish complete device-step timing or catalog rollout readiness. Simulator
recordings show the current app; the parametric contact prototype is still
outside it. Every created simulator and child process is recorded under this
workspace's owner and cleaned by the invocation's exit handlers.
