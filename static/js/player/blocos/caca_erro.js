// Texto com erros escondidos: o aluno toca nos trechos que acha errados.

export const caca_erro = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    const trechos = cfg.trechos || [];
    const total = trechos.filter((t) => t.erro).length;
    let achados = 0;
    let tentativasErradas = 0;
    let concluido = false;

    const placar = el("p", { class: "ce-placar", "aria-live": "polite" });
    const texto = el("div", { class: "ce-texto" });
    const explicacoes = el("ol", { class: "ce-explicacoes", "aria-live": "polite" });
    const btnRevelar = el("button", { class: "pl-link", type: "button", hidden: true }, "Mostrar os que faltam");
    corpo.append(
      el("p", { class: "atividade-instrucao", text: cfg.instrucao }),
      cfg.contexto ? el("div", { class: "ce-contexto", html: md(cfg.contexto) }) : null,
      placar, texto, btnRevelar, explicacoes,
    );

    const atualizar = () => {
      placar.innerHTML = `🔎 <b>${achados}</b> de <b>${total}</b> erro(s) encontrado(s)`;
      if (!concluido && achados === total) {
        concluido = true;
        btnRevelar.hidden = true;
        placar.innerHTML = tentativasErradas === 0 ? "🎉 Você achou todos, sem nenhum palpite errado!" : "🎉 Você achou todos os erros!";
        ctx.efeitos.confete(corpo.closest(".player") || document.body, 70);
        ctx.concluir({ tentativasErradas, acertosPrimeira: tentativasErradas === 0 ? 1 : 0 });
      }
    };

    const revelar = (span, t, porDica = false) => {
      span.classList.add("achado");
      if (porDica) span.classList.add("revelado");
      span.disabled = true;
      span.setAttribute("aria-label", `${t.texto} — erro encontrado`);
      const n = explicacoes.children.length + 1;
      span.dataset.n = String(n);
      explicacoes.append(el("li", {}, el("q", { text: t.texto }), el("span", { html: md(t.explicacao || "") })));
      achados += 1;
      atualizar();
    };

    for (const t of trechos) {
      const span = el("button", { class: "ce-trecho", type: "button", text: t.texto });
      span.addEventListener("click", () => {
        if (span.disabled || concluido) return;
        if (t.erro) {
          ctx.efeitos.acerto(span);
          revelar(span, t);
        } else {
          tentativasErradas += 1;
          ctx.efeitos.erro(span);
          placar.innerHTML = `Esse trecho está correto. 🔎 <b>${achados}</b> de <b>${total}</b>`;
          if (tentativasErradas >= 4) btnRevelar.hidden = false;
        }
      });
      texto.append(span, " ");
    }
    btnRevelar.addEventListener("click", () => {
      [...texto.querySelectorAll(".ce-trecho")].forEach((span, i) => {
        if (trechos[i].erro && !span.disabled) revelar(span, trechos[i], true);
      });
    });
    atualizar();
  },
};
