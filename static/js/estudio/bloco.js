// Editor de bloco: monta o formulário do schema e atualiza a prévia ao vivo.
(function () {
  "use strict";
  var form = document.getElementById("form-bloco");
  if (!form) return;
  var iframe = document.getElementById("previa");
  var status = document.getElementById("previa-status");
  var textarea = form.querySelector("[name=config]");
  var tipo = form.querySelector("[name=tipo]");
  var schemas = JSON.parse(document.getElementById("schemas-blocos").textContent);

  // Frases numeradas do roteiro — mesma divisão do backend (cursos/roteiro.py).
  var roteiro = form.querySelector("[name=roteiro]");
  var listaFrases = document.querySelector("#frases-numeradas ol");
  function numerarFrases() {
    if (!listaFrases) return;
    listaFrases.innerHTML = "";
    var personagem = "narrador";
    var falas = [];
    var atual = null;
    roteiro.value.split(/\r?\n/).forEach(function (linha) {
      linha = linha.trim();
      if (!linha) { atual = null; return; }
      var m = linha.match(/^@([a-z0-9_-]+)\s*:\s*(.*)$/i);
      if (m) { personagem = m[1].toLowerCase(); linha = m[2].trim(); atual = null; if (!linha) return; }
      if (!atual) { atual = { p: personagem, t: "" }; falas.push(atual); }
      atual.t = (atual.t + " " + linha).trim();
    });
    var n = 0;
    falas.forEach(function (f) {
      f.t.split(/(?<=[.!?…])\s+(?=\S)/).forEach(function (frase) {
        if (!frase.trim()) return;
        var li = document.createElement("li");
        li.className = "font-mono text-xs";
        li.textContent = n + " · @" + f.p + ": " + frase.trim();
        listaFrases.appendChild(li);
        n += 1;
      });
    });
    if (!n) listaFrases.innerHTML = '<li class="text-xs suave">Sem narração.</li>';
  }
  roteiro.addEventListener("input", numerarFrases);
  numerarFrases();

  window.MayaEditorSchema.montar(document.getElementById("editor-schema"), textarea, schemas, tipo);

  var timer = null;
  var pedido = 0;
  function atualizar() {
    clearTimeout(timer);
    status.textContent = "atualizando…";
    timer = setTimeout(function () {
      var meu = ++pedido;
      fetch(form.dataset.previa, { method: "POST", body: new FormData(form), credentials: "same-origin" })
        .then(function (r) { return r.text(); })
        .then(function (html) {
          if (meu !== pedido) return;
          iframe.srcdoc = html;
          status.textContent = "atualizado";
        })
        .catch(function () { status.textContent = "falha ao atualizar a prévia"; });
    }, 700);
  }
  form.addEventListener("input", atualizar);
  form.addEventListener("change", atualizar);
  form.addEventListener("config-alterada", atualizar);
  atualizar();

  var sujo = false;
  form.addEventListener("input", function () { sujo = true; });
  form.addEventListener("config-alterada", function () { sujo = true; });
  form.addEventListener("submit", function () { sujo = false; });
  window.addEventListener("beforeunload", function (e) { if (sujo) { e.preventDefault(); e.returnValue = ""; } });
})();
