# Progresso — MayaAcademy

## Situação em 24/11/2026

O código das fases **F0, F1 e F2** está pronto e verificado localmente (num ambiente descartável). Ainda **não foi instalado no servidor**.
Próximo passo: instalar em **produção** e passar pelo **GATE 2**.

### Feito

**F0 — Infraestrutura (scripts prontos, falta executar no servidor)**
- `deploy/instalar.sh hml|prod`, `deploy.sh`, `rollback.sh`, `backup.sh` (diário, mantém os últimos 5, e antes de toda migration), systemd `@hml/@prod`, nginx.
- Redis próprio (`mayaacademy-redis`, 127.0.0.1:6380). O 6379 do servidor é do Evolution.
- Página "em construção" em `/` e health check em `/saude/` (Gate 1).

**F1 — Núcleo**
- Usuário com login por e-mail, cadastro, recuperação de senha e rate limit no login (5 tentativas a cada 15 min, por IP + e-mail).
- Papéis aluno/gestor/criador/superadmin, organizações e AuditLog imutável. Modelos de curso, módulo, aula, bloco, personagem e questão. Django admin.

**F2 — Motor de blocos, player e Estúdio**
- 12 tipos de bloco com schema validado no backend e componente próprio no player.
- Player genérico: narração sincronizada frase a frase, mascote com boca animada, legendas, transcrição, velocidade, tela de início e de conclusão com confete e som, modo escuro, `prefers-reduced-motion`, teclado (K, C, setas) e layout de celular.
- TTS trocável (`google` com marcas SSML por frase, ou `nulo`). Só regera o áudio quando o hash do roteiro ou da voz muda (N10). Geração pelo Celery (bloco, aula ou curso), comando `gerar_audios_curso` e estimativa de caracteres.
- Estúdio no padrão MayaCorp:
  - CRUD de curso, módulo, aula e bloco, com reordenação por arrastar (inclusive aula entre módulos).
  - Formulário gerado a partir do schema, com JSON bruto opcional, prévia ao vivo em largura de celular e frases numeradas do roteiro.
  - Checklist de publicação (N9) e versão incrementada ao republicar.
- Importador YAML/JSON com erros por linha, prévia e confirmação, além de exportação. Documentação em `docs/formato-roteiro.md`.
- **Aula-piloto** "Limites e alucinações" (`conteudo/ia-com-sabedoria-piloto.yaml`), versão genérica sem nada da RCA. Tem 7 blocos: cena narrada, diálogo, chat simulado, caça ao erro, antes × depois, cenário ramificado e quiz. Acompanham 8 questões de prova.
- **Download do curso** (pedido do Jefferson em 24/11): pacote HTML5 + SCORM 1.2 que abre em `file://`, em sites e em LMS.
- 49 testes automatizados, todos passando. Percurso completo da aula no navegador (celular e desktop, claro e escuro), sem erros de console.

**F2.5 — Gerador de curso a partir de PDF**
- Tela "Curso a partir de PDF": um ou mais PDFs (limite `PDF_LIMITE_PAGINAS`, padrão 300), público, nível, tom, duração,
  nº de módulos, nomes do narrador e do mascote, e a declaração de direito de uso (vai para o AuditLog).
- Pipeline no Celery com barra de progresso: extração por página (OCR com Tesseract nas páginas sem texto, se instalado),
  mapa do conteúdo por trechos, ementa proposta → **gate do criador** (editar, reordenar, dividir, juntar, excluir).
- Só depois de "Aprovar e gerar aulas" o curso é criado (rascunho) e cada aula é gerada numa chamada própria, só com as
  páginas de origem. Saída validada pelo mesmo registro de blocos do importador; até 2 correções com os erros; se ainda
  falhar, a aula fica "precisa de revisão" sem travar as outras (N11, N12, N13).
- Questões de fixação e de prova por aula, sempre com página de origem. Bloco sem origem recebe o selo "⚠ além do PDF".
- Relatório (aulas, problemas, páginas não aproveitadas, OCR) e painel de custo (cada chamada com tokens, custo e duração,
  mais a estimativa do TTS). "Ver trecho do PDF" no bloco e "Gerar de novo" a aula com instrução extra.
- IA: **OpenAI** (pedido do Jefferson em 24/11), isolada em `services/llm.py`.

**F3, F4 (parte), F5 e F6 — itens que estavam "em breve" (pedido do Jefferson em 24/11)**
- Matrícula, progresso salvo a cada bloco e retomada (N8), aulas liberadas em ordem (N1), página do curso do aluno.
- Prova final: só com 100% das aulas (N2), sorteio com alternativas embaralhadas e snapshot (N3), nota mínima e
  tentativas, com tentativa extra liberada pelo criador no Estúdio › Alunos (N4, AuditLog).
- Certificado automático na aprovação (N5): PDF A4 com QR code, código `MA-XXXXX-XXXXX`, validação pública.
- XP (aula, quiz de primeira, interações, curso) e medalhas (Primeiro certificado, Nota 100, Maratonista, Mil de XP);
  ranking por organização (o gestor liga/desliga; o aluno pode ficar anônimo).
- Catálogo público, página do curso com aula de amostra, matrícula gratuita.
- Organizações: licenças por curso (vagas e validade, alterações no AuditLog), convites por e-mail com link,
  vaga consumida só no aceite (N6), painel do gestor com progresso, notas, certificados, filtros e CSV.
- Pagamentos: interface de gateway com provedor "manual" (o criador confirma no painel); a matrícula só nasce da
  confirmação, pelo mesmo caminho do webhook, que é idempotente (N7).
- Estúdio: alunos do curso (matrícula manual, tentativa extra, certificado manual) e relatórios gerais.
- Publicação: com `TTS_PROVIDER=nulo` o item de áudio do checklist passa (legendas cronometradas); com voz ligada,
  continua exigindo todos os áudios (N9).

### Falta

- Remover a hml do servidor; instalar prod, DNS de `academy.mayacorp.com.br` e certbot → **GATE 1**.
- **GATE 2 (duro):** o Jefferson aprovar a aula-piloto no celular e no desktop.
- F2.5 (gerador por PDF): o PDF de teste é "Formação completa em Pilates" (185 páginas, 11 sem texto que vão precisar de OCR). Ele está na raiz do projeto, fora do Git.
- F3 a F7 conforme a especificação.

### Decisões tomadas (com o motivo)

- **24/11: IA da OpenAI** no gerador por PDF (a especificação sugeria Anthropic). Modelo e preço ficam no `.env`
  (`OPENAI_MODEL`, `LLM_PRECO_ENTRADA_1M`, `LLM_PRECO_SAIDA_1M`), para trocar sem mexer no código.
- **24/11: sem homologação.** Ambiente único = produção (`academy.mayacorp.com.br`, branch `main`), por decisão do Jefferson.
  A hml chegou a ser instalada (`/home/deploy/mayaacademy/hml`) e deve ser removida do servidor. O Gate 2 acontece em produção.

- **Hospedagem no servidor do Flicsales.** A especificação falava em "prod2 (GCP)", mas o Jefferson não usa Google.
- **Padrão da fábrica MayaCorp** (pedido em 24/11), exceto homologação: tags `vN`, paleta e shell do MayaJus e auditoria imutável.
- **Stack mantida em Django**, porque a especificação pede o padrão PilatesFinal/RCA. A fábrica usa FastAPI + Next no MayaJus e no MayaFit. *Ver dúvida 1.*
- **SCORM entrou na v1** (a especificação deixava fora), por causa do pedido de baixar o curso para publicar em várias plataformas.
- Player em ES modules empacotados num script único, para funcionar em `file://` e dentro de LMS.
- Mascote padrão **"Maya"** (hexágono Indigo) e narrador **coruja** Teal. Nome e paleta são provisórios. *Ver dúvida 3.*

### Dúvidas para o Jefferson

1. **Stack:** seguimos em Django (como a especificação pede) ou o "padrão da fábrica" inclui migrar para FastAPI + Next como no MayaJus?
4. **Mascote:** o nome "Maya" e as cores (Indigo e Teal) estão aprovados?
5. **Google Cloud TTS:** precisa de uma chave de API (conta Google Cloud só para o TTS). Usamos ela ou prefere outro provedor? Até lá o provedor é `nulo` (legendas sem voz).
6. **Plataformas de destino do download:** o SCORM atende Moodle, LearnWorlds, TalentLMS e similares. Hotmart e Udemy só aceitam **vídeo**: quer que a gente renderize as aulas em MP4 também?
7. **Login com Google na v1?** Hoje é só e-mail e senha.
8. **Limite de páginas do PDF:** mantemos 300?
9. **Gateway de pagamento:** qual? Até a F6 fica o provedor "manual".

### Para revisar (marcados como REVISAR na especificação)

- Vozes do Google TTS usadas: `pt-BR-Neural2-B` (narrador) e `pt-BR-Neural2-C` (Maya). Conferir a disponibilidade e o preço atuais antes de gerar em massa.
- O arquivo de mídia (`/media/`) é servido sem login. Na F3, os áudios de aulas pagas passam a usar link assinado.
