// 2–4 questões com explicação imediata, uma de cada vez.

import { montarQuestao } from "./questoes.js";

export const quiz_fixacao = {
  montar(corpo, bloco, ctx) {
    const { el } = ctx;
    const questoes = (bloco.config || {}).questoes || [];
    let atual = 0;
    let acertos = 0;
    const pos = el("p", { class: "qz-pos" });
    const area = el("div", { class: "qz-area" });
    const seguir = el("button", { class: "pl-btn", type: "button", hidden: true });
    corpo.append(pos, area, seguir);

    const mostrar = () => {
      area.innerHTML = "";
      seguir.hidden = true;
      pos.textContent = `Questão ${atual + 1} de ${questoes.length}`;
      const card = montarQuestao(ctx, questoes[atual], {
        modo: "quiz",
        aoTerminar: ({ primeira }) => {
          if (primeira) acertos += 1;
          if (atual < questoes.length - 1) {
            seguir.textContent = "Próxima questão";
            seguir.hidden = false;
            if (!window.MAYA_SEM_FOCO) seguir.focus();
          } else {
            const resumo = el("p", { class: "qz-resumo", text: `Você acertou ${acertos} de ${questoes.length} de primeira.` });
            area.append(resumo);
            if (acertos === questoes.length) ctx.efeitos.confete(corpo.closest(".player") || document.body, 80);
            ctx.concluir({ acertosPrimeira: acertos, total: questoes.length });
          }
        },
      });
      area.append(card);
      ctx.animar(card, { opacity: 0, y: 16 }, { opacity: 1, y: 0 });
      if (!window.MAYA_SEM_FOCO) card.querySelector("button")?.focus({ preventScroll: true });
    };
    seguir.addEventListener("click", () => { atual += 1; mostrar(); });
    mostrar();
  },
};
