# Train-only structural removal comparison

Both arms completed all 44 scheduled captures and passed the retained offline provenance, timing and exact app/helper cleanup checks. Root and independent whole-image reviews found incorrect workout colors in both arms. The comparison stopped without a reversal or production adoption.

The same installed binary (`45fb07606a423a5e29e125e0179ff414bbc221d93554990c10c3e26d6831f26b`) contained only a temporary 22-line DEBUG TrainView gate beyond the pristine application sources. The action enabled structural removal of the Train board slot while the workout destination was shown. Both runs used the muted, awake, passive normal deep-link workflow. Source, patch, helper, release, build/install and parity records are retained exactly.

| Arm | Whole-image findings reported by root and independent reviewers |
| --- | --- |
| Control | Early Rest captures 010–018 remain red; 090 is blue. Second Hang 190–196 remains blue. Following Rest 197–207 is blue. |
| Action | Early Rest captures 010–018 remain red; 090 is blue. Second Hang 191–197 remains blue. Following Rest 198–207 is blue. |

Hands are absent in captures 004/005 and visible from 006 onward in both reviewed runs. Action capture 190 still shows Rest, while control 190 already shows Hang: matching external offsets do not establish matching internal phase boundaries.

There are no CPU/material, scene-lifetime or viewport brackets in these runs. Structural removal does not prove framework deallocation. These Simulator observations establish neither a hardware result nor a causal mechanism. No human approval, geometry change, completed repair or hand-image workout result is claimed.

The raw completion records retain their original pending-visual-review status, and the control freeze retains its historical pending-tail field. Later exact whole-image reviews supplement those records without rewriting them. The preflight preparation failures and correction are also retained.

Cleanup records cover each exact launched app and its owned awake helper. The persistent Simulator and DerivedData remained controller-owned; this packet does not claim their deletion.

See [index.md](index.md), [retention-manifest.json](retention-manifest.json) and [retained-files.sha256.json](retained-files.sha256.json).
