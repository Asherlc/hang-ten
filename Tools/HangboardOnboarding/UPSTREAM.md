# Imported pipeline provenance

The onboarding tool was imported from the local `hangboard-vectorizer`
repository at commit `ce08eb9` (`feat: add zero-call semantic replay
benchmark`). Package code, self-contained tests, evidence, and operator
documentation were copied without semantic changes. Eight legacy test modules
that depended on mutable, unversioned `work/real-beastmaker/**` directories
were omitted; see `TESTING.md`.

`reference/metolius-compact-ii/accepted-run` is the accepted visual run with
run identity
`30c65a90865de3c7de6e8e27a061056c4ef59e2d7a700e1406e3ae272e83e0b6`.
It is intentionally versioned so `hangboard-semantic-benchmark` can fail
closed unless cached semantic replay reproduces its Stage 2 labels, Stage 3
geometry, and Stage 4 highlight pixels exactly with zero live model calls.

Generated onboarding runs do not belong here. Put them below the Hang Ten
repository's ignored `.context/hangboard-onboarding/` directory.
