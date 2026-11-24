# arthurceicorrea.github.io

[![Site](https://github.com/arthurceicorrea/arthurceicorrea.github.io/actions/workflows/site.yml/badge.svg)](https://github.com/arthurceicorrea/arthurceicorrea.github.io/actions/workflows/site.yml)

Personal portfolio of Arthur Cei Corrêa — DevOps, applied AI and security.
One static page in Portuguese, English, Spanish and Italian, published at <https://arthurceicorrea.github.io/>, with a page per language at `/pt/`, `/en/`, `/es/` and `/it/`. It is only published after a pipeline of checks passes.

## What the site does

- **Four languages.** The home page is the English edition. It sends other visitors to their language page, choosing with `?lang=pt`, `?lang=en`, `?lang=es` or `?lang=it`; otherwise the visitor's country, inferred from the device time zone with no external lookup (Brazil and Portugal: PT; Italy: IT; Spain and Spanish-speaking America: ES), then the browser language, then English. Without JavaScript, it stays in English. ([ADR 3](docs/adr/0003-language-by-time-zone-not-ip-address.md))
- **Nothing from third parties.** No frameworks, no third-party scripts, fonts or images, no analytics, no cookies. The fonts, Cinzel and EB Garamond, are self-hosted as WOFF2 under the SIL Open Font License. ([ADR 4](docs/adr/0004-no-third-party-resources-and-no-analytics.md))
- **A restrictive Content Security Policy**, in a meta tag: `style-src 'self'; script-src 'self'`, so no inline styles or scripts run, only files served by the site. ([ADR 2](docs/adr/0002-content-security-policy-in-a-meta-tag-with-self.md))
- **Accessible**: WCAG 2.2 AA, checked on every page by axe and Lighthouse.
- **CVs from the same content.** The four PDF CVs are printed by the build from the same texts as the page, so the site and the CVs always say the same.
- **No phone number, address or health data** in the pages or the CVs; the tests look for phone numbers.

## Running locally

Requirements: Python 3.12, Node 22, Java 21 (for the W3C validator), Google Chrome and `make`.
The build, which prints the CVs, and the browser tests use the system Chrome, or the path in `CHROME_PATH`.

```sh
make setup   # install the tools, at the exact versions in ci/requirements.txt and ci/package-lock.json
make lint    # check code style: Stylelint, ESLint and Prettier on src/css/ and src/js/
make build   # build the site into _site/ (python ci/build.py)
make test    # same checks as the pipeline, in the same order: static tests, W3C HTML validation, browser tests, accessibility tests
make serve   # serve _site/ at http://localhost:8000/
```

- Run `make build` before `make test`: the tests check the site already built in `_site/`.
- To fix the formatting that `make lint` reports, run `ci/node_modules/.bin/prettier --write "src/css/**/*.css" "src/js/**/*.js"`.
- Lighthouse runs only in the pipeline.
- To compare two builds pixel by pixel, for example `main` and a branch, run `python ci/compare_screens.py OLD_SITE NEW_SITE CAPTURES`: it captures every page at 390 and 1440 px and fails if any capture differs.
- If your system has `python3` but no `python`, add `PYTHON=python3` to any command, for example `make build PYTHON=python3`.

## Folder structure

```
src/                    source of the pages
  page.html             the page, written once (Jinja2 template)
  cv.html               the CV, printed to PDF in each language (Jinja2 template; not published)
  404.html              the error page (Jinja2 template)
  content/              every text, one file per language: pt.toml, en.toml, es.toml, it.toml
  css/                  styles, one @layer per file: tokens, base, layout, components, plus 404.css and cv.css
  js/                   language.js (picks the language, before the first paint) and page.js (the rest)
  fonts/                the CV's typeface, Atkinson Hyperlegible Next (not published), with its licence
static/                 files served as they are: fonts/, images, vCard, robots.txt
ci/                     build and pipeline tools
  build.py              builds _site/ from src/ and static/
  monitor.py            checks the live site (after each deploy and weekly)
  compare_screens.py    compares two builds pixel by pixel
  lighthouserc.json     Lighthouse settings; lighthouse_summary.py writes the scores to the run summary
  requirements.txt      Python tools, exact versions
  package.json          Node tools, exact versions; package-lock.json pins every npm package
  stylelint.config.js   Stylelint rules, with the two adjustments explained
  eslint.config.js      ESLint rules
tests/                  pytest tests (see Tests)
docs/
  PLAN.md               the plan this structure came from, stage by stage
  adr/                  architecture decision records (see Decisions)
.github/
  workflows/site.yml    the pipeline: check, publish, check the live site
  workflows/monitor.yml the weekly live check
  dependabot.yml        weekly updates of actions and tools
Makefile                setup, lint, build, test, serve
CLAUDE.md               instructions for the AI assistant used on this repository
```

`_site/`, the built site, is not versioned: the pipeline builds it from scratch on every run.

## Pipeline

Every pull request and every push to `main` runs [`.github/workflows/site.yml`](.github/workflows/site.yml). Nothing reaches `main` without a pull request whose **Validar** job passed ([ADR 6](docs/adr/0006-one-pull-request-per-change-with-required-pipeline.md)), and nothing is published without it ([ADR 1](docs/adr/0001-github-pages-published-by-github-actions.md)).

The **Validar** job:

1. **Code style** (`make lint`): Stylelint (standard config) on `src/css/`, ESLint (recommended rules) on `src/js/` and Prettier on both. The two adjusted Stylelint rules are explained in `ci/stylelint.config.js`.
2. **Build** (`ci/build.py`):
   - stops if a text of `pt.toml` is missing from another language;
   - renders the template into `_site/`: the home page in English, and one page per language, each with only its own edition and with title, description, canonical URL and sharing preview in that language;
   - copies `static/`;
   - joins the styles of `src/css/` into `/assets/site.css` (one `@layer` per file) and copies the scripts of `src/js/` to `/assets/`;
   - prints the four CVs from `src/cv.html` to `/cv/`, with Playwright in Chrome: A4, tagged PDF with an outline, the page texts in each language, and the page numbers in the CV's language; the CV text uses Atkinson Hyperlegible Next, a typeface made for legibility ([ADR 8](docs/adr/0008-cvs-printed-by-the-build-in-a-legible-typeface.md));
   - writes `sitemap.xml` and `version.txt`, and fills in the footer date and year from the last commit.
3. **Static validation** (`tests/test_content.py` and `tests/test_static.py`): every text in all four languages, the exact Content Security Policy, no inline styles or scripts, HTML nesting, unique ids, absolute local paths, safe external links, no third-party resources, structured data, language pages, `robots.txt`, `sitemap.xml`, no phone number in the pages, the CVs or the vCard, and the CVs themselves: all four built, each with its page's texts, at most two pages, page numbers in its language.
4. **W3C HTML validation**: the official Nu Html Checker on every generated page.
5. **Browser test** (`tests/test_browser.py`): headless Chrome on mobile and desktop widths. Checks the right language shown, the home page sending each visitor to their language page, fonts loaded, no console errors or CSP violations, the language switch, pages without JavaScript, the language chosen by country (simulated time zones), the buttons and the 404 page.
6. **Accessibility audit** (`tests/test_a11y.py`): axe-core on every page, mobile and desktop. Any WCAG 2.2 A or AA violation fails the run.
7. **Lighthouse** (`ci/lighthouserc.json`): performance, accessibility, best practices and SEO for each page.
   - Accessibility below 95 or best practices below 90 fail the run.
   - The scores, and the audits that lose points, appear in the run summary, with the full reports kept as an artifact.

Then, on `main` only:

8. **Publicar**: `_site/` is published to GitHub Pages.
9. **Conferir no ar** (`ci/monitor.py`): the live site must serve the commit just deployed (`version.txt`), with every page and file, the custom 404, the HTTP→HTTPS redirect and a valid certificate.

**Monitoring.** [`.github/workflows/monitor.yml`](.github/workflows/monitor.yml) runs the same live check every Monday. If it fails, it opens an issue labelled `monitoramento`; when the site passes again, it closes the issue. GitHub disables scheduled workflows in repositories with no commits for 60 days.

**Dependencies.**
- Workflow actions are pinned to exact commits ([ADR 7](docs/adr/0007-github-actions-pinned-by-commit-hash.md)).
- The build, test and lint tools are pinned to exact versions in `ci/requirements.txt` and `ci/package.json`, and `ci/package-lock.json` pins every npm package, installed with `npm ci`.
- The pipeline caches pip and npm downloads, keyed on those files.
- Dependabot ([`.github/dependabot.yml`](.github/dependabot.yml)) opens a weekly pull request when any of them has a new version, and the pipeline checks it before merging.

## Tests

The tests are in `tests/` and run with [pytest](https://docs.pytest.org/). Each check is a test with a descriptive name. A check that applies to several pages, links or files runs once for each, and the item is shown in brackets, for example `test_local_file_exists[pt/index.html:103:/cv/arthur-cei-correa-cv-pt.pdf]` (page, line, address).

| File | What it checks | Needs |
|---|---|---|
| `tests/test_content.py` | every key of `pt.toml` exists in the other three languages | nothing |
| `tests/test_static.py` | the built HTML and CVs, without a browser: security policy, links, languages, structured data, sitemap, CVs matching the page | `make build` |
| `tests/test_browser.py` | the site in headless Chrome: languages, redirects, switcher, buttons, 404 | `make build` |
| `tests/test_a11y.py` | axe-core accessibility audit, WCAG 2.2 A and AA | `make build`, `make setup` |

```sh
python -m pytest                                  # every test (the W3C validator runs only in make test)
python -m pytest tests/test_static.py             # one file
python -m pytest -k csp                           # tests whose name contains "csp"
python -m pytest -k "test_right_edition_is_visible and pt"   # combine words with and, or, not
python -m pytest --collect-only -q                # list the tests without running them
python -m pytest --site OTHER_FOLDER              # test another build instead of _site/
```

When a test fails, pytest prints a block per failure, starting with the test name, and at the end a `short test summary info` with one line per failure: `FAILED <file>::<test>[<item>] - <message>`. The message, in Portuguese, says what is wrong and where, for example `pt/index.html, linha 130: link externo precisa de target="_blank" rel="noopener noreferrer" (...)`. To run only that test again, copy its name after `python -m pytest`.

External links must be in `ALLOWED_EXTERNAL`, in `tests/helpers.py`.

## Decisions

The main decisions behind the site are recorded in [`docs/adr/`](docs/adr/), each with its context, the decision and its consequences:

1. [GitHub Pages, published only by GitHub Actions](docs/adr/0001-github-pages-published-by-github-actions.md)
2. [Content Security Policy in a meta tag, with `'self'`](docs/adr/0002-content-security-policy-in-a-meta-tag-with-self.md)
3. [Language by time zone, not by IP address](docs/adr/0003-language-by-time-zone-not-ip-address.md)
4. [No third-party resources and no analytics](docs/adr/0004-no-third-party-resources-and-no-analytics.md)
5. [Jinja2 and TOML instead of a site generator or framework](docs/adr/0005-jinja2-and-toml-instead-of-a-site-generator.md)
6. [One pull request per change, with the pipeline required](docs/adr/0006-one-pull-request-per-change-with-required-pipeline.md)
7. [GitHub Actions pinned by commit hash](docs/adr/0007-github-actions-pinned-by-commit-hash.md)
8. [CVs printed by the build, in a legible typeface](docs/adr/0008-cvs-printed-by-the-build-in-a-legible-typeface.md)

## License

The code (HTML structure, CSS, JavaScript and the scripts in `ci/`) is released under the [MIT License](LICENSE).
The texts, the CVs and the images are by Arthur Cei Corrêa, all rights reserved; they are not covered by the MIT License.
The fonts in `static/fonts/` and `src/fonts/` are not by Arthur Cei Corrêa and keep their own SIL Open Font License.
