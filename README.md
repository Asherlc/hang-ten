# Hang Ten

Hang Ten is a SwiftUI prototype for guided hangboard sessions. It starts with the
Metolius Wood Grips Compact II and is designed around the interaction that makes
Fingy useful: the current cue highlights the holds to use on a board map.

## Included

- Today screen with the next session and selected board.
- Metolius ten-minute sequence format translated to Compact II hold IDs.
- Research-backed and widely used protocols: Max Hangs, F80/F100 force-board
  sessions, Eva IntHangs, 7/3 Repeaters, and Abrahangs.
- Coach-developed variants: 7–53 Max Hangs, 3–6–9 Ladders, Density Hangs, and
  Zlagboard 60/60 Endurance.
- Plan detail view with the complete session flow and source link.
- Live guided timer with a start countdown, hang/rest intervals, pause/resume,
  and automatic hold cues.
- Explicit open-hand, half-crimp, full-crimp, pocket, and sloper metadata with
  a two-hand finger-position diagram.
- Completed routines can be saved to Apple Health as functional strength
  workouts after the system permission prompt.
- Progress screen with lightweight session history.
- A reusable board design language: future hangboards provide normalized
  silhouette, plane, and hold geometry while sharing the same sculpted
  materials, depth classes, mirroring, highlights, and hit testing.

## Run

Open HangTen.xcodeproj in Xcode 26 or build from the repository root:

~~~sh
xcodebuild -project HangTen.xcodeproj \
  -scheme HangTen \
  -sdk iphonesimulator \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO build
~~~

## Adding another board

1. Add another TrainingBoard to BoardCatalog.all in
   HangTen/Models/TrainingModels.swift.
2. Give each hold a stable board-scoped ID and normalized HoldFrame.
3. Create a board-specific `BoardDesign` extension beside
   `MetoliusCompactIIDesign.swift`. Describe only normalized geometry:
   silhouette, material planes, and hold pieces. Paired geometry should be
   defined once and mirrored.
4. Register the design in `BoardDesignCatalog`. `BoardDesignLanguage.swift`
   resolves every piece through the shared textureless sculpted-wood renderer.
   The same contact path is used for the inactive cavity, active fill, and
   derived interaction region, so highlights cannot drift out of alignment.
5. Set each hold's `gripType` and `cueStyle` so the board map and hand diagram
   describe the intended contact position.
6. Add a TrainingPlan that references the new board ID, or use
   HoldTarget.kind(...) for a plan that should resolve by hold type.

Boards without bespoke artwork continue to use the neutral vector fallback.
Board photos are reference metadata only; runtime geometry remains
deterministic and scalable.

Official routines live in `PlanCatalog` in
`HangTen/Models/TrainingModels.swift`. Each routine keeps its source label and
URL next to its board-specific hold targets. The timer supports variable hang
durations so short max hangs, repeaters, long density intervals, and extended
force-board recovery periods are represented without rounding everything to a
ten-second cue.

Manufacturer routines should be added with their official source URL and
source label. The catalog is intentionally source-linked so board-specific
plans can be audited as more manufacturers are added.

## Training source and safety

The Metolius plan follows the published ten-minute sequence format and uses the
official guidance around warm-up, open-hand grip, recovery, and secure
installation. The other plans are timer-and-hold-cue translations of the
linked research protocols or coaching methods; they are not a substitute for
individual programming or professional medical advice. Force-board plans use
the Compact II's 19 mm edge as a visual proxy, so use a calibrated force board
when following the study's percentage targets. Verify every hold against the
physical board before training.

Evidence overview:
https://pmc.ncbi.nlm.nih.gov/articles/PMC9806751/

- Metolius Wood Grips II Training Board:
  https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards
- Metolius Contact Training Guide:
  https://www.metoliusclimbing.com/pages/contact-training-guide
- Metolius Training Board Manual:
  https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826
