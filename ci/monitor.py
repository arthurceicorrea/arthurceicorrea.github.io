"""Verifica o site no ar: usado depois de cada publicação e, uma vez por semana, pelo monitoramento.

Confere:
- (com --expect-version) que o site no ar já serve o commit que acabou de ser publicado,
  tentando por até 10 minutos, enquanto a publicação se propaga;
- página inicial, páginas /pt/, /en/, /es/, /it/, páginas de agradecimento (/pt/gratiarum-actio/
  e as outras três), de privacidade (/pt/privacidade/, /en/privacy/, /es/privacidad/,
  /it/privacy/), as listas de artigos (/pt/artigos/, /en/articles/, /es/articulos/, /it/articoli/) e
  cada artigo publicado (tests/published.txt): resposta 200, HTML, idioma certo e política de
  segurança presente;
- página 404 personalizada para endereços inexistentes;
- robots.txt, sitemap.xml, o feed dos artigos (feed.xml), currículos em PDF, fontes, folhas de estilo e scripts de /assets/
  e imagens de prévia;
- redirecionamento de http para https;
- cabeçalhos de segurança postos pela Cloudflare (infra/rules.tf);
- redirecionamento do www e do endereço antigo (arthurceicorrea.github.io) para o domínio;
- nenhuma resposta do site traz Set-Cookie: a página de privacidade diz que o site não usa cookies, e
  a Cloudflare só os põe se alguém ligar a proteção contra robôs (Bot Fight Mode e afins) no painel,
  fora do Terraform (infra/settings.tf);
- certificado HTTPS válido por pelo menos 14 dias. Com o proxy, é o certificado da Cloudflare; se o do
  GitHub Pages, por trás dela, vencer, a Cloudflare responde com erro e as páginas acima falham.

Uso: python ci/monitor.py https://arthurceicorrea.dev/ [--expect-version SHA]
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
cookies = []  # (endereço, cabeçalho Set-Cookie) de toda resposta do site que trouxer um
responses = []  # endereço de cada resposta recebida, para dizer quantas foram conferidas


def note(url, headers):
    """Guarda o endereço da resposta e os Set-Cookie que ela trouxer."""
    responses.append(url)
    cookies.extend((url, value) for value in headers.get_all('Set-Cookie') or [])


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
                note(url, response.headers)
                return response.status, response.headers.get('Content-Type', ''), response.read()
        except urllib.error.HTTPError as error:
            note(url, error.headers)
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
PAGES = {'': None, 'pt/': 'pt-BR', 'en/': 'en', 'es/': 'es', 'it/': 'it',
         'pt/gratiarum-actio/': 'pt-BR', 'en/gratiarum-actio/': 'en', 'es/gratiarum-actio/': 'es', 'it/gratiarum-actio/': 'it',
         'pt/privacidade/': 'pt-BR', 'en/privacy/': 'en', 'es/privacidad/': 'es', 'it/privacy/': 'it',
         'pt/artigos/': 'pt-BR', 'en/articles/': 'en', 'es/articulos/': 'es', 'it/articoli/': 'it'}
# os artigos publicados, só em inglês: a mesma lista que os testes conferem no site montado
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests', 'published.txt'), encoding='utf-8') as f:
    PAGES.update({line.strip().lstrip('/'): 'en' for line in f if line.strip() and not line.startswith('#')})
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
    'feed.xml': ('xml', b'<feed'),
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
    'fonts/eb-garamond-600.woff2': ('font/woff2', b'wOF2'),
    'og.png': ('image/png', b'\x89PNG'),
    'og-pt.png': ('image/png', b'\x89PNG'),
    'og-gratiarum.png': ('image/png', b'\x89PNG'),
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
    note('http://%s/' % HOST, response.headers)
    location = response.getheader('Location', '')
    check(response.status in (301, 308) and location.startswith('https://'), 'http redireciona para https',
          '%s %s' % (response.status, location))
except OSError as error:
    check(False, 'http redireciona para https', error)


def raw(host, path):
    """Uma requisição HTTPS que não segue redirecionamentos: devolve (status, cabeçalhos)."""
    connection = http.client.HTTPSConnection(host, 443, timeout=20, context=ssl.create_default_context())
    try:
        connection.request('GET', path, headers={'User-Agent': AGENT})
        response = connection.getresponse()
        response.read()
        note('https://%s%s' % (host, path), response.headers)
        return response.status, response.headers
    finally:
        connection.close()


# ---------- cabeçalhos de segurança ----------
# Postos pela Cloudflare (infra/rules.tf), porque o GitHub Pages não deixa o site defini-los.
# Escritos aqui de novo, e não lidos do Terraform, para que a conferência não concorde por construção.
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "frame-ancestors 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': ('camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), hid=(), '
                           'midi=(), bluetooth=(), browsing-topics=()'),
}
for path in ('/', '/pt/'):
    try:
        status, headers = raw(HOST, path)
        for name, expected in SECURITY_HEADERS.items():
            check(headers.get(name) == expected, 'cabeçalho %s (%s)' % (name, path), headers.get(name))
    except (OSError, ssl.SSLError) as error:
        check(False, 'cabeçalhos de segurança (%s)' % path, error)

# ---------- redirecionamentos para o domínio ----------
OLD_HOST = 'arthurceicorrea.github.io'
REDIRECTS = [] if HOST == OLD_HOST else [
    ('www.' + HOST, '/en/?x=1', 'https://%s/en/?x=1' % HOST, 'www leva ao domínio, com caminho e parâmetros'),
    (OLD_HOST, '/pt/', urljoin(BASE, 'pt/'), 'endereço antigo leva ao domínio'),
]
for host, path, target, label in REDIRECTS:
    try:
        status, headers = raw(host, path)
        check(status in (301, 308) and headers.get('Location') == target, label,
              '%s %s' % (status, headers.get('Location')))
    except (OSError, ssl.SSLError) as error:
        check(False, label, error)

# ---------- nenhum cookie ----------
# Todas as respostas acima: páginas, 404, arquivos, cabeçalhos e redirecionamentos.
check(bool(responses) and not cookies, 'nenhuma resposta do site traz Set-Cookie (%d respostas conferidas)' % len(responses),
      '; '.join('%s: %s' % (url, value.split(';', 1)[0].split('=', 1)[0]) for url, value in cookies[:5]))

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
