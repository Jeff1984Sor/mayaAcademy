#!/usr/bin/env bash
#
# Primeira instalação de um ambiente da MayaAcademy no servidor compartilhado (o mesmo do Flicsales).
# Regra da casa: não atualizar, reiniciar nem reconfigurar nada que já exista. Só acrescentar.
#
#   sudo bash deploy/instalar.sh hml     # hml-academy.mayacorp.com.br  (web 10091)  branch develop
#   sudo bash deploy/instalar.sh prod    # academy.mayacorp.com.br      (web 10081)  branch main
#
# Cria: pasta /home/deploy/mayaacademy/<amb>, banco e usuário PostgreSQL próprios, .venv, .env,
# serviços mayaacademy-{web,worker}@<amb>, site nginx mayaacademy-<amb>, Redis próprio (container
# mayaacademy-redis em 127.0.0.1:6380; o Redis da 6379 é do Evolution e NÃO é usado).
#
set -euo pipefail

AMB="${1:?informe o ambiente: hml ou prod}"
case "$AMB" in
  prod) BRANCH=main;    WEB_PORTA=10081; DOMINIO="${DOMINIO:-academy.mayacorp.com.br}";     REDIS_DB=0 ;;
  hml)  BRANCH=develop; WEB_PORTA=10091; DOMINIO="${DOMINIO:-hml-academy.mayacorp.com.br}"; REDIS_DB=2 ;;
  *) echo "Ambiente inválido: $AMB (use hml ou prod)"; exit 1 ;;
esac
REPO="${REPO:-https://github.com/Jeff1984Sor/mayaAcademy.git}"
USUARIO=deploy
BASE=/home/$USUARIO/mayaacademy
DIR="$BASE/$AMB"
BANCO="mayaacademy_$AMB"
ROLE="mayaacademy_$AMB"
NGINX_SITE="/etc/nginx/sites-available/mayaacademy-$AMB"
REDIS_PORTA=6380

[ "$(id -u)" = "0" ] || { echo "Rode com sudo: sudo bash deploy/instalar.sh $AMB"; exit 1; }
id "$USUARIO" >/dev/null 2>&1 || { echo "Usuário $USUARIO não existe."; exit 1; }
como() { sudo -u "$USUARIO" -H bash -lc "$1"; }

echo "=== MayaAcademy ($AMB) → $DIR ==="

echo "--- 1/10 Conferindo o servidor (nada é alterado nesta etapa)"
if ss -ltn "( sport = :$WEB_PORTA )" | grep -q LISTEN; then echo "    Porta $WEB_PORTA já está em uso. Abortado sem alterar nada."; exit 1; fi
[ -e "$DIR" ] && { echo "    $DIR já existe. Para atualizar use: ./deploy/deploy.sh $AMB"; exit 1; }
[ -e "$NGINX_SITE" ] && { echo "    $NGINX_SITE já existe. Abortado."; exit 1; }
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$BANCO'" | grep -q 1; then
  echo "    O banco $BANCO já existe. Abortado (não apago bancos)."; exit 1
fi
LIVRE_GB="$(df -BG --output=avail /home | tail -1 | tr -dc '0-9')"
echo "    Espaço livre em /home: ${LIVRE_GB} GB (áudios MP3 ocupam espaço; acompanhe)"
[ "${LIVRE_GB:-0}" -ge 3 ] || { echo "    Menos de 3 GB livres. Abortado."; exit 1; }
echo "    Porta $WEB_PORTA livre, pasta e banco novos. OK."

echo "--- 2/10 Pacotes: instala só o que falta, sem atualizar o que existe"
FALTAM=""
for pkg in git curl openssl nginx postgresql-client certbot python3-certbot-nginx python3-venv tesseract-ocr tesseract-ocr-por; do
  dpkg -s "$pkg" >/dev/null 2>&1 || FALTAM="$FALTAM $pkg"
done
if [ -n "$FALTAM" ]; then
  echo "    instalando:$FALTAM"
  apt-get install -y -qq --no-upgrade $FALTAM >/dev/null
fi
NODE_VER="$(como 'node -v' 2>/dev/null || echo v0)"
[ "$(echo "$NODE_VER" | cut -d. -f1 | tr -d v)" -ge 18 ] || { echo "    Node.js >= 18 necessário (build do CSS). Encontrado: $NODE_VER"; exit 1; }

echo "--- 3/10 Redis próprio (container mayaacademy-redis em 127.0.0.1:$REDIS_PORTA)"
if docker ps -a --format '{{.Names}}' | grep -qx mayaacademy-redis; then
  echo "    já existe (compartilhado entre hml e prod, cada um com seus índices)"
else
  docker run -d --name mayaacademy-redis --restart unless-stopped -p 127.0.0.1:$REDIS_PORTA:6379 \
    -v mayaacademy-redis:/data redis:7-alpine redis-server --appendonly yes >/dev/null
  echo "    criado"
fi

echo "--- 4/10 Código ($BRANCH)"
como "mkdir -p '$BASE' && git clone -q -b '$BRANCH' '$REPO' '$DIR'"

echo "--- 5/10 Banco de dados $BANCO (novo; os outros bancos não são tocados)"
SENHA_BANCO="$(openssl rand -hex 24)"
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$ROLE'" | grep -q 1; then
  sudo -u postgres psql -q -c "ALTER ROLE $ROLE WITH LOGIN PASSWORD '$SENHA_BANCO'"
else
  sudo -u postgres psql -q -c "CREATE ROLE $ROLE WITH LOGIN PASSWORD '$SENHA_BANCO'"
fi
sudo -u postgres psql -q -c "CREATE DATABASE $BANCO OWNER $ROLE ENCODING 'UTF8'"

echo "--- 6/10 .env (só o que é de servidor; segredos de integração são preenchidos depois, à mão)"
como "cat > '$DIR/.env'" <<ENV
AMBIENTE=$AMB
WEB_PORTA=$WEB_PORTA
SECRET_KEY=$(openssl rand -hex 48)
DEBUG=False
ALLOWED_HOSTS=$DOMINIO
CSRF_TRUSTED_ORIGINS=https://$DOMINIO
SITE_URL=https://$DOMINIO
DB_NAME=$BANCO
DB_USER=$ROLE
DB_PASSWORD=$SENHA_BANCO
DB_HOST=127.0.0.1
DB_PORT=5432
CELERY_BROKER_URL=redis://127.0.0.1:$REDIS_PORTA/$REDIS_DB
CELERY_RESULT_BACKEND=redis://127.0.0.1:$REDIS_PORTA/$REDIS_DB
CACHE_URL=redis://127.0.0.1:$REDIS_PORTA/$((REDIS_DB + 1))
MEDIA_ROOT=$DIR/media
STATIC_ROOT=$DIR/staticfiles
LOG_DIR=$DIR/logs
TTS_PROVIDER=nulo
GOOGLE_TTS_API_KEY=
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=MayaAcademy <nao-responda@mayacorp.com.br>
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=
LLM_PRECO_ENTRADA_1M=0
LLM_PRECO_SAIDA_1M=0
PDF_LIMITE_PAGINAS=300
ENV
como "chmod 600 '$DIR/.env' && mkdir -p '$DIR/media' '$DIR/logs' '$DIR/staticfiles'"

echo "--- 7/10 Python, CSS, player, migrations e estáticos"
como "cd '$DIR' && python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt"
como "cd '$DIR' && npm ci --silent && npm run build:css --silent"
como "cd '$DIR' && .venv/bin/python manage.py montar_player && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput -v0"

echo "--- 8/10 Serviços (systemd) — só acrescenta, não mexe nos existentes"
for svc in web worker; do
  sed "s|__BASE__|$BASE|g; s|__USUARIO__|$USUARIO|g" "$DIR/deploy/systemd/mayaacademy-$svc@.service" \
    > "/etc/systemd/system/mayaacademy-$svc@.service"
done
systemctl daemon-reload
systemctl enable --now "mayaacademy-web@$AMB" "mayaacademy-worker@$AMB"

echo "--- 9/10 nginx (site próprio; nginx -t antes do reload)"
sed "s|__DOMINIO__|$DOMINIO|g; s|__WEB__|$WEB_PORTA|g; s|__DIR__|$DIR|g" \
  "$DIR/deploy/nginx/mayaacademy.conf.template" > "$NGINX_SITE"
ln -s "$NGINX_SITE" "/etc/nginx/sites-enabled/mayaacademy-$AMB"
if nginx -t 2>/tmp/mayaacademy-nginx.txt; then
  systemctl reload nginx   # reload: os sites existentes continuam no ar
else
  rm -f "/etc/nginx/sites-enabled/mayaacademy-$AMB"
  echo "    O nginx recusou a configuração nova; ela foi DESFEITA (os outros sites seguem intactos):"
  cat /tmp/mayaacademy-nginx.txt
  exit 1
fi
# backup diário 02:30, mantém os últimos 5 (especificação F0)
echo "30 2 * * * $USUARIO $DIR/deploy/backup.sh $AMB >> $BASE/backup-$AMB.log 2>&1" > "/etc/cron.d/mayaacademy-backup-$AMB"

echo "--- 10/10 Primeiro criador (superusuário)"
if { : </dev/tty; } 2>/dev/null; then
  como "cd '$DIR' && .venv/bin/python manage.py createsuperuser" </dev/tty
else
  echo "    Sem terminal: depois rode  cd $DIR && .venv/bin/python manage.py createsuperuser"
fi

sleep 3
CODIGO="$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $DOMINIO" -H 'X-Forwarded-Proto: https' "http://127.0.0.1:$WEB_PORTA/saude/" || echo 000)"
echo
echo "=== Pronto: $AMB instalado (app local: HTTP $CODIGO) ==="
echo "    1) DNS: registro A '$DOMINIO' → IP deste servidor"
echo "    2) HTTPS: sudo certbot --nginx -d $DOMINIO"
echo "    3) Preencha no $DIR/.env: SMTP, GOOGLE_TTS_API_KEY (e TTS_PROVIDER=google), OPENAI_API_KEY e OPENAI_MODEL"
echo "       e depois: sudo systemctl restart mayaacademy-web@$AMB mayaacademy-worker@$AMB"
