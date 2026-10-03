# Exact evaluation and authorized convergence screens

The app remains on its accepted solver at baseline `886067b15`. These are native experiments; seated cords and catalog enablement are unchanged. The user authorized an isolated physical convergence experiment, with original physical gates, 1/240-second steps, normal-speed video and stability checks required before adoption. None establishes a real-time device result.

The fused evaluator performs one parity query per particle and one triangle traversal per link per distinct configuration. It retains separate original radius-specific candidate sets, arithmetic, facet/witness ordering and manifold merging for point, row and merit outputs. Geometry is memoized only on exact position/height/orientation/topology keys; objective/violation additionally require exact prediction, mass and weight keys. Penalty changes reuse those components, not the resulting merit score. Inside endpoints use the original queries.

934 original, inside, boundary, degenerate and crossing queries passed bit comparison, including a large parallel batch. Seven alternating complete-step pairs retained byte-identical physical checkpoints, cache invalidation and rollback guards. Serial fusion's median ratio was 0.6333; four-chunk parallel fusion's was 0.5664. Missing contacts, flipped inside signs and stale changed-prediction scores were rejected. Query reductions remain ordered after workers join; initialized buffer slots have disjoint ownership.

Per-segment previous accepted clearance improves the unchanged Lipschitz CCD skip. Twenty steps retained original physical checkpoints byte for byte and independently exact cached clearances. Later receipts keep raw row distances before manifold merging; no-hit rows certify a radius lower bound. Final queries are omitted only when that bound cannot reduce either the exact known global clearance or its radius-relative margin. Both reported minima therefore remain exact; cached far-link values are explicitly conservative lower bounds. Inside/unresolved cases retain original distance queries. Twenty paired steps retained private physical checkpoints byte for byte and independently conservative cached bounds. Parallel original swept queries passed the same 20-step check. Transaction copies and invalid-dt rollback preserve the caches.

Negative contact multipliers are only fresh-factor starting hints. All geometry, factors, responses, tensile release, regularized KKT fallback and full inactive separation are rebuilt or checked. Twenty propagated same-input pairs stayed within the fixed 1 micrometre comparator (maximum 0.1992 micrometres). Initial compile/capture failures remain under the evidence roots; corrected builds, not failed builds, supplied measurements.

The first 50 micrometre convergence screen used the line-search-scaled movement and failed at step 20: 132.158 micrometres from a converged original reference. It is closed. Using the full undamped QP correction instead passed all 540 fixed turn/return steps: maximum sampled converged-reference difference 13.712 micrometres, original physical gates passed. This did not guarantee force convergence: two steps hit the existing 80-correction cap, and terminal speed remained noisy. Combined exact speedups retain those physical checks but do not yet meet the 4 ms device target. The recorded distributions and caps are in the JSON audit. A first-feasible motion stop with a speed-derived destination stop failed at step 20 (1.161 mm reference difference); that successor is also closed.

Reproduction (each label must be new):

```sh
rtk proxy python3 Tools/HangboardRopePrototype/run_live_query_identity.py --label fresh-queries --receipts
rtk proxy python3 Tools/HangboardRopePrototype/run_live_speed_screen.py --label fresh-fused --kind fused
rtk proxy python3 Tools/HangboardRopePrototype/run_live_speed_screen.py --label fresh-parallel --kind parallel
rtk proxy python3 Tools/HangboardRopePrototype/run_live_speed_screen.py --label fresh-cache --kind cache
rtk proxy python3 Tools/HangboardRopePrototype/run_live_speed_screen.py --label fresh-receipts --kind receipts
rtk proxy python3 Tools/HangboardRopePrototype/run_live_speed_screen.py --label fresh-hints --kind hints
rtk proxy python3 Tools/HangboardRopePrototype/run_live_speed_screen.py --label fresh-trajectory --kind convergence --parallel-sweep
```

Runners rebuild the pinned accepted Swift source via read-only Git access, hash inputs and generated snapshots, and own/reap exact process groups on all exits. Historical binaries are not executed. Runtime checkpoints and the descriptor are retained inputs; the generated caches do not pretend to be serialized in the original physical checkpoint. HTTP servers and simulators were not created for these screens. The Opus advisor was archived and exact closed/archived status verified after reaching its session limit. The untracked failing catalog-inventory test remains outside acceptance and commits.
