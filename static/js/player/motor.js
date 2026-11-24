// Motor genérico do player: lê os blocos da aula e renderiza cada um pelo tipo.
// Não depende do servidor: o ambiente (Django, pacote SCORM, prévia do Estúdio)
// injeta callbacks em `opcoes`. Uso:
//   MayaPlayer.montarAula(container, dadosAula, { aoProgresso, aoConcluir, aoSair, retomarEm })

import { el, esc, md, anunciar, animar, reduzMovimento } from "./util.js";
import { criarAvatar } from "./avatar.js";
import { Narracao } from "./narracao.js";
import { confete, somParabens, acerto, erro, somAcerto, somErro } from "./efeitos.js";
import { COMPONENTES } from "./blocos/index.js";

const VELOCIDADES = [1, 1.25, 1.5, 0.75];

function falaComEnfase(texto) {
  return esc(texto).replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

export function montarAula(raiz, dados, opcoes = {}) {
  const blocos = dados.blocos || [];
  const personagens = dados.personagens || {};
  const estado = {
    atual: -1,
    concluidos: new Set(opcoes.concluidos || []),
    resultados: {},
    componente: null,
    legendas: localStorage.getItem("maya-legendas") !== "off",
    velocidade: 0,
  };

  raiz.innerHTML = "";
  raiz.classList.add("player");
  if (dados.curso?.cor_primaria) raiz.style.setProperty("--curso-primaria", dados.curso.cor_primaria);
  if (dados.curso?.cor_secundaria) raiz.style.setProperty("--curso-secundaria", dados.curso.cor_secundaria);

  // ---------- estrutura ----------
  const audio = el("audio", { preload: "auto", class: "pl-audio" });
  const narr = new Narracao(audio);

  const progresso = el("ol", { class: "pl-progresso", "aria-label": "Blocos da aula" });
  const contador = el("span", { class: "pl-contador" });
  const btnSair = opcoes.aoSair
    ? el("button", { class: "pl-icone", type: "button", "aria-label": "Sair da aula", onclick: () => { narr.parar(); opcoes.aoSair(); } }, "←")
    : null;
  const btnTema = el("button", {
    class: "pl-icone", type: "button", "aria-label": "Alternar modo escuro",
    onclick: () => {
      const escuro = document.documentElement.dataset.tema !== "escuro";
      document.documentElement.dataset.tema = escuro ? "escuro" : "claro";
      localStorage.setItem("maya-tema", escuro ? "escuro" : "claro");
    },
  }, "◐");
  const btnSom = el("button", {
    class: "pl-icone", type: "button", "aria-label": "Sons de efeito (acerto, erro, parabéns)",
    onclick: () => {
      const off = document.documentElement.dataset.som !== "off";
      document.documentElement.dataset.som = off ? "off" : "on";
      localStorage.setItem("maya-som", off ? "off" : "on");
      btnSom.textContent = off ? "🔇" : "🔊";
    },
  }, document.documentElement.dataset.som === "off" ? "🔇" : "🔊");

  const topo = el("header", { class: "pl-topo" },
    btnSair,
    el("div", { class: "pl-titulo" },
      el("small", { text: dados.curso?.titulo || "" }),
      el("h1", { text: dados.aula?.titulo || "" })),
    el("div", { class: "pl-acoes" }, contador, btnSom, btnTema),
  );

  const palco = el("main", { class: "pl-palco", tabindex: "-1" });

  // Barra de narração
  const btnPlay = el("button", { class: "pl-play", type: "button", "aria-label": "Tocar narração", onclick: () => narr.alternar() }, "▶");
  const btnReplay = el("button", { class: "pl-icone", type: "button", "aria-label": "Ouvir de novo", onclick: () => { narr.irPara(0); narr.tocar(); } }, "↺");
  const barra = el("input", { type: "range", class: "pl-barra", min: "0", max: "1000", value: "0", "aria-label": "Posição da narração" });
  barra.addEventListener("input", () => narr.irPara((barra.value / 1000) * narr.duracao));
  const btnVel = el("button", { class: "pl-chip", type: "button", "aria-label": "Velocidade da narração", onclick: () => {
    estado.velocidade = (estado.velocidade + 1) % VELOCIDADES.length;
    narr.definirVelocidade(VELOCIDADES[estado.velocidade]);
    btnVel.textContent = `${VELOCIDADES[estado.velocidade]}×`;
  } }, "1×");
  const btnCC = el("button", { class: "pl-chip", type: "button", "aria-pressed": String(estado.legendas), "aria-label": "Legendas", onclick: () => {
    estado.legendas = !estado.legendas;
    localStorage.setItem("maya-legendas", estado.legendas ? "on" : "off");
    btnCC.setAttribute("aria-pressed", String(estado.legendas));
    legenda.hidden = !estado.legendas;
  } }, "CC");
  const btnTranscricao = el("button", { class: "pl-chip", type: "button", "aria-label": "Transcrição", onclick: () => abrirTranscricao() }, "☰", el("span", { class: "pl-chip-texto", text: " Transcrição" }));
  const legenda = el("p", { class: "pl-legenda", "aria-live": "polite" });
  legenda.hidden = !estado.legendas;
  const barraNarr = el("section", { class: "pl-narracao", "aria-label": "Narração" },
    el("div", { class: "pl-controles" }, btnPlay, btnReplay, barra, btnVel, btnCC, btnTranscricao),
    legenda,
  );

  const btnAnterior = el("button", { class: "pl-btn pl-btn-sec", type: "button", onclick: () => ir(estado.atual - 1) }, "Anterior");
  const btnProximo = el("button", { class: "pl-btn", type: "button", onclick: () => avancar() }, "Próximo");
  const dica = el("span", { class: "pl-dica", "aria-live": "polite" });
  const nav = el("footer", { class: "pl-nav" }, btnAnterior, dica, btnProximo);

  const transcricao = el("dialog", { class: "pl-dialogo", "aria-label": "Transcrição" });
  const anuncio = el("div", { id: "anuncio-sr", class: "sr-only", "aria-live": "assertive" });

  raiz.append(topo, palco, barraNarr, nav, transcricao, anuncio, audio);

  blocos.forEach((b, i) => {
    progresso.append(el("li", { "data-i": i, title: b.titulo || "" }));
  });
  topo.append(progresso);

  // ---------- narração → interface (re-registrado a cada bloco) ----------
  function ouvintesInterface() {
    narr.on("estado", (tocando) => {
      btnPlay.textContent = tocando ? "❚❚" : "▶";
      btnPlay.setAttribute("aria-label", tocando ? "Pausar narração" : "Tocar narração");
    });
    narr.on("tempo", (t, d) => { if (d) barra.value = String(Math.round((t / d) * 1000)); });
    narr.on("frase", (_i, item, ultima) => {
      if (!ultima) return;
      const nome = personagens[item.personagem]?.nome;
      legenda.innerHTML = `${nome ? `<b>${esc(nome)}:</b> ` : ""}${falaComEnfase(item.texto)}`;
    });
  }

  // ---------- contexto passado aos componentes ----------
  const ctx = {
    personagens,
    narracao: narr,
    reduzMovimento,
    md, el, esc, animar, anunciar,
    efeitos: { acerto, erro, confete, somAcerto, somErro },
    concluir(resultado = {}) {
      const b = blocos[estado.atual];
      if (!b) return;
      estado.resultados[b.id] = resultado;
      marcarConcluido(estado.atual);
    },
    personagemPadrao(slug) {
      if (slug && personagens[slug]) return personagens[slug];
      return Object.values(personagens).find((p) => p.papel === "mascote") || Object.values(personagens)[0] || null;
    },
    avatar(personagem, opts) { return criarAvatar(personagem, opts); },
    // Faz o avatar "falar" quando a frase atual é do personagem (ou de qualquer um, se slug for null).
    vincularAvatar(av, slug) {
      let falandoAgora = false;
      narr.on("frase", (_i, item, ultima) => {
        if (!ultima) return;
        falandoAgora = !slug || item.personagem === slug;
      });
      narr.on("estado", (tocando) => av.estado(tocando && falandoAgora ? "falando" : "neutro"));
      narr.on("boca", (nivel) => av.abrirBoca(falandoAgora ? nivel : 0));
      narr.on("fim", () => { av.estado("neutro"); av.abrirBoca(0); });
    },
  };

  // ---------- navegação ----------
  function interativosPendentes() {
    return blocos.filter((b, i) => b.interativo && !estado.concluidos.has(i));
  }

  function marcarConcluido(i) {
    if (estado.concluidos.has(i)) { atualizarNav(); return; }
    estado.concluidos.add(i);
    progresso.children[i]?.classList.add("feito");
    opcoes.aoProgresso?.({ bloco: blocos[i].id, indice: i, concluidos: [...estado.concluidos], resultados: estado.resultados });
    atualizarNav();
  }

  function atualizarNav() {
    const b = blocos[estado.atual];
    const ultimo = estado.atual === blocos.length - 1;
    btnAnterior.disabled = estado.atual <= 0;
    const bloqueado = b?.interativo && !estado.concluidos.has(estado.atual);
    if (ultimo) {
      const pend = interativosPendentes();
      btnProximo.textContent = "Concluir aula";
      btnProximo.disabled = pend.length > 0;
      dica.textContent = pend.length ? `Falta concluir: ${pend.map((p) => p.titulo || "atividade").join(", ")}` : "";
    } else {
      btnProximo.textContent = "Próximo";
      btnProximo.disabled = Boolean(bloqueado);
      dica.textContent = bloqueado ? "Conclua a atividade para continuar" : "";
    }
    contador.textContent = `${estado.atual + 1}/${blocos.length}`;
    [...progresso.children].forEach((li, j) => {
      li.classList.toggle("atual", j === estado.atual);
      li.classList.toggle("feito", estado.concluidos.has(j));
    });
  }

  function ir(i) {
    if (i < 0 || i >= blocos.length) return;
    narr.parar();
    narr.limparOuvintes();
    ouvintesInterface();

    estado.componente?.destruir?.();
    estado.atual = i;
    const bloco = blocos[i];
    narr.carregar(bloco);
    legenda.textContent = "";
    barra.value = "0";
    barraNarr.hidden = !narr.temNarracao;

    palco.innerHTML = "";
    const quadro = el("article", { class: `bloco bloco-${bloco.tipo}`, "aria-labelledby": `bt-${bloco.id}` });
    quadro.append(el("h2", { id: `bt-${bloco.id}`, class: "bloco-titulo", text: bloco.titulo || "" }));
    if (bloco.alem_do_pdf && opcoes.mostrarSelos) {
      quadro.append(el("p", { class: "selo-revisao", text: "⚠ conteúdo além do PDF" }));
    }
    if (bloco.texto_tela && bloco.tipo !== "texto_apoio") {
      quadro.append(el("div", { class: "bloco-intro", html: md(bloco.texto_tela) }));
    }
    const corpo = el("div", { class: "bloco-corpo" });
    quadro.append(corpo);
    palco.append(quadro);

    const comp = COMPONENTES[bloco.tipo];
    if (!comp) {
      corpo.append(el("p", { class: "aviso", text: `Tipo de bloco não suportado: ${bloco.tipo}` }));
      estado.componente = null;
    } else {
      estado.componente = comp.montar(corpo, bloco, ctx) || null;
    }
    if (!bloco.interativo) marcarConcluido(i);

    animar(quadro, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.45 });
    atualizarNav();
    // Na prévia do Estúdio (iframe) o foco não pode sair do editor.
    if (!opcoes.semFoco) {
      palco.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: reduzMovimento() ? "auto" : "smooth" });
    }
    anunciar(`Bloco ${i + 1} de ${blocos.length}: ${bloco.titulo || ""}`);
    if (narr.temNarracao && estado.iniciado) narr.tocar();
    opcoes.aoBloco?.(i);
  }

  function avancar() {
    if (estado.atual < blocos.length - 1) { ir(estado.atual + 1); return; }
    if (interativosPendentes().length) return;
    concluirAula();
  }

  function concluirAula() {
    narr.parar();
    estado.componente?.destruir?.();
    const mascote = ctx.personagemPadrao();
    const av = criarAvatar(mascote, { tamanho: 150 });
    const acertos = Object.values(estado.resultados).reduce((s, r) => s + (r.acertosPrimeira || 0), 0);
    palco.innerHTML = "";
    const tela = el("section", { class: "conclusao" },
      av.el,
      el("h2", { text: "Aula concluída!" }),
      el("p", { class: "conclusao-xp", text: `+${dados.aula?.xp || 0} XP` }),
      acertos ? el("p", { text: `${acertos} acerto(s) de primeira nos quizzes` }) : null,
      el("div", { class: "conclusao-acoes" },
        el("button", { class: "pl-btn pl-btn-sec", type: "button", onclick: () => { estado.iniciado = true; nav.hidden = false; ir(0); } }, "Rever aula"),
        opcoes.aoSair ? el("button", { class: "pl-btn", type: "button", onclick: () => opcoes.aoSair() }, opcoes.rotuloSair || "Continuar") : null,
      ),
    );
    palco.append(tela);
    barraNarr.hidden = true;
    nav.hidden = true;
    av.estado("comemorando");
    confete(raiz);
    somParabens();
    anunciar("Aula concluída! Parabéns!");
    opcoes.aoConcluir?.({ aula: dados.aula?.id, resultados: estado.resultados, xp: dados.aula?.xp || 0 });
  }

  function abrirTranscricao() {
    const b = blocos[estado.atual];
    const linhas = [];
    let falaAtual = -1;
    for (const item of b?.timeline || []) {
      if (item.fala !== falaAtual) {
        falaAtual = item.fala;
        linhas.push({ personagem: item.personagem, textos: [] });
      }
      linhas[linhas.length - 1].textos.push(item.texto);
    }
    transcricao.innerHTML = "";
    transcricao.append(
      el("h2", { text: `Transcrição — ${b?.titulo || ""}` }),
      ...linhas.map((l) => el("p", { html: `<b>${esc(personagens[l.personagem]?.nome || l.personagem)}:</b> ${falaComEnfase(l.textos.join(" "))}` })),
      el("button", { class: "pl-btn", type: "button", onclick: () => transcricao.close() }, "Fechar"),
    );
    transcricao.showModal();
  }

  // Atalhos: K = tocar/pausar, C = legendas, setas = navegar (fora de campos de formulário)
  const teclas = (ev) => {
    if (ev.target.closest("input, textarea, select, [contenteditable]") || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "k" || ev.key === "K") { ev.preventDefault(); narr.alternar(); }
    if (ev.key === "c" || ev.key === "C") btnCC.click();
    if (ev.key === "ArrowRight" && !btnProximo.disabled && !ev.target.closest(".bloco-corpo")) btnProximo.click();
    if (ev.key === "ArrowLeft" && !btnAnterior.disabled && !ev.target.closest(".bloco-corpo")) btnAnterior.click();
  };
  document.addEventListener("keydown", teclas);

  // ---------- início: tela "Começar" desbloqueia o áudio (iOS/Android) ----------
  const inicio = Math.min(Math.max(opcoes.retomarEm || 0, 0), Math.max(blocos.length - 1, 0));
  if (!blocos.length) {
    palco.append(el("p", { class: "aviso", text: "Esta aula ainda não tem blocos." }));
    nav.hidden = true; barraNarr.hidden = true;
    return { destruir() {} };
  }
  if (opcoes.semTelaInicial) {
    estado.iniciado = true;
    ir(inicio);
  } else {
    barraNarr.hidden = true;
    nav.hidden = true;
    const mascote = ctx.personagemPadrao();
    const av = criarAvatar(mascote, { tamanho: 140 });
    const comecar = el("button", { class: "pl-btn pl-btn-grande", type: "button" }, inicio > 0 ? "Continuar de onde parei" : "Começar aula");
    comecar.addEventListener("click", () => {
      estado.iniciado = true;
      audio.play().catch(() => {}); audio.pause(); // desbloqueio
      nav.hidden = false;
      ir(inicio);
    });
    palco.append(el("section", { class: "inicio-aula" },
      av.el,
      el("h2", { text: dados.aula?.titulo || "" }),
      dados.aula?.objetivo ? el("p", { text: dados.aula.objetivo }) : null,
      el("p", { class: "inicio-dica", text: "🎧 Esta aula tem narração. Use fones ou aumente o volume. Legendas e transcrição estão disponíveis." }),
      comecar,
    ));
    av.estado("neutro");
    if (!opcoes.semFoco) comecar.focus();
  }

  return {
    ir,
    destruir() {
      narr.parar();
      estado.componente?.destruir?.();
      document.removeEventListener("keydown", teclas);
      raiz.innerHTML = "";
    },
  };
}

// Preferências salvas (tema, som) aplicadas antes de montar.
(function aplicarPreferencias() {
  const tema = localStorage.getItem("maya-tema");
  if (tema) document.documentElement.dataset.tema = tema;
  const somPref = localStorage.getItem("maya-som");
  if (somPref) document.documentElement.dataset.som = somPref;
})();
