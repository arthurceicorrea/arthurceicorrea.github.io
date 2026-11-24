# 6. One pull request per change, with the pipeline required

- Status: accepted
- Date: 2026-11-23

## Context

Since the first pipeline, the site could only be published after every check passed ([ADR 1](0001-github-pages-published-by-github-actions.md)). That protected the deploy, but not the `main` branch itself: a commit could be pushed straight to `main` and only then fail, leaving the branch broken until the next fix.

The project has one person, so asking for another person's approval is not possible.

## Decision

The repository ruleset **Proteger main**, active on the default branch and with no bypass list, requires:

- a pull request for every change to `main`, with 0 required approvals;
- the **Validar** status check to pass before merging;
- no force pushes and no deletion of `main`.

Each change gets its own branch and its own pull request, opened as a draft while it is being reviewed.

## Consequences

- `main` only receives commits that passed the whole pipeline, so it can always be published.
- Every change, including the weekly Dependabot updates, leaves a reviewable record: the pull request, its description and its checks.
- The job name **Validar** is part of the rule. Renaming the job in the workflow would leave the rule waiting for a check that never runs.
- Without force pushes, history is never rewritten on `main`. A branch that falls behind `main` is updated with a merge commit, not a rebase.
- An urgent fix also goes through a pull request and waits for the pipeline, about three minutes.

The ruleset is a GitHub setting, not a file in the repository: it is changed under Settings → Rules → Rulesets.
