# arthurceicorrea.github.io

Personal portfolio of Arthur Cei Corrêa — DevOps, applied AI and security.
One static page in Portuguese, English, Spanish and Italian, published at <https://arthurceicorrea.github.io/>, with a page per language at `/pt/`, `/en/`, `/es/` and `/it/`.

- No frameworks, no third-party scripts, fonts or trackers; a restrictive Content Security Policy with hashes for the inline style and script.
- Choose the language with `?lang=pt`, `?lang=en`, `?lang=es` or `?lang=it`; otherwise the visitor's country, inferred from the device time zone with no external lookup (Brazil and Portugal: PT; Italy: IT; Spain and Spanish-speaking America: ES), then the browser language, then English.
- Fonts: Cinzel and EB Garamond, self-hosted as WOFF2 under the SIL Open Font License (see `fonts/`).

## Pipeline

`index.html` is the single source. Every push to `main` runs [`.github/workflows/site.yml`](.github/workflows/site.yml):

1. **Build** (`ci/build.py`): copies the site to `_site/` and generates one page per language, each with only its own edition and with title, description, canonical URL and sharing preview (Open Graph image) in that language.
2. **Static validation** (`ci/validate.py _site`): CSP hashes, HTML nesting, unique ids, absolute local paths, safe external links, no third-party resources, structured data, language pages, `robots.txt`, `sitemap.xml`, and no phone number in the pages or the CVs.
3. **Browser test** (`ci/smoke.py _site`): headless Chrome on mobile and desktop widths — right language shown, fonts loaded, no console errors or CSP violations, language switch, pages without JavaScript, language chosen by country (simulated time zones), 404 page.
4. **Deploy**: only if all checks pass, `_site/` is published to GitHub Pages. Pull requests run the checks without publishing.

To check locally: `python ci/build.py && python ci/validate.py _site && python ci/smoke.py _site`. After editing the inline style or script, run `python ci/csp_hash.py index.html`.

Dependabot (`.github/dependabot.yml`) opens a pull request when a workflow action has a new version; the pipeline checks it before merging.
