# Countdown audio pack

This directory is intentionally empty in source control except for this file
and `.gitkeep`. Hang Ten never contains an ElevenLabs API key and never makes
ElevenLabs requests at runtime.

An authorized maintainer may generate a pack locally from the repository root:

```sh
ELEVENLABS_API_KEY='…' ELEVENLABS_VOICE_ID='…' \
  rtk zsh scripts/generate-elevenlabs-countdown-audio.sh
```

The command creates `countdown-1.mp3`, `countdown-2.mp3`, `countdown-3.mp3`,
and `metadata.json`. Review each generated file, update
`HangTenTests/BoardSourceBoundaryTrackedPaths.txt` whenever a generated pack
file is added or removed (including `metadata.json`), then explicitly commit
the pack before it can ship in the app bundle.
