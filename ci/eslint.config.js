// ESLint: verifica o JavaScript de src/js/ com as regras recomendadas (@eslint/js).
// Uso: make lint (ou ci/node_modules/.bin/eslint --config ci/eslint.config.js src/js), a partir da
// raiz do repositório: os caminhos abaixo são relativos a ela.
const js = require('@eslint/js');
const globals = require('globals');

module.exports = [
  {
    files: ['src/js/**/*.js'],
    rules: js.configs.recommended.rules,
    languageOptions: { ecmaVersion: 'latest', globals: globals.browser },
  },
  // language.js é um script comum, carregado no <head> sem defer, antes da primeira pintura.
  { files: ['src/js/language.js'], languageOptions: { sourceType: 'script' } },
  // page.js é carregado como módulo (type="module").
  { files: ['src/js/page.js'], languageOptions: { sourceType: 'module' } },
];
