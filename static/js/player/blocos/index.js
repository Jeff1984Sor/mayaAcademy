// Registro de componentes: tipo do bloco → componente. Para um tipo novo,
// crie o arquivo e adicione uma linha aqui (e o schema em cursos/blocos.py).

import { cena_narrada } from "./cena_narrada.js";
import { dialogo } from "./dialogo.js";
import { chat_simulado } from "./chat_simulado.js";
import { antes_depois } from "./antes_depois.js";
import { arrastar_soltar } from "./arrastar_soltar.js";
import { montador } from "./montador.js";
import { caca_erro } from "./caca_erro.js";
import { cenario_ramificado } from "./cenario_ramificado.js";
import { flashcards } from "./flashcards.js";
import { quiz_fixacao } from "./quiz_fixacao.js";
import { missao } from "./missao.js";
import { texto_apoio } from "./texto_apoio.js";

export const COMPONENTES = {
  cena_narrada, dialogo, chat_simulado, antes_depois, arrastar_soltar, montador,
  caca_erro, cenario_ramificado, flashcards, quiz_fixacao, missao, texto_apoio,
};
