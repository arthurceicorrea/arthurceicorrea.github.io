# Atalhos para montar e testar o site localmente.
# Os comandos são os mesmos do pipeline (.github/workflows/site.yml), na mesma ordem.
# Onde só existe "python3", rode, por exemplo: make build PYTHON=python3

PYTHON ?= python
SITE := _site
VNU := ci/node_modules/vnu-jar/build/dist/vnu.jar

.DEFAULT_GOAL := build
.PHONY: setup build test serve

# Instala as ferramentas de teste, nas versões exatas de ci/requirements.txt e ci/package.json.
setup:
	$(PYTHON) -m pip install -r ci/requirements.txt
	npm install --prefix ci --no-audit --no-fund

# Monta o site em _site/ (página inicial, uma página por idioma, 404 e arquivos).
build:
	$(PYTHON) ci/build.py

# Valida o site já montado, na ordem do pipeline: textos completos e validação estática (pytest),
# validador do W3C, teste no navegador (pytest) e acessibilidade (pytest). Os testes ficam em tests/.
# O validador do W3C ignora só as duas mensagens sobre propriedades recentes do CSS, como no pipeline.
# LC_ALL=C.UTF-8 garante que o Java leia as aspas curvas do filtro mesmo onde a máquina não tem locale UTF-8.
test:
	$(PYTHON) -m pytest tests/test_content.py tests/test_static.py
	LC_ALL=C.UTF-8 java -jar $(VNU) --errors-only --format gnu --skip-non-html --filterpattern '.*(“interpolate-size”|“allow-discrete”).*' $(SITE)
	$(PYTHON) -m pytest tests/test_browser.py
	$(PYTHON) -m pytest tests/test_a11y.py

# Serve o site montado em http://localhost:8000/
serve:
	$(PYTHON) -m http.server 8000 -d $(SITE)
