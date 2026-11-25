#!/usr/bin/env bash
#
# Deploy da MayaAcademy (mesmo ritual do MayaJus/RCA): passos sempre na mesma ordem,
# testes antes de reiniciar, backup do banco antes de migration e, em produção, tag vN.
# Nada vai para produção sem ter passado pela homologação.
#
# Uso (no servidor, como deploy, dentro de /home/deploy/mayaacademy/<amb>):
#     ./deploy/deploy.sh hml            # branch develop -> hml-academy.mayacorp.com.br
#     ./deploy/deploy.sh prod           # branch main    -> academy.mayacorp.com.br  (cria tag vN)
#     ./deploy/deploy.sh prod --sem-tag
#
set -euo pipefail

AMB="${1:?informe o ambiente: hml ou prod}"
case "$AMB" in
  hml)  BRANCH="${BRANCH:-develop}" ;;
  prod) BRANCH="${BRANCH:-main}" ;;
  *) echo "Ambiente inválido: $AMB"; exit 1 ;;
esac
CRIAR_TAG=0
[ "$AMB" = "prod" ] && CRIAR_TAG=1
[ "${2:-}" = "--sem-tag" ] && CRIAR_TAG=0

APP_DIR="${APP_DIR:-$HOME/mayaacademy/$AMB}"
SERVICOS="mayaacademy-web@$AMB mayaacademy-worker@$AMB"
cd "$APP_DIR"
PY="$APP_DIR/.venv/bin/python"
WEB_PORTA="$(grep -E '^WEB_PORTA=' .env | cut -d= -f2)"
DOMINIO="$(grep -E '^ALLOWED_HOSTS=' .env | cut -d= -f2 | cut -d, -f1)"

echo "=== 1/8  Situação atual ($AMB) ==="
VERSAO_ANTERIOR="$(cat VERSION 2>/dev/null || echo dev)"
COMMIT_ANTERIOR="$(git rev-parse --short HEAD)"
echo "    no ar: $VERSAO_ANTERIOR ($COMMIT_ANTERIOR)"
if [ -n "$(git status --porcelain -uno)" ]; then
  echo "    ATENÇÃO: arquivos versionados modificados no servidor:"
  git status --short -uno
  read -r -p "    Continuar? [s/N] " r
  [ "$r" = "s" ] || exit 1
fi

echo "=== 2/8  Código ($BRANCH) ==="
git fetch -q origin
git fetch -q origin --tags 2>/dev/null || true
git checkout -q "$BRANCH"
git pull -q --ff-only origin "$BRANCH"
COMMIT_NOVO="$(git rev-parse --short HEAD)"
git log --oneline "$COMMIT_ANTERIOR..$COMMIT_NOVO" | sed 's/^/      /'

echo "=== 3/8  Dependências, CSS e player ==="
.venv/bin/pip install -q -r requirements.txt
npm ci --silent
npm run build:css --silent
"$PY" manage.py montar_player

echo "=== 4/8  Testes ==="
if ! "$PY" -m pytest -q; then
  echo "    Testes falharam. Deploy abortado (nada foi reiniciado, banco intacto)."
  exit 1
fi

echo "=== 5/8  Migrations (backup antes, se houver alguma pendente) ==="
if ! "$PY" manage.py migrate --check >/dev/null 2>&1; then
  ./deploy/backup.sh "$AMB" --antes-de-migration
  "$PY" manage.py migrate --noinput
else
  echo "    nenhuma migration pendente"
fi
"$PY" manage.py collectstatic --noinput -v0

echo "=== 6/8  Versão ==="
if [ "$CRIAR_TAG" = "1" ]; then
  ULTIMA="$(git tag --list 'v[0-9]*' | sed 's/^v//' | sort -n | tail -1)"
  PROXIMA="v$(( ${ULTIMA:-0} + 1 ))"
  echo "$PROXIMA" > VERSION
  GIT_ID=(-c user.name="Deploy MayaCorp" -c user.email="deploy@mayacorp.com.br")
  git "${GIT_ID[@]}" tag -a "$PROXIMA" -m "Deploy $PROXIMA em $(date '+%d/%m/%Y %H:%M')"
  if git push -q origin "$PROXIMA" 2>/dev/null; then echo "    tag $PROXIMA publicada"; else echo "    tag $PROXIMA só local (o rollback funciona igual)"; fi
else
  echo "hml-$COMMIT_NOVO" > VERSION
fi

echo "=== 7/8  Reiniciando ==="
# Reaplica os units do systemd se mudaram no repositório (só os da MayaAcademy).
BASE="$(dirname "$APP_DIR")"
for svc in web worker; do
  NOVO="$(sed "s|__BASE__|$BASE|g; s|__USUARIO__|$(id -un)|g" "deploy/systemd/mayaacademy-$svc@.service")"
  if [ "$NOVO" != "$(cat "/etc/systemd/system/mayaacademy-$svc@.service" 2>/dev/null)" ]; then
    echo "$NOVO" | sudo tee "/etc/systemd/system/mayaacademy-$svc@.service" >/dev/null
    echo "    unit mayaacademy-$svc@ atualizado"
    UNITS_MUDARAM=1
  fi
done
[ "${UNITS_MUDARAM:-0}" = "1" ] && sudo systemctl daemon-reload
sudo systemctl restart $SERVICOS
sleep 4
systemctl is-active $SERVICOS

echo "=== 8/8  Saúde ==="
CODIGO="$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $DOMINIO" -H 'X-Forwarded-Proto: https' "http://127.0.0.1:$WEB_PORTA/saude/" || echo 000)"
echo "    /saude/: HTTP $CODIGO"
if [ "$CODIGO" != "200" ]; then
  echo "    O site NÃO respondeu. Para voltar:  ./deploy/rollback.sh $AMB $VERSAO_ANTERIOR"
  exit 1
fi
echo "    OK: $(cat VERSION) no ar em $AMB."
