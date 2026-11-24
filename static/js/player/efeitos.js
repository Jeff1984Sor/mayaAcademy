// Micro-animações de acerto/erro, confete e sons curtos (Web Audio, sem arquivos).

import { reduzMovimento } from "./util.js";

let ctxSom = null;
function som() {
  if (document.documentElement.dataset.som === "off") return null;
  try {
    ctxSom = ctxSom || new (window.AudioContext || window.webkitAudioContext)();
    return ctxSom;
  } catch (_) { return null; }
}

function nota(ctx, freq, inicio, dur, volume = 0.08, tipo = "sine") {
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = tipo;
  osc.frequency.value = freq;
  g.gain.setValueAtTime(0, ctx.currentTime + inicio);
  g.gain.linearRampToValueAtTime(volume, ctx.currentTime + inicio + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + inicio + dur);
  osc.connect(g).connect(ctx.destination);
  osc.start(ctx.currentTime + inicio);
  osc.stop(ctx.currentTime + inicio + dur + 0.05);
}

export function somAcerto() {
  const c = som(); if (!c) return;
  nota(c, 660, 0, 0.12); nota(c, 880, 0.09, 0.18);
}

export function somErro() {
  const c = som(); if (!c) return;
  nota(c, 220, 0, 0.18, 0.06, "triangle");
}

export function somParabens() {
  const c = som(); if (!c) return;
  [523, 659, 784, 1047].forEach((f, i) => nota(c, f, i * 0.12, 0.3, 0.07));
  nota(c, 1319, 0.5, 0.6, 0.05);
}

export function acerto(el) {
  el.classList.add("fx-acerto");
  somAcerto();
  if (window.gsap && !reduzMovimento()) {
    window.gsap.fromTo(el, { scale: 0.96 }, { scale: 1, duration: 0.35, ease: "back.out(3)", clearProps: "transform" });
  }
}

export function erro(el) {
  el.classList.add("fx-erro");
  somErro();
  if (window.gsap && !reduzMovimento()) {
    window.gsap.fromTo(el, { x: 0 }, { x: 8, duration: 0.07, repeat: 5, yoyo: true, ease: "none", clearProps: "transform" });
  }
  setTimeout(() => el.classList.remove("fx-erro"), 700);
}

export function confete(alvo = document.body, quantidade = 120) {
  if (reduzMovimento()) return;
  const canvas = document.createElement("canvas");
  canvas.className = "confete";
  canvas.setAttribute("aria-hidden", "true");
  alvo.append(canvas);
  const ctx = canvas.getContext("2d");
  const ret = canvas.getBoundingClientRect();
  canvas.width = ret.width * devicePixelRatio;
  canvas.height = ret.height * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const cores = [getComputedStyle(document.documentElement).getPropertyValue("--cor-primaria").trim() || "#6D28D9",
    getComputedStyle(document.documentElement).getPropertyValue("--cor-secundaria").trim() || "#F59E0B",
    "#10B981", "#3B82F6", "#EC4899"];
  const pecas = Array.from({ length: quantidade }, () => ({
    x: ret.width / 2 + (Math.random() - 0.5) * 80,
    y: ret.height * 0.35,
    vx: (Math.random() - 0.5) * 12,
    vy: -Math.random() * 12 - 4,
    r: Math.random() * Math.PI,
    vr: (Math.random() - 0.5) * 0.3,
    w: 6 + Math.random() * 6,
    h: 8 + Math.random() * 8,
    cor: cores[Math.floor(Math.random() * cores.length)],
  }));
  const inicio = performance.now();
  const quadro = (agora) => {
    const t = agora - inicio;
    ctx.clearRect(0, 0, ret.width, ret.height);
    for (const p of pecas) {
      p.vy += 0.35; p.vx *= 0.99; p.x += p.vx; p.y += p.vy; p.r += p.vr;
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.r);
      ctx.globalAlpha = Math.max(0, 1 - t / 2600);
      ctx.fillStyle = p.cor;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }
    if (t < 2600) requestAnimationFrame(quadro);
    else canvas.remove();
  };
  requestAnimationFrame(quadro);
}
