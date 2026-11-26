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
- **Mudou um texto num idioma, mude nos quatro.**
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

**Objetivo:** dar ao lema o lugar de única nota alta da página e tirar da interface os vícios de página gerada por máquina. É a única etapa que muda o visual de propósito; o conteúdo continua o mesmo.

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

## Depois da reformulação (conteúdo)

- Revisão dos textos em italiano e espanhol por um falante nativo.
- Competências ligadas às provas: cada grupo diz onde foi usado, com link para o projeto.
- Formato e tamanho nos links de download (por exemplo, "PDF, 104 KB").
- Atalho `/cv`, que abre o currículo no idioma do visitante (depois do domínio).
