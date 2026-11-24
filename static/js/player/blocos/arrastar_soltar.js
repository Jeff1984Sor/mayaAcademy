// Classificar itens em categorias. Funciona com arrastar (mouse/toque) e com
// toque/teclado: selecione o item e depois a categoria.

import { embaralhar } from "../util.js";

export const arrastar_soltar = {
  montar(corpo, bloco, ctx) {
    const { el } = ctx;
    const cfg = bloco.config || {};
    const banco = el("div", { class: "as-banco", "aria-label": "Itens para classificar" });
    const zonas = {};
    const area = el("div", { class: "as-zonas" });
    const feedback = el("p", { class: "as-feedback", "aria-live": "polite" });
    const contador = el("p", { class: "as-contador" });
    for (const c of cfg.categorias || []) {
      const lista = el("div", { class: "as-lista" });
      const zona = el("div", { class: "as-zona", role: "button", tabindex: "0", "data-cat": c.id, "aria-label": `Colocar na categoria ${c.nome}` },
        el("span", { class: "as-zona-nome", text: c.nome }), lista);
      zona.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); zona.click(); }
      });
      zona._lista = lista;
      zonas[c.id] = zona;
      area.append(zona);
    }
    corpo.append(el("p", { class: "atividade-instrucao", text: cfg.instrucao }), banco, area, feedback, contador);

    const itens = embaralhar(cfg.itens || []);
    let selecionado = null;
    let colocados = 0;
    let erros = 0;
    const atualizar = () => { contador.textContent = `${colocados} de ${itens.length} classificados`; };

    const soltar = (chip, catId) => {
      const item = chip._item;
      const zona = zonas[catId];
      if (!zona) return;
      if (item.categoria === catId) {
        // Na categoria o item vira texto (não pode haver botão dentro da zona clicável).
        const colocado = el("span", { class: "as-item certo", text: item.texto });
        chip.remove();
        zona._lista.append(colocado);
        ctx.efeitos.acerto(colocado);
        feedback.textContent = item.feedback ? `✓ ${item.feedback}` : "✓ Isso mesmo!";
        colocados += 1;
        selecionado = null;
        atualizar();
        if (colocados === itens.length) {
          feedback.textContent = erros === 0 ? "🎉 Perfeito, tudo certo de primeira!" : "🎉 Tudo classificado!";
          ctx.efeitos.confete(corpo.closest(".player") || document.body, 60);
          ctx.concluir({ erros, acertosPrimeira: erros === 0 ? 1 : 0 });
        }
      } else {
        erros += 1;
        ctx.efeitos.erro(chip);
        ctx.efeitos.erro(zona);
        feedback.textContent = item.feedback ? `✗ Ainda não. ${item.feedback}` : "✗ Não é aqui. Tente outra categoria.";
      }
    };

    for (const item of itens) {
      const chip = el("button", { class: "as-item", type: "button", text: item.texto });
      chip._item = item;
      chip.addEventListener("click", () => {
        if (chip.disabled) return;
        banco.querySelectorAll(".selecionado").forEach((c) => c.classList.remove("selecionado"));
        selecionado = selecionado === chip ? null : chip;
        if (selecionado) {
          chip.classList.add("selecionado");
          feedback.textContent = `Selecionado: “${item.texto}”. Agora escolha a categoria.`;
        }
      });
      // Arrastar com Pointer Events (mouse e toque)
      chip.addEventListener("pointerdown", (ev) => {
        if (chip.disabled || ev.button > 0) return;
        const inicio = { x: ev.clientX, y: ev.clientY };
        let movendo = false;
        let fantasma = null;
        const mover = (e) => {
          if (!movendo && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) > 8) {
            movendo = true;
            fantasma = chip.cloneNode(true);
            fantasma.classList.add("as-fantasma");
            document.body.append(fantasma);
            chip.classList.add("arrastando");
          }
          if (movendo) {
            e.preventDefault();
            fantasma.style.left = `${e.clientX}px`;
            fantasma.style.top = `${e.clientY}px`;
            Object.values(zonas).forEach((z) => z.classList.toggle("sobre", z === zonaEm(e)));
          }
        };
        const zonaEm = (e) => document.elementFromPoint(e.clientX, e.clientY)?.closest(".as-zona");
        const fim = (e) => {
          document.removeEventListener("pointermove", mover);
          document.removeEventListener("pointerup", fim);
          Object.values(zonas).forEach((z) => z.classList.remove("sobre"));
          chip.classList.remove("arrastando");
          if (movendo) {
            fantasma?.remove();
            const z = zonaEm(e);
            if (z) soltar(chip, z.dataset.cat);
            chip._ignorarClique = true;
            setTimeout(() => { chip._ignorarClique = false; }, 50);
          }
        };
        document.addEventListener("pointermove", mover, { passive: false });
        document.addEventListener("pointerup", fim);
      });
      chip.addEventListener("click", (e) => { if (chip._ignorarClique) e.stopImmediatePropagation(); }, true);
      banco.append(chip);
    }
    for (const [id, zona] of Object.entries(zonas)) {
      zona.addEventListener("click", () => {
        if (selecionado) soltar(selecionado, id);
        else feedback.textContent = "Primeiro escolha um item.";
      });
    }
    atualizar();
  },
};
