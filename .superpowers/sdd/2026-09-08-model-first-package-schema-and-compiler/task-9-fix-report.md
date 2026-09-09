# Task 9 documentation fix

## Result

Clarified `Tools/HangboardModels/README.md:17-20` so the raster contract
explicitly says canonical raster presentations collectively own every logical
hold exactly once and form an exact, single-owner partition. This preserves
the schema-v2 rule that a hold inventory may be partitioned across multiple
original raster presentations.

The checked-in `captain-fingerfood-dual` fixture confirms the rule: `primary`
owns `straight-edge-20` and `outer-jug`, while `reverse` owns
`curved-edge-20`.

No package, application, geometry, generator, or other documentation files
were changed. The pre-existing untracked
`Tools/HangboardModels/beastmaker_1000.py` remains untouched.

## Verification

- `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed: 61 complete packages, `drafts: []`.
- `rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest Tools/HangboardPackages/tests Tools/HangboardModels/test_evidence_packet.py Tools/HangboardModels/test_model_descriptor.py -q`
  passed: 532 tests.
- `rtk git diff --check` passed with no output.

No persistent resources were created.
