# Imported pipeline provenance

The onboarding tool was imported from the local `hangboard-vectorizer`
repository at commit `ce08eb9`. Package code, self-contained tests, evidence,
and operator documentation were copied into this repository.

The former tracked onboarding-run fixture was removed when published content
migrated to canonical packages. The semantic benchmark now validates semantic
and artwork parity directly from a package below `Hangboards/`, without relying
on a `run.json` identity. Generated onboarding runs belong below the ignored
`.context/` workspace and are never repository packages.
