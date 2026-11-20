# arthurceicorrea.github.io

[![Site](https://github.com/arthurceicorrea/arthurceicorrea.github.io/actions/workflows/site.yml/badge.svg)](https://github.com/arthurceicorrea/arthurceicorrea.github.io/actions/workflows/site.yml)

Personal portfolio of Arthur Cei Corrêa — DevOps, applied AI and security.
One static page in Portuguese, English, Spanish and Italian, published at <https://arthurceicorrea.github.io/>, with a page per language at `/pt/`, `/en/`, `/es/` and `/it/`.

- No frameworks, no third-party scripts, fonts or trackers; a restrictive Content Security Policy with hashes for the inline style and script.
- Choose the language with `?lang=pt`, `?lang=en`, `?lang=es` or `?lang=it`; otherwise the visitor's country, inferred from the device time zone with no external lookup (Brazil and Portugal: PT; Italy: IT; Spain and Spanish-speaking America: ES), then the browser language, then English.
- Fonts: Cinzel and EB Garamond, self-hosted as WOFF2 under the SIL Open Font License (see `fonts/`).

## Pipeline

`index.html` is the single source. Every push to `main` runs [`.github/workflows/site.yml`](.github/workflows/site.yml):

1. **Build** (`ci/build.py`): copies the site to `_site/` and generates one page per language, each with only its own edition and with title, description, canonical URL and sharing preview (Open Graph image) in that language.
2. **Static validation** (`ci/validate.py _site`): CSP hashes, HTML nesting, unique ids, absolute local paths, safe external links, no third-party resources, structured data, language pages, `robots.txt`, `sitemap.xml`, and no phone number in the pages or the CVs.
3. **W3C HTML validation**: the official Nu Html Checker on every generated page.
4. **Browser test** (`ci/smoke.py _site`): headless Chrome on mobile and desktop widths — right language shown, fonts loaded, no console errors or CSP violations, language switch, pages without JavaScript, language chosen by country (simulated time zones), 404 page.
5. **Accessibility audit** (`ci/a11y.py`): axe-core on every page, mobile and desktop; any WCAG 2.2 A or AA violation fails the run.
6. **Lighthouse** (`ci/lighthouserc.json`): performance, accessibility, best practices and SEO for each page. Accessibility below 95 or best practices below 90 fail the run; the scores, and the audits that lose points, appear in the run summary, with the full reports kept as an artifact.
7. **Deploy**: only if all checks pass, `_site/` is published to GitHub Pages. Pull requests run the checks without publishing.
8. **Post-deploy check** (`ci/monitor.py`): once published, the live site must serve the commit just deployed (`version.txt`), with every page and file, the custom 404, the HTTP→HTTPS redirect and a valid certificate.

**Monitoring.** [`.github/workflows/monitor.yml`](.github/workflows/monitor.yml) runs the same live check every Monday. If it fails, it opens an issue labelled `monitoramento`; when the site passes again, it closes the issue. (GitHub disables scheduled workflows after 60 days without commits.)

To check locally: `python ci/build.py && python ci/validate.py _site && python ci/smoke.py _site` (the W3C, axe and Lighthouse steps need `npm install --prefix ci` and Java). After editing the inline style or script, run `python ci/csp_hash.py index.html`.

**Dependencies.** Workflow actions are pinned to exact commits, and the test tools to exact versions (`ci/requirements.txt`, `ci/package.json`). Dependabot (`.github/dependabot.yml`) opens a weekly pull request when any of them has a new version; the pipeline checks it before merging. The footer date and year come from the last commit, filled in by the build.
