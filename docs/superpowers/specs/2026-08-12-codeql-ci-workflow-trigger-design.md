# Conditional CodeQL Merge Gate Design

## Goal

Keep CodeQL merge protection meaningful without making every pull request wait for every source-language analysis.

## Constraint

GitHub does not support applying its native `Require code scanning results` ruleset conditionally by changed path. Workflow-level `paths` filters are also unsafe for required checks because a filtered workflow can remain expected or pending without ever reporting a result.

## Design

The CodeQL workflow runs for every pull request targeting `main`, every push to `main`, merge groups, manual dispatches, and the weekly schedule. A change-detection job classifies the diff by language using `dorny/paths-filter`, pinned to the full commit for v4.0.3.

CodeQL's GitHub Actions analysis runs on every workflow invocation. It is the inexpensive baseline analysis that ensures the native CodeQL ruleset always receives a result, and it provides useful coverage for workflow supply-chain and injection risks. Swift, Python, and JavaScript/TypeScript analysis jobs run only when matching code, dependency/build inputs, or the CodeQL workflow itself changes. Scheduled and manually dispatched workflows force all language analyses.

An always-running job named `CodeQL gate` depends on change detection and every analysis job. It passes when the detector and GitHub Actions analysis succeed and every selected source analysis succeeds. Deliberately skipped source-language jobs are accepted; failed or cancelled jobs are rejected.

The `Main` repository ruleset retains the native CodeQL rule with its current thresholds (`errors` for quality alerts and `high_or_higher` for security alerts). This preserves GitHub's native alert enforcement. The ruleset also requires the `CodeQL gate` status check from GitHub Actions, ensuring selected analyses cannot fail or be cancelled silently.

## Changed-Path Policy

- Swift: Swift sources, the Xcode project, Swift package manifests and resolved dependencies, and the CodeQL workflow.
- Python: Python sources, Python dependency manifests and lock files, and the CodeQL workflow.
- JavaScript/TypeScript: JavaScript/TypeScript sources, Node package manifests and lock files, and the CodeQL workflow.
- GitHub Actions: always analyzed because the repository always contains workflow code and this scan is the low-cost native-ruleset anchor.
- Documentation, metadata, images, and unrelated configuration: skip the source-language analyses.

## Verification

Repository tests assert that the workflow has no PR/push path filter, uses the pinned change detector, includes the `actions` language, conditions each source analysis on the corresponding detector output, and defines an `always()` gate that depends on every analysis.

After pushing, the new `CodeQL gate` must complete successfully on PR #115 before repository settings change. The ruleset update is then verified by reading it back and confirming both the native CodeQL rule and the required `CodeQL gate` status context are active.

## Approval

The user approved applying the best-practice conditional gate and repository-settings change on 2026-08-12.
