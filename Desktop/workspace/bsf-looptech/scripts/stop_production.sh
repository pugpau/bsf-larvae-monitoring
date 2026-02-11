#!/bin/bash

# BSF-LoopTech 本番環境停止スクリプト
# MacBook本番運用用

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

log_header "BSF-LoopTech 本番環境停止"

# 1. アプリケーションプロセス停止
log_info "1. アプリケーションプロセス停止中..."

# PIDファイルから各プロセスを停止
PID_FILES=(
    "temp/app.pid:FastAPIアプリケーション"
    "temp/ml_scheduler.pid:MLパイプラインスケジューラー"
    "temp/mosquitto.pid:TLS MQTTブローカー"
)

for pid_file_info in "${PID_FILES[@]}"; do
    pid_file="${pid_file_info%%:*}"
    process_name="${pid_file_info##*:}"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "  停止中: $process_name (PID: $pid)"
            kill -TERM "$pid"
            
            # プロセス終了を待機（最大10秒）
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # 強制終了が必要な場合
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "  強制終了: $process_name (PID: $pid)"
                kill -KILL "$pid"
            fi
            
            log_info "  ✅ $process_name を停止しました"
        else
            log_warn "  $process_name は既に停止しています"
        fi
        rm -f "$pid_file"
    else
        log_warn "  $process_name のPIDファイルが見つかりません"
    fi
done

# 2. 関連プロセスの確認と停止
log_info "2. 関連プロセス確認中..."

# 残存するプロセスを検索して停止
PROCESS_PATTERNS=(
    "uvicorn.*main:app"
    "python.*ml_pipeline_manager.py"
    "mosquitto.*mosquitto.conf"
)

for pattern in "${PROCESS_PATTERNS[@]}"; do
    pids=$(pgrep -f "$pattern" 2>/dev/null || echo "")
    if [ -n "$pids" ]; then
        log_info "  残存プロセス発見: $pattern"
        for pid in $pids; do
            log_info "  停止中: PID $pid"
            kill -TERM "$pid" 2>/dev/null || true
        done
    fi
done

# 3. データベースサービスの処理
log_info "3. データベースサービス確認中..."

# 開発用途のため、PostgreSQLとInfluxDBは停止しない
# （他のアプリケーションでも使用されている可能性があるため）
log_info "  PostgreSQL: 継続実行（他のアプリケーションで使用される可能性があります）"
log_info "  InfluxDB: 継続実行（他のアプリケーションで使用される可能性があります）"

# 4. MQTTブローカーの処理
log_info "4. MQTTブローカー確認中..."

# Brew管理のMosquittoは停止しない（システム全体で使用される可能性があるため）
log_info "  標準Mosquitto: 継続実行（システム全体で使用される可能性があります）"

# 5. 一時ファイルのクリーンアップ
log_info "5. 一時ファイルクリーンアップ中..."

# 一時ファイルを削除
if [ -d "temp" ]; then
    rm -f temp/*.pid
    rm -f temp/production_started.marker
    log_info "  ✅ 一時ファイルを削除しました"
fi

# 6. 最終確認
log_info "6. 停止確認中..."

sleep 2

# プロセス確認
RUNNING_PROCESSES=()
for pattern in "${PROCESS_PATTERNS[@]}"; do
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        RUNNING_PROCESSES+=("$pattern")
    fi
done

if [ ${#RUNNING_PROCESSES[@]} -eq 0 ]; then
    log_info "  ✅ 全てのBSF-LoopTechプロセスが停止しました"
else
    log_warn "  ⚠️  以下のプロセスがまだ実行中です:"
    for process in "${RUNNING_PROCESSES[@]}"; do
        log_warn "    - $process"
    done
fi

# 7. ログ情報保存
log_info "7. 停止ログ保存中..."

# 停止時刻をログに記録
echo "$(date): BSF-LoopTech production stopped" >> logs/system.log

log_header "システム停止完了"

echo ""
log_info "🛑 BSF-LoopTech本番環境の停止が完了しました"
echo ""
log_info "📊 システム状況:"
if [ ${#RUNNING_PROCESSES[@]} -eq 0 ]; then
    log_info "  ✅ 全てのアプリケーションプロセスが停止"
else
    log_warn "  ⚠️  一部プロセスが実行中（上記参照）"
fi
echo ""
log_info "💾 データベース:"
log_info "  - PostgreSQL: 継続実行中"
log_info "  - InfluxDB: 継続実行中"
echo ""
log_info "📁 保持されるデータ:"
log_info "  - ログファイル: logs/"
log_info "  - データベース: 保持"
log_info "  - モデルレジストリ: model_registry/"
log_info "  - 証明書: certs/"
echo ""
log_info "🔄 再起動方法:"
log_info "  ./scripts/start_production.sh"
echo ""

log_info "✅ 本番環境停止プロセス完了"