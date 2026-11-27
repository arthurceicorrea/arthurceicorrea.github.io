# Site-portfólio de Arthur Cei Corrêa

Site estático em quatro idiomas (pt-BR, en, es, it), publicado no GitHub Pages apenas pelo GitHub Actions (`.github/workflows/site.yml`). O plano de trabalho está em `docs/PLAN.md`: faça só a etapa pedida, nada além dela.

## Comandos

- Instalar: `make setup` (as dependências de `ci/requirements.txt` e, com `npm ci`, de `ci/package-lock.json`)
- Verificar o estilo do código: `make lint` (Stylelint, ESLint e Prettier em `src/css/` e `src/js/`). Para corrigir a formatação: `ci/node_modules/.bin/prettier --write "src/css/**/*.css" "src/js/**/*.js"`.
- Montar: `make build` (roda `python ci/build.py` e gera `_site/`)
- Testar: `make test`, depois de `make build`. Roda, na ordem do workflow, o pytest com `tests/test_content.py` e `tests/test_static.py`, o validador do W3C (precisa de Java), e o pytest com `tests/test_browser.py` e `tests/test_a11y.py`. O Lighthouse só roda no pipeline.
- Um teste só: `python -m pytest -k nome` (por exemplo, `-k csp`).
- Ver o site: `make serve` (em http://localhost:8000/)
- Onde só existir `python3`, acrescente `PYTHON=python3` ao comando.
- Os testes com navegador usam o Chrome do sistema, ou o caminho em `CHROME_PATH`.

## Regras

- Nenhum recurso de terceiros (fontes, scripts, imagens, analytics): tudo é servido pelo próprio site.
- Política de segurança de conteúdo restritiva: nunca `'unsafe-inline'` nem `'unsafe-eval'`.
- WCAG 2.2 AA: contraste mínimo 4,5:1, foco visível, `lang` em cada bloco de idioma.
- Link externo da interface e dos modelos, com `target="_blank"`, leva `rel="noopener noreferrer"` e precisa constar em `ALLOWED_EXTERNAL`, em `tests/helpers.py`. Os links no corpo dos artigos são só `https`, abrem na mesma aba e não carregam nada.
- Nunca publicar telefone, endereço ou dados de saúde. Os testes procuram telefones.
- Conteúdo verdadeiro: não inventar fatos, métricas, certificações ou competências.
- Interface e apresentação, nos quatro idiomas: mudou um texto num idioma, mude nos quatro. Os textos ficam em `src/content/{pt,en,es,it}.toml`, e um teste exige as mesmas chaves nos quatro; os modelos ficam em `src/`, com a moldura comum em `src/layout.html`.
- Artigos, só em inglês (a partir da Etapa 12 de `docs/PLAN.md`): o texto e o título de cada artigo ficam em inglês, em `src/articles/<slug>.md`, junto com o resumo, que é apresentação e vai nos quatro idiomas. As listas e a página inicial apresentam os artigos nos quatro idiomas, com o título marcado `lang="en"`. Um artigo publicado nunca muda de slug, e o seu endereço fica em `tests/published.txt`. Trecho em outra língua, no corpo ou no título: `[Sapientis est ordinare]{lang=la}`; é a única marcação além do CommonMark (`ci/articles.py`). A página inicial mostra os três artigos mais recentes; o currículo, os marcados com `cv = true` (no máximo dois).
- Ações do GitHub ficam presas por hash de commit, com a versão num comentário. Ferramentas de teste ficam com versões exatas.
- Mensagens de commit em inglês, no imperativo.
