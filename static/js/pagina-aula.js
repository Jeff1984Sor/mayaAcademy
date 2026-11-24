// Inicializa o player na página da aula (Django). Progresso e conclusão (N8)
// entram na F3; por enquanto a posição fica no navegador para retomar.
(function () {
  "use strict";
  var raiz = document.getElementById("player");
  var dados = JSON.parse(document.getElementById("dados-aula").textContent);
  var chave = "maya-aula-" + dados.aula.id;
  var salvo = {};
  try { salvo = JSON.parse(localStorage.getItem(chave) || "{}"); } catch (e) { salvo = {}; }
  var sair = raiz.dataset.sairUrl;

  window.MayaPlayer.montarAula(raiz, dados, {
    retomarEm: salvo.indice || 0,
    concluidos: salvo.concluidos || [],
    mostrarSelos: raiz.dataset.previa === "1",
    aoProgresso: function (p) {
      try { localStorage.setItem(chave, JSON.stringify({ indice: p.indice, concluidos: p.concluidos })); } catch (e) {}
    },
    aoConcluir: function () {
      try { localStorage.removeItem(chave); } catch (e) {}
    },
    aoSair: sair ? function () { window.location.href = sair; } : null,
    rotuloSair: "Voltar",
  });
})();
