# MayaAcademy

Plataforma de cursos online da MayaCorp: aulas com narração, animação e interação, Estúdio para criar cursos
(inclusive a partir de roteiro YAML e, em breve, de PDF) e download do curso como pacote HTML5/SCORM.

Visão técnica e regras do projeto: [`CLAUDE.md`](CLAUDE.md). Andamento: [`docs/PROGRESSO.md`](docs/PROGRESSO.md).
Formato dos roteiros: [`docs/formato-roteiro.md`](docs/formato-roteiro.md).

## Deploy

O servidor é compartilhado com outros sistemas MayaCorp. Os scripts só acrescentam coisas e nunca mexem no que já existe.

**Primeira vez (por ambiente)**, no servidor, como `deploy`:

```bash
git clone https://github.com/Jeff1984Sor/mayaAcademy.git /tmp/mayaacademy-instalador
sudo bash /tmp/mayaacademy-instalador/deploy/instalar.sh hml     # depois, quando aprovado: prod
```

O instalador confere porta, pasta e banco (aborta se algo já existir). Depois cria o banco e o usuário PostgreSQL próprios, o Redis próprio,
o `.env`, a `.venv`, o build do CSS e do player, as migrations, os serviços systemd, o site nginx (com `nginx -t`), o cron de backup
e o primeiro superusuário. Em seguida:

1. DNS: registro A de `hml-academy.mayacorp.com.br` (ou `academy.`) para o IP do servidor.
2. HTTPS: `sudo certbot --nginx -d hml-academy.mayacorp.com.br`
3. Preencha no `.env` o SMTP, a chave do Google TTS (`TTS_PROVIDER=google`) e a da Anthropic. Depois reinicie os serviços.

**Atualizações:**

```bash
cd /home/deploy/mayaacademy/hml && ./deploy/deploy.sh hml      # branch develop
cd /home/deploy/mayaacademy/prod && ./deploy/deploy.sh prod    # branch main, cria tag vN
```

O `deploy.sh` faz pull, instala as dependências, gera o CSS e o player e roda os **testes** (se falharem, nada é reiniciado). Faz **backup do banco
antes de qualquer migration**, migra, roda o collectstatic, reinicia e confere o `/saude/`. Para voltar: `./deploy/rollback.sh prod v7`.

## Reiniciar os serviços

```bash
sudo systemctl restart mayaacademy-web@prod mayaacademy-worker@prod
systemctl status mayaacademy-web@prod mayaacademy-worker@prod
tail -f /home/deploy/mayaacademy/prod/logs/app.log          # também: celery.log, gunicorn-erro.log
```

## Importar um curso

- Pela tela: **Estúdio › Importar roteiro** (valida, mostra os erros por linha e a prévia, e cria como rascunho).
- Pelo terminal: `.venv/bin/python manage.py importar_roteiro conteudo/ia-com-sabedoria-piloto.yaml`

## Gerar áudios

- Pela tela: botões "Gerar áudio" no bloco, na aula ou no curso (mostram antes a estimativa de caracteres).
- Pelo terminal: `.venv/bin/python manage.py gerar_audios_curso ia-com-sabedoria --estimar` e depois sem `--estimar`.
- Só blocos cujo roteiro ou voz mudou são enviados ao TTS. Use `--forcar` para regerar tudo.
- Com `TTS_PROVIDER=nulo` não há áudio: o player usa legendas cronometradas (bom para homologação sem custo).

## Baixar um curso para outras plataformas

**Estúdio › curso › Baixar pacote (SCORM)** gera um `.zip` que:

- abre no computador (descompacte e abra `index.html`);
- sobe em LMS compatível com SCORM 1.2 (Moodle, LearnWorlds, TalentLMS...), com conclusão e nota reportadas ao LMS;
- pode ser publicado em qualquer hospedagem estática.

## Desenvolvimento

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m pytest -q
```
