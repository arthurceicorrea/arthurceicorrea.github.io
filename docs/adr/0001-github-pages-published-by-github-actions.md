# 1. GitHub Pages, published only by GitHub Actions

- Status: accepted
- Date: 2026-11-16

## Context

The portfolio is a static site: HTML, CSS, JavaScript, fonts, images and PDF files, with no server-side code. It needs a host with HTTPS, at no cost, that a single person can run.

The site is also meant to show the owner's DevOps work, so how it reaches production matters as much as where it lives.

## Decision

Host the site on GitHub Pages, in the same repository as its source, and publish it only through the GitHub Actions workflow [`.github/workflows/site.yml`](../../.github/workflows/site.yml):

- the **Validar** job builds `_site/` and runs every check (code style, static tests, W3C validator, browser tests, accessibility audit, Lighthouse), then uploads `_site/` as the Pages artifact (`actions/upload-pages-artifact`);
- the **Publicar** job deploys that artifact (`actions/deploy-pages`), only on `main` and only after **Validar** passes; pull requests run the checks without publishing;
- the **Conferir no ar** job then checks the live site serves the commit just deployed (`version.txt`), with every page and file ([`ci/monitor.py`](../../ci/monitor.py)).

There is no `gh-pages` branch and no publishing from a folder: nothing reaches the site without passing the pipeline.

## Consequences

- Hosting and HTTPS cost nothing, and the whole path from commit to live site is in the repository, readable and reviewable.
- A broken change cannot be published: if any check fails, the deploy job does not run.
- GitHub Pages serves files as they are. It does not let the site set its own HTTP response headers, so the security policy goes in a meta tag ([ADR 2](0002-content-security-policy-in-a-meta-tag-with-self.md)). It runs no server code, so the visitor's language is chosen in the browser ([ADR 3](0003-language-by-time-zone-not-ip-address.md)).
- The site lives at `arthurceicorrea.github.io` until a custom domain is bought (stage 8 of [`docs/PLAN.md`](../PLAN.md)), which would also allow security headers through a proxy in front of Pages.
- A weekly workflow ([`.github/workflows/monitor.yml`](../../.github/workflows/monitor.yml)) runs the same live check and opens an issue if it fails. GitHub disables scheduled workflows in repositories with no commits for 60 days.
