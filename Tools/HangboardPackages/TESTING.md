# Testing the hangboard package validator

Install the development dependencies in the repository-local validator
environment, then run the package tests:

```sh
python3 -m venv .context/hangboard-packages-venv
.context/hangboard-packages-venv/bin/python -m pip install \
  -e 'Tools/HangboardPackages[dev]'
.context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests -q
```

Exercise direct discovery through both read-only commands:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
scripts/hangboard-packages.sh status --root Hangboards
```

The final-inventory check succeeds only when all direct-child packages are
complete and schema-valid. Status prints the same validated package inventory
without requiring the inventory to be final.
