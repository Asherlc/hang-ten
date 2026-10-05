# Development documentation

Start with the [project README](../README.md) for setup and the app architecture.
These guides describe the current source layout and tooling.

| Task | Guide |
| --- | --- |
| Build generated resources and understand CI delivery | [Generated artifacts](GENERATED_ARTIFACTS.md) |
| Author or change a board | [Adding a board](ADDING_A_BOARD.md), [native CAD tools](../Tools/HangboardCAD/README.md) |
| Avoid CAD geometry and contact-binding mistakes | [Geometry precautions](freecad-authoring-lessons.md) |
| Author and validate cords | [Cord authoring](HANGBOARD_CORD_AUTHORING.md) |
| Diagnose suspension, offline models, or Apple ODR | [Suspension and ODR](3D_SUSPENSION_AND_ODR.md), [ODR packaging](IOS_ON_DEMAND_RESOURCES.md) |
| Import or audit a training routine | [Adding a routine](ADDING_A_ROUTINE.md) |
| Validate the iOS app | [Simulator validation](IOS_SIMULATOR_VALIDATION.md), [runtime services](IOS_RUNTIME_SERVICES.md) |
| Maintain runtime appearance | [Wood](CAD_WOOD_APPEARANCE.md), [plastic](CAD_PLASTIC_APPEARANCE.md), [grip hand](grip-hand-model.md) |
| Validate and stage board packages | [Package tools](../Tools/HangboardPackages/README.md), [testing](../Tools/HangboardPackages/TESTING.md) |

Product source mappings and manufacturer evidence live in `source-audits/`;
training prescriptions and field mappings live in `plan-audits/`. These justify
authored facts. Working plans, execution notes, logs, and cleanup receipts
belong in workspace-owned `.context` directories or CI artifacts.
