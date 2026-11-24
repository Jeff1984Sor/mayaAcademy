// Situação com escolhas e consequências diferentes.

export const cenario_ramificado = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    const nos = Object.fromEntries((cfg.nos || []).map((n) => [n.id, n]));
    const caminho = el("ol", { class: "cr-caminho", "aria-label": "Suas escolhas" });
    const cena = el("div", { class: "cr-cena", "aria-live": "polite" });
    corpo.append(cfg.titulo ? el("p", { class: "atividade-instrucao", text: cfg.titulo }) : null, cena, caminho);
    let ruins = 0;
    let concluido = false;

    const finalizar = () => {
      if (concluido) return;
      concluido = true;
      ctx.concluir({ escolhasRuins: ruins, acertosPrimeira: ruins === 0 ? 1 : 0 });
    };

    const mostrar = (id) => {
      const no = nos[id];
      cena.innerHTML = "";
      if (!no) return;
      const card = el("div", { class: "cr-no" }, el("div", { class: "cr-texto", html: md(no.texto) }));
      cena.append(card);
      ctx.animar(card, { opacity: 0, x: 30 }, { opacity: 1, x: 0, duration: 0.4 });
      if (!no.escolhas?.length) {
        card.append(el("p", { class: "cr-fim", text: "Fim do cenário." }), botaoReiniciar());
        finalizar();
        return;
      }
      const opcoes = el("div", { class: "cr-opcoes" });
      for (const escolha of no.escolhas) {
        const btn = el("button", { class: "cr-opcao", type: "button", text: escolha.texto });
        btn.addEventListener("click", () => {
          opcoes.querySelectorAll("button").forEach((b) => { b.disabled = true; });
          btn.classList.add(`cr-${escolha.tipo || "neutro"}`);
          if (escolha.tipo === "ruim") { ruins += 1; ctx.efeitos.erro(btn); }
          else if (escolha.tipo === "bom") ctx.efeitos.acerto(btn);
          const icone = { bom: "✅", ruim: "⚠️", neutro: "➡️" }[escolha.tipo || "neutro"];
          const conseq = el("div", { class: `cr-consequencia cr-${escolha.tipo || "neutro"}`, role: "status" },
            el("span", { "aria-hidden": "true", text: icone }), el("div", { html: md(escolha.consequencia) }));
          card.append(conseq);
          ctx.animar(conseq, { opacity: 0, y: 12 }, { opacity: 1, y: 0 });
          caminho.append(el("li", { class: `cr-${escolha.tipo || "neutro"}`, text: escolha.texto }));
          const seguir = el("button", { class: "pl-btn", type: "button" }, escolha.vai_para ? "Continuar" : "Ver desfecho");
          seguir.addEventListener("click", () => {
            if (escolha.vai_para) mostrar(escolha.vai_para);
            else {
              seguir.remove();
              card.append(el("p", { class: "cr-fim", text: "Fim do cenário." }), botaoReiniciar());
              finalizar();
            }
          });
          card.append(seguir);
          if (!window.MAYA_SEM_FOCO) seguir.focus();
        });
        opcoes.append(btn);
      }
      card.append(opcoes);
    };

    const botaoReiniciar = () => {
      const b = el("button", { class: "pl-btn pl-btn-sec", type: "button" }, "↺ Tentar outro caminho");
      b.addEventListener("click", () => { caminho.innerHTML = ""; mostrar(cfg.inicio); });
      return b;
    };
    mostrar(cfg.inicio);
  },
};
