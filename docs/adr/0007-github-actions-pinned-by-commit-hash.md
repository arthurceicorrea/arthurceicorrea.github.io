# 7. GitHub Actions pinned by commit hash

- Status: accepted
- Date: 2026-11-20

## Context

A workflow step such as `uses: actions/checkout@v7` runs code from another repository. The `v7` part is a tag, and tags can be moved: whoever controls that repository, or an attacker who takes it over, can point the tag at different code. The next run then executes that code inside the pipeline, which here builds and publishes the site.

This happened in March 2025: the `tj-actions/changed-files` action was compromised and most of its version tags were repointed to a malicious commit that printed CI secrets to public logs (CVE-2025-30066). Moving a tag does not change what a commit hash points to.

## Decision

Every `uses:` line in [`.github/workflows/`](../../.github/workflows/) points to the full 40-character commit hash of the action, with the version in a comment:

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
```

Dependabot ([`.github/dependabot.yml`](../../.github/dependabot.yml)) checks the actions every week and opens a pull request that updates both the hash and the comment.

## Consequences

- A commit hash cannot be moved, so each run uses exactly the code that was reviewed.
- Updates still arrive, as Dependabot pull requests that go through the pipeline like any other change ([ADR 6](0006-one-pull-request-per-change-with-required-pipeline.md)).
- The hash is not readable on its own; the comment says which version it is, and must be kept in step with the hash.
- The same idea applies to the other tools: Python and npm packages are pinned to exact versions, and `ci/package-lock.json` pins every npm package, including indirect ones.

## Sources

- CISA, [Supply Chain Compromise of Third-Party tj-actions/changed-files (CVE-2025-30066)](https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-github-action-cve-2025-30066).
- Wiz, [GitHub Action tj-actions/changed-files supply chain attack](https://wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066): the attacker modified existing version tags to point to the malicious code.
