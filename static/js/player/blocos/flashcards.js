// Cartões de frente e verso. Conclui quando todos foram virados ao menos uma vez.

export const flashcards = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cartoes = (bloco.config || {}).cartoes || [];
    const vistos = new Set();
    let i = 0;
    let concluido = false;
    const cartao = el("button", { class: "fc-cartao", type: "button", "aria-live": "polite" });
    const frente = el("div", { class: "fc-face fc-frente" });
    const verso = el("div", { class: "fc-face fc-verso" });
    cartao.append(el("div", { class: "fc-interno" }, frente, verso));
    const ant = el("button", { class: "pl-btn pl-btn-sec", type: "button", "aria-label": "Cartão anterior" }, "‹");
    const prox = el("button", { class: "pl-btn pl-btn-sec", type: "button", "aria-label": "Próximo cartão" }, "›");
    const pos = el("span", { class: "fc-pos" });
    corpo.append(el("p", { class: "atividade-instrucao", text: "Toque no cartão para virar." }), cartao, el("div", { class: "fc-nav" }, ant, pos, prox));

    const render = () => {
      const c = cartoes[i];
      cartao.classList.remove("virado");
      frente.innerHTML = md(c.frente);
      verso.innerHTML = md(c.verso);
      cartao.setAttribute("aria-label", `Cartão ${i + 1}: ${c.frente}. Toque para ver o verso.`);
      pos.textContent = `${i + 1} / ${cartoes.length} · ${vistos.size} virados`;
      ant.disabled = i === 0;
      prox.disabled = i === cartoes.length - 1;
    };
    cartao.addEventListener("click", () => {
      cartao.classList.toggle("virado");
      if (cartao.classList.contains("virado")) {
        vistos.add(i);
        cartao.setAttribute("aria-label", `Verso: ${cartoes[i].verso}`);
      }
      pos.textContent = `${i + 1} / ${cartoes.length} · ${vistos.size} virados`;
      if (!concluido && vistos.size === cartoes.length) {
        concluido = true;
        ctx.efeitos.somAcerto();
        ctx.concluir();
      }
    });
    ant.addEventListener("click", () => { if (i > 0) { i -= 1; render(); } });
    prox.addEventListener("click", () => { if (i < cartoes.length - 1) { i += 1; render(); } });
    render();
  },
};
