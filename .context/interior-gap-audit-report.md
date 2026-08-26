# Interior-gap transparency audit

Date: 2026-08-24

Branch: `add-changeable-editor-backgrounds`

Pipeline: pinned `rembg` U-2-Net mask followed by package-specific,
four-connected, source-RGB-bounded correction fills.

## Root cause and correction contract

`Tools/HangboardPackages/scripts/remove_primary_backdrops.py` applied an
enclosed-background correction only to four manually named packages. Any
reviewed background opening not represented in `_ENCLOSED_BACKGROUND_SEEDS`
was left to the model mask and could remain opaque.

The correction remains deliberately narrow: each seed expands only through
four-connected pixels whose three RGB channels remain within 12 levels of the
seed sample, and each individual fill is capped at 100,000 visited pixels. No
global or broad white-keying was added.

## Complete audited seed inventory

The following 19 seeds are the complete configuration after this change.
Seeds marked **new** were added in this audit; the others were retained from
the preceding reviewed correction.

| Package | Seed(s) | Reviewed background opening |
| --- | --- | --- |
| `beastmaker-1000` | `(215, 10)`, `(785, 10)` **new** | left and right top background cutouts; already mostly transparent in the model mask, now deterministic and with remaining partial-alpha backdrop cleared |
| `soill-iron-palm-2` | `(768, 425)`, `(768, 530)`, `(768, 635)` **new** | three background openings between the horizontal rails |
| `soill-training-tiles` | `(500, 450)` **new** | retained background in the left tile's upper interior opening; the mirrored right opening was already transparent |
| `tension-grindstone` | `(887, 443)` | centre window |
| `trango-rock-prodigy-pivot` | `(590, 310)`, `(710, 310)`, `(1055, 310)`, `(1180, 310)` **new** | narrow and wide upper handle openings on both halves |
| `yy-travelboard` | `(190, 625)`, `(1348, 625)` | left and right circular mounting holes |
| `yy-verticalboard-evo` | `(887, 500)` | centre handle opening |
| `yy-verticalboard-one` | `(887, 500)` **new** | centre handle opening |
| `yy-penta-evo` | `(145, 595)`, `(1385, 595)`, `(180, 720)`, `(1355, 720)` | both circular and both lower slot openings |

The test fixture pairs every configured seed with a retained physical-surface
pixel, so a broken configured fill or one that crosses onto the named surface
fails the focused regression.

## Visual evidence and 44-board review

Dark-background contact sheets before correction:

- `.context/interior-gap-contact-sheets-before/interior-gaps-before-01.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-02.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-03.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-04.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-05.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-06.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-07.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-08.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-09.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-10.png`
- `.context/interior-gap-contact-sheets-before/interior-gaps-before-11.png`

Dark-background contact sheets after the complete rembg-plus-correction rerun:

- `.context/interior-gap-contact-sheets-after/interior-gaps-after-01.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-02.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-03.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-04.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-05.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-06.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-07.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-08.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-09.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-10.png`
- `.context/interior-gap-contact-sheets-after/interior-gaps-after-11.png`

Sheet coverage, in sorted package order:

1. Beastmaker 1000, Beastmaker 2000, DeWoodstok Woodbord, Escape Beta 22.
2. Escape Unlimited, Evolv Kilter Basic Long, Frictitious DoorMount Pro 7,
   Frictitious Megalith.
3. Lattice Triple Rung, Metolius Climbers Edge, Metolius Contact, Metolius
   Foundry.
4. Metolius Light Rail 2, Metolius Prime Rib, Metolius Project, Metolius Rock
   Rings 3D.
5. Metolius Simulator 3D, Metolius Wood Grips Compact II, Metolius Wood Grips
   Deluxe II, Moon Armstrong.
6. Nature Stoāk Board III, So iLL Iron Palm 2, So iLL Split Palm, So iLL
   Training Tiles.
7. target10a Linebreaker BASE, Tension Flash Board, Tension Grindstone,
   Tension Honestone.
8. Tension Whetstone, The Hangboard, Trango Rock Prodigy Forge, Trango Rock
   Prodigy Natural.
9. Trango Rock Prodigy Pivot, Trango Rock Prodigy Training Center, YY
   Baguette, YY Baguette Evo.
10. YY Penta Evo, YY TravelBoard, YY VerticalBoard Evo, YY VerticalBoard First.
11. YY VerticalBoard Light, YY VerticalBoard One, Zlagboard Evo, Zlagboard Pro.

Original-resolution dark composites and coordinate-grid evidence exist for
each new package in both of these directories:

- `.context/interior-gap-details-before/`
- `.context/interior-gap-details-after/`

The reviewed files are `beastmaker-1000.png`, `soill-iron-palm-2.png`,
`soill-training-tiles.png`, `trango-rock-prodigy-pivot.png`, and
`yy-verticalboard-one.png`, plus each corresponding `-grid.png` coordinate
overlay.

All 11 post-run sheets were inspected. The selected gaps show the dark
background. Physical surfaces and pocket floors remain present, as do
lettering/detail, mounting hardware, ropes, intentional shadows, and separated
board pieces.

## TDD red/green evidence

Focused RED command, run before changing the seed map:

```sh
.context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_remove_primary_backdrops.py::test_known_enclosed_background_fixtures_clear_only_the_named_through_holes -q
```

Result against the old four-package map: `11 failed, 8 passed`. Each of the 11
new seed cases failed because its reviewed opening remained alpha 255 in the
controlled opaque-mask fixture.

The same focused command after the minimal map expansion produced:
`19 passed in 1.81s`.

Fresh full package-tool suite:

```text
143 passed in 5.93s
```

## Reprocessing and byte-level asset audit

All 44 `assets/primary.png` files were passed through the pinned U-2-Net model
and the correction function in one sorted run with one model session. Only the
five newly configured packages differed from the pre-fix committed assets;
all changes were reductions in alpha:

| Package | Alpha pixels cleared from pre-fix asset | Dimensions |
| --- | ---: | --- |
| `beastmaker-1000` | 1,158 | 1000 × 259 |
| `soill-iron-palm-2` | 125,144 | 1536 × 1024 |
| `soill-training-tiles` | 24,485 | 1536 × 1024 |
| `trango-rock-prodigy-pivot` | 18,532 | 1774 × 887 |
| `yy-verticalboard-one` | 18,838 | 1774 × 887 |

`.context/interior-gap-asset-audit.json` records every board's dimensions,
RGB SHA-256, alpha counts, and alpha delta. The audit compared every current
asset against both the original pre-transparency source at `a0a26eb8^` and the
pre-fix `HEAD` version and confirmed:

- 44 of 44 dimensions are unchanged;
- 44 of 44 decoded RGB planes are byte-identical to the base source and
  pre-fix asset;
- every primary contains both fully transparent and retained pixels;
- no pixel became more opaque;
- every `Hangboards/*/board.json` is byte-identical to `HEAD`.

## Package validation

Fresh commands:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
scripts/hangboard-packages.sh status --root Hangboards
git diff --check
```

Results: both package commands reported 44 complete boards and zero drafts;
`git diff --check` produced no errors.
