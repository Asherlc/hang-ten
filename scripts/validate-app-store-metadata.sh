#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
project_path="$repo_root/HangTen.xcodeproj"
icon_dir="$repo_root/HangTen/Resources/Assets.xcassets/AppIcon.appiconset"
contents_path="$icon_dir/Contents.json"

fail() {
  echo "App Store metadata validation failed: $*" >&2
  exit 1
}

require_icon_entry() {
  local filename="$1"
  local size="$2"

  jq -e --arg filename "$filename" --arg size "$size" \
    '.images[] | select(.filename == $filename and .size == $size)' \
    "$contents_path" >/dev/null \
    || fail "AppIcon catalog is missing $filename at $size"

  test -f "$icon_dir/$filename" \
    || fail "AppIcon catalog references missing file $filename"
}

require_png_dimensions() {
  local filename="$1"
  local expected="$2"
  local actual

  actual="$(sips -g pixelWidth -g pixelHeight "$icon_dir/$filename" 2>/dev/null \
    | awk '/pixelWidth:/ { width = $2 } /pixelHeight:/ { height = $2 } END { print width "x" height }')"
  test "$actual" = "$expected" \
    || fail "$filename is $actual; expected $expected"
}

require_setting() {
  local settings="$1"
  local expected="$2"
  local normalized_settings
  normalized_settings="$(sed 's/^[[:space:]]*//' <<< "$settings")"
  grep -Fqx "$expected" <<< "$normalized_settings" \
    || fail "missing build setting: $expected"
}

test -f "$contents_path" || fail "missing AppIcon Contents.json"
require_icon_entry "AppIcon-60@2x.png" "60x60"
require_icon_entry "AppIcon-76@2x.png" "76x76"
require_icon_entry "AppIcon-83.5@2x.png" "83.5x83.5"
require_icon_entry "AppIcon-1024.png" "1024x1024"
require_png_dimensions "AppIcon-60@2x.png" "120x120"
require_png_dimensions "AppIcon-76@2x.png" "152x152"
require_png_dimensions "AppIcon-83.5@2x.png" "167x167"
require_png_dimensions "AppIcon-1024.png" "1024x1024"

for configuration in Debug Release; do
  settings="$(xcodebuild \
    -project "$project_path" \
    -scheme HangTen \
    -configuration "$configuration" \
    -showBuildSettings 2>/dev/null)"

  require_setting "$settings" "ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon"
  require_setting "$settings" "INFOPLIST_KEY_CFBundleIconName = AppIcon"
  require_setting "$settings" "INFOPLIST_KEY_NSHealthShareUsageDescription = Hang Ten reads your Apple Health workout history to restore your progress on a new device."
  require_setting "$settings" "INFOPLIST_KEY_NSHealthUpdateUsageDescription = Hang Ten saves completed hangboard sessions to Apple Health."
  require_setting "$settings" "INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight"
done

echo "App Store metadata is valid for Debug and Release."
