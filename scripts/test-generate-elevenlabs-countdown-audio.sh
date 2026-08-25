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

fake_bin="$workspace/bin"
mkdir -p "$fake_bin"
request_log="$workspace/requests.log"

cat > "$fake_bin/curl" <<'EOF'
#!/bin/zsh
set -euo pipefail

log_file=${FAKE_CURL_LOG:?}
output_file=''
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
print -n -- "audio-for-${body}" > "$output_file"
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

success_output=$(PATH="$fake_bin:$PATH" FAKE_CURL_LOG="$request_log" \
  ELEVENLABS_API_KEY=test-key ELEVENLABS_VOICE_ID=test-voice \
  ELEVENLABS_OUTPUT_DIRECTORY="$workspace/output" zsh "$generator" 2>&1)

actual_files=("${(@f)$(cd "$workspace/output" && print -rl -- *)}")
expected_files=(countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json)
[[ "${actual_files[*]}" == "${expected_files[*]}" ]] || fail "unexpected output files: ${actual_files[*]}"

for clip in countdown-1.mp3 countdown-2.mp3 countdown-3.mp3 metadata.json; do
  [[ -s "$workspace/output/$clip" ]] || fail "$clip was not written with content"
done

[[ $(rg -c '^method=POST$' "$request_log") == 3 ]] || fail 'requests were not POSTs'
[[ $(rg -c '^header=xi-api-key: test-key$' "$request_log") == 3 ]] || fail 'API key header was not sent'
[[ $(rg -c '^header=Content-Type: application/json$' "$request_log") == 3 ]] || fail 'JSON content header was not sent'
[[ $(rg -c '^url=https://api\.elevenlabs\.io/v1/text-to-speech/test-voice\?output_format=mp3_22050_32$' "$request_log") == 3 ]] || fail 'voice URL or default output format was wrong'
[[ "$success_output" != *test-key* ]] || fail 'generator diagnostics exposed the API key'
! rg -q -- 'test-key' "$workspace/output/metadata.json" || fail 'metadata exposed the API key'

rg -q 'CountdownAudio' "$repo_root/HangTen.xcodeproj/project.pbxproj" || fail 'CountdownAudio is not registered as an app resource'

print -- 'PASS: ElevenLabs countdown generator contract'
