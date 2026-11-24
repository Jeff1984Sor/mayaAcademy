// Ponto de entrada: expõe window.MayaPlayer para as páginas (Django e pacote baixado).

import { montarAula } from "./motor.js";

window.MayaPlayer = { montarAula };
