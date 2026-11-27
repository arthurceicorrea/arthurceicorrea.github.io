# Plano de reformulação do site

Reorganizar o site, hoje concentrado num `index.html` de cerca de 1.400 linhas com quatro edições do mesmo conteúdo, em arquivos separados por função, com boas práticas. O visitante não deve notar diferença: mesmo visual, mesmo conteúdo, mesmas notas no Lighthouse.

Cada etapa é um ramo e um pull request. Uma etapa só começa depois que a anterior foi incorporada ao `main`.

## Regras que valem em todas as etapas

- **Visual e conteúdo idênticos**, salvo onde a etapa disser o contrário. Em qualquer mudança que possa alterar o visual, anexar capturas antes e depois, em 390 px e 1440 px, das páginas `/pt/` e `/en/`.
- **Os testes atuais são a rede de segurança.** Só se ajusta um teste quando a etapa muda de propósito o que ele verifica, e o pull request explica cada ajuste.
- **Nada de terceiros:** fontes, scripts, imagens e serviços vêm do próprio site. Nenhum rastreador.
- **Política de segurança de conteúdo restritiva.** Nunca `'unsafe-inline'` nem `'unsafe-eval'`.
- **Acessibilidade WCAG 2.2 AA**, verificada pelo axe e pelo Lighthouse (acessibilidade ≥ 95).
- **Nenhum framework rodando no navegador.** Ferramentas de build e de teste podem ser usadas.
- **Sem telefone, endereço ou dados de saúde** em páginas e currículos.
- **Interface e apresentação, nos quatro idiomas:** mudou um texto num idioma, mude nos quatro. **Artigos, só em inglês** (a partir da Etapa 13): o texto e o título ficam em inglês, e o resumo de cada artigo, que é apresentação, nos quatro idiomas.
- **O relatório final de cada etapa** explica, em português simples, o que mudou e por quê.

## Estrutura de destino

```
src/
  page.html          modelo da página (Jinja2), escrito uma vez
  404.html           modelo da página de erro
  content/
    pt.toml          textos de cada idioma
    en.toml
    es.toml
    it.toml
  css/
    tokens.css       cores, fontes, medidas
    base.css         tipografia e elementos
    layout.css       topo, sumário, seções
    components.css   ficha, projetos, botões
  js/
    language.js      escolha do idioma (roda cedo, no <head>)
    page.js          copiar e-mail, voltar ao topo, seção atual, impressão
static/              fontes, currículos, imagens, vCard, robots.txt
ci/                  build e ferramentas do pipeline
tests/               testes em pytest
docs/
  PLAN.md            este arquivo
  adr/               registros de decisão
```

A estrutura é o destino. Cada etapa chega a uma parte dela.

---

## Etapa 0: preparação

**Objetivo:** deixar o repositório pronto para as próximas etapas, sem mudar o site.

**O que muda**
- `CLAUDE.md` na raiz e este `docs/PLAN.md`.
- `LICENSE` com a licença MIT para o código. No README, uma nota dizendo que textos, currículos e imagens são de Arthur Cei Corrêa, com todos os direitos reservados.
- `.editorconfig`: UTF-8, LF, indentação de 2 espaços, 4 em Python, linha final.
- `Makefile` com:
  - `make setup`: instala as dependências de `ci/requirements.txt` e `ci/package.json`;
  - `make build`: roda `python ci/build.py`;
  - `make test`: roda validação, teste no navegador e acessibilidade, na ordem do workflow;
  - `make serve`: roda `python -m http.server 8000 -d _site`.
- README: seção "Como rodar localmente" usando o `make`.

**Fora do escopo:** qualquer mudança em `index.html`, CSS, JS ou testes.

**Pronto quando:** `make build && make test` passa, o `_site/` gerado é idêntico byte a byte ao de antes (exceto `version.txt` e a data do rodapé), e o pipeline do pull request está verde.

**O que Arthur precisa entender:** para que serve cada arquivo novo e o que cada alvo do `make` executa.

---

## Etapa 1: fluxo por pull request (feita por Arthur no GitHub)

**Objetivo:** nada entra no `main` sem o pipeline verde.

Esta etapa é uma configuração, não código. Arthur faz no GitHub:

1. Settings → Rules → Rulesets → **Proteger main** → editar.
2. Marcar **Require a pull request before merging**, com 0 aprovações obrigatórias, porque o projeto tem uma pessoa só.
3. Marcar **Require status checks to pass** e adicionar a verificação **Validar**.
4. Manter **Restrict deletions** e **Block force pushes**. Não adicionar ninguém à lista de exceções.
5. Salvar e confirmar com a passkey.

**Pronto quando:** um pull request de teste mostra a verificação **Validar** como obrigatória, e um push direto no `main` é recusado.

**O que Arthur precisa entender:** a diferença entre proteger o deploy (o que já existia) e proteger o próprio `main`.

---

## Etapa 2: CSS e JavaScript em arquivos próprios

**Objetivo:** tirar o `<style>` e o `<script>` embutidos de `index.html` e `404.html`.

**O que muda**
- O CSS vai para `src/css/` (tokens, base, layout, components) organizado com `@layer`. O build junta tudo num único `/assets/site.css`.
- O JavaScript vai para `src/js/`:
  - `language.js` decide o idioma. Continua carregado no `<head>` sem `defer`, porque precisa agir antes da primeira pintura da página, para o visitante não ver o idioma errado piscar.
  - `page.js` cuida do resto e é carregado como módulo (`type="module"`).
- A política de segurança passa a ser `style-src 'self'; script-src 'self'`, sem hashes. O bloco JSON-LD (`application/ld+json`) continua embutido, porque é dado e não código executado.
- Sai `ci/csp_hash.py`. Em `ci/validate.py`, a verificação de hashes vira outra: nenhum `<style>` ou `<script>` embutido além do JSON-LD, nenhum atributo `style=` ou `on...=`, e a política exatamente como definida.

**Fora do escopo:** modelo, textos por idioma, a raiz.

**Pronto quando:**
- as capturas antes e depois são idênticas pixel a pixel, conferidas com um script de comparação do Playwright, nas quatro páginas de idioma e na raiz, em 390 px e 1440 px;
- todos os testes passam;
- o Lighthouse mantém as notas.

**O que Arthur precisa entender:** por que `'self'` é tão seguro quanto os hashes aqui, e por que `language.js` não pode ser adiado.

---

## Etapa 3: modelo único e textos por idioma

**Objetivo:** acabar com as quatro cópias da página.

**O que muda**
- `src/page.html`, um modelo Jinja2 com a estrutura da página escrita uma vez, e `src/404.html`.
- `src/content/{pt,en,es,it}.toml` com todos os textos. Os projetos ficam como uma lista de dados: acrescentar um projeto é acrescentar um bloco.
- `ci/build.py` passa a montar cada página a partir do modelo e do arquivo do idioma, em vez de recortar edições de um HTML grande. Gera título, descrição, Open Graph, `canonical`, `hreflang`, sitemap e `version.txt`, como hoje.
- **A raiz muda de propósito.** Deixa de carregar os quatro idiomas e passa a ser a edição em inglês (`x-default`). O `language.js`, na raiz, leva o visitante para `/pt/`, `/es/` ou `/it/` pela mesma ordem de hoje: `?lang=`, depois o fuso do aparelho, depois o idioma do navegador. Sem JavaScript, a raiz fica em inglês.
- Os arquivos estáticos (fontes, currículos, imagens, vCard, robots) vão para `static/`, copiados como estão.
- Novo teste: cada chave presente em `pt.toml` existe nos outros três. Faltou um texto, o build falha.
- Jinja2 entra em `ci/requirements.txt`, com versão exata.

**Fora do escopo:** mudar textos. Esta etapa move conteúdo, não o reescreve.

**Pronto quando:**
- `/pt/`, `/en/`, `/es/` e `/it/` ficam iguais pixel a pixel às de antes;
- a raiz redireciona conforme o descrito;
- os testes de idioma do `ci/smoke.py`, e também os checks da raiz em `ci/validate.py` e `ci/monitor.py` (que exigiam as quatro edições na raiz), foram ajustados só no que diz respeito à raiz, cada ajuste explicado no pull request;
- tudo mais passa sem mudança.

Se o pull request ficar grande demais para revisar, dividir em dois: primeiro as páginas de idioma, depois a raiz.

**O que Arthur precisa entender:** como um modelo e quatro arquivos de texto geram cinco páginas, e por que a raiz mudou.

---

## Etapa 4: testes em pytest

**Objetivo:** trocar os scripts com a função `check()` caseira pelo padrão de mercado.

**O que muda**
- `tests/` com pytest: `test_static.py` (o que hoje está em `validate.py`), `test_browser.py` (`smoke.py`), `test_a11y.py` (`a11y.py`). Mesmas verificações, uma por teste, com nomes descritivos.
- `make test` e o workflow passam a rodar `pytest`.
- pytest entra em `ci/requirements.txt`, com versão exata.

**Fora do escopo:** novas verificações, exceto se uma antiga não puder ser reproduzida igual.

**Pronto quando:** o número de verificações é igual ou maior que antes, e quebrar de propósito uma página (por exemplo, apagar um texto em `it.toml`) faz o teste certo falhar com uma mensagem clara.

**O que Arthur precisa entender:** como rodar um teste só (`pytest -k nome`) e como ler uma falha.

---

## Etapa 5: verificadores de estilo de código e cache no pipeline

**O que muda**
- Stylelint (configuração padrão) para `src/css/`, ESLint (recomendado) para `src/js/` e Prettier para CSS e JS, como dependências de desenvolvimento em `ci/package.json`, com versões exatas. Novo `make lint`, e um passo no workflow antes dos testes.
- Cache das dependências do pip e do npm no pipeline, com ações presas por hash de commit, como as demais.

**Fora do escopo:** mudar regras para silenciar erros. Erro real se corrige; regra que não se aplica ao projeto se desliga com um comentário explicando.

**Pronto quando:** `make lint` passa, e o tempo do job **Validar** antes e depois aparece no pull request.

---

## Etapa 6: documentação

**O que muda**
- README reescrito: o que é o site, como rodar, a estrutura de pastas, o pipeline (o que cada etapa verifica) e o monitoramento semanal.
- `docs/adr/` com um registro curto por decisão (contexto, decisão, consequências):
  1. GitHub Pages, publicado só pelo GitHub Actions
  2. Política de segurança em meta tag, com `'self'`
  3. Idioma pelo fuso horário, e não pelo endereço IP
  4. Nenhum recurso de terceiros e nenhum analytics
  5. Jinja2 e TOML em vez de um gerador de sites ou framework
  6. Um pull request por mudança, com o pipeline obrigatório
  7. Ações do GitHub presas por hash de commit

**Pronto quando:** Arthur leu cada registro e confirmou que descreve o que ele decidiu.

---

## Etapa 7: currículos gerados a partir do conteúdo

**Objetivo:** o site e os currículos nunca mais se desencontrarem.

**O que muda**
- `src/cv.html`, o modelo do currículo, e os dados que só o currículo usa nos arquivos de conteúdo.
- O build gera os quatro PDFs em A4 com o Playwright (`page.pdf`), no lugar dos PDFs feitos à mão.
- As verificações atuais de currículo continuam valendo: nenhum telefone, rodapé no idioma do currículo.

**Pronto quando:** os quatro PDFs são gerados no pipeline, o texto bate com o site, e Arthur aprovou o visual comparando com os PDFs atuais.

---

## Etapa 8: refinamento tipográfico

**Objetivo:** dar ao lema o lugar de única nota alta da página e tirar da interface os vícios de página gerada por máquina. É a única etapa da reformulação que muda o visual de propósito; o conteúdo continua o mesmo.

**O que muda**
- O lema vira inscrição: o Cinzel em tamanho grande, em duas linhas fixas, com o ponto romano (interpunct) entre as palavras da primeira, decorativo e silencioso para leitores de tela.
- O Cinzel fica só onde é inscrição: o lema, a atribuição e os títulos das seções. Menu, seletor de idioma, botões, "Ver detalhes", "Copiar" e o link de pular passam ao EB Garamond, em caixa normal; os idiomas em versaletes.
- O nome passa ao EB Garamond, em caixa normal e um pouco maior, como o autor sob a epígrafe. A animação própria do nome, que fechava o espaçamento das letras, sai: ele surge como o resto da apresentação.
- Saem os pontos médios do seletor de idioma e da linha dos ofícios, que passa a ser uma frase em itálico, com vírgulas.
- Cores, contrastes, textos, a página 404 e os currículos não mudam. No currículo o nome fica em Cinzel: lá não há lema com que disputar, e o nome é o único título da página.
- Um registro de decisão (ADR 9) explica a escolha.

**Pronto quando:** os testes e o `make lint` passam, o Lighthouse mantém as notas, a 404 fica igual pixel a pixel, e Arthur aprovou as capturas antes e depois das páginas de idioma e da raiz, em 390 px e 1440 px.

**O que Arthur precisa entender:** por que gastar a ousadia num lugar só, por que o ponto romano pertence ao lema e não ao menu, e por que o nome muda no site e não no currículo.

---

## Etapa 9: domínio próprio

Domínio: `arthurceicorrea.dev`, comprado na Cloudflare em 25/11/2026. A etapa sai em três pull requests, para que cada merge chegue ao `main` com o pipeline verde: a infraestrutura; depois de o domínio responder com certificado, o proxy; depois do proxy aplicado, a troca do endereço e a conferência dos cabeçalhos no ar.

**Feito por Arthur, antes do código**
- Compra do domínio e DNSSEC ligado.
- Um bucket R2, `arthurceicorrea-tfstate`, para o estado do Terraform.
- Duas credenciais de cada tipo, todas restritas a este domínio ou a este bucket: um token da Cloudflare e uma chave do R2 só de leitura, guardados como segredos do repositório para o `plan` do pipeline; um token e uma chave de escrita, só no gerenciador de senhas de Arthur, para o `apply`. Nunca num arquivo.

**Pull request A: infraestrutura** (o site não muda)
- `infra/` com Terraform (provedor da Cloudflare), versões exatas e estado no R2:
  - DNS apontando para o GitHub Pages, `www` e o registro TXT que verifica o domínio no GitHub;
  - registros que declaram que o domínio não tem e-mail (MX nulo, SPF e DMARC), contra e-mails falsos em nome dele;
  - redirecionamento do `www` e cabeçalhos de segurança: política de segurança com `frame-ancestors 'none'`, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`;
  - SSL Full (strict), e desligado tudo o que reescreve o HTML ou injeta scripts.
- O proxy da Cloudflare começa desligado, porque o GitHub só emite o certificado quando o DNS aponta direto para ele.
- `terraform plan` roda no pull request (workflow `infra.yml`). `terraform apply` é feito por Arthur, conforme `infra/README.md`.
- Depois do `apply`, Arthur verifica o domínio no GitHub, informa-o em Settings → Pages, espera o certificado e marca "Enforce HTTPS". O arquivo `CNAME` não é preciso: com a publicação pelo GitHub Actions, o GitHub o ignora e usa essa configuração.
- Registro de decisão: ADR 10.

**Pull request B1: proxy**
- O proxy é ligado, e com ele os cabeçalhos e o redirecionamento. Antes do `apply`, o certificado Universal da Cloudflare precisa estar ativo.
- Fica separado da troca do endereço porque o merge publica o site e confere o que está no ar na hora: os cabeçalhos só existem depois do `apply`, que vem depois do merge.

**Pull request B2: troca do endereço**
- Troca do endereço do site em todo lugar: `ci/build.py`, `static/` (vCard, robots), sitemap, `canonical`, testes, workflows e README. O endereço antigo `arthurceicorrea.github.io` passa a redirecionar sozinho.
- O monitoramento passa a conferir também os cabeçalhos de segurança no ar.
- Fora do repositório, feito por Arthur: README do perfil e LinkedIn.

---

## Etapa 10: agradecimento (colofão e página Gratiarum actio)

**Objetivo:** incluir no site um agradecimento católico, tomista, no tom visual do site (fundo escuro, dourado, Cinzel e EB Garamond, lema "Sapientis est ordinare"). O texto agradece primeiro a Deus e depois à esposa de Arthur, nessa ordem, de propósito: é a ordem da caridade em Santo Tomás e ecoa o lema. A esposa não é nomeada: o texto diz sempre "minha esposa". Esta etapa muda o conteúdo e o visual de propósito, só no que se descreve abaixo.

**O que muda**
- **Colofão.** Primeira linha do rodapé, discreta, com a fórmula latina *Non nisi te, Domine*, na raiz e nas páginas de idioma. O lema continua no alto, como única nota alta da página (Etapa 8): a página abre com o lema e fecha com o colofão. O latim é o mesmo nos quatro idiomas e não se traduz.
  - É um link para a página Gratiarum actio no idioma atual. Na raiz, que é a edição em inglês, leva a `/en/gratiarum-actio/`.
  - Na própria página Gratiarum actio, o colofão aparece sem link.
  - A 404 não recebe colofão: não tem rodapé e mostra os quatro idiomas de uma vez.
- **Página Gratiarum actio**, em `/pt/gratiarum-actio/`, `/en/gratiarum-actio/`, `/es/gratiarum-actio/` e `/it/gratiarum-actio/`. O endereço é o mesmo nos quatro idiomas, porque é latim.
  - Modelo próprio em `src/` (por exemplo, `src/gratiarum.html`), com o mesmo `<head>`, a mesma política de segurança, as mesmas folhas de estilo e o mesmo rodapé da página principal.
  - A prosa e as traduções das citações vão numa tabela nova, `[gratiarum]`, em cada `src/content/{pt,en,es,it}.toml`. O latim fica escrito uma vez só, no modelo, como hoje o lema em `src/page.html`: assim é idêntico nos quatro idiomas por construção.
  - `ci/build.py` gera as quatro páginas, cada uma com título, descrição, Open Graph, `canonical` e `hreflang` próprios (o `x-default` aponta para a edição em inglês), e as acrescenta ao sitemap.
  - O seletor de idioma leva à mesma página nos outros idiomas, e há um link de volta à página inicial do idioma.
- **Latim marcado.** Todo trecho em latim, no colofão e na página, inclusive os que aparecem no meio da prosa, leva `lang="la"`, por acessibilidade.
- **Testes**
  - As quatro páginas novas entram em `PAGES`, em `tests/helpers.py` e em `ci/monitor.py`, e nas `url` de `ci/lighthouserc.json`, para que valham nelas as verificações que já existem: política de segurança, telefones, links, validador do W3C, axe e Lighthouse.
  - Novos testes: cada página com colofão o tem como link para a página Gratiarum actio do próprio idioma (na raiz, a do inglês); na página Gratiarum actio, o colofão não é link; todo trecho em latim tem `lang="la"`; os trechos em latim são idênticos nas quatro edições.
  - `tests/test_content.py` passa a cobrir a tabela `[gratiarum]` sem mudança: cada chave de `pt.toml` precisa existir nos outros três.

**Texto da página**

A versão em português está abaixo. As versões em inglês, espanhol e italiano são traduções fiéis dela, no mesmo registro elevado. O latim não muda: cada citação latina fica em latim nos quatro idiomas, seguida da tradução no idioma da página. Só a prosa e as traduções são traduzidas.

- Título: *Gratiarum actio*
- Epígrafe:
  > *Ingressum instruas, progressum dirigas, egressum compleas.*
  > Instruí o começo, dirigi o progresso, completai o fim.
  > — Santo Tomás de Aquino, oração *Creator ineffabilis*
- Parágrafo 1:
  > A Deus, ótimo e máximo, princípio e fim de todas as coisas, rendo graças em primeiro lugar, como é de justiça. Se é próprio do sábio ordenar, e se, como ensina Santo Tomás, o nome de sábio pertence propriamente àquele que considera o fim do universo, que é também o seu princípio (Suma contra os Gentios I, 1), então ordenar o meu trabalho é ordená-lo a Ele. Tudo o que aqui se mostra d'Ele procede, pois toda dádiva perfeita desce do Pai das luzes (Tg 1, 17).
- Parágrafo 2:
  > Depois, à minha esposa. "*Domus et divitiae dantur a parentibus; a Domino autem proprie uxor prudens*": a casa e as riquezas vêm dos pais, mas a esposa prudente vem propriamente do Senhor (Pr 19, 14). E entre marido e mulher, diz Santo Tomás, "*maxima amicitia esse videtur*", parece haver a maior das amizades (Suma contra os Gentios III, 123). Por ela, companheira dos trabalhos e consolo da vida, rendo graças a Deus, e a ela agradeço de todo o coração.
- Fecho, em latim e sem tradução: *Laus Deo.*

Dedicatória curta em latim, guardada para usos futuros (por exemplo, nos currículos). Não entra na página nesta etapa: a epígrafe já abre a página, a dedicatória repetiria os dois parágrafos, e ainda não tem tradução aprovada por Arthur.

> *Deo Optimo Maximo, principio et fini omnium, a quo omne datum optimum descendit, primas gratias ago; deinde uxori meae, praecipuo eius dono, laborum sociae et vitae solacio.*

**Fora do escopo:** mudanças de estrutura alheias à etapa; a dedicatória na página; a 404 e os currículos.

**Pronto quando:**
- o colofão está visível e funcional na raiz e nas quatro páginas de idioma, levando à página Gratiarum actio no idioma certo;
- a página existe nos quatro idiomas, com o latim idêntico em todos e marcado com `lang="la"`;
- o nome da esposa não aparece em parte alguma: textos, metadados, commits e pull request;
- `make build`, `make lint` e `make test` passam, com as linhas de resumo coladas no pull request, e o Lighthouse mantém as notas, também nas páginas novas;
- o pull request traz capturas antes e depois, em 390 px e 1440 px, do rodapé de `/pt/` e `/en/`, e capturas da página nova nos mesmos tamanhos (ela não tem "antes");
- o relatório final explica cada mudança em português simples, como para uma entrevista.

**O que Arthur precisa entender:** como uma página nova entra no build (modelo, tabela de textos, endereços, sitemap) sem copiar a estrutura da página principal; por que o latim fica escrito uma vez só no modelo e a prosa nos arquivos de idioma; e para que serve `lang="la"`: leitores de tela e tradutores automáticos sabem que o trecho é latim e não o leem como se fosse português ou inglês.

---

## Etapas 11 a 14: privacidade, alertas de segurança e artigos

As etapas de privacidade (11) e de artigos (13 e 14) vêm de uma discussão de 25 a 27/11/2026, registrada no ADR 11. Arthur passa a publicar artigos com regularidade: no site primeiro e, depois, no LinkedIn, com um resumo e o link. Os artigos são escritos só em inglês; o resto do site continua nos quatro idiomas. A privacidade vem antes porque é pequena, descreve uma situação que já existe (a Cloudflare está na frente do site desde a Etapa 9) e cria no build a peça que as listas de artigos vão usar: uma página nos quatro idiomas, com endereço traduzido, registrada numa tabela única de páginas. A Etapa 12 entrou depois, em 27/11/2026, quando a aba de segurança do GitHub mostrou quatro alertas do CodeQL e a política de segurança desligada; vem antes dos artigos por ser pequena e tratar de segurança.

---

## Etapa 11: aviso de privacidade

**Objetivo:** dizer com exatidão, numa página curta nos quatro idiomas, o que o site não faz e o que acontece fora dele; e garantir com testes que a página, o rodapé e o site nunca se contradigam.

**O que muda**
- **Página de privacidade** em `/pt/privacidade/`, `/en/privacy/`, `/es/privacidad/` e `/it/privacy/`. O endereço é traduzido, ao contrário da Gratiarum actio, que é latim.
  - Modelo próprio, `src/privacy.html`, que estende `src/layout.html`: mesmo `<head>`, mesma política de segurança, mesmo rodapé. No topo (bloco `top`), o link de volta à página inicial do idioma, como na Gratiarum actio.
  - Os textos e o endereço de cada idioma numa tabela nova, `[privacy]`, em cada `src/content/{pt,en,es,it}.toml`.
  - O seletor de idioma leva à mesma página nos outros idiomas.
- **Rodapé.** A frase "Página sem cookies, sem rastreadores e sem recursos de terceiros." passa a ser link para a página de privacidade do idioma, em todas as páginas com rodapé. O texto da frase não muda.
- **Tabela única das páginas** em `ci/build.py`. Cada entrada diz o modelo, o endereço em cada idioma (traduzido ou igual) e as versões alternativas; dela saem a montagem, o `canonical`, o `hreflang` (o `x-default` aponta para a edição em inglês) e o sitemap, que hoje são escritos caso a caso. A Gratiarum actio passa a usar a tabela, sem nenhuma mudança no que se publica.
- **Infraestrutura, só um comentário.** Em `infra/settings.tf`, junto ao bloco `cloudflare_bot_management`: ligar qualquer desses recursos faz a Cloudflare pôr cookies (por exemplo, `__cf_bm`) e obriga a mudar a página de privacidade e o rodapé. O `terraform plan` não muda.
- **Testes**
  - As quatro páginas entram em `PAGES` (`tests/helpers.py`), em `ci/monitor.py` e nas `url` de `ci/lighthouserc.json`, para que valham nelas as verificações que já existem.
  - Novo: toda página listada no `sitemap.xml` está em `PAGES`. Assim nenhuma página nova escapa dos testes, e a lista dos testes continua escrita à parte, sem concordar com o build por construção.
  - Novo: em toda página com rodapé, a frase de privacidade é link para a página de privacidade do próprio idioma.
  - Novo: as quatro edições da página de privacidade têm o link da política da Cloudflare, o da declaração do GitHub (os dois em `ALLOWED_EXTERNAL`) e o e-mail.
  - Novo: nenhum arquivo de `src/js/` usa `document.cookie`, `localStorage`, `sessionStorage`, `indexedDB`, `fetch`, `XMLHttpRequest` ou `sendBeacon`. É o que sustenta "nada guardado, nada enviado".
  - Novo, no navegador: depois de visitar as páginas, o navegador não tem cookie nenhum do site, e o `localStorage` está vazio.
  - Novo, no ar (`ci/monitor.py`, a cada publicação e toda semana): nenhuma resposta do site traz `Set-Cookie`. É o teste que percebe se alguém ligar o Bot Fight Mode no painel da Cloudflare, fora do Terraform.

**Texto da página**

A versão em português está abaixo. As versões em inglês, espanhol e italiano são traduções fiéis dela. Os links das duas políticas levam às páginas em inglês e dizem isso (`hreflang="en"` e a indicação "em inglês" no texto).

- Título: Privacidade
- Parágrafo 1:
  > Este site não usa cookies, não guarda nada no seu navegador, não mede visitas e não carrega nada de outros sites: fontes, estilos, scripts e imagens vêm dele mesmo. O idioma é escolhido no seu aparelho, pelo fuso horário, sem consultar serviço algum, e o endereço desta página não é enviado aos sites para onde os links levam.
- Parágrafo 2, com a lista:
  > Fora do site, dois serviços recebem a sua visita, como acontece com qualquer site publicado neles:
  > - a Cloudflare, que responde pelo domínio `arthurceicorrea.dev` e entrega as páginas, processa o seu endereço IP e dados da conexão (política de privacidade da Cloudflare, em inglês);
  > - o GitHub Pages, que hospeda o site, registra o endereço IP de quem visita, por segurança, e o recebe da Cloudflare a cada página buscada (declaração de privacidade do GitHub, em inglês).
- Parágrafo 3:
  > Nenhuma das duas políticas fixa um prazo de guarda desses registros. Ao seguir um link para o LinkedIn ou o GitHub, você passa às regras desses sites. Dúvidas: (o e-mail, como link).

Os fatos por trás do texto, conferidos em 27/11/2026:
- GitHub, [What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), seção "Data collection": o endereço IP de quem visita é registrado e guardado por segurança, com ou sem login no GitHub. A [declaração de privacidade](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement) não dá prazo de retenção.
- Cloudflare, [HTTP headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/): `CF-Connecting-IP` e `X-Forwarded-For` são acrescentados por padrão e levam o IP do visitante ao servidor de origem. Por isso o GitHub recebe o IP mesmo com o proxy ligado; quem usa o endereço antigo em `github.io` fala direto com o GitHub antes do redirecionamento.
- Cloudflare, [política de privacidade](https://www.cloudflare.com/privacypolicy/): processa endereços IP e dados de roteamento dos visitantes, é processadora dos registros e encaminha os visitantes ao dono do site; não fixa prazo de retenção desses registros. Daí o e-mail de contato na página.
- Cloudflare, [cookies](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/cloudflare-cookies/): os cookies que ela põe vêm de recursos que se ligam (Bot Management, Bot Fight Mode, regras de taxa, desafios); o Terraform os mantém desligados ([ADR 10](adr/0010-cloudflare-in-front-of-github-pages-managed-by-terraform.md)).

**Fora do escopo:** alegar conformidade com qualquer lei (a página só descreve fatos verificáveis); mudar o texto da frase do rodapé; mudar configurações da Cloudflare; os artigos.

**Pronto quando:**
- a página existe nos quatro idiomas, com o texto aprovado por Arthur;
- a frase do rodapé é link em todas as páginas com rodapé, e a Gratiarum actio é publicada igual a antes;
- `make build`, `make lint` e `make test` passam, com as linhas de resumo coladas no pull request, e o Lighthouse mantém as notas, também na página nova;
- depois do merge, a conferência no ar passa, inclusive a de `Set-Cookie`;
- o pull request traz capturas antes e depois, em 390 px e 1440 px, do rodapé de `/pt/` e `/en/`, e capturas da página nova nos mesmos tamanhos.

**O que Arthur precisa entender:** por que a frase "sem cookies" depende de uma configuração da Cloudflare, e como a conferência no ar a garante; por que o GitHub recebe o IP do visitante mesmo com a Cloudflare na frente; por que a página descreve fatos e não alega conformidade com lei; e como a tabela única de páginas evita escrever endereços, `hreflang` e sitemap caso a caso.

---

## Etapa 12: alertas do CodeQL e política de segurança

**Objetivo:** resolver os quatro alertas que o CodeQL abriu no `main` e publicar a política de segurança do repositório, que o GitHub mostra como desligada. O visitante não nota diferença.

**Os alertas, examinados um a um em 27/11/2026**

| # | Alerta do CodeQL | Onde | Decisão |
|---|---|---|---|
| 1 | Use of insecure SSL/TLS version (alto) | `ci/monitor.py`, conferência do certificado | Corrigir: a versão mínima de TLS passa a ser explícita. |
| 3 | Client-side URL redirect (médio) | `src/js/language.js`, redirecionamento da página inicial | Não há falha explorável: o idioma só pode ser `pt`, `en`, `es` ou `it`, e a âncora vem depois da barra, então não muda o domínio nem o caminho. Reescrever a linha para que a própria análise o reconheça, sem dispensar o alerta. |
| 4 | DOM text reinterpreted as HTML (alto) | a mesma linha | O mesmo do #3. |
| 2 | Bad HTML filtering regexp (alto, marcado como teste) | `tests/test_static.py`, teste de scripts embutidos | Não há falha: a expressão procura `<script>` no HTML que o próprio build gera e não filtra conteúdo de ninguém. O código fica como está; Arthur dispensa o alerta. |

**Feito por Arthur, no GitHub**
- Dispensar o alerta #2 como *Used in tests*, com o comentário: "Test code: the regex looks for inline scripts in the site's own build output; it does not filter untrusted input."
- Depois do merge, conferir em Security and quality que a análise do `main` fechou os alertas #1, #3 e #4 e que a política de segurança aparece como ativa.

**O que muda**
- **`ci/monitor.py`:** uma função só cria o contexto TLS do monitor, com `minimum_version = ssl.TLSVersion.TLSv1_2`, e as três conexões HTTPS passam a usá-la (as páginas lidas com `urlopen`, os redirecionamentos e o certificado). Nas versões atuais do Python o mínimo já é TLS 1.2, mas implícito; fica escrito, igual ao que a Cloudflare impõe (`min_tls_version = "1.2"` em `infra/settings.tf`).
- **`src/js/language.js`:** o redirecionamento da página inicial deixa de concatenar `location.hash` inteiro: `"/" + current + "/" + (location.hash ? "#" + location.hash.slice(1) : "")`. O comportamento é o mesmo (`/pt/` sem âncora, `/pt/#projetos` com ela); o `#` passa a ser texto fixo do código, e não algo lido da URL. Um comentário explica o porquê.
- **`SECURITY.md`**, na raiz, em inglês como o README:
  - o que cobre: o site em `arthurceicorrea.dev`, o código, os workflows e a infraestrutura deste repositório;
  - como relatar: só pelo relato privado de vulnerabilidades do GitHub (link para `/security/advisories/new`), nunca numa issue pública; nenhum e-mail, porque o domínio não tem e-mail;
  - versão coberta: só a que está no ar, publicada do `main`;
  - o que fica de fora: falhas do próprio GitHub, do GitHub Pages ou da Cloudflare, que se relatam a eles;
  - nenhum prazo de resposta, porque Arthur não definiu um.
- **README:** o `SECURITY.md` entra na estrutura de pastas e ganha uma linha na seção de segurança.
- **Testes:** um teste novo no navegador, com o fuso do Brasil: a página inicial com `#projetos` leva a `/pt/#projetos`, e sem âncora leva a `/pt/`, sem `#` no fim. Ele garante que a reescrita não mudou o comportamento.

**Fora do escopo:** mudar configurações do GitHub (análise de código, relato privado, regras do ramo); um workflow próprio do CodeQL no lugar da configuração padrão; comentários de supressão no código; qualquer outra mudança no monitor ou na escolha do idioma.

**Pronto quando:**
- a análise do CodeQL no pull request não aponta os alertas #1, #3 e #4. Se a reescrita não bastar para o #3 e o #4, o pull request diz isso, e Arthur decide entre outra reescrita e dispensar os alertas como *False positive*;
- `make build`, `make lint` e `make test` passam, com as linhas de resumo coladas no pull request, e o monitor passa contra o site no ar (na sessão, se ela alcançar o site; senão, no pipeline depois do merge);
- o pull request diz que não há mudança visual e, por isso, não traz capturas.

**O que Arthur precisa entender:** como o CodeQL segue um dado de uma "fonte" (a URL) até um "destino" (`location.replace`) e por que ele não enxerga as garantias do caminho, como a lista fechada de idiomas; quando se corrige o código e quando se dispensa um alerta, e por que dispensar exige justificativa; para que servem o `SECURITY.md` e o relato privado (divulgação coordenada: a falha chega primeiro ao dono, e não ao público); e por que escrever o TLS mínimo, mesmo quando ele já é o padrão.

---

## Etapa 13: artigos

**Objetivo:** publicar artigos no próprio site, em inglês, apresentados nos quatro idiomas. A estreia é um artigo de apresentação do site e do projeto; junto com ele, o ensaio que já está no LinkedIn passa a morar no site.

**Feito por Arthur, antes do código**
- Fornecer o texto final do artigo de apresentação, redigido na sessão de Comunicação, já atualizado com a etapa em que o projeto estiver (o rascunho é de 25/11/2026, quando o plano ia até a Etapa 8), o título e o resumo nos quatro idiomas.
- Fornecer o texto integral de "From Purism to Prudence: Artificial Intelligence and the Right Order of Means", publicado no LinkedIn em 24/08/2026.
- Confirmar o resumo do ensaio nos quatro idiomas (são os de `[article]`, hoje nos arquivos de conteúdo).

**O que muda**
- **Um arquivo por artigo**, `src/articles/<slug>.md`. O nome do arquivo é o slug: minúsculas sem acento, palavras separadas por hífen, curto. **Uma vez publicado, o slug nunca muda**; o título pode mudar. Os dois primeiros são o da apresentação, cujo slug sai do título final, e `src/articles/from-purism-to-prudence.md`.
  - Cabeçalho em TOML entre linhas `+++`, lido pelo `tomllib` (o exemplo é o do ensaio):
    ```toml
    +++
    title = "From Purism to Prudence: Artificial Intelligence and the Right Order of Means"
    date = 2026-08-24
    # updated = 2026-…   (opcional)
    linkedin = "https://www.linkedin.com/pulse/…"   # opcional: onde o texto também saiu

    [summary]
    en = "…"
    pt = "…"
    es = "…"
    it = "…"
    +++
    ```
  - Corpo em Markdown (CommonMark), escrito como prosa. Aspas e travessões tipográficos se escrevem diretamente, como nos arquivos TOML.
  - O build para, com uma mensagem que diz o arquivo e o campo, se faltar `title`, `date` ou um dos quatro resumos, se um resumo estiver vazio, se a data for inválida ou futura, ou se o nome do arquivo não seguir a regra do slug.
- **Markdown com `markdown-it-py==4.3.0` e `mdurl==0.1.2`**, versões exatas em `ci/requirements.txt`. Preset `commonmark`, com `html` desligado: todo HTML escrito no texto sai escapado, de modo que nenhum artigo introduz `<script>`, `style=` ou `on…=`, e a política de segurança e os testes continuam valendo sem exceção. Sem conversão tipográfica automática e sem notas de rodapé (se um texto precisar delas, entra `mdit-py-plugins`, com versão exata).
- **Código novo num módulo próprio**, `ci/articles.py`, importado por `ci/build.py`: lê e valida os artigos, transforma o Markdown e monta o feed. Os artigos, as listas e o feed entram na tabela única de páginas da Etapa 11.
- **Página de cada artigo**, só em inglês, em `/en/articles/<slug>/`, com o modelo `src/article.html`, que estende `src/layout.html`.
  - A página inteira é em inglês, inclusive o topo, o rodapé e as datas: `<html lang="en" data-lang="en">`. Com o idioma fixo, o script de idioma não leva ninguém a outra página, qualquer que seja o fuso.
  - Título, data e, quando houver `linkedin`, a linha "Originally published on LinkedIn on {date}", com o link.
  - `canonical` para a própria página e **nenhum `hreflang`**: não há versão em outra língua. O seletor de idioma marca EN como atual, e PT, ES e IT levam à lista de artigos naquela língua.
  - Dados estruturados: o mesmo nó `Person` da página inicial (mesmo `@id`) e um nó `Article` com `headline`, `description` (o resumo em inglês), `url`, `inLanguage` (`en`), `datePublished`, `dateModified`, `author` e, quando houver, `sameAs` com o endereço do LinkedIn.
  - Prévia de compartilhamento: `og:type` `article`, `article:published_time`, `article:modified_time`, `og:locale` `en_US` e a imagem `og.png`. Imagem de prévia própria de cada artigo fica para depois.
  - Tipografia, conforme o [ADR 9](adr/0009-cinzel-only-where-the-page-is-an-inscription.md): o título do artigo e os intertítulos em EB Garamond, o título maior; o corpo em EB Garamond, com cerca de 65 a 70 caracteres por linha. O Cinzel fica nos títulos de seção, como o "Artigos" da lista. O detalhe se decide com as capturas.
- **Listas de artigos nos quatro idiomas**, em `/pt/artigos/`, `/en/articles/`, `/es/articulos/` e `/it/articoli/`, com o modelo `src/articles.html`.
  - A interface (título, datas por extenso, rótulos) no idioma da lista. Os mesmos artigos nas quatro, do mais recente ao mais antigo, sem paginação.
  - Cada item: o título em inglês, com `lang="en"` no título e `hreflang="en"` no link; a data no formato do idioma; o resumo no idioma da lista.
  - No alto das listas em português, espanhol e italiano, uma frase: "Os artigos são escritos em inglês." (e o equivalente). Na inglesa, não.
  - As quatro declaram as versões nos outros idiomas (`hreflang`), e o seletor leva à mesma lista nos outros idiomas.
  - Um link para o feed.
- **Feed Atom único**, `/feed.xml`, com `xml:lang="en"`: resumo e texto completo de cada artigo, autor e datas. O identificador do feed e de cada entrada é um URI `tag:` (RFC 4151), que não depende do endereço do site: `tag:arthurceicorrea.dev,2026-11-25:articles` para o feed e `tag:arthurceicorrea.dev,2026-11-25:<slug>` para cada entrada (a data é a da compra do domínio, quando ele já era de Arthur). Um `<link rel="alternate" type="application/atom+xml">` em `src/layout.html` anuncia o feed em todas as páginas que usam a moldura.
- **Sitemap**: as quatro listas, com as versões por idioma, e cada artigo, sem versões alternativas; todos com `lastmod`.
- **Links no corpo dos artigos**: só `https`, abrindo na mesma aba (sem `target`), e nada carregado como recurso. `ALLOWED_EXTERNAL` continua valendo para os links da interface e dos modelos. Imagens dentro de artigos ficam fora desta etapa.
- **A estreia: o artigo de apresentação.** O texto é de Arthur, e a data é a do dia em que for publicado. Não tem campo `linkedin`, porque sai primeiro no site; o post no LinkedIn vem depois, com o resumo e o link. Como é o mais recente, aparece no topo das listas e do feed.
- **O ensaio do LinkedIn passa a ser um arquivo de artigo**, com a data original, 24/08/2026, e a menção ao LinkedIn. Por ser mais antigo, vem depois da apresentação nas listas e no feed.
- **Os dados saem do build e dos arquivos de idioma.** A constante `ARTICLE` de `ci/build.py` e as chaves `summary` de `[article]` saem; a seção da página inicial, o bloco `work` dos dados estruturados e o currículo passam a ler os arquivos de artigo.
  - A seção da página inicial mantém a forma atual nesta etapa, com um artigo só, o mais recente (a apresentação). O link leva à página do artigo no site, e os rótulos que citam o LinkedIn passam a citar o site. A forma nova da seção vem na Etapa 14.
  - O currículo continua com o ensaio, lido agora do arquivo dele. A escolha dos artigos do currículo vem na Etapa 14.
- **Registro de decisão:** [ADR 11](adr/0011-articles-in-markdown-in-english-built-by-the-same-script.md). O ADR 5 passa a dizer que foi estendido por ele.
- **Testes**
  - Do conteúdo, sem o site montado: o cabeçalho de cada artigo tem `title`, `date` e os quatro resumos, nenhum vazio; a data não está no futuro; o nome do arquivo segue a regra do slug.
  - **Endereços publicados não somem:** um arquivo `tests/published.txt` lista o endereço de cada artigo já publicado, e o teste falha se algum deles não existir no site montado. Acrescentar a linha faz parte de publicar um artigo.
  - Página do artigo: `lang="en"` e `data-lang="en"`; `canonical` para ela mesma e nenhum `hreflang`; dados estruturados com o artigo e a pessoa; o seletor leva às quatro listas.
  - Listas: o idioma da página e as quatro versões declaradas; cada título com `lang="en"`; a frase sobre o inglês nas três listas que não são inglesas; cada artigo de `src/articles/` aparece em cada lista, com o resumo do idioma.
  - Feed: XML bem formado, identificadores únicos e no formato `tag:`, cada link existe no site, datas coerentes com os cabeçalhos.
  - Links no corpo: só `https`, sem `target`, nada carregado como recurso.
  - No navegador: com o fuso do Brasil, a página do artigo continua em inglês; o seletor leva às listas; nenhum erro no console. O axe passa a cobrir uma lista e o artigo.
  - Ajustes em testes existentes, cada um explicado no pull request: "mesmas versões que a página inicial" passa a valer só para as páginas iniciais; `ALLOWED_EXTERNAL` deixa de valer para os links no corpo dos artigos; os testes do currículo e dos dados estruturados passam a ler o resumo do arquivo do artigo; as listas e o artigo entram em `PAGES`, em `ci/monitor.py` e no Lighthouse.

**Fora do escopo:** traduções de artigos (se um dia houver, ganham endereço próprio e só então entram `hreflang` e `workTranslation`); imagens e notas de rodapé nos artigos; categorias, paginação e busca; imagem de prévia por artigo; a forma nova da seção da página inicial e a escolha dos artigos do currículo (Etapa 14); banco de dados e gerador de sites (descartados no ADR 11).

**Pronto quando:**
- o artigo de apresentação está publicado em `/en/articles/<slug>/`, com o texto fornecido por Arthur e a data da publicação, no topo das listas e do feed;
- o ensaio está publicado em `/en/articles/from-purism-to-prudence/`, com o texto fornecido por Arthur, a data de 24/08/2026 e a menção ao LinkedIn;
- `tests/published.txt` lista os dois endereços;
- as quatro listas e o feed existem, e o sitemap os lista;
- os currículos continuam em duas páginas e com o resumo do ensaio no seu idioma;
- `make build`, `make lint` e `make test` passam, com as linhas de resumo coladas no pull request, e o Lighthouse mantém as notas, também nas páginas novas;
- o pull request traz capturas da página do artigo e das listas `/pt/artigos/` e `/en/articles/`, em 390 px e 1440 px, e antes e depois da seção da página inicial.

**O que Arthur precisa entender:** como um arquivo Markdown vira página (cabeçalho, corpo, modelo, tabela de páginas); por que o HTML dentro do Markdown fica desligado; por que o slug nunca muda e como `tests/published.txt` guarda isso; por que o feed usa identificadores `tag:` e não endereços; por que a página do artigo não tem `hreflang` e o seletor leva às listas; e por que os artigos ficam no repositório, e não num banco de dados, nem num gerador de sites.

---

## Etapa 14: artigos na página inicial e no currículo

**Objetivo:** mostrar os artigos mais recentes na página inicial sem que a seção cresça a cada publicação, e levar ao currículo só os artigos que Arthur escolher.

**O que muda**
- **A seção "Artigo" passa a "Artigos"**, no título e no sumário, nos quatro idiomas. A âncora muda junto: `#artigos`, `#articles`, `#articulos`, `#articoli`. Um link antigo para `#artigo` leva ao topo da página, sem erro.
- **Até três artigos, um em destaque e dois em linha:**
  - o mais recente, em destaque: título em inglês (`lang="en"`), data no formato do idioma e resumo no idioma da página;
  - os dois anteriores, uma linha cada: título e data;
  - nas páginas em português, espanhol e italiano, a frase "Os artigos são escritos em inglês." acima dos itens;
  - no fim, o link "Todos os artigos", para a lista do idioma, presente mesmo com um artigo só.
- **Sem carrossel e sem movimento.** Tudo visível, sem JavaScript. Um carrossel foi considerado e descartado: dois dos três artigos ficariam escondidos; passar sozinho seria um segundo movimento na página, contra o [ADR 9](adr/0009-cinzel-only-where-the-page-is-an-inscription.md), que deixa o fio dourado sob o lema como único; e a WCAG 2.2.2 exigiria botão de pausa e parada com o foco e com o mouse.
- **Currículo: no máximo dois artigos, escolhidos por Arthur**, com `cv = true` no cabeçalho do artigo. Cada um entra com título, data e o resumo no idioma do currículo, e uma linha final dá o endereço da lista de artigos no idioma. O build para se houver mais de dois marcados. O ensaio começa marcado; o artigo de apresentação não, porque interessa a quem visita o site, e pouco a quem lê um currículo.
- **Testes**
  - A página inicial mostra no máximo três artigos, o mais recente em destaque com o resumo do idioma, os outros só com título e data, e o link para a lista do idioma; a frase sobre o inglês nas três línguas que não são inglesas.
  - O sumário continua levando a cinco seções visíveis.
  - O currículo traz o resumo de cada artigo marcado, no seu idioma; no máximo dois marcados; o teste de "no máximo duas páginas" continua valendo.

**Fora do escopo:** mudar as outras seções da página inicial; carrossel ou qualquer rotação automática; mudar o desenho do currículo além da seção de artigos.

**Pronto quando:**
- `make build`, `make lint` e `make test` passam, com as linhas de resumo coladas no pull request, e o Lighthouse mantém as notas;
- Arthur aprovou as capturas antes e depois da seção, em `/pt/` e `/en/`, em 390 px e 1440 px, e os quatro currículos.

**O que Arthur precisa entender:** por que um artigo em destaque e dois em linha, e não um carrossel; por que o currículo leva os artigos escolhidos, e não os mais recentes; e por que mudar a âncora é aceitável aqui, ao contrário do slug de um artigo.

---

## Depois da reformulação (conteúdo)

- Revisão dos textos em italiano e espanhol por um falante nativo.
- Competências ligadas às provas: cada grupo diz onde foi usado, com link para o projeto.
- Formato e tamanho nos links de download (por exemplo, "PDF, 104 KB").
- Atalho `/cv`, que abre o currículo no idioma do visitante (depois do domínio).
