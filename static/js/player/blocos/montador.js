// Montar algo peça por peça (ex.: um prompt) com medidor de qualidade.

function embaralhar(lista) {
  const copia = [...lista];
  for (let i = copia.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

export const montador = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    const pecas = (cfg.pecas || []).map((p, i) => ({ ...p, i, peso: p.peso ?? (p.distrator ? 0 : 25) }));
    const boas = pecas.filter((p) => !p.distrator);
    const pesoTotal = boas.reduce((s, p) => s + p.peso, 0) || 1;
    const escolhidas = [];
    // em_ordem: as peças certas valem na ordem da config; na tela aparecem embaralhadas.
    const emOrdem = !!cfg.em_ordem;
    let errosOrdem = 0;
    const exibicao = emOrdem ? embaralhar(pecas) : pecas;

    const resultado = el("div", { class: "mt-resultado", "aria-live": "polite" });
    const medidor = el("div", { class: "mt-medidor", role: "meter", "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Qualidade" },
      el("div", { class: "mt-medidor-barra" }));
    const rotuloMedidor = el("span", { class: "mt-medidor-rotulo" });
    const feedback = el("p", { class: "mt-feedback", "aria-live": "polite" });
    const opcoesEl = el("div", { class: "mt-pecas" });
    corpo.append(
      el("p", { class: "atividade-instrucao", text: cfg.instrucao }),
      cfg.objetivo ? el("p", { class: "mt-objetivo", html: `🎯 ${md(cfg.objetivo).replace(/^<p>|<\/p>$/g, "")}` }) : null,
      el("div", { class: "mt-montagem" }, el("small", { text: "Sua montagem" }), resultado),
      el("div", { class: "mt-medidor-linha" }, medidor, rotuloMedidor),
      opcoesEl, feedback,
    );

    let concluido = false;
    const render = () => {
      resultado.innerHTML = escolhidas.length
        ? escolhidas.map((p) => `<span class="mt-trecho ${p.distrator ? "ruim" : ""}">${ctx.esc(p.texto)}</span>`).join(" ")
        : '<span class="mt-vazio">Toque nas peças abaixo para montar.</span>';
      const pontos = escolhidas.reduce((s, p) => s + (p.distrator ? -20 : p.peso), 0);
      const pct = Math.max(0, Math.min(100, Math.round((pontos / pesoTotal) * 100)));
      medidor.firstElementChild.style.width = `${pct}%`;
      medidor.dataset.nivel = pct >= 100 ? "otimo" : pct >= 60 ? "bom" : "fraco";
      medidor.setAttribute("aria-valuenow", String(pct));
      rotuloMedidor.textContent = `${pct}% ${pct >= 100 ? "— excelente!" : pct >= 60 ? "— está ficando bom" : ""}`;
      const completo = boas.every((p) => escolhidas.includes(p)) && !escolhidas.some((p) => p.distrator);
      if (completo && !concluido) {
        concluido = true;
        feedback.innerHTML = `🎉 ${md(cfg.mensagem_final || "Montagem completa!").replace(/^<p>|<\/p>$/g, "")}`;
        ctx.efeitos.confete(corpo.closest(".player") || document.body, 80);
        ctx.efeitos.somAcerto();
        ctx.concluir({ acertosPrimeira: escolhidas.length === boas.length && !errosOrdem ? 1 : 0 });
      }
    };

    for (const p of exibicao) {
      const btn = el("button", { class: "mt-peca", type: "button", "aria-pressed": "false" },
        el("strong", { text: p.rotulo }), el("span", { text: p.texto }));
      btn.addEventListener("click", () => {
        const idx = escolhidas.indexOf(p);
        if (emOrdem && idx < 0 && !p.distrator) {
          const proxima = boas[escolhidas.filter((e) => !e.distrator).length];
          if (proxima !== p) {
            errosOrdem += 1;
            ctx.efeitos.erro(btn);
            feedback.textContent = "✗ Ainda não é a vez desta etapa. Qual vem antes?";
            return;
          }
        }
        if (emOrdem && idx >= 0 && !p.distrator && escolhidas.filter((e) => !e.distrator).pop() !== p) {
          feedback.textContent = "Para desfazer, remova primeiro a última etapa colocada.";
          return;
        }
        if (idx >= 0) {
          escolhidas.splice(idx, 1);
          btn.setAttribute("aria-pressed", "false");
          btn.classList.remove("usada");
          feedback.textContent = "";
        } else {
          escolhidas.push(p);
          btn.setAttribute("aria-pressed", "true");
          btn.classList.add("usada");
          if (p.distrator) {
            ctx.efeitos.erro(btn);
            feedback.textContent = `✗ ${p.feedback || "Essa peça atrapalha mais do que ajuda. Toque de novo para remover."}`;
          } else {
            ctx.efeitos.acerto(btn);
            feedback.textContent = p.feedback ? `✓ ${p.feedback}` : "";
          }
        }
        render();
      });
      opcoesEl.append(btn);
    }
    render();
  },
};
