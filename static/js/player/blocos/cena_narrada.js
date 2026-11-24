// Cena narrada: personagem + quadro onde os visuais entram frase a frase.

const ICONES_CENA = { titulo: "", cartao: "💡", lista: "📋", icone: "", alerta: "⚠️", citacao: "❝", numero: "" };

export const cena_narrada = {
  montar(corpo, bloco, ctx) {
    const { el, md, animar } = ctx;
    const cfg = bloco.config || {};
    const personagem = ctx.personagemPadrao(cfg.personagem);
    const av = ctx.avatar(personagem, { tamanho: 110 });
    const quadro = el("div", { class: "cena-quadro", "aria-live": "polite" });
    const palco = el("div", { class: `cena cena-fundo-${cfg.fundo || "palco"}` },
      el("div", { class: "cena-personagem" }, av.el, personagem ? el("span", { class: "cena-nome", text: personagem.nome }) : null),
      quadro,
    );
    corpo.append(palco);

    let animLottie = null;
    if (cfg.lottie && window.lottie && !ctx.reduzMovimento()) {
      const camada = el("div", { class: "cena-lottie", "aria-hidden": "true" });
      palco.prepend(camada);
      animLottie = window.lottie.loadAnimation({ container: camada, renderer: "svg", loop: true, autoplay: true, path: cfg.lottie });
    }

    ctx.vincularAvatar(av, personagem?.slug === cfg.personagem ? cfg.personagem : null);
    const porFrase = new Map();
    for (const v of cfg.visuais || []) {
      if (!porFrase.has(v.frase)) porFrase.set(v.frase, []);
      porFrase.get(v.frase).push(v);
    }
    const mostrados = new Set();

    const renderVisual = (v) => {
      const icone = v.icone || ICONES_CENA[v.tipo] || "";
      let n;
      if (v.tipo === "titulo") n = el("h3", { class: "vis vis-titulo", text: v.texto || "" });
      else if (v.tipo === "lista") {
        n = el("div", { class: "vis vis-lista" },
          v.texto ? el("strong", { text: v.texto }) : null,
          el("ul", {}, ...(v.itens || []).map((t) => el("li", { html: md(t).replace(/^<p>|<\/p>$/g, "") }))));
      } else if (v.tipo === "numero") n = el("div", { class: "vis vis-numero" }, el("span", { text: v.texto || "" }), v.itens?.[0] ? el("small", { text: v.itens[0] }) : null);
      else if (v.tipo === "icone") n = el("div", { class: "vis vis-icone", "aria-hidden": !v.texto }, el("span", { class: "vis-emoji", text: icone }), v.texto ? el("p", { text: v.texto }) : null);
      else n = el("div", { class: `vis vis-${v.tipo}` }, icone ? el("span", { class: "vis-emoji", "aria-hidden": "true", text: icone }) : null, el("div", { html: md(v.texto || "") }));
      return n;
    };

    const mostrar = (indice) => {
      for (const v of porFrase.get(indice) || []) {
        const chave = `${indice}-${(cfg.visuais || []).indexOf(v)}`;
        if (mostrados.has(chave)) continue;
        mostrados.add(chave);
        if (v.tipo === "titulo") quadro.innerHTML = "";
        const n = renderVisual(v);
        quadro.append(n);
        // Mantém o quadro legível no celular: no máximo 3 visuais.
        while (quadro.children.length > 3) quadro.firstElementChild.remove();
        animar(n, { opacity: 0, y: 18, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.5 });
        if (n.querySelectorAll("li").length) animar(n.querySelectorAll("li"), { opacity: 0, x: -12 }, { opacity: 1, x: 0, stagger: 0.12, delay: 0.15 });
        if (v.estado) av.estado(v.estado);
      }
    };

    ctx.narracao.on("frase", (i) => mostrar(i));
    // Sem narração tocando (ex.: voltou ao bloco), mostra o primeiro visual.
    mostrar(0);
    ctx.narracao.on("fim", () => {
      // Ao terminar, garante que todos os visuais apareceram (quem pulou não perde conteúdo).
      for (const k of porFrase.keys()) mostrar(k);
    });
    return { destruir: () => animLottie?.destroy() };
  },
};
