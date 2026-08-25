#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h}
generator="$repo_root/scripts/generate-elevenlabs-countdown-audio.sh"
workspace=$(mktemp -d)
trap 'rm -rf -- "$workspace"' EXIT

fail() {
  print -u2 -- "FAIL: $*"
  exit 1
}

assert_metadata() {
  local metadata_path=$1

  python3 - "$metadata_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as metadata_file:
    metadata = json.load(metadata_file)

expected = {
    "voice_id": "test-voice",
    "model_id": "eleven_flash_v2_5",
    "output_format": "mp3_22050_32",
    "source_phrases": ["1", "2", "3"],
    "clips": ["countdown-1.mp3", "countdown-2.mp3", "countdown-3.mp3"],
}

if metadata != expected:
    raise SystemExit(f"unexpected metadata: {metadata!r}")
PY
}

fake_bin="$workspace/bin"
mkdir -p "$fake_bin"
request_log="$workspace/requests.log"

cat > "$fake_bin/curl" <<'EOF'
#!/bin/zsh
set -euo pipefail

log_file=${FAKE_CURL_LOG:?}
output_file=''
write_out=''
method=''
url=''
headers=()
body=''

while (( $# > 0 )); do
  case "$1" in
    --request)
      method=$2
      shift 2
      ;;
    --header)
      headers+=("$2")
      shift 2
      ;;
    --data)
      body=$2
      shift 2
      ;;
    --output)
      output_file=$2
      shift 2
      ;;
    --write-out)
      write_out=$2
      shift 2
      ;;
    *)
      url=$1
      shift
      ;;
  esac
done

print -r -- "method=$method" >> "$log_file"
for header in "${headers[@]}"; do
  print -r -- "header=$header" >> "$log_file"
done
print -r -- "body=$body" >> "$log_file"
print -r -- "url=$url" >> "$log_file"
print -r -- '---' >> "$log_file"

if [[ ${FAKE_CURL_FAILURE:-} == 1 ]]; then
  print -n -- '{"detail":{"code":"quota_exceeded","message":"Request https://api.elevenlabs.io/v1/text-to-speech/test-voice?output_format=mp3_22050_32 with xi-api-key: other-secret and encoded=test-key%2Dderived."}}' > "$output_file"
  if [[ "$write_out" == *http_code* ]]; then
    print -n -- '402'
  fi
  exit 0
fi

print -n -- "audio-for-${body}" > "$output_file"
if [[ "$write_out" == *http_code* ]]; then
  print -n -- '200'
fi
EOF
chmod +x "$fake_bin/curl"

set +e
missing_output=$(PATH="$fake_bin:$PATH" FAKE_CURL_LOG="$request_log" \
  ELEVENLABS_VOICE_ID=test-voice ELEVENLABS_OUTPUT_DIRECTORY="$workspace/output" \
  zsh "$generator" 2>&1)
missing_status=$?
set -e

(( missing_status != 0 )) || fail 'missing API key unexpectedly succeeded'
[[ "$missing_output" == *ELEVENLABS_API_KEY* ]] || fail 'missing API key error was not reported'
[[ ! -e "$request_log" ]] || fail 'curl was called before credentials were validated'

output_directory="$workspace/output"
mkdir -p "$output_directory"
print -- 'Keep this documentation.' > "$output_directory/README.md"
print -- 'Keep this marker.' > "$output_directory/.gitkeep"

success_output=$(PATH="$fake_bin:$PATH" FAKE_CURL_LOG="$request_log" \
  ELEVENLABS_API_KEY=test-key ELEVENLABS_VOICE_ID=test-voice \
  ELEVENLABS_OUTPUT_DIRECTORY="$output_directory" zsh "$generator" 2>&1)

actual_files=("${(@f)$(cd "$output_directory" && print -rl -- *(ND))}")
expected_files=(.gitkeep README.md countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json)
[[ "${actual_files[*]}" == "${expected_files[*]}" ]] || fail "unexpected output files: ${actual_files[*]}"

for clip in countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json; do
  [[ -s "$output_directory/$clip" ]] || fail "$clip was not written with content"
done

[[ $(<"$output_directory/README.md") == 'Keep this documentation.' ]] || fail 'README.md was not preserved'
[[ $(<"$output_directory/.gitkeep") == 'Keep this marker.' ]] || fail '.gitkeep was not preserved'
assert_metadata "$output_directory/metadata.json" || fail 'metadata did not record the generated-pack contract'

[[ $(rg -c '^method=POST$' "$request_log") == 3 ]] || fail 'requests were not POSTs'
[[ $(rg -c '^header=xi-api-key: test-key$' "$request_log") == 3 ]] || fail 'API key header was not sent'
[[ $(rg -c '^header=Content-Type: application/json$' "$request_log") == 3 ]] || fail 'JSON content header was not sent'
[[ $(rg -c '^url=https://api\.elevenlabs\.io/v1/text-to-speech/test-voice\?output_format=mp3_22050_32$' "$request_log") == 3 ]] || fail 'voice URL or default output format was wrong'
[[ "$success_output" != *test-key* ]] || fail 'generator diagnostics exposed the API key'
! rg -q -- 'test-key' "$output_directory/metadata.json" || fail 'metadata exposed the API key'

pack_before_failure=$(cd "$output_directory" && shasum countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json)
set +e
failure_output=$(PATH="$fake_bin:$PATH" FAKE_CURL_LOG="$request_log" FAKE_CURL_FAILURE=1 \
  ELEVENLABS_API_KEY=test-key ELEVENLABS_VOICE_ID=test-voice \
  ELEVENLABS_OUTPUT_DIRECTORY="$output_directory" zsh "$generator" 2>&1)
failure_status=$?
set -e

(( failure_status != 0 )) || fail 'HTTP failure unexpectedly succeeded'
[[ "$failure_output" == *'HTTP 402'* ]] || fail 'HTTP failure status was not reported'
[[ "$failure_output" == *quota_exceeded* ]] || fail 'ElevenLabs error code was not reported'
[[ "$failure_output" != *test-key* ]] || fail 'HTTP failure diagnostics exposed the API key'
[[ "$failure_output" != *other-secret* && "$failure_output" != *test-key%2Dderived* ]] || fail 'HTTP failure diagnostics exposed provider credentials'
[[ "$failure_output" != *xi-api-key* && "$failure_output" != *https://api.elevenlabs.io* ]] || fail 'HTTP failure diagnostics exposed request metadata'
[[ "$pack_before_failure" == "$(cd "$output_directory" && shasum countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json)" ]] || fail 'HTTP failure replaced the existing audio pack'

foreign_output_directory="$workspace/foreign-output"
mkdir -p "$foreign_output_directory"
print -- 'Do not replace this file.' > "$foreign_output_directory/foreign.txt"
set +e
foreign_output=$(PATH="$fake_bin:$PATH" FAKE_CURL_LOG="$request_log" \
  ELEVENLABS_API_KEY=test-key ELEVENLABS_VOICE_ID=test-voice \
  ELEVENLABS_OUTPUT_DIRECTORY="$foreign_output_directory" zsh "$generator" 2>&1)
foreign_status=$?
set -e

(( foreign_status != 0 )) || fail 'foreign output directory unexpectedly succeeded'
[[ "$foreign_output" == *'not a recognized countdown audio pack'* ]] || fail 'foreign output directory rejection was not reported'
[[ $(<"$foreign_output_directory/foreign.txt") == 'Do not replace this file.' ]] || fail 'foreign output directory was modified'

rg -q 'CountdownAudio' "$repo_root/HangTen.xcodeproj/project.pbxproj" || fail 'CountdownAudio is not registered as an app resource'

print -- 'PASS: ElevenLabs countdown generator contract'
