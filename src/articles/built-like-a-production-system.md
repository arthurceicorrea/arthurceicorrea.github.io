+++
title = "[Sapientis est ordinare]{lang=la}: A Personal Website Built Like a Production System"
date = 2026-11-27

[summary]
en = "How this site is built and run like a production system: every change goes through a pull request and a pipeline of automated checks, with a plan in stages, a strict security policy, actions pinned by commit, infrastructure in Terraform, CVs generated from the site and no trackers or third-party resources; what the process caught, how AI was used, and why the motto."
pt = "Como este site é feito e mantido como um sistema em produção: toda mudança passa por pull request e por um pipeline de verificações automáticas, com um plano em etapas, uma política de segurança restritiva, actions fixadas por commit, infraestrutura em Terraform, currículos gerados a partir do site e nenhum rastreador nem recurso de terceiros; o que o processo apanhou, como a IA foi usada e o porquê do lema."
es = "Cómo este sitio se construye y se mantiene como un sistema en producción: todo cambio pasa por un pull request y por un pipeline de verificaciones automáticas, con un plan por etapas, una política de seguridad restrictiva, actions fijadas por commit, infraestructura en Terraform, currículos generados a partir del sitio y ningún rastreador ni recurso de terceros; lo que el proceso detectó, cómo se usó la IA y el porqué del lema."
it = "Come questo sito viene costruito e gestito come un sistema in produzione: ogni modifica passa da una pull request e da una pipeline di verifiche automatiche, con un piano a tappe, una politica di sicurezza restrittiva, actions fissate per commit, infrastruttura in Terraform, curriculum generati dal sito e nessun tracker né risorsa di terze parti; che cosa ha intercettato il processo, come è stata usata l’IA e il perché del motto."
+++

My personal website presents my portfolio in four languages (Portuguese, English, Spanish and Italian) and, starting with this one, my articles, written in English. It is also, by design, run like a production system. Every change goes through a pull request, nothing ships until a pipeline of automated checks passes, and every significant decision is written down. A small site is the cheapest place to practice the habits that large systems demand.

## Where it started

The first version went live on November 16, 2026, hosted on GitHub Pages. The same day, a GitHub Actions pipeline became the only way into production: it validated the HTML, tested the page in a real browser and published it. Four days later it also began confirming, after every deploy, that the live site was serving that exact commit.

The code behind it was less disciplined than the process around it. All four language editions lived one after another in a single HTML file of about a thousand lines, and the build script cut each language out with regular expressions. Every structural change had to be made four times, and a fix in one language could easily be missed in the other three.

## A staged plan

Instead of rewriting everything at once, I wrote a [plan in stages](https://github.com/arthurceicorrea/arthurceicorrea.github.io/blob/main/docs/PLAN.md) (in Portuguese). Each stage states its goal and what changes, and most also list what is out of scope and give a concrete definition of done. Two rules apply throughout:

- **Visitors shouldn’t notice a thing.** Same design, same content, same quality scores, unless a stage sets out to change them.
- **The existing tests are the safety net.** A test changes only when a stage deliberately changes what it checks, and every such change is explained.

Each stage gets its own branch and at least one pull request, and the next stage doesn’t start until the previous one is merged.

## What changed

Twelve stages, numbered from 0 to 11, came before this article. About half of them rebuilt the site from the inside without changing what visitors see. The rest changed it deliberately: they generated the CVs from the site, refined the typography, moved the site to its own domain, and added a page of thanksgiving and a privacy notice. Five changes say the most about how it works now.

**Protecting the main branch.** The pipeline already kept a broken change from being deployed, but not from landing on `main`. A repository ruleset now requires a pull request for every change and a passing validation job before merge, with force pushes blocked and no bypass list. Since the project has one maintainer, the rule asks for no approvals, only a green pipeline. Protecting the deployment and protecting the branch are different safeguards, and the site now has both.

**A strict Content Security Policy.** The CSS and JavaScript moved out of the HTML into their own files, and the policy went from hashes to `'self'`: everything is denied by default, and only files served by the site itself are allowed. No `'unsafe-inline'`, no `'unsafe-eval'`. To confirm nothing had changed, every page was captured before and after, at 390 and 1440 pixels wide, and compared pixel by pixel.

**Supply chain security.** Every GitHub Action is pinned to a full commit hash instead of a version tag. The risk is real: in March 2025, the `tj-actions/changed-files` action was compromised and its version tags were repointed to malicious code (CVE-2025-30066). A tag can be moved; a commit hash can’t. Dependabot checks every week and opens a pull request when an action has a new version; those pull requests go through the same pipeline as everything else.

**Infrastructure as code.** The site now lives at `arthurceicorrea.dev`, and the old `github.io` address redirects to it. GitHub Pages still hosts the site; Cloudflare answers for the domain. Everything at Cloudflare that can be code is Terraform: the DNS records, the `www` redirect, the security headers that GitHub Pages doesn’t let a site set, such as HSTS and `frame-ancestors` (which a meta tag can’t carry), and records declaring that the domain sends no email, so that mail forged in its name is rejected. Every pull request that touches the infrastructure runs `terraform plan` with read-only credentials. The credentials that can write exist only in my password manager, and I apply each plan myself after the merge, so a leak from the pipeline could change nothing.

**CVs generated from the site.** The PDF CVs used to be made by hand. Now the build prints them from the same content as the page, and the tests fail if the site and a CV disagree. The next section explains why that mattered.

The remaining work made the code safer to change. The pages are now Jinja2 templates, most of them built on one shared layout, with one TOML file per language, and the build fails if a text is missing in any language. I chose not to use a static site generator: the whole build is a few hundred lines of Python, with no conventions of a larger tool to learn. Stylelint, ESLint and Prettier check the code style. Every significant decision has an [architecture decision record (ADR)](https://github.com/arthurceicorrea/arthurceicorrea.github.io/tree/main/docs/adr); there are eleven so far.

The homegrown check scripts became more than 700 pytest tests: static checks, browser tests with Playwright and accessibility audits with axe. Lighthouse runs in the pipeline too and fails the build if the accessibility score drops below 95. On the run that published the privacy notice, all thirteen pages scored 100 for accessibility, best practices and SEO, and 99 or 100 for performance. A full run, from the first check to the confirmation on the live site, takes about six minutes.

## What the process caught

A process like this earns its keep when it catches what a person would miss. A few examples:

- **The CVs had drifted from the site.** Comparing them turned up real contradictions: they called the Frio Solidário repository private while the site linked to it, described my role in SellOut EasyTrack differently, and named a different area of interest. Worse, they used fonts whose license did not allow embedding, so they could not even be regenerated as they were. Generating them from the site’s content ended the drift. The test that guards them writes out the expected footers itself rather than reading them from the content files, so it cannot pass merely because it shares a source with the build.
- **The repository’s own policy stopped the Terraform setup.** The repository only allows actions published by GitHub and by its owner, so the official action that installs Terraform was refused. Instead of opening an exception in the policy, the pipeline now downloads the Terraform release directly and verifies it against its published SHA-256 checksum.
- **The accessibility audit was measuring the wrong moment.** The thanksgiving page fades its text in slowly, and halfway through a fade the text is still translucent, so the contrast measured then is not the contrast the visitor reads. The audit now waits for the animations to finish and checks the page at rest.
- **The linters found leftovers.** Stylelint exposed a duplicated CSS rule, left behind when the styles were split into files in stage 2. It also flagged two things that were intentional: vendor prefixes and the older media query syntax, both still needed by older versions of Safari and Chrome. The two rules behind those warnings were adjusted, with the reason written in the config, instead of being switched off.

## Principles behind the project

- **No third parties in the page.** Fonts, scripts and images all come from the site itself, as the security policy requires. There are no analytics, no cookies and no trackers. A short [privacy notice](https://arthurceicorrea.dev/en/privacy/) states what Cloudflare and GitHub receive from a visit, and a check on the live site fails if any response ever sets a cookie.
- **Language detection without tracking.** The visitor’s language is chosen on the device itself, from its time zone and browser language, not from the IP address, which would mean sending every visitor’s address to a geolocation service.
- **Accessibility.** WCAG 2.2 AA, checked on every change.
- **No personal data on display.** No phone number or home address on the pages or the CVs, and the tests scan for phone numbers.

## On using AI

The code in this project is written with an AI agent, and the repository says so. The instructions the agent works under are public too, in [`CLAUDE.md`](https://github.com/arthurceicorrea/arthurceicorrea.github.io/blob/main/CLAUDE.md). I conceived and lead the project, setting the requirements, the pipeline checks and the priorities for each improvement. The agent’s work goes through the same pull requests and the same pipeline as everything else. I wrote about the principle behind this in an earlier essay, *[From Purism to Prudence: Artificial Intelligence and the Right Order of Means](https://arthurceicorrea.dev/en/articles/from-purism-to-prudence/)*: the instrument serves the intellect, and AI-suggested code must be read, tested and understood before it reaches production. Directing an AI agent within a disciplined process, with a defined scope, clear acceptance criteria and automated verification, is part of the job today, and I see no reason to hide it.

## What comes next

This article opens the new articles section, built in stage 12. Articles are written in Markdown and in English, and listed in the four languages. Alongside this article, *From Purism to Prudence*, which until now was only on LinkedIn, moves to the site with its original date. The next stage brings the latest articles to the home page and lets me choose which ones appear on my CV.

I’ll post a short note on LinkedIn as each stage ships. Longer pieces will appear here, and the [Atom feed](https://arthurceicorrea.dev/feed.xml) is the easiest way to follow them.

## Why the motto

*[Sapientis est ordinare]{lang=la}*, «it belongs to the wise to order», comes from the first chapter of St. Thomas Aquinas’s *Summa contra Gentiles*, where he takes it from Aristotle. In his thought it reaches to the ordering of all things to their end, the virtues included, and I try to live by it in that breadth. As a motto, though, I adopted it with my work as a software engineer in mind, and this site is one instance of it: every part has a reason to be where it is, and every decision can be explained.

The home page opens with that motto, and every footer begins with a colophon: *[Non nisi te, Domine]{lang=la}*, the answer St. Thomas is said to have given when Christ asked him what reward he wanted. The colophon links to a short page of thanksgiving.

The site’s repository is public at [github.com/arthurceicorrea/arthurceicorrea.github.io](https://github.com/arthurceicorrea/arthurceicorrea.github.io).
