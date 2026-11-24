// Escolha do idioma. Carregado no <head> sem defer: define o idioma antes da primeira
// pintura, para o visitante nunca ver o idioma errado. Usado também pela página 404.
(function () {
  'use strict';

  // Código de cada idioma (pastas /pt/, /en/... e ?lang=) e etiqueta lang da edição.
  var TAGS = { pt: 'pt-BR', en: 'en', es: 'es', it: 'it' };
  var root = document.documentElement;

  // "pt-BR" -> "pt"; devolve null se não for um dos quatro idiomas.
  function pick(value) {
    var code = String(value || '').toLowerCase().split(/[-_]/)[0];
    return TAGS.hasOwnProperty(code) ? code : null;
  }

  function fromUrl() {
    var match = /[?&]lang=([^&#]*)/.exec(location.search);
    return match ? pick(match[1]) : null;
  }

  function fromBrowser() {
    var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language];
    for (var i = 0; i < list.length; i++) {
      var code = pick(list[i]);
      if (code) return code;
    }
    return null;
  }

  // País deduzido do fuso horário do aparelho, sem nenhuma consulta externa.
  // Só entram fusos de países com língua clara; nos demais vale o idioma do navegador.
  var ZONES = {
    pt: /^(America\/(Sao_Paulo|Araguaina|Bahia|Belem|Boa_Vista|Campo_Grande|Cuiaba|Eirunepe|Fortaleza|Maceio|Manaus|Noronha|Porto_Velho|Recife|Rio_Branco|Santarem)|Brazil\/.+|Europe\/Lisbon|Portugal|Atlantic\/(Azores|Madeira|Cape_Verde)|Africa\/(Luanda|Maputo|Bissau|Sao_Tome))$/,
    it: /^(Europe\/(Rome|Vatican|San_Marino)|Italy)$/,
    es: /^(Europe\/Madrid|Africa\/(Ceuta|Malabo)|Atlantic\/Canary|America\/(Argentina\/.+|Buenos_Aires|Catamarca|Cordoba|Jujuy|Mendoza|Mexico_City|Cancun|Merida|Monterrey|Matamoros|Chihuahua|Ciudad_Juarez|Ojinaga|Mazatlan|Bahia_Banderas|Hermosillo|Tijuana|Bogota|Lima|Santiago|Punta_Arenas|Caracas|Montevideo|Asuncion|La_Paz|Guayaquil|Guatemala|El_Salvador|Tegucigalpa|Managua|Costa_Rica|Panama|Havana|Santo_Domingo)|Pacific\/(Easter|Galapagos)|Chile\/.+|Mexico\/.+|Cuba)$/
  };

  function fromZone() {
    try {
      var zone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      for (var code in ZONES) {
        if (ZONES.hasOwnProperty(code) && ZONES[code].test(zone)) return code;
      }
    } catch (error) { /* navegador sem Intl: segue para o idioma do navegador */ }
    return null;
  }

  // As páginas de cada idioma trazem o idioma fixo em data-lang. Na página inicial, a ordem é:
  // parâmetro da URL, país (pelo fuso horário), idioma do navegador, inglês.
  var current = pick(root.getAttribute('data-lang')) || fromUrl() || fromZone() || fromBrowser() || 'en';
  root.lang = TAGS[current]; // definido antes de o corpo ser lido: o idioma errado nunca chega a aparecer

  document.addEventListener('DOMContentLoaded', function () {
    var edition = document.querySelector('main > [lang="' + TAGS[current] + '"]');
    var description = document.querySelector('meta[name="description"]');
    if (edition) {
      document.title = edition.getAttribute('data-title');
      if (description) description.setAttribute('content', edition.getAttribute('data-desc'));
    }
    // seletor de idioma: nome para leitores de tela e idioma ativo marcado
    var nav = document.querySelector('.langs');
    if (nav) { // a página 404 não tem seletor de idioma
      nav.setAttribute('aria-label', nav.getAttribute('data-' + current));
      var links = nav.querySelectorAll('a');
      for (var i = 0; i < links.length; i++) {
        if (links[i].getAttribute('data-lang') === current) links[i].setAttribute('aria-current', 'true');
        else links[i].removeAttribute('aria-current');
      }
    }
  });
})();
