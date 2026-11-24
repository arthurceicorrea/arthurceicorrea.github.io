# 8. CVs printed by the build, in a legible typeface

- Status: accepted
- Date: 2026-11-24

## Context

Until stage 7 of [`docs/PLAN.md`](../PLAN.md), the four PDF CVs were made by hand and kept in `static/cv/`. They had drifted from the site: they said the Frio Solidário repository was private while the site linked to it, described the owner's role in SellOut EasyTrack differently, named a different area of interest, and each listed facts the other did not have.

They also used fonts that are not in the repository and whose licence does not allow embedding them, so they could not be regenerated as they were.

Two questions had to be settled:

- **When to generate the CVs**: when the site is published, or in the visitor's browser when they click the download link.
- **Which typeface to use**: the site's EB Garamond, or one made for reading.

## Decision

**The build prints the CVs from the page's content.** [`src/cv.html`](../../src/cv.html) is rendered from the same keys of `src/content/<language>.toml` as the page; only the summary title and the page footer are CV-only, in `[resume]`. [`ci/build.py`](../../ci/build.py) opens it in Chrome with Playwright and prints an A4, tagged PDF with an outline into `/cv/`, at every build. The CV's HTML is not published.

Generating the PDF at click time was set aside. The content only changes when the site is published, so the visitor would get the same text either way, and doing it in the browser would mean:

- a PDF library in JavaScript, served by the site ([ADR 4](0004-no-third-party-resources-and-no-analytics.md)), loaded by every visitor;
- PDFs without the structure that screen readers use;
- a file the pipeline cannot check before visitors receive it, which could vary from browser to browser;
- no CV without JavaScript.

**The CV text uses [Atkinson Hyperlegible Next](https://github.com/googlefonts/atkinson-hyperlegible-next)**, designed by the Braille Institute for readers with low vision, with distinct shapes for easily confused characters (I, l and 1; 0 and O). Cinzel stays in the name and the section titles, linking the CV to the site. The site keeps EB Garamond. Labels and dates are upright, not in italics.

## Consequences

- The site and the CVs cannot disagree: the tests look for every page text in the CV of its language, and the build fails before publishing if they differ ([`tests/test_static.py`](../../tests/test_static.py)).
- Changing a text on the page changes the CV at the next publication, with nothing else to edit.
- The build needs Chrome, locally as well as in the pipeline, and takes a few more seconds.
- The CV is easier to read at a glance than with the site's typeface, at the cost of a less classical look than the page.
- The CV fonts are versioned in [`src/fonts/`](../../src/fonts/), with their SIL Open Font License, and are not published.
- A CV must fit in two pages; adding content may need the layout or the texts to be revisited.

WCAG 2.2 does not require any particular typeface: the switch is for readability, not for compliance.
