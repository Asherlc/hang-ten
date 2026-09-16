# Contact Requirement Normalization

## Problem

`ContactRequirement` has overlapping fields that encode the same information in different ways:

- `kind` and `requiredFeatures` both describe hold type, with features like `.mediumEdge` encoding both kind and size
- `depthRangeMillimeters` and size features (`.mediumEdge`, `.largeEdge`) both describe depth, one precisely and one fuzzily
- `compatibleGripTypes` overlaps with kind — pockets and slopers only support open-hand, edges support crimps, etc.
- `ContactSelectionPolicy.allMatching` is really "I don't care which one," which is a property of the requirement breadth, not a selection mode

The `HoldFeature` enum mixes four orthogonal concerns: size (large/medium/small), shape (flat/round), angle (incut/slot), and grip (crimp). "Medium" has no consistent meaning across manufacturers — Rock Prodigy Pivot's "medium crimp" is 9mm while the community standard is 20mm.

## Goals

1. Remove overlapping fields — each field has one job
2. Eliminate ambiguity — no manufacturer-relative labels where numeric values exist
3. Keep fuzzy labels for sources that don't specify exact depths
4. Infer grip compatibility from hold properties rather than storing it

## Design

### New `ContactRequirement`

```swift
struct ContactRequirement: Codable, Hashable {
    let kind: HoldKind?
    let shape: HoldShape?
    let depth: TargetDepth?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let selection: ContactSelectionPolicy
}
```

### New types

```swift
enum HoldShape: String, Codable, Hashable {
    case flat
    case round
    case incut
    case slot
}

enum TargetDepth: Codable, Hashable {
    case category(HoldSize)
    case range(MillimeterRange)
}

enum HoldSize: String, Codable, Hashable {
    case tiny
    case small
    case medium
    case large
}

enum ContactSelectionPolicy: String, Codable, Hashable {
    case single
    case bilateralPair
}
```

### What each field covers

| Field | Replaces | Purpose |
|-------|----------|---------|
| `kind` | `kind` (unchanged) | Coarse hold type: edge, sloper, pocket, pinch, jug, gaston |
| `shape` | shape subset of `requiredFeatures` | Geometry: flat, round, incut, slot |
| `depth` | `depthRangeMillimeters` + size features | Coarse category OR exact mm range |
| `fingerCapacity` | `fingerCapacity` (unchanged) | For pockets: 2, 3, or 4 fingers |
| `handCapacity` | `handCapacity` (unchanged) | Single or double hand |
| `selection` | `selection` (reduced) | `.single` or `.bilateralPair` |

### What was removed and why

| Removed field | Why |
|---------------|-----|
| `requiredFeatures: Set<HoldFeature>` | Replaced by `shape` + `depth`. Size features encode depth (use `depth`). Shape features encode geometry (use `shape`). Grip features are inferred from kind. |
| `compatibleGripTypes: Set<GripType>` | Inferred from kind + shape + depth. Sloper → open-hand. Pocket → open-hand. Edge → crimp or open-hand depending on depth. No need to store explicitly. |
| `ContactSelectionPolicy.allMatching` | "Any matching hold" is a broad requirement, not a selection mode. Achieved by leaving `kind`/`shape`/`depth` unset or loosely specified. |

### Migration examples

**"Hang from any edge"**
```
Before: kind: .edge, requiredFeatures: [], selection: .allMatching
After:  kind: .edge, selection: .single
```

**"Hang from a medium edge"**
```
Before: kind: .edge, requiredFeatures: [.mediumEdge], selection: .allMatching
After:  kind: .edge, depth: .category(.medium), selection: .single
```

**"Hang from a 20mm edge"**
```
Before: kind: .edge, depthRangeMillimeters: {18, 22}, selection: .allMatching
After:  kind: .edge, depth: .range({18, 22}), selection: .single
```

**"Hang from a flat incut edge, 3 fingers"**
```
Before: kind: .edge, requiredFeatures: [.flatEdge, .incutEdge], fingerCapacity: 3, selection: .allMatching
After:  kind: .edge, shape: .flat, depth: ..., fingerCapacity: 3, selection: .single
```

**"Hang from any pocket, 3 fingers"**
```
Before: kind: .pocket, fingerCapacity: 3, selection: .allMatching
After:  kind: .pocket, fingerCapacity: 3, selection: .single
```

**Bilateral pair**
```
Before: kind: .edge, requiredFeatures: [.mediumEdge], selection: .bilateralPair
After:  kind: .edge, depth: .category(.medium), selection: .bilateralPair
```

### Impact on board JSON

Board `contacts` would replace `features: Set<HoldFeature>` with:
- `shape: HoldShape?` (when applicable)
- Depth remains as `depthRangeMillimeters` (already present)

The `HoldFeature` enum and the `features` field on `PhysicalContact` would be removed. Board packages that currently declare `"features": ["flatSloper"]` would declare `"shape": "flat"` instead.

### Impact on resolution

The resolver (`ContactResolver.matches`) would check:
1. `kind` matches (unchanged)
2. `shape` matches contact's shape (new)
3. `depth` overlaps with contact's depth range (new — replaces feature-based matching)
4. `fingerCapacity` matches (unchanged)
5. `handCapacity` matches (unchanged)

Grip compatibility is derived: the resolver knows that edges support crimps and open-hand, while slopers and pockets only support open-hand. No stored `compatibleGripTypes` needed.

### Impact on custom routines

The custom routine editor (`CustomRoutineEditorView`) currently exposes `GenericTargetChoice` with `.kind(HoldKind)` and `.feature(HoldFeature)`. This would change to:
- Kind picker (edge, sloper, pocket, etc.)
- Shape picker (flat, round, incut, slot) — shown when kind supports it
- Depth picker: either a size category (tiny/small/medium/large) or exact mm range

The `strippingUnsupportedCustomCueFields()` function would no longer need to strip `gripType` and `fingerConfiguration` from custom steps — those fields would not exist on `ContactRequirement`.

### Shape validity per kind

Not all shapes apply to all kinds. The schema does not enforce this at the type level — invalid combinations (e.g., `kind: .pocket, shape: .incut`) are simply unmatched by any board contact. The resolver treats shape as an optional filter; if no contact on the board has that shape for the given kind, the requirement fails to resolve.

Practical shape-kind pairings:
- **edge**: flat, incut, slot
- **sloper**: flat, round
- **pinch**: flat, round
- **jug**: flat, round
- **pocket**: (no shape — distinguished by finger capacity and depth)
- **gaston**: (no shape)

### Out of scope

- **`WorkoutStep` vs `WorkoutStepDefinition` duplication**: These are near-identical runtime vs persistence models. A separate pass could unify them, but that's structural deduplication, not semantic overlap.
- **`CustomRoutineStepDraft` vs `WorkoutStepDefinition`**: The draft is a UI editing model with intentionally simplified fields. It serves a distinct layer.
- **Segments redundancy**: Step-level targets are materialized into segment targets by the normalizer. This is intentional shorthand, not a bug.
