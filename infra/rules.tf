# Regras que só agem com o proxy da Cloudflare ligado (local.proxied). Ficam prontas desde já,
# para que ligar o proxy seja a única mudança daquele pull request.

# www.arthurceicorrea.dev/qualquer/caminho?x=1 → https://arthurceicorrea.dev/qualquer/caminho?x=1
resource "cloudflare_ruleset" "redirect_www" {
  zone_id = local.zone_id
  name    = "Redirecionamentos"
  kind    = "zone"
  phase   = "http_request_dynamic_redirect"

  rules = [{
    ref         = "www_to_apex"
    description = "www para o dominio raiz, mantendo caminho e parametros"
    expression  = "(http.host eq \"www.${local.domain}\")"
    action      = "redirect"
    action_parameters = {
      from_value = {
        status_code           = 301
        preserve_query_string = true
        target_url = {
          expression = "concat(\"https://${local.domain}\", http.request.uri.path)"
        }
      }
    }
  }]
}

# Cabeçalhos de segurança que o GitHub Pages não deixa definir.
# - Content-Security-Policy: só frame-ancestors, que não funciona em meta tag (ADR 2). O resto da política
#   continua na meta tag das páginas; o navegador aplica as duas, e uma não afrouxa a outra.
# - Strict-Transport-Security: o navegador só usa HTTPS no domínio por um ano. O .dev já exige HTTPS
#   para todo o domínio de topo; o cabeçalho repete a regra para este domínio e os subdomínios.
# - X-Content-Type-Options: o navegador não tenta adivinhar o tipo de um arquivo.
# - Referrer-Policy: igual à meta tag das páginas; nenhum endereço de origem é enviado a outros sites.
# - Permissions-Policy: nega recursos que o site não usa. A área de transferência não entra na lista,
#   porque o botão de copiar o e-mail precisa dela.
resource "cloudflare_ruleset" "security_headers" {
  zone_id = local.zone_id
  name    = "Cabecalhos de seguranca"
  kind    = "zone"
  phase   = "http_response_headers_transform"

  rules = [{
    ref         = "security_headers"
    description = "Cabecalhos de seguranca em todas as respostas do site"
    expression  = "(http.host eq \"${local.domain}\")"
    action      = "rewrite"
    action_parameters = {
      headers = {
        "Content-Security-Policy" = {
          operation = "set"
          value     = "frame-ancestors 'none'"
        }
        "Strict-Transport-Security" = {
          operation = "set"
          value     = "max-age=31536000; includeSubDomains"
        }
        "X-Content-Type-Options" = {
          operation = "set"
          value     = "nosniff"
        }
        "Referrer-Policy" = {
          operation = "set"
          value     = "no-referrer"
        }
        "Permissions-Policy" = {
          operation = "set"
          value     = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), hid=(), midi=(), bluetooth=(), browsing-topics=()"
        }
      }
    }
  }]
}
