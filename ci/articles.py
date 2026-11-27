"""Artigos: lê src/articles/<slug>.md, confere o cabeçalho, transforma o corpo e monta o feed.

Usado por ci/build.py. Cada artigo é um arquivo Markdown cujo nome é o seu endereço (o slug):
/en/articles/<slug>/. Uma vez publicado, o slug nunca muda; o título pode mudar.

O arquivo começa por um cabeçalho em TOML entre duas linhas +++:

    +++
    title = "Título, em inglês"
    date = 2026-08-24              # data de publicação, sem aspas
    # updated = 2026-…            (opcional: data da última revisão)
    # linkedin = "https://www.linkedin.com/pulse/…"   (opcional: onde o texto também saiu)
    # cv = true                    (opcional: o artigo vai no currículo; no máximo dois)

    [summary]                      # resumo nos quatro idiomas: é apresentação
    en = "…"
    pt = "…"
    es = "…"
    it = "…"
    +++

Depois vem o corpo, em Markdown (CommonMark), escrito como prosa, com aspas e travessões
tipográficos escritos diretamente. O HTML escrito no texto sai escapado: nenhum artigo introduz
<script>, style= ou on…=, e a política de segurança vale sem exceção.

A única marcação além do CommonMark é a língua de um trecho que não está em inglês, exigida pela
WCAG (3.1.2, língua das partes): [Sapientis est ordinare]{lang=la} vira
<span lang="la">Sapientis est ordinare</span>, e *[telos]{lang=grc-Latn}*, o mesmo em itálico.
Vem do plugin attrs de mdit-py-plugins, que aceitaria qualquer atributo; aqui só lang é aceito.
O título aceita só essa marcação: title = "[Sapientis est ordinare]{lang=la}: A Personal…".
Onde o título vai como texto (<title>, prévia, dados estruturados, feed), a marcação sai.

O build para, com uma mensagem que diz o arquivo e o campo, se: o nome do arquivo não seguir a
regra do slug; faltar title, date ou um dos quatro resumos; um resumo estiver vazio; a data for
inválida ou futura; houver um campo desconhecido; o corpo tiver um título de nível 1 (o título
vem do cabeçalho), uma imagem (fora desta etapa), um link que não seja https, ou um trecho
marcado com qualquer atributo além de lang; ou se mais de dois artigos tiverem cv = true.
"""
import datetime
import os
import re
import tomllib
import types
from xml.sax.saxutils import escape, quoteattr

from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins.attrs import attrs_plugin

# nome do arquivo sem .md: minúsculas sem acento e algarismos, palavras separadas por hífen
SLUG = re.compile(r'[a-z0-9]+(-[a-z0-9]+)*')
FENCE = '+++'
SUMMARY_CODES = ('en', 'pt', 'es', 'it')
FIELDS = {'title', 'date', 'updated', 'linkedin', 'summary', 'cv'}
CV_MAX = 2  # artigos no currículo, no máximo
# etiqueta de língua (BCP 47) de um trecho: la, grc-Latn, pt-BR...
LANG = re.compile(r'[a-z]{2,3}(-[A-Za-z0-9]{2,8})*')
FOLDER = 'en/articles/'  # endereço das páginas dos artigos, depois do domínio: /en/articles/<slug>/
# Identificadores do feed (RFC 4151): não dependem do endereço do site. A data é a da compra do
# domínio, quando ele já era do autor.
TAG = 'tag:arthurceicorrea.dev,2026-11-25:'
# As datas dos artigos são dias, sem hora; no feed, que pede data e hora, cada uma vira a meia-noite
# no fuso do autor (São Paulo).
ZONE = datetime.timezone(datetime.timedelta(hours=-3))
AUTHOR = 'Arthur Cei Corrêa'
# campo linkedin: só artigos do LinkedIn (o prefixo também está em ALLOWED_EXTERNAL, em tests/helpers.py)
LINKEDIN = 'https://www.linkedin.com/pulse/'


class ArticleError(Exception):
    """Um artigo com problema; a mensagem diz o arquivo e o campo."""


def markdown():
    """CommonMark, com o HTML do texto escapado e sem conversão tipográfica automática. Atributos
    entre chaves só depois de um trecho entre colchetes ([...]{lang=la}); depois de links, imagens
    e código, ficam como texto."""
    md = MarkdownIt('commonmark', {'html': False, 'xhtmlOut': False, 'typographer': False})
    return md.use(attrs_plugin, after=('span_close',), spans=True)


def split(text, where):
    """Separa o cabeçalho (TOML entre linhas +++) do corpo."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != FENCE:
        raise ArticleError('%s: o arquivo precisa começar pelo cabeçalho, entre duas linhas %s' % (where, FENCE))
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == FENCE:
            return '\n'.join(lines[1:i]), '\n'.join(lines[i + 1:])
    raise ArticleError('%s: falta a linha %s que fecha o cabeçalho' % (where, FENCE))


def day(header, field, where, today, required=True):
    value = header.get(field)
    if value is None:
        if required:
            raise ArticleError('%s: falta o campo %s (por exemplo, %s = 2026-08-24, sem aspas)' % (where, field, field))
        return None
    if type(value) is not datetime.date:
        raise ArticleError('%s: %s = %r não é uma data; escreva só o dia, sem aspas, como %s = 2026-08-24' % (where, field, value, field))
    if value > today:
        raise ArticleError('%s: %s = %s está no futuro' % (where, field, value.isoformat()))
    return value


def check_header(header, where, today):
    unknown = sorted(set(header) - FIELDS)
    if unknown:
        raise ArticleError('%s: campo desconhecido no cabeçalho: %s (os campos são %s)' % (where, ', '.join(unknown), ', '.join(sorted(FIELDS))))
    title = header.get('title')
    if not isinstance(title, str) or not title.strip():
        raise ArticleError('%s: falta o campo title, o título do artigo, em inglês' % where)
    date = day(header, 'date', where, today)
    updated = day(header, 'updated', where, today, required=False)
    if updated and updated < date:
        raise ArticleError('%s: updated = %s é anterior a date = %s' % (where, updated, date))
    linkedin = header.get('linkedin')
    if linkedin is not None and not (isinstance(linkedin, str) and linkedin.startswith(LINKEDIN)):
        raise ArticleError('%s: linkedin = %r deveria ser um artigo do LinkedIn, %s…' % (where, linkedin, LINKEDIN))
    summary = header.get('summary')
    if not isinstance(summary, dict):
        raise ArticleError('%s: falta a tabela [summary], com o resumo em %s' % (where, ', '.join(SUMMARY_CODES)))
    for code in SUMMARY_CODES:
        text = summary.get(code)
        if not isinstance(text, str) or not text.strip():
            raise ArticleError('%s: falta o resumo summary.%s, ou está vazio' % (where, code))
    cv = header.get('cv', False)
    if type(cv) is not bool:
        raise ArticleError('%s: cv = %r; escreva cv = true (o artigo vai no currículo) ou apague a linha' % (where, cv))
    extra = sorted(set(summary) - set(SUMMARY_CODES))
    if extra:
        raise ArticleError('%s: resumo em idioma desconhecido: summary.%s' % (where, ', summary.'.join(extra)))
    return title.strip(), date, updated, linkedin, cv, {code: summary[code].strip() for code in SUMMARY_CODES}


def tokens_of(tokens):
    for token in tokens:
        yield token
        yield from tokens_of(token.children or [])


def check_body(tokens, where):
    for token in tokens_of(tokens):
        line = ' (linha %d do corpo)' % (token.map[0] + 1) if token.map else ''
        if token.type == 'heading_open' and token.tag == 'h1':
            raise ArticleError('%s: título de nível 1 (#) no corpo%s; o título do artigo vem do cabeçalho, '
                               'e os intertítulos começam em ##' % (where, line))
        if token.type == 'image':
            raise ArticleError('%s: imagem no corpo (%s); imagens em artigos ainda não são aceitas' % (where, token.attrGet('src')))
        if token.type == 'link_open' and not str(token.attrGet('href') or '').startswith('https://'):
            raise ArticleError('%s: link %r no corpo; os links dos artigos são só https://' % (where, token.attrGet('href')))
        if token.type == 'span_open':
            extra = sorted(set(token.attrs) - {'lang'})
            lang = str(token.attrGet('lang') or '')
            if extra or not LANG.fullmatch(lang):
                raise ArticleError('%s: trecho marcado com %s; nos artigos, só se marca a língua de um trecho, como '
                                   '[Sapientis est ordinare]{lang=la}' % (where, dict(token.attrs)))


def title_of(md, title, where):
    """O título como texto e como HTML: só texto e trechos marcados com a língua."""
    tokens = md.parseInline(title)[0].children or []
    for token in tokens:
        if token.type not in ('text', 'span_open', 'span_close'):
            raise ArticleError('%s: title = %r: no título, só a marcação da língua de um trecho, '
                               'como [Sapientis est ordinare]{lang=la}' % (where, title))
    check_body(tokens, where)
    text = ''.join(t.content for t in tokens if t.type == 'text')
    return text, Markup(md.renderer.render(tokens, md.options, {}))


def load(folder, today):
    """Os artigos de folder, do mais recente ao mais antigo. Cada um tem slug, title (texto),
    title_html (com a língua dos trechos marcada), date,
    updated (ou None), modified (updated ou date), linkedin (ou None), cv (vai no currículo), summary (por idioma),
    path (/en/articles/<slug>/, sem a barra inicial) e html, o corpo já transformado."""
    md = markdown()
    found = []
    for name in sorted(os.listdir(folder)):
        where = 'src/articles/' + name
        if not name.endswith('.md'):
            raise ArticleError('%s: em src/articles/ só há artigos, um arquivo .md cada' % where)
        slug = name[:-3]
        if not SLUG.fullmatch(slug):
            raise ArticleError('%s: o nome do arquivo é o endereço do artigo; use só minúsculas sem acento, '
                               'algarismos e hífens entre as palavras, como from-purism-to-prudence.md' % where)
        with open(os.path.join(folder, name), encoding='utf-8') as f:
            text = f.read()
        header_text, body = split(text, where)
        try:
            header = tomllib.loads(header_text)
        except tomllib.TOMLDecodeError as error:
            raise ArticleError('%s: o cabeçalho não é TOML válido: %s' % (where, error)) from None
        title, date, updated, linkedin, cv, summary = check_header(header, where, today)
        tokens = md.parse(body)
        if not tokens:
            raise ArticleError('%s: o corpo do artigo está vazio' % where)
        check_body(tokens, where)
        html = md.renderer.render(tokens, md.options, {})
        title, title_html = title_of(md, title, where)
        found.append(types.SimpleNamespace(
            slug=slug, title=title, title_html=title_html, date=date, updated=updated, modified=updated or date, linkedin=linkedin, cv=cv,
            summary=summary, path=FOLDER + slug + '/', lang='en', html=Markup(html)))  # o corpo já vem escapado
    marked = [a.slug for a in found if a.cv]
    if len(marked) > CV_MAX:
        raise ArticleError('src/articles/: %d artigos com cv = true (%s); o currículo leva no máximo %d'
                           % (len(marked), ', '.join(sorted(marked)), CV_MAX))
    return sorted(found, key=lambda a: (a.date, a.slug), reverse=True)


def stamp(day):
    """Data e hora do feed (RFC 3339): a meia-noite do dia, no fuso do autor."""
    return datetime.datetime.combine(day, datetime.time(), ZONE).isoformat()


def feed(articles, base, title):
    """Feed Atom único, em inglês: resumo e texto completo de cada artigo, autor e datas."""
    updated = max(a.modified for a in articles)
    entries = ''.join(
        '  <entry>\n'
        '    <id>%s</id>\n'
        '    <title>%s</title>\n'
        '    <link rel="alternate" type="text/html" href=%s/>\n'
        '    <published>%s</published>\n'
        '    <updated>%s</updated>\n'
        '    <summary>%s</summary>\n'
        '    <content type="html">%s</content>\n'
        '  </entry>\n' % (TAG + a.slug, escape(a.title), quoteattr(base + a.path), stamp(a.date), stamp(a.modified),
                          escape(a.summary['en']), escape(str(a.html)))
        for a in articles)
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">\n'
            '  <id>%sarticles</id>\n'
            '  <title>%s</title>\n'
            '  <link rel="self" type="application/atom+xml" href=%s/>\n'
            '  <link rel="alternate" type="text/html" href=%s/>\n'
            '  <updated>%s</updated>\n'
            '  <author>\n    <name>%s</name>\n    <uri>%s</uri>\n  </author>\n'
            '%s</feed>\n') % (TAG, escape(title), quoteattr(base + 'feed.xml'), quoteattr(base + FOLDER),
                              stamp(updated), escape(AUTHOR), escape(base), entries)
