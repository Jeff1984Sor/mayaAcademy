#!/usr/bin/env bash
# Backup do banco (pg_dump) + mídia.
#   ./deploy/backup.sh prod                         # diário (cron 02:30), mantém os últimos 5
#   ./deploy/backup.sh prod --antes-de-migration    # chamado pelo deploy.sh antes de migrar (R2)
set -euo pipefail
AMB="${1:-prod}"
MOTIVO="${2:-diario}"; MOTIVO="${MOTIVO#--}"
APP_DIR="/home/deploy/mayaacademy/$AMB"
DESTINO="${BACKUP_DIR:-/home/deploy/backups/mayaacademy/$AMB}"
MANTER="${MANTER:-5}"
le() { grep -E "^$1=" "$APP_DIR/.env" | cut -d= -f2-; }
mkdir -p "$DESTINO"
QUANDO="$(date +%Y%m%d-%H%M)"
PGPASSWORD="$(le DB_PASSWORD)" pg_dump -h "$(le DB_HOST)" -p "$(le DB_PORT)" -U "$(le DB_USER)" -Fc \
  -f "$DESTINO/banco_${QUANDO}_${MOTIVO}.dump" "$(le DB_NAME)"
if [ "$MOTIVO" = "diario" ]; then
  # mídia só no diário (áudios podem ser regerados a partir do roteiro, mas evita custo de TTS)
  tar -czf "$DESTINO/media_${QUANDO}.tar.gz" -C "$APP_DIR" media 2>/dev/null || true
  ls -1t "$DESTINO"/banco_*_diario.dump 2>/dev/null | tail -n +$((MANTER + 1)) | xargs -r rm -f
  ls -1t "$DESTINO"/media_*.tar.gz 2>/dev/null | tail -n +$((MANTER + 1)) | xargs -r rm -f
fi
# backups pré-migration: mantém os últimos 10
ls -1t "$DESTINO"/banco_*_antes-de-migration.dump 2>/dev/null | tail -n +11 | xargs -r rm -f
echo "Backup $AMB $QUANDO ($MOTIVO) ok em $DESTINO"
