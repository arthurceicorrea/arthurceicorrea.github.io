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
404. O latim: todo trecho marcado com lang="la" e idêntico nos quatro idiomas. Por fim,
robots.txt, sitemap.xml, versão publicada, a ausência de telefone nas páginas, nos currículos e no
cartão de contato, e os currículos gerados: os quatro existem, trazem os textos da página no seu
idioma (resumo, formação e experiência, projetos, competências, idiomas e artigo), cabem em duas
páginas e numeram as páginas no idioma do currículo.

Testes que valem para várias páginas, links ou arquivos rodam uma vez para cada um; o item
aparece entre colchetes no nome do teste, por exemplo test_local_file_exists[pt/index.html:142:/cv/...].

Uso: make build && python -m pytest tests/test_static.py
"""
import datetime
import functools
import os
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import pytest

import helpers
from helpers import (ALLOWED_EXTERNAL, CODES, GRATIARUM, GRATIARUM_PAGES, LANGUAGE_PAGES, LANGS, LOCALES, PAGES, PHONE, POLICY,
                     RESOURCE_TAGS, VOID, page)

helpers.require_site()

on_every_page = pytest.mark.parametrize('name', list(PAGES))
on_pages_with_data = pytest.mark.parametrize('name', [n for n in PAGES if n != '404.html'])
on_language_pages = pytest.mark.parametrize('name', list(LANGUAGE_PAGES))


def short(url, size=70):
    return url if len(url) <= size else url[:size - 1] + '…'


def links(kind):
    """(página, etiqueta, atributos, linha, endereço) de cada endereço externo ou local, com o id do teste."""
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


def test_sitemap_lists_home_language_and_thanksgiving_pages():
    locs = [u.find('s:loc', SITEMAP).text for u in sitemap_urls()]
    expected = ([helpers.base()] + [helpers.base() + code + '/' for code in CODES]
                + [helpers.base() + code + '/' + GRATIARUM for code in CODES])
    assert locs == expected, 'sitemap.xml lista %s; esperado %s' % (locs, expected)


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
    main = page(name).body.split('<main', 1)[1].split('</main>', 1)[0]
    assert ('<a href="/%s/">' % code) in main, '%s: falta o link de volta a /%s/' % (name, code)


@on_thanksgiving_pages
def test_thanksgiving_has_no_unreplaced_marker(name):
    text = re.sub(r'<[^>]+>', ' ', page(name).body)
    found = re.search(r'\{[a-z_]+\}', text)
    assert not found, '%s: marcador sem trocar no texto: %s' % (name, found.group(0) if found else '')


@on_thanksgiving_pages
def test_thanksgiving_has_the_same_person_as_home(name):
    assert page(name).person() == page('index.html').person(), '%s: dados estruturados da pessoa diferentes dos da página inicial' % name


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
LATIN = ['Non nisi te, Domine', 'Gratiarum actio', 'Ingressum instruas, progressum dirigas, egressum compleas.',
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
        found.append((code, 'article.summary', c['article']['summary']))
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
    assert expected in found, '%s: falta o texto de %s em src/content/%s.toml: %r' % (name, where, code, text)


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
