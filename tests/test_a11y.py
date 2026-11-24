"""Auditoria automática de acessibilidade (axe-core) do site montado (antes: ci/a11y.py).

Abre cada página num Chrome sem interface, no celular e em tela larga, e roda o axe com as
regras WCAG 2.0, 2.1 e 2.2, níveis A e AA. Qualquer violação reprova o teste. As recomendações
de boas práticas do axe não reprovam: aparecem num resumo no fim da execução.

Uso: make build && python -m pytest tests/test_a11y.py
(o axe.min.js vem do pacote npm axe-core, instalado por make setup; outro caminho: --axe ARQUIVO)
"""
import pytest

PAGES = ['?lang=pt', '?lang=en', '?lang=es', '?lang=it', 'pt/', 'en/', 'es/', 'it/', '404.html']
WIDTHS = {360: 740, 1440: 900}
WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']


@pytest.mark.parametrize('path, width', [pytest.param(p, w, id='/%s-%dpx' % (p, w)) for p in PAGES for w in WIDTHS])
def test_no_wcag_a_or_aa_violation(browser, site_url, axe, axe_advice, path, width):
    # bypass_csp só neste teste: a política do site bloquearia o script do axe injetado
    ctx = browser.new_context(viewport={'width': width, 'height': WIDTHS[width]}, timezone_id='UTC', bypass_csp=True)
    page = ctx.new_page()
    page.goto(site_url + path)
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    page.evaluate(axe)
    result = page.evaluate("""async () => {
      const run = await axe.run(document, { resultTypes: ['violations'] });
      return run.violations.map(v => ({ id: v.id, impact: v.impact, tags: v.tags, help: v.help,
                                        nodes: v.nodes.map(n => n.target.join(' ')).slice(0, 3) }));
    }""")
    ctx.close()
    violations = []
    for v in result:
        if set(v['tags']) & set(WCAG):
            violations.append('%s [%s] %s -> %s' % (v['id'], v['impact'], v['help'], v['nodes']))
        else:
            axe_advice.add('%s: %s' % (v['id'], v['help']))
    assert not violations, '/%s a %d px: violações WCAG A/AA:\n  %s' % (path, width, '\n  '.join(violations))
