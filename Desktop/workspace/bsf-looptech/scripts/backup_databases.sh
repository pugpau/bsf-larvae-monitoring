#!/bin/bash

# BSF-LoopTech データベースバックアップスクリプト
# Docker環境用

set -e

# 設定
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups"
POSTGRES_HOST="postgres"
POSTGRES_USER="bsf_user"
POSTGRES_DB="bsf_system"
INFLUXDB_HOST="influxdb"
INFLUXDB_ORG="bsf_org"
INFLUXDB_BUCKET="bsf_data"

# ログ関数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# バックアップディレクトリ作成
mkdir -p "${BACKUP_DIR}/postgres" "${BACKUP_DIR}/influxdb"

# PostgreSQLバックアップ
log_info "Starting PostgreSQL backup..."
if pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    --verbose --clean --if-exists --create \
    > "${BACKUP_DIR}/postgres/bsf_postgres_${TIMESTAMP}.sql"; then
    log_info "PostgreSQL backup completed: bsf_postgres_${TIMESTAMP}.sql"
else
    log_error "PostgreSQL backup failed"
    exit 1
fi

# InfluxDBバックアップ (データエクスポート)
log_info "Starting InfluxDB backup..."
if curl -X POST "http://${INFLUXDB_HOST}:8086/api/v2/query" \
    -H "Authorization: Token ${INFLUXDB_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "from(bucket: \"'${INFLUXDB_BUCKET}'\") |> range(start: -30d)",
        "type": "flux"
    }' > "${BACKUP_DIR}/influxdb/bsf_influxdb_${TIMESTAMP}.json"; then
    log_info "InfluxDB backup completed: bsf_influxdb_${TIMESTAMP}.json"
else
    log_error "InfluxDB backup failed"
    exit 1
fi

# 古いバックアップファイルの削除（30日以上前）
log_info "Cleaning up old backup files..."
find "${BACKUP_DIR}" -name "*.sql" -mtime +30 -delete
find "${BACKUP_DIR}" -name "*.json" -mtime +30 -delete

log_info "Backup process completed successfully"