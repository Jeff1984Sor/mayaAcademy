// Inicializa o player na página da aula (Django).
// Com matrícula: progresso salvo no servidor a cada bloco (N8) e conclusão registrada (XP).
// Sem matrícula (prévia do criador, aula de amostra): posição guardada só no navegador.
(function () {
  "use strict";
  var raiz = document.getElementById("player");
  var dados = JSON.parse(document.getElementById("dados-aula").textContent);
  var estado = JSON.parse(document.getElementById("estado-aula").textContent);
  var sair = raiz.dataset.sairUrl;
  var chave = "maya-aula-" + dados.aula.id;
  var inicio = Date.now();

  function csrf() {
    var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function segundos() {
    var s = Math.round((Date.now() - inicio) / 1000);
    inicio = Date.now();
    return s;
  }

  function enviar(url, corpo) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(corpo),
      keepalive: true,
    }).then(function (r) { return r.json().catch(function () { return {}; }); });
  }

  var salvo = {};
  if (!estado.salvar) {
    try { salvo = JSON.parse(localStorage.getItem(chave) || "{}"); } catch (e) { salvo = {}; }
  }

  window.MayaPlayer.montarAula(raiz, dados, {
    retomarEm: estado.salvar ? estado.retomar : (salvo.indice || 0),
    concluidos: estado.salvar ? estado.concluidos : (salvo.concluidos || []),
    mostrarSelos: raiz.dataset.previa === "1",
    aoProgresso: function (p) {
      if (estado.salvar) {
        enviar(estado.url_progresso, { indice: p.indice, concluidos: p.concluidos, resultados: p.resultados, segundos: segundos() });
      } else {
        try { localStorage.setItem(chave, JSON.stringify({ indice: p.indice, concluidos: p.concluidos })); } catch (e) {}
      }
    },
    aoConcluir: function (r) {
      if (!estado.salvar) {
        try { localStorage.removeItem(chave); } catch (e) {}
        return;
      }
      var todos = (dados.blocos || []).map(function (b) { return b.id; });
      // A página do curso mostra a próxima aula liberada e a prova.
      enviar(estado.url_concluir, { resultados: r.resultados, concluidos: todos, segundos: segundos() });
    },
    aoSair: sair ? function () { window.location.href = sair; } : null,
    rotuloSair: estado.salvar ? "Voltar ao curso" : "Voltar",
  });
})();
