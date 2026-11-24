"""Compara, pixel a pixel, duas montagens do site (por exemplo, a do main e a de um ramo).

Serve cada pasta num servidor local, abre as mesmas páginas num Chrome sem interface,
no celular (390 px) e em tela larga (1440 px), e tira uma captura da página inteira.
As duas capturas de cada página precisam ser idênticas byte a byte: o mesmo Chrome,
com os mesmos pixels, gera o mesmo PNG.

Para a comparação não depender do momento da montagem nem do relógio:
- a data e o ano do rodapé (que vêm do último commit) são trocados por um texto fixo;
- o fuso horário e o idioma do navegador são fixos (UTC, inglês), e a página inicial
  aparece sempre em inglês;
- as animações e transições são levadas ao fim antes da captura.

Uso: python ci/compare_screens.py PASTA_ANTES PASTA_DEPOIS PASTA_CAPTURAS
     (sai com erro se alguma captura diferir; as capturas ficam em PASTA_CAPTURAS/antes e /depois)
Variável opcional CHROME_PATH: caminho de um Chrome já instalado.
"""
import functools
import http.server
import os
import sys
import threading

from playwright.sync_api import sync_playwright

PAGES = {'inicio': '', 'pt': 'pt/', 'en': 'en/', 'es': 'es/', 'it': 'it/', '404': '404.html'}
WIDTHS = (390, 1440)
FIXED_DATE = """() => {
  document.querySelectorAll('footer time').forEach(t => { t.textContent = 'DATA'; });
  document.querySelectorAll('.year').forEach(y => { y.textContent = '0000'; });
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(folder):
    handler = functools.partial(QuietHandler, directory=folder)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, 'http://127.0.0.1:%d/' % server.server_address[1]


def capture(browser, base, path, width, out):
    ctx = browser.new_context(viewport={'width': width, 'height': 900}, timezone_id='UTC', locale='en-US')
    page = ctx.new_page()
    page.goto(base + path, wait_until='load')
    page.evaluate('document.fonts.ready.then(() => true)')
    page.evaluate(FIXED_DATE)
    page.screenshot(path=out, full_page=True, animations='disabled', caret='hide')
    ctx.close()


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    before, after, out = (os.path.abspath(a) for a in sys.argv[1:])
    for label in ('antes', 'depois'):
        os.makedirs(os.path.join(out, label), exist_ok=True)
    servers = {label: serve(folder) for label, folder in (('antes', before), ('depois', after))}
    differ = []
    with sync_playwright() as pw:
        chrome = os.environ.get('CHROME_PATH')
        browser = pw.chromium.launch(executable_path=chrome) if chrome else pw.chromium.launch(channel='chrome')
        for name, path in PAGES.items():
            for width in WIDTHS:
                files = {}
                for label, (_, base) in servers.items():
                    files[label] = os.path.join(out, label, '%s-%d.png' % (name, width))
                    capture(browser, base, path, width, files[label])
                same = open(files['antes'], 'rb').read() == open(files['depois'], 'rb').read()
                print(('igual     ' if same else 'DIFERENTE ') + '/%s (%d px)' % (path, width))
                if not same:
                    differ.append('/%s (%d px)' % (path, width))
        browser.close()
    for server, _ in servers.values():
        server.shutdown()
    print('\n%s' % ('Capturas: todas idênticas.' if not differ else 'Capturas: %d diferente(s).' % len(differ)))
    sys.exit(1 if differ else 0)


if __name__ == '__main__':
    main()
