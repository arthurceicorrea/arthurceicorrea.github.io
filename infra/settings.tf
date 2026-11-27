# Configurações da zona. As que dizem respeito ao tráfego só agem com o proxy ligado.
locals {
  zone_settings = {
    # Cloudflare → GitHub Pages também por HTTPS, conferindo o certificado do GitHub ("Full (strict)").
    ssl = "strict"
    # http:// vira https:// já na Cloudflare.
    always_use_https = "on"
    min_tls_version  = "1.2"
    # Desligados porque reescrevem o HTML: o Email Obfuscation e o Rocket Loader injetam scripts de
    # terceiros, que a política de segurança bloquearia e o ADR 4 proíbe; o Automatic HTTPS Rewrites
    # mexe nos links, que já são todos https.
    email_obfuscation        = "off"
    rocket_loader            = "off"
    automatic_https_rewrites = "off"
  }
}

resource "cloudflare_zone_setting" "this" {
  for_each = local.zone_settings

  zone_id    = local.zone_id
  setting_id = each.key
  value      = each.value
}

# Recursos de proteção contra robôs que alteram as páginas ou podem barrar visitas legítimas:
# - enable_js: injeta um script de detecção em cada página (terceiro, bloqueado pela CSP);
# - fight_mode: desafia tráfego automatizado, inclusive a conferência do site no ar feita pelo pipeline;
# - crawler_protection: o "labirinto" que insere links escondidos nas páginas;
# - is_robots_txt_managed: anteporia regras da Cloudflare ao robots.txt do site;
# - ai_bots_protection: bloquearia robôs de IA, o que contradiz o "Allow: /" do robots.txt do site.
# Privacidade: ligar qualquer destes recursos faz a Cloudflare pôr cookies no navegador de quem visita
# (por exemplo, __cf_bm), e o site deixaria de ser "sem cookies". Isso obriga a mudar a página de
# privacidade (src/privacy.html e a tabela [privacy] de src/content/) e a frase do rodapé. A
# conferência no ar (ci/monitor.py) falha se alguma resposta do site trouxer Set-Cookie.
resource "cloudflare_bot_management" "this" {
  zone_id               = local.zone_id
  enable_js             = false
  fight_mode            = false
  crawler_protection    = "disabled"
  is_robots_txt_managed = false
  ai_bots_protection    = "disabled"
}
