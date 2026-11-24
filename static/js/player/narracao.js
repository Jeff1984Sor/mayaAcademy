// Controlador de narração: um único <audio> compartilhado (desbloqueado no
// primeiro toque, exigência do iOS) ou, sem áudio, um relógio que percorre a
// timeline estimada. Emite eventos por frase para sincronizar animação e legenda.

export class Narracao {
  constructor(audioEl) {
    this.audio = audioEl;
    this.timeline = [];
    this.ouvintes = { frase: [], fim: [], estado: [], tempo: [], boca: [] };
    this.indice = -1;
    this.relogio = null;
    this.tempo = 0;
    this.duracao = 0;
    this.tocando = false;
    this.velocidade = 1;
    this.analisador = null;
    this.dadosFreq = null;
    this._raf = null;

    // Eventos do <audio> só valem quando o bloco tem MP3. Sem isso, o "play/pause" de
    // desbloqueio (botão Começar) chega atrasado e pararia o relógio da narração estimada.
    this.audio.addEventListener("timeupdate", () => { if (this.comAudio) this._tick(this.audio.currentTime); });
    this.audio.addEventListener("ended", () => { if (this.comAudio) this._terminou(); });
    this.audio.addEventListener("play", () => { if (this.comAudio) this._estado(true); });
    this.audio.addEventListener("pause", () => { if (this.comAudio) this._estado(false); });
  }

  on(evento, fn) { this.ouvintes[evento].push(fn); }
  limparOuvintes() { for (const k in this.ouvintes) this.ouvintes[k] = []; }
  _emitir(evento, ...args) { for (const fn of this.ouvintes[evento]) fn(...args); }

  carregar(bloco) {
    this.parar();
    this.timeline = bloco.timeline || [];
    this.duracao = bloco.duracao || 0;
    this.indice = -1;
    this.tempo = 0;
    this.comAudio = Boolean(bloco.audio);
    if (this.comAudio) {
      this.audio.src = bloco.audio;
      this.audio.playbackRate = this.velocidade;
    } else {
      this.audio.removeAttribute("src");
    }
  }

  get temNarracao() { return this.timeline.length > 0; }

  async tocar() {
    if (!this.temNarracao) return;
    if (this.tempo >= this.duracao - 0.05) this.irPara(0);
    if (this.comAudio) {
      this._prepararAnalisador();
      try { await this.audio.play(); } catch (_) { this._estado(false); }
    } else {
      this._estado(true);
      let ultimo = performance.now();
      const passo = (agora) => {
        if (!this.tocando) return;
        this.tempo += ((agora - ultimo) / 1000) * this.velocidade;
        ultimo = agora;
        this._tick(this.tempo);
        if (this.tempo >= this.duracao) { this._terminou(); return; }
        this.relogio = requestAnimationFrame(passo);
      };
      this.relogio = requestAnimationFrame(passo);
    }
    this._loopBoca();
  }

  pausar() {
    if (this.comAudio) this.audio.pause();
    else { cancelAnimationFrame(this.relogio); this._estado(false); }
  }

  alternar() { this.tocando ? this.pausar() : this.tocar(); }

  parar() {
    this.pausar();
    cancelAnimationFrame(this._raf);
    if (this.comAudio) { try { this.audio.currentTime = 0; } catch (_) {} }
    this.tempo = 0;
  }

  irPara(segundos) {
    this.tempo = Math.max(0, Math.min(segundos, this.duracao));
    this.indice = -1;
    if (this.comAudio) this.audio.currentTime = this.tempo;
    this._tick(this.tempo);
  }

  definirVelocidade(v) {
    this.velocidade = v;
    this.audio.playbackRate = v;
  }

  _estado(tocando) {
    this.tocando = tocando;
    this._emitir("estado", tocando);
  }

  _tick(t) {
    this.tempo = t;
    this._emitir("tempo", t, this.duracao);
    let atual = -1;
    for (let i = 0; i < this.timeline.length; i++) {
      if (t >= this.timeline[i].inicio) atual = i;
      else break;
    }
    if (atual !== this.indice && atual >= 0) {
      // Dispara também as frases puladas (ex.: arrastar a barra), em ordem.
      const de = this.indice < atual ? this.indice + 1 : atual;
      for (let i = de; i <= atual; i++) this._emitir("frase", i, this.timeline[i], i === atual);
      this.indice = atual;
    }
  }

  _terminou() {
    cancelAnimationFrame(this.relogio);
    this.tempo = this.duracao;
    this._estado(false);
    this._emitir("fim");
  }

  // Nível de abertura da boca (0..1) — amplitude real se possível, senão simulado.
  nivelBoca() {
    if (!this.tocando) return 0;
    const frase = this.timeline[this.indice];
    if (!frase || this.tempo > frase.fim) return 0;
    if (this.analisador) {
      this.analisador.getByteFrequencyData(this.dadosFreq);
      let soma = 0;
      for (let i = 2; i < 40; i++) soma += this.dadosFreq[i];
      return Math.min(1, soma / (38 * 150));
    }
    return 0.25 + 0.6 * Math.abs(Math.sin(this.tempo * 13) * Math.sin(this.tempo * 7.3));
  }

  _prepararAnalisador() {
    // Em file:// (pacote baixado) o navegador silenciaria o áudio roteado pelo
    // Web Audio; nesse caso a boca usa a animação simulada.
    if (this.analisador || !window.AudioContext || !/^https?:$/.test(location.protocol)) return;
    try {
      const ctx = new AudioContext();
      const fonte = ctx.createMediaElementSource(this.audio);
      this.analisador = ctx.createAnalyser();
      this.analisador.fftSize = 256;
      this.dadosFreq = new Uint8Array(this.analisador.frequencyBinCount);
      fonte.connect(this.analisador);
      this.analisador.connect(ctx.destination);
      this.ctxAudio = ctx;
    } catch (_) {
      this.analisador = null;
    }
  }

  _loopBoca() {
    cancelAnimationFrame(this._raf);
    const loop = () => {
      this._emitir("boca", this.nivelBoca());
      if (this.tocando) this._raf = requestAnimationFrame(loop);
      else this._emitir("boca", 0);
    };
    this._raf = requestAnimationFrame(loop);
  }
}
