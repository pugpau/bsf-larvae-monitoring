#!/bin/bash

# BSF-LoopTech データベースバックアップスクリプト
# Docker環境用 — PostgreSQLのみ
#
# Usage: ./scripts/backup_databases.sh
# Cron/launchd: config/com.bsf-looptech.backup.plist (daily 3:00 AM JST)

set -e

# 設定
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BSF_BACKUP_DIR:-$HOME/BSF_Backups}"
CONTAINER_NAME="${BSF_POSTGRES_CONTAINER:-bsf-postgres}"
POSTGRES_USER="${POSTGRES_USER:-bsf_user}"
POSTGRES_DB="${POSTGRES_DB:-bsf_system}"
RETENTION_DAYS=30

# ログ関数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# バックアップディレクトリ作成
mkdir -p "${BACKUP_DIR}/postgres"

# Dockerコンテナの状態確認
if ! docker inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
    log_error "PostgreSQLコンテナ '$CONTAINER_NAME' が見つかりません"
    exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME")" != "true" ]; then
    log_error "PostgreSQLコンテナ '$CONTAINER_NAME' が起動していません"
    exit 1
fi

# PostgreSQLバックアップ（Docker exec経由）
BACKUP_FILE="${BACKUP_DIR}/postgres/bsf_${TIMESTAMP}.sql.gz"
log_info "PostgreSQLバックアップを開始します..."

if docker exec "$CONTAINER_NAME" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --verbose --clean --if-exists --create 2>/dev/null \
    | gzip > "$BACKUP_FILE"; then

    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "PostgreSQLバックアップ完了: $(basename "$BACKUP_FILE") ($BACKUP_SIZE)"
else
    log_error "PostgreSQLバックアップ失敗"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 古いバックアップファイルの削除
log_info "古いバックアップを削除中（${RETENTION_DAYS}日以上前）..."
DELETED_COUNT=$(find "${BACKUP_DIR}/postgres" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l | tr -d ' ')
if [ "$DELETED_COUNT" -gt 0 ]; then
    log_info "  ${DELETED_COUNT}件の古いバックアップを削除しました"
fi

# バックアップ一覧を表示
TOTAL_BACKUPS=$(find "${BACKUP_DIR}/postgres" -name "*.sql.gz" | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}/postgres" 2>/dev/null | cut -f1)
log_info "バックアップ完了 — 合計: ${TOTAL_BACKUPS}件 (${TOTAL_SIZE})"
