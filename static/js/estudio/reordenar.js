// Reordenação por arrastar (HTML5 drag and drop) para listas com [data-reordenar].
// Listas com o mesmo data-grupo trocam itens entre si (ex.: mover aula de módulo).
(function () {
  "use strict";
  var csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  var arrastado = null;
  var origem = null;

  function itensDiretos(lista) {
    return Array.prototype.filter.call(lista.children, function (li) { return li.hasAttribute("data-id"); });
  }

  function salvar(lista) {
    var ids = itensDiretos(lista).map(function (li) { return li.dataset.id; });
    return fetch(lista.dataset.reordenar, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf) },
      body: JSON.stringify({ ids: ids, pai: lista.dataset.pai }),
    }).then(function (r) {
      if (!r.ok) throw new Error("falha");
      renumerar(lista);
    }).catch(function () {
      alert("Não foi possível salvar a nova ordem. Recarregue a página.");
    });
  }

  function renumerar(lista) {
    itensDiretos(lista).forEach(function (li, i) {
      var n = li.querySelector(".rounded-full.bg-maya-100");
      if (n && lista.dataset.reordenar.indexOf("blocos") >= 0) n.textContent = String(i + 1);
    });
  }

  document.querySelectorAll("[data-reordenar]").forEach(function (lista) {
    lista.addEventListener("dragstart", function (e) {
      var li = e.target.closest("[data-id]");
      if (!li || li.parentElement !== lista) return;
      e.stopPropagation();
      arrastado = li; origem = lista;
      li.classList.add("arrastando");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", li.dataset.id);
    });
    lista.addEventListener("dragend", function () {
      if (arrastado) arrastado.classList.remove("arrastando");
    });
    lista.addEventListener("dragover", function (e) {
      if (!arrastado) return;
      var mesmoGrupo = lista === origem || (lista.dataset.grupo && lista.dataset.grupo === origem.dataset.grupo);
      if (!mesmoGrupo) return;
      e.preventDefault();
      e.stopPropagation();
      var alvo = e.target.closest("[data-id]");
      if (alvo && alvo.parentElement === lista && alvo !== arrastado) {
        var r = alvo.getBoundingClientRect();
        var depois = e.clientY > r.top + r.height / 2;
        lista.insertBefore(arrastado, depois ? alvo.nextSibling : alvo);
      } else if (!alvo || alvo.parentElement !== lista) {
        if (arrastado.parentElement !== lista) lista.appendChild(arrastado);
      }
    });
    lista.addEventListener("drop", function (e) {
      if (!arrastado) return;
      e.preventDefault();
      e.stopPropagation();
      var destino = arrastado.parentElement;
      var pendentes = [salvar(destino)];
      if (origem && origem !== destino) pendentes.push(salvar(origem));
      arrastado = null; origem = null;
      Promise.all(pendentes);
    });
  });
})();
