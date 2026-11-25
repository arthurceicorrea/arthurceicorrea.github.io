# 2. Content Security Policy in a meta tag, with 'self'

- Status: accepted
- Date: 2026-11-16, revised 2026-11-24

## Context

A Content Security Policy (CSP) tells the browser which sources a page may load styles, scripts, fonts and images from. If an attacker manages to inject a script into the page, a strict policy stops the browser from running it.

The usual place for the policy is an HTTP response header, but GitHub Pages does not let a site set its own headers ([ADR 1](0001-github-pages-published-by-github-actions.md)). The CSP specification allows the same policy in a `<meta http-equiv="Content-Security-Policy">` element, with a few directives left out: `frame-ancestors`, `report-uri` and `sandbox` are ignored there.

The first version of the site kept its CSS and JavaScript inline and allowed them by their SHA-256 hashes. Every edit to the style or the script meant computing a new hash and updating the policy.

## Decision

Every page carries the same policy in a meta tag, and stage 2 of [`docs/PLAN.md`](../PLAN.md) replaced the hashes with `'self'`:

```
default-src 'none'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self' data:;
connect-src 'self'; base-uri 'none'; form-action 'none'
```

- Everything is denied by default (`default-src 'none'`) and allowed back only from the site's own address.
- No inline styles or scripts: CSS is served from `/assets/site.css` and JavaScript from `/assets/language.js` and `/assets/page.js`. The only inline block is the JSON-LD structured data, which is data and is not executed.
- Never `'unsafe-inline'` nor `'unsafe-eval'`.
- `<meta name="referrer" content="no-referrer">` also keeps the site's address out of the requests to other sites.

## Consequences

- An injected `<script>` or `style=""` is blocked, because it is neither a file from the site nor allowed by a hash. That makes `'self'` as strict as the hashes here, with no hash to recompute when the CSS or JavaScript changes.
- The tests check the exact policy on every page, and that there is no inline style, script, `style=` or `on...=` attribute ([`tests/test_static.py`](../../tests/test_static.py)).
- `frame-ancestors` cannot be set in a meta tag, so the site cannot forbid being embedded in another site's frame. That needs a header: stage 9 of the plan adds it, with HSTS and the other security headers, through Cloudflare in front of Pages once there is a custom domain.
- Any service that rewrites the HTML on the way (for example Cloudflare's Email Obfuscation or Rocket Loader) would inject inline scripts that the policy blocks, so it must stay off.

## Sources

- MDN, [`frame-ancestors`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors): "This directive is not supported in the `<meta>` element."
- GitHub Community, [HTTP Headers (e.g. Content-Security-Policy) on Pages](https://github.com/orgs/community/discussions/54257): GitHub Pages has no way to add custom headers.
