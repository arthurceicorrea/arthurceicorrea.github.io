locals {
  domain  = "arthurceicorrea.dev"
  zone_id = "238d98d094ce6bb5abd277b62568055d"

  # Proxy da Cloudflare. Começa desligado: o GitHub só emite o certificado do domínio quando o DNS aponta
  # direto para os IPs dele. Depois do certificado emitido e do "Enforce HTTPS" marcado no GitHub, um
  # pull request à parte liga o proxy, e só então valem os cabeçalhos de segurança e o redirecionamento
  # do www feito pela Cloudflare (até lá, o próprio GitHub Pages leva o www para o domínio raiz).
  proxied = false

  # Endereços do GitHub Pages para um domínio raiz, segundo a documentação do GitHub.
  github_pages_ipv4 = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"]
  github_pages_ipv6 = ["2606:50c0:8000::153", "2606:50c0:8001::153", "2606:50c0:8002::153", "2606:50c0:8003::153"]
}
