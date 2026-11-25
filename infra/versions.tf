# Versões exatas do Terraform e do provedor da Cloudflare, como as demais ferramentas do repositório.
# O .terraform.lock.hcl, versionado ao lado, prende também os hashes do provedor baixado.
terraform {
  required_version = "= 1.17.2"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "= 5.29.0"
    }
  }

  # O estado (o registro do que já existe na Cloudflare) fica num bucket R2 da própria conta, pela API
  # compatível com S3. As verificações abaixo são próprias da AWS e não se aplicam ao R2.
  # As credenciais vêm de AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY: no pipeline, a chave só de leitura;
  # na máquina de Arthur, a chave de escrita. Nunca num arquivo.
  backend "s3" {
    bucket = "arthurceicorrea-tfstate"
    key    = "site/terraform.tfstate"
    region = "auto"
    endpoints = {
      s3 = "https://3cf0e51a420453b823441b187b412db5.r2.cloudflarestorage.com"
    }
    use_path_style              = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
    # trava o estado durante o apply, para duas execuções não o gravarem ao mesmo tempo
    use_lockfile = true
  }
}

# O token vem de CLOUDFLARE_API_TOKEN: no pipeline, o token só de leitura; na máquina de Arthur, o de edição.
provider "cloudflare" {}
