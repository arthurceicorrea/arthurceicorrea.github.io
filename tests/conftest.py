"""Configuração comum dos testes (pytest), lida antes de qualquer teste.

Opções de linha de comando:
  --site PASTA   site montado por ci/build.py (padrão: _site)
  --axe ARQUIVO  axe.min.js do pacote npm axe-core (padrão: ci/node_modules/axe-core/axe.min.js)
Variável opcional CHROME_PATH: caminho de um Chrome já instalado; sem ela, usa o Chrome do sistema.

Fixtures (valores que os testes recebem pelo nome do parâmetro):
  site_url   endereço de um servidor local que serve o site montado; um só por execução
  browser    Chrome sem interface (Playwright); um só por execução
  axe        texto do axe.min.js
"""
import functools
import http.server
import os
import threading

import pytest

import helpers

AXE_ADVICE = pytest.StashKey[set]()


def pytest_addoption(parser):
    parser.addoption('--site', default=os.path.join(helpers.REPO, '_site'), help='pasta do site montado (padrão: _site)')
    parser.addoption('--axe', default=os.path.join(helpers.REPO, 'ci', 'node_modules', 'axe-core', 'axe.min.js'),
                     help='caminho do axe.min.js (padrão: ci/node_modules/axe-core/axe.min.js)')


def pytest_configure(config):
    helpers.ROOT = os.path.abspath(config.getoption('--site'))
    config.stash[AXE_ADVICE] = set()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope='session')
def site_url():
    helpers.require_site()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=helpers.ROOT))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield 'http://127.0.0.1:%d/' % server.server_address[1]
    server.shutdown()


@pytest.fixture(scope='session')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        chrome = os.environ.get('CHROME_PATH')
        instance = pw.chromium.launch(executable_path=chrome) if chrome else pw.chromium.launch(channel='chrome')
        yield instance
        instance.close()


@pytest.fixture(scope='session')
def axe(pytestconfig):
    name = pytestconfig.getoption('--axe')
    if not os.path.isfile(name):
        pytest.exit('axe.min.js não encontrado em %s. Rode antes: make setup' % name, returncode=2)
    with open(name, encoding='utf-8') as f:
        return f.read()


@pytest.fixture(scope='session')
def axe_advice(pytestconfig):
    """Recomendações de boas práticas do axe: só relatadas no fim, não reprovam."""
    return pytestconfig.stash[AXE_ADVICE]


def pytest_terminal_summary(terminalreporter, config):
    advice = config.stash.get(AXE_ADVICE, set())
    if advice:
        terminalreporter.section('axe: boas práticas (não reprovam)')
        for line in sorted(advice):
            terminalreporter.write_line(line)
