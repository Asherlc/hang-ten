# Testing the vendored pipeline

Install the development extra in a repository-local environment, then run the
complete pipeline and Workbench suites:

```sh
.context/hangboard-onboarding-venv/bin/python -m pip install \
  -e 'Tools/HangboardPipeline[dev]'
.context/hangboard-onboarding-venv/bin/python -m pytest \
  Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
```

Validate the canonical package registry and exercise approved-package staging
without writing into the app source tree:

```sh
scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
.context/hangboard-onboarding-venv/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_generated_catalog_import.py -q
destination="$(mktemp -d)/Hangboards"
.context/hangboard-onboarding-venv/bin/python \
  scripts/stage-approved-board-packages.py \
  --repository-root . \
  --destination "$destination"
```

The generated experimental catalog and its Swift/JSON exporters were retired.
Draft packages remain review inventory only; only registry entries with
`status: approved` are staged into an app resource destination.
