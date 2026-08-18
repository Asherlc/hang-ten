# Testing the vendored pipeline

Install the development extra in a repository-local environment, then run the
complete pipeline and Workbench suites:

```sh
.context/hangboard-onboarding-venv/bin/python -m pip install \
  -e 'Tools/HangboardPipeline[dev]'
.context/hangboard-onboarding-venv/bin/python -m pytest \
  Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
```

Validate direct-child packages and exercise package staging
without writing into the app source tree:

```sh
scripts/hangboard-tools.sh packages validate --root Hangboards
.context/hangboard-onboarding-venv/bin/python -m pytest \
  Tools/HangboardPipeline/tests/test_generated_catalog_import.py -q
stage_root="$(mktemp -d)"
TARGET_BUILD_DIR="$stage_root"
UNLOCALIZED_RESOURCES_FOLDER_PATH="HangTen.app"
destination="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/Hangboards"
TARGET_BUILD_DIR="$TARGET_BUILD_DIR" \
UNLOCALIZED_RESOURCES_FOLDER_PATH="$UNLOCALIZED_RESOURCES_FOLDER_PATH" \
.context/hangboard-onboarding-venv/bin/python \
  scripts/stage-board-packages.py \
  --repository-root . \
  --destination "$destination"
```

The generated experimental catalog and its Swift/JSON exporters were retired.
Complete direct-child packages are validated and staged into the app resource
destination. Imported primary-only boards remain migration drafts until they
satisfy the complete package contract.
