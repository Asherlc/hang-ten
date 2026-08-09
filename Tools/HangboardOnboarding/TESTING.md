# Testing the vendored pipeline

Install the development extra in the repository-local environment, then run
the self-contained suite:

```sh
.context/hangboard-onboarding-venv/bin/python -m pip install \
  -e 'Tools/HangboardOnboarding[dev]'
.context/hangboard-onboarding-venv/bin/python -m pytest \
  Tools/HangboardOnboarding/tests -q
scripts/hangboard-tools.sh benchmark
```

The imported project also had eight legacy test modules coupled to roughly
200 MB of mutable `work/real-beastmaker/**` directories outside the Python
package. Several assertions were already stale at upstream commit `ce08eb9`.
Those modules are not vendored. Their durable accepted-product behavior is
covered here by the versioned Metolius run and its fail-closed, zero-call
Stage 2 through Stage 4 parity benchmark.

## Catalog outline generation checks

Generate the full product-image outline catalog and review overlays with:

```sh
.context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli \
  --source-dir docs/hangboard-generative-catalog \
  --output-dir docs/hangboard-generative-catalog/outlines \
  --review-dir .context/hardboard-outlines/reviews
```

Then validate the committed catalog set and the CLI contract:

```sh
.context/hangboard-onboarding-venv/bin/python -m pytest \
  Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py -q
.context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli \
  --source-dir docs/hangboard-generative-catalog \
  --output-dir docs/hangboard-generative-catalog/outlines \
  --check
```

The catalog test expects the source image set and output JSON stems to match
exactly, excluding `contact-sheet-primary.png`. It also checks that each
document points back to the correct PNG, preserves the advisory
manufacturer-reference table, keeps every path and `bounds` value normalized,
and matches the source image canvas dimensions.

Because the detector emits approximate hold semantics, the generated JSON and
review overlays must be visually inspected before runtime use. The overlay PNGs
in `.context/hardboard-outlines/reviews` are the review artifact of record for
wide, square, and other representative board layouts.
