// Utilitários do player (sem dependências).

export const reduzMovimento = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
  document.documentElement.dataset.movimento === "reduzido";

export function esc(texto) {
  return String(texto ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Markdown mínimo e seguro: **negrito**, *itálico*, `código`, listas "- ", parágrafos.
export function md(texto) {
  const inline = (s) =>
    esc(s)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  const linhas = String(texto ?? "").split(/\r?\n/);
  let html = "";
  let lista = false;
  let paragrafo = [];
  const fecharP = () => {
    if (paragrafo.length) html += `<p>${inline(paragrafo.join(" "))}</p>`;
    paragrafo = [];
  };
  for (const linha of linhas) {
    const l = linha.trim();
    if (/^[-•]\s+/.test(l)) {
      fecharP();
      if (!lista) { html += "<ul>"; lista = true; }
      html += `<li>${inline(l.replace(/^[-•]\s+/, ""))}</li>`;
      continue;
    }
    if (lista) { html += "</ul>"; lista = false; }
    if (!l) fecharP();
    else paragrafo.push(l);
  }
  fecharP();
  if (lista) html += "</ul>";
  return html;
}

export function el(tag, attrs = {}, ...filhos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) {
    if (f === null || f === undefined || f === false) continue;
    n.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return n;
}

export function embaralhar(lista) {
  const a = [...lista];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export const esperar = (ms) => new Promise((r) => setTimeout(r, reduzMovimento() ? Math.min(ms, 60) : ms));

// Anima com GSAP se disponível e permitido; senão aplica o estado final direto.
export function animar(alvo, de, ate = {}) {
  const gsap = window.gsap;
  if (!gsap || reduzMovimento()) {
    if (ate.onComplete) ate.onComplete();
    return null;
  }
  return gsap.fromTo(alvo, de, { duration: 0.5, ease: "power2.out", ...ate, ...{ clearProps: ate.clearProps ?? "transform,opacity" } });
}

export function anunciar(texto) {
  const regiao = document.getElementById("anuncio-sr");
  if (regiao) {
    regiao.textContent = "";
    setTimeout(() => { regiao.textContent = texto; }, 30);
  }
}
