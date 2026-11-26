locals {
  domain  = "arthurceicorrea.dev"
  zone_id = "238d98d094ce6bb5abd277b62568055d"

  # Proxy da Cloudflare. Começou desligado, porque o GitHub só emite o certificado do domínio quando o DNS
  # aponta direto para os IPs dele. Com o certificado emitido e o "Enforce HTTPS" marcado (25/11/2026),
  # o proxy foi ligado: os visitantes falam com a Cloudflare, que acrescenta os cabeçalhos de segurança,
  # redireciona o www e busca as páginas no GitHub Pages por HTTPS, conferindo o certificado dele.
  proxied = true

  # Endereços do GitHub Pages para um domínio raiz, segundo a documentação do GitHub.
  github_pages_ipv4 = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"]
  github_pages_ipv6 = ["2606:50c0:8000::153", "2606:50c0:8001::153", "2606:50c0:8002::153", "2606:50c0:8003::153"]
}
