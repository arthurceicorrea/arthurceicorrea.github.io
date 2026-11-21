"""Teste do site montado num Chrome sem interface, executado pelo pipeline antes de publicar.

Serve a pasta _site localmente e confere:
- página inicial com ?lang= nos quatro idiomas, no celular e em tela larga: edição certa,
  seletor, botões de currículo, fontes, nenhuma rolagem horizontal, nenhum erro no console
  (inclusive bloqueios da CSP);
- páginas /pt/, /en/, /es/, /it/: uma só edição, idioma fixo mesmo com fuso de outro país,
  título traduzido, e funcionamento sem JavaScript;
- seletor de idioma, que leva de uma página a outra;
- escolha do idioma pelo país (fuso horário simulado de Brasil, Portugal, Itália, Espanha,
  Argentina, México, EUA e Polônia), na página inicial e na 404;
- página 404 no idioma do navegador.

Uso: python ci/build.py && python ci/smoke.py _site
Variável opcional CHROME_PATH: caminho de um Chrome já instalado.
"""
import functools
import http.server
import os
import sys
import threading

from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, '_site')
if not os.path.isfile(os.path.join(ROOT, 'index.html')):
    sys.exit('Site montado não encontrado em %s. Rode antes: python ci/build.py' % ROOT)
TAGS = {'pt': 'pt-BR', 'en': 'en', 'es': 'es', 'it': 'it'}
failures = []


def check(ok, label, detail=''):
    print(('ok    ' if ok else 'FALHA ') + label + (' :: %s' % (detail,) if detail and not ok else ''))
    if not ok:
        failures.append(label)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
threading.Thread(target=server.serve_forever, daemon=True).start()
SITE = 'http://127.0.0.1:%d/' % server.server_address[1]

STATE = """() => ({
  lang: document.documentElement.lang,
  editions: [...document.querySelectorAll('main > .t')].map(e => e.lang),
  visible: [...document.querySelectorAll('main > .t')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.lang),
  title: document.title,
  current: [...document.querySelectorAll('.langs a[aria-current]')].map(a => a.dataset.lang),
  navVisible: !!document.querySelector('.langs') && getComputedStyle(document.querySelector('.langs')).display !== 'none',
  cv: [...document.querySelectorAll('a.btn')].filter(e => e.offsetParent !== null).map(a => a.getAttribute('href')),
  jumps: [...document.querySelectorAll('.jump a[href^="#"]')].filter(a => a.offsetParent !== null).map(a => { const t = document.getElementById(a.hash.slice(1)); return !!t && t.offsetParent !== null; }),
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  fonts: [...document.fonts].filter(f => f.status !== 'unloaded').map(f => f.status)
})"""


def open_page(browser, path, errors=None, **options):
    options.setdefault('timezone_id', 'UTC')  # UTC: fuso que não indica país
    options.setdefault('locale', 'en-US')
    ctx = browser.new_context(**options)
    page = ctx.new_page()
    if errors is not None:
        page.on('console', lambda m: errors.append(m.text) if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('requestfailed', lambda r: errors.append('falhou: ' + r.url))
    page.goto(SITE + path)
    page.wait_for_load_state('networkidle')
    return ctx, page


with sync_playwright() as pw:
    chrome = os.environ.get('CHROME_PATH')
    browser = pw.chromium.launch(executable_path=chrome) if chrome else pw.chromium.launch(channel='chrome')

    # página inicial e páginas por idioma, no celular e em tela larga
    for code, tag in TAGS.items():
        for path in ('?lang=' + code, code + '/'):
            for width, height in ((360, 740), (1440, 900)):
                errors = []
                ctx, page = open_page(browser, path, errors, viewport={'width': width, 'height': height})
                page.evaluate('document.fonts.ready')
                s = page.evaluate(STATE)
                where = '/%s, %dpx' % (path, width)
                check(s['lang'] == tag and s['visible'] == [tag], 'edição certa visível (%s)' % where, s['visible'])
                if path.endswith('/'):
                    check(s['editions'] == [tag], 'só uma edição na página (%s)' % where, s['editions'])
                check(s['current'] == [code] and s['navVisible'], 'seletor visível e no idioma ativo (%s)' % where, s['current'])
                check(len(s['jumps']) == 5 and all(s['jumps']), 'sumário leva às cinco seções visíveis (%s)' % where, s['jumps'])
                check(len(s['cv']) == 2 and all(h == '/cv/arthur-cei-correa-cv-%s.pdf' % code for h in s['cv']),
                      'botões de currículo no idioma ativo (%s)' % where, s['cv'])
                check(s['fonts'] and all(f == 'loaded' for f in s['fonts']), 'fontes carregadas (%s)' % where, s['fonts'])
                check(s['overflow'] <= 0, 'sem rolagem horizontal (%s)' % where, s['overflow'])
                check(not errors, 'console sem erros nem bloqueios da CSP (%s)' % where, errors[:3])
                ctx.close()

    # páginas por idioma: idioma fixo mesmo com fuso de outro país, e sem JavaScript
    titles = set()
    for code, tag in TAGS.items():
        ctx, page = open_page(browser, code + '/', timezone_id='Europe/Rome' if code != 'it' else 'America/Sao_Paulo')
        s = page.evaluate(STATE)
        titles.add(s['title'])
        check(s['lang'] == tag, 'idioma fixo na página /%s/ com fuso de outro país' % code, s['lang'])
        ctx.close()
        ctx, page = open_page(browser, code + '/', java_script_enabled=False)
        s = page.evaluate(STATE)
        check(s['lang'] == tag and s['visible'] == [tag] and s['current'] == [code] and s['navVisible'],
              'página /%s/ funciona sem JavaScript' % code, (s['lang'], s['visible'], s['current']))
        ctx.close()
    check(len(titles) == 4, 'título traduzido nas quatro páginas', titles)

    # seletor: leva de uma página a outra
    errors = []
    ctx, page = open_page(browser, '', errors, locale='pt-BR')
    check(page.evaluate('document.documentElement.lang') == 'pt-BR', 'página inicial no idioma do navegador (fuso sem país)')
    for code, tag in (('it', 'it'), ('es', 'es'), ('en', 'en'), ('pt', 'pt-BR')):
        with page.expect_navigation():
            page.click('.langs a[data-lang="%s"]' % code)
        page.wait_for_load_state('networkidle')
        s = page.evaluate(STATE)
        check(s['lang'] == tag and s['editions'] == [tag] and page.evaluate('location.pathname') == '/%s/' % code,
              'seletor leva à página /%s/' % code, (s['lang'], page.evaluate('location.pathname')))
    check(not errors, 'console sem erros ao navegar pelo seletor', errors[:3])
    ctx.close()

    # idioma pelo país (fuso horário do aparelho), com navegador em outro idioma
    cases = [
        ('America/Sao_Paulo', 'en-US', '', 'pt-BR', 'Brasil'),
        ('America/Manaus', 'en-US', '', 'pt-BR', 'Brasil (Manaus)'),
        ('Europe/Lisbon', 'en-GB', '', 'pt-BR', 'Portugal'),
        ('Europe/Rome', 'en-US', '', 'it', 'Itália'),
        ('Europe/Madrid', 'en-US', '', 'es', 'Espanha'),
        ('America/Argentina/Buenos_Aires', 'en-US', '', 'es', 'Argentina'),
        ('America/Mexico_City', 'en-US', '', 'es', 'México'),
        ('America/New_York', 'en-US', '', 'en', 'EUA'),
        ('Europe/Warsaw', 'pl-PL', '', 'en', 'Polônia'),
        ('Europe/Warsaw', 'es-ES', '', 'es', 'Polônia, navegador em espanhol'),
        ('America/Sao_Paulo', 'pt-BR', '?lang=it', 'it', 'Brasil com ?lang=it'),
    ]
    for zone, locale, query, tag, label in cases:
        for target in ('', '404.html'):
            errors = []
            ctx, page = open_page(browser, target + query, errors, locale=locale, timezone_id=zone)
            got = page.evaluate('document.documentElement.lang')
            check(got == tag and not errors, 'país: %s -> %s (/%s)' % (label, tag, target), (got, errors[:2]))
            ctx.close()

    # botão de voltar ao topo: escondido no alto, aparece ao rolar e leva de volta ao início
    for width in (360, 1440):
        ctx, page = open_page(browser, 'pt/', viewport={'width': width, 'height': 800})
        shown = lambda: page.evaluate("getComputedStyle(document.querySelector('.totop')).visibility")
        check(shown() == 'hidden', 'botão de voltar ao topo escondido no alto (%dpx)' % width, shown())
        page.evaluate('window.scrollTo({top: document.body.scrollHeight, behavior: "instant"})')
        page.wait_for_timeout(1200)  # recolhido enquanto rola para baixo; volta 0,7 s depois de parar
        check(shown() == 'visible', 'botão de voltar ao topo aparece ao rolar (%dpx)' % width, shown())
        page.click('.jump a[href="#projetos"]')
        for _ in range(30):
            if page.evaluate("document.querySelector('.jump a[href=\"#projetos\"]').getAttribute('aria-current')") == 'location':
                break
            page.wait_for_timeout(100)
        marked = page.evaluate("[...document.querySelectorAll('.jump a[aria-current]')].map(a => a.hash)")
        check(marked == ['#projetos'], 'sumário marca a seção que está sendo lida (%dpx)' % width, marked)
        page.evaluate('window.scrollBy({top: -300, behavior: "instant"})'); page.wait_for_timeout(50)
        page.evaluate('window.scrollBy({top: 200, behavior: "instant"})'); page.wait_for_timeout(400)  # o recolhimento leva 0,25 s
        check(shown() == 'hidden', 'botão se recolhe enquanto se rola para baixo (%dpx)' % width, shown())
        page.wait_for_timeout(1200)
        check(shown() == 'visible', 'botão volta quando a rolagem para (%dpx)' % width, shown())
        page.click('.totop')
        for _ in range(50):  # a CSP do site barra wait_for_function; consulta a posição até chegar ao topo
            if page.evaluate('window.scrollY') == 0:
                break
            page.wait_for_timeout(100)
        page.wait_for_timeout(600)
        check(shown() == 'hidden', 'botão leva ao topo e some de novo (%dpx)' % width, shown())
        ctx.close()

    # copiar o e-mail: o botão aparece, copia o endereço e avisa
    ctx, page = open_page(browser, 'pt/', permissions=['clipboard-read', 'clipboard-write'])
    copy = page.locator('.intro .copy')
    check(copy.is_visible(), 'botão de copiar o e-mail aparece', copy.count())
    copy.click(); page.wait_for_timeout(200)
    check(page.evaluate('navigator.clipboard.readText()') == 'arthurceicorrea@gmail.com', 'e-mail copiado para a área de transferência')
    check(page.locator('.intro .copy + [role=status]').inner_text() == 'E-mail copiado.', 'leitor de tela é avisado da cópia')
    summary = page.locator('#projetos summary').first
    check(summary.inner_text().strip().lower() == 'ver detalhes', 'detalhes fechados dizem "Ver detalhes"', summary.inner_text())
    summary.click(); page.wait_for_timeout(100)
    check(summary.inner_text().strip().lower() == 'ocultar detalhes', 'detalhes abertos dizem "Ocultar detalhes"', summary.inner_text())
    ctx.close()

    # página de erro: idioma do navegador, fontes por caminho absoluto, sem erros no console
    for locale, tag in (('pt-BR', 'pt-BR'), ('en-US', 'en'), ('es-MX', 'es'), ('it-IT', 'it'), ('de-DE', 'en')):
        errors = []
        ctx, page = open_page(browser, '404.html', errors, locale=locale, viewport={'width': 360, 'height': 740})
        page.evaluate('document.fonts.ready')
        s = page.evaluate("""() => ({
          lang: document.documentElement.lang,
          visible: [...document.querySelectorAll('main > .t')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.lang),
          home: [...document.querySelectorAll('a.btn')].filter(e => e.offsetParent !== null).map(a => a.getAttribute('href')),
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          fonts: [...document.fonts].filter(f => f.status !== 'unloaded').map(f => f.status)
        })""")
        where = '404, navegador %s' % locale
        check(s['lang'] == tag and s['visible'] == [tag], 'edição certa visível (%s)' % where, s['visible'])
        check(s['home'] == ['/'], 'botão leva ao início (%s)' % where, s['home'])
        check(s['fonts'] and all(f == 'loaded' for f in s['fonts']), 'fontes carregadas (%s)' % where, s['fonts'])
        check(s['overflow'] <= 0 and not errors, 'sem rolagem horizontal nem erros no console (%s)' % where, errors[:3])
        ctx.close()
    browser.close()

server.shutdown()
print('\n%s' % ('Teste no navegador: tudo certo.' if not failures else 'Teste no navegador: %d falha(s).' % len(failures)))
sys.exit(1 if failures else 0)
