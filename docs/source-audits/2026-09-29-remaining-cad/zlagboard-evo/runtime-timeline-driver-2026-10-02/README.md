# Evo isolated timeline-delivery diagnostics — 2026-10-02

All **60 board-state/color captures passed** across the three isolated A/B/C arms. The actual normal-workout defect remains unresolved. This experiment establishes no production fix, TimelineView repair, new implementation or human acceptance.

| Arm | Isolated state delivery | Board sequence |
| --- | --- | --- |
| A | Task-driven state, no TimelineView | Clear → red → blue → red → blue: passed |
| B | Same task-driven state under a 250 ms TimelineView | Clear → red → blue → red → blue: passed |
| C | Phase derived from monotonic time inside a 250 ms TimelineView | Clear → red → blue → red → blue: passed |

Each phase has four complete screen captures, with no discarded phase. The viewport remains the exact measured **210 × 36 points** used by the previous standalone experiment. Board/presentation and surrounding standalone hierarchy remain fixed. This does not exercise the removed workout, navigation or BoardMap context.

[The frozen report](raw/timeline-abc-findings.json), SHA-256 `effb6b15f59431baf2b78b9448a74b18b6fc06dd8dd944bc8ec7c3745a3b912d`, retains complete traces, requested states, actual mutations, image hashes, capture windows and limitations. Root's image/hash reviews are retained for [A](raw/timeline-a/root-byte-equivalence-review.json), [B](raw/timeline-b/root-byte-equivalence-review.json) and [C](raw/timeline-c/root-byte-equivalence-review.json). All raw commands, captures, stdout/stderr, proposals/applied source and code/package parity remain exact.

## Limits and interpretation

One bounded A/B/C series ran, without repeats. onChange timestamps identify callback execution, not exact body evaluation; actual material mutation may occur first. C's early screenshots were assessed against actual write times. No timing was tuned or failed evidence normalized. The measurement omitted per-tick/body logging, SceneEvents subscriptions, periodic sampling, touch, camera gestures and AX polling, but sparse records and screenshot capture are still diagnostic instrumentation. CPU state alone does not prove display correctness.

The [Astra delivery analysis](analysis/architecture-committee/astra-timeline-delivery-review.txt) and [context-boundary audit](analysis/context-boundary-audit/report.json) are retained analysis, not tested production recommendations. The source excerpts are exact historical context. Earlier failed real-workout and corrected OFF evidence remain in their unchanged appendices. Passing these isolated delivery mechanisms neither erases those failures nor identifies a particular surrounding-context cause.

## Provenance and ownership

[retention-manifest.json](retention-manifest.json) maps every scratch source to its retained path and SHA-256. Embedded absolute scratch paths remain provenance. [The exact three-file snapshot](frozen-source/snapshot.json) and [diff](frozen-source/current-three-file-diff.patch) were frozen against `0586621843817e106d924eb630196aadfb20c62d` before further diagnostic source work; no temporary diagnostic patch is claimed as a production repair.

Canonical CAD, queue/lock and human acceptance records are unchanged. Earlier packet bytes were verified unchanged. The exact registered Simulator and build/result paths remain live under the existing owner controller, pending cleanup; the retained ownership snapshot is not deletion proof. This docs promotion used no source, index, commit or device operations. Subsequent experiments and final cleanup require separate evidence.
