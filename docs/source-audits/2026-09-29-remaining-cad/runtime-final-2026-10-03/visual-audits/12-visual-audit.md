# ROOT #12 current app visual audit

The supplied frames show correct visible wood rendering and localized highlights for one representative contact on each of Poker's four faces. Horizontal orbit reaches an end-on view; the sequential diagonal retry supplies a genuine top-oblique view. The landscape model and selected card fit clearly. The three-frame addendum below confirms one physical Face A slot pick and outer-slot restoration. **The initial vertical top gesture remains FAIL. User acceptance and workout validation are not claimed.**

I inspected 16 complete frames with `view_image` at original detail, without cropping or pixel measurement. All screenshot byte hashes match their receipts; every receipt matches installed binary SHA-256 `7aca0429a95c54572cec9367f5120c7873e8f53bceb97cc09f27cd5906e3bbca` and [installed provenance](installed-app-provenance.json) SHA-256 `0f378ff2f58a27921251399ed035ab357ae993cf517569527390ac30d016232f`. The provenance identifies commit `f9554600c1e5d94d027346ca5d6ca7343d71a7e7`, board `owl-climb.poker`, and native model `1ee84de3f5054d55bd1078e466499cbc508decd11826bd5e626b349a75ba3675`. Previously accepted source geometry and approvals are unchanged.

| Check | Whole-frame observation |
| --- | --- |
| Face A | [Left outer slot](app-captures/12-live-hold-face-a-left-outer-slot.png) has a localized red interior and rounded boundary with other slots/pockets inactive. |
| Face B | [Left deep sloper](app-captures/12-live-hold-face-b-left-deep-sloper.png) highlights the broad deep curved region with the corresponding right form and adjacent contacts wood-colored. |
| Face C | [Left shallow half-round](app-captures/12-live-hold-face-c-left-shallow-half-round.png) shows the shallower contact shape and its distinct selected region. |
| Face D | [Left deep rounded recess](app-captures/12-live-hold-face-d-left-deep-rounded-recess.png) shows the deeper recess and visible lower lip; its title wraps cleanly in the selected card. |
| Materials/inactive state | All sampled body and inactive contact surfaces retain warm wood shading. [Unselected Train](app-captures/12-live-unselected-train.png) has no red highlight. The supplied same-scene restoration addendum is reviewed below. |
| Horizontal orbit | [Orbit 1](app-captures/12-live-horizontal-orbit-1.png), [2](app-captures/12-live-horizontal-orbit-2.png), and [3](app-captures/12-live-horizontal-orbit-3.png) progress to a genuine end-on view. At the final angle the selected Face B surface is occluded; its selected card remains. The board is small in that view, so detailed highlight coverage comes from front and landscape evidence. |
| Initial vertical gesture | **FAIL retained:** [raw failure](app-captures/12-top-touch-did-not-orbit.png) stays front-facing, with revision 1 and azimuth/elevation 0. [Capture batch](capture-normal-batch-12.json) records exit 1 and unchanged projected contact frames. `cameraSettled=true` does not prove a successful gesture. |
| Diagonal retry | [Successful top-oblique frame](app-captures/12-live-top-oblique.png) visibly changes projection and exposes the top surface. [Retry receipt](capture-tail12-commands-receipt.json) records exit 0; the frame records revision 5, azimuth -0.54071856, elevation 0.3253892. This pass does not erase the failed vertical gesture. |
| Suspension | Poker's established [metadata matrix](read-only-plan/runtime-review-matrix.json) has no suspension profile or reusable instances. No cord is expected or shown. |
| Landscape/UI | [Landscape](app-captures/12-live-landscape.png) fits the full Face A model and its complete selected card without clipping. The portrait cards match Edge/Sloper kinds and the selected face contacts. The 34-entry grid extends below the viewport and uses ellipsis; scrolling and picking are not assessed. |
| Normal lens | [Normal lens](app-captures/12-live-normal-lens.png) keeps the complete model and matching selected card visible. |

The initial four-contact sample plus the addendum's opposite Face A slot cover five distinct contacts, not all 34 logical contacts. The [JSON audit](12-visual-audit.json) contains the exact frame inventory and scope limits. Only these scratch reports were written; this agent performed no app, Simulator, build, external-resource, production, or canonical operations.

## Supplied interaction addendum

[Physical Face A slot pick](app-captures/12-slot-physical-mesh-pick.png) shows the highlighted viewer-left slot and matching `Face A left outer slot` / `Edge` card. Its receipt records `actualPhysicalMeshPick=true`, `tapRevision=1`, and `pickedContact=face-a-left-outer-slot` after a before state with `tapRevision=0`.

[Right outer slot selected](app-captures/12-left-restored-right-selected-same-scene.png) restores the left slot to wood and highlights only the right. [Left outer slot selected again](app-captures/12-right-restored-left-selected-same-scene.png) restores the right to wood. Cards and chips follow the corresponding IDs. The three receipts share launch timestamp, `sameScene=true` and `tapRevision=1`; selection-only updates keep renderer revision 2. All three additional screenshot hashes match receipts and current installed binary/provenance, and all three states are settled.

This confirms one physical pick and Face A outer-slot restoration. Other-face picking/restoration, full deselection and real-workout phases remain unaudited. The original failed vertical gesture remains a retained failure.
