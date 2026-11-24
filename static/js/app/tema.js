// Carregado no <head> (síncrono): aplica tema e menu recolhido antes da pintura.
(function () {
  var html = document.documentElement;
  var tema = "auto";
  try { tema = localStorage.getItem("maya-tema-app") || "auto"; } catch (e) {}
  var escuro = tema === "escuro" || (tema === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  html.classList.toggle("dark", escuro);
  try { if (localStorage.getItem("sb-recolhido") === "1") html.classList.add("sb-recolhido"); } catch (e) {}
})();
