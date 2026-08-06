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
