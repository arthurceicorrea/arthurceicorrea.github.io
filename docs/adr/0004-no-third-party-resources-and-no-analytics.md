# 4. No third-party resources and no analytics

- Status: accepted
- Date: 2026-11-16

## Context

Most websites load fonts, scripts or images from other companies' servers, and many add an analytics service to count visitors. Each of those requests tells a third party who visited the page, from which address and when, and often sets cookies that call for a consent banner.

A third-party script also runs with the same power as the site's own code: if that server is compromised, the page is too.

## Decision

Everything the page uses is served by the site itself, and nothing measures the visitors:

- the Cinzel and EB Garamond fonts are self-hosted as WOFF2 files, under their SIL Open Font License ([`static/fonts/`](../../static/fonts/));
- the CSS, the JavaScript, the images, the CVs and the vCard are files of the repository;
- there is no analytics, no tracking pixel and no cookie;
- links to LinkedIn and GitHub are plain links, opened in a new tab with `rel="noopener noreferrer"`; nothing from those sites is embedded.

The footer says it in each language: "No cookies, no trackers and no third-party resources on this page."

## Consequences

- The security policy enforces it: with `default-src 'none'` and only `'self'` allowed back ([ADR 2](0002-content-security-policy-in-a-meta-tag-with-self.md)), the browser refuses to load anything from another server.
- The tests check it too: every external address must be in `ALLOWED_EXTERNAL` and none may be loaded as a resource ([`tests/test_static.py`](../../tests/test_static.py)), and the browser tests fail on any blocked request in the console.
- There is no consent banner to show and no visitor data to protect.
- There are no visit statistics. If they are ever needed, this record has to be revisited first.
- Fonts and their updates are the site's job: the files are versioned with the code, with their licences next to them.
