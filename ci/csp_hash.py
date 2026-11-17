"""Recalcula os hashes sha256 da política de segurança (CSP) de uma página.

Use depois de alterar o bloco de estilos ou o bloco de script de index.html ou 404.html.
Uso: python ci/csp_hash.py index.html [--check]
"""
import base64
import hashlib
import re
import sys

path = sys.argv[1]
raw = open(path, encoding='utf-8').read()


def inner(tag):
    found = re.findall(r'^<%s>(.*?)</%s>$' % (tag, tag), raw, flags=re.S | re.M)
    assert len(found) == 1, 'esperava um único bloco <%s>' % tag
    return found[0]


def sha256(text):
    return 'sha256-' + base64.b64encode(hashlib.sha256(text.encode('utf-8')).digest()).decode()


style, script = sha256(inner('style')), sha256(inner('script'))
match = re.search(r"style-src '(sha256-[^']*)'; script-src '(sha256-[^']*)'", raw)
assert match, 'meta CSP não encontrada'
if '--check' in sys.argv:
    ok = (match.group(1), match.group(2)) == (style, script)
    print('hashes conferem' if ok else 'hashes divergem: style %s, script %s' % (style, script))
    sys.exit(0 if ok else 1)
raw = raw[:match.start()] + "style-src '%s'; script-src '%s'" % (style, script) + raw[match.end():]
open(path, 'w', encoding='utf-8', newline='\n').write(raw)
print('CSP atualizada: style %s, script %s' % (style, script))
