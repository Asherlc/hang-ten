# Beastmaker contact specification corrections

Reviewed 2026-10-01. Applies to the existing tulipwood Beastmaker 1000 and 2000 packages, preserving their board/revision/contact IDs. The user requested independent research, explicitly included non-manufacturer sources, supplied the numbered diagrams and Lesti SVG, and authorized corrections. Secondary measurements are used deliberately rather than represented as manufacturer-certified specifications.

## Sources and caveats

- **L1000**: [Gordon Lesti's measurement article](https://gordonlesti.com/measuring-the-beastmaker-1000-hold-depth/), [original SVG](https://gordonlesti.com/media/post/measuring-the-beastmaker-1000-hold-depth/beastmaker1000.svg). Firsthand ruler measurements of one board, published 2024-01-07; not factory tolerances. Labels and declared SVG positions were inspected directly.
- **D1000 / D2000**: [Numbered hold guides](https://thehangboard.com/pages/beastmaker-1000-vs-2000). The user supplied both images. Commercial competitor, unstated measurement methodology; used for named contact types, capacities and approximate depth corroboration. Its whole-product comparison contains errors and is not accepted as a general specification source.
- **C2000**: [ClimbersZone product and annotated drawing](https://climberszone.com/hangboards/579-beastmaker-2000.html), [drawing](https://climberszone.com/1663-large_default/beastmaker-2000.jpg). Explicit positional depths, sloper angles, sloping pockets and incut center. Retailer evidence with unstated measurement provenance.
- **R**: [Owner/caliper compilation](https://www.reddit.com/r/climbharder/comments/cek236/beastmaker_1000_and_2000_edgehold_sizes/). Different specimens and measurement conventions. Corroborates common working depths and two-tier back-two pockets; does not establish factory-exact dimensions.
- **M1000 / M2000**: [Original 1000](https://www.beastmaker.co.uk/collections/fingerboards/products/beastmaker-1000-series), [original 2000](https://www.beastmaker.co.uk/products/beastmaker-2000-series). Nominal descriptions and inventory. 1000 says 10 mm small pockets; 2000 center edge is printed “22m”, interpreted as nominal 22 mm with an explicit unit-typo caveat.
- **DIM1000**: [Climb On Equipment](https://climb-on-equipment.shoplightspeed.com/beastmaker-hangboard-1000-series.html). Original 1000 dimensions 580 × 150 × 58 mm; avoids relying on M1000's suspect 5 mm last dimension or assuming a beech revision is identical.

## Measurement decisions

1000 uses L1000's measured upper outer 15 mm and center 53 mm values. Existing matching depths stay. M1000's nominal 10 mm is retained here as an explicit disagreement; it is not described as a typo or proven physical error. No unsupported explanation for the difference is asserted.

2000 preserves nominal 22 mm for the central edge because M2000 names it, despite D2000's 20 mm and C2000's 23 mm. Other owner measurements differ too. The sloping mono's existing 55 mm is retained as corroborated by R/D2000; C2000's 45 mm disagrees. These represent approximate contact-depth labels, not a common certified measurement plane.

The back-two pockets already have separate native bound contacts: `front-middle-3` / `front-middle-7` for the 35 mm portions and `hold-26` / `hold-27` for their 50 mm portions. The existing descriptor places each pair in the corresponding left/right pocket region. Rename these portions explicitly instead of encoding a continuous 35–50 mm range or adding new contacts. Source: D2000/R/C2000's two-depth description. This corrects the earlier research report's mistaken speculation that hold-26/27 were unexplained rear contacts.

The sources use both “edge” and “pocket” for the 1000 upper three-finger holds; preserve their established edge kind and use the supplied D1000 terminology. Add directly stated finger capacities. Do not add grip prescriptions, pairing, side metadata, or training-plan cues.

Sloping and incut distinctions are explicit in names; the 2000 center also receives supported `shape=incut`. Top sloper names use the drawing's positional 45°/35°/20° map. No sloper geometry is inferred from pixels.

## Field-by-field changes

Names include existing depths where those values are corroborated; the audit above states their limits. The following table lists every changed factual field, including optional capacity and naming changes.

### beastmaker-1000

| Contact / field | Before | After | Source mapping |
| --- | --- | --- | --- |
| Board dimensions | 580 × 150 mm | 580 × 150 × 58 mm | DIM1000 |
| pocket-top-outer-left / name | "10 mm 4 Finger Edge Left" | "15 mm 4 Finger Edge Left" | D1000; L1000 for depth |
| pocket-top-outer-left / depth | {"range": {"minimum": 10, "maximum": 10}} | {"range": {"minimum": 15, "maximum": 15}} | D1000; L1000 for depth |
| pocket-top-outer-left / fingerCapacity | null | 4 | D1000; L1000 for depth |
| pocket-top-outer-right / name | "10 mm 4 Finger Edge Right" | "15 mm 4 Finger Edge Right" | D1000; L1000 for depth |
| pocket-top-outer-right / depth | {"range": {"minimum": 10, "maximum": 10}} | {"range": {"minimum": 15, "maximum": 15}} | D1000; L1000 for depth |
| pocket-top-outer-right / fingerCapacity | null | 4 | D1000; L1000 for depth |
| pocket-top-left / fingerCapacity | null | 3 | D1000; L1000 for depth |
| pocket-top-right / fingerCapacity | null | 3 | D1000; L1000 for depth |
| pocket-middle-outer-left / name | "Pocket Middle Outer Left" | "45 mm 4 Finger Edge Left" | D1000; L1000 for depth |
| pocket-middle-outer-left / fingerCapacity | null | 4 | D1000; L1000 for depth |
| pocket-middle-mid-left / name | "Pocket Middle Mid Left" | "50 mm 2 Finger Deep Pocket Left" | D1000; L1000 for depth |
| pocket-middle-inner-left / name | "Pocket Middle Inner Left" | "45 mm 3 Finger Deep Pocket Left" | D1000; L1000 for depth |
| pocket-middle-center / name | "50 mm 4 Finger Edge Center" | "53 mm 4 Finger Edge Center" | D1000; L1000 for depth |
| pocket-middle-center / depth | {"range": {"minimum": 50, "maximum": 50}} | {"range": {"minimum": 53, "maximum": 53}} | D1000; L1000 for depth |
| pocket-middle-center / fingerCapacity | null | 4 | D1000; L1000 for depth |
| pocket-middle-inner-right / name | "Pocket Middle Inner Right" | "45 mm 3 Finger Deep Pocket Right" | D1000; L1000 for depth |
| pocket-middle-mid-right / name | "Pocket Middle Mid Right" | "50 mm 2 Finger Deep Pocket Right" | D1000; L1000 for depth |
| pocket-middle-outer-right / name | "Pocket Middle Outer Right" | "45 mm 4 Finger Edge Right" | D1000; L1000 for depth |
| pocket-middle-outer-right / fingerCapacity | null | 4 | D1000; L1000 for depth |
| pocket-bottom-outer-left / name | "Pocket Bottom Outer Left" | "20 mm 4 Finger Edge Left" | D1000; L1000 for depth |
| pocket-bottom-outer-left / fingerCapacity | null | 4 | D1000; L1000 for depth |
| pocket-bottom-mid-left / name | "Pocket Bottom Mid Left" | "25 mm 2 Finger Pocket Left" | D1000; L1000 for depth |
| pocket-bottom-inner-left / name | "Pocket Bottom Inner Left" | "20 mm 3 Finger Pocket Left" | D1000; L1000 for depth |
| pocket-bottom-inner-right / name | "Pocket Bottom Inner Right" | "20 mm 3 Finger Pocket Right" | D1000; L1000 for depth |
| pocket-bottom-mid-right / name | "Pocket Bottom Mid Right" | "25 mm 2 Finger Pocket Right" | D1000; L1000 for depth |
| pocket-bottom-outer-right / name | "Pocket Bottom Outer Right" | "20 mm 4 Finger Edge Right" | D1000; L1000 for depth |
| pocket-bottom-outer-right / fingerCapacity | null | 4 | D1000; L1000 for depth |

### beastmaker-2000

| Contact / field | Before | After | Source mapping |
| --- | --- | --- | --- |
| top-sloper-1 / name | "Top Sloper 1" | "45 Degree Sloper Left" | C2000; M2000 angles |
| top-sloper-2 / name | "Top Sloper 2" | "35 Degree Sloper Left" | C2000; M2000 angles |
| top-sloper-3 / name | "Top Sloper 3" | "20 Degree Center Sloper" | C2000; M2000 angles |
| top-sloper-4 / name | "Top Sloper 4" | "35 Degree Sloper Right" | C2000; M2000 angles |
| front-upper-1 / name | "Front Upper 1" | "40 mm 3 Finger Pocket Left" | D2000 / R |
| front-upper-2 / name | "Front Upper 2" | "20 mm 3 Finger Pocket Right" | D2000 / R |
| front-middle-1 / name | "Front Middle 1" | "33 mm 4 Finger Edge Left" | D2000 / R |
| front-middle-1 / fingerCapacity | null | 4 | D2000 / R |
| front-middle-2 / name | "Front Middle 2" | "55 mm Sloping Mono Left" | C2000 / M2000 profile; R / D2000 depth |
| front-middle-3 / name | "Front Middle 3" | "35 mm Back 2 Pocket Shallow Portion Left" | D2000 / R |
| front-middle-4 / name | "Front Middle 4" | "30 mm 2 Finger Pocket Left" | D2000 / R |
| front-middle-5 / fingerCapacity | null | 4 | D2000 / R |
| front-middle-6 / name | "Front Middle 6" | "30 mm 2 Finger Pocket Right" | D2000 / R |
| front-middle-7 / name | "Front Middle 7" | "35 mm Back 2 Pocket Shallow Portion Right" | D2000 / R |
| front-middle-8 / name | "Front Middle 8" | "55 mm Sloping Mono Right" | C2000 / M2000 profile; R / D2000 depth |
| front-middle-9 / name | "Front Middle 9" | "33 mm 4 Finger Edge Right" | D2000 / R |
| front-middle-9 / fingerCapacity | null | 4 | D2000 / R |
| front-lower-1 / name | "Front Lower 1" | "15 mm 4 Finger Edge Left" | D2000 / R |
| front-lower-1 / fingerCapacity | null | 4 | D2000 / R |
| front-lower-2 / name | "Front Lower 2" | "25 mm Mono Left" | D2000 / R |
| front-lower-3 / name | "Front Lower 3" | "20 mm 2 Finger Pocket Left" | D2000 / R |
| front-lower-4 / name | "Front Lower 4" | "20 mm Sloping 2 Finger Pocket Left" | C2000 / M2000 profile; R / D2000 depth |
| front-lower-5 / name | "22 mm Center Edge" | "22 mm Incut 4 Finger Edge Center" | M2000 nominal depth; C2000 incut; D2000 capacity |
| front-lower-5 / fingerCapacity | null | 4 | M2000 nominal depth; C2000 incut; D2000 capacity |
| front-lower-5 / shape | null | "incut" | M2000 nominal depth; C2000 incut; D2000 capacity |
| front-lower-6 / name | "Front Lower 6" | "20 mm Sloping 2 Finger Pocket Right" | C2000 / M2000 profile; R / D2000 depth |
| front-lower-7 / name | "Front Lower 7" | "20 mm 2 Finger Pocket Right" | D2000 / R |
| front-lower-8 / name | "Front Lower 8" | "25 mm Mono Right" | D2000 / R |
| front-lower-9 / name | "Front Lower 9" | "15 mm 4 Finger Edge Right" | D2000 / R |
| front-lower-9 / fingerCapacity | null | 4 | D2000 / R |
| hold-26 / name | "Hold 26" | "50 mm Back 2 Pocket Deep Portion Left" | D2000 / R |
| hold-27 / name | "Hold 27" | "50 mm Back 2 Pocket Deep Portion Right" | D2000 / R |
| hold-28 / name | "Hold 28" | "45 Degree Sloper Right" | C2000; M2000 angles |

## Validation

The [2026-10-06 capacity audit](2026-10-06-finger-capacity.md) adds reviewed
four-finger estimates to the previously unspecified jugs and slopers. The
Beastmaker 1000 source hash in `Tools/HangboardCAD/display_depth_audits.json`
was refreshed for that manifest-only edit. All geometry bytes and the reviewed
metadata/display depth differences remain unchanged.

The supported `set_board_manifest.py` rewrites only the native metadata. Compared every FCStd archive member against the pre-change copies: only Document.xml differs; all CAD shape members are byte-identical. Presentations, descriptors, model assets and contact bindings stay unchanged. No generated board.json is committed.

Package validation and catalog status pass for all 66 packages with no drafts. iOS build, contact resolution/recording tests and screenshots are recorded after execution below.

Executed `python3 -m pytest Tools/HangboardPackages/tests/test_complete_catalog_source_audit.py Tools/HangboardPackages/tests/test_board_package_staging.py -q`: **40 passed**. Existing catalog-dimension and contact-selection/cue expectations were updated to the corrected facts.

iOS Debug builds succeeded with `xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=<owned UUID>' -derivedDataPath .context/DerivedData build` on iPhone 17 Pro / iOS 26.5 and 26.3. Owned device names were `Hang Ten Paseo spiteful-fox Review`; exact UUIDs are retained in workspace validation logs.

The requested `-only-testing:HangTenTests/ContactResolverTests -parallel-testing-enabled NO test` runs compiled but did not execute assertions: simulator install/launch services stalled. Restarting the first owned device aborted that launch with Mach IPC error -308. The alternate runtime also stalled before tests started, and its screenshot service timed out after 15 seconds. Both test launch attempts were stopped. No screenshots or successful Swift test execution are claimed. CAD geometry and model bindings were proven unchanged at the archive-member level; app visual review remains unverified because of this simulator limitation.
