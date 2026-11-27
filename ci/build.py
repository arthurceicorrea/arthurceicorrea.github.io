"""Monta a pasta publicada (_site) a partir do repositório.

- Lê os textos de src/content/<idioma>.toml e para, com uma mensagem, se faltar um
  texto: cada chave de pt.toml precisa existir nos outros três idiomas.
- Monta cada página a partir de um modelo (Jinja2) que estende src/layout.html, onde ficam
  o <head>, o seletor de idioma e o rodapé, comuns a todas. As páginas estão numa tabela única,
  PAGES: cada entrada diz o modelo e o endereço de cada idioma, e dela saem a montagem, o
  endereço canônico, as versões por idioma (hreflang) e o sitemap:
  - src/page.html, o portfólio: /pt/, /en/, /es/, /it/, só a edição daquele idioma, com o
    idioma fixo, e título, descrição, endereço canônico e prévia de compartilhamento (Open
    Graph) no idioma; e a página inicial, a edição em inglês, marcada com data-home: o script
    de idioma leva os outros visitantes à página do seu idioma;
  - src/gratiarum.html, o agradecimento: /pt/gratiarum-actio/ e as outras três, uma edição
    cada, com o idioma fixo, e endereços por idioma próprios (o padrão é a edição em inglês).
- Monta a 404 a partir de src/404.html, com as quatro edições: o script de idioma
  mostra a do visitante.
- Copia, como estão, os arquivos de static/: fontes, imagens, vCard e arquivos de
  indexação.
- Gera os quatro currículos em PDF (A4) a partir do modelo src/cv.html, com os mesmos
  textos da página: abre cada um no Chrome (Playwright) e o imprime em /cv/. O HTML
  do currículo não é publicado, só o PDF.
- Monta /assets/: junta os arquivos de src/css/ em site.css (e em 404.css, para a
  página de erro), na ordem das camadas (@layer), e copia os scripts de src/js/.
- Gera sitemap.xml a partir da mesma tabela: cada página, com as versões nos outros idiomas
  (hreflang) e a padrão (x-default).
- Preenche no rodapé a data da última atualização (a do último commit) e o ano,
  e grava version.txt com o commit publicado, que o monitoramento confere no ar.

Uso: python ci/build.py   (a partir da raiz do repositório; cria ou recria _site/)
"""
import datetime
import functools
import http.server
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import types

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site')
SRC = os.path.join(ROOT, 'src')
BASE = 'https://arthurceicorrea.dev/'
# Idiomas, na ordem do seletor: código no endereço, etiqueta de idioma, região do Open Graph,
# imagem de prévia e nome do idioma nele mesmo.
TAGS = {'pt': 'pt-BR', 'en': 'en', 'es': 'es', 'it': 'it'}
LOCALES = {'pt': 'pt_BR', 'en': 'en_US', 'es': 'es_ES', 'it': 'it_IT'}
IMAGES = {'pt': 'og-pt.png', 'en': 'og.png', 'es': 'og-es.png', 'it': 'og-it.png'}
GRATIARUM_IMAGE = 'og-gratiarum.png'  # prévia do agradecimento: a mesma nos quatro idiomas, porque é toda em latim
NAMES = {'pt': 'Português', 'en': 'English', 'es': 'Español', 'it': 'Italiano'}
DEFAULT = 'en'  # idioma da página inicial sem JavaScript e da 404
# Página de agradecimento: o mesmo endereço nos quatro idiomas, porque é latim (/pt/gratiarum-actio/...).
GRATIARUM = 'gratiarum-actio/'
# Dados que não mudam com o idioma.
EMAIL = 'arthurceicorrea@gmail.com'
LINKEDIN = 'https://www.linkedin.com/in/arthurceicorrea/'
GITHUB = 'https://github.com/arthurceicorrea'
ARTICLE = {
    'headline': 'From Purism to Prudence: Artificial Intelligence and the Right Order of Means',
    'url': 'https://www.linkedin.com/pulse/from-purism-prudence-teleological-error-resistance-arthur-cei-corr%C3%AAa-awqef/',
    'date': '2026-08-24',
    'lang': 'en',
}
# Política de segurança de todas as páginas: estilos e scripts só de arquivos do próprio site.
POLICY = ("default-src 'none'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self' data:; "
          "connect-src 'self'; base-uri 'none'; form-action 'none'")
# Folhas de estilo publicadas em /assets/: ordem das camadas e arquivos de src/css/, nesta ordem.
CSS = {
    'site.css': ('tokens, base, layout, components', ['tokens.css', 'base.css', 'layout.css', 'components.css']),
    '404.css': ('tokens, page', ['tokens.css', '404.css']),
}
# Estilo do currículo: só usado para imprimir o PDF, não é publicado.
CV_CSS = ('tokens, cv', ['tokens.css', 'cv.css'])


def git(*args):
    try:
        return subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def namespace(value):
    """Dicionários viram objetos simples: no modelo, e.ui.copy é o texto, e não o método copy."""
    if isinstance(value, dict):
        return types.SimpleNamespace(**{k: namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [namespace(v) for v in value]
    return value


def as_date(day):
    return datetime.date.fromisoformat(day) if isinstance(day, str) else day


def long_date(day, edition):
    """Data por extenso no formato do idioma, por exemplo 24 de agosto de 2026."""
    day = as_date(day)
    return edition.date.format.format(day=day.day, month=edition.date.months[day.month - 1], year=day.year)


def time_tag(day, edition):
    day = as_date(day)
    return Markup('<time datetime="%s">%s</time>') % (day.isoformat(), long_date(day, edition))


def missing(reference, other, path=''):
    """Chaves de reference (pt.toml) que faltam em other, também dentro dos itens das listas.
    Chaves a mais em other são permitidas (por exemplo, uma nota que só um idioma tem)."""
    if isinstance(reference, dict):
        if not isinstance(other, dict):
            return ['%s deveria ser uma tabela' % path]
        found = []
        for key, value in reference.items():
            where = path + '.' + key if path else key
            found += missing(value, other[key], where) if key in other else ['falta %s' % where]
        return found
    if isinstance(reference, list):
        if not isinstance(other, list) or len(other) != len(reference):
            return ['%s tem %d itens em pt.toml e %s aqui' % (path, len(reference), len(other) if isinstance(other, list) else 'nenhum')]
        return [problem for i, (a, b) in enumerate(zip(reference, other)) for problem in missing(a, b, '%s[%d]' % (path, i + 1))]
    return []


def load_content():
    content = {}
    for code in TAGS:
        with open(os.path.join(SRC, 'content', code + '.toml'), 'rb') as f:
            content[code] = tomllib.load(f)
    problems = ['src/content/%s.toml: %s' % (code, problem)
                for code in TAGS if code != 'pt' for problem in missing(content['pt'], content[code])]
    if problems:
        sys.exit('Faltam textos (cada chave de pt.toml precisa existir nos outros idiomas):\n  ' + '\n  '.join(problems))
    return content


def edition(code, content):
    return namespace(dict(content[code], code=code, tag=TAGS[code]))


def render(env, template, path, folder=OUT, **context):
    text = env.get_template(template).render(**context)
    target = os.path.join(folder, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def same_address(path):
    """Endereço igual nos quatro idiomas, depois de /<idioma>/: por exemplo, pt/gratiarum-actio/."""
    return {code: '%s/%s' % (code, path) for code in TAGS}


def page_table(content):
    """Tabela única das páginas com conteúdo. Cada entrada é uma página nos quatro idiomas, uma
    edição por idioma, e diz:
      template  o modelo, em src/, que estende layout.html;
      paths     o endereço de cada edição, depois do domínio (por exemplo, pt/gratiarum-actio/),
                igual nos quatro idiomas ou traduzido;
      text      a tabela do arquivo de idioma com a descrição (description) e, se a página não
                escreve o título no modelo, o título (title);
      image     a imagem de prévia, a mesma nos quatro idiomas; None: a de cada idioma (IMAGES);
      alt       a tabela do arquivo de idioma com o texto alternativo da imagem (image_alt);
      home      se a entrada tem também a página inicial, a edição em inglês publicada em /. A
                versão padrão (x-default) é então a página inicial; nas outras, a edição em inglês.
    Dela saem a montagem, o endereço canônico, as versões por idioma (hreflang) e o sitemap."""
    page = types.SimpleNamespace
    return {
        # o portfólio: a página inicial e /pt/, /en/, /es/, /it/
        'portfolio': page(template='page.html', paths=same_address(''), text='meta', image=None, alt='meta', home=True),
        # o agradecimento: o mesmo endereço nos quatro idiomas, porque é latim
        'gratiarum': page(template='gratiarum.html', paths=same_address(GRATIARUM), text='gratiarum',
                          image=GRATIARUM_IMAGE, alt='gratiarum', home=False),
    }


def x_default(entry):
    """Endereço da versão padrão de uma página, para quem não tem um dos quatro idiomas."""
    return BASE if entry.home else BASE + entry.paths[DEFAULT]


def head(entry, code, content, home=False, og_description=None):
    """Dados do <head> de uma edição de uma página da tabela. home: a página inicial, a edição em
    inglês publicada em /, sem idioma fixo, para o script de idioma levar os outros visitantes à
    página deles. Uma página que escreve o título no modelo (o agradecimento, em latim) não tem
    title na sua tabela de textos; ali, page não tem title."""
    text = content[code][entry.text]
    own = {'description': text['description'], 'image': entry.image or IMAGES[code],
           'image_alt': content[code][entry.alt]['image_alt']}
    if 'title' in text:
        own['title'] = text['title']
    return types.SimpleNamespace(
        html_lang=TAGS[code], data_lang=None if home else code, home=home, current=code,
        paths=entry.paths, x_default=x_default(entry),
        og_description=og_description or own['description'],
        locale=LOCALES[code], locale_alternates=[LOCALES[other] for other in TAGS if other != code],
        url=BASE if home else BASE + entry.paths[code], **own)


def environment():
    return Environment(loader=FileSystemLoader(SRC), autoescape=True, undefined=StrictUndefined,
                       trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)


def pages(content, day, table):
    env = environment()
    shared = {
        'base': BASE, 'policy': Markup(POLICY),  # constante do build: entra sem escape
        'email': EMAIL, 'linkedin': LINKEDIN, 'github': GITHUB,
        'article': namespace(ARTICLE), 'updated': day, 'time_tag': time_tag,
        'languages': [types.SimpleNamespace(code=c, tag=t, name=NAMES[c]) for c, t in TAGS.items()],
        'addresses': {name: entry.paths for name, entry in table.items()},  # para os links do rodapé
    }
    for name, entry in table.items():
        if entry.home:
            # página inicial: a edição em inglês; o script de idioma leva os outros visitantes à página deles
            render(env, entry.template, 'index.html',
                   page=head(entry, DEFAULT, content, home=True, og_description=content[DEFAULT]['meta']['og_description_root']),
                   editions=[edition(DEFAULT, content)], current_page=name, **shared)
        for code in TAGS:
            render(env, entry.template, entry.paths[code] + 'index.html', page=head(entry, code, content),
                   editions=[edition(code, content)], current_page=name, **shared)
    render(env, '404.html', '404.html', editions=[edition(code, content) for code in TAGS], default=edition(DEFAULT, content), **shared)


def sitemap(table):
    """sitemap.xml: cada página da tabela, com as versões por idioma e a padrão (x-default)."""
    urls = ''
    for entry in table.values():
        links = ''.join('    <xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>\n' % (TAGS[code], BASE, path)
                        for code, path in entry.paths.items())
        links += '    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>\n' % x_default(entry)
        locs = ([BASE] if entry.home else []) + [BASE + path for path in entry.paths.values()]
        urls += ''.join('  <url>\n    <loc>%s</loc>\n%s  </url>\n' % (loc, links) for loc in locs)
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
                '%s</urlset>\n' % urls)


def stylesheet(layers, parts):
    """Junta arquivos de src/css/ numa folha só, declarando antes a ordem das camadas."""
    text = '/* Gerado por ci/build.py a partir de src/css/. Edite lá, não aqui. */\n@layer %s;\n' % layers
    for part in parts:
        text += '\n' + open(os.path.join(SRC, 'css', part), encoding='utf-8').read()
    return text


def assets():
    """Monta /assets/ a partir de src/: as folhas de estilo e os scripts."""
    folder = os.path.join(OUT, 'assets')
    os.makedirs(folder)
    for name, (layers, parts) in CSS.items():
        with open(os.path.join(folder, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(stylesheet(layers, parts))
    scripts = os.path.join(SRC, 'js')
    for name in sorted(os.listdir(scripts)):
        if name.endswith('.js'):
            shutil.copy2(os.path.join(scripts, name), os.path.join(folder, name))


def css_string(text):
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


def page_label(text):
    """Rodapé do PDF em CSS: "Página {page} de {total}" vira "Página " counter(page) " de " counter(pages)."""
    counters = {'{page}': 'counter(page)', '{total}': 'counter(pages)'}
    parts = re.split(r'(\{page\}|\{total\})', text)
    return Markup(' '.join(counters.get(part) or css_string(part) for part in parts if part))


def adds_nothing(role, summary):
    """O papel no projeto já está dito no resumo (sem contar maiúsculas e o ponto final)."""
    return role.rstrip('.').lower() in summary.lower()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def cvs(content):
    """Gera /cv/arthur-cei-correa-cv-<idioma>.pdf: monta src/cv.html numa pasta temporária,
    com as fontes e o estilo, serve essa pasta num servidor local e a imprime no Chrome."""
    from playwright.sync_api import Error, sync_playwright
    env = environment()
    target = os.path.join(OUT, 'cv')
    os.makedirs(target, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        # fontes do site (Cinzel, no nome e nos títulos) e as só do currículo (src/fonts/)
        shutil.copytree(os.path.join(ROOT, 'static', 'fonts'), os.path.join(folder, 'fonts'))
        shutil.copytree(os.path.join(SRC, 'fonts'), os.path.join(folder, 'fonts'), dirs_exist_ok=True)
        with open(os.path.join(folder, 'cv.css'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(stylesheet(*CV_CSS))
        for code in TAGS:
            e = edition(code, content)
            render(env, 'cv.html', 'cv-%s.html' % code, folder=folder, e=e, email=EMAIL, linkedin=LINKEDIN,
                   github=GITHUB, site=BASE + code + '/', article=namespace(ARTICLE), long_date=long_date,
                   adds_nothing=adds_nothing, page_label=page_label(e.resume.page))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=folder))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        address = 'http://127.0.0.1:%d/' % server.server_address[1]
        try:
            with sync_playwright() as pw:
                chrome = os.environ.get('CHROME_PATH')
                try:
                    browser = pw.chromium.launch(executable_path=chrome) if chrome else pw.chromium.launch(channel='chrome')
                except Error as error:
                    sys.exit('Não foi possível abrir o Chrome para gerar os currículos (instale o Google Chrome '
                             'ou indique o caminho em CHROME_PATH):\n%s' % error)
                page = browser.new_page()
                for code in TAGS:
                    page.goto(address + 'cv-%s.html' % code)
                    page.evaluate('document.fonts.ready.then(() => true)')
                    page.pdf(path=os.path.join(target, 'arthur-cei-correa-cv-%s.pdf' % code), prefer_css_page_size=True,
                             print_background=True, tagged=True, outline=True)
                browser.close()
        finally:
            server.shutdown()


def main():
    content = load_content()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # arquivos estáticos (fontes, imagens, vCard, robots.txt...), copiados como estão
    shutil.copytree(os.path.join(ROOT, 'static'), OUT, dirs_exist_ok=True)
    assets()
    commit_date = git('log', '-1', '--format=%cs')
    day = datetime.date.fromisoformat(commit_date) if commit_date else datetime.date.today()
    version = os.environ.get('GITHUB_SHA') or git('rev-parse', 'HEAD') or 'local'
    with open(os.path.join(OUT, 'version.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(version + '\n')
    table = page_table(content)
    pages(content, day, table)
    cvs(content)
    sitemap(table)
    count = sum(len(files) for _, _, files in os.walk(OUT))
    print('Site montado em _site/: %d arquivos, com as páginas %s; versão %s, atualizado em %s.' % (
        count, ', '.join('/' + path for entry in table.values() for path in entry.paths.values()), version[:7], day.isoformat()))


if __name__ == '__main__':
    sys.exit(main())
