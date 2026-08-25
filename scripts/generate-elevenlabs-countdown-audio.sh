#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h}
output_directory=${ELEVENLABS_OUTPUT_DIRECTORY:-"$repo_root/HangTen/Resources/CountdownAudio"}
model_id=${ELEVENLABS_MODEL_ID:-eleven_flash_v2_5}
output_format=${ELEVENLABS_OUTPUT_FORMAT:-mp3_22050_32}
voice_id=${ELEVENLABS_VOICE_ID:-}
pack_filenames=(countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json)

if [[ -z ${ELEVENLABS_API_KEY:-} ]]; then
  print -u2 -- 'ELEVENLABS_API_KEY must be set.'
  exit 1
fi

if [[ -z $voice_id ]]; then
  print -u2 -- 'ELEVENLABS_VOICE_ID must be set.'
  exit 1
fi

output_parent=${output_directory:h}
mkdir -p -- "$output_parent"
if [[ -e "$output_directory" || -L "$output_directory" ]]; then
  if [[ ! -d "$output_directory" || -L "$output_directory" ]]; then
    print -u2 -- 'ElevenLabs output path must be a real countdown audio directory.'
    exit 1
  fi

  for existing_file in "$output_directory"/*(ND); do
    case ${existing_file:t} in
      .gitkeep|README.md|countdown-1.mp3|countdown-2.mp3|countdown-3.mp3|metadata.json)
        [[ -f "$existing_file" && ! -L "$existing_file" ]] || {
          print -u2 -- 'ElevenLabs output directory contains an unsafe countdown audio entry.'
          exit 1
        }
        ;;
      *)
        print -u2 -- 'ElevenLabs output directory is not a recognized countdown audio pack.'
        exit 1
        ;;
    esac
  done
else
  mkdir -- "$output_directory"
fi

temporary_directory=$(mktemp -d "$output_parent/.CountdownAudio.XXXXXX")

cleanup() {
  [[ -n ${temporary_directory:-} && -d "$temporary_directory" ]] && rm -rf -- "$temporary_directory"
}
trap cleanup EXIT

json_string() {
  python3 - "$1" <<'PY'
import json
import sys

print(json.dumps(sys.argv[1], ensure_ascii=False))
PY
}

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
  request_body="{\"text\":$(json_string "$phrase"),\"model_id\":$(json_string "$model_id")}"
  request_url="https://api.elevenlabs.io/v1/text-to-speech/$voice_id?output_format=$output_format"
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

python3 - "$voice_id" "$model_id" "$output_format" > "$temporary_directory/metadata.json" <<'PY'
import json
import sys

json.dump(
    {
        "voice_id": sys.argv[1],
        "model_id": sys.argv[2],
        "output_format": sys.argv[3],
        "source_phrases": ["1", "2", "3"],
        "clips": ["countdown-1.mp3", "countdown-2.mp3", "countdown-3.mp3"],
    },
    sys.stdout,
    ensure_ascii=False,
    separators=(",", ":"),
)
print()
PY

for filename in "${pack_filenames[@]}"; do
  [[ -s "$temporary_directory/$filename" ]] || {
    print -u2 -- 'Failed to generate a complete ElevenLabs countdown audio pack.'
    exit 1
  }
done

for filename in "${pack_filenames[@]}"; do
  if ! mv -f -- "$temporary_directory/$filename" "$output_directory/$filename"; then
    print -u2 -- 'Failed to install the ElevenLabs countdown audio pack.'
    exit 1
  fi
done

print -- "Generated countdown audio pack in $output_directory"
