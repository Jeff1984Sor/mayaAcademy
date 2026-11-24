// Formulário gerado a partir do JSON Schema do tipo de bloco.
// Mantém o <textarea name="config"> como fonte da verdade (o que o Django valida).
(function () {
  "use strict";

  var ROTULOS = {
    personagem: "Personagem (slug)", fundo: "Fundo", lottie: "Animação Lottie (URL)", visuais: "Visuais",
    frase: "Nº da frase do roteiro (0 = primeira)", tipo: "Tipo", texto: "Texto", itens: "Itens", icone: "Ícone (emoji)",
    estado: "Estado do personagem", titulo: "Título", nome_usuario: "Nome do usuário", nome_ia: "Nome da IA",
    mensagens: "Mensagens", de: "Quem fala", nota: "Nota didática", nota_tipo: "Tipo da nota",
    rotulo_antes: "Rótulo do antes", rotulo_depois: "Rótulo do depois", antes: "Antes", depois: "Depois",
    comentario: "Comentário (após comparar)", instrucao: "Instrução", categorias: "Categorias", id: "Identificador",
    nome: "Nome", categoria: "Categoria (id)", feedback: "Feedback", objetivo: "Objetivo", pecas: "Peças",
    rotulo: "Rótulo", peso: "Peso (0–100)", distrator: "É distrator (atrapalha)", mensagem_final: "Mensagem final",
    contexto: "Contexto", trechos: "Trechos do texto", erro: "Este trecho tem erro", explicacao: "Explicação",
    inicio: "Nó inicial (id)", nos: "Nós do cenário", escolhas: "Escolhas", consequencia: "Consequência",
    vai_para: "Vai para o nó (vazio = fim)", cartoes: "Cartões", frente: "Frente", verso: "Verso",
    questoes: "Questões", enunciado: "Enunciado", alternativas: "Alternativas", correta: "Nº da correta (0 = primeira)",
    passos: "Passos", recompensa: "Recompensa", destaque: "Destaque", paginas_origem: "Páginas de origem",
  };
  var LONGOS = ["texto", "antes", "depois", "contexto", "explicacao", "enunciado", "verso", "consequencia",
    "comentario", "destaque", "recompensa", "mensagem_final", "nota", "objetivo"];

  function rotulo(chave) { return ROTULOS[chave] || chave.replace(/_/g, " ").replace(/^./, function (c) { return c.toUpperCase(); }); }

  function el(tag, attrs, filhos) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (filhos || []).forEach(function (f) { if (f) n.appendChild(f); });
    return n;
  }

  function valorPadrao(schema) {
    if (schema.enum) return schema.enum[0];
    if (schema.type === "object") {
      var o = {};
      (schema.required || []).forEach(function (k) { o[k] = valorPadrao(schema.properties[k]); });
      return o;
    }
    if (schema.type === "array") return [];
    if (schema.type === "integer") return 0;
    if (schema.type === "boolean") return false;
    return "";
  }

  function limpar(valor, schema) {
    // remove opcionais vazios para não poluir o JSON salvo
    if (schema.type === "object" && valor && typeof valor === "object") {
      var out = {};
      Object.keys(valor).forEach(function (k) {
        var sub = schema.properties && schema.properties[k];
        var v = sub ? limpar(valor[k], sub) : valor[k];
        var obrigatorio = (schema.required || []).indexOf(k) >= 0;
        var vazio = v === "" || v === null || v === undefined || v === false || (Array.isArray(v) && !v.length);
        if (obrigatorio || !vazio) out[k] = v;
      });
      return out;
    }
    if (schema.type === "array" && Array.isArray(valor)) return valor.map(function (v) { return limpar(v, schema.items); });
    return valor;
  }

  function campo(chave, schema, valor, obrigatorio, mudar) {
    var id = "cfg-" + Math.random().toString(36).slice(2, 9);
    var label = el("label", { for: id, text: rotulo(chave) + (obrigatorio ? " *" : "") });
    var entrada;
    if (schema.enum) {
      entrada = el("select", { id: id });
      if (!obrigatorio) entrada.appendChild(el("option", { value: "", text: "—" }));
      schema.enum.forEach(function (op) {
        var o = el("option", { value: op, text: op });
        if (op === valor) o.selected = true;
        entrada.appendChild(o);
      });
      entrada.addEventListener("change", function () { mudar(entrada.value || undefined); });
    } else if (schema.type === "boolean") {
      entrada = el("input", { id: id, type: "checkbox" });
      entrada.checked = Boolean(valor);
      entrada.addEventListener("change", function () { mudar(entrada.checked); });
      return el("label", { class: "flex items-center gap-2 text-sm" }, [entrada, document.createTextNode(rotulo(chave))]);
    } else if (schema.type === "integer") {
      entrada = el("input", { id: id, type: "number", step: "1" });
      if (valor !== undefined && valor !== null) entrada.value = valor;
      entrada.addEventListener("input", function () { mudar(entrada.value === "" ? undefined : parseInt(entrada.value, 10)); });
    } else {
      var longo = LONGOS.indexOf(chave) >= 0;
      entrada = longo ? el("textarea", { id: id, rows: "2" }) : el("input", { id: id, type: "text" });
      entrada.value = valor || "";
      entrada.addEventListener("input", function () { mudar(entrada.value); });
    }
    return el("div", {}, [label, entrada]);
  }

  function renderizar(container, schema, valor, mudar, chave) {
    if (schema.type === "object") {
      var caixa = el("div", { class: "space-y-3" });
      var atual = valor && typeof valor === "object" ? valor : {};
      Object.keys(schema.properties || {}).forEach(function (k) {
        var sub = schema.properties[k];
        var obrig = (schema.required || []).indexOf(k) >= 0;
        var atualizar = function (v) { atual[k] = v; mudar(atual); };
        if (sub.type === "array") {
          var bloco = el("fieldset", { class: "rounded-lg border border-slate-200 p-3 dark:border-slate-700" },
            [el("legend", { class: "px-1 text-sm font-semibold", text: rotulo(k) + (obrig ? " *" : "") })]);
          renderizar(bloco, sub, atual[k] || [], atualizar, k);
          caixa.appendChild(bloco);
        } else if (sub.type === "object") {
          var grupo = el("fieldset", { class: "rounded-lg border border-slate-200 p-3" }, [el("legend", { text: rotulo(k) })]);
          renderizar(grupo, sub, atual[k] || {}, atualizar, k);
          caixa.appendChild(grupo);
        } else {
          caixa.appendChild(campo(k, sub, atual[k], obrig, atualizar));
        }
      });
      container.appendChild(caixa);
      return;
    }
    if (schema.type === "array") {
      var lista = Array.isArray(valor) ? valor : [];
      var itens = el("ol", { class: "space-y-2" });
      var redesenhar = function () {
        container.innerHTML = container.querySelector("legend") ? container.querySelector("legend").outerHTML : "";
        renderizar(container, schema, lista, mudar, chave);
      };
      lista.forEach(function (item, i) {
        var li = el("li", { class: "rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60" });
        var barra = el("div", { class: "mb-1 flex items-center justify-between text-xs text-slate-500" }, [el("span", { text: "#" + i })]);
        var acoes = el("span", { class: "flex gap-1" });
        [["↑", -1], ["↓", 1]].forEach(function (par) {
          var b = el("button", { type: "button", class: "btn-sec px-2 py-0.5", "aria-label": par[1] < 0 ? "Mover para cima" : "Mover para baixo", text: par[0] });
          b.addEventListener("click", function () {
            var j = i + par[1];
            if (j < 0 || j >= lista.length) return;
            var t = lista[i]; lista[i] = lista[j]; lista[j] = t;
            mudar(lista); redesenhar();
          });
          acoes.appendChild(b);
        });
        var rem = el("button", { type: "button", class: "btn-perigo px-2 py-0.5", "aria-label": "Remover item", text: "✕" });
        rem.addEventListener("click", function () { lista.splice(i, 1); mudar(lista); redesenhar(); });
        acoes.appendChild(rem);
        barra.appendChild(acoes);
        li.appendChild(barra);
        var atualizarItem = function (v) { lista[i] = v; mudar(lista); };
        if (schema.items.type === "object") renderizar(li, schema.items, item, atualizarItem, chave);
        else li.appendChild(campo(chave === "alternativas" ? "texto" : "texto", schema.items, item, true, atualizarItem));
        itens.appendChild(li);
      });
      container.appendChild(itens);
      var add = el("button", { type: "button", class: "btn-sec mt-2 py-1 text-xs", text: "+ Adicionar" });
      add.addEventListener("click", function () { lista.push(valorPadrao(schema.items)); mudar(lista); redesenhar(); });
      container.appendChild(add);
    }
  }

  window.MayaEditorSchema = {
    montar: function (container, textarea, schemas, seletorTipo) {
      function render() {
        var schema = schemas[seletorTipo.value];
        container.innerHTML = "";
        if (!schema) return;
        var valor;
        try { valor = JSON.parse(textarea.value || "{}"); } catch (e) {
          container.appendChild(el("p", { class: "text-sm text-red-600", text: "O JSON bruto está inválido; corrija abaixo para voltar ao formulário." }));
          return;
        }
        renderizar(container, schema, valor, function (novo) {
          textarea.value = JSON.stringify(limpar(novo, schema), null, 2);
          textarea.dispatchEvent(new CustomEvent("config-alterada", { bubbles: true }));
        });
      }
      textarea.addEventListener("change", render);
      seletorTipo.addEventListener("change", render);
      render();
    },
  };
})();
