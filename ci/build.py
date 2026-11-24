"""Monta a pasta publicada (_site) a partir do repositório.

- Lê os textos de src/content/<idioma>.toml e para, com uma mensagem, se faltar um
  texto: cada chave de pt.toml precisa existir nos outros três idiomas.
- Monta cada página a partir do modelo src/page.html (Jinja2):
  - /pt/, /en/, /es/, /it/: só a edição daquele idioma, com o idioma fixo, e título,
    descrição, endereço canônico e prévia de compartilhamento (Open Graph) no idioma;
  - a página inicial: as quatro edições, e o script de idioma mostra a do visitante.
- Monta a 404 a partir de src/404.html, também com as quatro edições.
- Copia, como estão, os arquivos de static/: fontes, currículos, imagens, vCard e
  arquivos de indexação.
- Monta /assets/: junta os arquivos de src/css/ em site.css (e em 404.css, para a
  página de erro), na ordem das camadas (@layer), e copia os scripts de src/js/.
- Gera sitemap.xml: a página inicial e as quatro páginas de idioma, cada uma com as
  versões nos outros idiomas (hreflang).
- Preenche no rodapé a data da última atualização (a do último commit) e o ano,
  e grava version.txt com o commit publicado, que o monitoramento confere no ar.

Uso: python ci/build.py   (a partir da raiz do repositório; cria ou recria _site/)
"""
import datetime
import os
import shutil
import subprocess
import sys
import tomllib
import types

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site')
SRC = os.path.join(ROOT, 'src')
BASE = 'https://arthurceicorrea.github.io/'
# Idiomas, na ordem do seletor: código no endereço, etiqueta de idioma, região do Open Graph,
# imagem de prévia e nome do idioma nele mesmo.
TAGS = {'pt': 'pt-BR', 'en': 'en', 'es': 'es', 'it': 'it'}
LOCALES = {'pt': 'pt_BR', 'en': 'en_US', 'es': 'es_ES', 'it': 'it_IT'}
IMAGES = {'pt': 'og-pt.png', 'en': 'og.png', 'es': 'og-es.png', 'it': 'og-it.png'}
NAMES = {'pt': 'Português', 'en': 'English', 'es': 'Español', 'it': 'Italiano'}
DEFAULT = 'en'  # idioma da página inicial sem JavaScript e da 404
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


def render(env, template, path, **context):
    text = env.get_template(template).render(**context)
    target = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def head(code, content, url, og_description=None, data_lang=None):
    meta = content[code]['meta']
    return types.SimpleNamespace(
        html_lang=TAGS[code], data_lang=data_lang, current=code,
        title=meta['title'], description=meta['description'], og_description=og_description or meta['description'],
        locale=LOCALES[code], locale_alternates=[LOCALES[other] for other in TAGS if other != code],
        url=url, image=IMAGES[code], image_alt=meta['image_alt'])


def pages(content, day):
    env = Environment(loader=FileSystemLoader(SRC), autoescape=True, undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    shared = {
        'base': BASE, 'policy': Markup(POLICY),  # constante do build: entra sem escape
        'email': EMAIL, 'linkedin': LINKEDIN, 'github': GITHUB,
        'article': namespace(ARTICLE), 'updated': day, 'time_tag': time_tag,
        'languages': [types.SimpleNamespace(code=c, tag=t, name=NAMES[c]) for c, t in TAGS.items()],
    }
    everyone = [edition(code, content) for code in TAGS]
    root_description = content[DEFAULT]['meta']['og_description_root']
    render(env, 'page.html', 'index.html', page=head(DEFAULT, content, BASE, og_description=root_description),
           editions=everyone, **shared)
    for code in TAGS:
        render(env, 'page.html', os.path.join(code, 'index.html'),
               page=head(code, content, BASE + code + '/', data_lang=code), editions=[edition(code, content)], **shared)
    render(env, '404.html', '404.html', editions=everyone, default=edition(DEFAULT, content), **shared)


def sitemap():
    """sitemap.xml: cada página publicada, com as versões por idioma e a padrão (x-default)."""
    links = ''.join('    <xhtml:link rel="alternate" hreflang="%s" href="%s%s/"/>\n' % (tag, BASE, code) for code, tag in TAGS.items())
    links += '    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>\n' % BASE
    urls = ''.join('  <url>\n    <loc>%s</loc>\n%s  </url>\n' % (loc, links) for loc in [BASE] + [BASE + code + '/' for code in TAGS])
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
                '%s</urlset>\n' % urls)


def assets():
    """Monta /assets/ a partir de src/: as folhas de estilo e os scripts."""
    folder = os.path.join(OUT, 'assets')
    os.makedirs(folder)
    for name, (layers, parts) in CSS.items():
        text = '/* Gerado por ci/build.py a partir de src/css/. Edite lá, não aqui. */\n@layer %s;\n' % layers
        for part in parts:
            text += '\n' + open(os.path.join(SRC, 'css', part), encoding='utf-8').read()
        with open(os.path.join(folder, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    scripts = os.path.join(SRC, 'js')
    for name in sorted(os.listdir(scripts)):
        if name.endswith('.js'):
            shutil.copy2(os.path.join(scripts, name), os.path.join(folder, name))


def main():
    content = load_content()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # arquivos estáticos (fontes, currículos, imagens, vCard, robots.txt...), copiados como estão
    shutil.copytree(os.path.join(ROOT, 'static'), OUT, dirs_exist_ok=True)
    assets()
    commit_date = git('log', '-1', '--format=%cs')
    day = datetime.date.fromisoformat(commit_date) if commit_date else datetime.date.today()
    version = os.environ.get('GITHUB_SHA') or git('rev-parse', 'HEAD') or 'local'
    with open(os.path.join(OUT, 'version.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(version + '\n')
    pages(content, day)
    sitemap()
    count = sum(len(files) for _, _, files in os.walk(OUT))
    print('Site montado em _site/: %d arquivos, com as páginas %s; versão %s, atualizado em %s.' % (
        count, ', '.join('/%s/' % c for c in TAGS), version[:7], day.isoformat()))


if __name__ == '__main__':
    sys.exit(main())
