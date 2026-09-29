# Per-hand plan targets

## Intent

An athlete should see every hold needed for the current grip. The plan data should say which holds the hands use, rather than combining a step-level hand count with a separate contact-selection policy. Migrate every bundled plan, preserving source-prescribed one-hand, asymmetric, and sequential tasks. Unless the source specifies otherwise, a hang uses two hands.

## Authored work-target format

A work target has an ordered `tasks` array. Each task is directly an array of one or two hand targets; there is no `Task` object. One entry means one hand, two entries mean simultaneous use of two hands. An absent `side` is unconstrained; `side` is present only for a source-prescribed left or right hand. Equal targets do not imply that the two hands must use distinct physical contacts.

```json
{
  "tasks": [
    [
      { "target": { "kind": "edge", "depth": { "minMM": 20, "maxMM": 20 } } },
      { "target": { "kind": "edge", "depth": { "minMM": 20, "maxMM": 20 } } }
    ],
    [
      { "target": { "kind": "sloper", "shape": "round" }, "side": "left" },
      { "target": { "kind": "jug" }, "side": "right" }
    ]
  ]
}
```

The JSON Schema for this object uses `$defs/Depth`. Categorical depth is `{ "category": "tiny" | "small" | "medium" | "large" }`. Measured depth is `{ "minMM": number, "maxMM": number }`, including exact values with equal bounds. Both forms reject extra properties. The app validates finite nonnegative bounds and `minMM <= maxMM`. `kind` and `shape` are enums matching `HoldKind` and `HoldShape`. A contact predicate needs at least one property. `fingerCapacity` is 1–4. The schema has no `if`/`else`, `hands`, `allowSwap`, or contact-selection field.

An empty `tasks` array means the athlete chooses holds, preserving the existing self-selected catalog exceptions. Rest segments have no target. The target schema should be stored as a versioned repository file and checked against every exported built-in work target.

## Resolution

Resolve each task as a simultaneous assignment of its hand entries to physical contacts, respecting predicates and any explicit sides. On a two-hand board, two equal entries may map to a documented `handCapacity: 2` contact or to a matching left/right pair. Two different entries must each resolve; neither may be discarded to make the step compatible. A physical contact with capacity 1 cannot serve both hands at once.

On a one-hand board, a two-entry task requires two copies of the board, one contact per copy. The workout explains the two-board requirement. It does not alternate hands automatically, since alternating changes the exercise. A one-entry task needs one board. A source-prescribed left or right side applies to the athlete's hand, not the board copy.

Compatibility, plan preview, live highlight, hold cues, and recording consume the same resolved assignment. Preview uses the first task. A timed step with multiple tasks and no source-backed subtask durations must preserve their order and expose a manual task change during the step; it must not invent time slices. The active highlight is the current task's full contact set. A historical recording retains the resolved contacts actually used.

## Migration boundary

The bundled library moves to `tasks` for every work segment. Migrate at the seed catalog and regenerate `PlanLibrary.json`; keep source order, durations, repetition counts, instructions, and provenance intact. Audit each bundled work segment against its primary source before choosing one or two hands and before splitting multiple old requirements into simultaneous or sequential tasks. In particular, source-prescribed single-arm steps must be one-entry tasks even where today's step metadata says `double`.

Existing custom routines and saved workouts may still contain legacy `handUse`, `side`, and `ContactRequirement.selection`. Decode them without data loss and translate them at the persistence boundary. New bundled data must not encode those redundant fields. Editing or duplicating a legacy routine writes the new target form only after the translation preserves its behavior. Do not change historical activity payloads in place.

The runtime derives hand count from each task. Step-level hand preference remains only where the source permits a genuine athlete choice; it cannot override a source-prescribed two-hand task. The plan editor can author one or two hand targets and ordered tasks without exposing selection policy.

## Validation

Add schema validation for the exported JSON; round-trip tests for categorical, exact, and ranged depth; rejection of malformed tasks and depth; resolution tests for paired contacts, one shared capacity-two contact, asymmetric contacts, and one-hand boards; and regression tests for the originally reported 7/3 cue. Audit all 26 built-in plans and check target resolution on every board where each plan is offered. Verify representative preview, live highlight, manual task change, and recording in an isolated iOS Simulator. Keep source URL and step-to-source mappings for changed routine content.
