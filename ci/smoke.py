"""Teste da página num Chrome sem interface, executado pelo pipeline antes de publicar.

Serve o repositório localmente e confere, nos quatro idiomas: edição certa visível,
título traduzido, fontes carregadas, nenhum erro no console (inclusive bloqueios da
CSP), troca de idioma pelo seletor, botão de currículo do idioma ativo e ausência de
rolagem horizontal no celular e em tela larga. Confere também a página 404 e a escolha
do idioma pelo país (fuso horário simulado de Brasil, Portugal, Itália, Espanha, Argentina,
México, EUA e Polônia).

Uso: python ci/smoke.py   (a partir da raiz do repositório)
Variável opcional CHROME_PATH: caminho de um Chrome já instalado.
"""
import functools
import http.server
import os
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
BASE = 'http://127.0.0.1:%d/index.html' % server.server_address[1]

STATE = """() => ({
  lang: document.documentElement.lang,
  visible: [...document.querySelectorAll('main > .t')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.lang),
  title: document.title,
  current: [...document.querySelectorAll('.langs a[aria-current]')].map(a => a.dataset.lang),
  cv: [...document.querySelectorAll('a.btn')].filter(e => e.offsetParent !== null).map(a => a.getAttribute('href')),
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  fonts: [...document.fonts].map(f => f.status)
})"""

with sync_playwright() as pw:
    chrome = os.environ.get('CHROME_PATH')
    browser = pw.chromium.launch(executable_path=chrome) if chrome else pw.chromium.launch(channel='chrome')

    for code, tag in TAGS.items():
        for width, height in ((360, 740), (1440, 900)):
            ctx = browser.new_context(viewport={'width': width, 'height': height}, locale='en-US', timezone_id='UTC')
            page = ctx.new_page()
            errors = []
            page.on('console', lambda m: errors.append(m.text) if m.type in ('error', 'warning') else None)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('requestfailed', lambda r: errors.append('falhou: ' + r.url))
            page.goto(BASE + '?lang=' + code)
            page.wait_for_load_state('networkidle')
            page.evaluate('document.fonts.ready')
            s = page.evaluate(STATE)
            where = '%s, %dpx' % (code.upper(), width)
            check(s['lang'] == tag and s['visible'] == [tag], 'edição certa visível (%s)' % where, s['visible'])
            check(s['current'] == [code], 'seletor marca o idioma ativo (%s)' % where, s['current'])
            check(len(s['cv']) == 2 and all(h.endswith('-cv-%s.pdf' % code) for h in s['cv']),
                  'botões de currículo no idioma ativo (%s)' % where, s['cv'])
            check(s['fonts'] and all(f == 'loaded' for f in s['fonts']), 'fontes carregadas (%s)' % where, s['fonts'])
            check(s['overflow'] <= 0, 'sem rolagem horizontal (%s)' % where, s['overflow'])
            check(not errors, 'console sem erros nem bloqueios da CSP (%s)' % where, errors[:3])
            ctx.close()

    # troca de idioma pelo seletor, sem recarregar
    ctx = browser.new_context(locale='pt-BR', timezone_id='UTC')  # UTC: fuso que não indica país
    page = ctx.new_page()
    errors = []
    page.on('console', lambda m: errors.append(m.text) if m.type in ('error', 'warning') else None)
    page.goto(BASE)
    page.wait_for_load_state('networkidle')
    check(page.evaluate('document.documentElement.lang') == 'pt-BR', 'idioma inicial vem do navegador')
    titles = set()
    for code, tag in (('it', 'it'), ('es', 'es'), ('en', 'en'), ('pt', 'pt-BR')):
        page.click('.langs a[data-lang="%s"]' % code)
        s = page.evaluate(STATE)
        titles.add(s['title'])
        check(s['lang'] == tag and s['visible'] == [tag] and page.evaluate('location.search') == '?lang=' + code,
              'clique em %s troca o idioma' % code.upper(), (s['lang'], s['visible']))
    check(len(titles) == 4, 'título traduzido nos quatro idiomas', titles)
    check(not errors, 'console sem erros após as trocas', errors[:3])
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
        for target in ('index.html', '404.html'):
            ctx = browser.new_context(locale=locale, timezone_id=zone)
            page = ctx.new_page()
            errors = []
            page.on('console', lambda m: errors.append(m.text) if m.type in ('error', 'warning') else None)
            page.goto(BASE.replace('index.html', target) + query)
            page.wait_for_load_state('networkidle')
            got = page.evaluate('document.documentElement.lang')
            check(got == tag and not errors, 'país: %s -> %s (%s)' % (label, tag, target), (got, errors[:2]))
            ctx.close()

    # página de erro: idioma do navegador, fontes por caminho absoluto, sem erros no console
    for locale, tag in (('pt-BR', 'pt-BR'), ('en-US', 'en'), ('es-MX', 'es'), ('it-IT', 'it'), ('de-DE', 'en')):
        ctx = browser.new_context(locale=locale, timezone_id='UTC', viewport={'width': 360, 'height': 740})
        page = ctx.new_page()
        errors = []
        page.on('console', lambda m: errors.append(m.text) if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('requestfailed', lambda r: errors.append('falhou: ' + r.url))
        page.goto(BASE.replace('index.html', '404.html'))
        page.wait_for_load_state('networkidle')
        page.evaluate('document.fonts.ready')
        s = page.evaluate("""() => ({
          lang: document.documentElement.lang,
          visible: [...document.querySelectorAll('main > .t')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.lang),
          title: document.title,
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
