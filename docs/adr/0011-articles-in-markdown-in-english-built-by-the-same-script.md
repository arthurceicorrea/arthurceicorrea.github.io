# 11. Articles in Markdown, in English, built by the same script

- Status: accepted
- Date: 2026-11-27; context corrected the same day (the first article); amended the same day (the language of a passage, and the essay leaving LinkedIn)
- Extends: [ADR 5](0005-jinja2-and-toml-instead-of-a-site-generator.md)

## Context

The owner will publish articles regularly: on the site first, then on LinkedIn, with a summary and the link. The site opens its articles with a presentation of the site and the project. With it comes an essay already on LinkedIn, *From Purism to Prudence: Artificial Intelligence and the Right Order of Means* (24 August 2026). Until now the site only pointed to the essay: its title, address and date were a constant in `ci/build.py`, and its summary lived in the four content files.

The articles are written in English only. The rest of the site, interface and presentation included, stays in Portuguese, English, Spanish and Italian, under the rule that a text changed in one language is changed in all four.

[ADR 5](0005-jinja2-and-toml-instead-of-a-site-generator.md) chose Jinja2 and TOML over a site generator for a one-page site, and said it should be revisited if the site grew beyond one page. Articles are that growth. Four questions had to be settled: where the articles are stored, in what format, how they are built, and how an English-only text sits in a four-language site.

## Decision

**Each article is a Markdown file in the repository**, `src/articles/<slug>.md`, whose name is its address. A TOML header between `+++` lines, read by `tomllib` like the content files, holds the title, the date, an optional update date, an optional LinkedIn address and the summary in the four languages. The body is CommonMark.

**The body is rendered by [markdown-it-py](https://github.com/executablebooks/markdown-it-py)** (4.3.0, with its only dependency, mdurl 0.1.2, both pinned), with the `commonmark` preset and raw HTML turned off. Any HTML written in an article comes out escaped, so no article can add a `<script>`, a `style=` or an `on…=` attribute, and the Content Security Policy ([ADR 2](0002-content-security-policy-in-a-meta-tag-with-self.md)) and its tests hold for articles without exception.

**The language of a passage is the one markup beyond CommonMark.** The site marks Latin with `lang="la"`, and WCAG 2.2 success criterion 3.1.2 (Language of Parts, level AA) asks that the language of each passage be programmatically determinable; the first two articles carry Latin and transliterated Greek. The `attrs` plugin of [mdit-py-plugins](https://github.com/executablebooks/mdit-py-plugins) (0.7.0, pinned) turns `[Sapientis est ordinare]{lang=la}` into `<span lang="la">…</span>`, in the body and in the title. The plugin would accept any attribute, so the build accepts `lang` alone and stops on any other (`style`, `class`, `id`, `title`); event attributes are dropped by the plugin itself, and a test checks they never reach the page. Where the title is used as plain text (the page title, the share preview, the structured data, the feed), the markup is removed.

**The same build script builds them**, with the new code in its own module, `ci/articles.py`, and every page (portfolio, thanksgiving, privacy, article lists, articles) entered in one table in `ci/build.py`, from which the addresses, `canonical`, `hreflang` and the sitemap are derived.

**Articles are English only; their presentation is in four languages:**

- the article page, at `/en/articles/<slug>/`, is entirely in English, including its frame, and declares no `hreflang`, since no other version exists; the language switcher there leads to the article list in each other language;
- the article lists, at `/pt/artigos/`, `/en/articles/`, `/es/articulos/` and `/it/articoli/`, show the same articles with the interface in their language: the title in English, marked `lang="en"`, the summary in the list's language, and, in the three non-English lists, a sentence saying the articles are written in English;
- the summary is presentation, so it is required in the four languages, and the build stops if one is missing, as it does for the content files.

**One Atom feed**, `/feed.xml`, with `tag:` URIs ([RFC 4151](https://www.rfc-editor.org/rfc/rfc4151)) as identifiers instead of addresses, so a future change of address does not make readers see every article again as new.

**A published slug never changes.** A list of published addresses, `tests/published.txt`, makes the tests fail if one disappears.

## Alternatives considered

- **An external database, relational or not.** GitHub Pages runs no server code ([ADR 1](0001-github-pages-published-by-github-actions.md)), so a database could only be read in two ways. Read by the visitor's browser, every visit would send the visitor's address to a third party ([ADR 4](0004-no-third-party-resources-and-no-analytics.md)), the policy would have to allow another origin, a key would be public in the JavaScript, and without JavaScript, or for search engines and link previews, there would be no article. Read by the build, the same commit could produce different sites, and an article fix would reach the site without a pull request or the pipeline ([ADR 6](0006-one-pull-request-per-change-with-required-pipeline.md)). Size was the reason to consider it, and it does not apply: an essay is some 20 to 25 KB of text; the whole repository, with its history, was 614 KiB when this was decided; GitHub recommends repositories under 10 GB and files under 1 MB, and limits a published Pages site to 1 GB. Git already gives the articles what a database would: history, authorship, review.
- **A site generator** (Pelican, Hugo, Zola, Eleventy). Each gives articles and feeds for free, but would mean rewriting every template, the four-language content check, the CV printing and the tests that import the build, for a list, a feed and a few pages.
- **Python-Markdown**, the best-known library: it does not follow CommonMark and passes raw HTML through, with no safe mode since version 3, so it would need a sanitizer. **mistune**: smaller and fast, with less use. **Pandoc**: a separate program to install in the pipeline.
- **Translated articles**, and folders per language for them: not needed, since the owner writes in English only.
- **Leaving Latin and Greek in articles unmarked**, with the article body exempt from the test that requires `lang="la"`: no new package, but a WCAG gap the rest of the site does not have, and screen readers would read the Latin with English pronunciation.

## Consequences

- Writing an article is adding one file and one line in `tests/published.txt`, through a pull request like any other change; the pipeline checks it before it is published.
- The build code is about 650 lines in all after this decision, some 230 of them in `ci/articles.py`, docstrings included. Three packages are added to `ci/requirements.txt`.
- A passage in another language is written `[text]{lang=xx}`, inside the emphasis if it is italic: `*[telos]{lang=grc-Latn}*`.
- An article cannot carry HTML of its own: tables, embeds or styled blocks would need a Markdown plugin, pinned, or a change of this record.
- Each article must have its summary in four languages; the text itself, never.
- Links in an article body may point anywhere over `https`, without the `ALLOWED_EXTERNAL` list that governs the interface, but open in the same tab and load nothing.
- Revisit this record, and the choice of a generator, when the site needs categories, pagination or search, when articles need image processing, when the build code passes about 800 lines in all, or when an article is to be translated (it would get its own address, and only then `hreflang` and `workTranslation`).

## Sources

- GitHub Docs, [Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits) and [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
- markdown-it-py, [documentation](https://markdown-it-py.readthedocs.io/): the `html` option and link validation.
- mdit-py-plugins, [attrs plugin](https://mdit-py-plugins.readthedocs.io/en/latest/#attributes).
- W3C, [Understanding WCAG 2.2: Language of Parts (3.1.2)](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html).
- T. Kindberg and S. Hawke, [RFC 4151: The 'tag' URI Scheme](https://www.rfc-editor.org/rfc/rfc4151).
