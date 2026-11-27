"""Textos completos em todos os idiomas (src/content/<idioma>.toml).

Cada chave de pt.toml precisa existir nos outros três arquivos, também dentro dos itens das
listas, e as listas precisam ter o mesmo tamanho. É a mesma checagem que faz ci/build.py parar
(a função missing, de lá), aqui com um teste por idioma: apagar um texto de it.toml reprova
test_texts_are_complete[it] e diz qual chave falta. Não precisa do site montado.

Também confere os artigos (src/articles/<slug>.md), lendo o cabeçalho aqui de novo, e não pelo
build: o nome do arquivo segue a regra do slug; o cabeçalho tem title, date e os quatro resumos,
nenhum vazio; a data não está no futuro. E confere que o build (ci/articles.py) recusa, com uma
mensagem que diz o arquivo e o campo, cada problema que deve recusar (também mais de dois artigos
marcados para o currículo), e que a página de um artigo
publicado também no LinkedIn traz a linha "Originally published on LinkedIn".

Uso: python -m pytest tests/test_content.py
"""
import datetime
import os
import re
import sys
import tomllib

import pytest

import helpers

sys.path.insert(0, os.path.join(helpers.REPO, 'ci'))
import articles  # noqa: E402
import build  # noqa: E402
from build import missing  # noqa: E402

CONTENT = os.path.join(helpers.REPO, 'src', 'content')


def load(code):
    with open(os.path.join(CONTENT, code + '.toml'), 'rb') as f:
        return tomllib.load(f)


@pytest.mark.parametrize('code', [c for c in helpers.CODES if c != 'pt'])
def test_texts_are_complete(code):
    problems = missing(load('pt'), load(code))
    assert not problems, 'src/content/%s.toml: faltam textos de pt.toml:\n  %s' % (code, '\n  '.join(problems))


# ---------- artigos: o cabeçalho de cada arquivo ----------

ARTICLES = os.path.join(helpers.REPO, 'src', 'articles')
NAMES = sorted(os.listdir(ARTICLES))
# a regra do slug, escrita aqui de novo: minúsculas sem acento e algarismos, hífen entre as palavras
SLUG = re.compile(r'[a-z0-9]+(-[a-z0-9]+)*\.md')


@pytest.mark.parametrize('name', NAMES)
def test_article_file_name_is_a_slug(name):
    assert SLUG.fullmatch(name), 'src/articles/%s: o nome é o endereço do artigo; use minúsculas sem acento, algarismos e hífens' % name


@pytest.mark.parametrize('slug', list(helpers.article_headers()))
def test_article_header_has_title_date_and_four_summaries(slug):
    header = helpers.article_headers()[slug]
    summary = header.get('summary') or {}
    problems = ([] if isinstance(header.get('title'), str) and header['title'].strip() else ['title'])
    problems += [] if type(header.get('date')) is datetime.date else ['date']
    problems += ['summary.%s' % code for code in helpers.CODES if not str(summary.get(code) or '').strip()]
    assert not problems, 'src/articles/%s.md: faltam, ou estão vazios ou inválidos, no cabeçalho: %s' % (slug, ', '.join(problems))


@pytest.mark.parametrize('slug', list(helpers.article_headers()))
def test_article_date_is_not_in_the_future(slug):
    header = helpers.article_headers()[slug]
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)  # um dia de folga: o fuso de quem roda
    days = [header[k] for k in ('date', 'updated') if type(header.get(k)) is datetime.date]
    assert all(day <= tomorrow for day in days), 'src/articles/%s.md: data no futuro: %s' % (slug, days)


# ---------- artigos: o que o build recusa ----------

TODAY = datetime.date(2026, 11, 27)
GOOD_HEADER = """+++
title = "A title"
date = 2026-08-24

[summary]
en = "Summary."
pt = "Resumo."
es = "Resumen."
it = "Riassunto."
+++
"""


def load_one(tmp_path, text, name='an-article.md'):
    (tmp_path / name).write_text(text, encoding='utf-8')
    return articles.load(str(tmp_path), TODAY)


def test_build_accepts_a_good_article(tmp_path):
    found = load_one(tmp_path, GOOD_HEADER + '\nSome *text* with [a link](https://example.org/) and [Deo gratias]{lang=la}.\n')
    html = str(found[0].html)
    assert '<span lang="la">Deo gratias</span>' in html and '<a href="https://example.org/">' in html


REFUSED = {
    'bad slug': ('An_Article.md', GOOD_HEADER + 'Text.\n', 'nome do arquivo'),
    'no header': ('an-article.md', 'Text.\n', 'cabeçalho'),
    'no title': ('an-article.md', GOOD_HEADER.replace('title = "A title"\n', ''), 'title'),
    'no date': ('an-article.md', GOOD_HEADER.replace('date = 2026-08-24\n', ''), 'date'),
    'date as text': ('an-article.md', GOOD_HEADER.replace('date = 2026-08-24', 'date = "2026-08-24"'), 'date'),
    'future date': ('an-article.md', GOOD_HEADER.replace('2026-08-24', '2026-11-28'), 'futuro'),
    'missing summary': ('an-article.md', GOOD_HEADER.replace('it = "Riassunto."\n', ''), 'summary.it'),
    'empty summary': ('an-article.md', GOOD_HEADER.replace('"Resumo."', '" "'), 'summary.pt'),
    'unknown field': ('an-article.md', GOOD_HEADER.replace('date = 2026-08-24', 'date = 2026-08-24\ntags = []'), 'tags'),
    'level-1 heading': ('an-article.md', GOOD_HEADER + '# Title again\n', 'nível 1'),
    'image': ('an-article.md', GOOD_HEADER + '![x](https://example.org/x.png)\n', 'imagem'),
    'http link': ('an-article.md', GOOD_HEADER + '[x](http://example.org/)\n', 'https'),
    'relative link': ('an-article.md', GOOD_HEADER + '[x](/en/)\n', 'https'),
    'style attribute': ('an-article.md', GOOD_HEADER + '[x]{style="color:red"}\n', 'lang'),
    'class': ('an-article.md', GOOD_HEADER + '[x]{.highlight}\n', 'lang'),
    'attribute besides lang': ('an-article.md', GOOD_HEADER + '[x]{lang=la title="t"}\n', 'lang'),
    'markup in title': ('an-article.md', GOOD_HEADER.replace('"A title"', '"A [title](https://example.org/)"') + 'Text.\n', 'title'),
    'empty body': ('an-article.md', GOOD_HEADER, 'vazio'),
    'cv as text': ('an-article.md', GOOD_HEADER.replace('date = 2026-08-24', 'date = 2026-08-24\ncv = "yes"') + 'Text.\n', 'cv'),
}


@pytest.mark.parametrize('case', list(REFUSED))
def test_build_refuses_a_bad_article(tmp_path, case):
    name, text, field = REFUSED[case]
    with pytest.raises(articles.ArticleError) as error:
        load_one(tmp_path, text, name)
    assert name in str(error.value) and field in str(error.value), 'mensagem sem o arquivo ou o campo: %s' % error.value


def test_build_refuses_more_than_two_articles_in_the_cv(tmp_path):
    marked = GOOD_HEADER.replace('date = 2026-08-24', 'date = 2026-08-24\ncv = true') + 'Text.\n'
    for name in ('one.md', 'two.md'):
        (tmp_path / name).write_text(marked, encoding='utf-8')
    assert [a.slug for a in articles.load(str(tmp_path), TODAY) if a.cv] == ['two', 'one']
    (tmp_path / 'three.md').write_text(marked, encoding='utf-8')
    with pytest.raises(articles.ArticleError) as error:
        articles.load(str(tmp_path), TODAY)
    assert 'cv = true' in str(error.value) and 'three' in str(error.value), 'mensagem sem o campo ou os artigos: %s' % error.value


def test_build_escapes_html_written_in_an_article(tmp_path):
    found = load_one(tmp_path, GOOD_HEADER + 'A <script>alert(1)</script> and <b style="x" onclick="y">bold</b>.\n\n<div>block</div>\n\n'
                     '[x]{lang=la onclick="go()"}\n')
    html = str(found[0].html)
    assert '<script' not in html and '<b ' not in html and '<div' not in html and '&lt;script&gt;' in html
    assert 'onclick=' not in html.replace('onclick=&quot;', ''), 'um atributo on…= passou para o HTML: %s' % html


# ---------- artigos: a linha do LinkedIn ----------

def test_article_published_on_linkedin_says_so(tmp_path):
    """Nenhum artigo de hoje tem o campo linkedin; a página de um que tenha diz onde e quando saiu."""
    url = 'https://www.linkedin.com/pulse/an-article/'
    posts = load_one(tmp_path, GOOD_HEADER.replace('date = 2026-08-24', 'date = 2026-08-24\nlinkedin = "%s"' % url) + 'Text.\n')
    content = build.load_content()
    table = build.page_table(content, posts)
    entry = table['article:an-article']
    html = build.environment().get_template('article.html').render(
        page=build.head(entry, 'en', content), editions=[build.edition('en', content)], current_page='article:an-article',
        post=entry.post, **build.shared_context(content, TODAY, table, posts))
    line = 'Originally published on <a href="%s" target="_blank" rel="noopener noreferrer">LinkedIn' % url
    assert line in html and '"sameAs": "%s"' % url in html and 'on <time datetime="2026-08-24">August 24, 2026</time>.' in html
