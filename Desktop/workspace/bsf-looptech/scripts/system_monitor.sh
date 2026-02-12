#!/bin/bash

# BSF-LoopTech システム監視スクリプト
# Docker環境用 — コンテナ・リソース監視
#
# Usage: ./scripts/system_monitor.sh [--json] [--quiet]
# launchd: config/com.bsf-looptech.monitor.plist (30分ごと)

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# オプション解析
JSON_OUTPUT=false
QUIET=false
for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --quiet) QUIET=true ;;
    esac
done

# ログ関数
log_info() {
    if [ "$QUIET" = false ]; then
        echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_header() {
    if [ "$QUIET" = false ]; then
        echo -e "${BLUE}================================${NC}"
        echo -e "${BLUE}$1${NC}"
        echo -e "${BLUE}================================${NC}"
    fi
}

EXIT_CODE=0

# ─── システムリソース監視 ───
check_system_resources() {
    log_header "システムリソース"

    # CPU使用率（macOS）
    CPU_USAGE=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | tr -d '%')
    log_info "CPU使用率: ${CPU_USAGE}%"
    if (( $(echo "$CPU_USAGE > 90" | bc -l) )); then
        log_warn "CPU使用率が90%を超えています"
        EXIT_CODE=1
    fi

    # メモリ使用率
    MEM_TOTAL=$(sysctl -n hw.memsize 2>/dev/null)
    MEM_TOTAL_GB=$(echo "scale=1; $MEM_TOTAL / 1073741824" | bc)
    # vm_stat で空きページ数を取得
    FREE_PAGES=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
    PAGE_SIZE=$(sysctl -n hw.pagesize)
    MEM_FREE_GB=$(echo "scale=1; $FREE_PAGES * $PAGE_SIZE / 1073741824" | bc)
    MEM_USED_GB=$(echo "scale=1; $MEM_TOTAL_GB - $MEM_FREE_GB" | bc)
    MEM_PERCENT=$(echo "scale=0; $MEM_USED_GB * 100 / $MEM_TOTAL_GB" | bc)
    log_info "メモリ: ${MEM_USED_GB}GB / ${MEM_TOTAL_GB}GB (${MEM_PERCENT}%)"
    if [ "$MEM_PERCENT" -gt 90 ]; then
        log_warn "メモリ使用率が90%を超えています"
        EXIT_CODE=1
    fi

    # ディスク使用率
    DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
    DISK_AVAIL=$(df -h / | tail -1 | awk '{print $4}')
    log_info "ディスク: ${DISK_USAGE}% 使用中 (空き: ${DISK_AVAIL})"
    if [ "$DISK_USAGE" -gt 85 ]; then
        log_warn "ディスク使用率が85%を超えています"
        EXIT_CODE=1
    fi
}

# ─── Dockerコンテナ監視 ───
check_docker_containers() {
    log_header "Dockerコンテナ"

    # Docker の動作確認
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker が起動していません"
        EXIT_CODE=2
        return
    fi

    # 期待されるコンテナ一覧
    EXPECTED_CONTAINERS=("bsf-postgres" "bsf-router")

    for CONTAINER in "${EXPECTED_CONTAINERS[@]}"; do
        if docker inspect "$CONTAINER" > /dev/null 2>&1; then
            STATUS=$(docker inspect -f '{{.State.Status}}' "$CONTAINER")
            HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "no-healthcheck")

            if [ "$STATUS" = "running" ]; then
                if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "no-healthcheck" ]; then
                    log_info "$CONTAINER: ${GREEN}running${NC} ($HEALTH)"
                else
                    log_warn "$CONTAINER: running but $HEALTH"
                    EXIT_CODE=1
                fi
            else
                log_error "$CONTAINER: $STATUS"
                EXIT_CODE=2
            fi
        else
            log_error "$CONTAINER: コンテナが存在しません"
            EXIT_CODE=2
        fi
    done

    # Blue-Green バックエンド — アクティブスロットのみチェック
    ACTIVE_SLOT_FILE="config/active-slot"
    if [ -f "$ACTIVE_SLOT_FILE" ]; then
        ACTIVE_SLOT=$(cat "$ACTIVE_SLOT_FILE")
        ACTIVE_CONTAINER="bsf-backend-${ACTIVE_SLOT}"
        if docker inspect "$ACTIVE_CONTAINER" > /dev/null 2>&1; then
            STATUS=$(docker inspect -f '{{.State.Status}}' "$ACTIVE_CONTAINER")
            HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$ACTIVE_CONTAINER" 2>/dev/null || echo "no-healthcheck")
            if [ "$STATUS" = "running" ] && [ "$HEALTH" = "healthy" ]; then
                log_info "$ACTIVE_CONTAINER (active): ${GREEN}running${NC} ($HEALTH)"
            else
                log_error "$ACTIVE_CONTAINER (active): $STATUS ($HEALTH)"
                EXIT_CODE=2
            fi
        else
            log_error "アクティブバックエンド '$ACTIVE_CONTAINER' が存在しません"
            EXIT_CODE=2
        fi
    else
        log_warn "active-slot ファイルが見つかりません（Blue-Green未初期化？）"
    fi
}

# ─── PostgreSQL接続確認 ───
check_postgresql() {
    log_header "PostgreSQL"

    CONTAINER_NAME="bsf-postgres"
    if docker inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
        if docker exec "$CONTAINER_NAME" pg_isready -U bsf_user -d bsf_system > /dev/null 2>&1; then
            log_info "PostgreSQL: ${GREEN}接続OK${NC}"

            # DB サイズ
            DB_SIZE=$(docker exec "$CONTAINER_NAME" psql -U bsf_user -d bsf_system -t -c "SELECT pg_size_pretty(pg_database_size('bsf_system'));" 2>/dev/null | tr -d ' ')
            log_info "データベースサイズ: $DB_SIZE"

            # アクティブ接続数
            CONN_COUNT=$(docker exec "$CONTAINER_NAME" psql -U bsf_user -d bsf_system -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='bsf_system';" 2>/dev/null | tr -d ' ')
            log_info "アクティブ接続数: $CONN_COUNT"
        else
            log_error "PostgreSQL: 接続失敗"
            EXIT_CODE=2
        fi
    else
        log_error "PostgreSQLコンテナが存在しません"
        EXIT_CODE=2
    fi
}

# ─── ヘルスチェック ───
check_health_endpoints() {
    log_header "ヘルスチェック"

    # /health エンドポイント (port 3000 via router)
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/health 2>/dev/null || echo "000")
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        log_info "/health: ${GREEN}OK${NC} (HTTP $HEALTH_RESPONSE)"
    else
        log_error "/health: 応答なし (HTTP $HEALTH_RESPONSE)"
        EXIT_CODE=2
    fi

    # /ready エンドポイント
    READY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ready 2>/dev/null || echo "000")
    if [ "$READY_RESPONSE" = "200" ]; then
        log_info "/ready: ${GREEN}OK${NC} (HTTP $READY_RESPONSE)"
    else
        log_warn "/ready: 未準備 (HTTP $READY_RESPONSE)"
        EXIT_CODE=1
    fi
}

# ─── バックアップ確認 ───
check_backups() {
    log_header "バックアップ"

    BACKUP_DIR="${BSF_BACKUP_DIR:-$HOME/BSF_Backups}/postgres"
    if [ -d "$BACKUP_DIR" ]; then
        LATEST=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
        if [ -n "$LATEST" ]; then
            LATEST_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$LATEST")
            LATEST_SIZE=$(du -h "$LATEST" | cut -f1)
            TOTAL_COUNT=$(ls "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l | tr -d ' ')
            log_info "最新バックアップ: $(basename "$LATEST") ($LATEST_SIZE, $LATEST_DATE)"
            log_info "バックアップ総数: ${TOTAL_COUNT}件"

            # 24時間以上前の場合は警告
            LATEST_EPOCH=$(stat -f "%m" "$LATEST")
            NOW_EPOCH=$(date +%s)
            DIFF_HOURS=$(( (NOW_EPOCH - LATEST_EPOCH) / 3600 ))
            if [ "$DIFF_HOURS" -gt 25 ]; then
                log_warn "最新バックアップが${DIFF_HOURS}時間前です（24時間以上経過）"
                EXIT_CODE=1
            fi
        else
            log_warn "バックアップファイルが見つかりません"
            EXIT_CODE=1
        fi
    else
        log_warn "バックアップディレクトリが存在しません: $BACKUP_DIR"
    fi
}

# ─── 実行 ───
log_header "BSF-LoopTech システム監視 — $(date '+%Y-%m-%d %H:%M:%S')"
check_system_resources
check_docker_containers
check_postgresql
check_health_endpoints
check_backups

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    log_info "全チェック ${GREEN}正常${NC}"
elif [ $EXIT_CODE -eq 1 ]; then
    log_warn "警告あり — 確認してください"
else
    log_error "異常検出 — 対応が必要です"
fi

exit $EXIT_CODE
