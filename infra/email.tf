# O domínio não envia nem recebe e-mail. Estes três registros dizem isso ao mundo, para que ninguém
# consiga mandar mensagens falsas em nome de @arthurceicorrea.dev: Gmail, Outlook e os demais recusam.

# MX nulo (RFC 7505): o domínio não recebe e-mail.
resource "cloudflare_dns_record" "null_mx" {
  zone_id  = local.zone_id
  name     = local.domain
  type     = "MX"
  content  = "."
  priority = 0
  ttl      = 1
  comment  = "Dominio sem e-mail (Terraform)"
}

# SPF: nenhum servidor está autorizado a enviar e-mail pelo domínio.
resource "cloudflare_dns_record" "spf" {
  zone_id = local.zone_id
  name    = local.domain
  type    = "TXT"
  content = "\"v=spf1 -all\""
  ttl     = 1
  comment = "Dominio sem e-mail (Terraform)"
}

# DMARC: rejeitar toda mensagem que diga vir do domínio, também dos subdomínios. Sem endereço de
# relatórios (rua), para não mandar dados a ninguém.
resource "cloudflare_dns_record" "dmarc" {
  zone_id = local.zone_id
  name    = "_dmarc.${local.domain}"
  type    = "TXT"
  content = "\"v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s\""
  ttl     = 1
  comment = "Dominio sem e-mail (Terraform)"
}
