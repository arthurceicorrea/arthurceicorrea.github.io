"""Validação estática do site montado por ci/build.py (antes: ci/validate.py).

Confere, sem navegador, em todas as páginas (inicial, 404 e uma por idioma): a política de
segurança (CSP) exatamente como definida, nenhum estilo ou script embutido (só os dados
estruturados), aninhamento do HTML, ids únicos, ausência de atributos style e on...,
links externos seguros, nenhum recurso de terceiros, caminhos locais absolutos e existentes,
e dados estruturados. Na página inicial, só a edição em inglês, marcada (data-home) para o
script levar cada visitante à página do seu idioma; na 404, a paridade das quatro edições;
nas páginas por idioma, uma só edição, idioma fixo, endereço canônico e prévia de
compartilhamento no idioma certo. Na página de agradecimento (/pt/gratiarum-actio/ e as outras
três), o mesmo, com endereços por idioma próprios, o seletor levando à mesma página nos outros
idiomas e o link de volta à página inicial. O colofão do rodapé: link para o agradecimento no
idioma da página (na página inicial, o inglês), sem link no próprio agradecimento, e ausente da
404. A página de privacidade (/pt/privacidade/, /en/privacy/, /es/privacidad/, /it/privacy/): o
mesmo, com o endereço traduzido, os links das duas políticas e o e-mail; a frase de privacidade
do rodapé, link para ela no idioma da página; e nenhum script do site que guarde algo no navegador
ou envie algo a outro lugar. Os artigos: os endereços publicados (tests/published.txt) existem; a
página de cada artigo, só em inglês, sem hreflang, sem seletor de idioma, com a trilha no topo
(Home / Articles), os links do fim para as outras listas, o tempo de leitura e os dados estruturados
do artigo e da trilha; as quatro listas, com a trilha no idioma da lista, cada artigo, o resumo no
idioma da lista e a frase sobre o inglês; o feed; os links no corpo dos artigos (só https, na mesma aba, nada carregado);
e, na página inicial, o artigo mais recente. O latim: todo trecho marcado com lang="la" e idêntico
nos quatro idiomas. Toda página do sitemap.xml está na lista dos testes (PAGES). Por fim,
robots.txt, sitemap.xml, versão publicada, a fonte do negrito (EB Garamond semibold), a ausência de telefone nas páginas, nos currículos e no
cartão de contato, e os currículos gerados: os quatro existem, trazem os textos da página no seu
idioma (resumo, formação e experiência, projetos, competências, idiomas e o resumo do ensaio), cabem em duas
páginas e numeram as páginas no idioma do currículo.

Testes que valem para várias páginas, links ou arquivos rodam uma vez para cada um; o item
aparece entre colchetes no nome do teste, por exemplo test_local_file_exists[pt/index.html:142:/cv/...].

Uso: make build && python -m pytest tests/test_static.py
"""
import datetime
import functools
import html
import math
import os
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import pytest

import helpers
from helpers import (ALLOWED_EXTERNAL, ARTICLE_LISTS, ARTICLE_PAGES, CODES, GRATIARUM, GRATIARUM_PAGES, LANGUAGE_PAGES, LANGS,
                     LIST_PAGES, LOCALES, PAGES, PHONE, POLICY, PRIVACY, PRIVACY_PAGES, RESOURCE_TAGS, VOID, page)

helpers.require_site()

on_every_page = pytest.mark.parametrize('name', list(PAGES))
on_pages_with_data = pytest.mark.parametrize('name', [n for n in PAGES if n != '404.html'])
on_language_pages = pytest.mark.parametrize('name', list(LANGUAGE_PAGES))


def article_day(header, field):
    """Data de um artigo: date ou, para "updated", a de revisão se houver, senão a de publicação."""
    return header.get(field) or header['date']


def short(url, size=70):
    return url if len(url) <= size else url[:size - 1] + '…'


def links(kind):
    """(página, etiqueta, atributos, linha, endereço) de cada endereço externo ou local, com o id do teste.
    Os links no corpo dos artigos ficam de fora: têm regras próprias (links no corpo, mais abaixo)."""
    found = []
    for name in PAGES:
        for tag, a, line, url in page(name).links():
            external = url.startswith(('http://', 'https://'))
            local = not external and not url.startswith(('mailto:', '#', '?', 'data:'))
            if (kind == 'external' and external) or (kind == 'external-a' and external and tag == 'a') or (kind == 'local' and local):
                found.append(pytest.param(name, tag, a, line, url, id='%s:%d:%s' % (name, line, short(url))))
    return found


def font_urls():
    return [pytest.param(name, url, id='%s:%s' % (name, url))
            for name in PAGES for url in re.findall(r'url\("([^"]+)"\)', page(name).styles)]


def edition_attributes(name, tag):
    found = re.search(r'<div class="t" lang="%s"\s+data-title="([^"]+)"\s+data-desc="([^"]+)">' % re.escape(tag), page(name).raw)
    return (found.group(1), found.group(2)) if found else (None, None)


def image_exists(url):
    return bool(url) and url.startswith(helpers.base()) and os.path.isfile(helpers.path(url[len(helpers.base()):]))


def footer_dates():
    """Datas (<time>) e anos do rodapé de cada página com conteúdo."""
    stamps = {}
    for name in [n for n in PAGES if n != '404.html']:
        text = page(name).raw
        text = text[text.find('<footer'):]  # só a data do rodapé; outras datas (o artigo) ficam de fora
        stamps[name] = (re.findall(r'<time datetime="([^"]+)">', text), re.findall(r'<span class="year">(\d{4})</span>', text))
    return stamps


# ---------- política de segurança (CSP) e código embutido ----------

@on_every_page
def test_line_endings_are_lf(name):
    assert '\r' not in page(name).raw, '%s: há quebras de linha CRLF; use LF' % name


@on_every_page
def test_no_inline_style_block(name):
    assert not re.search(r'<style[\s>]', page(name).code), '%s: há um bloco <style> embutido; o CSS vai em src/css/' % name


@on_every_page
def test_no_inline_script_except_structured_data(name):
    inline = [attrs for attrs, content in re.findall(r'<script\b([^>]*)>(.*?)</script>', page(name).code, flags=re.S)
              if 'src=' not in attrs and attrs.strip() != 'type="application/ld+json"']
    assert not inline, '%s: há script embutido além do JSON-LD (atributos: %s); o JavaScript vai em src/js/' % (name, inline)


@on_every_page
def test_csp_meta_is_present(name):
    assert page(name).csp is not None, '%s: falta a meta tag Content-Security-Policy' % name


@on_every_page
def test_csp_is_exactly_the_policy(name):
    assert page(name).csp == POLICY, '%s: política diferente da definida.\n  na página: %s\n  esperada:  %s' % (name, page(name).csp, POLICY)


@on_every_page
def test_csp_is_restrictive(name):
    csp = page(name).csp or ''
    assert "default-src 'none'" in csp and 'unsafe-inline' not in csp and 'unsafe-eval' not in csp, \
        "%s: a política precisa de default-src 'none' e não pode ter unsafe-inline nem unsafe-eval: %s" % (name, csp)


@on_every_page
def test_no_inline_style_attribute(name):
    found = re.search(r'\sstyle\s*=', page(name).code)
    assert not found, '%s: atributo style embutido (posição %d); use uma classe e o CSS' % (name, found.start() if found else 0)


@on_every_page
def test_no_inline_event_handler(name):
    found = re.search(r'\son[a-z]+\s*=', page(name).code)
    assert not found, '%s: manipulador de evento embutido (%s); use src/js/' % (name, found.group(0).strip() if found else '')


# ---------- estrutura do HTML e edições ----------

@on_every_page
def test_html_tags_are_well_nested(name):
    p = page(name).parsed
    assert not p.errors and not p.stack, '%s: etiquetas mal aninhadas: %s' % (name, p.errors[:3] or ['sem fechamento: %s' % p.stack[:3]])


@on_every_page
def test_ids_are_unique(name):
    ids = page(name).parsed.ids
    dups = sorted({i for i in ids if ids.count(i) > 1})
    assert not dups, '%s: ids repetidos: %s' % (name, dups)


@pytest.mark.parametrize('name', [n for n, e in PAGES.items() if e])
def test_only_its_edition_is_present(name):
    p, edition = page(name), PAGES[name]
    others = sorted({a.get('lang') for tag, a, line in p.tags if a.get('class') == 't' and a.get('lang') != edition})
    assert p.parsed.counts[edition], '%s: a edição %s não está na página' % (name, edition)
    assert not others, '%s: deveria ter só a edição %s, mas tem também: %s' % (name, edition, others)


@pytest.mark.parametrize('name', [n for n, e in PAGES.items() if e is None])
def test_four_editions_have_the_same_structure(name):
    counts = page(name).parsed.counts
    shapes = [counts[lang] for lang in LANGS]
    assert all(shapes) and all(s == shapes[0] for s in shapes), \
        '%s: as edições têm estruturas diferentes (etiquetas por edição: %s)' % (name, {lang: sum(counts[lang].values()) for lang in LANGS})


@on_every_page
def test_one_stylesheet_from_assets(name):
    sheets = page(name).stylesheets
    assert len(sheets) == 1 and sheets[0].startswith('/assets/'), '%s: esperada uma folha de estilo em /assets/, encontradas: %s' % (name, sheets)


@on_every_page
def test_local_paths_are_absolute(name):
    p = page(name)
    relative = [url for tag, a, line, url in p.links() if not url.startswith(('/', '#', 'data:', 'http://', 'https://', 'mailto:'))]
    relative += [u for u in re.findall(r'url\("([^"]+)"\)', p.raw + p.styles) if not u.startswith('/')]
    assert not relative, '%s: caminhos relativos quebram nas pastas /pt/ etc. e na 404; use caminhos que começam com /: %s' % (name, relative)


# ---------- links e recursos ----------

@pytest.mark.parametrize('name, tag, attrs, line, url', links('external'))
def test_external_url_is_allowed(name, tag, attrs, line, url):
    assert url.startswith(ALLOWED_EXTERNAL), \
        '%s, linha %d: endereço externo fora da lista ALLOWED_EXTERNAL (tests/helpers.py): %s' % (name, line, url)


@pytest.mark.parametrize('name, tag, attrs, line, url', links('external'))
def test_external_url_is_not_loaded_as_a_resource(name, tag, attrs, line, url):
    resource = tag in RESOURCE_TAGS or (tag == 'link' and attrs.get('rel') not in ('canonical', 'alternate'))
    assert not resource, '%s, linha %d: <%s> carrega um recurso de terceiros: %s; sirva-o pelo próprio site' % (name, line, tag, url)


@pytest.mark.parametrize('name, tag, attrs, line, url', links('external-a'))
def test_external_link_has_safe_target_and_rel(name, tag, attrs, line, url):
    assert attrs.get('target') == '_blank' and attrs.get('rel') == 'noopener noreferrer', \
        '%s, linha %d: link externo precisa de target="_blank" rel="noopener noreferrer" (tem target=%r, rel=%r): %s' % (
            name, line, attrs.get('target'), attrs.get('rel'), url)


@pytest.mark.parametrize('name, tag, attrs, line, url', links('local'))
def test_local_file_exists(name, tag, attrs, line, url):
    assert os.path.isfile(helpers.local_file(url)), '%s, linha %d: o arquivo de %s não existe no site montado' % (name, line, url)


@pytest.mark.parametrize('name, url', font_urls())
def test_font_file_exists(name, url):
    assert os.path.isfile(helpers.local_file(url)), '%s: a folha de estilo cita %s, que não existe no site montado' % (name, url)


def test_semibold_font_is_declared_and_exists():
    """O negrito é o EB Garamond semibold, arquivo próprio (Etapa 14), e não um negrito simulado."""
    css = helpers.read('assets', 'site.css')
    face = re.search(r'@font-face\s*\{[^}]*font-family:\s*"EB Garamond";[^}]*font-weight:\s*600;[^}]*'
                     r'src:\s*url\("/fonts/eb-garamond-600\.woff2"\)[^}]*\}', css)
    strong = re.search(r'strong,\s*b\s*\{\s*font-weight:\s*600;', css)
    with open(helpers.local_file('/fonts/eb-garamond-600.woff2'), 'rb') as f:
        magic = f.read(4)
    assert face and strong and magic == b'wOF2', 'falta o EB Garamond semibold: @font-face %s, strong %s, arquivo %r' % (bool(face), bool(strong), magic)


@on_every_page
def test_no_phone_number_in_page_text(name):
    found = PHONE.search(re.sub(r'<[^>]+>', ' ', page(name).body))
    assert not found, '%s: parece haver um telefone no texto: %r' % (name, found.group(0) if found else '')


# ---------- dados estruturados (JSON-LD) ----------

@on_pages_with_data
def test_one_structured_data_block(name):
    assert len(page(name).json_ld_blocks()) == 1, '%s: esperado um bloco application/ld+json, encontrados %d' % (name, len(page(name).json_ld_blocks()))


@on_pages_with_data
def test_structured_data_is_valid_json(name):
    assert page(name).structured_data() is not None, '%s: o bloco de dados estruturados não é JSON válido' % name


@on_pages_with_data
def test_structured_data_describes_the_person_and_the_site(name):
    nodes = page(name).structured_data() or []
    people = [n for n in nodes if n.get('@type') == 'Person']
    data = people[0] if people else {}
    assert len(people) == 1 and data.get('name') and data.get('url') == helpers.base(), \
        '%s: esperado um nó Person com nome e url %s; tipos encontrados: %s' % (name, helpers.base(), [n.get('@type') for n in nodes])


@on_pages_with_data
def test_listed_profiles_are_allowed(name):
    profiles = page(name).person().get('sameAs', [])
    assert all(u.startswith(ALLOWED_EXTERNAL) for u in profiles), '%s: perfil fora da lista permitida: %s' % (name, profiles)


@on_pages_with_data
def test_listed_articles_are_by_the_author(name):
    nodes = page(name).structured_data() or []
    person = page(name).person()
    works = [n for n in nodes if n.get('@type') == 'Article']
    assert all(w.get('url', '').startswith(ALLOWED_EXTERNAL) and w.get('author', {}).get('@id') == person.get('@id') for w in works), \
        '%s: artigo sem autor certo ou com endereço não permitido: %s' % (name, [w.get('url') for w in works])


# ---------- página inicial ----------

def test_home_page_is_english_and_marked_to_redirect():
    assert '<html lang="en" data-home>' in page('index.html').raw, \
        'index.html: a página inicial deve começar com <html lang="en" data-home>, que o script de idioma usa para redirecionar'


def test_skip_link_target_exists():
    body = page('index.html').body
    assert '#conteudo' not in body or ' id="conteudo"' in body, 'index.html: o link "Ir para o conteúdo" aponta para #conteudo, que não existe'


@pytest.mark.parametrize('code', list(CODES))
def test_home_links_to_cv(code):
    assert ('href="/cv/arthur-cei-correa-cv-%s.pdf"' % code) in page('index.html').body, 'index.html: falta o link para o currículo em %s' % code


@pytest.mark.parametrize('code', list(CODES))
def test_home_switcher_links_to_language_page(code):
    assert ('<a href="/%s/" data-lang="%s"' % (code, code)) in page('index.html').body, 'index.html: o seletor não leva a /%s/' % code


def test_canonical_url_is_declared():
    assert page('index.html').canonical, 'index.html: falta <link rel="canonical">'


def test_home_alternates_point_to_language_pages():
    assert page('index.html').alternates == helpers.expected_alternates(), \
        'index.html: versões por idioma (hreflang) diferentes do esperado: %s' % page('index.html').alternates


def test_home_share_image_exists():
    image = page('index.html').meta('og:image')
    assert image_exists(image), 'index.html: a imagem de compartilhamento (og:image) não existe: %s' % image


# ---------- páginas por idioma ----------

@on_language_pages
def test_language_page_was_built(name):
    assert os.path.isfile(helpers.path(name)), '%s não foi gerada pelo build' % name


@on_language_pages
def test_html_element_has_fixed_language(name):
    code, tag = LANGUAGE_PAGES[name]
    assert ('<html lang="%s" data-lang="%s">' % (tag, code)) in page(name).raw, '%s: esperado <html lang="%s" data-lang="%s">' % (name, tag, code)


@on_language_pages
def test_title_is_in_page_language(name):
    title, desc = edition_attributes(name, LANGUAGE_PAGES[name][1])
    found = re.search(r'<title>([^<]*)</title>', page(name).raw)
    got = found.group(1) if found else None
    assert got == title, '%s: <title> %r difere do título da edição %r' % (name, got, title)


@on_language_pages
def test_description_and_preview_are_in_page_language(name):
    p = page(name)
    title, desc = edition_attributes(name, LANGUAGE_PAGES[name][1])
    got = (p.meta('description'), p.meta('og:description'), p.meta('og:title'))
    assert got == (desc, desc, title), '%s: descrição e prévia (description, og:description, og:title) fora do idioma da página: %s' % (name, got)


@on_language_pages
def test_og_locale_matches_page(name):
    code = LANGUAGE_PAGES[name][0]
    assert page(name).meta('og:locale') == LOCALES[code], '%s: og:locale %r, esperado %r' % (name, page(name).meta('og:locale'), LOCALES[code])


@on_language_pages
def test_canonical_url_is_the_page_itself(name):
    url = helpers.base() + LANGUAGE_PAGES[name][0] + '/'
    p = page(name)
    assert p.canonical == url and p.meta('og:url') == url, '%s: canonical %r e og:url %r, esperado %r' % (name, p.canonical, p.meta('og:url'), url)


@on_language_pages
def test_same_alternates_as_home(name):
    assert page(name).alternates == helpers.expected_alternates(), '%s: versões por idioma (hreflang) diferentes: %s' % (name, page(name).alternates)


@on_language_pages
def test_share_image_exists(name):
    p = page(name)
    assert image_exists(p.meta('og:image')) and p.meta('twitter:image') == p.meta('og:image'), \
        '%s: imagem de compartilhamento ausente ou diferente entre og:image e twitter:image: %s' % (name, p.meta('og:image'))


@on_language_pages
def test_switcher_marks_page_language(name):
    code, tag = LANGUAGE_PAGES[name]
    raw = page(name).raw
    link = '<a href="/%s/" data-lang="%s" lang="%s" hreflang="%s" aria-current="true">' % (code, code, tag, tag)
    assert link in raw and raw.count('aria-current="true"') == 1, '%s: o seletor deve marcar só %s com aria-current' % (name, code.upper())


@on_language_pages
def test_page_has_its_cv_button(name):
    code = LANGUAGE_PAGES[name][0]
    assert ('href="/cv/arthur-cei-correa-cv-%s.pdf"' % code) in page(name).body, '%s: falta o botão do currículo em %s' % (name, code)


@on_language_pages
def test_same_structured_data_as_home(name):
    assert page(name).person() == page('index.html').person(), '%s: dados estruturados da pessoa diferentes dos da página inicial' % name


# ---------- rodapé e versão ----------

def test_same_update_date_on_every_page():
    stamps = footer_dates()
    dates = {d for found, _ in stamps.values() for d in found}
    assert len(dates) == 1 and len(stamps['index.html'][0]) == 1, 'datas de atualização diferentes entre as páginas: %s' % stamps


def test_update_date_is_not_in_the_future():
    dates = {d for found, _ in footer_dates().values() for d in found}
    assert len(dates) == 1, 'datas de atualização diferentes entre as páginas: %s' % dates
    day = datetime.date.fromisoformat(dates.pop())
    assert day <= datetime.date.today() + datetime.timedelta(days=1), 'data de atualização no futuro: %s' % day


def test_footer_year_is_the_update_year():
    stamps = footer_dates()
    dates = {d for found, _ in stamps.values() for d in found}
    years = {y for _, found in stamps.values() for y in found}
    assert len(dates) == 1 and years == {dates.pop()[:4]}, 'ano do rodapé %s diferente do ano da atualização' % years


def test_version_file_names_the_published_commit():
    name = helpers.path('version.txt')
    version = open(name, encoding='utf-8').read().strip() if os.path.isfile(name) else ''
    assert re.fullmatch(r'[0-9a-f]{40}|local', version), 'version.txt deveria ter o commit publicado (40 caracteres hexadecimais): %r' % version


# ---------- página de erro ----------

def test_404_page_is_not_indexed():
    assert '<meta name="robots" content="noindex">' in page('404.html').raw, '404.html: falta <meta name="robots" content="noindex">'


# ---------- robots.txt e sitemap.xml ----------

SITEMAP = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'x': 'http://www.w3.org/1999/xhtml'}


def sitemap_urls():
    return ET.parse(helpers.path('sitemap.xml')).findall('s:url', SITEMAP)


def test_robots_points_to_the_sitemap():
    assert 'Sitemap: %ssitemap.xml' % helpers.base() in helpers.read('robots.txt'), 'robots.txt não aponta para %ssitemap.xml' % helpers.base()


def test_sitemap_is_well_formed():
    try:
        sitemap_urls()
    except ET.ParseError as error:
        pytest.fail('sitemap.xml não é XML bem formado: %s' % error)


def test_sitemap_lists_home_language_thanksgiving_privacy_and_article_pages():
    locs = [u.find('s:loc', SITEMAP).text for u in sitemap_urls()]
    expected = ([helpers.base()] + [helpers.base() + code + '/' for code in CODES]
                + [helpers.base() + code + '/' + GRATIARUM for code in CODES]
                + [helpers.base() + code + '/' + PRIVACY[code] for code in CODES]
                + [helpers.base() + code + '/' + ARTICLE_LISTS[code] for code in CODES])
    articles = sorted(helpers.base() + address.lstrip('/') for address in helpers.published())
    assert locs[:len(expected)] == expected and sorted(locs[len(expected):]) == articles, \
        'sitemap.xml lista %s; esperado %s e os artigos %s' % (locs, expected, articles)


def test_every_page_in_the_sitemap_is_tested():
    """Toda página publicada no sitemap está em PAGES (tests/helpers.py), a lista em que valem as
    verificações de todas as páginas. Página nova sem teste reprova aqui."""
    untested = [loc for loc in (u.find('s:loc', SITEMAP).text for u in sitemap_urls())
                if not loc.startswith(helpers.base()) or os.path.relpath(helpers.local_file(loc[len(helpers.base()) - 1:]), helpers.ROOT) not in PAGES]
    assert not untested, 'páginas do sitemap.xml fora de PAGES, em tests/helpers.py (acrescente-as lá): %s' % untested


@pytest.mark.parametrize('loc', [''] + ['%s/' % code for code in CODES], ids=lambda loc: '/' + loc)
def test_sitemap_declares_alternates(loc):
    url = helpers.base() + loc
    found = [u for u in sitemap_urls() if u.find('s:loc', SITEMAP).text == url]
    assert found, 'sitemap.xml não lista %s' % url
    alternates = {e.get('hreflang'): e.get('href') for e in found[0].findall('x:link', SITEMAP)}
    assert alternates == helpers.expected_alternates(), 'sitemap.xml: versões por idioma de %s diferentes do esperado: %s' % (url, alternates)


@pytest.mark.parametrize('code', list(CODES))
def test_sitemap_declares_thanksgiving_alternates(code):
    url = helpers.base() + code + '/' + GRATIARUM
    found = [u for u in sitemap_urls() if u.find('s:loc', SITEMAP).text == url]
    assert found, 'sitemap.xml não lista %s' % url
    alternates = {e.get('hreflang'): e.get('href') for e in found[0].findall('x:link', SITEMAP)}
    assert alternates == helpers.expected_alternates(GRATIARUM), 'sitemap.xml: versões por idioma de %s diferentes do esperado: %s' % (url, alternates)


@pytest.mark.parametrize('code', list(CODES))
def test_sitemap_declares_privacy_alternates(code):
    url = helpers.base() + code + '/' + PRIVACY[code]
    found = [u for u in sitemap_urls() if u.find('s:loc', SITEMAP).text == url]
    assert found, 'sitemap.xml não lista %s' % url
    alternates = {e.get('hreflang'): e.get('href') for e in found[0].findall('x:link', SITEMAP)}
    assert alternates == helpers.expected_alternates(PRIVACY), 'sitemap.xml: versões por idioma de %s diferentes do esperado: %s' % (url, alternates)


@pytest.mark.parametrize('code', list(CODES))
def test_sitemap_declares_article_list_alternates_and_lastmod(code):
    url = helpers.base() + code + '/' + ARTICLE_LISTS[code]
    found = [u for u in sitemap_urls() if u.find('s:loc', SITEMAP).text == url]
    assert found, 'sitemap.xml não lista %s' % url
    alternates = {e.get('hreflang'): e.get('href') for e in found[0].findall('x:link', SITEMAP)}
    newest = max(article_day(h, 'updated') for h in helpers.article_headers().values())
    lastmod = found[0].find('s:lastmod', SITEMAP)
    assert alternates == helpers.expected_alternates(ARTICLE_LISTS), 'sitemap.xml: versões por idioma de %s: %s' % (url, alternates)
    assert lastmod is not None and lastmod.text == newest.isoformat(), \
        'sitemap.xml: lastmod de %s deveria ser %s, a data do artigo mais recente: %s' % (url, newest, lastmod is not None and lastmod.text)


@pytest.mark.parametrize('slug', list(helpers.article_headers()))
def test_sitemap_lists_each_article_without_versions(slug):
    url = helpers.base() + 'en/articles/%s/' % slug
    found = [u for u in sitemap_urls() if u.find('s:loc', SITEMAP).text == url]
    assert found, 'sitemap.xml não lista %s' % url
    lastmod = found[0].find('s:lastmod', SITEMAP)
    expected = article_day(helpers.article_headers()[slug], 'updated').isoformat()
    assert not found[0].findall('x:link', SITEMAP) and lastmod is not None and lastmod.text == expected, \
        'sitemap.xml: %s deveria vir sem versões em outras línguas e com lastmod %s' % (url, expected)


# ---------- página de agradecimento (Gratiarum actio) ----------

on_thanksgiving_pages = pytest.mark.parametrize('name', list(GRATIARUM_PAGES))
# Título da página, igual nos quatro idiomas, porque é latim. Escrito aqui de novo, e não lido do modelo.
THANKSGIVING_TITLE = 'Gratiarum actio — Arthur Cei Corrêa'


@on_thanksgiving_pages
def test_thanksgiving_page_was_built(name):
    assert os.path.isfile(helpers.path(name)), '%s não foi gerada pelo build' % name


@on_thanksgiving_pages
def test_thanksgiving_page_has_fixed_language(name):
    code, tag = GRATIARUM_PAGES[name]
    assert ('<html lang="%s" data-lang="%s">' % (tag, code)) in page(name).raw, '%s: esperado <html lang="%s" data-lang="%s">' % (name, tag, code)


@on_thanksgiving_pages
def test_thanksgiving_title_is_the_latin_title(name):
    title, desc = edition_attributes(name, GRATIARUM_PAGES[name][1])
    found = re.search(r'<title>([^<]*)</title>', page(name).raw)
    got = found.group(1) if found else None
    assert got == title == THANKSGIVING_TITLE, '%s: <title> %r e título da edição %r; esperado %r' % (name, got, title, THANKSGIVING_TITLE)


@on_thanksgiving_pages
def test_thanksgiving_description_and_preview_are_in_page_language(name):
    p = page(name)
    title, desc = edition_attributes(name, GRATIARUM_PAGES[name][1])
    got = (p.meta('description'), p.meta('og:description'), p.meta('og:title'))
    assert desc and got == (desc, desc, title), '%s: descrição e prévia fora do idioma da página: %s' % (name, got)


@pytest.mark.parametrize('field', ['description', 'og:description'])
def test_thanksgiving_descriptions_differ_by_language(field):
    found = {page(name).meta(field) for name in GRATIARUM_PAGES}
    assert len(found) == 4, '%s das páginas de agradecimento deveria ter uma versão por idioma: %s' % (field, found)


@on_thanksgiving_pages
def test_thanksgiving_og_locale_matches_page(name):
    code = GRATIARUM_PAGES[name][0]
    assert page(name).meta('og:locale') == LOCALES[code], '%s: og:locale %r, esperado %r' % (name, page(name).meta('og:locale'), LOCALES[code])


@on_thanksgiving_pages
def test_thanksgiving_canonical_url_is_the_page_itself(name):
    url = helpers.base() + GRATIARUM_PAGES[name][0] + '/' + GRATIARUM
    p = page(name)
    assert p.canonical == url and p.meta('og:url') == url, '%s: canonical %r e og:url %r, esperado %r' % (name, p.canonical, p.meta('og:url'), url)


@on_thanksgiving_pages
def test_thanksgiving_alternates_point_to_the_same_page_in_each_language(name):
    assert page(name).alternates == helpers.expected_alternates(GRATIARUM), \
        '%s: versões por idioma (hreflang) diferentes: %s' % (name, page(name).alternates)


@on_thanksgiving_pages
def test_thanksgiving_switcher_leads_to_the_same_page_in_each_language(name):
    code, tag = GRATIARUM_PAGES[name]
    raw = page(name).raw
    missing = [other for other in CODES if ('<a href="/%s/%s" data-lang="%s"' % (other, GRATIARUM, other)) not in raw]
    current = '<a href="/%s/%s" data-lang="%s" lang="%s" hreflang="%s" aria-current="true">' % (code, GRATIARUM, code, tag, tag)
    assert not missing and current in raw and raw.count('aria-current="true"') == 1, \
        '%s: o seletor deveria levar a /<idioma>/%s nos quatro idiomas (faltam: %s) e marcar só %s' % (name, GRATIARUM, missing, code.upper())


@on_thanksgiving_pages
def test_thanksgiving_links_back_to_the_home_page_of_its_language(name):
    code = GRATIARUM_PAGES[name][0]
    top = page(name).body.split('<header class="wrap top"', 1)[1].split('</header>', 1)[0]
    assert ('<a class="home" href="/%s/">' % code) in top, '%s: falta, no topo, o link de volta a /%s/' % (name, code)


@on_thanksgiving_pages
def test_thanksgiving_is_shared_as_an_article(name):
    p = page(name)
    assert p.meta('og:type') == 'article' and p.meta('profile:first_name') is None, \
        '%s: a prévia deveria ser de um artigo (og:type article, sem os dados de perfil): og:type %r' % (name, p.meta('og:type'))


@pytest.mark.parametrize('name', ['index.html'] + list(LANGUAGE_PAGES))
def test_portfolio_is_shared_as_a_profile(name):
    p = page(name)
    assert p.meta('og:type') == 'profile' and p.meta('profile:first_name') == 'Arthur', \
        '%s: a prévia do portfólio deveria ser de um perfil: og:type %r' % (name, p.meta('og:type'))


@on_thanksgiving_pages
def test_thanksgiving_has_its_own_share_image(name):
    p = page(name)
    image = p.meta('og:image')
    assert image == helpers.base() + 'og-gratiarum.png' and image_exists(image) and p.meta('twitter:image') == image, \
        '%s: a imagem de prévia deveria ser og-gratiarum.png, existir e ser a mesma em og:image e twitter:image: %s' % (name, image)


def test_thanksgiving_share_image_alt_differs_by_language():
    alts = {page(name).meta('og:image:alt') for name in GRATIARUM_PAGES}
    portfolio = {page(name).meta('og:image:alt') for name in LANGUAGE_PAGES}
    assert len(alts) == 4 and not alts & portfolio, \
        'o texto alternativo da prévia do agradecimento deveria ter uma versão por idioma, diferente da do portfólio: %s' % alts


@on_thanksgiving_pages
def test_thanksgiving_structured_data_describes_the_page(name):
    p = page(name)
    works = [n for n in p.structured_data() or [] if n.get('@type') == 'Article']
    assert len(works) == 1 and works[0].get('url') == p.canonical and works[0].get('headline') == 'Gratiarum actio' \
        and works[0].get('inLanguage') == GRATIARUM_PAGES[name][1], \
        '%s: os dados estruturados deveriam descrever esta página (Article com url, título e idioma dela): %s' % (name, works)


@on_thanksgiving_pages
def test_thanksgiving_has_no_unreplaced_marker(name):
    text = re.sub(r'<[^>]+>', ' ', page(name).body)
    found = re.search(r'\{[a-z_]+\}', text)
    assert not found, '%s: marcador sem trocar no texto: %s' % (name, found.group(0) if found else '')


@on_thanksgiving_pages
def test_thanksgiving_has_the_same_person_as_home(name):
    assert page(name).person() == page('index.html').person(), '%s: dados estruturados da pessoa diferentes dos da página inicial' % name


# ---------- página de privacidade ----------

on_privacy_pages = pytest.mark.parametrize('name', list(PRIVACY_PAGES))
# Os links que a página precisa ter, em todas as edições: as duas políticas, em inglês, e o e-mail.
# Escritos aqui de novo, e não lidos do modelo.
PRIVACY_LINKS = {
    'Cloudflare': 'https://www.cloudflare.com/privacypolicy/',
    'GitHub': 'https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement',
    'e-mail': 'mailto:arthurceicorrea@gmail.com',
}


@on_privacy_pages
def test_privacy_page_was_built(name):
    assert os.path.isfile(helpers.path(name)), '%s não foi gerada pelo build' % name


@on_privacy_pages
def test_privacy_page_has_fixed_language(name):
    code, tag = PRIVACY_PAGES[name]
    assert ('<html lang="%s" data-lang="%s">' % (tag, code)) in page(name).raw, '%s: esperado <html lang="%s" data-lang="%s">' % (name, tag, code)


@on_privacy_pages
def test_privacy_title_is_in_page_language(name):
    title, desc = edition_attributes(name, PRIVACY_PAGES[name][1])
    found = re.search(r'<title>([^<]*)</title>', page(name).raw)
    got = found.group(1) if found else None
    assert title and got == title, '%s: <title> %r difere do título da edição %r' % (name, got, title)


@on_privacy_pages
def test_privacy_description_and_preview_are_in_page_language(name):
    p = page(name)
    title, desc = edition_attributes(name, PRIVACY_PAGES[name][1])
    got = (p.meta('description'), p.meta('og:description'), p.meta('og:title'))
    assert desc and got == (desc, desc, title), '%s: descrição e prévia fora do idioma da página: %s' % (name, got)


@pytest.mark.parametrize('field', ['description', 'og:description'])
def test_privacy_descriptions_differ_by_language(field):
    # o título não entra: "Privacy" é a mesma palavra em inglês e em italiano
    found = {page(name).meta(field) for name in PRIVACY_PAGES}
    assert len(found) == 4, '%s da página de privacidade deveria ter uma versão por idioma: %s' % (field, found)


@on_privacy_pages
def test_privacy_og_locale_matches_page(name):
    code = PRIVACY_PAGES[name][0]
    assert page(name).meta('og:locale') == LOCALES[code], '%s: og:locale %r, esperado %r' % (name, page(name).meta('og:locale'), LOCALES[code])


@on_privacy_pages
def test_privacy_canonical_url_is_the_page_itself(name):
    code = PRIVACY_PAGES[name][0]
    url = helpers.base() + code + '/' + PRIVACY[code]
    p = page(name)
    assert p.canonical == url and p.meta('og:url') == url, '%s: canonical %r e og:url %r, esperado %r' % (name, p.canonical, p.meta('og:url'), url)


@on_privacy_pages
def test_privacy_alternates_point_to_the_translated_addresses(name):
    assert page(name).alternates == helpers.expected_alternates(PRIVACY), \
        '%s: versões por idioma (hreflang) diferentes: %s' % (name, page(name).alternates)


@on_privacy_pages
def test_privacy_switcher_leads_to_the_same_page_in_each_language(name):
    code, tag = PRIVACY_PAGES[name]
    raw = page(name).raw
    missing = [other for other in CODES if ('<a href="/%s/%s" data-lang="%s"' % (other, PRIVACY[other], other)) not in raw]
    current = '<a href="/%s/%s" data-lang="%s" lang="%s" hreflang="%s" aria-current="true">' % (code, PRIVACY[code], code, tag, tag)
    assert not missing and current in raw and raw.count('aria-current="true"') == 1, \
        '%s: o seletor deveria levar à privacidade nos quatro idiomas (faltam: %s) e marcar só %s' % (name, missing, code.upper())


@on_privacy_pages
def test_privacy_links_back_to_the_home_page_of_its_language(name):
    code = PRIVACY_PAGES[name][0]
    top = page(name).body.split('<header class="wrap top"', 1)[1].split('</header>', 1)[0]
    assert ('<a class="home" href="/%s/">' % code) in top, '%s: falta, no topo, o link de volta a /%s/' % (name, code)


@on_privacy_pages
def test_privacy_share_image_is_the_one_of_its_language(name):
    p = page(name)
    home = page('%s/index.html' % PRIVACY_PAGES[name][0])
    assert image_exists(p.meta('og:image')) and p.meta('og:image') == home.meta('og:image') == p.meta('twitter:image') \
        and p.meta('og:image:alt') == home.meta('og:image:alt'), \
        '%s: a prévia deveria ser a da página inicial do idioma: %s' % (name, p.meta('og:image'))


@on_privacy_pages
def test_privacy_is_shared_as_a_website(name):
    p = page(name)
    assert p.meta('og:type') == 'website' and p.meta('profile:first_name') is None, \
        '%s: a prévia deveria ser de um site (og:type website, sem os dados de perfil): og:type %r' % (name, p.meta('og:type'))


@on_privacy_pages
def test_privacy_structured_data_describes_the_page(name):
    p = page(name)
    nodes = [n for n in p.structured_data() or [] if n.get('@type') != 'Person']
    assert len(nodes) == 1 and nodes[0].get('@type') == 'WebPage' and nodes[0].get('url') == p.canonical \
        and nodes[0].get('inLanguage') == PRIVACY_PAGES[name][1], \
        '%s: os dados estruturados deveriam descrever esta página (WebPage com url e idioma dela): %s' % (name, nodes)


@on_privacy_pages
def test_privacy_has_the_same_person_as_home(name):
    assert page(name).person() == page('index.html').person(), '%s: dados estruturados da pessoa diferentes dos da página inicial' % name


@on_privacy_pages
def test_privacy_has_no_unreplaced_marker(name):
    text = re.sub(r'<[^>]+>', ' ', page(name).body)
    found = re.search(r'\{[a-z_]+\}', text)
    assert not found, '%s: marcador sem trocar no texto: %s' % (name, found.group(0) if found else '')


@pytest.mark.parametrize('name, what', [(n, w) for n in PRIVACY_PAGES for w in PRIVACY_LINKS])
def test_privacy_page_links_to_the_policies_and_the_email(name, what):
    main = page(name).body.split('<main', 1)[1].split('</main>', 1)[0]
    assert ('<a href="%s"' % PRIVACY_LINKS[what]) in main, '%s: falta, no texto, o link %s (%s)' % (name, what, PRIVACY_LINKS[what])


@pytest.mark.parametrize('name, what', [(n, w) for n in PRIVACY_PAGES for w in ('Cloudflare', 'GitHub')])
def test_privacy_policy_links_say_they_are_in_english(name, what):
    found = [a for tag, a, line in page(name).tags if tag == 'a' and a.get('href') == PRIVACY_LINKS[what]]
    assert found and all(a.get('hreflang') == 'en' for a in found), '%s: o link da política (%s) deveria levar hreflang="en"' % (name, what)


# ---------- frase de privacidade do rodapé: link para a página de privacidade do idioma ----------

# Páginas com rodapé e para onde a frase leva: na página inicial, que é a edição em inglês, a privacidade em inglês.
FOOTER_PAGES = {name: lang for name, lang in PAGES.items() if lang}
TAG_CODES = {tag: code for code, tag in CODES.items()}


def privacy_line(name):
    """O segundo parágrafo do rodapé, o da frase de privacidade."""
    raw = page(name).raw
    footer = raw[raw.find('<footer'):] if '<footer' in raw else ''
    found = re.search(r'<p class="colophon">.*?</p>\s*<p>(.*?)</p>', footer, flags=re.S)
    return found.group(1) if found else ''


@pytest.mark.parametrize('name', list(FOOTER_PAGES))
def test_footer_privacy_sentence_links_to_the_privacy_page_of_its_language(name):
    code = TAG_CODES[FOOTER_PAGES[name]]
    links = re.findall(r'<a href="([^"]+)"', privacy_line(name))
    assert links == ['/%s/%s' % (code, PRIVACY[code])], '%s: a frase de privacidade deveria ser link para /%s/%s; links: %s' % (
        name, code, PRIVACY[code], links)


@pytest.mark.parametrize('name', list(FOOTER_PAGES))
def test_footer_privacy_link_is_marked_current_only_on_the_privacy_page(name):
    marked = 'aria-current="page"' in privacy_line(name)
    assert marked == (name in PRIVACY_PAGES), '%s: aria-current="page" no link de privacidade do rodapé só na própria página de privacidade' % name


# ---------- scripts do site: nada guardado no navegador, nada enviado ----------

STORAGE_OR_NETWORK = re.compile(r'\b(document\.cookie|localStorage|sessionStorage|indexedDB|fetch|XMLHttpRequest|sendBeacon)\b')
SCRIPTS = os.path.join(helpers.REPO, 'src', 'js')


@pytest.mark.parametrize('script', sorted(n for n in os.listdir(SCRIPTS) if n.endswith('.js')))
def test_script_stores_and_sends_nothing(script):
    """É o que sustenta, na página de privacidade, "não guarda nada no seu navegador" e o envio de nada."""
    text = open(os.path.join(SCRIPTS, script), encoding='utf-8').read()
    found = sorted(set(STORAGE_OR_NETWORK.findall(text)))
    assert not found, 'src/js/%s usa %s; a página de privacidade diz que o site não guarda nem envia nada' % (script, found)


# ---------- colofão (primeira linha do rodapé) ----------

COLOPHON = 'Non nisi te, Domine'
# Páginas cujo colofão é link, e para onde: na página inicial, que é a edição em inglês, o agradecimento em inglês.
COLOPHON_LINKS = {'index.html': '/en/' + GRATIARUM, **{name: '/%s/%s' % (code, GRATIARUM) for name, (code, tag) in LANGUAGE_PAGES.items()}}


def colophon(name):
    """O primeiro parágrafo do rodapé, se for o colofão; None se não for."""
    raw = page(name).raw
    footer = raw[raw.find('<footer'):] if '<footer' in raw else ''
    found = re.search(r'<div class="foot">\s*<p class="colophon">(.*?)</p>', footer, flags=re.S)
    return found.group(1) if found else None


@pytest.mark.parametrize('name', list(COLOPHON_LINKS) + list(GRATIARUM_PAGES))
def test_colophon_is_the_first_line_of_the_footer(name):
    text = colophon(name)
    assert text is not None and COLOPHON in text, '%s: o rodapé deveria começar pelo colofão (%s)' % (name, COLOPHON)


@pytest.mark.parametrize('name', list(COLOPHON_LINKS))
def test_colophon_links_to_the_thanksgiving_page_of_its_language(name):
    links = re.findall(r'<a href="([^"]+)"', colophon(name) or '')
    assert links == [COLOPHON_LINKS[name]], '%s: o colofão deveria ser um link para %s; links: %s' % (name, COLOPHON_LINKS[name], links)


@pytest.mark.parametrize('name', list(COLOPHON_LINKS))
def test_colophon_link_says_where_it_leads(name):
    note = re.search(r'<span class="vh"> \(([^)]+)\)</span></a>', colophon(name) or '')
    assert note, '%s: o link do colofão precisa dizer, para leitores de tela, aonde leva' % name


@on_thanksgiving_pages
def test_colophon_is_not_a_link_on_the_thanksgiving_page(name):
    assert '<a ' not in (colophon(name) or '<a '), '%s: na própria página de agradecimento, o colofão não é link' % name


def test_404_has_no_colophon():
    assert COLOPHON not in page('404.html').raw, '404.html: a página de erro não tem rodapé nem colofão'


# ---------- latim marcado com lang="la" e igual nos quatro idiomas ----------

# Trechos em latim do site, escritos aqui de novo, e não lidos dos modelos.
# A epígrafe vai em três linhas fixas, uma por membro; cada membro é um trecho.
LATIN = ['Non nisi te, Domine', 'Gratiarum actio', 'Ingressum instruas,', 'progressum dirigas,', 'egressum compleas.',
         'Creator ineffabilis', 'Domus et divitiae dantur a parentibus; a Domino autem proprie uxor prudens',
         'maxima amicitia esse videtur', 'Laus Deo.']


class LatinParser(HTMLParser):
    """Textos do corpo da página, cada um com o idioma em vigor (o lang do elemento mais próximo),
    e o texto de cada elemento marcado com lang="la"."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.texts, self.latin, self.open = [], [], [], []
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.in_body = True
        if tag in VOID:
            return
        lang = dict(attrs).get('lang') or (self.stack[-1][1] if self.stack else None)
        self.stack.append((tag, lang))
        if dict(attrs).get('lang') == 'la':
            self.open.append([len(self.stack), ''])

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        if self.open and self.open[-1][0] == len(self.stack):
            self.latin.append(self.open.pop()[1])
        self.stack.pop()

    def handle_data(self, data):
        if self.in_body and data.strip():
            self.texts.append((data, self.stack[-1][1] if self.stack else None))
        for item in self.open:
            item[1] += data


@functools.lru_cache(maxsize=None)
def latin_of(name):
    parser = LatinParser()
    parser.feed(page(name).raw)
    return parser


@pytest.mark.parametrize('name', [n for n in PAGES if n != '404.html'])
def test_latin_is_marked_as_latin(name):
    unmarked = [(text.strip(), lang) for text, lang in latin_of(name).texts for phrase in LATIN if phrase in text and lang != 'la']
    assert not unmarked, '%s: trecho em latim sem lang="la" (texto, idioma em vigor): %s' % (name, unmarked)


@on_thanksgiving_pages
def test_thanksgiving_page_has_all_its_latin(name):
    found = ' '.join(text for text, lang in latin_of(name).texts if lang == 'la')
    missing = [phrase for phrase in LATIN if phrase not in found]
    assert not missing, '%s: faltam, marcados como latim, os trechos: %s' % (name, missing)


@pytest.mark.parametrize('group', ['portfolio', 'gratiarum'])
def test_latin_is_identical_in_the_four_languages(group):
    names = list(LANGUAGE_PAGES) if group == 'portfolio' else list(GRATIARUM_PAGES)
    found = {name: latin_of(name).latin for name in names}
    first = found[names[0]]
    different = {name: latin for name, latin in found.items() if latin != first}
    assert first and not different, 'trechos em latim diferentes entre os idiomas (%s):\n  %s: %s\n  %s' % (
        group, names[0], first, '\n  '.join('%s: %s' % item for item in different.items()))


# ---------- currículos e cartão de contato ----------

CV_NAMES = ['arthur-cei-correa-cv-%s.pdf' % code for code in CODES]
# Lista dos artigos de cada idioma, como o currículo a escreve (sem https:// e sem a barra final).
CV_LIST = {code: 'arthurceicorrea.dev/%s/%s' % (code, ARTICLE_LISTS[code].rstrip('/')) for code in CODES}


def cv_articles():
    """Os artigos que o currículo leva: os marcados com cv = true no cabeçalho."""
    return {slug: h for slug, h in helpers.article_headers().items() if h.get('cv') is True}


def test_at_most_two_articles_go_in_the_cv():
    assert len(cv_articles()) <= 2, 'cv = true em %d artigos (%s); o currículo leva no máximo dois' % (len(cv_articles()), sorted(cv_articles()))


@pytest.mark.parametrize('slug', [s for s in helpers.article_headers() if s not in cv_articles()])
def test_cv_leaves_out_unmarked_articles(slug):
    summaries = helpers.article_headers()[slug]['summary']
    found = [code for code in CODES if squeezed(summaries[code]) in squeezed(cv_text('arthur-cei-correa-cv-%s.pdf' % code))]
    assert not found, 'o artigo %s não tem cv = true, mas o resumo dele está no currículo em %s' % (slug, found)


@pytest.mark.parametrize('code', list(CODES))
def test_cv_ends_its_articles_with_the_list_of_its_language(code):
    if not cv_articles():
        pytest.skip('nenhum artigo com cv = true')
    assert CV_LIST[code] in cv_text('arthur-cei-correa-cv-%s.pdf' % code), \
        'arthur-cei-correa-cv-%s.pdf: falta o endereço da lista de artigos, %s' % (code, CV_LIST[code])
# Rodapé da primeira página de cada currículo, escrito aqui e não lido do conteúdo.
CV_FOOTERS = {'pt': 'Página 1 de 2', 'en': 'Page 1 of 2', 'es': 'Página 1 de 2', 'it': 'Pagina 1 di 2'}


@functools.lru_cache(maxsize=None)
def cv_reader(name):
    from pypdf import PdfReader
    return PdfReader(helpers.path('cv', name))


@functools.lru_cache(maxsize=None)
def cv_text(name):
    return ''.join(p.extract_text() or '' for p in cv_reader(name).pages)


def squeezed(text):
    """Texto sem espaços nem quebras de linha: a extração do PDF quebra as linhas onde a página quebrou."""
    return re.sub(r'\s+', '', text)


def site_texts():
    """Textos da página que o currículo também precisa trazer, por idioma: (idioma, onde, texto)."""
    import tomllib
    found = []
    for code in CODES:
        with open(os.path.join(helpers.REPO, 'src', 'content', code + '.toml'), 'rb') as f:
            c = tomllib.load(f)
        found.append((code, 'intro.summary', c['intro']['summary']))
        found += [(code, 'intro.glance[%d]' % i, g['text']) for i, g in enumerate(c['intro']['glance'], 1)]
        for i, e in enumerate(c['education'], 1):
            found += [(code, 'education[%d].%s' % (i, k), e[k]) for k in ('title', 'meta', 'text')]
        for i, p in enumerate(c['projects'], 1):
            found += [(code, 'projects[%d].%s' % (i, k), p[k]) for k in ('title', 'meta', 'summary', 'stack')]
            found.append((code, 'projects[%d].role' % i, p['role']))
            found.append((code, 'projects[%d].repo' % i, p['repo'].split('://', 1)[1] if 'repo' in p else p['repo_note']))
        for i, g in enumerate(c['skills']['groups'], 1):
            found += [(code, 'skills.groups[%d].%s' % (i, k), g[k]) for k in ('name', 'items')]
        found += [(code, 'languages.items[%d]' % i, '%s (%s)' % (l['name'], l['level'])) for i, l in enumerate(c['languages']['items'], 1)]
        found += [(code, 'artigo %s: summary.%s' % (slug, code), header['summary'][code]) for slug, header in cv_articles().items()]
    return [pytest.param(code, where, text, id='%s:%s' % (code, where)) for code, where, text in found]


def test_all_four_cvs_are_built():
    assert helpers.cv_files() == sorted(CV_NAMES), 'cv/: esperados %s; encontrados %s' % (sorted(CV_NAMES), helpers.cv_files())


@pytest.mark.parametrize('code, where, text', site_texts())
def test_cv_has_the_site_text(code, where, text):
    name = 'arthur-cei-correa-cv-%s.pdf' % code
    expected, found = squeezed(text), squeezed(cv_text(name))
    if where.endswith('.role'):
        # quando o resumo do projeto já diz o papel (SellOut EasyTrack), o currículo não o repete:
        # basta estar no resumo, que pode começar com minúscula e não terminar ali
        expected, found = expected.rstrip('.').lower(), found.lower()
    source = 'src/articles/%s.md' % where.split()[1].rstrip(':') if where.startswith('artigo ') else 'src/content/%s.toml' % code
    assert expected in found, '%s: falta o texto de %s em %s: %r' % (name, where, source, text)


@pytest.mark.parametrize('name', CV_NAMES)
def test_cv_has_at_most_two_pages(name):
    pages = len(cv_reader(name).pages)
    assert pages <= 2, '%s: %d páginas; o currículo deve caber em duas' % (name, pages)


@pytest.mark.parametrize('name', CV_NAMES)
def test_cv_title_is_the_name(name):
    title = (cv_reader(name).metadata or {}).get('/Title')
    assert title == 'Arthur Cei Corrêa', '%s: título do documento %r; esperado Arthur Cei Corrêa' % (name, title)


@pytest.mark.parametrize('code', list(CODES))
def test_cv_footer_numbers_pages_in_its_language(code):
    name = 'arthur-cei-correa-cv-%s.pdf' % code
    assert CV_FOOTERS[code] in cv_text(name), '%s: falta o rodapé "%s"' % (name, CV_FOOTERS[code])


def test_pypdf_is_available():
    try:
        import pypdf  # noqa: F401
    except ImportError:
        pytest.fail('pypdf não instalado: rode make setup')


@pytest.mark.parametrize('name', helpers.cv_files())
def test_cv_is_readable(name):
    assert len(cv_text(name)) > 500, '%s: pouco texto extraível; o PDF precisa ter texto, não só imagem' % name


@pytest.mark.parametrize('name', helpers.cv_files())
def test_no_phone_number_in_cv(name):
    found = PHONE.search(cv_text(name))
    assert not found, '%s: parece haver um telefone: %r' % (name, found.group(0) if found else '')


@pytest.mark.parametrize('name', [n for n in helpers.cv_files() if not n.endswith('-en.pdf')])
def test_cv_footer_is_in_its_language(name):
    assert 'Page 1 of' not in cv_text(name), '%s: o rodapé está em inglês ("Page 1 of"), e não no idioma do currículo' % name


def test_vcard_has_name_and_site():
    card = helpers.read('arthur-cei-correa.vcf')
    assert card.startswith('BEGIN:VCARD') and 'FN:Arthur Cei Corrêa' in card and 'URL:' + helpers.base() in card, \
        'arthur-cei-correa.vcf: esperado BEGIN:VCARD, FN:Arthur Cei Corrêa e URL:%s' % helpers.base()


def test_no_phone_number_in_vcard():
    found = PHONE.search(helpers.read('arthur-cei-correa.vcf'))
    assert not found, 'arthur-cei-correa.vcf: parece haver um telefone: %r' % (found.group(0) if found else '')


# ---------- artigos: endereços publicados ----------

@pytest.mark.parametrize('address', helpers.published())
def test_published_address_still_exists(address):
    """Um endereço publicado nunca some: mudar o slug de um artigo, ou apagá-lo, reprova aqui."""
    assert os.path.isfile(helpers.local_file(address)), \
        '%s está em tests/published.txt, mas não existe no site montado; o slug de um artigo publicado não muda' % address


@pytest.mark.parametrize('slug', list(helpers.article_headers()))
def test_every_article_is_in_published_list(slug):
    assert '/en/articles/%s/' % slug in helpers.published(), \
        'src/articles/%s.md: acrescente /en/articles/%s/ a tests/published.txt (publicar um artigo inclui essa linha)' % (slug, slug)


# ---------- artigos: a página de cada artigo ----------

on_article_pages = pytest.mark.parametrize('name', list(ARTICLE_PAGES))


def slug_of(name):
    return name.split('/')[2]


def header_of(name):
    return helpers.article_headers()[slug_of(name)]


@on_article_pages
def test_article_page_is_english_with_fixed_language(name):
    assert '<html lang="en" data-lang="en">' in page(name).raw, '%s: esperado <html lang="en" data-lang="en">' % name


@on_article_pages
def test_article_title_and_description(name):
    p, header = page(name), header_of(name)
    title = helpers.plain_title(header['title']) + ' — Arthur Cei Corrêa'
    found = re.search(r'<title>([^<]*)</title>', p.raw)
    got = (found.group(1) if found else None, p.meta('og:title'), p.meta('description'), p.meta('og:description'))
    assert got == (title, title, header['summary']['en'], header['summary']['en']), \
        '%s: título e descrição deveriam ser o título do artigo e o resumo em inglês: %s' % (name, got)


@on_article_pages
def test_article_heading_is_its_title(name):
    found = re.search(r'<h1>(.*?)</h1>', page(name).body, flags=re.S)
    text = re.sub(r'<[^>]+>', '', found.group(1)) if found else None
    assert text == helpers.plain_title(header_of(name)['title']), '%s: o título da página (h1) deveria ser o do artigo: %r' % (name, text)


@on_article_pages
def test_article_canonical_is_itself_and_no_alternates(name):
    p = page(name)
    url = helpers.base() + name[:-len('index.html')]
    assert p.canonical == url and p.meta('og:url') == url and p.alternates == {}, \
        '%s: canonical %r, og:url %r e versões %s; esperado %s e nenhum hreflang, porque o artigo só existe em inglês' % (
            name, p.canonical, p.meta('og:url'), p.alternates, url)


@on_article_pages
def test_article_is_shared_as_an_article(name):
    p, header = page(name), header_of(name)
    published = header['date'].isoformat()
    modified = article_day(header, 'updated').isoformat()
    got = (p.meta('og:type'), p.meta('og:locale'), p.meta('article:published_time'), p.meta('article:modified_time'))
    assert got == ('article', 'en_US', published, modified) and 'og:locale:alternate' not in p.raw \
        and p.meta('profile:first_name') is None and image_exists(p.meta('og:image')), \
        '%s: prévia de artigo em inglês, com as datas %s e %s, sem outras regiões: %s' % (name, published, modified, got)


@on_article_pages
def test_article_structured_data(name):
    p, header = page(name), header_of(name)
    works = [n for n in p.structured_data() or [] if n.get('@type') == 'Article']
    expected = {'headline': helpers.plain_title(header['title']), 'url': p.canonical, 'inLanguage': 'en',
                'datePublished': header['date'].isoformat(), 'dateModified': article_day(header, 'updated').isoformat(),
                'description': header['summary']['en']}
    got = {k: works[0].get(k) for k in expected} if len(works) == 1 else works
    assert got == expected and p.person() == page('index.html').person(), \
        '%s: dados estruturados do artigo diferentes do esperado (ou a pessoa difere da página inicial): %s' % (name, got)


def top_of(name):
    return page(name).body.split('<header class="wrap top"', 1)[1].split('</header>', 1)[0]


@on_article_pages
def test_article_has_no_language_switcher(name):
    """Etapa 14: nada no artigo se traduz, e o seletor levava o leitor para fora dele."""
    raw = page(name).raw
    assert 'class="langs"' not in raw and 'aria-current="true"' not in raw, '%s: a página do artigo não deveria ter seletor de idioma' % name


@on_article_pages
def test_article_trail_leads_to_the_root_and_the_english_list(name):
    """A trilha: Home leva à raiz, onde o script de idioma escolhe a página inicial do visitante;
    Articles, à lista em inglês. A barra entre os passos é só visual (CSS)."""
    trail = re.search(r'<nav class="trail" aria-label="([^"]+)">(.*?)</nav>', top_of(name), flags=re.S)
    steps = re.findall(r'<li><a href="([^"]+)"([^>]*)>([^<]+)</a></li>', trail.group(2)) if trail else []
    assert trail and trail.group(1) == 'Breadcrumb' and steps == [('/', '', 'Home'), ('/en/articles/', '', 'Articles')], \
        '%s: no topo, a trilha deveria ser Home (/) / Articles (/en/articles/): %s' % (name, steps)


@on_article_pages
def test_article_ends_with_links_to_the_other_lists_in_their_languages(name):
    end = re.search(r'<nav class="others" aria-label="Summaries in other languages">(.*?)</nav>', page(name).body, flags=re.S)
    links = re.findall(r'<a href="([^"]+)" lang="([^"]+)" hreflang="([^"]+)">([^<]+)</a>', end.group(1)) if end else []
    expected = [('/pt/' + ARTICLE_LISTS['pt'], 'pt-BR', 'pt-BR', 'Resumos em português'),
                ('/es/' + ARTICLE_LISTS['es'], 'es', 'es', 'Resúmenes en español'),
                ('/it/' + ARTICLE_LISTS['it'], 'it', 'it', 'Riassunti in italiano')]
    assert links == expected, '%s: no fim, os links para as listas em português, espanhol e italiano, cada um na sua língua: %s' % (name, links)


@on_article_pages
def test_article_breadcrumb_in_structured_data(name):
    p, header = page(name), header_of(name)
    crumbs = [n for n in p.structured_data() or [] if n.get('@type') == 'BreadcrumbList']
    items = [(i.get('position'), i.get('name'), i.get('item')) for i in crumbs[0]['itemListElement']] if len(crumbs) == 1 else crumbs
    expected = [(1, 'Home', helpers.base()), (2, 'Articles', helpers.base() + 'en/articles/'),
                (3, helpers.plain_title(header['title']), p.canonical)]
    assert items == expected, '%s: BreadcrumbList diferente do esperado: %s' % (name, items)


# palavras por minuto, escritas aqui de novo, e não lidas de ci/articles.py
WORDS_PER_MINUTE = 230


@on_article_pages
def test_article_reading_time_matches_its_word_count(name):
    """O tempo de leitura, sob a data, é o número de palavras do corpo (epígrafe incluída) dividido
    por 230, arredondado para cima. A contagem aqui lê a página montada."""
    p = page(name)
    body = p.body.split('<div class="body prose">', 1)[1].split('<nav class="others"', 1)[0]
    text = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    words = len(re.findall(r"\w+(?:[’'-]\w+)*", text))
    hero = p.body.split('<header class="hero">', 1)[1].split('</header>', 1)[0]
    found = re.search(r'(\d+) min read', hero)
    assert found and int(found.group(1)) == max(1, math.ceil(words / WORDS_PER_MINUTE)), \
        '%s: %d palavras; o tempo de leitura deveria ser %d min: %s' % (name, words, math.ceil(words / WORDS_PER_MINUTE), found and found.group(0))


@on_article_pages
def test_article_frontispiece(name):
    """Acima do título, "Article"; sob ele, a data e o tempo de leitura."""
    hero = page(name).body.split('<header class="hero">', 1)[1].split('</header>', 1)[0]
    assert re.search(r'<p class="kicker">Article</p>\s*<h1>.*?</h1>\s*<p class="meta"><time datetime="[^"]+">[^<]+</time>'
                     r'.*?<span class="sep" aria-hidden="true"> · </span>\d+ min read</p>', hero, flags=re.S), \
        '%s: o frontispício deveria ter "Article", o título e a data com o tempo de leitura' % name


@on_article_pages
def test_article_shows_its_date_in_english(name):
    day = header_of(name)['date']
    expected = '<time datetime="%s">%s %d, %d</time>' % (day.isoformat(), day.strftime('%B'), day.day, day.year)
    hero = page(name).body.split('<header class="hero">', 1)[1].split('</header>', 1)[0]
    assert expected in hero, '%s: falta a data de publicação, em inglês, sob o título: %s' % (name, expected)


@on_article_pages
def test_article_has_no_unreplaced_marker(name):
    text = re.sub(r'<[^>]+>', ' ', page(name).body.split('<div class="body prose">')[0])
    found = re.search(r'\{[a-z_]+\}', text)
    assert not found, '%s: marcador sem trocar no texto: %s' % (name, found.group(0) if found else '')


# ---------- artigos: links no corpo ----------

def body_links():
    return [pytest.param(name, tag, a, url, id='%s:%d:%s' % (name, line, short(url)))
            for name in ARTICLE_PAGES for tag, a, line, url in page(name).links(prose=True)]


@pytest.mark.parametrize('name', list(ARTICLE_PAGES))
def test_article_body_is_found(name):
    assert page(name).prose_tags(), '%s: o corpo do artigo (class="body prose") não foi encontrado' % name


@pytest.mark.parametrize('name, tag, attrs, url', body_links())
def test_body_link_is_https_in_the_same_tab(name, tag, attrs, url):
    assert tag == 'a' and url.startswith('https://') and 'target' not in attrs, \
        '%s: link no corpo deveria ser https e abrir na mesma aba (<%s>, target=%r): %s' % (name, tag, attrs.get('target'), url)


@pytest.mark.parametrize('name, tag, attrs, url', [p for p in body_links() if p.values[3].startswith(helpers.base())])
def test_body_link_to_the_site_exists(name, tag, attrs, url):
    assert os.path.isfile(helpers.local_file(url[len(helpers.base()) - 1:])), '%s: o link leva a uma página que não existe no site: %s' % (name, url)


@pytest.mark.parametrize('name', list(ARTICLE_PAGES))
def test_body_loads_nothing(name):
    loaded = sorted({tag for tag, a, line in page(name).prose_tags() if tag in RESOURCE_TAGS + ('link', 'style', 'form')})
    attributes = sorted({k for tag, a, line in page(name).prose_tags() for k in a if k == 'style' or k.startswith('on')})
    assert not loaded and not attributes, '%s: o corpo do artigo carrega recursos (%s) ou tem atributos proibidos (%s)' % (name, loaded, attributes)


@pytest.mark.parametrize('name', list(ARTICLE_PAGES))
def test_body_marks_only_languages(name):
    """A única marcação além do CommonMark é a língua de um trecho (<span lang="...">)."""
    spans = [a for tag, a, line in page(name).prose_tags() if tag == 'span']
    assert all(set(a) == {'lang'} and a['lang'] for a in spans), '%s: <span> no corpo com algo além de lang: %s' % (name, spans)


# ---------- artigos: as quatro listas ----------

on_list_pages = pytest.mark.parametrize('name', list(LIST_PAGES))
# Frase no alto das listas que não são inglesas; escrita aqui de novo, e não lida dos arquivos de idioma.
WRITTEN_IN = {'pt': 'Os artigos são escritos em inglês.', 'es': 'Los artículos están escritos en inglés.',
              'it': 'Gli articoli sono scritti in inglese.'}


@on_list_pages
def test_list_has_fixed_language(name):
    code, tag = LIST_PAGES[name]
    assert ('<html lang="%s" data-lang="%s">' % (tag, code)) in page(name).raw, '%s: esperado <html lang="%s" data-lang="%s">' % (name, tag, code)


@on_list_pages
def test_list_title_and_description_are_in_page_language(name):
    p = page(name)
    title, desc = edition_attributes(name, LIST_PAGES[name][1])
    found = re.search(r'<title>([^<]*)</title>', p.raw)
    got = (found.group(1) if found else None, p.meta('description'), p.meta('og:description'), p.meta('og:title'))
    assert title and desc and got == (title, desc, desc, title), '%s: título e descrição fora do idioma da página: %s' % (name, got)


@on_list_pages
def test_list_canonical_and_alternates(name):
    p = page(name)
    code = LIST_PAGES[name][0]
    url = helpers.base() + code + '/' + ARTICLE_LISTS[code]
    assert p.canonical == url and p.alternates == helpers.expected_alternates(ARTICLE_LISTS) and p.meta('og:locale') == LOCALES[code], \
        '%s: canonical %r, versões %s e og:locale %r' % (name, p.canonical, p.alternates, p.meta('og:locale'))


@on_list_pages
def test_list_switcher_leads_to_the_same_list_in_each_language(name):
    code, tag = LIST_PAGES[name]
    raw = page(name).raw
    missing = [other for other in CODES if ('<a href="/%s/%s" data-lang="%s"' % (other, ARTICLE_LISTS[other], other)) not in raw]
    current = '<a href="/%s/%s" data-lang="%s" lang="%s" hreflang="%s" aria-current="true">' % (code, ARTICLE_LISTS[code], code, tag, tag)
    assert not missing and current in raw and raw.count('aria-current="true"') == 1, \
        '%s: o seletor deveria levar à lista nos quatro idiomas (faltam: %s) e marcar só %s' % (name, missing, code.upper())


# Trilha no topo das listas, no idioma da lista; escrita aqui de novo, e não lida dos arquivos de idioma.
TRAIL = {'pt': ('Trilha de navegação', 'Página inicial', 'Artigos'), 'en': ('Breadcrumb', 'Home', 'Articles'),
         'es': ('Ruta de navegación', 'Página de inicio', 'Artículos'), 'it': ('Percorso di navigazione', 'Pagina iniziale', 'Articoli')}


@on_list_pages
def test_list_trail_in_its_language_with_the_current_page(name):
    """A trilha leva à página inicial do idioma e marca a própria lista como a página atual."""
    code = LIST_PAGES[name][0]
    label, home, heading = TRAIL[code]
    trail = re.search(r'<nav class="trail" aria-label="([^"]+)">(.*?)</nav>', top_of(name), flags=re.S)
    steps = re.findall(r'<li><a href="([^"]+)"([^>]*)>([^<]+)</a></li>', trail.group(2)) if trail else []
    expected = [('/%s/' % code, '', home), ('/%s/%s' % (code, ARTICLE_LISTS[code]), ' aria-current="page"', heading)]
    assert trail and trail.group(1) == label and steps == expected, \
        '%s: no topo, a trilha deveria ser %s / %s, com a lista marcada como atual: %s' % (name, home, heading, steps)


@pytest.mark.parametrize('name, slug', [(n, s) for n in LIST_PAGES for s in helpers.article_headers()])
def test_list_shows_each_article_with_the_summary_of_its_language(name, slug):
    code = LIST_PAGES[name][0]
    header = helpers.article_headers()[slug]
    main = page(name).body.split('<main', 1)[1]
    link = '<h2 lang="en"><a href="/en/articles/%s/" hreflang="en">' % slug
    summary = '<p>%s</p>' % header['summary'][code].replace('&', '&amp;')
    assert link in main and summary in main, '%s: falta o artigo %s, com o título em inglês (lang="en") e o resumo em %s' % (name, slug, code)


@on_list_pages
def test_list_is_newest_first(name):
    slugs = re.findall(r'<h2 lang="en"><a href="/en/articles/([^/]+)/"', page(name).body)
    headers = helpers.article_headers()
    expected = sorted(headers, key=lambda s: (headers[s]['date'], s), reverse=True)
    assert slugs == expected, '%s: artigos na ordem %s; esperado do mais recente ao mais antigo: %s' % (name, slugs, expected)


@on_list_pages
def test_list_says_articles_are_in_english(name):
    code = LIST_PAGES[name][0]
    text = re.sub(r'<[^>]+>', ' ', page(name).body)
    if code == 'en':
        assert not any(sentence in text for sentence in WRITTEN_IN.values()), '%s: a lista inglesa não diz que os artigos são em inglês' % name
    else:
        assert WRITTEN_IN[code] in text, '%s: falta a frase "%s"' % (name, WRITTEN_IN[code])


@on_list_pages
def test_list_links_to_the_feed(name):
    assert '<a href="/feed.xml" type="application/atom+xml">' in page(name).body, '%s: falta o link para o feed' % name


@pytest.mark.parametrize('name', [n for n, e in PAGES.items() if e])
def test_page_announces_the_feed(name):
    assert '<link rel="alternate" type="application/atom+xml" href="/feed.xml"' in page(name).raw, '%s: o <head> não anuncia o feed' % name


# ---------- artigos: o feed ----------

ATOM = {'a': 'http://www.w3.org/2005/Atom'}
TAG = 'tag:arthurceicorrea.dev,2026-11-25:'


@functools.lru_cache(maxsize=None)
def feed():
    return ET.parse(helpers.path('feed.xml')).getroot()


def feed_day(text):
    """Dia de uma data do feed (RFC 3339), no fuso que ela própria declara."""
    return datetime.datetime.fromisoformat(text).date()


def test_feed_is_well_formed_and_in_english():
    try:
        root = feed()
    except (ET.ParseError, OSError) as error:
        pytest.fail('feed.xml não é XML bem formado: %s' % error)
    assert root.tag == '{%s}feed' % ATOM['a'] and root.get('{http://www.w3.org/XML/1998/namespace}lang') == 'en', \
        'feed.xml deveria ser um feed Atom com xml:lang="en"'


def test_feed_identifiers_are_unique_tag_uris():
    ids = [feed().find('a:id', ATOM).text] + [e.find('a:id', ATOM).text for e in feed().findall('a:entry', ATOM)]
    expected = [TAG + 'articles'] + [TAG + slug for slug in sorted(helpers.article_headers(), key=lambda s: (helpers.article_headers()[s]['date'], s), reverse=True)]
    assert ids == expected and len(set(ids)) == len(ids), 'feed.xml: identificadores %s; esperados %s' % (ids, expected)


def test_feed_links_exist():
    links = [l.get('href') for l in feed().iter('{%s}link' % ATOM['a'])]
    missing = [href for href in links if not href.startswith(helpers.base()) or not os.path.isfile(helpers.local_file(href[len(helpers.base()) - 1:]))]
    assert links and not missing, 'feed.xml: links que não existem no site montado: %s' % missing


@pytest.mark.parametrize('slug', list(helpers.article_headers()))
def test_feed_entry_matches_the_article_header(slug):
    header = helpers.article_headers()[slug]
    entries = [e for e in feed().findall('a:entry', ATOM) if e.find('a:id', ATOM).text == TAG + slug]
    assert len(entries) == 1, 'feed.xml: o artigo %s deveria ter uma entrada' % slug
    e = entries[0]
    got = (e.find('a:title', ATOM).text, feed_day(e.find('a:published', ATOM).text), feed_day(e.find('a:updated', ATOM).text),
           e.find('a:summary', ATOM).text, e.find('a:link', ATOM).get('href'))
    expected = (helpers.plain_title(header['title']), header['date'], article_day(header, 'updated'), header['summary']['en'],
                helpers.base() + 'en/articles/%s/' % slug)
    assert got == expected, 'feed.xml: entrada de %s diferente do cabeçalho do artigo:\n  %s\n  esperado %s' % (slug, got, expected)
    assert e.find('a:content', ATOM).get('type') == 'html' and len(e.find('a:content', ATOM).text or '') > 500, \
        'feed.xml: a entrada de %s deveria trazer o texto completo (content type="html")' % slug


def test_feed_updated_is_the_newest_change():
    newest = max(article_day(h, 'updated') for h in helpers.article_headers().values())
    assert feed_day(feed().find('a:updated', ATOM).text) == newest, 'feed.xml: updated deveria ser %s' % newest


# ---------- página inicial: a seção de artigos ----------

# Âncora da seção em cada idioma, escrita aqui de novo; e a do singular, que deixou de existir na Etapa 13.
ARTICLES_ANCHOR = {'pt': 'artigos', 'en': 'articles', 'es': 'articulos', 'it': 'articoli'}
OLD_ANCHOR = {'pt': 'artigo', 'en': 'article', 'es': 'articulo', 'it': 'articolo'}
HOME_MAX = 3


def newest_first():
    headers = helpers.article_headers()
    return sorted(headers, key=lambda s: (headers[s]['date'], s), reverse=True)


def articles_section(name):
    """O HTML da seção de artigos de uma página do portfólio ('' se não houver)."""
    code = TAG_CODES[PAGES[name]]
    found = re.search(r'<section class="sec" id="%s">(.*?)</section>' % ARTICLES_ANCHOR[code], page(name).body, flags=re.S)
    return found.group(1) if found else ''


on_portfolio_pages = pytest.mark.parametrize('name', ['index.html'] + list(LANGUAGE_PAGES))


@on_portfolio_pages
def test_home_articles_section_has_the_new_anchor(name):
    code = TAG_CODES[PAGES[name]]
    body = page(name).body
    assert articles_section(name) and ('href="#%s"' % ARTICLES_ANCHOR[code]) in body and ('id="%s"' % OLD_ANCHOR[code]) not in body, \
        '%s: a seção deveria ter a âncora #%s, citada no sumário, e não mais #%s' % (name, ARTICLES_ANCHOR[code], OLD_ANCHOR[code])


@on_portfolio_pages
def test_home_shows_at_most_three_articles_newest_first(name):
    slugs = re.findall(r'<a href="/en/articles/([^/]+)/"', articles_section(name))
    expected = newest_first()[:HOME_MAX]
    assert slugs == expected, '%s: a seção mostra %s; esperado os %d mais recentes, do mais recente ao mais antigo: %s' % (name, slugs, HOME_MAX, expected)


@on_portfolio_pages
def test_home_features_the_newest_article_with_its_summary(name):
    code = TAG_CODES[PAGES[name]]
    slug = newest_first()[0]
    header = helpers.article_headers()[slug]
    section = articles_section(name)
    featured = section.split('<article class="entry">', 1)[1].split('</article>', 1)[0] if '<article class="entry">' in section else ''
    day = header['date'].isoformat()
    assert ('<a href="/en/articles/%s/" hreflang="en">' % slug) in featured and ('<time datetime="%s">' % day) in featured \
        and ('<p>%s</p>' % header['summary'][code]) in featured, \
        '%s: o destaque deveria ser o artigo mais recente (%s), com a data e o resumo em %s' % (name, slug, code)


@on_portfolio_pages
def test_home_earlier_articles_have_title_and_date_only(name):
    section = articles_section(name)
    lines = re.findall(r'<li>(.*?)</li>', section, flags=re.S)
    headers = helpers.article_headers()
    earlier = newest_first()[1:HOME_MAX]
    problems = [slug for slug, line in zip(earlier, lines)
                if ('<a href="/en/articles/%s/"' % slug) not in line or ('<time datetime="%s">' % headers[slug]['date'].isoformat()) not in line
                or any(summary in line for summary in headers[slug]['summary'].values())]
    assert len(lines) == len(earlier) and not problems, \
        '%s: os anteriores ao destaque deveriam vir numa linha cada, só com título e data (%d linhas; com problema: %s)' % (name, len(lines), problems)


@on_portfolio_pages
def test_home_section_links_to_the_list_of_its_language(name):
    code = TAG_CODES[PAGES[name]]
    assert ('<p class="all"><a href="/%s/%s">' % (code, ARTICLE_LISTS[code])) in articles_section(name), \
        '%s: falta, no fim da seção, o link para /%s/%s' % (name, code, ARTICLE_LISTS[code])


@on_portfolio_pages
def test_home_section_says_articles_are_in_english(name):
    code = TAG_CODES[PAGES[name]]
    text = re.sub(r'<[^>]+>', ' ', articles_section(name))
    if code == 'en':
        assert not any(sentence in text for sentence in WRITTEN_IN.values()), '%s: a seção em inglês não diz que os artigos são em inglês' % name
    else:
        assert WRITTEN_IN[code] in text, '%s: falta, na seção, a frase "%s"' % (name, WRITTEN_IN[code])
