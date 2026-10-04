# Retained evidence

- [Initial whole screenshot](raw/evo/hand-image-workout-live-a-landscape/launch-initial.png): navigation-time only; not a timed phase or visual pass.
- [Original failure](raw/evo/hand-image-workout-live-a-landscape/failure.txt) and [completion](raw/evo/hand-image-workout-live-a-landscape/completion.json).
- [Raw commands](raw/evo/hand-image-workout-live-a-landscape/commands.json), [termination error](raw/evo/hand-image-workout-live-a-landscape/006-stderr.txt), and [app cleanup](raw/evo/hand-image-workout-live-a-landscape/app-cleanup.json).
- [Trace-copy hash record](raw/evo/hand-image-workout-live-a-landscape/trace-copy.json) and [36-file source freeze](raw/hand-image-workout-live-a-independent-audit/run-frozen-manifest.json).
- [Actual release](raw/evo/hand-image-workout-live-a-landscape/runtime-release.json), [helper](raw/hand-image-workout-runtime-prep/capture.py), [branch checks](raw/hand-image-workout-runtime-prep/branch_schema.py), and [event schema](raw/hand-image-workout-runtime-prep/event-schema.json).
- [Independent helper review](raw/hand-image-workout-helper-independent-review/report.json) and [prospective common-validator plan](raw/hand-image-workout-helper-independent-review/common-validator-command-plan.json).

Raw scratch-relative paths remain historical; `retention-manifest.json` gives the exact source-to-packet mapping. The inventory records packet hashes without altering any raw evidence.

Post-freeze supplement: [exact matching crash](raw/hand-image-live-startup-crash-audit/HangTen-2026-10-02-232849.ips), [identity/timing/stack audit](raw/hand-image-live-startup-crash-audit/report.json), and [source callsite excerpt](raw/hand-image-live-startup-crash-audit/audio-callsite.txt). This identifies the startup abort boundary without changing the invalid comparison outcome.
