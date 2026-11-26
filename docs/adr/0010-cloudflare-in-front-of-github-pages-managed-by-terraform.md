# 10. Cloudflare in front of GitHub Pages, managed by Terraform

- Status: accepted
- Date: 2026-11-25

## Context

The site moves from `arthurceicorrea.github.io` to its own domain, `arthurceicorrea.dev`, bought at Cloudflare. Stage 9 of [`docs/PLAN.md`](../PLAN.md) also asks for the security headers that GitHub Pages does not let a site set: `frame-ancestors`, which a meta tag cannot carry ([ADR 2](0002-content-security-policy-in-a-meta-tag-with-self.md)), HSTS, `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`.

Three questions followed: who serves the site, who sets the headers, and how the DNS and those rules are kept, reviewed and reproduced.

## Decision

**GitHub Pages keeps serving the site** ([ADR 1](0001-github-pages-published-by-github-actions.md)), and **Cloudflare answers for the domain**: DNS first, then, with its proxy on, the headers and the `www` → apex redirect, set by response-header and redirect rules. The proxy starts off, because GitHub only issues the domain's certificate when the DNS points straight at its addresses; a later pull request turns it on, with SSL set to Full (strict) so Cloudflare also checks GitHub's certificate.

**Everything at Cloudflare that can be code is Terraform, in [`infra/`](../../infra/)**, with the Terraform and provider versions pinned exactly and the provider's hashes in `.terraform.lock.hcl`. A pull request that touches `infra/` runs `terraform fmt`, `validate` and `plan` (workflow [`infra.yml`](../../.github/workflows/infra.yml)), and the plan appears in the run summary. Arthur applies it from his machine after the merge. Done by hand, and documented in [`infra/README.md`](../../infra/README.md): buying the domain, DNSSEC, the tokens and keys, and the custom domain in the repository's Pages settings.

**The state lives in a Cloudflare R2 bucket**, through R2's S3-compatible API: same provider, free at this size, and nothing outside Cloudflare and GitHub. HCP Terraform was the alternative, at the cost of one more service and account.

**Two credentials of each kind, one that reads and one that writes.** The pipeline holds a Cloudflare token with read-only permissions and an R2 key that only reads the state bucket, both limited to this zone or bucket. The edit token and the write key exist only in Arthur's password manager. A leak from the pipeline, the place most exposed to third-party code, could change nothing.

**The domain declares that it has no e-mail**: null MX, SPF `-all` and DMARC `p=reject`, without a reporting address, so no one else receives data. A new domain without these records can be used to send mail in its owner's name.

**Nothing at Cloudflare may change the pages**: Email Obfuscation, Rocket Loader, Automatic HTTPS Rewrites, JavaScript detections, Bot Fight Mode, the crawler "labyrinth" and the managed `robots.txt` are turned off in code. Each would inject a script, rewrite the HTML or `robots.txt`, or challenge legitimate visitors such as the pipeline's live check, against [ADR 4](0004-no-third-party-resources-and-no-analytics.md) and the Content Security Policy. The AI-crawler block is off too, so the site answers as its `robots.txt` says (`Allow: /`).

## Consequences

- The domain, its records and its rules can be read, reviewed in a pull request and rebuilt from the repository.
- The full header set exists only with the proxy on; until then the site has the same protection as on `github.io`, plus HTTPS enforced by the `.dev` top-level domain itself.
- The `Content-Security-Policy` header carries only `frame-ancestors 'none'`; the rest of the policy stays in the pages' meta tag. Browsers enforce both, and neither weakens the other.
- With the proxy on, Cloudflare caches the static files it caches by default (styles, scripts, fonts, images, PDFs) for as long as GitHub Pages allows, about ten minutes. After a deploy those files can take that long to update; the HTML pages and `version.txt` are not cached, so the live check still sees the new commit at once.
- Applying is a manual step: the pipeline only shows the plan. A change made in the Cloudflare dashboard shows up as a difference in the next plan.
- The read-only Cloudflare token expires after a year and the edit token after 90 days; renewing them is documented in `infra/README.md`.
- Dependabot pull requests receive no secrets, so for them the job checks format and validity but skips the plan.
