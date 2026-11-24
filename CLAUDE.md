# Site-portfólio de Arthur Cei Corrêa

Site estático em quatro idiomas (pt-BR, en, es, it), publicado no GitHub Pages apenas pelo GitHub Actions (`.github/workflows/site.yml`). O plano de trabalho está em `docs/PLAN.md`: faça só a etapa pedida, nada além dela.

## Comandos

- Instalar: `make setup` (as dependências de `ci/requirements.txt` e `ci/package.json`)
- Montar: `make build` (roda `python ci/build.py` e gera `_site/`)
- Testar: `make test`, depois de `make build`. Roda, na ordem do workflow, `ci/validate.py`, o validador do W3C (precisa de Java), `ci/smoke.py` e `ci/a11y.py`. O Lighthouse só roda no pipeline.
- Ver o site: `make serve` (em http://localhost:8000/)
- Onde só existir `python3`, acrescente `PYTHON=python3` ao comando.
- Os testes com navegador usam o Chrome do sistema, ou o caminho em `CHROME_PATH`.

## Regras

- Nenhum recurso de terceiros (fontes, scripts, imagens, analytics): tudo é servido pelo próprio site.
- Política de segurança de conteúdo restritiva: nunca `'unsafe-inline'` nem `'unsafe-eval'`.
- WCAG 2.2 AA: contraste mínimo 4,5:1, foco visível, `lang` em cada bloco de idioma.
- Link externo com `target="_blank"` leva `rel="noopener noreferrer"` e precisa constar em `ALLOWED_EXTERNAL`, em `ci/validate.py`.
- Nunca publicar telefone, endereço ou dados de saúde. Os testes procuram telefones.
- Conteúdo verdadeiro: não inventar fatos, métricas, certificações ou competências.
- Mudou um texto num idioma, mude nos quatro. Os textos ficam em `src/content/{pt,en,es,it}.toml`; o modelo da página é `src/page.html`.
- Ações do GitHub ficam presas por hash de commit, com a versão num comentário. Ferramentas de teste ficam com versões exatas.
- Mensagens de commit em inglês, no imperativo.
