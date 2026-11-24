"""Verifica o site no ar: usado depois de cada publicação e, uma vez por semana, pelo monitoramento.

Confere:
- (com --expect-version) que o site no ar já serve o commit que acabou de ser publicado,
  tentando por até 10 minutos, enquanto a publicação se propaga;
- página inicial e páginas /pt/, /en/, /es/, /it/: resposta 200, HTML, idioma certo e
  política de segurança presente;
- página 404 personalizada para endereços inexistentes;
- robots.txt, sitemap.xml, currículos em PDF, fontes, folhas de estilo e scripts de /assets/
  e imagens de prévia;
- redirecionamento de http para https;
- certificado HTTPS válido por pelo menos 14 dias.

Uso: python ci/monitor.py https://arthurceicorrea.github.io/ [--expect-version SHA]
Só usa a biblioteca padrão do Python.
"""
import datetime
import http.client
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urljoin, urlparse

BASE = sys.argv[1].rstrip('/') + '/'
EXPECT = sys.argv[sys.argv.index('--expect-version') + 1] if '--expect-version' in sys.argv else None
HOST = urlparse(BASE).hostname
AGENT = 'portfolio-monitor (+%s)' % BASE
results = []


def check(ok, label, detail=''):
    print(('ok    ' if ok else 'FALHA ') + label + (' :: %s' % (detail,) if detail and not ok else ''))
    results.append((ok, label, '' if ok else str(detail)))


def fetch(path, fresh=False):
    """Devolve (status, tipo de conteúdo, corpo). fresh=True contorna o cache da CDN."""
    url = urljoin(BASE, path)
    if fresh:
        url += ('&' if '?' in url else '?') + 'nocache=' + uuid.uuid4().hex
    request = urllib.request.Request(url, headers={'User-Agent': AGENT, 'Cache-Control': 'no-cache'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.headers.get('Content-Type', ''), response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers.get('Content-Type', ''), error.read()
        except (urllib.error.URLError, socket.timeout, ConnectionError) as error:
            if attempt == 2:
                return 0, '', str(error).encode()
            time.sleep(5)


# ---------- versão publicada ----------
if EXPECT:
    deadline, served = time.time() + 600, ''
    while True:
        status, _, body = fetch('version.txt', fresh=True)
        served = body.decode('utf-8', 'replace').strip() if status == 200 else 'HTTP %d' % status
        if served == EXPECT or time.time() > deadline:
            break
        time.sleep(20)
    check(served == EXPECT, 'o site no ar serve o commit publicado (%s)' % EXPECT[:7], 'serve: %s' % served[:40])

# ---------- páginas ----------
PAGES = {'': None, 'pt/': 'pt-BR', 'en/': 'en', 'es/': 'es', 'it/': 'it'}
for path, tag in PAGES.items():
    status, kind, body = fetch(path, fresh=True)
    html = body.decode('utf-8', 'replace')
    where = '/' + path
    check(status == 200 and kind.startswith('text/html'), 'página responde (%s)' % where, '%s %s' % (status, kind))
    check('http-equiv="Content-Security-Policy"' in html, 'política de segurança presente (%s)' % where)
    if tag:
        check('<html lang="%s" data-lang="%s">' % (tag, path[:2]) in html, 'idioma certo (%s)' % where)
    else:
        check('Sapientis est ordinare' in html and '<html lang="en" data-home>' in html, 'página inicial em inglês, marcada para levar ao idioma do visitante')

status, kind, body = fetch('esta-pagina-nao-existe-' + uuid.uuid4().hex[:8])
check(status == 404 and b'Page not found' in body, 'endereço inexistente mostra a página 404 do site', status)

# ---------- arquivos ----------
FILES = {
    'robots.txt': ('text/plain', b'Sitemap:'),
    'sitemap.xml': ('xml', b'<urlset'),
    'cv/arthur-cei-correa-cv-pt.pdf': ('application/pdf', b'%PDF'),
    'cv/arthur-cei-correa-cv-en.pdf': ('application/pdf', b'%PDF'),
    'cv/arthur-cei-correa-cv-es.pdf': ('application/pdf', b'%PDF'),
    'cv/arthur-cei-correa-cv-it.pdf': ('application/pdf', b'%PDF'),
    'assets/site.css': ('text/css', b'@layer'),
    'assets/404.css': ('text/css', b'@layer'),
    'assets/language.js': ('javascript', b'//'),
    'assets/page.js': ('javascript', b'//'),
    'fonts/cinzel-400.woff2': ('font/woff2', b'wOF2'),
    'fonts/eb-garamond-400.woff2': ('font/woff2', b'wOF2'),
    'og.png': ('image/png', b'\x89PNG'),
    'og-pt.png': ('image/png', b'\x89PNG'),
    'apple-touch-icon.png': ('image/png', b'\x89PNG'),
    'arthur-cei-correa.vcf': ('vcard', b'BEGIN:VCARD'),
}
for path, (kind_expected, magic) in FILES.items():
    status, kind, body = fetch(path)
    found = magic in body[:2000] if kind_expected.startswith(('text', 'xml')) else body.startswith(magic)
    check(status == 200 and kind_expected in kind and found, 'arquivo disponível: /%s' % path, '%s %s' % (status, kind))

# ---------- http -> https ----------
try:
    connection = http.client.HTTPConnection(HOST, 80, timeout=20)
    connection.request('GET', '/', headers={'User-Agent': AGENT})
    response = connection.getresponse()
    location = response.getheader('Location', '')
    check(response.status in (301, 308) and location.startswith('https://'), 'http redireciona para https',
          '%s %s' % (response.status, location))
except OSError as error:
    check(False, 'http redireciona para https', error)

# ---------- certificado ----------
try:
    context = ssl.create_default_context()
    with socket.create_connection((HOST, 443), timeout=20) as raw:
        with context.wrap_socket(raw, server_hostname=HOST) as tls:
            expires = datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(tls.getpeercert()['notAfter']), datetime.timezone.utc)
    days = (expires - datetime.datetime.now(datetime.timezone.utc)).days
    check(days >= 14, 'certificado HTTPS válido por mais %d dias' % days, 'vence em %s' % expires.date())
except (OSError, ssl.SSLError, KeyError, ValueError) as error:
    check(False, 'certificado HTTPS válido', error)

# ---------- resumo ----------
failed = [r for r in results if not r[0]]
summary = ['### Verificação do site no ar', '', '%s: %d verificações, %d falha(s).' % (BASE, len(results), len(failed))]
if failed:
    summary += ['', '| Falhou | Detalhe |', '|---|---|'] + ['| %s | %s |' % (label, detail.replace('|', '/')) for _, label, detail in failed]
target = os.environ.get('GITHUB_STEP_SUMMARY')
if target:
    open(target, 'a', encoding='utf-8').write('\n'.join(summary) + '\n')
print('\n' + ('Site no ar: tudo certo.' if not failed else 'Site no ar: %d falha(s).' % len(failed)))
sys.exit(1 if failed else 0)
