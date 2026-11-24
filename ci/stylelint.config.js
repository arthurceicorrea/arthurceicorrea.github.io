// Stylelint: verifica o CSS de src/css/ com a configuração padrão (stylelint-config-standard).
// Uso: make lint (ou ci/node_modules/.bin/stylelint --config ci/stylelint.config.js "src/css/**/*.css")
//
// Duas regras ajustadas, porque a configuração padrão pediria uma sintaxe que alguns navegadores
// que o site atende não entendem:
module.exports = {
  extends: ['stylelint-config-standard'],
  rules: {
    // Prefixos mantidos de propósito:
    // - -webkit-text-size-adjust: o Safari do iPhone só entende a versão com prefixo, até nas versões
    //   atuais; sem ela, o iPhone aumenta o texto sozinho quando a tela é girada.
    // - -webkit-mask-image: o Chrome anterior ao 120 (dezembro de 2023) só entende a versão com
    //   prefixo; ela faz o esfumado na borda do sumário rolável do celular.
    'property-no-vendor-prefix': [true, { ignoreProperties: ['-webkit-text-size-adjust', '-webkit-mask-image'] }],
    // (min-width: ...) em vez de (width >= ...): navegadores anteriores ao Safari 16.4 (março de 2023)
    // e ao Chrome 104 ignoram a media query inteira na sintaxe nova, inclusive a do sumário no celular.
    'media-feature-range-notation': 'prefix',
  },
};
