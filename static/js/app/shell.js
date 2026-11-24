// Shell MayaCorp: tema (claro/escuro/auto), menu recolhível, gaveta no celular,
// paleta de comandos (Ctrl+K) e toasts.
(function () {
  "use strict";
  var html = document.documentElement;

  // ---------- tema ----------
  var midia = window.matchMedia("(prefers-color-scheme: dark)");
  function temaAtual() { try { return localStorage.getItem("maya-tema-app") || "auto"; } catch (e) { return "auto"; } }
  function aplicarTema(tema) {
    try { localStorage.setItem("maya-tema-app", tema); } catch (e) {}
    html.classList.toggle("dark", tema === "escuro" || (tema === "auto" && midia.matches));
    document.querySelectorAll("[data-tema]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.tema === tema)); });
  }
  document.querySelectorAll("[data-tema]").forEach(function (b) {
    b.addEventListener("click", function () { aplicarTema(b.dataset.tema); });
  });
  midia.addEventListener("change", function () { if (temaAtual() === "auto") aplicarTema("auto"); });
  aplicarTema(temaAtual());

  // ---------- menu recolhível e gaveta ----------
  document.querySelectorAll("[data-recolher-menu]").forEach(function (b) {
    b.addEventListener("click", function () {
      var novo = !html.classList.contains("sb-recolhido");
      html.classList.toggle("sb-recolhido", novo);
      try { localStorage.setItem("sb-recolhido", novo ? "1" : "0"); } catch (e) {}
    });
  });
  var gaveta = document.getElementById("gaveta");
  var fundo = document.getElementById("gaveta-fundo");
  var abrirGaveta = document.querySelector("[data-abrir-gaveta]");
  function gavetaAberta(aberta) {
    if (!gaveta) return;
    gaveta.classList.toggle("hidden", !aberta);
    fundo.classList.toggle("hidden", !aberta);
    gaveta.setAttribute("aria-hidden", String(!aberta));
    if (abrirGaveta) abrirGaveta.setAttribute("aria-expanded", String(aberta));
    if (aberta) { var primeiro = gaveta.querySelector("a"); if (primeiro) primeiro.focus(); }
  }
  if (abrirGaveta) abrirGaveta.addEventListener("click", function () { gavetaAberta(true); });
  if (fundo) fundo.addEventListener("click", function () { gavetaAberta(false); });

  // ---------- toasts ----------
  document.querySelectorAll("[data-toast]").forEach(function (t, i) {
    var fechar = function () { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(function () { t.remove(); }, 300); };
    t.querySelector("[data-fechar-toast]").addEventListener("click", fechar);
    if (!t.classList.contains("toast-erro")) setTimeout(fechar, 5000 + i * 800);
  });

  // ---------- paleta de comandos ----------
  var paleta = document.getElementById("paleta");
  if (!paleta) return;
  var campo = document.getElementById("paleta-busca");
  var lista = document.getElementById("paleta-lista");
  var urlBusca = paleta.dataset.busca;
  var telas = Array.prototype.map.call(document.querySelectorAll("#sb a.sb-item"), function (a) {
    return { rotulo: a.textContent.trim(), url: a.getAttribute("href"), tipo: "Tela" };
  });
  var resultados = [];
  var sel = 0;
  var timer = null;

  function render() {
    lista.innerHTML = "";
    if (!resultados.length) {
      var vazio = document.createElement("li");
      vazio.className = "px-3 py-6 text-center text-sm suave";
      vazio.textContent = "Nada encontrado.";
      lista.appendChild(vazio);
      return;
    }
    resultados.forEach(function (r, i) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = r.url;
      a.className = "paleta-item";
      a.setAttribute("role", "option");
      a.setAttribute("aria-selected", String(i === sel));
      var tipo = document.createElement("span");
      tipo.className = "w-16 shrink-0 text-[11px] uppercase suave";
      tipo.textContent = r.tipo;
      var texto = document.createElement("span");
      texto.className = "min-w-0 flex-1 truncate";
      texto.textContent = r.rotulo;
      a.appendChild(tipo); a.appendChild(texto);
      if (r.detalhe) {
        var d = document.createElement("span");
        d.className = "truncate text-xs suave";
        d.textContent = r.detalhe;
        a.appendChild(d);
      }
      li.appendChild(a);
      lista.appendChild(li);
    });
  }

  function buscar() {
    var q = campo.value.trim().toLowerCase();
    var locais = telas.filter(function (t) { return !q || t.rotulo.toLowerCase().indexOf(q) >= 0; });
    resultados = locais;
    sel = 0;
    render();
    if (!urlBusca || q.length < 2) return;
    clearTimeout(timer);
    timer = setTimeout(function () {
      fetch(urlBusca + "?q=" + encodeURIComponent(q), { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : { itens: [] }; })
        .then(function (d) { resultados = locais.concat(d.itens || []); sel = 0; render(); })
        .catch(function () {});
    }, 200);
  }

  function abrir() {
    if (paleta.open) return;
    campo.value = "";
    paleta.showModal();
    buscar();
    campo.focus();
  }
  document.querySelectorAll("[data-abrir-paleta]").forEach(function (b) { b.addEventListener("click", abrir); });
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) { e.preventDefault(); abrir(); }
  });
  campo.addEventListener("input", buscar);
  campo.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, resultados.length - 1); render(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); render(); }
    else if (e.key === "Enter" && resultados[sel]) { e.preventDefault(); window.location.href = resultados[sel].url; }
    else if (e.key === "Escape") { e.preventDefault(); paleta.close(); }
  });
  paleta.addEventListener("click", function (e) { if (e.target === paleta) paleta.close(); });
})();
