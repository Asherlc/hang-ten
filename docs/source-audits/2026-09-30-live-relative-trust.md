# Live correction trust at production resolution

The shortest-link absolute trust bound limited a rigid translation even though
translation preserves material lengths. It also let an unrelated tiny link
throttle another physical loop. The replacement bounds each link's relative
applied endpoint displacement by 0.1 times that link's immutable rest length.
Fixed supports contribute zero motion; board attachments contribute the solved
world vertical height displacement. This changes the initial Newton trial
fraction, never the inertial objective, Hessian, constraints or acceptance.

The simultaneous material/height/contact solve, complete inactive affine
separation, nonlinear global merit, passage refresh, exact triangle clearance,
finite-radius self/inter-cord contact, CCD and transactional retries/rollback
remain unchanged. Material count and radii remain at production settings.
The historical coarse RelativeTrustSolver is not adopted: its other solver,
margin and sampling settings remain historical evidence only.

Five hand-checked behavioral cases failed against the extracted former bound
and pass against the new bound. A focused independent review found no must-fix
issues; its additional Euclidean diagonal/transverse-motion case passes too.
The fresh full host physics suite passed 71 tests (five new cases included),
covering KKT oracles, sliding material, physical reversals, convergence,
determinism/half timestep, wood/self/inter-cord CCD and rollback. The sixth new
case was compiled and run separately after review; the full suite was not
needlessly repeated for this test-only addition.

The unchanged fixed Clavellium corpus is upright, 90 degrees, 180 degrees,
upright, 90 degrees, upright, with dt 1/240 and a maximum 1,200 steps per
transition. Every accepted frame retains all 280 material particles, identical
rest lengths and geometryAccepted. Each settled destination also checks the
computed expected upper aperture bearing within 0.2 mm and actual surface gap
at most radius + 0.3 mm. Both full-resolution baseline and candidate completed
all six transitions (123/297/297/476/297/297 steps).

| Phase | Baseline host p95 ms | Candidate host p95 ms |
| --- | ---: | ---: |
| upright | 408.285 | 156.135 |
| 90 degrees | 477.607 | 135.429 |
| 180 degrees | 473.887 | 191.825 |
| upright return | 216.706 | 229.736 |
| 90 degrees repeat | 182.606 | 339.918 |
| upright repeat | 191.910 | 969.161 |

These host runs share a machine with other workspaces. The candidate's maximum
step was 7.228 seconds. The variation and mixed results do not establish a
performance improvement; no device/mesh-update measurement or 4 ms claim is
made. The change corrects the trust rule's resolution dependence, and does not
close the geometry/contact architecture gap. All seated cords remain available;
no new board/profile is live enabled by this change. Native CAD error bounds,
shared settled-bearing certification, physical-device performance and the
remaining live catalog gates are still outstanding.

Source snapshots, exact commands, binaries, full ordered frames and logs are
retained under `.context/strong-owl-live-physics-execution/`. The linked JSON
summary binds source and evidence hashes. Its frames are host numerical
evidence, not native visual review or a continuous CAD accuracy certificate.

[Machine-readable evidence](2026-09-30-live-relative-trust-summary.json).
