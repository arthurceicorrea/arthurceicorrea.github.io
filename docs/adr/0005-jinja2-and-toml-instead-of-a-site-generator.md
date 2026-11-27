# 5. Jinja2 and TOML instead of a site generator or framework

- Status: accepted; extended by [ADR 11](0011-articles-in-markdown-in-english-built-by-the-same-script.md), which answers the last consequence below for articles
- Date: 2026-11-24

## Context

Until stage 3 of [`docs/PLAN.md`](../PLAN.md), the site was one `index.html` of about 1,070 lines holding the four language editions one after another. The build script cut each language page out of it with regular expressions. A change in structure had to be made four times, and a text could be fixed in one language and forgotten in another.

The site is one page in four languages plus an error page. The plan rules out any framework running in the browser, and keeps build and test tools allowed.

## Decision

The page is written once, as a [Jinja2](https://jinja.palletsprojects.com/) template, and its texts live in one [TOML](https://toml.io/) file per language:

- [`src/page.html`](../../src/page.html) and [`src/404.html`](../../src/404.html) hold the structure;
- [`src/content/{pt,en,es,it}.toml`](../../src/content/) hold every text; projects are a list, so adding one is adding a `[[projects]]` block;
- [`ci/build.py`](../../ci/build.py), about 200 lines of Python, renders one page per language and the home page, copies `static/`, joins the CSS, and writes the sitemap and `version.txt`.

No static site generator (such as Hugo, Eleventy or Astro) and no front-end framework.

## Consequences

- The only new dependencies are Jinja2 and MarkupSafe, pinned to exact versions; TOML is read by `tomllib`, part of Python since 3.11. The pipeline already used Python for its tests.
- The whole build fits in one file that can be read in a few minutes, with no conventions of a larger tool to learn.
- Jinja2 escapes every text by default; only the few `_html` fields that carry a link go in as markup.
- The build stops if a key of `pt.toml` is missing from another language, and `tests/test_content.py` runs the same check as a test.
- Features a generator gives for free (blog posts, pagination, image processing, plugins) would have to be written by hand. If the site grows beyond one page, this record should be revisited.
