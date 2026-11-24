// Comportamento da página: voltar ao topo, copiar o e-mail, seção atual no sumário e impressão.
// Carregado como módulo (type="module"): roda depois de o HTML ser lido, antes do evento
// DOMContentLoaded, e já em modo estrito. O idioma já foi definido por language.js.

var edition = document.querySelector(
  'main > [lang="' + document.documentElement.lang + '"]',
);
// botão de voltar ao topo: aparece quando a apresentação sai da tela
var button = document.querySelector(".totop");
var intro = edition && edition.querySelector(".intro");
if (button && intro && "IntersectionObserver" in window) {
  new IntersectionObserver(function (entries) {
    button.classList.toggle("on", !entries[0].isIntersecting);
  }).observe(intro);
  // recolhe-se enquanto o visitante rola para baixo lendo; volta quando ele para ou sobe
  var lastY = window.scrollY,
    rest;
  window.addEventListener(
    "scroll",
    function () {
      var y = window.scrollY;
      if (y > lastY + 4) {
        button.classList.add("down");
        clearTimeout(rest);
        rest = setTimeout(function () {
          button.classList.remove("down");
        }, 700);
      } else if (y < lastY - 4) {
        clearTimeout(rest);
        button.classList.remove("down");
      }
      lastY = y;
    },
    { passive: true },
  );
}
// botões de copiar o e-mail: aparecem só onde o navegador permite copiar
if (navigator.clipboard && window.isSecureContext) {
  var copies = document.querySelectorAll(".copy");
  for (var c = 0; c < copies.length; c++) {
    copies[c].hidden = false;
    copies[c].addEventListener("click", function () {
      var copy = this,
        status = this.nextElementSibling;
      navigator.clipboard
        .writeText(copy.getAttribute("data-copy"))
        .then(function () {
          copy.classList.add("done");
          status.textContent = copy.getAttribute("data-said");
          setTimeout(function () {
            copy.classList.remove("done");
            status.textContent = "";
          }, 2000);
        });
    });
  }
}
// sumário: marca a seção que está sendo lida (faixa no terço superior da tela)
var jumps = edition ? edition.querySelectorAll('.jump a[href^="#"]') : [];
if (jumps.length && "IntersectionObserver" in window) {
  var strip = edition.querySelector(".jump ul");
  var mark = function (id) {
    for (var j = 0; j < jumps.length; j++) {
      var on = jumps[j].getAttribute("href") === "#" + id;
      if (on) {
        jumps[j].setAttribute("aria-current", "location");
        // no celular, traz o link marcado para dentro da faixa
        var left = jumps[j].offsetLeft - strip.offsetLeft;
        if (
          left < strip.scrollLeft ||
          left + jumps[j].offsetWidth > strip.scrollLeft + strip.clientWidth
        )
          strip.scrollLeft = left - 16;
      } else jumps[j].removeAttribute("aria-current");
    }
  };
  var spy = new IntersectionObserver(
    function (entries) {
      for (var k = 0; k < entries.length; k++)
        if (entries[k].isIntersecting) mark(entries[k].target.id);
    },
    { rootMargin: "-30% 0px -65% 0px" },
  );
  for (var n = 0; n < jumps.length; n++) {
    var target = document.getElementById(
      jumps[n].getAttribute("href").slice(1),
    );
    if (target) spy.observe(target);
  }
  if (intro)
    new IntersectionObserver(
      function (entries) {
        if (entries[0].isIntersecting) mark("");
      },
      { rootMargin: "-30% 0px -65% 0px" },
    ).observe(intro);
}

// impressão ou PDF: abre os detalhes dos projetos e os fecha de novo depois
var opened = [];
window.addEventListener("beforeprint", function () {
  opened = [].slice.call(document.querySelectorAll("details:not([open])"));
  for (var i = 0; i < opened.length; i++) opened[i].open = true;
});
window.addEventListener("afterprint", function () {
  for (var i = 0; i < opened.length; i++) opened[i].open = false;
  opened = [];
});
