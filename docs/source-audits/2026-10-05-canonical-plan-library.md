# Canonical plan library

`HangTen/Resources/PlanLibrary.json` is the checked-in plan source. Edit the
canonical JSON and retain a source mapping for every changed prescription or
classification, following [routine authoring](../ADDING_A_ROUTINE.md).
`PlanStorage.swift` decodes and validates the bundled document; missing or
invalid data fails explicitly. Both the timer and workout history consume its
expanded intervals.

The library retains 45 plans and 24 distinct source URLs, represented by
415 reusable blocks, 489 stored step definitions and 103 declared repeat
references. Its 779,793-byte canonical document has SHA-256
`4a4fb9125448d3248404b7f86d358d386b032cb01a2f115e82cda0960b975bbf`.

A block contains one prescription pattern; a plan reference's `repeatCount`
is its total run count, including the first. Optional `stepIDs` can contain one
pattern of ID stems (which receive `-1`, `-2`, etc. when repeated) or the entire
expanded sequence of exact historic IDs. Optional `stepTitles` can contain one
pattern or the complete expanded sequence of original occurrence labels.
Expanded overrides follow run order, then step order within each run. Omitted
overrides retain the template's ID/title behavior. Existing documents without
these fields continue to decode.

Only explicit position labels are factored out of template display titles.
Original titles remain in the reference overrides. Meaningful numbers such as
hold sizes and exercise counts, optional qualifiers, instructions, accessory
text, durations, ordered hand targets, grip/finger cues and work/rest segments
remain part of the prescription. A final effort or recovery with different
content uses its own reference. These template labels are presentation
adaptations; they do not replace the original sourced occurrence labels used
in workout execution.

The resolver retains the declared repeats as ranges over expanded runtime
steps, with their template display labels. Plan previews render those ranges
directly; they do not search for matching prescriptions or rewrite counters.
Equal steps without an authored repeat remain separate. Board-specific
max-hang selections retain the same repetition structure. Custom copies retain
the authored pattern and count as editable ranges instead of storing every
occurrence; their template captions are the same labeled presentation adaptations.

For canonical authoring, `scripts/deduplicate-plan-library.py` factors repeated
prescriptions and reuses identical blocks. It preserves plan order, metadata,
board restrictions and every expanded source field, and verifies exact
before/after expansion before `--write`. `--check` verifies idempotence;
`--against <previous-library.json>` verifies an earlier audited representation.
It is an authoring tool, not a runtime fallback. Adding a new source or changing
any prescription still requires the source audit in the routine authoring guide.

The 14 additional published presets and their source-specific adaptations are
covered by the [training-plan source audit](../TRAINING_PLAN_SOURCE_AUDIT_2026-10-05.md).
The 19 optional focus classifications are editorial adaptations covered by the
[workout chooser classification audit](../WORKOUT_CHOOSER_CLASSIFICATION_AUDIT_2026-10-05.md).
Neither block factoring nor template labels change those classifications,
source URLs, provenance labels or adaptation disclosures.

The source-prescription mappings below cover the same expanded content as
revision `07b9127`. Each fingerprint hashes the canonical sorted JSON for a
plan's ID, metadata, optional board ID and fully expanded original source
steps, before runtime segment normalization. It includes the complete original
step identities and labels as well as all prescription fields. Independent
native regression tests pin these fingerprints; existing prescription tests
continue to inspect source boundaries and resulting runtime assignments.

| Plan | Source | Expanded source steps | SHA-256 |
| --- | --- | ---: | --- |
| `metolius.generic-ten-minute.entry` | [Source](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | 20 | `bd9f18db936973141f29cd2dee2d1be6ee04bcef0f26c723216cf9b1a268f356` |
| `metolius.generic-ten-minute.intermediate` | [Source](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | 26 | `ce8f12f205768a621d7306fa054a5621bab39899583f51a0ba4cda6c4a9b8fe1` |
| `metolius.generic-ten-minute.advanced` | [Source](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | 27 | `f3ec308e3f128b9ef43e4f5b37124cebd966f5292e5332075e3a46d2282c65b6` |
| `metolius.contact.entry` | [Source](https://www.metoliusclimbing.com/pages/contact-training-guide) | 10 | `a5ebd0328577f58c127e15cf222934ba89d29895762c1b7a3a5cde3abd3b078c` |
| `metolius.contact.intermediate` | [Source](https://www.metoliusclimbing.com/pages/contact-training-guide) | 10 | `1297a76f9eefb94b967e5b1929ee96a63edc82c18389066f9a2c9fd069f28121` |
| `metolius.contact.advanced` | [Source](https://www.metoliusclimbing.com/pages/contact-training-guide) | 10 | `0da2a63e7fd843ec412e605ada037d224ca3ffbeecc141b8c7d0345d5afdd04d` |
| `metolius.simulator-3d.entry` | [Source](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | 10 | `a8529c7ca3daa0d5928795477dc5511367252d83540d228f26e7d494a705b8a7` |
| `metolius.simulator-3d.intermediate` | [Source](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | 10 | `793f860f0212e55c71cf743da65ec19f3d5459c74fc59ea41bf55e2c51bd068e` |
| `metolius.simulator-3d.advanced` | [Source](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | 10 | `fae59a3a6afd418a465af41a99283ad18c1ca867feb846cb0b88b3f8b331a542` |
| `metolius.rock-rings.ten-minute` | [Source](https://www.metoliusclimbing.com/pages/rock-ring-training-guide) | 10 | `af137d7aeed7706bb79174cf298a853be0559acd69bdcd3b11df3a0cc1a9a003` |
| `rptc.seven-three-repeaters` | [Source](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) | 8 | `24ad51f906cb766a6d72aa7530c4d665a64a3e9e9aa568eac01907f995efc819` |
| `research.max-hangs` | [Source](https://en-eva-lopez.blogspot.com/2018/05/fingerboard-training-guide-II-Maxhangs-SubHangs-and-Inthangs-methodology.html) | 5 | `0ac1426de92362319e028d6ae39bdc6eefa501f1f121455e2db4f56d098e875c` |
| `research.force-feedback-f80` | [Source](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | 38 | `d6d415aeb5a3e89aa16efc9f81c81c45fe945d8c17b7ff29e7e8256ce751bb66` |
| `research.force-feedback-f100` | [Source](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | 24 | `31dac2f62ae6f91db25db14bab22c747d3a21f8a770e4238989ed74362b20375` |
| `research.eva-int-hangs` | [Source](https://pubmed.ncbi.nlm.nih.gov/30988852/) | 17 | `30aa76b3ddcffbf3e4ca9becf4a29862535190786ecf98e04a3116a2a4ac88ee` |
| `research.seven-three-repeaters` | [Source](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full) | 95 | `3fda2dfbe46c33b325977c3b931ef0c1359a0208129db60a236786cd128a028e` |
| `research.megos-one-arm-7-3` | [Source](https://www.youtube.com/watch?v=urTeUObQlsg) | 53 | `069b713030fd32fbae5b5e47c2f1797fe1ed36a8da41d8282307b98fc76c8538` |
| `research.abrahangs` | [Source](https://www.youtube.com/watch?v=sBTI9qiH4UE) | 10 | `fbc3f6b6c5dbce69fcdaecd072e4f6d8e9206db051ff6fb97501d3fc84eebfd9` |
| `coach.horst-seven-fifty-three` | [Source](https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/) | 11 | `b351983dc8bd900680967c191dfc1c3b4ada7e9e9a0008c677fe62f7b4b6b87e` |
| `coach.bechtel-three-six-nine` | [Source](https://www.powercompanyclimbing.com/blog/2016/01/episode-2-resistance-training-with.html) | 3 | `4ff3403811ccfb835dcf0929839af591296cd365c10613c59662af4ebff2adc7` |
| `coach.density-hangs` | [Source](https://www.trainingbeta.com/the-simplest-finger-training-program/) | 7 | `f080de85b989211942e260e2c7809bd80bd9c49ae8525973b0a4bb87d3dc9bcf` |
| `coach.nelson-density-hangs.expert` | [Source](https://www.trainingbeta.com/the-simplest-finger-training-program/) | 17 | `fcf17ad7e5614d8a2a2ec9cc03abf8e8437d52388a41569294e25e233dfa25e6` |
| `coach.nelson-recruitment-pulls.beginner` | [Source](https://www.trainingbeta.com/the-simplest-finger-training-program/) | 23 | `4c251749aa7ce0e206c136737c0bb7d60b3942a250d45a1f1099f2cb6a50937b` |
| `coach.nelson-recruitment-pulls.expert` | [Source](https://www.trainingbeta.com/the-simplest-finger-training-program/) | 31 | `25f752f28ef109633b45df3e3ada5660e11409872c4c4c6addb8dda746c3f65d` |
| `coach.nelson-velocity-pulls.beginner` | [Source](https://www.trainingbeta.com/the-simplest-finger-training-program/) | 7 | `bc9249693745a8d0e5de9cfa72f53b5762d30576bb9d9be3851094039890a868` |
| `coach.nelson-velocity-pulls.expert` | [Source](https://www.trainingbeta.com/the-simplest-finger-training-program/) | 39 | `4f9621797f2eb70c13c7510089cb421ad183aef790d0aca91d944c132bee7a24` |
| `device.zlagboard-sixty-sixty` | [Source](https://strengthclimbing.com/zlagboard-forearm-endurance-workout/) | 10 | `d8871c8cd3daee20f23971cd66dcb84e1f659c35c62a8a9ddfd4cda9f36c711e` |
| `hoopers-beta.introductory-home-hangboard` | [Source](https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine) | 66 | `026dee2d886fc512058fc9da60f67b0f6ed5c17a747b375554c02bf4d65948b8` |
| `method.intermediate-hangboarding.repeaters` | [Source](https://methodclimb.com/intermediate-hangboarding/) | 29 | `c73ed40bf148696078eec86abc58c1d49b4a62b9da48b5ab922501f45ab8b909` |
| `method.intermediate-hangboarding.emom` | [Source](https://methodclimb.com/intermediate-hangboarding/) | 10 | `c3c7e62acada655428406089987a82133adf257aefddd92d4209ee0ae68e5d65` |
| `rei.hangboard-sample-workout` | [Source](https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html) | 36 | `a9dba5b4b5d7d3ecb2afce4ae286aabc6e4da9da698d99a47d4e675ef1408c6c` |
| `beastmaker-max-hangs` | [Source](https://www.beastmaker.co.uk/pages/training) | 5 | `7f4acb218324ccde1dc13aa07638dc29c0e3462281cabc0c1f90c6294918f026` |
| `beastmaker-repeaters` | [Source](https://www.beastmaker.co.uk/pages/training) | 13 | `beacdd2227bab852a5b3825a53947df2ec305efcd926b5fe1743ba1cd6fd7a91` |
| `tension-6-and-10` | [Source](https://tensionclimbing.com/blogs/blog/hangboarding-a-way) | 43 | `1b395c05eb721a15177477b27269f18279e4a01d5cd8c5c176b74848a28b264d` |
| `tension-6-6-6-plus` | [Source](https://tensionclimbing.com/blogs/blog/hangboarding-a-way) | 7 | `6c532322e23274b389769dc275af35161fa7f5e93446e2163622af8309f53463` |
| `tension-single-hangs` | [Source](https://tensionclimbing.com/blogs/blog/hangboarding-a-way) | 7 | `44c57d1915789b9198242d1df26ee77878fbb4184c65685a05741c33fa800abc` |
| `tension-long-hangs` | [Source](https://tensionclimbing.com/blogs/blog/hangboarding-a-way) | 5 | `0d8b02ccf1200ef454fc1f6259d694f9a512f3bc2cc79bafb455055ab0a314af` |
| `cameron-horst-two-handed-7-53` | [Source](https://trainingforclimbing.com/advanced-hangboard-training-technique/) | 17 | `e5ca641aa9a5724a85566cd8ea56e8e789c7830d3bd527d4483f85035d839e38` |
| `cameron-horst-one-arm` | [Source](https://trainingforclimbing.com/advanced-hangboard-training-technique/) | 14 | `badd8f6d9abadf4a06592a8b7b2daef5ba8db5844149fc5d2fa8a3f4d8385818` |
| `rei-hangboard-training-101` | [Source](https://www.rei.com/blog/uncategorized/hangboard-training-101) | 31 | `f7f505a1e1c96673ede1c74f3fab2ba761f63917131414d4252d214ffc8e5902` |
| `rock-prodigy.original-beginner` | [Source](https://rockclimberstrainingmanual.com/tools-for-rock-climbing-training/the-making-of-a-rock-prodigy/) | 35 | `6f2d1013077d583e7268b8b4e4ea2382db4344f1bc554c3d92994730b18b3298` |
| `rock-prodigy.rptc-intermediate` | [Source](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) | 97 | `3b8654fb3e13c1ba66821ed397491c7e8365adaf1e60e1f89cd307c91834eab9` |
| `rock-prodigy.original-advanced` | [Source](https://rockclimberstrainingmanual.com/tools-for-rock-climbing-training/the-making-of-a-rock-prodigy/) | 125 | `fd39b9ace30c97dfad1cf092d53bffbcf74dfaeaf6c84d83c1d21fde087acbb8` |
| `rock-prodigy.pivot-introductory` | [Source](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507) | 26 | `329429e47a09b10dfef40ff01f11b49a93f81d65ed3b322c1f46408bdffef163` |
| `rock-prodigy.pivot-intermediate` | [Source](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507) | 59 | `6d3c228cf46f04cbf5ebd3f517ab6540820271e2315d204a500a9f19ab324999` |
