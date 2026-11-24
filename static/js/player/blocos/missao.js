// Caso prático: contexto + passos de decisão; só avança acertando cada passo.

import { montarQuestao } from "./questoes.js";

export const missao = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    const passos = cfg.passos || [];
    let atual = 0;
    let primeiras = 0;
    const trilha = el("ol", { class: "ms-trilha", "aria-label": "Passos da missão" },
      ...passos.map((_, i) => el("li", { text: String(i + 1) })));
    const area = el("div", { class: "ms-area" });
    const seguir = el("button", { class: "pl-btn", type: "button", hidden: true }, "Próximo passo");
    corpo.append(
      el("div", { class: "ms-briefing" }, el("span", { class: "ms-selo", text: "🎯 Missão" }), el("h3", { text: cfg.titulo }), el("div", { html: md(cfg.contexto) })),
      trilha, area, seguir,
    );

    const mostrar = () => {
      area.innerHTML = "";
      seguir.hidden = true;
      [...trilha.children].forEach((li, i) => { li.classList.toggle("atual", i === atual); li.classList.toggle("feito", i < atual); });
      const card = montarQuestao(ctx, passos[atual], {
        modo: "missao",
        aoTerminar: ({ primeira }) => {
          if (primeira) primeiras += 1;
          trilha.children[atual].classList.add("feito");
          if (atual < passos.length - 1) { seguir.hidden = false; if (!window.MAYA_SEM_FOCO) seguir.focus(); return; }
          area.append(el("div", { class: "ms-final" },
            el("strong", { text: "Missão cumprida! 🏆" }),
            cfg.recompensa ? el("div", { html: md(cfg.recompensa) }) : null));
          ctx.efeitos.confete(corpo.closest(".player") || document.body, 100);
          ctx.concluir({ acertosPrimeira: primeiras === passos.length ? 1 : 0 });
        },
      });
      area.append(el("p", { class: "qz-pos", text: `Passo ${atual + 1} de ${passos.length}` }), card);
      ctx.animar(card, { opacity: 0, y: 16 }, { opacity: 1, y: 0 });
    };
    seguir.addEventListener("click", () => { atual += 1; mostrar(); });
    mostrar();
  },
};
