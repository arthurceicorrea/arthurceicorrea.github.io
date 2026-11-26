# Infrastructure: arthurceicorrea.dev on Cloudflare

Terraform for the domain `arthurceicorrea.dev`, whose DNS is at Cloudflare. The site itself is still served by GitHub Pages; Cloudflare answers for the name and, once the proxy is on, adds the security headers. See [ADR 10](../docs/adr/0010-cloudflare-in-front-of-github-pages-managed-by-terraform.md).

## What is managed here

| File | What it holds |
|---|---|
| `versions.tf` | exact Terraform and provider versions; the state in the R2 bucket `arthurceicorrea-tfstate` |
| `locals.tf` | domain, zone, GitHub Pages addresses, and `proxied`, the switch for the Cloudflare proxy |
| `dns.tf` | the apex to GitHub Pages (4 A, 4 AAAA), `www` to `arthurceicorrea.github.io`, and the TXT that verifies the domain with GitHub |
| `email.tf` | null MX, SPF `-all` and DMARC `p=reject`: the domain sends and receives no e-mail, so nobody can send mail in its name |
| `rules.tf` | the `www` → apex redirect and the security headers (both act only with the proxy on) |
| `settings.tf` | SSL Full (strict), HTTPS only, TLS 1.2 or later; off: everything that rewrites the HTML or injects scripts |

Not managed here, done by hand: buying the domain, DNSSEC (DNS → Settings), the API tokens and R2 keys, the GitHub secrets, and the custom domain in the repository's Settings → Pages.

## Credentials

Two of each, so the pipeline can only read ([ADR 10](../docs/adr/0010-cloudflare-in-front-of-github-pages-managed-by-terraform.md)):

| Used by | Cloudflare token (`CLOUDFLARE_API_TOKEN`) | R2 key for the state (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) |
|---|---|---|
| the pipeline, `terraform plan` | `terraform-ci-read`: six permissions, Read, this zone only; repository secret `CLOUDFLARE_API_TOKEN` | `tfstate-ci-read`: Object Read only, this bucket only; secrets `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` |
| Arthur, `terraform apply` | `terraform-arthur-edit`: the same six, Edit; only in his password manager | `tfstate-arthur-write`: Object Read & Write, this bucket only; only in his password manager |

The six permissions, all on the zone `arthurceicorrea.dev`: Zone, DNS, Zone Settings, Zone Transform Rules, Dynamic URL Redirects, Bot Management.

Never write a token or key to a file in this folder. Set them as environment variables for the session only.

## Applying a change

Changes reach Cloudflare in two moves: the pull request shows the plan (workflow **Infraestrutura**, job **Terraform**, in the run summary), and after the merge Arthur applies it from his machine, on an up-to-date `main`.

Requires Terraform 1.17.2 exactly (`versions.tf` refuses any other version).

PowerShell (`Read-Host -AsSecureString` hides what you type). Run the three `$env:` lines one at a time: paste the command alone, press Enter, and paste the value only when the prompt appears. A value pasted on the command line itself is not read, and it is shown on screen.

```powershell
cd infra
$env:CLOUDFLARE_API_TOKEN  = [Net.NetworkCredential]::new('', (Read-Host -AsSecureString 'terraform-arthur-edit')).Password
$env:AWS_ACCESS_KEY_ID     = [Net.NetworkCredential]::new('', (Read-Host -AsSecureString 'tfstate-arthur-write: Access Key ID')).Password
$env:AWS_SECRET_ACCESS_KEY = [Net.NetworkCredential]::new('', (Read-Host -AsSecureString 'tfstate-arthur-write: Secret Access Key')).Password
# check without showing the values: last four characters of the token (as in the dashboard), 32, 64, active
$t = $env:CLOUDFLARE_API_TOKEN; $t.Substring($t.Length - 4); $env:AWS_ACCESS_KEY_ID.Length; $env:AWS_SECRET_ACCESS_KEY.Length
(Invoke-RestMethod https://api.cloudflare.com/client/v4/user/tokens/verify -Headers @{ Authorization = "Bearer $env:CLOUDFLARE_API_TOKEN" }).result.status
terraform init
terraform plan "-out=apply.tfplan"    # must show the same changes as the pull request; the quotes stop PowerShell splitting the argument at the dot
terraform apply "apply.tfplan"
Remove-Item Env:CLOUDFLARE_API_TOKEN, Env:AWS_ACCESS_KEY_ID, Env:AWS_SECRET_ACCESS_KEY, apply.tfplan
```

Only three values go in: the `terraform-arthur-edit` token (starts with `cfut`), and the R2 key's Access Key ID (32 hexadecimal characters) and Secret Access Key (64). The R2 key's own token value, which also starts with `cfut`, is not used here.

Bash (`read -s` hides what you type):

```sh
cd infra
read -rsp 'terraform-arthur-edit: ' CLOUDFLARE_API_TOKEN; echo; export CLOUDFLARE_API_TOKEN
read -rsp 'Access Key ID: ' AWS_ACCESS_KEY_ID; echo; export AWS_ACCESS_KEY_ID
read -rsp 'Secret Access Key: ' AWS_SECRET_ACCESS_KEY; echo; export AWS_SECRET_ACCESS_KEY
terraform init
terraform plan -out=apply.tfplan
terraform apply apply.tfplan
unset CLOUDFLARE_API_TOKEN AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY; rm apply.tfplan
```

If the plan on your machine differs from the one in the pull request, stop: someone changed something in the dashboard, or `main` moved. Find out why before applying.

## First time: putting the domain in the air

1. Merge the pull request that creates `infra/`, then apply as above. The first plan creates every resource.
2. On GitHub, **github.com/settings/pages** (your profile, not the repository): next to `arthurceicorrea.dev`, click **Verify**. It may take a few minutes for the TXT to be seen.
3. In the repository, **Settings → Pages → Custom domain**: type `arthurceicorrea.dev` and save. A `CNAME` file is not needed: the site is published by GitHub Actions, and GitHub reads the domain from this setting.
4. Wait until GitHub has issued the certificate (the page shows it), then tick **Enforce HTTPS**.
5. Check: `https://arthurceicorrea.dev/` opens the site, `https://www.arthurceicorrea.dev/` goes to it, and `https://arthurceicorrea.github.io/` now redirects to it.

6. Turn on the proxy (`proxied = true` in `locals.tf`), so the headers and the Cloudflare redirect take effect. Before applying, check in the dashboard, **SSL/TLS → Edge Certificates**, that the **Universal** certificate is **Active**: it is the one visitors see once the proxy is on.

Then a last pull request changes the site's address everywhere in the repository and makes the live check verify the headers.

## Renewing a token

`terraform-ci-read` expires a year after it was created (around 2027-11-25), `terraform-arthur-edit` after 90 days. Create a new one with the same six permissions on the same zone, replace the repository secret (for the pipeline's token) or your password manager entry (for yours), and delete the old token.
