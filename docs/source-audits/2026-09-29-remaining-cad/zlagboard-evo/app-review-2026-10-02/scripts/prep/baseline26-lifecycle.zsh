#!/bin/zsh
set -euo pipefail
workspace="$PWD"
owner=placid-badger-cad-second-half
old="$workspace/.context/$owner/zlagboard-evo/ios-resume-2026-10-02"
scratch="$workspace/.context/$owner/zlagboard-evo/ios-26-4"
products="$scratch/Products-$owner"
uuid=""
cleanup() {
 original_exit=$?
 trap - EXIT INT TERM
 rtk proxy python3 "$workspace/.context/$owner/zlagboard-evo/prep/baseline26-cleanup.py" "$uuid" "$products" "$scratch" || exit $?
 exit "$original_exit"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rtk proxy mkdir -p "$scratch"
rtk proxy python3 - "$scratch" "$products" <<'REGISTER'
from pathlib import Path
import json,sys
s,products=map(Path,sys.argv[1:]);(s/'ownership.json').write_text(json.dumps({'owner':'placid-badger-cad-second-half','simulator':None,'preservedProducts':str(products),'traps':'EXIT INT TERM installed before product copy and Simulator creation'},indent=2)+'\n')
REGISTER
rtk proxy ditto "$old/DerivedData-$owner/Build/Products/Debug-iphonesimulator/HangTen.app" "$products/HangTen.app"
rtk proxy python3 "$workspace/.context/$owner/zlagboard-evo/prep/baseline26-handoff.py" "$old" "$scratch" "$products"
uuid="$(rtk proxy xcrun simctl create "Hang Ten Paseo $owner Review Zlagboard Evo iOS26.4 Baseline20261002" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-4)"
[[ "$uuid" =~ '^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$' ]]
print -r -- "$uuid" >> "$workspace/.context/paseo-pending-simulators"
print -r -- "$uuid" >> "$workspace/.context/paseo-owned-simulators"
rtk proxy python3 - "$scratch" "$uuid" <<'UUID'
from pathlib import Path
import json,sys
s=Path(sys.argv[1]);uid=sys.argv[2];p=s/'ownership.json';r=json.loads(p.read_text());r.update(simulator=uid,runtime='com.apple.CoreSimulator.SimRuntime.iOS-26-4');p.write_text(json.dumps(r,indent=2)+'\n');(s/'simulator-uuid').write_text(uid+'\n')
UUID
rtk proxy xcrun simctl boot "$uuid" > "$scratch/boot-command.log" 2>&1
rtk proxy python3 "$workspace/.context/$owner/zlagboard-evo/prep/resume-boot.py" "$uuid" "$scratch"
rtk proxy open -a Simulator --args -CurrentDeviceUDID "$uuid"
rtk proxy xcrun simctl io "$uuid" screenshot "$scratch/boot-screen.png" > "$scratch/boot-screen.log" 2>&1
rtk proxy xcrun simctl install "$uuid" "$products/HangTen.app" > "$scratch/install.log" 2>&1
rtk proxy xcrun simctl get_app_container "$uuid" com.hangten.training app > "$scratch/installed-container.txt"
print -r -- "$uuid" > "$scratch/simulator-ready"
print "iOS26.4 isolated app installed: $uuid"
while [[ ! -f "$scratch/cleanup-requested" ]]; do
 rtk proxy sleep 3
done
