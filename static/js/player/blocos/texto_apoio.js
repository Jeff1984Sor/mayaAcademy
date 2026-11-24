// Texto curto de apoio (nunca pode ser o único tipo da aula — validado no backend).

export const texto_apoio = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    corpo.append(el("div", { class: "ta-texto", html: md(bloco.texto_tela || "") }));
    if (cfg.destaque) {
      corpo.append(el("aside", { class: "ta-destaque" },
        el("span", { "aria-hidden": "true", text: cfg.icone || "💡" }),
        el("div", { html: md(cfg.destaque) })));
    }
  },
};
