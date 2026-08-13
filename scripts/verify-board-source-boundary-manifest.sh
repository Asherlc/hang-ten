#!/bin/sh
set -eu

repository_root=${SRCROOT:?SRCROOT must point to the repository root}
manifest="$repository_root/HangTenTests/BoardSourceBoundaryTrackedPaths.txt"
actual_manifest=$(mktemp "${TMPDIR:-/tmp}/board-source-boundary-manifest.XXXXXX")
trap 'rm -f "$actual_manifest"' EXIT HUP INT TERM

git -C "$repository_root" ls-files -- HangTen HangTen.xcodeproj/project.pbxproj > "$actual_manifest"

if ! diff -u "$manifest" "$actual_manifest"; then
    echo "error: BoardSourceBoundaryTrackedPaths.txt must exactly match git ls-files -- HangTen HangTen.xcodeproj/project.pbxproj." >&2
    exit 1
fi
