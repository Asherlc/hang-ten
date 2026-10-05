# Startup observation v2 (unapplied)

The three-file DEBUG proposal adds scalar attempt correlation to v1 without changing existing scheduling or production decisions. The source snapshots match the current f98 inputs; `git apply --check` passes. No source was applied or built.

Each request has an immutable UUID. A deferred audio callback consumes the recorded pending UUID, then either starts visibly under that UUID or creates an explicitly linked child request. Each arm Task captures its own immutable UUID. Synchronous diagnostic scopes never cross an await. Requested cancellation includes its actual pending/armed targets; catch and resumed-with-cancelled records separately identify observed cancellation. Old-task completion cannot silently adopt a newer request ID.

The registry retains strings and integer counts only. Context is existing audio-coach identity plus plan; the prospective evidence gate must require one context, one appearance, and no ambiguity marker. Reappearance or concurrent same-plan requests invalidate diagnostic attribution rather than blocking app behavior. The general audio-state callback intentionally has no guessed request identity; its dispatch event carries the consumed association.

The patch is larger (354 diff lines versus v1's 173) because of this explicit correlation, still within the same three reserved files. Existing source lines, actor annotations, Task/await/sleep/observer counts and state declarations are preserved. A 30-second observation is right-censored from recorded appearance. UUID/allocation/event I/O overhead is real; this cannot establish a cause or fix by itself. No typecheck, build or runtime result is claimed.
