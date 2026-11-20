"""Monta a pasta publicada (_site) a partir do repositório.

- Copia a página inicial (index.html, com as quatro edições e a escolha automática
  do idioma), a 404, as fontes, os currículos, as imagens e os arquivos de indexação.
- Preenche no rodapé a data da última atualização (a do último commit) e o ano,
  e grava version.txt com o commit publicado, que o monitoramento confere no ar.
- Gera uma página por idioma (/pt/, /en/, /es/, /it/): só a edição daquele idioma,
  idioma fixo, e título, descrição, endereço canônico e prévia de compartilhamento
  (Open Graph) no idioma da página. Os blocos de estilo e de script não mudam, de
  modo que os hashes da política de segurança continuam valendo.

Uso: python ci/build.py   (a partir da raiz do repositório; cria ou recria _site/)
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site')
BASE = 'https://arthurceicorrea.github.io/'
TAGS = {'pt': 'pt-BR', 'en': 'en', 'es': 'es', 'it': 'it'}
LOCALES = {'pt': 'pt_BR', 'en': 'en_US', 'es': 'es_ES', 'it': 'it_IT'}
IMAGES = {'pt': 'og-pt.png', 'en': 'og.png', 'es': 'og-es.png', 'it': 'og-it.png'}
IMAGE_ALT = {
    'pt': 'Sapientis est ordinare — Arthur Cei Corrêa: DevOps, IA aplicada, segurança',
    'en': 'Sapientis est ordinare — Arthur Cei Corrêa: DevOps, applied AI, security',
    'es': 'Sapientis est ordinare — Arthur Cei Corrêa: DevOps, IA aplicada, seguridad',
    'it': 'Sapientis est ordinare — Arthur Cei Corrêa: DevOps, IA applicata, sicurezza',
}
FILES = ['404.html', 'robots.txt', 'sitemap.xml', '.nojekyll', 'apple-touch-icon.png', 'favicon-32.png'] + sorted(IMAGES.values())
FOLDERS = ['fonts', 'cv']
VOID = {'meta', 'link', 'br', 'wbr', 'img', 'input', 'hr', 'source', 'area', 'base', 'col', 'embed', 'track', 'param'}


MONTHS = {
    'pt': ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'],
    'en': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    'es': ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'],
    'it': ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'],
}


def git(*args):
    try:
        return subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def long_date(day, code):
    month = MONTHS[code][day.month - 1]
    if code == 'en':
        return '%s %d, %d' % (month, day.day, day.year)
    if code == 'it':
        return '%d %s %d' % (day.day, month, day.year)
    return '%d de %s de %d' % (day.day, month, day.year)


def stamp(source, day):
    """Data da última atualização e ano do rodapé, nos quatro idiomas."""
    for code, tag in TAGS.items():
        source = replace_once(
            source,
            r'(<span class="t" lang="%s">[^<]*)<time datetime="[^"]*">[^<]*</time>' % re.escape(tag),
            None, lambda m: '%s<time datetime="%s">%s</time>' % (m.group(1), day.isoformat(), long_date(day, code)))
    return replace_once(source, r'<span class="year">\d{4}</span>', '<span class="year">%d</span>' % day.year)


class OtherEditions(HTMLParser):
    """Localiza, por posição no texto, os elementos class="t" de outros idiomas."""

    def __init__(self, source, keep):
        super().__init__(convert_charrefs=False)
        self.keep = keep
        self.line_starts = [0] + [m.end() for m in re.finditer('\n', source)]
        self.stack, self.ranges = [], []

    def position(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        a = dict(attrs)
        drop = a.get('class') == 't' and a.get('lang') in TAGS.values() and a.get('lang') != self.keep
        self.stack.append((tag, self.position() if drop else None))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        open_tag, start = self.stack.pop()
        assert open_tag == tag, 'HTML mal aninhado perto de </%s>' % tag
        if start is not None:
            self.ranges.append((start, self.position() + len('</%s>' % tag)))


def without_other_editions(source, keep):
    parser = OtherEditions(source, keep)
    parser.feed(source)
    parser.close()
    assert not parser.stack, 'HTML mal aninhado'
    result, cursor = [], 0
    for start, end in sorted(parser.ranges):
        if start < cursor:
            continue  # já removido junto com o elemento que o contém
        line_start = source.rfind('\n', 0, start) + 1
        if not source[line_start:start].strip():
            start = line_start  # leva junto a indentação
        if source[end:end + 1] == '\n':
            end += 1  # e a quebra de linha
        result.append(source[cursor:start])
        cursor = end
    result.append(source[cursor:])
    return ''.join(result)


def replace_once(text, pattern, replacement, function=None):
    new, count = re.subn(pattern, function or (lambda m: replacement), text, count=1)
    assert count == 1, 'não encontrado: %s' % pattern
    return new


def attribute(edition_tag, name, source):
    match = re.search(r'<div class="t" lang="%s"\s+data-title="([^"]+)"\s+data-desc="([^"]+)">' % re.escape(edition_tag), source)
    assert match, 'edição %s sem data-title/data-desc' % edition_tag
    return match.group(1) if name == 'title' else match.group(2)


def language_page(source, code):
    tag = TAGS[code]
    title, description = attribute(tag, 'title', source), attribute(tag, 'desc', source)
    url = BASE + code + '/'
    page = without_other_editions(source, tag)
    page = replace_once(page, r'<html lang="en">', '<html lang="%s" data-lang="%s">' % (tag, code))
    page = replace_once(page, r'<title>[^<]*</title>', '<title>%s</title>' % title)
    page = replace_once(page, r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % description)
    page = replace_once(page, r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%s">' % title)
    page = replace_once(page, r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%s">' % description)
    locales = '<meta property="og:locale" content="%s">\n' % LOCALES[code] + ''.join(
        '<meta property="og:locale:alternate" content="%s">\n' % LOCALES[other] for other in TAGS if other != code)
    page = replace_once(page, r'<meta property="og:locale" content="[^"]*">\n(?:<meta property="og:locale:alternate" content="[^"]*">\n)+', locales)
    page = replace_once(page, r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url)
    page = replace_once(page, r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s">' % url)
    page = replace_once(page, r'<meta property="og:image" content="[^"]*">', '<meta property="og:image" content="%s%s">' % (BASE, IMAGES[code]))
    page = replace_once(page, r'<meta property="og:image:alt" content="[^"]*">', '<meta property="og:image:alt" content="%s">' % IMAGE_ALT[code])
    page = replace_once(page, r'<meta name="twitter:image" content="[^"]*">', '<meta name="twitter:image" content="%s%s">' % (BASE, IMAGES[code]))
    # idioma ativo marcado no seletor também sem JavaScript
    page = page.replace(' aria-current="true">', '>')
    link = '<a href="/%s/" data-lang="%s" lang="%s" hreflang="%s">' % (code, code, tag, tag)
    page = replace_once(page, re.escape(link), link[:-1] + ' aria-current="true">')
    return page


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for name in FILES:
        shutil.copy2(os.path.join(ROOT, name), os.path.join(OUT, name))
    for folder in FOLDERS:
        shutil.copytree(os.path.join(ROOT, folder), os.path.join(OUT, folder))
    commit_date = git('log', '-1', '--format=%cs')
    day = datetime.date.fromisoformat(commit_date) if commit_date else datetime.date.today()
    version = os.environ.get('GITHUB_SHA') or git('rev-parse', 'HEAD') or 'local'
    with open(os.path.join(OUT, 'version.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(version + '\n')
    source = stamp(open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read(), day)
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(source)
    for code in TAGS:
        os.makedirs(os.path.join(OUT, code))
        with open(os.path.join(OUT, code, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(language_page(source, code))
    count = sum(len(files) for _, _, files in os.walk(OUT))
    print('Site montado em _site/: %d arquivos, com as páginas %s; versão %s, atualizado em %s.' % (
        count, ', '.join('/%s/' % c for c in TAGS), version[:7], day.isoformat()))


if __name__ == '__main__':
    sys.exit(main())
