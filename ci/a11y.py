"""Auditoria automática de acessibilidade (axe-core) do site montado, executada pelo pipeline.

Abre cada página num Chrome sem interface, no celular e em tela larga, e roda o axe
com as regras WCAG 2.0, 2.1 e 2.2, níveis A e AA. Qualquer violação reprova a
publicação. As recomendações de boas práticas do axe são só relatadas.

Uso: python ci/build.py && python ci/a11y.py _site caminho/para/axe.min.js
(o axe.min.js vem do pacote npm axe-core: npm install axe-core@4)
"""
import functools
import http.server
import os
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(sys.argv[1])
AXE = open(sys.argv[2], encoding='utf-8').read()
PAGES = ['?lang=pt', '?lang=en', '?lang=es', '?lang=it', 'pt/', 'en/', 'es/', 'it/', '404.html']
WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
threading.Thread(target=server.serve_forever, daemon=True).start()
SITE = 'http://127.0.0.1:%d/' % server.server_address[1]

violations, advice = [], set()
with sync_playwright() as pw:
    chrome = os.environ.get('CHROME_PATH')
    browser = pw.chromium.launch(executable_path=chrome) if chrome else pw.chromium.launch(channel='chrome')
    for path in PAGES:
        for width, height in ((360, 740), (1440, 900)):
            # bypass_csp só neste teste: a política do site bloquearia o script do axe injetado
            ctx = browser.new_context(viewport={'width': width, 'height': height}, timezone_id='UTC', bypass_csp=True)
            page = ctx.new_page()
            page.goto(SITE + path)
            page.wait_for_load_state('networkidle')
            page.evaluate('document.fonts.ready')
            page.evaluate(AXE)
            result = page.evaluate("""async (wcag) => {
              const run = await axe.run(document, { resultTypes: ['violations'] });
              return run.violations.map(v => ({ id: v.id, impact: v.impact, tags: v.tags, help: v.help,
                                                nodes: v.nodes.map(n => n.target.join(' ')).slice(0, 3) }));
            }""", WCAG)
            where = '/%s (%dpx)' % (path, width)
            for v in result:
                if set(v['tags']) & set(WCAG):
                    violations.append((where, v))
                    print('FALHA %s: %s [%s] %s -> %s' % (where, v['id'], v['impact'], v['help'], v['nodes']))
                else:
                    advice.add('%s: %s' % (v['id'], v['help']))
            if not any(w == where for w, _ in violations):
                print('ok    %s: nenhuma violação WCAG A/AA' % where)
            ctx.close()
    browser.close()
server.shutdown()

for line in sorted(advice):
    print('aviso (boa prática, não reprova): ' + line)
print('\n%s' % ('Acessibilidade: nenhuma violação WCAG A/AA.' if not violations
               else 'Acessibilidade: %d violação(ões).' % len(violations)))
sys.exit(1 if violations else 0)
