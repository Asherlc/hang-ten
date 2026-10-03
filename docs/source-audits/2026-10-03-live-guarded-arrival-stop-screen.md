# Guarded 50 µm arrival stop: false settling closes the experiment

The deliberate revisit failed the propagated trajectory at **step 177**. Candidate speed was 0.911336 mm/s and it reported settled. A strict original continuation from its complete accepted state had speed **1.126070 mm/s** and reported unsettled. The unchanged 1 mm/s settling requirement therefore fails. No tuning, app adoption or new video followed.

The all-phase 50 µm full-QP norm retained strain .0002 and arrival full-step acceptance. This norm was previously tested; the full-step guard and strict check at every reported settled frame were the new guards. Earlier negative-multiplier hints were already present, so they do not make this a new norm mechanism. Historical terminal noise remained adverse evidence and was reproduced here.

Fixed step 109 passed: two corrections versus eleven, strict pose error 2.167154 µm, seven alternating complete-step median ratio .214124. Ordinary step 140 passed: two corrections, strict error 1.728017 µm, ratio .915742. Neither checkpoint yet reported settled. Absolute candidate times remained roughly 5 ms, above the 4 ms host screen budget.

The independent trajectory stopped after 177 steps, 518 candidate versus 622 control QPs. Maximum propagated pose error was 11.897936 µm; all measured steps had original-mesh/material acceptance and zero caps/retries. This is partial trajectory evidence, not a passing 540-step screen or a speed/stability claim. The first actual settled-state strict continuation rejected the candidate.

Behavioral RED kept the flag inert and failed the ≤5-QP checkpoint gate. GREEN changed only norm selection in copied native sources, passed the two necessary checkpoints and exposed false settling in the required trajectory. All eight new private groups were independently verified absent. Companion JSON binds retained results, sources, proposal and resource manifests. Product solver, seated cords, CAD, packages and rendering remain unchanged.
