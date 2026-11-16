# arthurceicorrea.github.io

Personal portfolio of Arthur Cei Corrêa — DevOps, applied AI and security.
One static page in Portuguese, English, Spanish and Italian, published at <https://arthurceicorrea.github.io/>.

- No frameworks, no third-party scripts, fonts or trackers; a restrictive Content Security Policy with hashes for the inline style and script.
- Choose the language with `?lang=pt`, `?lang=en`, `?lang=es` or `?lang=it`; otherwise the browser language is used, falling back to English.
- Fonts: Cinzel and EB Garamond, self-hosted as WOFF2 under the SIL Open Font License (see `fonts/`).

## Pipeline

Every push to `main` runs [`.github/workflows/site.yml`](.github/workflows/site.yml):

1. **Static validation** (`ci/validate.py`): CSP hashes, HTML nesting, unique ids, safe external links, no third-party resources, local files present, parity of the four language editions, and no phone number in the page or the CVs.
2. **Browser test** (`ci/smoke.py`): headless Chrome in each language, on mobile and desktop widths — right edition shown, fonts loaded, no console errors or CSP violations, language switch, CV buttons, no horizontal scroll.
3. **Deploy**: only if both pass, the site is published to GitHub Pages. Pull requests run the checks without publishing.
