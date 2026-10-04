# Prestart suppression source audit

Read-only audit; no source, build, Simulator, or protocol changes. Frozen action evidence was read only after root authorized it. This does not select or authorize a new arm.

## What the source establishes

- `RootView.swift:1994–2011` recomputes Timeline content periodically using `WorkoutClock.monotonicTime`, not `context.date`. Countdown is a local value from the current session state. At a coherent recomputation during an initial countdown, the existing cue policy excludes hands (`WorkoutTimeline.swift:316–326`, `RootView.swift:2420–2444`). Skip countdown deliberately retains preview hands.
- `RootView.swift:2076` supplies the custom environment boolean from **only** `routineStartedAt == nil`. The synchronous initial-start mutation at `1801–1803` sets a future, nonnil routine date, a future active-start uptime, and initial countdown kind. Therefore this custom suppression becomes false for the whole armed initial countdown, even though work has not begun. There is no await between those three assignments; the audit does not assert a partially mutated struct became visible.
- `GripHandModelView.swift:136–149,989–1002` places the complete normal hand content behind that environment guard. Normal initializers create lazy storage, not scenes; the clear branch does not access `scene`. Constructor/make entries demonstrate that a hand-content path eventually executed, but they do not themselves record which environment value the child read or its session identity. The environment default is false (`86–94`).
- The `workout-prestart-hand-state` marker (`RootView.swift:2106–2117`) is a countdown onChange callback. Its countdown argument is a delivered value, while its nil predicate reads session state when the callback executes. It is neither an atomic state snapshot for the child nor a record of constructor-time predicate evaluation. The pre-autostart marker similarly occurs before the actual autostart decision.

## Startup ordering and possible unstarted branches

The environment modifier contains no session mutation, task, autostart callback, or countdown cancellation. It is inside Timeline content; the existing workout onAppear remains outside the GeometryReader (`2217–2263`). Source alone does not establish that this modifier reordered or prevented onAppear. Changing the hand-content branch can alter downstream view construction work, but no scheduling or blocking cause is demonstrated.

Ordinary onAppear sets `didAutoStart = true` before calling `toggleRunning`. Existing branches can defer initiation: required sensor preparation (`3157`, `3422`), audio preparation (`3182–3189`), or the audio arm task (`3197–3224`). Another toggle can cancel pending preparation/arming (`3141–3146`); scene inactivity can interrupt/cancel an initial countdown (`2264–2266`, `1825` onward). The frozen markers do not record the relevant branch outcomes, audio state, pending task, later active-start uptime, or didAutoStart. These are source possibilities, not diagnoses of this run.

## Frozen action evidence limits

The action is invalid for the intended color comparison: zero qualified phase screenshots within the 300-second harness bound, no positive countdown marker, and its original checker is not evaluable. Preserve that classification.

However, do **not** describe it as an app that remained unstarted for 300 seconds. The complete 152-record trace shows pre-autostart marker13 at epoch1790998919.910209, then pair constructor15 at1790998940.048887: about20.139 seconds later. Selected board preview appears at sequence20; requested/inputs turn active at145–148 around1790999110.20 and return preview at149–152 around1790999117.24, about7.03 seconds later. These CPU changes are compatible with workout time having advanced past a missed initial render/capture interval. They do not prove the displayed phases, exact session clock, or a main-thread stall. Root independently identified the same timing qualification. No constructor-time true prestart predicate is recorded, and the early true marker cannot be carried forward twenty seconds as unchanged state.

## Prospective future-deadline guard assessment, not a selected patch

To represent “not yet past initial countdown,” nil alone is insufficient. A predicate that covers nil plus a **future initial** active-start uptime would close that semantic gap if delivered coherently to the child. Restricting the future case to initial countdown matters: a blanket future-start check would suppress existing skip-preview hands and change visible behavior. After initial deadline, the same existing hand-content branch could resume without changing its camera, pose, colors, layout, or routine prescription.

This is not evidence that such a guard fixes the invalid action. A predicate evaluated using a Timeline sample is refreshed by that existing schedule, not by the clock merely advancing; a delayed update can conservatively extend suppression. It also cannot establish atomic delivery between independently evaluated environment/child content. The frozen action does not show an unwanted host during initial countdown, and its much later constructor could be appropriate after startup advanced. No next arm or production change is recommended from this evidence alone.

`source-excerpts.txt` and `source-hashes.json` bind the read source and line references. `report.json` binds the exact frozen trace and compact selected raw record fields. Earlier reports and raw bytes remain unchanged.
