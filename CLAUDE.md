# Site-portfólio de Arthur Cei Corrêa

Site estático em quatro idiomas (pt-BR, en, es, it), publicado no GitHub Pages apenas pelo GitHub Actions (`.github/workflows/site.yml`). O plano de trabalho está em `docs/PLAN.md`: faça só a etapa pedida, nada além dela.

## Comandos

- Instalar: `pip install -r ci/requirements.txt` e `npm install --prefix ci`
- Montar: `python ci/build.py` (gera `_site/`)
- Testar: `python ci/validate.py _site`, `python ci/smoke.py _site` e `python ci/a11y.py _site ci/node_modules/axe-core/axe.min.js`
- Os testes com navegador usam o Chrome do sistema, ou o caminho em `CHROME_PATH`.
- Quando existir o `Makefile`, use `make setup`, `make build`, `make test` e `make serve`, e atualize esta seção.

## Regras

- Nenhum recurso de terceiros (fontes, scripts, imagens, analytics): tudo é servido pelo próprio site.
- Política de segurança de conteúdo restritiva: nunca `'unsafe-inline'` nem `'unsafe-eval'`.
- WCAG 2.2 AA: contraste mínimo 4,5:1, foco visível, `lang` em cada bloco de idioma.
- Link externo com `target="_blank"` leva `rel="noopener noreferrer"` e precisa constar em `ALLOWED_EXTERNAL`, em `ci/validate.py`.
- Nunca publicar telefone, endereço ou dados de saúde. Os testes procuram telefones.
- Conteúdo verdadeiro: não inventar fatos, métricas, certificações ou competências.
- Mudou um texto num idioma, mude nos quatro.
- Ações do GitHub ficam presas por hash de commit, com a versão num comentário. Ferramentas de teste ficam com versões exatas.
- Mensagens de commit em inglês, no imperativo.
