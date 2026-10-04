#!/bin/zsh
set -euo pipefail
phase="$1"
shift
case "$phase" in red|red-timeline|normal-monotonic|green|candidate2|candidate3|candidate4) ;; *) exit 2;; esac
scratch="$PWD/.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02/highlight-regression/$phase"
result="$scratch/tests-placid-badger-cad-second-half.xcresult"
cleanup() {
 rtk proxy rm -rf "$result"
 rtk proxy python3 - "$result" "$scratch/cleanup.json" <<'VERIFY'
from pathlib import Path
import sys,json
p,out=sys.argv[1:];d={'exactResultBundle':p,'deleted':not Path(p).exists()};Path(out).write_text(json.dumps(d,indent=2)+'\n');assert d['deleted']
VERIFY
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rtk proxy mkdir -p "$scratch"
rtk proxy python3 - "$result" "$scratch/ownership.json" <<'OWN'
from pathlib import Path
import sys,json
p,out=sys.argv[1:];Path(out).write_text(json.dumps({'owner':'placid-badger-cad-second-half','exactResultBundle':p,'cleanup':'EXIT INT TERM trap before creation'},indent=2)+'\n')
OWN
rtk proxy python3 .context/placid-badger-cad-second-half/zlagboard-evo/prep/highlight-regression.py "$phase" "$@"
