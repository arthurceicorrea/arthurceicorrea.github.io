"""Funções que os testes usam para ler o site montado por ci/build.py.

ROOT é a pasta do site; tests/conftest.py a define a partir da opção --site (padrão: _site).
As páginas são lidas e analisadas uma vez só e guardadas (lru_cache).
"""
import functools
import json
import os
import re
from html.parser import HTMLParser

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, '_site')  # trocada por tests/conftest.py conforme --site

CODES = {'pt': 'pt-BR', 'en': 'en', 'es': 'es', 'it': 'it'}
LANGS = tuple(CODES.values())
LOCALES = {'pt': 'pt_BR', 'en': 'en_US', 'es': 'es_ES', 'it': 'it_IT'}
# Página de agradecimento: o mesmo endereço nos quatro idiomas (/pt/gratiarum-actio/...).
GRATIARUM = 'gratiarum-actio/'
LANGUAGE_PAGES = {'%s/index.html' % code: (code, tag) for code, tag in CODES.items()}
GRATIARUM_PAGES = {'%s/%sindex.html' % (code, GRATIARUM): (code, tag) for code, tag in CODES.items()}
# Páginas do site e a edição que cada uma deve ter: a 404 traz as quatro (None).
PAGES = {'index.html': 'en', **{name: tag for name, (code, tag) in LANGUAGE_PAGES.items()},
         **{name: tag for name, (code, tag) in GRATIARUM_PAGES.items()}, '404.html': None}
ALLOWED_EXTERNAL = (
    'https://arthurceicorrea.dev/',
    'https://github.com/arthurceicorrea',
    'https://www.linkedin.com/in/arthurceicorrea/',
    'https://github.com/CodeSquad-FIAP/Frio-Solidario-Global-Solution',
    'https://www.linkedin.com/pulse/from-purism-prudence-teleological-error-resistance-arthur-cei-corr%C3%AAa-awqef/',
)
# telefone brasileiro: +55, (11) 9xxxx-xxxx ou 9xxxx-xxxx
PHONE = re.compile(r'\+\s?55\b|\(\d{2}\)\s?9\d{4}-?\d{4}|\b9\d{4}-\d{4}\b')
# Política de segurança de todas as páginas: estilos e scripts só de arquivos do próprio site.
# Escrita aqui de novo, e não importada do build, para que o teste não concorde com o build por construção.
POLICY = ("default-src 'none'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self' data:; "
          "connect-src 'self'; base-uri 'none'; form-action 'none'")
VOID = {'meta', 'link', 'br', 'wbr', 'img', 'input', 'hr', 'source', 'area', 'base', 'col', 'embed', 'track', 'param'}
RESOURCE_TAGS = ('script', 'img', 'iframe', 'source', 'video', 'audio', 'embed', 'object')


def require_site():
    """Encerra a execução com uma mensagem clara se o site ainda não foi montado."""
    if not os.path.isfile(os.path.join(ROOT, 'index.html')):
        pytest.exit('Site montado não encontrado em %s. Rode antes: make build (ou python ci/build.py)' % ROOT, returncode=2)


def path(*parts):
    return os.path.join(ROOT, *parts)


def read(*parts):
    with open(path(*parts), encoding='utf-8') as f:
        return f.read()


def local_file(url):
    """Caminho no site de um endereço local, relativo ou absoluto ("/" é o index.html)."""
    name = url.split('?')[0].split('#')[0].lstrip('/')
    if name == '' or name.endswith('/'):
        name += 'index.html'
    return path(name)


class Parser(HTMLParser):
    """Guarda as etiquetas (com atributos e linha), os ids, os erros de aninhamento e, para cada
    edição de idioma, quantas etiquetas de cada tipo ela tem (para comparar as edições)."""

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


class Page:
    """Uma página do site: texto bruto, código sem comentários, corpo, etiquetas e folhas de estilo."""

    def __init__(self, name):
        self.name = name
        self.raw = read(name)
        self.code = re.sub(r'<!--.*?-->', '', self.raw, flags=re.S)
        self.body = self.code.split('<body>', 1)[1] if '<body>' in self.code else ''
        self.parsed = Parser()
        self.parsed.feed(self.raw)
        self.tags = self.parsed.tags
        self.stylesheets = [a.get('href') for tag, a, line in self.tags if tag == 'link' and a.get('rel') == 'stylesheet']
        self.styles = ''.join(open(local_file(h), encoding='utf-8').read() for h in self.stylesheets if os.path.isfile(local_file(h)))

    def meta(self, prop):
        found = re.search(r'<meta (?:property|name)="%s" content="([^"]*)">' % re.escape(prop), self.raw)
        return found.group(1) if found else None

    @property
    def csp(self):
        found = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', self.raw)
        return found.group(1) if found else None

    @property
    def canonical(self):
        found = re.search(r'<link rel="canonical" href="([^"]+)">', self.raw)
        return found.group(1) if found else None

    @property
    def alternates(self):
        return dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', self.raw))

    def json_ld_blocks(self):
        return re.findall(r'<script type="application/ld\+json">(.*?)</script>', self.raw, flags=re.S)

    def structured_data(self):
        """Nós do bloco de dados estruturados (JSON-LD); None se não houver um bloco válido."""
        blocks = self.json_ld_blocks()
        if len(blocks) != 1:
            return None
        try:
            data = json.loads(blocks[0])
        except ValueError:
            return None
        return data.get('@graph', [data])

    def person(self):
        nodes = self.structured_data() or []
        people = [n for n in nodes if n.get('@type') == 'Person']
        return people[0] if people else {}

    def links(self):
        """Cada endereço citado em href ou src: (etiqueta, atributos, linha, endereço)."""
        return [(tag, a, line, a.get(attr)) for tag, a, line in self.tags for attr in ('href', 'src') if a.get(attr)]


@functools.lru_cache(maxsize=None)
def page(name):
    return Page(name)


def base():
    """Endereço canônico do site, declarado na página inicial."""
    return page('index.html').canonical or ''


def expected_alternates(path=''):
    """Versões por idioma que cada página e o sitemap devem declarar. path vazio: o portfólio, cuja
    versão padrão (x-default) é a página inicial; GRATIARUM: o agradecimento, cuja padrão é a edição
    em inglês."""
    found = {tag: base() + code + '/' + path for code, tag in CODES.items()}
    found['x-default'] = base() + ('en/' + path if path else '')
    return found


def cv_files():
    folder = path('cv')
    return sorted(n for n in os.listdir(folder) if n.endswith('.pdf')) if os.path.isdir(folder) else []
