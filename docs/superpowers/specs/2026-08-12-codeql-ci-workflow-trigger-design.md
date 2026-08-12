# CodeQL CI Workflow Trigger Design

## Goal

Run CodeQL when CI workflow configuration changes, including Dependabot action-version updates such as PR #115.

## Root Cause

`.github/workflows/codeql.yml` limits `pull_request` and `push` triggers to a source-path allowlist. `.github/workflows/ci.yml` is absent from both lists, so PR #115's only changed file does not schedule CodeQL.

## Design

Add `.github/workflows/ci.yml` to the existing `paths` list for both the `pull_request` and `push` triggers. Preserve every current source path, event, permission, job, and schedule unchanged.

This is deliberately narrower than removing path filters or running CodeQL on every workflow edit: it covers the CI workflow that owns the upgraded GitHub Action while retaining the established execution-cost boundary.

## Verification

Parse the workflow as YAML and assert that both filtered triggers list `.github/workflows/ci.yml`. Inspect the diff to confirm no unrelated workflow behavior changes.

## Approval

The user approved this scoped design on 2026-08-12.
