/* Casca do curso baixado: menu de aulas, liberação em ordem, progresso e SCORM 1.2.
   Script clássico (sem módulos) para funcionar em file:// e dentro de LMS. */
(function () {
  "use strict";
  var CURSO = window.MAYA_CURSO;
  var app = document.getElementById("app");
  var chave = "maya-pacote-" + CURSO.curso.slug + "-v" + CURSO.curso.versao;

  // ---------- SCORM 1.2 (opcional: só se o LMS fornecer a API) ----------
  function acharAPI(win) {
    var tentativas = 0;
    while (win && tentativas < 10) {
      if (win.API) return win.API;
      if (win.parent === win) break;
      win = win.parent; tentativas++;
    }
    try { if (window.opener && window.opener.API) return window.opener.API; } catch (e) {}
    return null;
  }
  var API = null;
  try { API = acharAPI(window); } catch (e) { API = null; }
  var scormAtivo = false;
  if (API) {
    try {
      var r = API.LMSInitialize("");
      scormAtivo = r === "true" || r === true;
    } catch (e) { scormAtivo = false; }
  }
  function scormSet(k, v) { if (scormAtivo) { try { API.LMSSetValue(k, String(v)); } catch (e) {} } }
  function scormGet(k) { if (!scormAtivo) return ""; try { return API.LMSGetValue(k) || ""; } catch (e) { return ""; } }
  function scormCommit() { if (scormAtivo) { try { API.LMSCommit(""); } catch (e) {} } }
  window.addEventListener("beforeunload", function () {
    if (scormAtivo) { try { API.LMSCommit(""); API.LMSFinish(""); } catch (e) {} }
  });

  // ---------- estado ----------
  var aulas = [];
  CURSO.modulos.forEach(function (m, mi) {
    m.aulas.forEach(function (a) { aulas.push({ modulo: mi, dados: a }); });
  });

  function carregar() {
    var bruto = scormGet("cmi.suspend_data") || localStorage.getItem(chave) || "";
    try { return JSON.parse(bruto) || {}; } catch (e) { return {}; }
  }
  var estado = carregar();
  estado.concluidas = estado.concluidas || {};
  estado.blocos = estado.blocos || {};
  estado.notas = estado.notas || {};

  function salvar() {
    var texto = JSON.stringify(estado);
    try { localStorage.setItem(chave, texto); } catch (e) {}
    if (texto.length < 4000) scormSet("cmi.suspend_data", texto); // limite do SCORM 1.2: 4096
    var feitas = aulas.filter(function (a) { return estado.concluidas[a.dados.aula.id]; }).length;
    var notas = Object.keys(estado.notas).map(function (k) { return estado.notas[k]; });
    if (notas.length) {
      var media = Math.round(notas.reduce(function (s, n) { return s + n; }, 0) / notas.length);
      scormSet("cmi.core.score.min", 0); scormSet("cmi.core.score.max", 100); scormSet("cmi.core.score.raw", media);
    }
    scormSet("cmi.core.lesson_status", feitas === aulas.length ? "completed" : "incomplete");
    scormCommit();
  }
  if (scormAtivo && scormGet("cmi.core.lesson_status") === "not attempted") {
    scormSet("cmi.core.lesson_status", "incomplete"); scormCommit();
  }

  function liberada(i) { return i === 0 || Boolean(estado.concluidas[aulas[i - 1].dados.aula.id]); }

  // ---------- telas ----------
  document.documentElement.style.setProperty("--curso-primaria", CURSO.curso.cor_primaria);
  document.documentElement.style.setProperty("--curso-secundaria", CURSO.curso.cor_secundaria);
  app.classList.add("pacote-raiz");

  function menu() {
    var feitas = aulas.filter(function (a) { return estado.concluidas[a.dados.aula.id]; }).length;
    var pct = aulas.length ? Math.round((feitas / aulas.length) * 100) : 0;
    var html = '<div class="pacote"><header class="pacote-topo"><h1></h1><p class="pacote-sub"></p>' +
      '<div class="pacote-barra" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + pct + '"><span style="width:' + pct + '%"></span></div>' +
      '<p class="pacote-status">' + feitas + " de " + aulas.length + " aulas concluídas</p></header><main></main></div>";
    app.innerHTML = html;
    app.querySelector("h1").textContent = CURSO.curso.titulo;
    app.querySelector(".pacote-sub").textContent = CURSO.curso.subtitulo || "";
    var main = app.querySelector("main");
    var indice = 0;
    CURSO.modulos.forEach(function (m) {
      var sec = document.createElement("section");
      sec.className = "pacote-modulo";
      var h = document.createElement("h2"); h.textContent = m.titulo; sec.appendChild(h);
      var ol = document.createElement("ol");
      m.aulas.forEach(function (a) {
        var i = indice++;
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        var feita = Boolean(estado.concluidas[a.aula.id]);
        var aberta = liberada(i);
        btn.className = "pacote-aula" + (feita ? " feita" : "") + (aberta ? "" : " bloqueada");
        btn.disabled = !aberta;
        btn.innerHTML = '<span class="pacote-icone" aria-hidden="true">' + (feita ? "✓" : aberta ? "▶" : "🔒") + "</span><span></span>";
        btn.lastChild.textContent = a.aula.titulo;
        btn.setAttribute("aria-label", a.aula.titulo + (feita ? " (concluída)" : aberta ? "" : " (bloqueada: conclua a aula anterior)"));
        btn.addEventListener("click", function () { abrir(i); });
        li.appendChild(btn); ol.appendChild(li);
      });
      sec.appendChild(ol); main.appendChild(sec);
    });
    if (feitas === aulas.length && aulas.length) {
      var fim = document.createElement("p");
      fim.className = "pacote-fim";
      fim.textContent = "🎉 Parabéns! Você concluiu o curso.";
      main.appendChild(fim);
    }
  }

  function abrir(i) {
    var aula = aulas[i].dados;
    var id = aula.aula.id;
    var salvo = estado.blocos[id] || {};
    app.innerHTML = "";
    var raiz = document.createElement("div");
    app.appendChild(raiz);
    window.MayaPlayer.montarAula(raiz, aula, {
      retomarEm: estado.concluidas[id] ? 0 : (salvo.indice || 0),
      concluidos: estado.concluidas[id] ? [] : (salvo.concluidos || []),
      rotuloSair: i < aulas.length - 1 ? "Próxima aula" : "Voltar ao curso",
      aoProgresso: function (p) {
        estado.blocos[id] = { indice: p.indice, concluidos: p.concluidos };
        salvar();
      },
      aoConcluir: function (r) {
        estado.concluidas[id] = true;
        delete estado.blocos[id];
        var total = 0, acertos = 0;
        Object.keys(r.resultados || {}).forEach(function (k) {
          var res = r.resultados[k];
          if (res.total) { total += res.total; acertos += res.acertosPrimeira || 0; }
        });
        if (total) estado.notas[id] = Math.round((acertos / total) * 100);
        salvar();
      },
      aoSair: function () {
        if (estado.concluidas[id] && i < aulas.length - 1) abrir(i + 1);
        else menu();
      },
    });
  }

  menu();
})();
