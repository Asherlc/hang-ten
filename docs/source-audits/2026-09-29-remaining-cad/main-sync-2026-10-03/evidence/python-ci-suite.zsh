#!/bin/zsh
set -eu
trap 'rtk proxy python3 '/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger-cad-second-half/.context/placid-badger-cad-second-half/main-sync-2026-10-03/python-deps-cleanup.py'' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rtk proxy python3 '/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger-cad-second-half/.context/placid-badger-cad-second-half/main-sync-2026-10-03/python-ci-suite.py'
