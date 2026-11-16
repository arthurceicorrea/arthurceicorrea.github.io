"""Validação estática do portfólio, executada pelo pipeline antes de publicar.

Confere: hashes da CSP, aninhamento do HTML, ids únicos, ausência de estilos e
manipuladores embutidos, links externos seguros, nenhum recurso de terceiros,
arquivos locais referenciados, paridade das quatro edições e ausência de
número de telefone na página e nos currículos.

Uso: python ci/validate.py   (a partir da raiz do repositório)
"""
import base64
import hashlib
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')
LANGS = ('pt-BR', 'en', 'es', 'it')
ALLOWED_EXTERNAL = (
    'https://arthurceicorrea.github.io/',
    'https://github.com/arthurceicorrea',
    'https://www.linkedin.com/in/arthurceicorrea/',
)
# telefone brasileiro: +55, (11) 9xxxx-xxxx ou 9xxxx-xxxx
PHONE = re.compile(r'\+\s?55\b|\(\d{2}\)\s?9\d{4}-?\d{4}|\b9\d{4}-\d{4}\b')
VOID = {'meta', 'link', 'br', 'wbr', 'img', 'input', 'hr', 'source', 'area', 'base', 'col', 'embed', 'track', 'param'}

failures = []


def check(ok, label, detail=''):
    print(('ok    ' if ok else 'FALHA ') + label + (' :: %s' % detail if detail and not ok else ''))
    if not ok:
        failures.append(label)


raw = open(PAGE, encoding='utf-8').read()
check('\r' not in raw, 'quebras de linha LF (os hashes da CSP dependem disso)')
code = re.sub(r'<!--.*?-->', '', raw, flags=re.S)


# ---------- CSP ----------
def sha256(text):
    return 'sha256-' + base64.b64encode(hashlib.sha256(text.encode('utf-8')).digest()).decode()


blocks = {tag: re.findall(r'^<%s>(.*?)</%s>$' % (tag, tag), raw, flags=re.S | re.M) for tag in ('style', 'script')}
check(len(blocks['style']) == 1 and len(blocks['script']) == 1, 'um único bloco de estilo e um único bloco de script')
meta = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', raw)
check(bool(meta), 'meta CSP presente')
if meta and len(blocks['style']) == 1 and len(blocks['script']) == 1:
    csp = meta.group(1)
    want_style, want_script = sha256(blocks['style'][0]), sha256(blocks['script'][0])
    check("style-src '%s'" % want_style in csp, 'hash do estilo confere com a CSP', want_style)
    check("script-src '%s'" % want_script in csp, 'hash do script confere com a CSP', want_script)
    check("default-src 'none'" in csp and 'unsafe-inline' not in csp and 'unsafe-eval' not in csp,
          "CSP restritiva (default-src 'none', sem unsafe-inline nem unsafe-eval)")


# ---------- estrutura ----------
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


p = Parser()
p.feed(raw)
check(not p.errors and not p.stack, 'etiquetas HTML bem aninhadas', p.errors[:3] or p.stack[:3])
dups = sorted({i for i in p.ids if p.ids.count(i) > 1})
check(not dups, 'ids únicos', dups)

shapes = [p.counts[lang] for lang in LANGS]
check(all(shapes) and all(s == shapes[0] for s in shapes), 'as quatro edições têm a mesma estrutura',
      {lang: sum(p.counts[lang].values()) for lang in LANGS})

body = code.split('<body>', 1)[1] if '<body>' in code else ''
check(not re.search(r'\sstyle\s*=', code), 'nenhum atributo style embutido')
check(not re.search(r'\son[a-z]+\s*=', body), 'nenhum manipulador de evento embutido')
check('#conteudo' not in body or ' id="conteudo"' in body, 'âncora do link de pular existe')

# ---------- links e recursos ----------
for tag, a, line in p.tags:
    for attr in ('href', 'src'):
        url = a.get(attr)
        if not url:
            continue
        if url.startswith(('http://', 'https://')):
            check(url.startswith(ALLOWED_EXTERNAL), 'endereço externo permitido (linha %d)' % line, url)
            if tag in ('script', 'img', 'iframe', 'source', 'video', 'audio', 'embed', 'object') or \
               (tag == 'link' and a.get('rel') not in ('canonical', 'alternate')):
                check(False, 'nenhum recurso carregado de terceiros (linha %d)' % line, url)
            if tag == 'a':
                check(a.get('target') == '_blank' and a.get('rel') == 'noopener noreferrer',
                      'link externo com target e rel seguros (linha %d)' % line, url)
        elif not url.startswith(('mailto:', '#', '?', 'data:')):
            check(os.path.isfile(os.path.join(ROOT, url.split('?')[0].split('#')[0])),
                  'arquivo local existe: %s' % url)

for url in re.findall(r'url\("([^"]+)"\)', blocks['style'][0] if blocks['style'] else ''):
    check(os.path.isfile(os.path.join(ROOT, url)), 'fonte local existe: %s' % url)

for lang in ('pt', 'en', 'es', 'it'):
    check(('href="cv/arthur-cei-correa-cv-%s.pdf"' % lang) in body, 'botão do currículo %s presente' % lang)

# ---------- privacidade ----------
text_only = re.sub(r'<[^>]+>', ' ', body)
check(not PHONE.search(text_only), 'nenhum telefone no texto da página', PHONE.search(text_only))

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

print('\n%s' % ('Validação estática: tudo certo.' if not failures else 'Validação estática: %d falha(s).' % len(failures)))
sys.exit(1 if failures else 0)
