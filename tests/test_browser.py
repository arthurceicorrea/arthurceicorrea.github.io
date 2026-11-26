"""Teste do site montado num Chrome sem interface (antes: ci/smoke.py).

Serve a pasta do site localmente e confere:
- página inicial com ?lang= nos quatro idiomas, no celular e em tela larga: leva à página do
  idioma (fica na página inicial, em inglês, com ?lang=en); edição certa, seletor, sumário,
  botões de currículo, fontes, nenhuma rolagem horizontal, nenhum erro no console (inclusive
  bloqueios da CSP); o mesmo nas páginas /pt/, /en/, /es/, /it/;
- páginas por idioma: idioma fixo mesmo com fuso de outro país, título traduzido e
  funcionamento sem JavaScript;
- página inicial sem JavaScript: fica em inglês; e o botão Voltar não volta a ela depois de
  levar o visitante à página do seu idioma;
- seletor de idioma, que leva de uma página a outra;
- escolha do idioma pelo país (fuso horário simulado): a página inicial leva à página do idioma,
  e a 404 mostra a edição;
- botão de voltar ao topo, seção atual no sumário, copiar o e-mail e detalhes dos projetos;
- página de agradecimento (/pt/gratiarum-actio/ e as outras três), no celular e em tela larga:
  edição certa, título em latim, seletor, fontes, nenhuma rolagem horizontal, nenhum erro no
  console; idioma fixo mesmo com fuso de outro país e funcionamento sem JavaScript;
- colofão do rodapé: da página inicial e de /pt/ leva ao agradecimento no idioma da página; ali,
  o seletor leva à mesma página em outro idioma, e o link de volta, à página inicial do idioma;
- página 404 no idioma do navegador.

Cada cenário (página, largura, fuso, idioma do navegador) é aberto uma vez só; os testes
conferem, um a um, o que foi lido dele. O cenário aparece entre colchetes no nome do teste.

Uso: make build && python -m pytest tests/test_browser.py
"""
import unicodedata
from urllib.parse import urlparse

import pytest

from helpers import CODES, GRATIARUM

STATE = """() => ({
  lang: document.documentElement.lang,
  editions: [...document.querySelectorAll('main > .t')].map(e => e.lang),
  visible: [...document.querySelectorAll('main > .t')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.lang),
  title: document.title,
  path: location.pathname,
  current: [...document.querySelectorAll('.langs a[aria-current]')].map(a => a.dataset.lang),
  navVisible: !!document.querySelector('.langs') && getComputedStyle(document.querySelector('.langs')).display !== 'none',
  cv: [...document.querySelectorAll('a.btn')].filter(e => e.offsetParent !== null).map(a => a.getAttribute('href')),
  jumps: [...document.querySelectorAll('.jump a[href^="#"]')].filter(a => a.offsetParent !== null).map(a => { const t = document.getElementById(a.hash.slice(1)); return !!t && t.offsetParent !== null; }),
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  fonts: [...document.fonts].filter(f => f.status !== 'unloaded').map(f => f.status)
})"""
WIDTHS = {360: 740, 1440: 900}


def plain(text):
    """Nome de cenário sem acentos, para o id do teste ser legível e fácil de filtrar com -k."""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()


def landing(code):
    """Endereço aonde a página inicial leva um visitante deste idioma."""
    return '/' if code == 'en' else '/%s/' % code


def open_page(browser, site_url, path, errors=None, **options):
    options.setdefault('timezone_id', 'UTC')  # UTC: fuso que não indica país
    options.setdefault('locale', 'en-US')
    ctx = browser.new_context(**options)
    page = ctx.new_page()
    # Downloads que a página inicial começou e cancelou ao levar o visitante à página do idioma dele
    # (net::ERR_ABORTED) não são erro: a página seguinte baixa o que precisa. Qualquer outra falha é.
    left_home = []
    if errors is not None:
        started = {}
        page.on('request', lambda r: started.__setitem__(r, page.main_frame.url))
        page.on('console', lambda m: errors.append(m.text) if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('requestfailed', lambda r: (left_home if r.failure == 'net::ERR_ABORTED' and urlparse(started.get(r, '')).path == '/'
                                            else errors).append('falhou: ' + r.url))
    page.goto(site_url + path)
    page.wait_for_load_state('networkidle')
    if errors is not None and urlparse(page.url).path == '/':
        errors.extend(left_home)  # não saiu da página inicial: o cancelamento não se explica, é erro
    return ctx, page


@pytest.fixture(scope='module')
def once():
    """Roda cada cenário uma vez e guarda o resultado: once(função, argumentos...)."""
    results = {}

    def run(function, *args):
        key = (function.__name__,) + args
        if key not in results:
            results[key] = function(*args)
        return results[key]
    return run


# ---------- páginas: página inicial com ?lang= e páginas por idioma, no celular e em tela larga ----------

def visit(browser, site_url, path, width):
    errors = []
    ctx, page = open_page(browser, site_url, path, errors, viewport={'width': width, 'height': WIDTHS[width]})
    page.evaluate('document.fonts.ready')
    state = page.evaluate(STATE)
    ctx.close()
    return state, errors


PAGES = [pytest.param(code, path, width, id='/%s-%dpx' % (path, width))
         for code in CODES for path in ('?lang=' + code, code + '/') for width in WIDTHS]
on_every_page = pytest.mark.parametrize('code, path, width', PAGES)


@pytest.fixture
def state(once, browser, site_url, code, path, width):
    return once(visit, browser, site_url, path, width)


@pytest.mark.parametrize('code, path, width', [p for p in PAGES if p.values[1].startswith('?')])
def test_home_sends_visitor_to_language_page(state, code, path, width):
    s, errors = state
    assert s['path'] == landing(code), '/%s levou a %s; esperado %s' % (path, s['path'], landing(code))


@on_every_page
def test_right_edition_is_visible(state, code, path, width):
    s, errors = state
    assert s['lang'] == CODES[code] and s['visible'] == [CODES[code]], \
        '/%s: idioma %r e edição visível %s; esperado %s' % (path, s['lang'], s['visible'], CODES[code])


@on_every_page
def test_page_has_only_one_edition(state, code, path, width):
    s, errors = state
    assert s['editions'] == [CODES[code]], '/%s: edições na página %s; esperado só %s' % (path, s['editions'], CODES[code])


@on_every_page
def test_switcher_is_visible_and_marks_active_language(state, code, path, width):
    s, errors = state
    assert s['current'] == [code] and s['navVisible'], '/%s: seletor visível=%s, marcado %s; esperado %s' % (path, s['navVisible'], s['current'], code)


@on_every_page
def test_jump_menu_leads_to_five_visible_sections(state, code, path, width):
    s, errors = state
    assert len(s['jumps']) == 5 and all(s['jumps']), '/%s: o sumário deveria levar a 5 seções visíveis: %s' % (path, s['jumps'])


@on_every_page
def test_cv_buttons_are_in_active_language(state, code, path, width):
    s, errors = state
    expected = '/cv/arthur-cei-correa-cv-%s.pdf' % code
    assert len(s['cv']) == 2 and all(h == expected for h in s['cv']), '/%s: botões de currículo %s; esperado 2 para %s' % (path, s['cv'], expected)


@on_every_page
def test_fonts_are_loaded(state, code, path, width):
    s, errors = state
    assert s['fonts'] and all(f == 'loaded' for f in s['fonts']), '/%s: fontes não carregadas: %s' % (path, s['fonts'])


@on_every_page
def test_no_horizontal_scroll(state, code, path, width):
    s, errors = state
    assert s['overflow'] <= 0, '/%s a %d px: a página rola %d px na horizontal' % (path, width, s['overflow'])


@on_every_page
def test_console_has_no_errors_or_csp_blocks(state, code, path, width):
    s, errors = state
    assert not errors, '/%s: erros no console ou recursos que falharam: %s' % (path, errors[:3])


# ---------- páginas por idioma: idioma fixo e sem JavaScript ----------

def fixed_language(browser, site_url, code):
    ctx, page = open_page(browser, site_url, code + '/', timezone_id='Europe/Rome' if code != 'it' else 'America/Sao_Paulo')
    state = page.evaluate(STATE)
    ctx.close()
    return state


def without_javascript(browser, site_url, path):
    ctx, page = open_page(browser, site_url, path, java_script_enabled=False, timezone_id='America/Sao_Paulo', locale='pt-BR')
    state = page.evaluate(STATE)
    ctx.close()
    return state


@pytest.mark.parametrize('code', list(CODES))
def test_language_is_fixed_with_time_zone_of_another_country(once, browser, site_url, code):
    s = once(fixed_language, browser, site_url, code)
    assert s['lang'] == CODES[code], '/%s/ com fuso de outro país mostrou %r' % (code, s['lang'])


@pytest.mark.parametrize('code', list(CODES))
def test_language_page_works_without_javascript(once, browser, site_url, code):
    s = once(without_javascript, browser, site_url, code + '/')
    tag = CODES[code]
    assert s['lang'] == tag and s['visible'] == [tag] and s['current'] == [code] and s['navVisible'], \
        '/%s/ sem JavaScript: idioma %r, edição visível %s, seletor %s' % (code, s['lang'], s['visible'], s['current'])


def test_title_is_translated_on_four_pages(once, browser, site_url):
    titles = {once(fixed_language, browser, site_url, code)['title'] for code in CODES}
    assert len(titles) == 4, 'os títulos deveriam ser quatro, um por idioma: %s' % titles


# ---------- página inicial: sem JavaScript e botão Voltar ----------

def test_home_without_javascript_stays_in_english(once, browser, site_url):
    s = once(without_javascript, browser, site_url, '')
    assert s['lang'] == 'en' and s['visible'] == ['en'] and s['current'] == ['en'] and s['path'] == '/', \
        'página inicial sem JavaScript: idioma %r, edição visível %s, seletor %s, endereço %s' % (s['lang'], s['visible'], s['current'], s['path'])


def test_back_does_not_return_to_home_after_redirect(browser, site_url):
    ctx, page = open_page(browser, site_url, '', timezone_id='Europe/Rome')
    page.go_back()
    url = page.url
    ctx.close()
    assert not url.startswith(site_url), 'o botão Voltar voltou ao site (%s): a página inicial ficou no histórico' % url


# ---------- seletor: leva de uma página a outra ----------

def switcher_tour(browser, site_url):
    errors, steps = [], {}
    ctx, page = open_page(browser, site_url, '', errors, locale='pt-BR')
    start = page.evaluate(STATE)
    for code in ('it', 'es', 'en', 'pt'):
        with page.expect_navigation():
            page.click('.langs a[data-lang="%s"]' % code)
        page.wait_for_load_state('networkidle')
        steps[code] = page.evaluate(STATE)
    ctx.close()
    return start, steps, errors


def test_home_follows_browser_language(once, browser, site_url):
    start, steps, errors = once(switcher_tour, browser, site_url)
    assert start['lang'] == 'pt-BR' and start['path'] == '/pt/', \
        'navegador em português, fuso sem país: a página inicial levou a %s (%r); esperado /pt/' % (start['path'], start['lang'])


@pytest.mark.parametrize('code', ['it', 'es', 'en', 'pt'])
def test_switcher_leads_to_language_page(once, browser, site_url, code):
    start, steps, errors = once(switcher_tour, browser, site_url)
    s = steps[code]
    assert s['lang'] == CODES[code] and s['editions'] == [CODES[code]] and s['path'] == '/%s/' % code, \
        'o seletor %s levou a %s (idioma %r)' % (code.upper(), s['path'], s['lang'])


def test_console_has_no_errors_while_switching(once, browser, site_url):
    start, steps, errors = once(switcher_tour, browser, site_url)
    assert not errors, 'erros no console ao navegar pelo seletor: %s' % errors[:3]


# ---------- idioma pelo país (fuso horário do aparelho), com navegador em outro idioma ----------

COUNTRIES = [
    ('America/Sao_Paulo', 'en-US', '', 'pt', 'Brasil'),
    ('America/Manaus', 'en-US', '', 'pt', 'Brasil (Manaus)'),
    ('Europe/Lisbon', 'en-GB', '', 'pt', 'Portugal'),
    ('Europe/Rome', 'en-US', '', 'it', 'Itália'),
    ('Europe/Madrid', 'en-US', '', 'es', 'Espanha'),
    ('America/Argentina/Buenos_Aires', 'en-US', '', 'es', 'Argentina'),
    ('America/Mexico_City', 'en-US', '', 'es', 'México'),
    ('America/New_York', 'en-US', '', 'en', 'EUA'),
    ('Europe/Warsaw', 'pl-PL', '', 'en', 'Polônia'),
    ('Europe/Warsaw', 'es-ES', '', 'es', 'Polônia, navegador em espanhol'),
    ('America/Sao_Paulo', 'pt-BR', '?lang=it', 'it', 'Brasil com ?lang=it'),
]


@pytest.mark.parametrize('zone, locale, query, code, target', [
    pytest.param(zone, locale, query, code, target, id=plain('%s-%s-/%s' % (label, code, target)))
    for zone, locale, query, code, label in COUNTRIES for target in ('', '404.html')])
def test_language_by_country(browser, site_url, zone, locale, query, code, target):
    errors = []
    ctx, page = open_page(browser, site_url, target + query, errors, locale=locale, timezone_id=zone)
    got, landed = page.evaluate('document.documentElement.lang'), page.evaluate('location.pathname')
    ctx.close()
    assert got == CODES[code], 'fuso %s, navegador %s, /%s%s: idioma %r; esperado %r' % (zone, locale, target, query, got, CODES[code])
    if not target:
        assert landed == landing(code), 'fuso %s: a página inicial levou a %s; esperado %s' % (zone, landed, landing(code))
    assert not errors, 'fuso %s, /%s%s: erros no console: %s' % (zone, target, query, errors[:2])


# ---------- botão de voltar ao topo e seção atual no sumário ----------

def top_button(browser, site_url, width):
    ctx, page = open_page(browser, site_url, 'pt/', viewport={'width': width, 'height': 800})
    shown = lambda: page.evaluate("getComputedStyle(document.querySelector('.totop')).visibility")  # noqa: E731
    seen = {'at_top': shown()}
    page.evaluate('window.scrollTo({top: document.body.scrollHeight, behavior: "instant"})')
    page.wait_for_timeout(1200)  # recolhido enquanto rola para baixo; volta 0,7 s depois de parar
    seen['after_scroll'] = shown()
    page.click('.jump a[href="#projetos"]')
    for _ in range(30):
        if page.evaluate("document.querySelector('.jump a[href=\"#projetos\"]').getAttribute('aria-current')") == 'location':
            break
        page.wait_for_timeout(100)
    seen['marked'] = page.evaluate("[...document.querySelectorAll('.jump a[aria-current]')].map(a => a.hash)")
    page.evaluate('window.scrollBy({top: -300, behavior: "instant"})')
    page.wait_for_timeout(50)
    page.evaluate('window.scrollBy({top: 200, behavior: "instant"})')
    page.wait_for_timeout(400)  # o recolhimento leva 0,25 s
    seen['scrolling_down'] = shown()
    page.wait_for_timeout(1200)
    seen['stopped'] = shown()
    page.click('.totop')
    for _ in range(50):  # a CSP do site barra wait_for_function; consulta a posição até chegar ao topo
        if page.evaluate('window.scrollY') == 0:
            break
        page.wait_for_timeout(100)
    page.wait_for_timeout(600)
    seen['back_at_top'] = shown()
    ctx.close()
    return seen


on_both_widths = pytest.mark.parametrize('width', list(WIDTHS), ids=lambda w: '%dpx' % w)


@on_both_widths
def test_back_to_top_button_is_hidden_at_the_top(once, browser, site_url, width):
    assert once(top_button, browser, site_url, width)['at_top'] == 'hidden', 'o botão de voltar ao topo aparece no alto da página'


@on_both_widths
def test_back_to_top_button_appears_after_scrolling(once, browser, site_url, width):
    assert once(top_button, browser, site_url, width)['after_scroll'] == 'visible', 'o botão de voltar ao topo não aparece depois de rolar'


@on_both_widths
def test_jump_menu_marks_the_section_being_read(once, browser, site_url, width):
    marked = once(top_button, browser, site_url, width)['marked']
    assert marked == ['#projetos'], 'o sumário deveria marcar #projetos, marcou %s' % marked


@on_both_widths
def test_back_to_top_button_hides_while_scrolling_down(once, browser, site_url, width):
    assert once(top_button, browser, site_url, width)['scrolling_down'] == 'hidden', 'o botão não se recolhe enquanto se rola para baixo'


@on_both_widths
def test_back_to_top_button_returns_when_scrolling_stops(once, browser, site_url, width):
    assert once(top_button, browser, site_url, width)['stopped'] == 'visible', 'o botão não volta quando a rolagem para'


@on_both_widths
def test_back_to_top_button_leads_to_top_and_hides(once, browser, site_url, width):
    assert once(top_button, browser, site_url, width)['back_at_top'] == 'hidden', 'o botão não leva ao topo ou não some depois'


# ---------- copiar o e-mail e detalhes dos projetos ----------

def copy_and_details(browser, site_url):
    ctx, page = open_page(browser, site_url, 'pt/', permissions=['clipboard-read', 'clipboard-write'])
    copy = page.locator('.intro .copy')
    seen = {'copy_visible': copy.is_visible()}
    copy.click()
    page.wait_for_timeout(200)
    seen['clipboard'] = page.evaluate('navigator.clipboard.readText()')
    seen['status'] = page.locator('.intro .copy + [role=status]').inner_text()
    summary = page.locator('#projetos summary').first
    seen['closed'] = summary.inner_text().strip()
    summary.click()
    page.wait_for_timeout(100)
    seen['open'] = summary.inner_text().strip()
    ctx.close()
    return seen


def test_copy_email_button_appears(once, browser, site_url):
    assert once(copy_and_details, browser, site_url)['copy_visible'], 'o botão de copiar o e-mail não aparece em /pt/'


def test_copy_email_button_copies_the_address(once, browser, site_url):
    got = once(copy_and_details, browser, site_url)['clipboard']
    assert got == 'arthurceicorrea@gmail.com', 'a área de transferência ficou com %r' % got


def test_screen_reader_is_told_about_the_copy(once, browser, site_url):
    got = once(copy_and_details, browser, site_url)['status']
    assert got == 'E-mail copiado.', 'o aviso para leitores de tela foi %r; esperado "E-mail copiado."' % got


def test_closed_details_say_see_details(once, browser, site_url):
    got = once(copy_and_details, browser, site_url)['closed']
    assert got.lower() == 'ver detalhes', 'detalhes fechados dizem %r; esperado "Ver detalhes"' % got


def test_open_details_say_hide_details(once, browser, site_url):
    got = once(copy_and_details, browser, site_url)['open']
    assert got.lower() == 'ocultar detalhes', 'detalhes abertos dizem %r; esperado "Ocultar detalhes"' % got


# ---------- página de agradecimento (Gratiarum actio) ----------

THANKSGIVING_TITLE = 'Gratiarum actio — Arthur Cei Corrêa'
THANKS = [pytest.param(code, width, id='/%s/%s-%dpx' % (code, GRATIARUM.rstrip('/'), width)) for code in CODES for width in WIDTHS]
on_thanksgiving_pages = pytest.mark.parametrize('code, width', THANKS)


def thanksgiving(browser, site_url, code, width):
    return visit(browser, site_url, code + '/' + GRATIARUM, width)


@on_thanksgiving_pages
def test_thanksgiving_shows_its_edition_only(once, browser, site_url, code, width):
    s, errors = once(thanksgiving, browser, site_url, code, width)
    assert s['lang'] == CODES[code] and s['editions'] == [CODES[code]] and s['visible'] == [CODES[code]], \
        '/%s/%s: idioma %r, edições %s, visível %s' % (code, GRATIARUM, s['lang'], s['editions'], s['visible'])


@on_thanksgiving_pages
def test_thanksgiving_title_is_the_latin_title(once, browser, site_url, code, width):
    s, errors = once(thanksgiving, browser, site_url, code, width)
    assert s['title'] == THANKSGIVING_TITLE, '/%s/%s: título %r; esperado %r' % (code, GRATIARUM, s['title'], THANKSGIVING_TITLE)


@on_thanksgiving_pages
def test_thanksgiving_switcher_is_visible_and_marks_active_language(once, browser, site_url, code, width):
    s, errors = once(thanksgiving, browser, site_url, code, width)
    assert s['current'] == [code] and s['navVisible'], '/%s/%s: seletor visível=%s, marcado %s' % (code, GRATIARUM, s['navVisible'], s['current'])


@on_thanksgiving_pages
def test_thanksgiving_fonts_are_loaded(once, browser, site_url, code, width):
    s, errors = once(thanksgiving, browser, site_url, code, width)
    assert s['fonts'] and all(f == 'loaded' for f in s['fonts']), '/%s/%s: fontes não carregadas: %s' % (code, GRATIARUM, s['fonts'])


@on_thanksgiving_pages
def test_thanksgiving_has_no_horizontal_scroll(once, browser, site_url, code, width):
    s, errors = once(thanksgiving, browser, site_url, code, width)
    assert s['overflow'] <= 0, '/%s/%s a %d px: a página rola %d px na horizontal' % (code, GRATIARUM, width, s['overflow'])


@on_thanksgiving_pages
def test_thanksgiving_console_has_no_errors_or_csp_blocks(once, browser, site_url, code, width):
    s, errors = once(thanksgiving, browser, site_url, code, width)
    assert not errors, '/%s/%s: erros no console ou recursos que falharam: %s' % (code, GRATIARUM, errors[:3])


def thanksgiving_fixed_language(browser, site_url, code):
    ctx, page = open_page(browser, site_url, code + '/' + GRATIARUM, timezone_id='Europe/Rome' if code != 'it' else 'America/Sao_Paulo')
    state = page.evaluate(STATE)
    ctx.close()
    return state


@pytest.mark.parametrize('code', list(CODES))
def test_thanksgiving_language_is_fixed_with_time_zone_of_another_country(once, browser, site_url, code):
    s = once(thanksgiving_fixed_language, browser, site_url, code)
    assert s['lang'] == CODES[code] and s['path'] == '/%s/%s' % (code, GRATIARUM), \
        '/%s/%s com fuso de outro país mostrou %r em %s' % (code, GRATIARUM, s['lang'], s['path'])


@pytest.mark.parametrize('code', list(CODES))
def test_thanksgiving_works_without_javascript(once, browser, site_url, code):
    s = once(without_javascript, browser, site_url, code + '/' + GRATIARUM)
    tag = CODES[code]
    assert s['lang'] == tag and s['visible'] == [tag] and s['current'] == [code] and s['navVisible'], \
        '/%s/%s sem JavaScript: idioma %r, edição visível %s, seletor %s' % (code, GRATIARUM, s['lang'], s['visible'], s['current'])


# ---------- colofão: leva ao agradecimento; dali, o seletor e o link de volta ----------

def colophon_tour(browser, site_url):
    """Da página inicial (em inglês) pelo colofão; dali ao italiano pelo seletor e de volta à página
    inicial italiana pelo link de volta. Depois, de /pt/ pelo colofão."""
    errors, steps = [], {}
    ctx, page = open_page(browser, site_url, '', errors)
    steps['home'] = page.evaluate(STATE)['path']
    for name, selector in (('colophon', '.foot .colophon a'), ('switcher', '.langs a[data-lang="it"]'), ('back', 'main .back a')):
        with page.expect_navigation():
            page.click(selector)
        page.wait_for_load_state('networkidle')
        steps[name] = page.evaluate(STATE)
    page.goto(site_url + 'pt/')
    page.wait_for_load_state('networkidle')
    with page.expect_navigation():
        page.click('.foot .colophon a')
    page.wait_for_load_state('networkidle')
    steps['from_pt'] = page.evaluate(STATE)
    ctx.close()
    return steps, errors


def test_colophon_on_home_leads_to_english_thanksgiving(once, browser, site_url):
    steps, errors = once(colophon_tour, browser, site_url)
    s = steps['colophon']
    assert steps['home'] == '/' and s['path'] == '/en/' + GRATIARUM and s['lang'] == 'en', \
        'o colofão da página inicial (%s) levou a %s (%r); esperado /en/%s' % (steps['home'], s['path'], s['lang'], GRATIARUM)


def test_colophon_on_language_page_leads_to_its_thanksgiving(once, browser, site_url):
    steps, errors = once(colophon_tour, browser, site_url)
    s = steps['from_pt']
    assert s['path'] == '/pt/' + GRATIARUM and s['lang'] == 'pt-BR', 'o colofão de /pt/ levou a %s (%r)' % (s['path'], s['lang'])


def test_thanksgiving_switcher_leads_to_the_same_page_in_another_language(once, browser, site_url):
    steps, errors = once(colophon_tour, browser, site_url)
    s = steps['switcher']
    assert s['path'] == '/it/' + GRATIARUM and s['lang'] == 'it', 'o seletor IT levou a %s (%r)' % (s['path'], s['lang'])


def test_thanksgiving_back_link_leads_to_home_page_of_its_language(once, browser, site_url):
    steps, errors = once(colophon_tour, browser, site_url)
    s = steps['back']
    assert s['path'] == '/it/' and s['lang'] == 'it', 'o link de volta levou a %s (%r); esperado /it/' % (s['path'], s['lang'])


def test_console_has_no_errors_along_the_colophon(once, browser, site_url):
    steps, errors = once(colophon_tour, browser, site_url)
    assert not errors, 'erros no console no caminho pelo colofão: %s' % errors[:3]


# ---------- página de erro: idioma do navegador, fontes por caminho absoluto, sem erros no console ----------

ERROR_STATE = """() => ({
  lang: document.documentElement.lang,
  visible: [...document.querySelectorAll('main > .t')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.lang),
  home: [...document.querySelectorAll('a.btn')].filter(e => e.offsetParent !== null).map(a => a.getAttribute('href')),
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  fonts: [...document.fonts].filter(f => f.status !== 'unloaded').map(f => f.status)
})"""


def error_page(browser, site_url, locale):
    errors = []
    ctx, page = open_page(browser, site_url, '404.html', errors, locale=locale, viewport={'width': 360, 'height': 740})
    page.evaluate('document.fonts.ready')
    state = page.evaluate(ERROR_STATE)
    ctx.close()
    return state, errors


on_error_page = pytest.mark.parametrize('locale, tag', [('pt-BR', 'pt-BR'), ('en-US', 'en'), ('es-MX', 'es'), ('it-IT', 'it'), ('de-DE', 'en')],
                                        ids=lambda v: v if '-' in v else None)


@on_error_page
def test_error_page_shows_browser_language(once, browser, site_url, locale, tag):
    s, errors = once(error_page, browser, site_url, locale)
    assert s['lang'] == tag and s['visible'] == [tag], '404 com navegador %s: idioma %r, edição visível %s; esperado %s' % (locale, s['lang'], s['visible'], tag)


@on_error_page
def test_error_page_button_leads_home(once, browser, site_url, locale, tag):
    s, errors = once(error_page, browser, site_url, locale)
    assert s['home'] == ['/'], '404 com navegador %s: o botão leva a %s; esperado /' % (locale, s['home'])


@on_error_page
def test_error_page_fonts_are_loaded(once, browser, site_url, locale, tag):
    s, errors = once(error_page, browser, site_url, locale)
    assert s['fonts'] and all(f == 'loaded' for f in s['fonts']), '404 com navegador %s: fontes não carregadas: %s' % (locale, s['fonts'])


@on_error_page
def test_error_page_has_no_scroll_or_console_errors(once, browser, site_url, locale, tag):
    s, errors = once(error_page, browser, site_url, locale)
    assert s['overflow'] <= 0 and not errors, '404 com navegador %s: rolagem horizontal %d px, erros: %s' % (locale, s['overflow'], errors[:3])
