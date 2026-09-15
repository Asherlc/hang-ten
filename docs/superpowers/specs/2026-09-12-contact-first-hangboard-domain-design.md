# Contact-First Hangboard Domain Design

**Status:** approved direction; hard-cut implementation is pending review of this written contract.

## Goal

Replace Hang Ten's logical-hold ID contract with a contact-first board domain. A
plan describes the contact it requires; only a resolved board revision names
physical contacts and model nodes. This is a hard cut: production code contains
no legacy board-schema decoder, semantic-hold map, direct plan hold-ID target,
or legacy persistence decoder.

Existing raster-only boards remain supported as v3 raster presentations until a
verified model replaces them. That is a presentation choice, not a second
identity system. A model board remains model-only and ships no PNG or canonical
2D contact geometry.

## Domain model

`BoardRevision` is the package root. It has immutable `boardID`, immutable
`revisionID`, source-audit references, ordered `contacts`, ordered positions,
and typed presentation media.

`PhysicalContact` is the sole selectable surface entity. Its opaque `id` is
stable only within its board revision. It stores source-backed factual metadata:
name, kind, feature tags, capacity, documented depth range, grip compatibility,
side/pairing, and position membership. It does not store coaching copy, plan
aliases, display bounds, or a mesh node name.

`ContactRequirement` is the only plan-target value. It may state `kind`,
required features, a documented depth interval, finger capacity, hand capacity,
and required grip compatibility. Hand use, side, repetitions, timing, and grip
cue stay on the workout step, where they already describe the task rather than
the board. It has no `id`, `ids`, `semantic`, `semantics`, `fallback`, or
board-specific mapping member.

`ModelComponent` is a model-descriptor binding. It has an importer-visible
`nodeID`, a role of `body`, `contact`, or `attachment`, and an optional
`contactID` only for the `contact` role. A descriptor permits one or more body
components, zero or more attachments, and one or more mesh components per
contact. Descriptor `contactID` values must equal the package contact inventory;
node IDs never appear in plans or saved activity.

The former `BoardHold` becomes `PhysicalContact`; the former `HoldTarget`
becomes `ContactRequirement`. There is no compatibility typealias or legacy
initializer.

## Resolution

At workout start, `ContactResolver` filters the selected board revision's
contacts against a `ContactRequirement`, then applies the step's compatible
grip, selected position, hand-use rule, and side. It sorts candidates by the
package's canonical contact order.

The plan explicitly requests one of three selection policies:

- `allMatching`: all contacts satisfying the requirement;
- `single`: exactly one candidate after side/position filtering; and
- `bilateralPair`: exactly one documented pair with compatible factual
  descriptors.

Validation rejects a plan whose source-backed requirement cannot resolve for a
declared compatible board. Runtime fails closed with the current explicit
unavailable-target state if a package's declared revision violates the
assumption. It does not substitute a nearby contact, an alias, a feature
fallback, a raster path, or a different board revision.

Bundled plans are transcribed from direct IDs and semantic labels to factual
requirements backed by their existing retained plan source. Unsupported source
details are omitted; no requirement is inferred from model geometry.

## Board packages and models

All shipped packages use board schema v3. The Swift loader and Python validator
accept v3 only. They reject a root with `holds`, `semanticHolds`, v1/v2 media,
or unknown members rather than adapting it.

Raster media owns only its presentation's canonical contact paths and is valid
only for a raster presentation. Model media owns exactly one USDZ and one
hash-bound descriptor. Its model-derived contact centers and face-plane bounds
are generated outputs, never handwritten board metadata. A model presentation
cannot contain PNG media, raster paths, or a raster fallback.

The descriptor requires complete contact coverage, permits multiple disconnected
pieces for a contact, and permits multiple body components. This supports a
two-body product such as Triple Twins without collapsing either physical body
or fabricating an alias. It continues to reject unbound geometry and
attachments declared as selectable contacts.

## Persistence and external activity

On completion, each work segment records a resolution snapshot containing
`boardID`, `revisionID`, the model SHA-256 when model media was used, the
resolved physical contact IDs in canonical order, and the requirement that was
resolved. This makes historical activity auditable after a catalog correction.

The app writes v2 activity and session persistence under new storage keys. It
does not decode, translate, or retain local v1 records or custom plans that
contain direct hold IDs. The old local keys are removed as part of the release.
Previously written HealthKit workouts remain HealthKit history but are not
reinterpreted as v2 contact snapshots.

## Hard-cut removal list

The implementation removes all of the following instead of leaving deprecated
paths:

- `SemanticHoldMappingDefinition`, `BoardMappingDefinition`, `boardMappings`,
  and every `.semantic`, `.semantics`, and `.holdIDs` plan-target case;
- `HoldTarget.ids`, feature fallback substitution, and the resolver branches
  that accept a supplied hold-ID array;
- the `TrainingBoard.semanticHolds` field and all package-loader assignments;
- the one-body descriptor requirement and the equality contract between a
  training target ID and a model-node binding ID;
- v1/v2 board-package decoder branches, fixtures, validators, and conversion
  adapters; and
- local activity/session/custom-plan persistence decoders and keys that carry
  the former target or hold-ID formats.

The repository keeps only source-audit material needed to substantiate the new
v3 catalog. It does not retain a runtime or tooling compatibility adapter.

## Validation

Both parsers reject prohibited legacy keys and prove the same v3 contract with
a shared negative fixture matrix. Tests cover: a plan requirement with no IDs;
deterministic single/pair/all resolution; a two-body model descriptor; exact
mesh-to-contact inventory; model-only media isolation; source-backed depth
matching; unsupported requirements; and a persisted v2 resolution snapshot.

The full package catalog is migrated atomically before the v3-only loader is
introduced. The migration gate runs Python package validation, Swift parser
tests, all affected plan validation tests, model descriptor/native picking
tests, and the Hang Ten iOS build. Every model promotion also retains its
existing evidence, descriptor hash, actual-export validation, and human visual
review requirements.

## Non-goals

This change does not infer contact metadata from meshes, alter manufacturer
training prescriptions, fabricate geometry for unresolved supplied models, or
turn raster-only boards into models without verified source evidence. Those
remain separate catalog/model migration tasks executed against the v3 contract.
