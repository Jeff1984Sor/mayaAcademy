// Componente de questão compartilhado por quiz_fixacao e missao.

import { embaralhar } from "../util.js";

// modo "quiz": errou → mostra a correta e segue. modo "missao": errou → tenta de novo.
export function montarQuestao(ctx, q, { modo = "quiz", aoTerminar }) {
  const { el, md } = ctx;
  const ordem = embaralhar(q.alternativas.map((texto, i) => ({ texto, i })));
  const card = el("fieldset", { class: "qz-questao" }, el("legend", { html: md(q.enunciado) }));
  const lista = el("div", { class: "qz-alternativas" });
  const explicacao = el("div", { class: "qz-explicacao", "aria-live": "polite", hidden: true });
  card.append(lista, explicacao);
  let tentativas = 0;
  let resolvida = false;

  for (const alt of ordem) {
    const btn = el("button", { class: "qz-alt", type: "button", html: md(alt.texto).replace(/^<p>|<\/p>$/g, "") });
    btn.addEventListener("click", () => {
      if (resolvida || btn.disabled) return;
      tentativas += 1;
      const certa = alt.i === q.correta;
      if (certa) {
        resolvida = true;
        btn.classList.add("certa");
        ctx.efeitos.acerto(btn);
        lista.querySelectorAll("button").forEach((b) => { b.disabled = true; });
        explicacao.className = "qz-explicacao ok";
        explicacao.innerHTML = `<b>${tentativas === 1 ? "Certo de primeira! 🎯" : "Isso!"}</b> ${md(q.explicacao)}`;
        explicacao.hidden = false;
        aoTerminar({ primeira: tentativas === 1 });
        return;
      }
      btn.classList.add("errada");
      btn.disabled = true;
      ctx.efeitos.erro(btn);
      if (modo === "quiz") {
        resolvida = true;
        lista.querySelectorAll("button").forEach((b) => { b.disabled = true; });
        const correta = [...lista.children][ordem.findIndex((o) => o.i === q.correta)];
        correta.classList.add("certa", "revelada");
        explicacao.className = "qz-explicacao erro";
        explicacao.innerHTML = `<b>Não foi dessa vez.</b> ${md(q.explicacao)}`;
        explicacao.hidden = false;
        aoTerminar({ primeira: false });
      } else {
        explicacao.className = "qz-explicacao erro";
        explicacao.innerHTML = "<b>Ainda não.</b> Releia o contexto e tente outra opção.";
        explicacao.hidden = false;
      }
    });
    lista.append(btn);
  }
  return card;
}
