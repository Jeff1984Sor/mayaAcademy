# MayaAcademy — Especificação para implementação (Claude Code)

> **Leia este documento inteiro antes de escrever qualquer código.**
> Siga a ordem de implementação da seção 12 e **pare nos gates** indicados para aprovação.
> Onde houver `<!-- DEFINIR -->`, pergunte antes de assumir. Onde houver `<!-- REVISAR -->`, implemente e sinalize no resumo final.

---

## 1. Contexto

**MayaAcademy** é um novo produto da **MayaCorp**: uma plataforma de cursos online onde o Jeff cria, publica e vende/distribui cursos.

O padrão de referência é o curso EAD **"Como usar a IA com sabedoria"**, feito para o RCACONNECT (RCA). Ele já validou o conceito: **nenhuma aula é 100% texto**. Toda aula é uma sequência de **blocos** com narração em áudio, cena animada e interação (chat simulado, arrastar e soltar, caça ao erro, cenários ramificados etc.), mais gamificação, prova final e certificado.

A diferença: lá era **um curso dentro de um sistema**. Aqui é **uma plataforma para N cursos**, com:
- **Site público** com catálogo e página de venda de cada curso;
- **Área do aluno** com player multimídia, progresso, provas, certificados e gamificação;
- **Estúdio** (área do criador) cujo fluxo principal é: **subir um PDF e a IA gera o curso completo** (ementa, aulas multimídia, quizzes, prova), que o criador revisa e publica (seção 8.4);
- **Organizações (B2B)**: vender um curso para uma empresa com N vagas e painel do gestor (o mesmo papel que o RH tinha no curso da RCA).

O próprio curso "IA com sabedoria" deve poder virar um produto da MayaAcademy, vendido para outros escritórios (versão genérica, sem nada da RCA).

---

## 2. Restrições invioláveis

| # | Restrição |
|---|---|
| **R1** | **Nada roda local.** O código é editado no VS Code com o Claude Code conectado ao servidor via **Remote-SSH** na VM **prod2 (GCP), usuário `mayacorp22`**. Não rodar `runserver`, `pip install`, migrations nem testes na máquina Windows. Todo comando é executado no servidor. |
| **R2** | **Ambiente único: produção.** Não existe testing. Por isso: `DEBUG=False` sempre; **backup do banco (`pg_dump`) antes de toda migration**; nenhum comando destrutivo (`DROP`, `flush`, `rm -rf`, `migrate zero`, reset de banco) sem a minha confirmação explícita. |
| **R3** | **Não tocar nas outras aplicações da prod2.** Projeto, banco, usuário de banco, virtualenv, serviço systemd e server block do Nginx **próprios** da MayaAcademy. Antes de qualquer `reload` do Nginx, rodar `nginx -t`. Nunca editar configs de outros sites. |
| **R4** | **Sem CDN externo em runtime.** GSAP, Lottie e fontes servidos como estáticos do projeto. |
| **R5** | **Segredos só em `.env`** (fora do Git): `SECRET_KEY`, credenciais do banco, chave do Google Cloud TTS, SMTP, gateway de pagamento. Nunca logar nem commitar. |
| **R6** | **Nenhum dado real de cliente** em conteúdo de exemplo, fixtures ou seeds. |

---

## 3. Stack e infraestrutura

- **Backend:** Python 3.12 + **Django 5.x** (padrão PilatesFinal/RCA: apps por domínio, templates server-side, HTMX onde ajudar).
- **Banco:** **PostgreSQL** já existente na prod2 → criar banco `mayaacademy` e usuário `mayaacademy` dedicados.
- **Frontend:** templates Django + **Tailwind** (build no servidor) + **HTMX** + JS vanilla para o player; **GSAP** e **Lottie** para animação.
- **Filas:** **Celery + Redis** para geração de áudio (TTS), PDFs de certificado e e-mails. Verificar se Redis já existe na prod2; se existir, usar **um DB index exclusivo**. `<!-- DEFINIR se já houver Celery rodando para outro app -->`
- **Servidor:** Gunicorn (socket próprio) + **systemd** (`mayaacademy.service`, `mayaacademy-celery.service`) + **Nginx** (server block próprio) + **Certbot** (HTTPS).
- **Domínio:** `<!-- DEFINIR: ex. academy.mayacorp.com.br -->`
- **Mídia:** `MEDIA_ROOT` próprio no servidor (áudios MP3, Lottie JSON, imagens, PDFs). Camada de storage isolada para trocar por GCS depois sem refatorar.
- **Git:** repositório próprio; commits pequenos por etapa.

Estrutura sugerida:

```
/home/mayacorp22/apps/mayaacademy/
├── config/            # settings (base/prod), urls, celery, wsgi
├── core/              # usuários, perfis, organizações, permissões
├── catalogo/          # site público, páginas de curso, checkout
├── cursos/            # Curso, Módulo, Aula, BlocoAula, Personagem
├── estudio/           # área do criador, editor, importador de roteiro
├── aprendizado/       # matrícula, progresso, player, quizzes
├── avaliacoes/        # banco de questões, prova final, tentativas
├── certificados/      # emissão PDF, validação pública
├── gamificacao/       # XP, medalhas, ranking
├── pagamentos/        # interface de gateway (ver seção 9)
├── services/          # tts.py, llm.py, storage.py, pdf.py, ocr.py, email.py
├── static/ templates/
└── .env
```

---

## 4. Perfis de acesso

| Perfil | O que faz |
|---|---|
| **Visitante** | Navega no catálogo, vê página do curso e aula de amostra, se cadastra. |
| **Aluno** | Faz os cursos em que está matriculado, provas, baixa certificado, vê XP/medalhas. |
| **Gestor de organização** | Vê os alunos da sua organização: convites, progresso, notas, certificados; exporta CSV. Não edita cursos. |
| **Criador** (Jeff) | Acesso total ao Estúdio: cria/edita cursos, importa roteiros, gera áudios, publica, vê relatórios de todos. |
| **Superadmin** | Django admin + tudo acima. |

Login por e-mail + senha, com recuperação por e-mail. `<!-- DEFINIR: login com Google na v1? -->`

---

## 5. Modelagem de dados

- **Organizacao**: nome, CNPJ (opcional), logo, contato, ativa.
- **Usuario** (custom user, e-mail como login): nome, e-mail, organização (FK opcional), papel.
- **Curso**: título, slug, subtítulo, descrição longa, capa, trailer (áudio/animação opcional), carga horária, nível, categoria, status (`rascunho` / `publicado` / `arquivado`), modo de acesso (`gratuito` / `pago` / `convite`), preço, nota mínima da prova, nº de tentativas, nº de questões sorteadas, **versão**, aula de amostra (FK opcional), cores/tema do curso.
- **Personagem** (por curso): nome (ex.: "Clô"), papel (`narrador` / `mascote`), voz TTS (nome da voz, velocidade, tom), avatar (SVG/Lottie), estados disponíveis (neutro, falando, pensando, comemorando, alerta).
- **Modulo**: curso (FK), título, ordem.
- **Aula**: módulo (FK), título, duração estimada, ordem, XP, material complementar (arquivo opcional). Conteúdo vem dos blocos.
- **BlocoAula**: aula (FK), ordem, tipo (seção 6), **roteiro de narração** (texto com marcações de fala por personagem), texto de tela, config (JSON validado por tipo), áudio gerado (arquivo), duração, timestamps por frase, **hash do roteiro**.
- **Questao**: curso (FK), módulo (FK opcional), enunciado, alternativas, correta, explicação, dificuldade, uso (`fixacao` / `prova` / `ambos`), ativa.
- **Matricula**: aluno, curso, origem (`gratuita` / `compra` / `convite_org` / `manual`), organização (FK opcional), data, status, versão do curso na matrícula, concluída em.
- **ProgressoAula**: matrícula, aula, blocos concluídos, concluída em, tempo gasto.
- **TentativaProva**: matrícula, nº da tentativa, **snapshot das questões sorteadas e respostas**, nota, aprovado, início/fim, IP.
- **Certificado**: matrícula, código único de validação, emitido em, PDF, carga horária, nota.
- **XPEvento / Medalha / MedalhaAluno**: eventos de XP com origem; medalhas configuráveis por curso ou globais.
- **LicencaOrganizacao**: organização, curso, nº de vagas, vagas usadas, validade.
- **Convite**: licença (FK), e-mail, token, status, enviado/aceito em.
- **Pedido** (pagamentos): aluno, curso, valor, status, id externo do gateway, payload do webhook.
- **AuditLog**: quem, o quê, quando, IP (publicar curso, liberar tentativa extra, emitir certificado manual, alterar licença).

---

## 6. Motor de blocos (herdado do curso da RCA)

Cada aula é uma sequência de blocos. **Regra: mínimo 4 blocos por aula, pelo menos 2 interativos, nenhuma aula só com texto.**

| Tipo | Descrição |
|---|---|
| `cena_narrada` | Animação GSAP/Lottie sincronizada frase a frase com a narração; personagem com boca sincronizada ao áudio. |
| `dialogo` | Formato podcast: narrador + mascote conversando, com legenda. |
| `chat_simulado` | Conversa encenada com efeito de digitação (ex.: usuário × IA). |
| `antes_depois` | Slider comparando duas versões (ex.: prompt ruim × prompt bom). |
| `arrastar_soltar` | Classificar itens em categorias, com feedback por item. |
| `montador` | Montar algo peça por peça (ex.: prompt) com medidor de qualidade e celebração no fim. |
| `caca_erro` | Texto com erros escondidos; o aluno clica para encontrar. |
| `cenario_ramificado` | Situação com escolhas e consequências diferentes. |
| `flashcards` | Cartões de frente/verso para revisão. |
| `quiz_fixacao` | 2–4 questões com explicação imediata. |
| `missao` | Caso prático completo combinando vários passos. |
| `texto_apoio` | Texto curto de apoio — **nunca** pode ser o único tipo da aula. |

- Cada tipo tem seu **schema de config** validado no backend (ao salvar e ao importar) e um **componente JS** próprio no player.
- O player é um "motor" genérico: lê os blocos da aula e renderiza cada um pelo tipo. Novos tipos entram sem mexer nos existentes.
- Botão "Concluir aula" só habilita após passar por todos os blocos interativos e o quiz de fixação.

---

## 7. Multimídia

### 7.1 Áudio (narração)
- **Google Cloud Text-to-Speech**, vozes neurais **pt-BR**, com SSML (pausas, ênfase e `<mark>` para timestamps por frase). Isolado em `services/tts.py` com interface trocável de provedor. `<!-- REVISAR: vozes pt-BR disponíveis e custo atual -->`
- Cada personagem tem voz fixa configurada no curso.
- Geração assíncrona (Celery), por bloco, aula ou curso inteiro. Botão no Estúdio e comando `gerar_audios_curso <slug>`.
- **Só regera quando o hash do roteiro mudar** (controle de custo). Mostrar no Estúdio uma estimativa de caracteres antes de gerar.
- **Acessibilidade obrigatória:** legenda sincronizada e transcrição completa em todo áudio.

### 7.2 Animação e visual
- GSAP para timelines sincronizadas ao áudio; Lottie para mascotes e ilustrações.
- Mascote padrão da plataforma: SVG original e geométrico, nas cores da MayaCorp `<!-- DEFINIR nome e paleta -->`. Cada curso pode trocar de personagem.
- Micro-animações de acerto/erro, transições suaves entre blocos, dark mode.
- Respeitar `prefers-reduced-motion` com fallback estático completo.
- Responsivo de verdade: o player tem que funcionar bem no celular (é onde muita gente vai fazer o curso).

### 7.3 Gamificação
- XP por aula concluída, quiz acertado de primeira e interação completada.
- Medalhas configuráveis por curso + globais ("Maratonista" = curso em até 7 dias, "Nota 100", "Primeiro certificado").
- Ranking opcional por curso/organização (gestor liga/desliga; aluno pode ficar anônimo).
- Tela de conclusão com mascote comemorando, confete e áudio de parabéns.

---

## 8. Estúdio (área do criador)

O ponto mais importante da plataforma: **criar curso novo tem que ser rápido.**

### 8.1 Editor
- CRUD de curso → módulos → aulas → blocos, com reordenação por arrastar.
- Formulário de cada bloco gerado a partir do schema do tipo, com **pré-visualização ao vivo** no player.
- Botões: gerar áudio (bloco/aula/curso), pré-visualizar como aluno, publicar, arquivar.
- Publicar um curso exige: todas as aulas com ≥ 4 blocos e ≥ 2 interativos, todos os áudios gerados, banco de questões com pelo menos (nº sorteado × 1,5) questões de prova. Mostrar checklist do que falta.

### 8.2 Importador de roteiro
- Upload de um arquivo **YAML ou JSON** com o curso inteiro (ou um módulo/aula): metadados, personagens, módulos, aulas, blocos com roteiro e config, questões.
- Fluxo: upload → validação completa contra os schemas → **relatório de erros por linha/bloco** → pré-visualização → confirmar importação (cria como rascunho).
- Documentar o formato em `docs/formato-roteiro.md` **com um exemplo completo de uma aula**, para que eu possa gerar roteiros de curso com o Claude e importar direto.
- Exportar curso no mesmo formato (backup e reaproveitamento).

### 8.4 Gerador de curso a partir de PDF (funcionalidade principal)

O criador sobe um PDF (apostila, manual, e-book próprio, material de treinamento) e a plataforma gera um curso completo como **rascunho**, no mesmo formato do importador (8.2). Nada é publicado sem revisão humana.

**Tela "Novo curso a partir de PDF":**
- Upload de 1 ou mais PDFs (limite `<!-- DEFINIR, sugestão 300 páginas -->`).
- Parâmetros: público-alvo, nível (iniciante/intermediário/avançado), tom (leve/formal/técnico), duração-alvo do curso, nº aproximado de módulos, personagens (narrador + mascote), idioma (padrão pt-BR).
- Checkbox obrigatório: "Declaro que tenho direito de uso deste material para criar cursos" (registrado no AuditLog).

**Pipeline (Celery, com barra de progresso na tela por etapa):**

1. **Extração** — PDF → Markdown por página (PyMuPDF/pdfplumber). Páginas sem texto (escaneadas) → OCR (Tesseract pt-BR) e marcar como "OCR" no relatório. Guardar o texto por página com o número da página.
2. **Mapa do conteúdo** — IA lê o material e produz: temas principais, conceitos-chave, termos do glossário, exemplos e casos presentes no texto, e onde cada coisa aparece (páginas).
3. **Ementa proposta** — IA propõe módulos e aulas (título, objetivo de aprendizagem, páginas de origem, duração estimada).
   → **GATE do criador:** tela para editar, reordenar, juntar, dividir ou excluir módulos/aulas **antes** de gerar o conteúdo. Botão "Gerar aulas".
4. **Geração das aulas** — uma chamada por aula, recebendo só o trecho de origem + ementa + parâmetros. Saída: blocos no schema da seção 6 (cena narrada, diálogo, chat simulado, caça ao erro, arrastar e soltar, cenário ramificado etc.), respeitando ≥ 4 blocos e ≥ 2 interativos. A IA escolhe o tipo de bloco que melhor ensina cada conteúdo (ex.: lista de procedimentos → `montador`; certo/errado → `arrastar_soltar`; erros comuns → `caca_erro`; situações de decisão → `cenario_ramificado`).
5. **Banco de questões** — questões de fixação por aula + questões de prova (no mínimo nº sorteado × 1,5), com explicação e página de origem.
6. **Validação** — cada saída validada contra o schema; se inválida, reenviar à IA com o erro (até 2 tentativas); se ainda falhar, marcar a aula como "precisa de revisão" sem travar o resto.
7. **Rascunho pronto** — curso criado em rascunho no Estúdio, com relatório: aulas geradas, aulas com problema, páginas não aproveitadas, custo estimado de IA e de TTS.

**Regras de fidelidade ao PDF (obrigatórias no prompt da IA):**
- Conteúdo técnico (conceitos, números, regras, procedimentos) **só do PDF**. A IA pode criar analogias, histórias, personagens e exemplos didáticos, mas não fatos novos.
- Todo bloco e toda questão guardam as **páginas de origem**. No Estúdio, ao lado do bloco, botão "ver trecho do PDF".
- Se a IA precisar complementar algo que o PDF não cobre, marcar o bloco com o selo "⚠ conteúdo além do PDF" para o criador revisar.
- Não copiar trechos longos do PDF para a tela: reescrever de forma didática (narração conversada, não leitura do livro).

**IA:**
- Provedor isolado em `services/llm.py` (interface trocável). Padrão: **API da Anthropic (Claude)**; modelo configurável no `.env`. Usar saída estruturada/tool use para devolver o JSON dos blocos. `<!-- REVISAR: modelo e preço atuais na documentação da Anthropic -->`
- Prompts versionados em arquivos (`estudio/prompts/*.md`), não espalhados no código.
- Log de cada chamada: etapa, tokens de entrada/saída, custo estimado, duração. Painel de custo por curso gerado.
- Reprocessar uma aula individual ("gerar de novo esta aula" com instrução extra opcional, ex.: "mais leve", "mais exemplos práticos").

### 8.5 Versionamento
- Alterar curso publicado incrementa a versão. Alunos já matriculados continuam onde estão; certificado registra a versão.

---

## 9. Venda e acesso

- **Gratuito:** aluno se cadastra e se matricula direto.
- **Convite / organização:** criador cria a licença (organização + curso + vagas + validade); gestor envia convites por e-mail; aceite consome vaga.
- **Pago:** checkout por gateway via `pagamentos/` com **interface isolada** (`criar_cobranca`, `processar_webhook`). Matrícula liberada **só pelo webhook confirmado**, nunca pelo redirect. Webhook idempotente. `<!-- DEFINIR gateway: usar o mesmo escolhido para os SaaS MayaCorp -->`
- Na v1, se o gateway não estiver definido, implementar a interface com um provedor "manual" (criador libera a matrícula no painel) e deixar o gateway real para a fase F6.

---

## 10. Telas

**Público:** home com catálogo; página do curso (descrição, ementa, carga horária, trailer, **aula de amostra jogável**, preço/CTA); validação de certificado (`/certificado/<codigo>`).

**Aluno:** "Meus cursos" com progresso; página do curso com módulos/aulas e cadeados; player multimídia; prova final; certificados; perfil com XP e medalhas.

**Gestor:** painel da organização (vagas, convites, progresso por aluno, notas, certificados), filtros e exportação CSV.

**Criador:** Estúdio (seção 8); painel geral (matrículas, conclusão por curso, aulas onde o pessoal mais abandona, nota média, receita); liberar tentativa extra (com AuditLog).

---

## 11. Regras de negócio

| # | Regra | Critério de aceite |
|---|---|---|
| **N1** | Aulas liberadas em ordem: a próxima só abre após concluir a anterior. | Acessar URL de aula bloqueada redireciona com aviso. |
| **N2** | Prova final só libera com 100% das aulas concluídas. | Botão da prova desabilitado com indicação do que falta. |
| **N3** | Prova sorteia N questões do banco do curso; alternativas embaralhadas. | Duas tentativas seguidas trazem conjuntos/ordens diferentes; snapshot salvo na tentativa. |
| **N4** | Aprovação pela nota mínima do curso (padrão 70%); tentativas limitadas (padrão 3). | Após a última reprovação, só o criador libera nova tentativa (registrado no AuditLog). |
| **N5** | Certificado emitido automaticamente na aprovação: nome, curso, carga horária, data, nota, código e **QR code** de validação. | PDF gerado em até 1 min; URL pública valida o código. |
| **N6** | Convite consome vaga só no aceite; vaga não aceita expira junto com a licença. | Licença cheia bloqueia novos convites com mensagem clara. |
| **N7** | Matrícula paga só é criada pelo webhook confirmado. | Webhook duplicado não cria matrícula duplicada. |
| **N8** | Progresso salvo a cada bloco concluído. | Fechar o navegador no meio e voltar retoma no último bloco. |
| **N9** | Curso só publica com o checklist da seção 8.1 completo. | Botão "Publicar" mostra o que falta. |
| **N10** | Áudio só regera quando o hash do roteiro mudar. | Gerar duas vezes sem alteração não chama a API de TTS. |
| **N11** | Curso gerado por PDF nasce sempre como rascunho e só gera aulas após o criador aprovar a ementa. | Não existe caminho PDF → publicado sem passar pelo gate da ementa e pelo N9. |
| **N12** | Todo bloco e questão gerados têm página de origem; conteúdo além do PDF recebe selo de revisão. | Relatório do rascunho lista 100% dos blocos com origem ou selo. |
| **N13** | Falha em uma aula não derruba a geração do curso. | Com 1 aula inválida, as demais são criadas e ela aparece como "precisa de revisão". |

---

## 12. Ordem de implementação (obrigatória)

Ao fim de cada fase: resumo do que foi feito, comandos executados no servidor e o que testar. **Pare nos gates.**

**F0 — Infraestrutura na prod2**
Banco e usuário dedicados, virtualenv, projeto Django com settings de produção, `.env`, Gunicorn + systemd, Nginx (server block novo + `nginx -t`), HTTPS com Certbot, Celery + Redis, backup diário do banco com retenção dos últimos 5.
→ **GATE 1:** me mostrar o domínio respondendo em HTTPS com uma página "em construção" e o `systemctl status` dos serviços.

**F1 — Núcleo**
Usuários, perfis, organizações, permissões, login/cadastro/recuperação de senha, modelagem de cursos, módulos, aulas e blocos, Django admin.

**F2 — Motor de blocos + player + Estúdio básico**
Schemas por tipo, player genérico, TTS, editor no Estúdio, importador de roteiro e `docs/formato-roteiro.md`.
Criar **uma aula-piloto completa** (sugestão: uma versão genérica da aula "Limites e alucinações" do curso de IA, sem nada da RCA) com narração, cena animada, caça ao erro, chat simulado e quiz de fixação.
→ **GATE 2 (duro):** parar e me mostrar a aula-piloto rodando no celular e no desktop. **Não seguir sem a minha aprovação do visual e da experiência.**

**F2.5 — Gerador de curso a partir de PDF**
Extração + OCR, mapa do conteúdo, ementa com gate do criador, geração de aulas e questões, validação, relatório e painel de custo.
→ **GATE 3:** gerar um curso de teste a partir de um PDF que eu vou fornecer e me mostrar ementa, 2 aulas no player e o relatório de custo. Não seguir sem aprovação.

**F3 — Aprendizado e avaliação**
Matrícula, progresso, liberação em ordem, prova final, tentativas, certificados com validação pública, gamificação.

**F4 — Site público e catálogo**
Home, página do curso com aula de amostra, cadastro, matrícula gratuita.

**F5 — Organizações (B2B)**
Licenças, convites, painel do gestor, exportação CSV.

**F6 — Pagamentos**
Gateway definido + webhook + pedidos + painel de receita.

**F7 — Primeiro curso de catálogo**
Converter "Como usar a IA com sabedoria" para uma versão genérica (qualquer escritório/empresa), via importador de roteiro.

---

## 13. Qualidade — Definition of Done

- [ ] Testes automatizados (pytest/Django) para regras N1–N10, rodados **no servidor**.
- [ ] Sem N+1 nas telas de listagem e no player (`select_related`/`prefetch_related`).
- [ ] Player testado em celular (Android/iOS) e desktop; primeira aula carrega bem em 3G.
- [ ] Acessibilidade: legenda e transcrição em todo áudio, navegação por teclado, contraste AA, `prefers-reduced-motion`.
- [ ] `DEBUG=False`, `ALLOWED_HOSTS`, cookies seguros, CSRF, HSTS, rate limit no login.
- [ ] Logs da aplicação e do Celery em arquivo próprio com rotação.
- [ ] Backup antes de cada migration aplicado em produção.
- [ ] README com: como fazer deploy, como reiniciar os serviços, como importar um curso, como gerar áudios.

---

## 14. Fora de escopo (v1)

Não implementar, mesmo que pareça uma boa ideia:
- App mobile nativo;
- SCORM / xAPI / integração com LMS externo;
- Gerar curso a partir de vídeo, áudio, site ou Word (v1 é só PDF);
- Vídeo gravado e streaming de vídeo (a experiência é áudio + animação + interação);
- Aula ao vivo, fórum e comunidade;
- Marketplace com outros criadores (só o Jeff cria cursos na v1);
- Assinatura/mensalidade (v1 é venda por curso e licença B2B);
- Ambiente de testing (decisão do Jeff: direto em produção, com as salvaguardas da R2).
