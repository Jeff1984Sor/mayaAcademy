# Progresso — MayaAcademy

## Situação em 24/11/2026

O código das fases **F0, F1 e F2** está pronto e verificado localmente (num ambiente descartável). Ainda **não foi instalado no servidor**.
Próximo passo: instalar em **homologação** e passar pelo **GATE 2**.

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

### Falta

- Executar o F0 no servidor (instalar hml, DNS, certbot) → **GATE 1**.
- **GATE 2 (duro):** o Jefferson aprovar a aula-piloto no celular e no desktop.
- F2.5 (gerador por PDF): o PDF de teste é "Formação completa em Pilates" (185 páginas, 11 sem texto que vão precisar de OCR). Ele está na raiz do projeto, fora do Git.
- F3 a F7 conforme a especificação.

### Decisões tomadas (com o motivo)

- **Hospedagem no servidor do Flicsales.** A especificação falava em "prod2 (GCP)", mas o Jefferson não usa Google.
- **Padrão da fábrica MayaCorp** (pedido em 24/11): hml → prod, tags `vN`, paleta e shell do MayaJus e auditoria imutável.
- **Stack mantida em Django**, porque a especificação pede o padrão PilatesFinal/RCA. A fábrica usa FastAPI + Next no MayaJus e no MayaFit. *Ver dúvida 1.*
- **SCORM entrou na v1** (a especificação deixava fora), por causa do pedido de baixar o curso para publicar em várias plataformas.
- Player em ES modules empacotados num script único, para funcionar em `file://` e dentro de LMS.
- Mascote padrão **"Maya"** (hexágono Indigo) e narrador **coruja** Teal. Nome e paleta são provisórios. *Ver dúvida 3.*

### Dúvidas para o Jefferson

1. **Stack:** seguimos em Django (como a especificação pede) ou o "padrão da fábrica" inclui migrar para FastAPI + Next como no MayaJus?
2. **Ambientes:** a especificação dizia "só produção", mas o padrão da fábrica é hml antes. Os scripts suportam os dois. Posso instalar hml primeiro?
3. **Domínio:** `academy.mayacorp.com.br` e `hml-academy.mayacorp.com.br` estão bons? Ainda não têm DNS.
4. **Mascote:** o nome "Maya" e as cores (Indigo e Teal) estão aprovados?
5. **Google Cloud TTS:** precisa de uma chave de API (conta Google Cloud só para o TTS). Usamos ela ou prefere outro provedor? Até lá o provedor é `nulo` (legendas sem voz).
6. **Plataformas de destino do download:** o SCORM atende Moodle, LearnWorlds, TalentLMS e similares. Hotmart e Udemy só aceitam **vídeo**: quer que a gente renderize as aulas em MP4 também?
7. **Login com Google na v1?** Hoje é só e-mail e senha.
8. **Limite de páginas do PDF:** mantemos 300?
9. **Gateway de pagamento:** qual? Até a F6 fica o provedor "manual".

### Para revisar (marcados como REVISAR na especificação)

- Vozes do Google TTS usadas: `pt-BR-Neural2-B` (narrador) e `pt-BR-Neural2-C` (Maya). Conferir a disponibilidade e o preço atuais antes de gerar em massa.
- O arquivo de mídia (`/media/`) é servido sem login. Na F3, os áudios de aulas pagas passam a usar link assinado.
