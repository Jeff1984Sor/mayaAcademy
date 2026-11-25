// Gerador por PDF: barra de progresso (consulta a situação) e editor da ementa (gate do criador).
(function () {
  "use strict";

  // --- progresso ---------------------------------------------------------------
  var andamento = document.getElementById("andamento");
  if (andamento) {
    var statusInicial = andamento.dataset.status;
    var consultar = function () {
      fetch(andamento.dataset.url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (s) {
          document.getElementById("and-rotulo").textContent = s.rotulo;
          document.getElementById("and-etapa").textContent = s.etapa;
          document.getElementById("and-pct").textContent = s.progresso + "%";
          document.getElementById("and-preench").style.width = s.progresso + "%";
          document.getElementById("and-barra").setAttribute("aria-valuenow", s.progresso);
          if (s.status !== statusInicial || !s.em_andamento) { window.location.reload(); return; }
          setTimeout(consultar, 4000);
        })
        .catch(function () { setTimeout(consultar, 10000); });
    };
    setTimeout(consultar, 3000);
  }

  // --- editor da ementa -----------------------------------------------------------
  var raiz = document.getElementById("editor-ementa");
  var fonte = document.getElementById("dados-ementa");
  if (!raiz || !fonte) return;
  var ementa = JSON.parse(fonte.textContent);
  ementa.modulos = ementa.modulos || [];

  function el(tag, attrs, filhos) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "texto") e.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    });
    (filhos || []).forEach(function (f) { if (f) e.appendChild(f); });
    return e;
  }

  function campo(rotulo, valor, aoMudar, opcoes) {
    opcoes = opcoes || {};
    var id = "c" + Math.random().toString(36).slice(2, 9);
    var entrada = opcoes.area
      ? el("textarea", { id: id, rows: 2 })
      : el("input", { id: id, type: opcoes.tipo || "text" });
    entrada.value = valor == null ? "" : valor;
    if (opcoes.min) entrada.setAttribute("min", opcoes.min);
    if (opcoes.placeholder) entrada.setAttribute("placeholder", opcoes.placeholder);
    entrada.addEventListener("input", function () { aoMudar(entrada.value); });
    return el("div", { class: "campo mb-2 " + (opcoes.classe || "") }, [
      el("label", { for: id, texto: rotulo, class: "text-xs" }), entrada,
    ]);
  }

  function botao(texto, titulo, acao, perigo) {
    return el("button", { type: "button", class: (perigo ? "btn-perigo" : "btn-sec") + " px-2 py-1 text-xs", title: titulo,
      "aria-label": titulo, texto: texto, onclick: function () { acao(); desenhar(); } });
  }

  function mover(lista, i, delta) {
    var j = i + delta;
    if (j < 0 || j >= lista.length) return false;
    var t = lista[i]; lista[i] = lista[j]; lista[j] = t;
    return true;
  }

  function novaAula() { return { titulo: "Nova aula", objetivo: "", paginas_txt: "", duracao_min: 12 }; }

  function desenhar() {
    raiz.innerHTML = "";
    raiz.appendChild(el("div", { class: "cartao" }, [
      el("h3", { class: "mb-3 font-semibold", texto: "Curso" }),
      campo("Título do curso", ementa.titulo, function (v) { ementa.titulo = v; }),
      campo("Subtítulo", ementa.subtitulo, function (v) { ementa.subtitulo = v; }),
      campo("Descrição", ementa.descricao, function (v) { ementa.descricao = v; }, { area: true }),
      campo("Categoria", ementa.categoria, function (v) { ementa.categoria = v; }),
    ]));

    var totalMin = 0;
    ementa.modulos.forEach(function (m, mi) {
      var aulas = el("ol", { class: "space-y-3" });
      m.aulas.forEach(function (a, ai) {
        totalMin += parseInt(a.duracao_min, 10) || 0;
        aulas.appendChild(el("li", { class: "rounded-xl border border-navy-100 p-3 dark:border-dark-600" }, [
          el("div", { class: "mb-2 flex flex-wrap items-center justify-between gap-2" }, [
            el("strong", { class: "font-mono text-sm", texto: "Aula " + (mi + 1) + "." + (ai + 1) }),
            el("div", { class: "flex flex-wrap gap-1" }, [
              botao("↑", "Subir a aula", function () {
                if (!mover(m.aulas, ai, -1) && mi > 0) { ementa.modulos[mi - 1].aulas.push(m.aulas.splice(ai, 1)[0]); }
              }),
              botao("↓", "Descer a aula", function () {
                if (!mover(m.aulas, ai, 1) && mi < ementa.modulos.length - 1) { ementa.modulos[mi + 1].aulas.unshift(m.aulas.splice(ai, 1)[0]); }
              }),
              botao("Dividir", "Dividir em duas aulas (duplica; depois ajuste as páginas)", function () {
                var copia = JSON.parse(JSON.stringify(a)); copia.titulo = a.titulo + " (parte 2)";
                a.titulo = a.titulo.replace(/ \(parte 1\)$/, "") + " (parte 1)";
                m.aulas.splice(ai + 1, 0, copia);
              }),
              ai < m.aulas.length - 1 ? botao("Juntar com a próxima", "Juntar com a próxima aula", function () {
                var prox = m.aulas[ai + 1];
                a.paginas_txt = [a.paginas_txt, prox.paginas_txt].filter(Boolean).join(", ");
                a.duracao_min = (parseInt(a.duracao_min, 10) || 0) + (parseInt(prox.duracao_min, 10) || 0);
                a.objetivo = [a.objetivo, prox.objetivo].filter(Boolean).join(" ");
                m.aulas.splice(ai + 1, 1);
              }) : null,
              botao("Excluir", "Excluir a aula", function () { m.aulas.splice(ai, 1); }, true),
            ]),
          ]),
          campo("Título", a.titulo, function (v) { a.titulo = v; }),
          campo("Objetivo de aprendizagem", a.objetivo, function (v) { a.objetivo = v; }, { area: true }),
          el("div", { class: "grid gap-2 sm:grid-cols-[1fr_8rem]" }, [
            campo("Páginas de origem (ex.: 12-15, 18)", a.paginas_txt, function (v) { a.paginas_txt = v; }, { placeholder: "12-15, 18" }),
            campo("Duração (min)", a.duracao_min, function (v) { a.duracao_min = parseInt(v, 10) || 0; desenharTotal(); }, { tipo: "number", min: 3 }),
          ]),
        ]));
      });
      raiz.appendChild(el("section", { class: "cartao" }, [
        el("div", { class: "mb-3 flex flex-wrap items-end justify-between gap-2" }, [
          campo("Módulo " + (mi + 1), m.titulo, function (v) { m.titulo = v; }, { classe: "flex-1 mb-0" }),
          el("div", { class: "flex gap-1" }, [
            botao("↑", "Subir o módulo", function () { mover(ementa.modulos, mi, -1); }),
            botao("↓", "Descer o módulo", function () { mover(ementa.modulos, mi, 1); }),
            botao("+ Aula", "Adicionar aula neste módulo", function () { m.aulas.push(novaAula()); }),
            botao("Excluir módulo", "Excluir o módulo e suas aulas", function () {
              if (!m.aulas.length || window.confirm("Excluir o módulo “" + m.titulo + "” e suas " + m.aulas.length + " aula(s)?")) ementa.modulos.splice(mi, 1);
            }, true),
          ]),
        ]),
        aulas,
      ]));
    });

    raiz.appendChild(el("div", { class: "flex flex-wrap items-center justify-between gap-2" }, [
      botao("+ Módulo", "Adicionar módulo", function () { ementa.modulos.push({ titulo: "Novo módulo", aulas: [novaAula()] }); }),
      el("p", { class: "text-sm suave", id: "total-ementa" }),
    ]));
    desenharTotal();
  }

  function desenharTotal() {
    var aulas = 0, min = 0;
    ementa.modulos.forEach(function (m) { m.aulas.forEach(function (a) { aulas++; min += parseInt(a.duracao_min, 10) || 0; }); });
    var alvo = document.getElementById("total-ementa");
    if (alvo) alvo.textContent = ementa.modulos.length + " módulo(s) · " + aulas + " aula(s) · " + Math.round(min / 6) / 10 + " h no total";
  }

  document.getElementById("form-ementa").addEventListener("submit", function (ev) {
    document.getElementById("campo-ementa").value = JSON.stringify(ementa);
    if (ev.submitter && ev.submitter.value === "gerar") {
      var n = 0; ementa.modulos.forEach(function (m) { n += m.aulas.length; });
      if (!window.confirm("Aprovar a ementa e gerar " + n + " aula(s) com a IA? Isso tem custo de uso da API.")) ev.preventDefault();
    }
  });

  desenhar();
})();
