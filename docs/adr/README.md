# Architecture decision records

Each record explains one decision about how this site is built and published: the **context** that called for it, the **decision** itself and its **consequences**, good and bad. They follow Michael Nygard's format, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

| No. | Decision | Date |
|---|---|---|
| [1](0001-github-pages-published-by-github-actions.md) | GitHub Pages, published only by GitHub Actions | 2026-11-16 |
| [2](0002-content-security-policy-in-a-meta-tag-with-self.md) | Content Security Policy in a meta tag, with `'self'` | 2026-11-16, revised 2026-11-24 |
| [3](0003-language-by-time-zone-not-ip-address.md) | Language by time zone, not by IP address | 2026-11-17 |
| [4](0004-no-third-party-resources-and-no-analytics.md) | No third-party resources and no analytics | 2026-11-16 |
| [5](0005-jinja2-and-toml-instead-of-a-site-generator.md) | Jinja2 and TOML instead of a site generator or framework (extended by 11) | 2026-11-24 |
| [6](0006-one-pull-request-per-change-with-required-pipeline.md) | One pull request per change, with the pipeline required | 2026-11-23 |
| [7](0007-github-actions-pinned-by-commit-hash.md) | GitHub Actions pinned by commit hash | 2026-11-20 |
| [8](0008-cvs-printed-by-the-build-in-a-legible-typeface.md) | CVs printed by the build, in a legible typeface | 2026-11-24 |
| [9](0009-cinzel-only-where-the-page-is-an-inscription.md) | Cinzel only where the page is an inscription | 2026-11-25 |
| [10](0010-cloudflare-in-front-of-github-pages-managed-by-terraform.md) | Cloudflare in front of GitHub Pages, managed by Terraform | 2026-11-25 |
| [11](0011-articles-in-markdown-in-english-built-by-the-same-script.md) | Articles in Markdown, in English, built by the same script | 2026-11-27 |

A decision that changes gets a new record that supersedes the old one; the old one stays, marked as superseded, so the history of the reasoning is kept.
