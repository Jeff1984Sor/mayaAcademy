// Chat encenado com indicador de digitação e efeito de escrita nas respostas da IA.

import { esperar } from "../util.js";

export const chat_simulado = {
  montar(corpo, bloco, ctx) {
    const { el, md } = ctx;
    const cfg = bloco.config || {};
    const nomes = { usuario: cfg.nome_usuario || "Você", ia: cfg.nome_ia || "Assistente de IA", sistema: "" };
    const janela = el("div", { class: "chat", role: "log", "aria-label": cfg.titulo || "Conversa simulada" });
    const cabecalho = el("div", { class: "chat-topo" }, el("span", { class: "chat-ponto" }), el("strong", { text: cfg.titulo || nomes.ia }));
    const lista = el("div", { class: "chat-lista" });
    const btnRepetir = el("button", { class: "pl-btn pl-btn-sec", type: "button", hidden: true }, "↺ Rever conversa");
    const btnPular = el("button", { class: "pl-link", type: "button" }, "Mostrar tudo");
    janela.append(cabecalho, lista);
    corpo.append(janela, el("div", { class: "chat-acoes" }, btnPular, btnRepetir));

    let cancelado = false;
    let pular = false;
    const rolar = () => { lista.scrollTop = lista.scrollHeight; };

    const escrever = async (alvo, texto) => {
      if (pular || ctx.reduzMovimento()) { alvo.innerHTML = md(texto); return; }
      const palavras = texto.split(/(\s+)/);
      let acumulado = "";
      for (const p of palavras) {
        if (cancelado || pular) break;
        acumulado += p;
        alvo.innerHTML = md(acumulado);
        rolar();
        await esperar(p.trim() ? 38 : 0);
      }
      alvo.innerHTML = md(texto);
    };

    const rodar = async () => {
      cancelado = false; pular = false;
      lista.innerHTML = "";
      btnRepetir.hidden = true; btnPular.hidden = false;
      for (const m of cfg.mensagens || []) {
        if (cancelado) return;
        if (m.de === "sistema") {
          lista.append(el("p", { class: "chat-sistema", text: m.texto }));
          continue;
        }
        if (m.de === "ia" && !pular) {
          const digitando = el("div", { class: "chat-msg chat-ia chat-digitando", "aria-label": `${nomes.ia} digitando` }, el("i"), el("i"), el("i"));
          lista.append(digitando); rolar();
          await esperar(900);
          digitando.remove();
        } else if (!pular) {
          await esperar(500);
        }
        if (cancelado) return;
        const balao = el("div", { class: `chat-msg chat-${m.de}` });
        const texto = el("div", { class: "chat-texto" });
        balao.append(el("small", { text: nomes[m.de] }), texto);
        lista.append(balao);
        ctx.animar(balao, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.3 });
        if (m.de === "ia") await escrever(texto, m.texto);
        else texto.innerHTML = md(m.texto);
        if (m.nota) {
          const nota = el("div", { class: `chat-nota chat-nota-${m.nota_tipo || "alerta"}`, role: "note" },
            el("span", { "aria-hidden": "true", text: { alerta: "⚠️", ok: "✅", info: "💡" }[m.nota_tipo || "alerta"] }),
            el("span", { text: m.nota }));
          lista.append(nota);
          ctx.animar(nota, { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" });
        }
        rolar();
        if (!pular) await esperar(m.nota ? 1400 : 700);
      }
      btnRepetir.hidden = false; btnPular.hidden = true;
    };

    btnRepetir.addEventListener("click", rodar);
    btnPular.addEventListener("click", () => { pular = true; });
    rodar();
    return { destruir: () => { cancelado = true; } };
  },
};
