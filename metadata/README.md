# App Store metadata

The JSON files in this directory use the strict `asc metadata` localization
schema. App-info JSON may contain `name`, `subtitle`, `privacyPolicyUrl`,
`privacyChoicesUrl`, and `privacyPolicyText`; version localization JSON may
contain `description`, `keywords`, `marketingUrl`, `promotionalText`,
`supportUrl`, and `whatsNew`.

Copyright is an App Store version attribute, not a localization field, so it
must not be added to `version/1.0.0/en-US.json`. The canonical version-level
value is stored in `version/1.0.0/copyright.txt`, validated by
`scripts/validate-app-store-metadata.sh`, and applied with:

```sh
rtk asc versions update --version-id "VERSION_ID" \
  --copyright "$(<metadata/version/1.0.0/copyright.txt)"
```
