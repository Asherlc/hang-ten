# Late positive-gap contact initialization

The isolated initialization change passed its retained-state discriminator and
native fixtures, but **failed the complete nonlinear step**. It is not adopted in
the app. The measured configuration is closed; the original accepted solver and
seated cords remain available.

At unchanged geometry, the predecessor initialized newly admitted positive-gap
contacts with a 3.5 mm slack, despite actual gaps of roughly 29–50 µm. This injected
artificial contact-equation residual and force. Exact attribution included the
stationarity cross terms and recovered the preceding accepted trial's score.

The new opt-in prototype policy preserves original cold initialization at update
zero and for nonpositive/far gaps. For eligible later contacts it uses
`s=min(coldS,priorMeanSV/scale)` and `v=C+eps*s`. The existing contacts determine one
mean before discovery; every new row uses that mean. `initialS=coldS`, the row scale,
all physical rows, epsilon and final acceptance limits remain unchanged. This gives
zero initial `h` and bounds the new `s*v` by the current mean without increasing the
cold force. It does not guarantee final complementarity or stationarity.

The pre-registered counterfactual check passed updates 12, 13, 15 and 16 of the
immutable predecessor. Scores became 157.300, 164.312, 62.758 and 72.838, each below
the previous iteration-origin score. They can still exceed the preceding accepted
trial's score. These substitutions were independent, not a new trajectory.

The complete retained loaded-Clav checkpoint used the unchanged 16 updates,
16 ordinary trials per update, 1 s work budget and 10 s failsafe, with the existing
full KKT defect policy enabled. Candidate and deterministic replay took 202.618 and
206.163 ms; the original control accepted in 58.122 ms. Timings include native
diagnostics and do not establish device or frame performance.

Both candidates failed the final convergence/certificate cap. Final stationarity
was 1.592e-7, equality 4.435 µm, minimum row residual −92.068 µm, true
complementarity 7.544e-10 and internal complementarity 2.699e-10; last movement was
53.346 µm. Exact whole-checkpoint rollback and deterministic proposal trace passed.
The rejected proposal's independent static mesh check passed: strain 0.2227%,
length error 0.03125 mm, clearance 3.50793 mm and valid topology. This is not an
accepted step or swept collision result. The worst numerical wood row targets
radius plus 0.1 mm; its negative residual does not imply penetration below radius.

Exact reconstruction of the initial corrector fraction identifies the early
restriction: updates 0–8 are limited by relative-link displacement, with updates
1–4 accepting their first ordinary trial at fractions 0.03247, 0.02975, 0.03292 and
0.04505. Later restrictions mix force/slack positivity, trust and merit. Accurate
linear solves and reduced admission jumps did not establish nonlinear convergence.
No further initialization tuning, cap increase or full-step rerun follows.

Behavioral native RED/GREEN tests verify literal force/slack values, immutable
normalization, cold/negative/far fallback and invalid inputs. Astra's targeted
read-only review found no sign/integration blocker and identified a product-underflow
edge case outside the measured magnitudes. After closing the full-step experiment,
a separate RED fixture reproduced that issue; a rejection guard passed GREEN.
The measured complete-step source snapshot predates that guard and remains retained;
no solve was repeated with it.

Evidence: `.context/strong-owl-live-physics-contact-admission/PLAN.md`,
`preflight.json`, `coupled-step/report.json`, `step-analysis.json`, fixture logs and
source snapshots. The paired summary binds evidence hashes and exact process-group
cleanup verification. The intentionally failing untracked inventory test is WIP
and was not run or presented as an acceptance gate.
