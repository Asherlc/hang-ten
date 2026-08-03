#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
exec "$script_dir/conductor-resource-cleanup.sh" archive
