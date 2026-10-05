# Current app validation attempt — boards #10–15

**Bounded appearance, representative selections, one real mesh pick per board and ordinary touch views have retained evidence. Fresh app human acceptance remains pending. `appWorkflowPassed = false`.** Historical CAD/human geometry approvals remain intact; no geometry was changed during this attempt.

[Open the one-at-a-time whole-frame gallery](index.html). [Exact resource cleanup verification](cleanup/cleanup-verification.json) is retained separately.

The common workout gate is incomplete: #10 landscape rest preview retains the red work highlight, and its portrait attempt ended at a bounded 40-second accessibility timeout. Workouts for #11–15 were not executed afterward. These failures are retained, not converted into workflow passes.

| Board | App contact coverage | Physical mesh pick | Record |
| --- | --- | --- | --- |
| #10 Stone Hanger Mini | All 4 logical contacts | pull-up-jug | [Record](boards/10.md) |
| #11 Mini × KARMA8A | All 3 logical contacts | granite-edge-15 | [Record](boards/11.md) |
| #12 Owl Poker | Four representative contacts across faces A–D, not all 34 | face-a-left-outer-slot | [Record](boards/12.md) |
| #13 Plateau | One edge, 18→15→10→18 mm variants | edge-18 at 18 mm | [Record](boards/13.md) |
| #14 Flash | All 7 logical contacts; side convention not fully explained | three-edge-left | [Record](boards/14.md) |
| #15 Forge | Ten categories, not all 20 contacts; three upper regions edge-on | sloper-30-left | [Record](boards/15.md) |

[Whole-frame visual audits](visual-audits/) contain the detailed observations and limits. The [image/receipt integrity record](archive-integrity.json) and [installed-app provenance](installed-app-provenance.json) bind the whole frames under `app-captures/` to the installed binary. These are actual app captures; DEBUG-preselected screenshots alone are not counted as physical picks. Each separate pick receipt records an actual mesh tap and tapRevision0→1. Frame visibility does not recertify hidden passage clearance, all intermediate animation states, all contacts or all saved poses.

[Final canonical inputs](final-inputs.json) and each board JSON retain exact source/model/descriptor/sidecar hashes. Accepted geometry scopes and historical human answers are preserved. Only merged-main metadata was restored: Simulator shared round-sloper capacity 2 and Forge's two physical equipment IDs. The [metadata archive](metadata/README.md) retains before/after facts and byte-identical BRep/model preservation proofs; no routine or manufacturer fact was invented.

## Current automated evidence

The [latest final focused rerun](validation/final-strong-summary.json) passed **455 tests, 0 failures and 1 pre-existing skip** (456 total). The [test-only refinement](validation/final-test-refinement.json) adds a fixed-yaw camera-pitch assertion; production code and screenshot binary provenance remain unchanged. [Scoped code review](validation/shared-contact-failure-audit/final-code-review.md) approved the relevant fixes; its nonblocking pitch-test observation was subsequently addressed by that rerun.

The [full opt-in physics attempt](validation/full-attempt-summary.json) did not pass: it hit the owned timeout, with earlier failures and the live-scene settle timeout retained. The focused result is not a whole-suite pass. [Validation archive](validation/README.md) retains command receipts and raw logs; root's final cleanup evidence is separate under `cleanup/`.

## Remaining limits and failed attempts

- [#10 work frame](app-captures/10-workout-landscape-work-highlight.png) and [rest frame](app-captures/10-workout-landscape-rest-preview.png) show the unresolved red rest highlight. [Observation](capture-traces/10-workout-observation.json) and [bounded portrait trace](capture-traces/workout-multi.json) retain the failed workflow attempt. No subsequent #11–15 workout claim is made.
- #10's failed DEBUG side-readiness frame is retained; settled side evidence comes from ordinary touch orbit. Poker's first vertical top gesture did not orbit; its diagonal retry is retained separately.
- [Flash side-convention check](flash-hand-convention.md) finds stable intrinsic low/high-model-X labels and no established descriptor swap. The three-edge screenshot lacks active-pose evidence needed for a complete screen-side explanation. No side-label correction or semantic correctness pass is asserted.
- Forge's all 20-contact normal/entity tests are separate from its ten-category app images. Complete bearing-face coverage of the edge-on 40-degree sloper, large flat edge and slopey crimper is not established by those images.

Root owns subsequent user review and any runtime correction. This record does not reopen or broaden the accepted CAD geometry scope, and does not claim fresh human app approval.
