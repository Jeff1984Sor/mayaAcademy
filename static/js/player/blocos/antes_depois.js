// Slider comparando duas versões. Conclui quando o aluno vê os dois extremos.

export const antes_depois = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    const antes = el("div", { class: "ad-lado ad-antes" }, el("span", { class: "ad-rotulo", text: cfg.rotulo_antes }), el("div", { html: md(cfg.antes) }));
    const depois = el("div", { class: "ad-lado ad-depois" }, el("span", { class: "ad-rotulo", text: cfg.rotulo_depois }), el("div", { html: md(cfg.depois) }));
    const alca = el("div", { class: "ad-alca", "aria-hidden": "true" }, el("span", { text: "⇆" }));
    const caixa = el("div", { class: "ad-caixa" }, depois, antes, alca);
    const slider = el("input", {
      type: "range", min: "0", max: "100", value: "50", class: "ad-slider",
      "aria-label": `Arraste para comparar: ${cfg.rotulo_antes} e ${cfg.rotulo_depois}`,
    });
    const status = el("p", { class: "ad-status", text: `Arraste para ver “${cfg.rotulo_antes}” e “${cfg.rotulo_depois}”.` });
    const comentario = cfg.comentario ? el("div", { class: "ad-comentario", hidden: true, html: md(cfg.comentario) }) : null;
    corpo.append(caixa, slider, status, comentario);

    const vistos = { antes: false, depois: false };
    let concluido = false;
    const aplicar = (v) => {
      antes.style.clipPath = `inset(0 ${100 - v}% 0 0)`;
      alca.style.left = `${v}%`;
      if (v >= 85) vistos.antes = true;
      if (v <= 15) vistos.depois = true;
      if (!concluido && vistos.antes && vistos.depois) {
        concluido = true;
        status.textContent = "✓ Você comparou as duas versões.";
        if (comentario) { comentario.hidden = false; ctx.animar(comentario, { opacity: 0, y: 10 }, { opacity: 1, y: 0 }); }
        ctx.efeitos.somAcerto();
        ctx.concluir();
      }
    };
    slider.addEventListener("input", () => aplicar(Number(slider.value)));

    // Arrastar direto na caixa (melhor no celular)
    let arrastando = false;
    const posicao = (ev) => {
      const r = caixa.getBoundingClientRect();
      const v = Math.round(Math.max(0, Math.min(100, ((ev.clientX - r.left) / r.width) * 100)));
      slider.value = String(v);
      aplicar(v);
    };
    caixa.addEventListener("pointerdown", (ev) => { arrastando = true; caixa.setPointerCapture(ev.pointerId); posicao(ev); });
    caixa.addEventListener("pointermove", (ev) => { if (arrastando) posicao(ev); });
    caixa.addEventListener("pointerup", () => { arrastando = false; });
    aplicar(50);

    // Dica animada: mostra que dá para arrastar
    if (!ctx.reduzMovimento() && window.gsap) {
      const obj = { v: 50 };
      window.gsap.to(obj, { v: 62, duration: 0.5, yoyo: true, repeat: 1, delay: 0.6, ease: "sine.inOut", onUpdate: () => {
        antes.style.clipPath = `inset(0 ${100 - obj.v}% 0 0)`; alca.style.left = `${obj.v}%`;
      } });
    }
  },
};
