#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h}
output_directory=${ELEVENLABS_OUTPUT_DIRECTORY:-"$repo_root/HangTen/Resources/CountdownAudio"}
model_id=${ELEVENLABS_MODEL_ID:-eleven_flash_v2_5}
output_format=${ELEVENLABS_OUTPUT_FORMAT:-mp3_22050_32}

if [[ -z ${ELEVENLABS_API_KEY:-} ]]; then
  print -u2 -- 'ELEVENLABS_API_KEY must be set.'
  exit 1
fi

if [[ -z ${ELEVENLABS_VOICE_ID:-} ]]; then
  print -u2 -- 'ELEVENLABS_VOICE_ID must be set.'
  exit 1
fi

output_parent=${output_directory:h}
mkdir -p -- "$output_parent"
temporary_directory=$(mktemp -d "$output_parent/.CountdownAudio.XXXXXX")
backup_directory=''

cleanup() {
  [[ -n ${temporary_directory:-} && -d "$temporary_directory" ]] && rm -rf -- "$temporary_directory"
  [[ -n ${backup_directory:-} && -d "$backup_directory" ]] && rm -rf -- "$backup_directory"
}
trap cleanup EXIT

json_model_id=${model_id//\\/\\\\}
json_model_id=${json_model_id//\"/\\\"}

error_code() {
  local response_body=$1

  python3 - "$response_body" <<'PY' 2>/dev/null || true
import json
import re
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as response_file:
        detail = json.load(response_file).get("detail")
except (OSError, ValueError, AttributeError):
    detail = None

code = detail.get("code") if isinstance(detail, dict) else None
print(code if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", code) else "unavailable")
PY
}

for phrase in 1 2 3; do
  request_body="{\"text\":\"$phrase\",\"model_id\":\"$json_model_id\"}"
  request_url="https://api.elevenlabs.io/v1/text-to-speech/$ELEVENLABS_VOICE_ID?output_format=$output_format"
  http_status='000'
  if ! http_status=$(curl --silent \
    --request POST \
    --header "xi-api-key: $ELEVENLABS_API_KEY" \
    --header 'Content-Type: application/json' \
    --data "$request_body" \
    --output "$temporary_directory/countdown-$phrase.mp3" \
    --write-out '%{http_code}' \
    "$request_url" 2>/dev/null); then
    http_status='000'
  fi
  [[ "$http_status" =~ '^[0-9]{3}$' ]] || http_status='000'
  if (( 10#$http_status < 200 || 10#$http_status >= 300 )); then
    response_code=$(error_code "$temporary_directory/countdown-$phrase.mp3")
    [[ "$response_code" =~ '^[A-Za-z0-9_-]{1,80}$' ]] || response_code='unavailable'
    print -u2 -- "Failed to generate ElevenLabs countdown audio (HTTP $http_status: $response_code)."
    exit 1
  fi
done

print -r -- "{\"model_id\":\"$json_model_id\",\"output_format\":\"$output_format\",\"clips\":[\"countdown-1.mp3\",\"countdown-2.mp3\",\"countdown-3.mp3\"]}" > "$temporary_directory/metadata.json"

for filename in countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json; do
  [[ -s "$temporary_directory/$filename" ]] || {
    print -u2 -- 'Failed to generate a complete ElevenLabs countdown audio pack.'
    exit 1
  }
done

if [[ -e "$output_directory" ]]; then
  backup_directory=$(mktemp -d "$output_parent/.CountdownAudio.backup.XXXXXX")
  rmdir "$backup_directory"
  mv -- "$output_directory" "$backup_directory"
fi

if ! mv -- "$temporary_directory" "$output_directory"; then
  [[ -n $backup_directory && -d "$backup_directory" ]] && mv -- "$backup_directory" "$output_directory"
  print -u2 -- 'Failed to install the ElevenLabs countdown audio pack.'
  exit 1
fi
temporary_directory=''

print -- "Generated countdown audio pack in $output_directory"
