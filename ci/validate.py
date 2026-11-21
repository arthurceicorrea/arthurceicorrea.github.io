"""Validação estática do site montado por ci/build.py, executada pelo pipeline antes de publicar.

Confere em todas as páginas (inicial, 404 e uma por idioma): hashes da CSP,
aninhamento do HTML, ids únicos, ausência de estilos e manipuladores embutidos,
links externos seguros, nenhum recurso de terceiros, caminhos locais absolutos
e existentes, e dados estruturados. Na página inicial, a paridade das quatro
edições; nas páginas por idioma, uma só edição, idioma fixo, endereço canônico e
prévia de compartilhamento no idioma certo. Por fim, robots.txt, sitemap.xml e a
ausência de telefone nas páginas e nos currículos.

Uso: python ci/build.py && python ci/validate.py _site
"""
import json
import base64
import hashlib
import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, '_site')
if not os.path.isfile(os.path.join(ROOT, 'index.html')):
    sys.exit('Site montado não encontrado em %s. Rode antes: python ci/build.py' % ROOT)
CODES = {'pt': 'pt-BR', 'en': 'en', 'es': 'es', 'it': 'it'}
LANGS = ('pt-BR', 'en', 'es', 'it')
ALLOWED_EXTERNAL = (
    'https://arthurceicorrea.github.io/',
    'https://github.com/arthurceicorrea',
    'https://www.linkedin.com/in/arthurceicorrea/',
    'https://www.linkedin.com/pulse/from-purism-prudence-teleological-error-resistance-arthur-cei-corr%C3%AAa-awqef/',
)
# telefone brasileiro: +55, (11) 9xxxx-xxxx ou 9xxxx-xxxx
PHONE = re.compile(r'\+\s?55\b|\(\d{2}\)\s?9\d{4}-?\d{4}|\b9\d{4}-\d{4}\b')
VOID = {'meta', 'link', 'br', 'wbr', 'img', 'input', 'hr', 'source', 'area', 'base', 'col', 'embed', 'track', 'param'}

failures = []


def check(ok, label, detail=''):
    print(('ok    ' if ok else 'FALHA ') + label + (' :: %s' % (detail,) if detail and not ok else ''))
    if not ok:
        failures.append(label)


def sha256(text):
    return 'sha256-' + base64.b64encode(hashlib.sha256(text.encode('utf-8')).digest()).decode()


def local_file(url):
    """Caminho no repositório de um endereço local, relativo ou absoluto ("/" é o index.html)."""
    path = url.split('?')[0].split('#')[0].lstrip('/')
    if path == '' or path.endswith('/'):
        path += 'index.html'
    return os.path.join(ROOT, path)


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.tags = [], [], [], []
        self.edition = None  # idioma da edição em que estamos
        self.counts = {lang: {} for lang in LANGS}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        self.tags.append((tag, a, line))
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'div' and a.get('class') == 't' and a.get('lang') in LANGS and self.stack and self.stack[-1][0] == 'main':
            self.edition = (a['lang'], len(self.stack))
        # a nota sobre o nível de italiano existe só na edição italiana, de propósito
        if self.edition and a.get('class') != 'note':
            c = self.counts[self.edition[0]]
            key = tag + ('.' + a['class'] if 'class' in a else '')
            c[key] = c.get(key, 0) + 1
        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append('</%s> inesperado na linha %d' % (tag, self.getpos()[0]))
            return
        self.stack.pop()
        if self.edition and len(self.stack) == self.edition[1]:
            self.edition = None


def check_page(name, edition=None):
    """Verificações comuns a todas as páginas. edition=None exige as quatro edições;
    edition='pt-BR' (etc.) exige só aquela. Devolve (texto bruto, corpo sem comentários, analisador)."""
    where = ' [%s]' % name
    raw = open(os.path.join(ROOT, name), encoding='utf-8').read()
    check('\r' not in raw, 'quebras de linha LF (os hashes da CSP dependem disso)' + where)
    code = re.sub(r'<!--.*?-->', '', raw, flags=re.S)

    # ---------- CSP ----------
    blocks = {tag: re.findall(r'^<%s>(.*?)</%s>$' % (tag, tag), raw, flags=re.S | re.M) for tag in ('style', 'script')}
    one_each = len(blocks['style']) == 1 and len(blocks['script']) == 1
    check(one_each, 'um único bloco de estilo e um único bloco de script' + where)
    meta = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', raw)
    check(bool(meta), 'meta CSP presente' + where)
    if meta and one_each:
        csp = meta.group(1)
        want_style, want_script = sha256(blocks['style'][0]), sha256(blocks['script'][0])
        check("style-src '%s'" % want_style in csp, 'hash do estilo confere com a CSP' + where, want_style)
        check("script-src '%s'" % want_script in csp, 'hash do script confere com a CSP' + where, want_script)
        check("default-src 'none'" in csp and 'unsafe-inline' not in csp and 'unsafe-eval' not in csp,
              "CSP restritiva (default-src 'none', sem unsafe-inline nem unsafe-eval)" + where)

    # ---------- estrutura ----------
    p = Parser()
    p.feed(raw)
    check(not p.errors and not p.stack, 'etiquetas HTML bem aninhadas' + where, p.errors[:3] or p.stack[:3])
    dups = sorted({i for i in p.ids if p.ids.count(i) > 1})
    check(not dups, 'ids únicos' + where, dups)
    if edition is None:
        shapes = [p.counts[lang] for lang in LANGS]
        check(all(shapes) and all(s == shapes[0] for s in shapes), 'as quatro edições têm a mesma estrutura' + where,
              {lang: sum(p.counts[lang].values()) for lang in LANGS})
    else:
        others = sorted({a.get('lang') for tag, a, line in p.tags if a.get('class') == 't' and a.get('lang') != edition})
        check(p.counts[edition] and not others, 'só a edição %s presente' % edition + where, others)

    # páginas servidas em vários níveis de pasta: tudo o que é local tem de ser absoluto
    relative = [a.get(attr) for tag, a, line in p.tags for attr in ('href', 'src')
                if a.get(attr) and not a.get(attr).startswith(('/', '#', 'data:', 'http://', 'https://', 'mailto:'))]
    relative += [u for u in re.findall(r'url\("([^"]+)"\)', raw) if not u.startswith('/')]
    check(not relative, 'só caminhos locais absolutos' + where, relative)

    body = code.split('<body>', 1)[1] if '<body>' in code else ''
    check(not re.search(r'\sstyle\s*=', code), 'nenhum atributo style embutido' + where)
    check(not re.search(r'\son[a-z]+\s*=', body), 'nenhum manipulador de evento embutido' + where)

    # ---------- links e recursos ----------
    for tag, a, line in p.tags:
        for attr in ('href', 'src'):
            url = a.get(attr)
            if not url:
                continue
            if url.startswith(('http://', 'https://')):
                check(url.startswith(ALLOWED_EXTERNAL), 'endereço externo permitido (linha %d)' % line + where, url)
                if tag in ('script', 'img', 'iframe', 'source', 'video', 'audio', 'embed', 'object') or \
                   (tag == 'link' and a.get('rel') not in ('canonical', 'alternate')):
                    check(False, 'nenhum recurso carregado de terceiros (linha %d)' % line + where, url)
                if tag == 'a':
                    check(a.get('target') == '_blank' and a.get('rel') == 'noopener noreferrer',
                          'link externo com target e rel seguros (linha %d)' % line + where, url)
            elif not url.startswith(('mailto:', '#', '?', 'data:')):
                check(os.path.isfile(local_file(url)), 'arquivo local existe: %s' % url + where)

    for url in re.findall(r'url\("([^"]+)"\)', blocks['style'][0] if blocks['style'] else ''):
        check(os.path.isfile(local_file(url)), 'fonte local existe: %s' % url + where)

    text_only = re.sub(r'<[^>]+>', ' ', body)
    check(not PHONE.search(text_only), 'nenhum telefone no texto da página' + where, PHONE.search(text_only))
    return raw, body, p


# ---------- página inicial ----------
raw, body, parsed = check_page('index.html')
check('#conteudo' not in body or ' id="conteudo"' in body, 'âncora do link de pular existe')
for code in CODES:
    check(('href="/cv/arthur-cei-correa-cv-%s.pdf"' % code) in body, 'botão do currículo %s presente' % code)
    check(('<a href="/%s/" data-lang="%s"' % (code, code)) in body, 'seletor leva à página %s' % code)
canonical = re.search(r'<link rel="canonical" href="([^"]+)">', raw)
check(bool(canonical), 'endereço canônico declarado')
base = canonical.group(1) if canonical else ''
alternates_root = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', raw))
expected = {tag: base + code + '/' for code, tag in CODES.items()}
expected['x-default'] = base
check(alternates_root == expected, 'versões por idioma apontam para /pt/, /en/, /es/, /it/', alternates_root)


def structured_data(raw_page, where):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', raw_page, flags=re.S)
    check(len(blocks) == 1, 'um bloco de dados estruturados' + where)
    if not blocks:
        return None
    try:
        data = json.loads(blocks[0])
    except ValueError as error:
        check(False, 'dados estruturados em JSON válido' + where, error)
        return None
    nodes = data.get('@graph', [data])
    people = [n for n in nodes if n.get('@type') == 'Person']
    data = people[0] if people else {}
    check(len(people) == 1 and data.get('name') and data.get('url') == base,
          'dados estruturados descrevem a pessoa e o site' + where, [n.get('@type') for n in nodes])
    check(all(u.startswith(ALLOWED_EXTERNAL) for u in data.get('sameAs', [])), 'perfis listados são permitidos' + where)
    works = [n for n in nodes if n.get('@type') == 'Article']
    check(all(w.get('url', '').startswith(ALLOWED_EXTERNAL) and w.get('author', {}).get('@id') == data.get('@id') for w in works),
          'artigos listados são do autor e têm endereço permitido' + where, [w.get('url') for w in works])
    return data


person = structured_data(raw, ' [index.html]')


def meta(raw_page, prop):
    found = re.search(r'<meta (?:property|name)="%s" content="([^"]*)">' % re.escape(prop), raw_page)
    return found.group(1) if found else None


def image_exists(url):
    return url and url.startswith(base) and os.path.isfile(os.path.join(ROOT, url[len(base):]))


check(image_exists(meta(raw, 'og:image')), 'imagem de compartilhamento existe [index.html]', meta(raw, 'og:image'))

# ---------- páginas por idioma ----------
LOCALES = {'pt': 'pt_BR', 'en': 'en_US', 'es': 'es_ES', 'it': 'it_IT'}
for code, tag in CODES.items():
    name = '%s/index.html' % code
    where = ' [%s]' % name
    if not os.path.isfile(os.path.join(ROOT, name)):
        check(False, 'página gerada existe' + where)
        continue
    page_raw, page_body, page_parsed = check_page(name, edition=tag)
    edition = re.search(r'<div class="t" lang="%s"\s+data-title="([^"]+)"\s+data-desc="([^"]+)">' % re.escape(tag), page_raw)
    title, desc = (edition.group(1), edition.group(2)) if edition else (None, None)
    check(('<html lang="%s" data-lang="%s">' % (tag, code)) in page_raw, 'idioma fixo no elemento html' + where)
    check(re.search(r'<title>([^<]*)</title>', page_raw).group(1) == title, 'título no idioma da página' + where)
    check(meta(page_raw, 'description') == desc and meta(page_raw, 'og:description') == desc and meta(page_raw, 'og:title') == title,
          'descrição e prévia no idioma da página' + where)
    check(meta(page_raw, 'og:locale') == LOCALES[code], 'og:locale certo' + where, meta(page_raw, 'og:locale'))
    url = base + code + '/'
    page_canonical = re.search(r'<link rel="canonical" href="([^"]+)">', page_raw)
    check(page_canonical and page_canonical.group(1) == url and meta(page_raw, 'og:url') == url,
          'endereço canônico é a própria página' + where)
    check(dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', page_raw)) == expected,
          'mesmas versões por idioma da página inicial' + where)
    check(image_exists(meta(page_raw, 'og:image')) and meta(page_raw, 'twitter:image') == meta(page_raw, 'og:image'),
          'imagem de compartilhamento existe' + where, meta(page_raw, 'og:image'))
    check(('<a href="/%s/" data-lang="%s" lang="%s" hreflang="%s" aria-current="true">' % (code, code, tag, tag)) in page_raw
          and page_raw.count('aria-current="true"') == 1, 'seletor marca o idioma da página' + where)
    check(('href="/cv/arthur-cei-correa-cv-%s.pdf"' % code) in page_body, 'botão do currículo da página' + where)
    check(structured_data(page_raw, where) == person, 'mesmos dados estruturados da página inicial' + where)

# ---------- rodapé e versão ----------
import datetime
stamps = {}
for name in ['index.html'] + ['%s/index.html' % c for c in CODES]:
    text = open(os.path.join(ROOT, name), encoding='utf-8').read()
    text = text[text.find('<footer'):]  # só a data do rodapé; outras datas (o artigo) ficam de fora
    stamps[name] = (re.findall(r'<time datetime="([^"]+)">', text), re.findall(r'<span class="year">(\d{4})</span>', text))
dates = {d for found, _ in stamps.values() for d in found}
years = {y for _, found in stamps.values() for y in found}
check(len(dates) == 1 and len(stamps['index.html'][0]) == 4, 'mesma data de atualização em todas as páginas', dates)
if len(dates) == 1:
    day = datetime.date.fromisoformat(dates.pop())
    check(day <= datetime.date.today() + datetime.timedelta(days=1), 'data de atualização não está no futuro', day)
    check(years == {str(day.year)}, 'ano do rodapé é o da atualização', years)
version = open(os.path.join(ROOT, 'version.txt'), encoding='utf-8').read().strip() if os.path.isfile(os.path.join(ROOT, 'version.txt')) else ''
check(re.fullmatch(r'[0-9a-f]{40}|local', version) is not None, 'version.txt com o commit publicado', version)

# ---------- página de erro ----------
raw404, body404, parsed404 = check_page('404.html')
check('<meta name="robots" content="noindex">' in raw404, 'a página 404 não é indexada')

# ---------- robots.txt e sitemap.xml ----------
robots = open(os.path.join(ROOT, 'robots.txt'), encoding='utf-8').read()
check('Sitemap: %ssitemap.xml' % base in robots, 'robots.txt aponta para o sitemap do endereço canônico')
try:
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'x': 'http://www.w3.org/1999/xhtml'}
    urls = ET.parse(os.path.join(ROOT, 'sitemap.xml')).findall('s:url', ns)
    locs = [u.find('s:loc', ns).text for u in urls]
    check(locs == [base] + [base + code + '/' for code in CODES], 'sitemap.xml lista a página inicial e as quatro páginas', locs)
    for u in urls:
        alternates = {e.get('hreflang'): e.get('href') for e in u.findall('x:link', ns)}
        check(alternates == expected, 'sitemap.xml declara as versões por idioma de %s' % u.find('s:loc', ns).text, alternates)
except ET.ParseError as error:
    check(False, 'sitemap.xml é XML bem formado', error)

# ---------- currículos ----------
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
check(PdfReader is not None, 'pypdf disponível para ler os currículos')
if PdfReader:
    for name in sorted(os.listdir(os.path.join(ROOT, 'cv'))):
        if name.endswith('.pdf'):
            reader = PdfReader(os.path.join(ROOT, 'cv', name))
            content = ''.join(page.extract_text() or '' for page in reader.pages)
            check(len(content) > 500, 'currículo legível: %s' % name)
            check(not PHONE.search(content), 'nenhum telefone em %s' % name, PHONE.search(content))
            if not name.endswith('-en.pdf'):
                check('Page 1 of' not in content, 'rodapé no idioma do currículo: %s' % name)

print('\n%s' % ('Validação estática: tudo certo.' if not failures else 'Validação estática: %d falha(s).' % len(failures)))
sys.exit(1 if failures else 0)
