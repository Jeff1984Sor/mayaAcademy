# CLAUDE.md — MayaAcademy

> **Leia primeiro.** **MayaAcademy** (MayaCorp): plataforma de cursos online em que **nenhuma aula é só texto**. Cada aula é
> uma sequência de **blocos** (narração com TTS, cena animada, chat simulado, caça ao erro, cenários, quizzes...), com
> gamificação, prova final e certificado. O criador (Jefferson) monta cursos no **Estúdio**, importa roteiros YAML e,
> na F2.5, gera cursos a partir de **PDF**. Todo curso pode ser **baixado** (HTML5 + SCORM 1.2) para outras plataformas.
> Especificação: [`prompt-mayaacademy.md`](prompt-mayaacademy.md). Andamento e dúvidas: [`docs/PROGRESSO.md`](docs/PROGRESSO.md).

| Ambiente | Endereço | Pasta no servidor | Porta web | Banco | Branch |
|---|---|---|---|---|---|
| Produção (único) | `academy.mayacorp.com.br` | `/home/deploy/mayaacademy/prod` | 10081 | `mayaacademy_prod` | `main` |

**Sem homologação** (decisão do Jefferson em 24/11/2026). Os scripts ainda aceitam `hml`, mas não use.

**Servidor compartilhado** (o mesmo do Flicsales/MayaJus: `ssh flicsales`, usuário `deploy`, Ubuntu 24.04, PostgreSQL 16).
Regras: só **acrescentar** (nunca atualizar pacotes, reiniciar serviços alheios ou editar sites nginx de outros sistemas);
`nginx -t` antes de todo reload. O Redis da porta 6379 é do Evolution: **não usar**. A MayaAcademy tem o próprio
(container `mayaacademy-redis` em 127.0.0.1:6380, índices 0/1).

Ambiente único = produção, então o cuidado é dobrado: o `deploy.sh` roda os testes antes de reiniciar (se falharem, nada muda),
faz backup do banco antes de toda migration e cria a tag `vN` (ponto de retorno do `rollback.sh`). Deploy só quando o Jefferson mandar. Nenhum comando destrutivo (`DROP`, `flush`, `migrate zero`)
sem confirmação explícita. Nenhum dado real de cliente em exemplos/seeds (R6).

## Stack

- Python 3.12 + **Django 5.2** (apps por domínio, templates server-side, como o PilatesFinal/RCA), PostgreSQL, Celery + Redis.
- Front: templates + **Tailwind 3** (build no servidor, `npm run build:css`) + JS vanilla. Sem CDN em runtime: GSAP, Lottie,
  HTMX e fontes ficam em `static/` (R4).
- Gunicorn + systemd (`mayaacademy-web@<amb>`, `mayaacademy-worker@<amb>`) + nginx + Certbot. Ver `deploy/`.

## Mapa do código

- `config/` settings (`base`, `prod`, `test`), urls, celery. `.env` só com o que é de servidor (`.env.example`).
- `core/` usuário (login por e-mail, papéis aluno/gestor/criador/superadmin), organizações, **AuditLog imutável**
  (save/delete/update bloqueados), rate limit de login, `contexto.py` (menu do shell).
- `cursos/` modelos (Curso, Personagem, Modulo, Aula, BlocoAula, Questao) e o núcleo:
  - `blocos.py`: **registro dos tipos de bloco** (JSON Schema + validação extra + regra ≥4 blocos/≥2 interativos).
  - `roteiro.py`: parser `@slug: texto` → falas → frases (índice global usado na sincronização).
  - `audio.py` + `services/tts.py`: narração com controle por **hash do roteiro + vozes** (N10). Provedores `google` e `nulo`.
  - `roteiro_io.py`: importar/validar (erros com número da linha)/exportar YAML. `publicacao.py`: checklist N9 e versão.
  - `player.py`: JSON que o player consome. `bundle.py`: empacota o player em um script único.
  - `pacote.py`: **download do curso** (HTML5 + SCORM 1.2 num .zip).
- `geracao/` **gerador de curso por PDF** (F2.5): `pipeline.py` (extração+OCR → mapa → ementa → **gate do criador** →
  uma chamada por aula com validação e até 2 correções → relatório), `ia.py` (schemas de saída estrita), `falso.py`
  (IA sem rede para testes). Prompts versionados em `estudio/prompts/*.md`. IA isolada em `services/llm.py`
  (provedor **OpenAI**, `LLM_PROVIDER=openai`, modelo e preço no `.env`; cada chamada vira um `ChamadaLLM` com custo).
- `estudio/` área do criador (editor com formulário gerado do schema + prévia ao vivo, reordenação por arrastar, importador).
- `aprendizado/` página do player (matrícula/progresso entram na F3). `catalogo/` home ("em construção" até a F4) e `/saude/`.
- `static/js/player/` **player** em ES modules (motor genérico + um componente por tipo em `blocos/`). Nunca carregue os
  módulos direto: rode `manage.py montar_player` (gera `static/js/player.bundle.js`, que também vai no pacote SCORM e abre em `file://`).
- `static/css/player.css` CSS próprio do player (sem Tailwind, porque vai no pacote). `static/css/entrada.css` → Tailwind do resto.

### Criar um tipo de bloco novo

1. `cursos/blocos.py`: entrada em `TIPOS` (rótulo, interativo, schema, `extra` se precisar). 2. `cursos/exemplos.py`: config inicial.
3. `static/js/player/blocos/<tipo>.js` exportando `{ montar(corpo, bloco, ctx) }` e uma linha em `blocos/index.js`.
4. CSS em `player.css`. 5. Documente em `docs/formato-roteiro.md`. Interativo: chame `ctx.concluir({...})` ao terminar.

## Padrão MayaCorp

- Paleta: Navy `#1E2D6B`, Indigo `#7C8FFF`, Teal `#1A8F5E`, Amber `#F5A623`, Red `#C94343`, Dark `#0F1729`, Gray `#F7F8FC`.
  Fontes DM Sans + JetBrains Mono (locais, licença OFL em `static/fonts/`).
- Shell da área logada (`templates/app.html`): menu lateral escuro recolhível, topbar com busca **Ctrl+K**, tema
  claro/escuro/automático, toasts. Itens futuros aparecem como "em breve" (`core/contexto.py`).
- Cada curso tem cores próprias (white-label) no player; o padrão é Navy/Amber. No modo escuro, destaques em Indigo com texto escuro (AA).
- Textos em português claro, sem jargão. Permissões aplicadas no backend (`core/permissoes.py`).

## Como trabalhar

- Branch `main` = produção; trabalho em `feat/<assunto>` e merge na `main` quando aprovado. Nunca force-push na `main`.
- Commits pequenos, em português, dizendo o que muda e por quê.
- Antes de dar algo como pronto: `python -m pytest -q` verde (testes cobrem N9, N10, importador, permissões, pacote, bundle).
- Registre o andamento em `docs/PROGRESSO.md` (feito, falta, decisões, dúvidas para o Jefferson).
- Não commitar `.env`, PDFs de material (`/*.pdf`, `materiais/`), `media/`, `node_modules/`, `static/css/app.css`, `player.bundle.js`.

## Comandos

```bash
python -m pytest -q                                   # testes (settings de teste: SQLite em memória)
python manage.py montar_player                        # gera static/js/player.bundle.js
npm run build:css                                     # gera static/css/app.css
python manage.py importar_roteiro conteudo/ia-com-sabedoria-piloto.yaml [--validar] [--curso <slug>]
python manage.py exportar_roteiro <slug> -o saida.yaml
python manage.py gerar_audios_curso <slug> [--estimar] [--forcar]
./deploy/deploy.sh prod     ./deploy/rollback.sh prod v7     ./deploy/backup.sh prod
```
