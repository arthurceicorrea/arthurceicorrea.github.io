# 3. Language by time zone, not by IP address

- Status: accepted
- Date: 2026-11-17

## Context

The site is in Portuguese, English, Spanish and Italian. A visitor who opens the home page should see their own language without having to look for the switcher.

The browser language alone does not say where the visitor is: a phone or computer in Brazil, Italy or Spain may well be set to English.

The common alternative, finding the country from the visitor's IP address, needs a server or a geolocation service. GitHub Pages runs no server code ([ADR 1](0001-github-pages-published-by-github-actions.md)), and a geolocation service would be a third party receiving every visitor's address ([ADR 4](0004-no-third-party-resources-and-no-analytics.md)).

## Decision

[`src/js/language.js`](../../src/js/language.js) chooses the language in the browser, before the first paint, in this order:

1. the `?lang=` parameter (`pt`, `en`, `es`, `it`);
2. the country, inferred from the device time zone (`Intl.DateTimeFormat().resolvedOptions().timeZone`), only for time zones of countries with a clear language: Brazil and Portugal give Portuguese, Italy gives Italian, Spain and the Spanish-speaking countries of America give Spanish;
3. the browser language;
4. English.

The home page is the English edition. When the result is another language, the script takes the visitor to `/pt/`, `/es/` or `/it/` with `location.replace`. The language pages and the switcher always win: on `/it/`, the page is Italian whatever the time zone.

## Consequences

- No request leaves the browser to choose the language: no service, no cookie, no stored data, and it works the same on any static host.
- A VPN does not change the result, since the time zone comes from the device. A traveller whose device still has the home time zone gets the home language; the switcher and the language pages fix it in one click.
- Countries without a clear single language (for example Switzerland or Poland) fall back to the browser language, then English.
- The time zone list has to be maintained by hand in `language.js`. The browser tests simulate eleven country cases, among them Brazil, Portugal, Italy, Spain, Argentina, Mexico, the USA and Poland ([`tests/test_browser.py`](../../tests/test_browser.py)).
- Without JavaScript, the home page stays in English, and every language page still works.
