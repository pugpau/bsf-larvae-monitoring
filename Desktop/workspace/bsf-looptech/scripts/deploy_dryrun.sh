#!/bin/bash
# BSF-LoopTech デプロイ ドライラン
# Usage: ./scripts/deploy_dryrun.sh
#
# 本番デプロイの事前検証を行います。トラフィック切り替えは実行しません。
# すべてのチェックが PASS であれば、deploy-blue-green.sh deploy を実行してください。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ACTIVE_SLOT_FILE="${PROJECT_DIR}/config/active-slot"
REPORT_FILE="${PROJECT_DIR}/logs/dryrun_$(date '+%Y%m%d_%H%M%S').log"

# ── Colour helpers ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

log_pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
log_fail() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }
log_warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$((WARN + 1)); }
log_info() { echo -e "  ${BLUE}[INFO]${NC} $1"; }
log_header() { echo -e "\n${BLUE}══ $1 ══${NC}"; }

dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

cleanup() {
    log_header "クリーンアップ"
    if [ -n "${TARGET:-}" ]; then
        log_info "backend-${TARGET} を停止しています..."
        dc stop "backend-${TARGET}" 2>/dev/null || true
    fi
}

# ドライランがエラーで終了した場合もクリーンアップ
trap cleanup EXIT

# ログディレクトリ作成
mkdir -p "${PROJECT_DIR}/logs"

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   BSF-LoopTech デプロイ ドライラン       ║${NC}"
echo -e "${BLUE}║   $(date '+%Y-%m-%d %H:%M:%S')                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"

# ══════════════════════════════════════════
# 1. 前提条件の確認
# ══════════════════════════════════════════
log_header "1. 前提条件の確認"

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VER=$(docker --version | cut -d' ' -f3 | tr -d ',')
    log_pass "Docker: ${DOCKER_VER}"
else
    log_fail "Docker が見つかりません"
fi

# docker compose
if docker compose version &> /dev/null; then
    COMPOSE_VER=$(docker compose version --short 2>/dev/null || echo "unknown")
    log_pass "Docker Compose: ${COMPOSE_VER}"
else
    log_fail "Docker Compose が見つかりません"
fi

# .env.production
if [ -f "${PROJECT_DIR}/.env.production" ]; then
    log_pass ".env.production が存在します"
    # プレースホルダーチェック
    if grep -q "CHANGE_ME\|GENERATE_WITH" "${PROJECT_DIR}/.env.production"; then
        log_fail ".env.production にプレースホルダーが残っています"
    else
        log_pass ".env.production のプレースホルダーなし"
    fi
else
    log_fail ".env.production が見つかりません"
    echo -e "  ${YELLOW}→ cp config/env.production.template .env.production で作成してください${NC}"
fi

# SSL 証明書
if [ -f "${PROJECT_DIR}/config/ssl/server.crt" ] && [ -f "${PROJECT_DIR}/config/ssl/server.key" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in "${PROJECT_DIR}/config/ssl/server.crt" 2>/dev/null | cut -d= -f2 || echo "unknown")
    log_pass "SSL 証明書: 有効期限 ${EXPIRY}"
else
    log_warn "SSL 証明書が見つかりません (HTTPS 無効)"
fi

# ══════════════════════════════════════════
# 2. スロット判定
# ══════════════════════════════════════════
log_header "2. スロット判定"

TARGET=""
if [ -f "$ACTIVE_SLOT_FILE" ]; then
    ACTIVE=$(cat "$ACTIVE_SLOT_FILE")
    if [ "$ACTIVE" = "blue" ]; then
        TARGET="green"
    else
        TARGET="blue"
    fi
    log_pass "アクティブスロット: ${ACTIVE} → ターゲット: ${TARGET}"
else
    TARGET="blue"
    log_info "初回デプロイ: ターゲット = blue"
fi

# ══════════════════════════════════════════
# 3. Docker イメージビルド
# ══════════════════════════════════════════
log_header "3. Docker イメージビルド"

log_info "backend-${TARGET} をビルドしています..."
if dc build "backend-${TARGET}" 2>&1; then
    log_pass "backend-${TARGET} ビルド成功"
else
    log_fail "backend-${TARGET} ビルド失敗"
fi

# イメージサイズ
IMAGE_SIZE=$(docker images --format "{{.Size}}" "bsf-looptech-backend-${TARGET}" 2>/dev/null | head -1 || echo "unknown")
log_info "イメージサイズ: ${IMAGE_SIZE}"

# ══════════════════════════════════════════
# 4. PostgreSQL 確認
# ══════════════════════════════════════════
log_header "4. PostgreSQL 確認"

log_info "PostgreSQL コンテナを起動しています..."
dc up -d postgres 2>&1

# PostgreSQL の起動待ち
MAX_WAIT=60
ELAPSED=0
while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
    if dc exec -T postgres pg_isready -U bsf_user -d bsf_system > /dev/null 2>&1; then
        log_pass "PostgreSQL 起動完了 (${ELAPSED}s)"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    log_fail "PostgreSQL が ${MAX_WAIT}s 以内に起動しませんでした"
fi

# ══════════════════════════════════════════
# 5. Alembic マイグレーション (プレビュー)
# ══════════════════════════════════════════
log_header "5. Alembic マイグレーション (プレビュー)"

log_info "マイグレーション SQL をプレビューしています..."
if dc run --rm "backend-${TARGET}" alembic upgrade head --sql > /dev/null 2>&1; then
    log_pass "マイグレーション SQL 生成成功 (ドライラン)"
else
    log_warn "マイグレーション SQL プレビューをスキップ (DB 未初期化の可能性)"
fi

# マイグレーション整合性チェック
if [ -x "${SCRIPT_DIR}/verify_migration.sh" ]; then
    if "${SCRIPT_DIR}/verify_migration.sh" > /dev/null 2>&1; then
        log_pass "マイグレーションチェーン整合性 OK"
    else
        log_fail "マイグレーションチェーン整合性エラー"
    fi
else
    log_warn "verify_migration.sh が見つかりません"
fi

# ══════════════════════════════════════════
# 6. バックエンド起動テスト
# ══════════════════════════════════════════
log_header "6. バックエンド起動テスト"

log_info "backend-${TARGET} を起動しています..."
dc up -d "backend-${TARGET}" 2>&1

# 起動待ち
MAX_WAIT=60
ELAPSED=0
BACKEND_READY=false
while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
    if docker exec "bsf-backend-${TARGET}" curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log_pass "backend-${TARGET} 起動完了 (${ELAPSED}s)"
        BACKEND_READY=true
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ "$BACKEND_READY" = false ]; then
    log_fail "backend-${TARGET} が ${MAX_WAIT}s 以内に起動しませんでした"
fi

# ══════════════════════════════════════════
# 7. ヘルスチェック
# ══════════════════════════════════════════
log_header "7. ヘルスチェック"

if [ "$BACKEND_READY" = true ]; then
    # /health
    HEALTH_CODE=$(docker exec "bsf-backend-${TARGET}" curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
    if [ "$HEALTH_CODE" = "200" ]; then
        log_pass "GET /health → ${HEALTH_CODE}"
    else
        log_fail "GET /health → ${HEALTH_CODE} (期待値: 200)"
    fi

    # /ready
    READY_CODE=$(docker exec "bsf-backend-${TARGET}" curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/ready 2>/dev/null || echo "000")
    if [ "$READY_CODE" = "200" ]; then
        log_pass "GET /ready → ${READY_CODE}"
    else
        log_fail "GET /ready → ${READY_CODE} (期待値: 200)"
    fi

    # /health 応答内容
    HEALTH_BODY=$(docker exec "bsf-backend-${TARGET}" curl -sf http://localhost:8000/health 2>/dev/null || echo "{}")
    log_info "Health 応答: ${HEALTH_BODY}"
else
    log_fail "バックエンド未起動のためヘルスチェックをスキップ"
fi

# ══════════════════════════════════════════
# 8. backend-TARGET を停止 (トラフィック切り替えなし)
# ══════════════════════════════════════════
log_header "8. ターゲットバックエンド停止"

log_info "backend-${TARGET} を停止しています (ドライランのため)..."
dc stop "backend-${TARGET}" 2>/dev/null || true
# trap の cleanup が二重実行しないよう TARGET をクリア
TARGET=""
log_pass "ドライラン用バックエンドを停止しました"

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
log_header "ドライラン結果サマリー"

echo -e "  タイムスタンプ: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  イメージサイズ: ${IMAGE_SIZE:-unknown}"
echo -e "  ${GREEN}PASS${NC}: ${PASS}"
echo -e "  ${RED}FAIL${NC}: ${FAIL}"
echo -e "  ${YELLOW}WARN${NC}: ${WARN}"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}ドライラン完了 — 問題は検出されませんでした${NC}"
    echo ""
    echo -e "  本番デプロイを実行するには:"
    echo -e "    ${BLUE}./scripts/deploy-blue-green.sh deploy${NC}"
    echo -e "  (初回の場合)"
    echo -e "    ${BLUE}./scripts/deploy-blue-green.sh init${NC}"
    exit 0
else
    echo -e "  ${RED}${FAIL} 件の問題が検出されました — 修正後に再実行してください${NC}"
    exit 1
fi
