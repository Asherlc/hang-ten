# Compact Single-Hand Hangboards Design

## Goal

Expand Hang Ten's physical-board catalog with commercially available,
rope-suspended compact single-hand hangboards and lifting edges verified from
primary manufacturer evidence. Add only training plans whose complete
prescription (work, rest, repetitions, order, and side instruction) is
attributable to a primary source.

## Scope and taxonomy

This import uses the user's intended category: a compact board or lifting edge
used by one hand at a time, generally through a rope, a loading pin, or an
anchored band. It excludes conventional full-width hangboards merely because
they have a central hold that can be used one-handed.

An item is eligible when the manufacturer identifies it as a portable
hangboard, lifting edge/block, no-hang device, or single-hand portable board,
and provides enough first-party visual evidence to author each canonical hold
directly. Material finishes and cosmetic editions remain one product when their
physical hold layout is unchanged. Different grip inventories or dimensions are
separate packages.

Initial confirmed candidates include Nature Climbing Stone Hanger Mini, Lattice
Mini Bar, Lattice MXEdge Lift (Small and Large), Plateau Lifting Edge,
Frictitious Nug, and Max Climbing One Finger Trainer. The research pass also
checks manufacturer catalogues for Tension, Metolius, Captain Fingerfood,
Problemsolver, AEVORN, Aelith, Two Stones, and other identified makers. A
candidate is not imported if its official evidence is insufficient for a
complete direct hold inventory, front presentation, or physical identity.

## Data and provenance

Every imported package remains a flat `Hangboards/<slug>/board.json` package
with a hand-authored, head-on PNG presentation and manually drawn canonical
paths. Board packages contain no source material or audit file. A dated source
audit documents product URL, review date, exact revision, visual evidence,
hold-inventory mapping, variants, and any omission.

Plans remain separate from boards. A routine is added only from a primary
manufacturer or named-author source that states the complete prescribed
sequence. It is classified as board-flexible when semantic targets are factual,
and board-specific only when a numbered source map resolves to one imported
board. Mention-only articles and incomplete workout advice are recorded as
researched but are not turned into timer steps.

## Delivery and verification

The import is delivered in auditable batches. Each batch adds source audits,
complete packages, any source-complete plan seeds, regenerated
`PlanLibrary.json`, and targeted tests for catalog discovery and plan
resolution. The complete catalog is validated with the package script,
PlanLibrary export `--check`, and an iOS simulator visual review of normal,
active, and hit-tested paths. The final audit lists included products,
deduplicated variants, excluded candidates, and why each exclusion was needed.

## Constraints

- Use primary manufacturer evidence for board identity, geometry, and training
  prescriptions; record any exceptional non-primary source and caveat.
- Draw every path deliberately in Workbench. Do not use image-driven geometry,
  vectorization, registration, or contour tooling.
- Do not invent measurement, capacity, grip, plan, timing, rest, or coaching
  details. Omit unsupported fields.
- Preserve a training prescription exactly for `.official`; label any
  app-timing expansion `.adapted` and document it.
- Do not make a full-width board eligible merely because it supports a one-arm
  exercise.
