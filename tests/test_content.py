"""Textos completos em todos os idiomas (src/content/<idioma>.toml).

Cada chave de pt.toml precisa existir nos outros três arquivos, também dentro dos itens das
listas, e as listas precisam ter o mesmo tamanho. É a mesma checagem que faz ci/build.py parar
(a função missing, de lá), aqui com um teste por idioma: apagar um texto de it.toml reprova
test_texts_are_complete[it] e diz qual chave falta. Não precisa do site montado.

Uso: python -m pytest tests/test_content.py
"""
import os
import sys
import tomllib

import pytest

import helpers

sys.path.insert(0, os.path.join(helpers.REPO, 'ci'))
from build import missing  # noqa: E402

CONTENT = os.path.join(helpers.REPO, 'src', 'content')


def load(code):
    with open(os.path.join(CONTENT, code + '.toml'), 'rb') as f:
        return tomllib.load(f)


@pytest.mark.parametrize('code', [c for c in helpers.CODES if c != 'pt'])
def test_texts_are_complete(code):
    problems = missing(load('pt'), load(code))
    assert not problems, 'src/content/%s.toml: faltam textos de pt.toml:\n  %s' % (code, '\n  '.join(problems))
