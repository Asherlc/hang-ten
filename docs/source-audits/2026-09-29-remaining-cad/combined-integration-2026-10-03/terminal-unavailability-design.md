# Terminal unavailable renderer preparation

Bounded correction authorized by the published-ref review: first Start must not remain in Preparing 3D after the existing board or hand unavailable fallback is terminal. Successful CPU setup readiness, request ownership, the existing three-second countdown, audio deferral, authored tasks/times, resume and Skip stay unchanged. This does not certify GPU presentation.

Represent each mounted renderer as loading, ready or unavailable. Existing successful readiness queries retain their meaning. A separate resolution query requires every requested host kind to be present and every mounted host to have finished loading successfully or reached its existing unavailable fallback. The Start gate consumes only the current preparation token and only once. It blocks loading, missing hosts and stale or cancelled requests.

Board Surface reports its own loading/unavailable status and continues forwarding its ready descendant report. Single and paired hands report terminal unavailability explicitly without changing their overlay or attempting a retry. No substitute geometry, cached raster fallback or new training text is introduced.

Tests first reproduce the issue through real mounted preferences: missing board-resource acquisition and injected existing single/pair hand asset errors. Add focused policy cases for mixed readiness, missing/loading hosts, stale terminal records, cancellation and a fresh request. Retain successful current-host synchronization tests. Validation uses the existing CI numerical recipe, optimized Debug with assertions retained. Original physics waits, physical acceptance criteria and production solver bytes remain unchanged.
