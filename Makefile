# Atalhos para montar e testar o site localmente.
# Os comandos são os mesmos do pipeline (.github/workflows/site.yml), na mesma ordem.
# Onde só existe "python3", rode, por exemplo: make build PYTHON=python3

PYTHON ?= python
SITE := _site
VNU := ci/node_modules/vnu-jar/build/dist/vnu.jar
AXE := ci/node_modules/axe-core/axe.min.js

.DEFAULT_GOAL := build
.PHONY: setup build test serve

# Instala as ferramentas de teste, nas versões exatas de ci/requirements.txt e ci/package.json.
setup:
	$(PYTHON) -m pip install -r ci/requirements.txt
	npm install --prefix ci --no-audit --no-fund

# Monta o site em _site/ (página inicial, uma página por idioma, 404 e arquivos).
build:
	$(PYTHON) ci/build.py

# Valida o site já montado: verificações próprias, validador do W3C, navegador e acessibilidade.
# O validador do W3C ignora só as duas mensagens sobre propriedades recentes do CSS, como no pipeline.
# LC_ALL=C.UTF-8 garante que o Java leia as aspas curvas do filtro mesmo onde a máquina não tem locale UTF-8.
test:
	$(PYTHON) ci/validate.py $(SITE)
	LC_ALL=C.UTF-8 java -jar $(VNU) --errors-only --format gnu --skip-non-html --filterpattern '.*(“interpolate-size”|“allow-discrete”).*' $(SITE)
	$(PYTHON) ci/smoke.py $(SITE)
	$(PYTHON) ci/a11y.py $(SITE) $(AXE)

# Serve o site montado em http://localhost:8000/
serve:
	$(PYTHON) -m http.server 8000 -d $(SITE)
