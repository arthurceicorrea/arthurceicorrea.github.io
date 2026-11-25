# O domínio raiz aponta para o GitHub Pages (quatro endereços IPv4 e quatro IPv6), e o www para o
# endereço do repositório. TTL 1 é o "automático" da Cloudflare.

resource "cloudflare_dns_record" "apex_a" {
  for_each = toset(local.github_pages_ipv4)

  zone_id = local.zone_id
  name    = local.domain
  type    = "A"
  content = each.value
  ttl     = 1
  proxied = local.proxied
  comment = "GitHub Pages (Terraform)"
}

resource "cloudflare_dns_record" "apex_aaaa" {
  for_each = toset(local.github_pages_ipv6)

  zone_id = local.zone_id
  name    = local.domain
  type    = "AAAA"
  content = each.value
  ttl     = 1
  proxied = local.proxied
  comment = "GitHub Pages (Terraform)"
}

resource "cloudflare_dns_record" "www" {
  zone_id = local.zone_id
  name    = "www.${local.domain}"
  type    = "CNAME"
  content = "arthurceicorrea.github.io"
  ttl     = 1
  proxied = local.proxied
  comment = "Redireciona para o dominio raiz (Terraform)"
}

# Prova ao GitHub que o domínio é desta conta: só ela pode publicar um site do GitHub Pages nele.
# O valor é público por natureza (qualquer um lê o DNS); não é um segredo.
resource "cloudflare_dns_record" "github_pages_challenge" {
  zone_id = local.zone_id
  name    = "_github-pages-challenge-arthurceicorrea.${local.domain}"
  type    = "TXT"
  content = "\"e16d1f7bd81d0221019e1ed80ea7fb\""
  ttl     = 1
  comment = "Verificacao do dominio no GitHub Pages (Terraform)"
}
