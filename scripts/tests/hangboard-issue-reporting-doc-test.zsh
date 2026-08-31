#!/bin/zsh

set -euo pipefail

repo_root="${0:A:h:h:h}"
runbook="$repo_root/docs/hangboard-issue-reporting.md"
readme="$repo_root/README.md"

[[ -f "$runbook" ]] || {
  print -u2 "Missing hangboard issue reporting runbook: $runbook"
  exit 1
}

required_hidden_fields=(
  board_id
  board_name
  manufacturer
  presentation_id
  presentation_name
  platform
  app_version
  build
)

for key in $required_hidden_fields; do
  rg -q "\`$key\`" "$runbook" || {
    print -u2 "Runbook is missing hidden field: $key"
    exit 1
  }
done

required_text=(
  'Report a Hang Ten hangboard issue'
  'Incorrect hold/specification'
  'Missing or incorrect board'
  'Other'
  'title'
  'description'
  'reCAPTCHA'
  'Asherlc/hang-ten'
  'hangboard-report'
  'HANGBOARD_REPORT_FORM_URL'
  'https://tally.so/'
)

for text in $required_text; do
  rg -Fq -- "$text" "$runbook" || {
    print -u2 "Runbook is missing required text: $text"
    exit 1
  }
done

rg -Fq 'docs/hangboard-issue-reporting.md' "$readme" || {
  print -u2 'README does not link to the hangboard issue reporting runbook'
  exit 1
}

print 'Hangboard issue reporting documentation contract passed.'
