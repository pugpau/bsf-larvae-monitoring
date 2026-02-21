#!/bin/bash
# BSF-LoopTech Alembic マイグレーション整合性チェック
# Usage: ./scripts/verify_migration.sh
#
# マイグレーションチェーンが正常であることを検証します:
#   7b4fa5afc037 → a1 → a2 → a3 → a4 → a5 → a6 → a6b → a7 → a8 → a9 → a10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VERSIONS_DIR="${PROJECT_DIR}/alembic/versions"

# ── Colour helpers ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

log_pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
log_fail() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }
log_info() { echo -e "  ${BLUE}[INFO]${NC} $1"; }
log_header() { echo -e "\n${BLUE}══ $1 ══${NC}"; }

EXPECTED_HEAD="a10_activity_logs"
EXPECTED_COUNT=12

# ══════════════════════════════════════════
# 1. マイグレーションファイルの存在確認
# ══════════════════════════════════════════
log_header "1. マイグレーションファイルの存在確認"

if [ -d "$VERSIONS_DIR" ]; then
    log_pass "versions ディレクトリが存在します"
else
    log_fail "versions ディレクトリが見つかりません: $VERSIONS_DIR"
    echo -e "\n${RED}検証中断: マイグレーションディレクトリが存在しません${NC}"
    exit 1
fi

FILE_COUNT=$(find "$VERSIONS_DIR" -maxdepth 1 -name "*.py" ! -name "__*" | wc -l | tr -d ' ')
if [ "$FILE_COUNT" -eq "$EXPECTED_COUNT" ]; then
    log_pass "マイグレーションファイル数: ${FILE_COUNT} (期待値: ${EXPECTED_COUNT})"
else
    log_fail "マイグレーションファイル数: ${FILE_COUNT} (期待値: ${EXPECTED_COUNT})"
fi

# ══════════════════════════════════════════
# 2. チェーン整合性の検証
# ══════════════════════════════════════════
log_header "2. チェーン整合性の検証"

# 期待されるチェーン (revision → down_revision)
declare -a CHAIN=(
    "7b4fa5afc037:None"
    "a1_phase1_sm:7b4fa5afc037"
    "a2_phase1_ss:a1_phase1_sm"
    "a3_phase1_rc:a2_phase1_ss"
    "a4_phase3_ml:a3_phase1_rc"
    "a5_phase4_rag:a4_phase3_ml"
    "a6_phase5_batch:a5_phase4_rag"
    "a6_phase26_vec_idx:a6_phase5_batch"
    "a7_delivery:a6_phase26_vec_idx"
    "a8_recipe_versions:a7_delivery"
    "a9_formulation_records:a8_recipe_versions"
    "a10_activity_logs:a9_formulation_records"
)

for entry in "${CHAIN[@]}"; do
    rev="${entry%%:*}"
    expected_down="${entry##*:}"

    # Python ファイル内から down_revision を抽出
    actual_down=$(grep -rh "^down_revision" "$VERSIONS_DIR"/*.py 2>/dev/null \
        | grep -v "__pycache__" \
        | while IFS= read -r line; do
            file_rev=$(echo "$line" | sed -n 's/.*"\(.*\)".*/\1/p')
            echo "$file_rev"
        done | head -1 2>/dev/null || echo "")

    # revision が含まれるファイルを検索 (down_revision を除外)
    match_file=$(grep -rl "^revision.*=.*\"${rev}\"" "$VERSIONS_DIR"/*.py 2>/dev/null | head -1 || echo "")

    if [ -n "$match_file" ]; then
        actual_down=$(grep "^down_revision" "$match_file" | sed -n 's/.*"\(.*\)".*/\1/p' | head -1)
        if [ -z "$actual_down" ]; then
            actual_down=$(grep "^down_revision" "$match_file" | grep -o "None" | head -1)
        fi

        if [ "$actual_down" = "$expected_down" ]; then
            log_pass "${rev} → down: ${expected_down}"
        else
            log_fail "${rev} → down: ${actual_down} (期待値: ${expected_down})"
        fi
    else
        log_fail "リビジョン ${rev} のファイルが見つかりません"
    fi
done

# ══════════════════════════════════════════
# 3. HEAD の確認
# ══════════════════════════════════════════
log_header "3. HEAD の確認"

# HEAD = 他のどのマイグレーションからも down_revision として参照されていない revision
ALL_REVISIONS=$(grep -rh "^revision " "$VERSIONS_DIR"/*.py 2>/dev/null | sed -n 's/.*"\(.*\)".*/\1/p' | sort)
ALL_DOWN_REVISIONS=$(grep -rh "^down_revision " "$VERSIONS_DIR"/*.py 2>/dev/null | sed -n 's/.*"\(.*\)".*/\1/p' | sort)

HEAD_COUNT=0
HEAD_REV=""
for rev in $ALL_REVISIONS; do
    if ! echo "$ALL_DOWN_REVISIONS" | grep -qx "$rev"; then
        HEAD_COUNT=$((HEAD_COUNT + 1))
        HEAD_REV="$rev"
    fi
done

if [ "$HEAD_COUNT" -eq 1 ]; then
    log_pass "単一 HEAD: ${HEAD_REV}"
else
    log_fail "HEAD が ${HEAD_COUNT} 個あります (期待値: 1) — ブランチ競合の可能性"
fi

if [ "$HEAD_REV" = "$EXPECTED_HEAD" ]; then
    log_pass "HEAD が期待値と一致: ${EXPECTED_HEAD}"
else
    log_fail "HEAD: ${HEAD_REV} (期待値: ${EXPECTED_HEAD})"
fi

# ══════════════════════════════════════════
# 4. マイグレーションチェーン表示
# ══════════════════════════════════════════
log_header "4. マイグレーションチェーン"

echo ""
echo "  7b4fa5afc037 (initial: users, sessions, login_attempts, ...)"
echo "       |"
echo "  a1_phase1_sm (suppliers, incoming_materials拡張)"
echo "       |"
echo "  a2_phase1_ss (solidification_materials, leaching_suppressants)"
echo "       |"
echo "  a3_phase1_rc (recipes, recipe_details)"
echo "       |"
echo "  a4_phase3_ml (ml_models, ml_predictions)"
echo "       |"
echo "  a5_phase4_rag (chat_sessions, chat_messages, knowledge_chunks)"
echo "       |"
echo "  a6_phase5_batch (batch_job_runs)"
echo "       |"
echo "  a6b_phase26_vec_idx (HNSW vector index)"
echo "       |"
echo "  a7_delivery (incoming_materials, delivery_schedules)"
echo "       |"
echo "  a8_recipe_versions (recipe_versions, recipe_version_details)"
echo "       |"
echo "  a9_formulation_records (formulation_records)"
echo "       |"
echo "  a10_activity_logs (activity_logs) ← HEAD"
echo ""

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
log_header "検証結果サマリー"

echo -e "  ${GREEN}PASS${NC}: ${PASS}"
echo -e "  ${RED}FAIL${NC}: ${FAIL}"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}全チェック合格 — マイグレーションチェーンは正常です${NC}"
    exit 0
else
    echo -e "  ${RED}${FAIL} 件の問題が検出されました — 修正してから再実行してください${NC}"
    exit 1
fi
