#!/usr/bin/env bash
# Volta um ambiente para uma versão anterior:  ./deploy/rollback.sh prod v7
# Não desfaz migrations (nunca rodamos "migrate zero" sem confirmação do Jefferson).
# Se a versão nova criou colunas, elas ficam; para voltar o banco, restaure o backup
# feito antes da migration (pasta de backups, arquivo *_antes-de-migration.dump).
set -euo pipefail
AMB="${1:?ambiente (hml|prod)}"
VERSAO="${2:?versão (ex.: v7)}"
APP_DIR="${APP_DIR:-$HOME/mayaacademy/$AMB}"
cd "$APP_DIR"
if ! git rev-parse -q --verify "refs/tags/$VERSAO" >/dev/null; then
  echo "Tag $VERSAO não existe. Últimas:"
  git tag --list 'v*' | sort -V | tail -5
  exit 1
fi
git checkout -q "$VERSAO"
.venv/bin/pip install -q -r requirements.txt
npm ci --silent && npm run build:css --silent
.venv/bin/python manage.py montar_player
.venv/bin/python manage.py collectstatic --noinput -v0
echo "$VERSAO" > VERSION
sudo systemctl restart "mayaacademy-web@$AMB" "mayaacademy-worker@$AMB"
echo "Ambiente $AMB de volta em $VERSAO. Para retomar a branch: git checkout main"
