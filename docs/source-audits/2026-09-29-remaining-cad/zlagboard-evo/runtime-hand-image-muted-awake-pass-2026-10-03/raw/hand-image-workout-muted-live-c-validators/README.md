# Prospective awake-context LIVE-c validators

Preparation only; no validator/runtime execution. Existing LIVE-b validators are copied with LIVE-c path labels only, retaining the qualified first-before census gap and all other board/hand criteria. Original helper bytes and diffs are retained. The driver additionally records a separate prospective clock-stability result.

The new fixed gate requires max-minus-min app(epoch-uptime)<=0.1s over every trace row, and host(epoch-monotonic)<=0.1s over every command start/end. All12 original phase offsets and150ms capture-start deadlines remain required in both recorded domains. Drift makes the planned comparison ineligible; no after-the-fact exception or rewrite of prior statuses. Stable clocks alone do not prove absence of OS/GPU effects or the cause of earlier drift. Root's awake assertion wrapper is separate evidence and this helper changes no resources.

Run only after the completed LIVE-c trace is explicitly frozen: `rtk proxy python3 <this-directory>/validate.py <completed-freeze-gate.json>`. This is offline retained-file checking; whole-image review and any IMAGE authorization remain separate root decisions.
