# Live settling for hangboard cords

Status: approved by the user on 2026-09-29, including live settling on
Clavellium first, followed by the other corded boards.

The user additionally requested three times the current rope thickness.

## Intended behavior

Cord contact positions come from runtime geometry and physical constraints.
Changing the loaded board orientation makes the cord slide, take tension,
and settle against the board. A passage identifies an opening through which
the cord must remain threaded; its center is not a fixed rope attachment.
Authors specify the connection graph, physical attachment facts, dimensions,
and display estimates. They do not specify bearing points for each pose.

Use three times each existing rope's diameter throughout the rollout. Apply
the same increased radius to the rendered tube and the physics collider.
For Clavellium, the current 2 mm radius becomes 6 mm: 12 mm diameter instead
of 4 mm. This is a user-requested display adaptation, not a measurement of
the supplied sling. Do not use a thin invisible collider beneath a thick
rendered rope. A passage too small for the new diameter is a fit failure
to report and resolve, not permission to enlarge the physical board or
permit penetration. Keep real source dimensions unchanged.

First prove this behavior on the actual Clavellium CAD solid. Then use the
same simulation core for every represented cord in the catalog, adapting
each board's evidenced attachment or threading graph. Completion of the
Clavellium milestone does not complete the catalog rollout.

Camera orbit remains a camera operation and does not rotate the board
relative to gravity. Loaded-position changes and explicitly controlled
board-orientation transitions drive simulation. The current Clavellium
8 mm presentation remains as accepted by the user. Unknown grip-to-channel
mappings are not invented; debug physical rotations can test settling
without assigning those rotations to real grips.

## Existing boundary and failure

`BoardModelRealityScene` currently replaces transient cord geometry when
it selects a canonical position. CAD packages normally provide an offline
generated `cordContactPoints` cache; the older runtime section solvers are
static solves, not time-stepped rope dynamics.

Clavellium has three owner-confirmed straight passages. Its represented
single loop uses the central rectangular passage. Its current fixed mouth
centers allow a cord to end unsupported in the opening. A live system must
permit transverse motion within the opening and account for the continuous
hidden segment as part of the rope's length.

Previous experiments are not accepted implementations. Tests against the
corrected Mini Bar CAD solid found excessive local strain near the mouths,
despite some passing point-clearance checks. The new acceptance tests must
measure segment clearance, strain, topology, and convergence together.
See [the retained authoring guide](../../HANGBOARD_CORD_AUTHORING.md) and
[the historical experiment](../../../Tools/HangboardRopePrototype/README.md).

## Chosen approach

Implement a deterministic CPU constraint solver in Swift, independent of
RealityKit entities. Represent each physical rope as a continuous chain,
including particles within a hidden passage. Use fixed-step constrained
dynamics with length, contact, attachment, and passage constraints. Start
with XPBD distance constraints and a coupled board translation; use a
stiff-chain solve or simultaneous correction if local iterations cannot
meet the strain acceptance tests. No algorithm is accepted merely because
it produces plausible screenshots.

The loaded orientation is prescribed by the existing selected presentation.
The board's vertical position responds to gravity and rope tension. This
first release does not require free board tumbling, arbitrary dragging,
knots, or accurately measured friction and elasticity. Damping and masses
without primary measurements are explicitly display estimates. They must
not become manufacturer or training claims.

A native cloth or rigid-link chain is an alternative implementation, but
neither is a shortcut around passage topology or exact collision validation.
Interpolating old cached paths is rejected as a substitute for live contact.
The XPBD approach is selected for a testable core and control of these
constraints, not because the previous experiments establish convergence.

References: [XPBD paper](https://mmacklin.com/xpbd.pdf),
[RealityKit frame events](https://developer.apple.com/documentation/realitykit/sceneevents/update),
and [dynamic mesh buffers](https://developer.apple.com/documentation/realitykit/lowlevelmesh).

## Inputs and package contract

A hash-bound, bundled physics descriptor carries the simulation inputs:

- The board collision solid, in the existing importer/model coordinate basis
  and metres. For CAD boards, export the final watertight FreeCAD solid,
  including actual channel voids. Contact overlays are not extra obstacles.
- An explicit graph of fixed support endpoints, true board attachments,
  sliding passage portals, hidden channel connections, and exterior winding.
- Portal cross-sections and channel regions derived from the authored solid
  and identified channel features. Region constraints permit sliding;
  centerlines provide initialization and do not pin bearing particles.
- Rope radius and total rest length for each continuous rope; hidden lengths
  are included once. The compiler must reject ambiguous per-lead/total-length
  conversion instead of guessing a physical connection.
- Existing loaded rotations, optional source-backed mass, and clearly
  identified display estimates for missing simulation parameters.

Bind the physics descriptor to both source geometry and the shipped model
SHA-256. Generate it during CAD package compilation and stage it with normal
package metadata. The USDZ remains the only Apple On-Demand Resource and
ships without cords, material bindings, or textures. Do not commit generated
`board.json` for a CAD package.

Extend the existing Python and Swift package validators together. Initial
legacy packages continue to use their existing validated renderer until
their physics inputs pass the new contract. A malformed or hash-mismatched
physics-enabled package enters the existing unavailable state; it must not
silently use a decorative cord instead.

## Simulation and collision responsibilities

The pure solver owns positions, velocities, immutable rest lengths, support
constraints, board vertical state, and measured residuals. Begin with a
1/240 second fixed step and bounded substeps per rendered frame. These are
engineering starting values, not proven performance. Deterministic tests
advance an exact number of steps without a display clock.

Use an accelerated triangle collider with signed inside/outside queries
from a closed solid. A coarse field may accelerate queries, but acceptance
uses the actual surface. Enforce finite-radius segment contact, not just
particle distance. Swept collision or a conservative movement bound must
prevent crossing wood or a portal rim between steps. Recheck collision after
length corrections, and length residuals after contact corrections.

Passage constraints preserve the chosen channel and traversal order while
allowing the rope to slide against its walls. A rope cannot escape through
solid wood, switch to an adjacent Clavellium channel, or switch winding by
teleportation. For a continuous loop, the overhead support constrains its
physical ends; the hidden segment remains part of the dynamic chain.

True tied attachment endpoints remain fixed relative to the board. The
core must distinguish them from sliding mouths. Exterior wraps use a
separate connection graph with the same collision and length machinery;
do not turn an exterior lead into an unevidenced internal passage.

## Runtime and lifecycle

Keep simulation state per displayed board instance. Run bounded simulation
work separately from main-thread entity updates and publish validated frame
snapshots. Use a reusable tube mesh updated from particle positions rather
than allocating a new entity tree every frame. Hidden rope is naturally
occluded by the board and is not a separate visible channel spine.

On position change, retain the existing chain and transition the prescribed
board rotation through bounded increments so contact can evolve. Initialize
from a geometry-derived threaded seed on first load, not pose contact points.
If a seed cannot satisfy topology and length, fail explicitly.

Sleep the solver after settling; wake it for physical pose changes. Pause
when the view is hidden or the app is inactive, discard elapsed background
time, and cancel frame subscriptions/tasks when the scene is released.
Clearing and reselecting a position must not leak chains or subscriptions.
Paired models have independent chains and do not share mutable state.

Cord entities remain transient, non-pickable, and outside accessibility.
Selection highlighting still maps only to canonical physical contacts.
Frame the board and moving rope conservatively during motion; update final
framing once settled without making the camera chase every particle.
Reduce Motion suppresses settling animation and shows a runtime-computed,
validated settled result; it does not return to manually authored contacts.

## Clavellium acceptance gates

The following are proposed engineering tolerances, not physical product
measurements. Measure them with the actual final CAD collision solid and the
user-requested 6 mm-radius round-cord display adaptation of the photographed
flat sling. Use the increased radius when seeding, solving, and evaluating.

1. The central passage carries exactly one continuous loop. Both support
   endpoints remain constrained, and the rope traverses that same passage
   throughout settling and rotation. No intermediate mouth-center pins.
2. After settling, total loop-length error is at most 0.5 mm and maximum
   local relative segment strain is at most 0.5%. Report both; one cannot
   stand in for the other.
3. Finite-radius segment clearance is at least radius minus 0.05 mm during
   accepted motion and after settling. At expected loaded bearings, the
   surface gap is at most declared clearance plus 0.2 mm. Free spans are
   allowed to have greater clearance.
4. The upright rope contacts the upper passage wall automatically. Debug
   90 and 180 degree physical rotations move bearing to the appropriate
   surfaces without changing authoring coordinates. These are physics
   tests, not claims about which grip uses which passage.
5. Converge within five simulated seconds: speed below 1 mm/s and board
   displacement below 0.1 mm across the final 0.5 seconds, while meeting
   length and collision tolerances. Repeat deterministically and compare
   with half-sized time steps; endpoint/contact differences below 0.2 mm.
6. No nonfinite state, rope self-crossing, wood traversal, lost channel, or
   stretched links after repeated position changes, a delayed frame, pause
   and resume, or clearing and reselecting. Bound work on delayed frames.
7. Measure simulation plus mesh-update cost on an available physical iPhone
   before claiming device performance. Target 60 fps, with under 4 ms at
   the 95th percentile for one Clavellium rope. Simulator timings alone
   cannot establish this target. Record the device and OS with the result.

Pure solver tests precede app integration. Then validate current-source iOS
loading, picking, accessibility, lifecycle, portrait/landscape framing, and
Reduce Motion. Show front/side/top comparisons and native screenshots;
retain a recording or ordered frames that demonstrate actual settling.
Run package validation, staging/hash checks, and relevant native suites.
All external validation resources must carry workspace ownership and be
deleted by exact identity before reporting completion.

## Catalog rollout

Inventory generated from native manifests and sidecars as well as committed
board documents on 2026-09-29: 15 boards, 17 suspension setups. Existing
metadata labels below describe current representation, not proof of a
physical attachment graph or eligibility for live simulation.

| Package | Current suspension | Source |
| --- | --- | --- |
| clavellium-training-block | one internal loop | CAD |
| lattice-mini-bar | two internal loops | CAD |
| crimptonite-helium-mobile | internal loops | CAD |
| captain-fingerfood-pocket | paired exterior leads | CAD |
| j-bryant-ftg-32 | paired exterior leads | CAD |
| lattice-mxedge-lift-large | paired exterior leads | CAD |
| lattice-mxedge-lift-small | paired exterior leads | CAD |
| metolius-light-rail-2 | paired exterior leads | CAD |
| metolius-rock-rings-3d | two independent paired-lead instances | CAD |
| captain-fingerfood-dual | paired exterior leads | mesh |
| captain-fingerfood-unlevel | paired exterior leads | mesh |
| nature-stone-hanger | paired exterior leads | mesh |
| tension-flash-board | exterior two-branch cord | mesh |
| yy-baguette-evo | exterior two-branch cord | mesh |
| yy-penta-evo | two independent paired-lead instances | mesh |

After the Clavellium gate passes, test the curved Mini Bar channels and
rounded Helium Mobile ends before the remaining graph types. Audit every
remaining setup against retained exact-revision evidence. Upgrade collision
geometry and channel representation where necessary; do not infer hidden
connections or reclassify Captain Fingerfood's sourced lip-to-recess route
as a through-bore. Unsupported evidence or nonwatertight collision geometry
is an explicit rollout gap to resolve, not an excuse to mark a board covered.

Every canonical pose and every paired instance must pass the same topology,
strain, collision, convergence, lifecycle, and native visual gates. Refresh
the cord audit and delivery lock for promoted packages. No simulated cord
is marketed as a load-rating or safety analysis of the physical hangboard.
Include a per-board fit check for the threefold thickness increase, and retain
the baseline radius used to derive it so repeated builds do not multiply it
again. Any fit conflicts remain explicit rollout gaps.

## Implementation boundaries

Keep pure dynamics, collision queries, package compilation/validation, and
RealityKit frame/mesh integration in separate focused units. Integrate with
`BoardModelRealityTypes.swift`, `BoardModelView.swift`, existing suspension
types, `Tools/HangboardCAD`, and `Tools/HangboardPackages`. Preserve the
project's iOS 18 minimum and existing model identity/ODR contract.

Deliver the Clavellium core and integration first, with all numerical gates
and evidence, then the catalog adapters and package promotions. Do not
bundle unrelated hold geometry or routine changes into this subsystem.
