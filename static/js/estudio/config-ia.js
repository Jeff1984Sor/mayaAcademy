// Estúdio › Configurar IA: busca os modelos da conta, preenche preços e testa a conexão.
(function () {
  "use strict";
  var form = document.getElementById("form-ia");
  if (!form) return;
  var campoChave = form.querySelector("input[name=chave]");
  var campoModelo = form.querySelector("input[name=modelo]");
  var entrada = form.querySelector("input[name=preco_entrada_1m]");
  var saida = form.querySelector("input[name=preco_saida_1m]");
  var caixa = document.getElementById("modelos");
  var msgModelos = document.getElementById("msg-modelos");
  var msgTeste = document.getElementById("msg-teste");

  function csrf() { return form.querySelector("input[name=csrfmiddlewaretoken]").value; }

  function post(url, corpo) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(corpo),
    }).then(function (r) { return r.json(); });
  }

  function aplicarPreco(s) {
    if (!s) return;
    entrada.value = s.entrada;
    saida.value = s.saida;
  }

  form.querySelectorAll("[data-preco]").forEach(function (b) {
    b.addEventListener("click", function () { aplicarPreco({ entrada: b.dataset.entrada, saida: b.dataset.saida }); });
  });

  document.getElementById("btn-modelos").addEventListener("click", function (ev) {
    var botao = ev.currentTarget;
    botao.disabled = true;
    msgModelos.textContent = "Buscando os modelos da sua conta…";
    post(form.dataset.urlModelos, { chave: campoChave.value }).then(function (r) {
      botao.disabled = false;
      if (!r.ok) { msgModelos.textContent = "⚠ " + r.erro; return; }
      caixa.innerHTML = "";
      caixa.classList.remove("hidden");
      r.modelos.forEach(function (m) {
        var b = document.createElement("button");
        b.type = "button";
        b.setAttribute("role", "option");
        b.className = "flex w-full items-center justify-between gap-2 rounded px-3 py-2 text-left text-sm hover:bg-navy-50 dark:hover:bg-dark-700";
        b.innerHTML = '<span class="font-mono"></span><span class="text-xs"></span>';
        b.firstChild.textContent = m.id;
        if (m.sugestao) {
          b.lastChild.textContent = m.sugestao.rotulo + " · US$ " + m.sugestao.entrada + " / " + m.sugestao.saida;
          if (m.sugestao.linha === "sol") b.lastChild.className = "selo-ok";
        }
        b.addEventListener("click", function () {
          campoModelo.value = m.id;
          aplicarPreco(m.sugestao);
          caixa.querySelectorAll("button").forEach(function (x) { x.classList.remove("bg-indigo-100", "dark:bg-indigo-400/20"); });
          b.classList.add("bg-indigo-100", "dark:bg-indigo-400/20");
          msgModelos.textContent = "Escolhido: " + m.id + (m.sugestao ? " — preços preenchidos (confira na página oficial)." : " — preencha os preços abaixo.");
        });
        caixa.appendChild(b);
      });
      msgModelos.textContent = r.modelos.length + " modelo(s) de texto na sua conta. Clique em um para escolher (os da linha Sol estão marcados).";
    }).catch(function () { botao.disabled = false; msgModelos.textContent = "⚠ Não foi possível consultar agora."; });
  });

  form.querySelectorAll("[data-ouvir]").forEach(function (b) {
    b.addEventListener("click", function () {
      var voz = form.querySelector("[name=" + b.dataset.ouvir + "]").value;
      var modelo = form.querySelector("[name=tts_modelo]").value;
      b.disabled = true;
      b.textContent = "…";
      fetch(form.dataset.urlAmostra, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ chave: campoChave.value, voz: voz, modelo: modelo }),
      }).then(function (r) {
        if (!r.ok) return r.json().then(function (j) { throw new Error(j.erro); });
        return r.blob();
      }).then(function (blob) {
        new Audio(URL.createObjectURL(blob)).play();
        b.disabled = false; b.textContent = "▶ Ouvir";
      }).catch(function (e) {
        b.disabled = false; b.textContent = "▶ Ouvir";
        msgTeste.className = "text-sm text-perigo-700 dark:text-perigo-50";
        msgTeste.textContent = "✘ " + (e.message || "Não foi possível gerar a amostra.");
      });
    });
  });

  document.getElementById("btn-testar").addEventListener("click", function (ev) {
    var botao = ev.currentTarget;
    botao.disabled = true;
    msgTeste.className = "text-sm suave";
    msgTeste.textContent = "Testando…";
    post(form.dataset.urlTestar, { chave: campoChave.value, modelo: campoModelo.value }).then(function (r) {
      botao.disabled = false;
      if (r.ok) {
        msgTeste.className = "text-sm text-teal-700 dark:text-teal-100";
        msgTeste.textContent = "✔ Funcionou (" + r.modelo + ", " + r.segundos + " s): “" + r.resposta + "”. Agora clique em Salvar.";
      } else {
        msgTeste.className = "text-sm text-perigo-700 dark:text-perigo-50";
        msgTeste.textContent = "✘ " + r.erro;
      }
    }).catch(function () { botao.disabled = false; msgTeste.textContent = "✘ Não foi possível testar agora."; });
  });
})();
