// Diálogo estilo podcast: dois (ou mais) personagens, o que fala ganha destaque.

export const dialogo = {
  montar(corpo, bloco, ctx) {
    const { el, esc } = ctx;
    const slugs = [...new Set((bloco.timeline || []).map((t) => t.personagem))];
    const cartoes = {};
    const avatares = {};
    const estudio = el("div", { class: `podcast podcast-${(bloco.config || {}).fundo || "estudio"}` });
    for (const slug of slugs) {
      const p = ctx.personagens[slug] || { nome: slug, slug };
      const av = ctx.avatar(p, { tamanho: 96 });
      avatares[slug] = av;
      cartoes[slug] = el("div", { class: "podcast-pessoa", "data-slug": slug }, av.el, el("span", { text: p.nome }));
      estudio.append(cartoes[slug]);
    }
    const onda = el("div", { class: "podcast-onda", "aria-hidden": "true" }, ...Array.from({ length: 24 }, () => el("i")));
    const fala = el("p", { class: "podcast-fala" });
    const historico = el("details", { class: "podcast-historico" }, el("summary", { text: "Conversa até aqui" }));
    const lista = el("div");
    historico.append(lista);
    corpo.append(estudio, onda, fala, historico);

    let ativo = null;
    ctx.narracao.on("frase", (_i, item, ultima) => {
      if (item.frase === 0) {
        const p = ctx.personagens[item.personagem];
        lista.append(el("p", { html: `<b>${esc(p?.nome || item.personagem)}:</b> ` }));
      }
      lista.lastElementChild?.append(document.createTextNode(`${item.texto} `));
      if (!ultima) return;
      ativo = item.personagem;
      for (const [slug, c] of Object.entries(cartoes)) c.classList.toggle("ativo", slug === ativo);
      fala.innerHTML = `<b>${esc(ctx.personagens[ativo]?.nome || ativo)}</b> ${esc(item.texto).replace(/\*([^*]+)\*/g, "<em>$1</em>")}`;
    });
    ctx.narracao.on("estado", (tocando) => {
      onda.classList.toggle("tocando", tocando);
      for (const [slug, av] of Object.entries(avatares)) av.estado(tocando && slug === ativo ? "falando" : "neutro");
    });
    ctx.narracao.on("boca", (nivel) => {
      for (const [slug, av] of Object.entries(avatares)) av.abrirBoca(slug === ativo ? nivel : 0);
      onda.style.setProperty("--nivel", nivel.toFixed(2));
    });
    ctx.narracao.on("fim", () => {
      for (const av of Object.values(avatares)) { av.estado("neutro"); av.abrirBoca(0); }
    });
    if (!slugs.length) fala.textContent = "Este diálogo ainda não tem roteiro.";
  },
};
