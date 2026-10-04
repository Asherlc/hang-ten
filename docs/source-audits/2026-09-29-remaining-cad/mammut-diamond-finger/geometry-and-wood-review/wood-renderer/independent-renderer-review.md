# Independent runtime-finish review

**P2: hierarchical descriptor paths are accepted but not resolved for materials.** `BoardModelRealityTypes.swift:280` reads only `finishByNodeID[entity.name]`; existing contact binding at`:882` resolves short names and full paths relative to each instance. A valid `Group/Left` selector silently misses an entity named `Left`. A nested attachment path can inherit wood instead of the required neutral finish. Current Mammut and all current bundled descriptors use simple node names, so this does not affect today’s Mammut rendering.

Minimal correction: traverse each instance separately, pass its root into material recursion, and share the existing name-first/path-second lookup between material and contact maps. Keep parent-finish inheritance for unnamed mesh descendants. Add a nested-path material fixture that proves both a selected wood node and forced-neutral attachment, plus inherited unnamed child appearance.

The shader and wood/plastic/granite factories exactly match reference6126228e8c44c5832982acc09e10ce47809f50c0. Neutral defaults, shared-contact union, primary picking, native cord behavior and baseline restoration are preserved. Both parsers reject malformed/conflicting/unknown selectors and forbid attachment overrides. New tests cover every Mammut contact’s wood/highlight/restore behavior and scene isolation; staging tests retain model bytes. No production board literals found.

No build/test was run by this reviewer. Shared-contact custom-material combination lacks a direct test but code review found the union behavior preserved. Source hashes and full finding detail are retained in the adjacent JSON.
