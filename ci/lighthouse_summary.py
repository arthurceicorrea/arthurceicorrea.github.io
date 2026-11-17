"""Resume as notas do Lighthouse numa tabela, no resumo da execução do GitHub Actions.

Lê lighthouse-report/manifest.json (gerado por lhci com upload para o sistema de
arquivos) e escreve a tabela em $GITHUB_STEP_SUMMARY, ou na saída padrão.

Uso: python ci/lighthouse_summary.py lighthouse-report
"""
import json
import os
import sys
from urllib.parse import urlparse

manifest = json.load(open(os.path.join(sys.argv[1], 'manifest.json'), encoding='utf-8'))
columns = [('performance', 'Desempenho'), ('accessibility', 'Acessibilidade'),
           ('best-practices', 'Boas práticas'), ('seo', 'SEO')]
lines = ['### Notas do Lighthouse (celular simulado)', '',
         '| Página | ' + ' | '.join(label for _, label in columns) + ' |',
         '|---|' + '---:|' * len(columns)]
for entry in manifest:
    if not entry.get('isRepresentativeRun', True):
        continue
    path = urlparse(entry['url']).path or '/'
    scores = entry.get('summary', {})
    lines.append('| `%s` | ' % path + ' | '.join(
        '%d' % round(scores[key] * 100) if scores.get(key) is not None else '—' for key, _ in columns) + ' |')
# auditorias que tiram pontos, para saber o que melhorar
details = []
for entry in manifest:
    report_path = entry.get('jsonPath')
    if not report_path or not os.path.isfile(report_path):
        continue
    report = json.load(open(report_path, encoding='utf-8'))
    path = urlparse(entry['url']).path or '/'
    for key, label in columns:
        for ref in report['categories'][key]['auditRefs']:
            audit = report['audits'][ref['id']]
            if ref['weight'] > 0 and audit.get('score') is not None and audit['score'] < 0.9:
                note = audit.get('displayValue') or audit.get('explanation') or ''
                details.append('| `%s` | %s | %s | %s |' % (path, label, audit['title'], str(note).replace('|', '/')[:120]))
if details:
    lines += ['', '#### O que tira pontos', '', '| Página | Categoria | Auditoria | Detalhe |', '|---|---|---|---|'] + details
lines += ['', 'Os relatórios completos ficam no artefato **lighthouse-report** desta execução.']
text = '\n'.join(lines) + '\n'
target = os.environ.get('GITHUB_STEP_SUMMARY')
if target:
    open(target, 'a', encoding='utf-8').write(text)
print(text)
