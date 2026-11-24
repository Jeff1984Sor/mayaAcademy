// Mascote geométrico original da plataforma, em SVG inline.
// Estados: neutro, falando, pensando, comemorando, alerta (classe .estado-<nome>).
// A boca é uma elipse cujo raio vertical é controlado por abrirBoca(0..1).

import { reduzMovimento } from "./util.js";

const NS = "http://www.w3.org/2000/svg";

function forma(tipo, cor) {
  // "maya": hexágono arredondado; "coruja": círculo com "orelhas" triangulares; "robo": quadrado.
  if (tipo === "robo") {
    return `<rect x="22" y="26" width="76" height="70" rx="16" fill="${cor}"/>
            <rect x="56" y="10" width="8" height="16" rx="4" fill="${cor}"/><circle cx="60" cy="10" r="6" fill="var(--avatar-destaque)"/>`;
  }
  if (tipo === "coruja") {
    return `<path d="M26 34 L38 14 L50 30 Z M94 34 L82 14 L70 30 Z" fill="${cor}"/>
            <circle cx="60" cy="60" r="38" fill="${cor}"/>`;
  }
  return `<path d="M60 14 L96 34 Q100 36 100 41 L100 79 Q100 84 96 86 L60 106 Q60 106 24 86 Q20 84 20 79 L20 41 Q20 36 24 34 Z" fill="${cor}"/>`;
}

export function criarAvatar(personagem, { tamanho = 120 } = {}) {
  const cor = personagem?.cor || "var(--cor-primaria)";
  const tipo = personagem?.avatar_padrao || "maya";
  const wrap = document.createElement("div");
  wrap.className = "avatar estado-neutro";
  wrap.style.setProperty("--tam", `${tamanho}px`);
  wrap.setAttribute("role", "img");
  wrap.setAttribute("aria-label", personagem ? `${personagem.nome}` : "Mascote");

  if (personagem?.avatar && /\.svg$/i.test(personagem.avatar)) {
    const img = document.createElement("img");
    img.src = personagem.avatar;
    img.alt = "";
    wrap.append(img);
    return { el: wrap, estado: (e) => definirEstado(wrap, e), abrirBoca: () => {} };
  }

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 120 120");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = `
    <g class="av-corpo">
      ${forma(tipo, cor)}
      <path class="av-brilho" d="M40 34 Q52 26 66 28" stroke="#fff" stroke-opacity=".35" stroke-width="5" fill="none" stroke-linecap="round"/>
      <g class="av-olhos">
        <ellipse class="av-olho" cx="45" cy="56" rx="9" ry="10" fill="#fff"/>
        <ellipse class="av-olho" cx="75" cy="56" rx="9" ry="10" fill="#fff"/>
        <circle class="av-pupila" cx="46" cy="57" r="4.5" fill="#1f1235"/>
        <circle class="av-pupila" cx="76" cy="57" r="4.5" fill="#1f1235"/>
      </g>
      <path class="av-sobrancelha" d="M36 42 L52 40 M68 40 L84 42" stroke="#1f1235" stroke-width="3" stroke-linecap="round"/>
      <ellipse class="av-boca" cx="60" cy="80" rx="10" ry="2.5" fill="#1f1235"/>
      <circle class="av-bochecha" cx="33" cy="72" r="5" fill="#fff" fill-opacity=".25"/>
      <circle class="av-bochecha" cx="87" cy="72" r="5" fill="#fff" fill-opacity=".25"/>
    </g>`;
  wrap.append(svg);
  const boca = svg.querySelector(".av-boca");

  return {
    el: wrap,
    estado: (e) => definirEstado(wrap, e),
    abrirBoca(nivel) {
      const n = Math.max(0, Math.min(1, nivel));
      boca.setAttribute("ry", (2.5 + n * 8).toFixed(1));
      boca.setAttribute("rx", (10 - n * 2).toFixed(1));
    },
  };
}

function definirEstado(wrap, estado) {
  wrap.className = wrap.className.replace(/estado-\S+/g, "").trim() + ` estado-${estado || "neutro"}`;
  if (estado === "comemorando" && window.gsap && !reduzMovimento()) {
    window.gsap.fromTo(wrap, { y: 0 }, { y: -14, duration: 0.25, yoyo: true, repeat: 3, ease: "power1.out" });
  }
}
