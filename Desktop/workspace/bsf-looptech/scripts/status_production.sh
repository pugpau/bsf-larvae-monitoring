#!/bin/bash

# BSF-LoopTech 本番環境ステータス確認スクリプト
# MacBook本番運用用

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

log_section() {
    echo -e "${CYAN}--- $1 ---${NC}"
}

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

log_header "BSF-LoopTech 本番環境ステータス"
echo ""

# 1. システム概要
log_section "システム概要"
echo "📅 確認日時: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📂 プロジェクト: $PROJECT_DIR"

if [ -f "temp/production_started.marker" ]; then
    start_time=$(cat temp/production_started.marker)
    echo "🚀 起動時刻: $start_time"
    
    # 稼働時間計算
    start_epoch=$(date -j -f "%Y-%m-%d %H:%M:%S" "$start_time" "+%s" 2>/dev/null || echo "0")
    current_epoch=$(date "+%s")
    uptime_seconds=$((current_epoch - start_epoch))
    
    if [ $uptime_seconds -gt 0 ]; then
        uptime_days=$((uptime_seconds / 86400))
        uptime_hours=$(( (uptime_seconds % 86400) / 3600 ))
        uptime_minutes=$(( (uptime_seconds % 3600) / 60 ))
        echo "⏱️  稼働時間: ${uptime_days}日 ${uptime_hours}時間 ${uptime_minutes}分"
    fi
else
    log_warn "起動マーカーファイルが見つかりません"
fi
echo ""

# 2. プロセス状況
log_section "プロセス状況"

PROCESS_CHECKS=(
    "FastAPIアプリケーション:temp/app.pid:uvicorn.*main:app"
    "MLパイプラインスケジューラー:temp/ml_scheduler.pid:python.*ml_pipeline_manager.py"
    "TLS MQTTブローカー:temp/mosquitto.pid:mosquitto.*mosquitto.conf"
)

for check in "${PROCESS_CHECKS[@]}"; do
    IFS=':' read -r name pid_file pattern <<< "$check"
    
    echo -n "  $name: "
    
    # PIDファイルから確認
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}実行中${NC} (PID: $pid)"
        else
            echo -e "${RED}停止${NC} (PIDファイル残存)"
        fi
    else
        # プロセスパターンで検索
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            pids=$(pgrep -f "$pattern" | tr '\n' ' ')
            echo -e "${YELLOW}実行中${NC} (PID: $pids - PIDファイル無し)"
        else
            echo -e "${RED}停止${NC}"
        fi
    fi
done
echo ""

# 3. サービス状況
log_section "サービス状況"

# HTTP API確認
echo -n "  HTTP API (localhost:8000): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}正常${NC}"
elif curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null | grep -q "200\|404"; then
    echo -e "${YELLOW}接続可能${NC} (ヘルスエンドポイント無し)"
else
    echo -e "${RED}接続不可${NC}"
fi

# MQTT TLS確認
echo -n "  MQTT TLS (localhost:8883): "
if timeout 5 mosquitto_pub -h localhost -p 8883 --cafile certs/ca.crt -t "test/status" -m "test" > /dev/null 2>&1; then
    echo -e "${GREEN}正常${NC}"
else
    echo -e "${RED}接続不可${NC}"
fi

# MQTT標準確認
echo -n "  MQTT Standard (localhost:1883): "
if timeout 5 mosquitto_pub -h localhost -p 1883 -t "test/status" -m "test" > /dev/null 2>&1; then
    echo -e "${GREEN}正常${NC}"
else
    echo -e "${RED}接続不可${NC}"
fi

echo ""

# 4. データベース状況
log_section "データベース状況"

# PostgreSQL確認
echo -n "  PostgreSQL: "
if brew services list | grep postgresql | grep started > /dev/null; then
    echo -e "${GREEN}実行中${NC}"
else
    echo -e "${RED}停止${NC}"
fi

# InfluxDB確認
echo -n "  InfluxDB: "
if brew services list | grep influxdb | grep started > /dev/null; then
    echo -e "${GREEN}実行中${NC}"
else
    echo -e "${RED}停止${NC}"
fi

echo ""

# 5. リソース使用状況
log_section "リソース使用状況"

# CPU使用率（BSF関連プロセス）
echo "  CPU使用率 (BSF関連プロセス):"
bsf_pids=$(pgrep -f "uvicorn.*main:app|python.*ml_pipeline_manager.py|mosquitto.*mosquitto.conf" 2>/dev/null || echo "")
if [ -n "$bsf_pids" ]; then
    for pid in $bsf_pids; do
        if ps -p "$pid" > /dev/null 2>&1; then
            cpu_usage=$(ps -p "$pid" -o %cpu= | tr -d ' ')
            command=$(ps -p "$pid" -o comm= | tr -d ' ')
            echo "    $command (PID: $pid): ${cpu_usage}%"
        fi
    done
else
    echo "    BSF関連プロセスが見つかりません"
fi

# メモリ使用量
echo "  メモリ使用量:"
if [ -n "$bsf_pids" ]; then
    total_memory=0
    for pid in $bsf_pids; do
        if ps -p "$pid" > /dev/null 2>&1; then
            memory_kb=$(ps -p "$pid" -o rss= | tr -d ' ')
            memory_mb=$((memory_kb / 1024))
            command=$(ps -p "$pid" -o comm= | tr -d ' ')
            echo "    $command (PID: $pid): ${memory_mb}MB"
            total_memory=$((total_memory + memory_mb))
        fi
    done
    echo "    合計: ${total_memory}MB"
else
    echo "    BSF関連プロセスが見つかりません"
fi

# ディスク使用量
echo "  ディスク使用量:"
if [ -d "logs" ]; then
    logs_size=$(du -sh logs 2>/dev/null | cut -f1)
    echo "    ログファイル: $logs_size"
fi

if [ -d "data" ]; then
    data_size=$(du -sh data 2>/dev/null | cut -f1)
    echo "    データファイル: $data_size"
fi

if [ -d "model_registry" ]; then
    models_size=$(du -sh model_registry 2>/dev/null | cut -f1)
    echo "    モデルレジストリ: $models_size"
fi

echo ""

# 6. ログ状況
log_section "ログ状況"

LOG_FILES=(
    "logs/application.log:アプリケーション"
    "logs/ml_pipeline.log:MLパイプライン"
    "logs/mosquitto.log:MQTTブローカー"
    "logs/system.log:システム"
)

for log_info in "${LOG_FILES[@]}"; do
    IFS=':' read -r log_file log_name <<< "$log_info"
    
    echo -n "  $log_name: "
    if [ -f "$log_file" ]; then
        file_size=$(du -h "$log_file" | cut -f1)
        line_count=$(wc -l < "$log_file" 2>/dev/null || echo "0")
        mod_time=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$log_file" 2>/dev/null || echo "unknown")
        echo "$file_size ($line_count行) - 最終更新: $mod_time"
        
        # 最新のエラーログチェック
        if grep -i "error\|exception\|failed" "$log_file" | tail -1 > /dev/null 2>&1; then
            latest_error=$(grep -i "error\|exception\|failed" "$log_file" | tail -1)
            echo "    ⚠️  最新エラー: ${latest_error:0:80}..."
        fi
    else
        echo -e "${YELLOW}ファイル無し${NC}"
    fi
done

echo ""

# 7. 設定状況
log_section "設定状況"

echo "  環境変数:"
echo "    MQTT_TLS_ENABLED: ${MQTT_TLS_ENABLED:-'設定無し'}"
echo "    MQTT_BROKER_PORT: ${MQTT_BROKER_PORT:-'設定無し'}"
echo "    POSTGRES_HOST: ${POSTGRES_HOST:-'設定無し'}"

echo "  証明書ファイル:"
CERT_FILES=("certs/ca.crt" "certs/mqtt-server.crt" "certs/mqtt-client.crt")
for cert in "${CERT_FILES[@]}"; do
    if [ -f "$cert" ]; then
        echo "    ✅ $cert"
    else
        echo "    ❌ $cert"
    fi
done

echo ""

# 8. 推奨アクション
log_section "推奨アクション"

# 問題がある場合の推奨アクション
issues_found=false

# プロセスチェック
for check in "${PROCESS_CHECKS[@]}"; do
    IFS=':' read -r name pid_file pattern <<< "$check"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ! kill -0 "$pid" 2>/dev/null; then
            if [ "$issues_found" = false ]; then
                echo "  以下の問題が検出されました:"
                issues_found=true
            fi
            echo "    ⚠️  $name が停止しています"
        fi
    fi
done

# ログサイズチェック
for log_info in "${LOG_FILES[@]}"; do
    IFS=':' read -r log_file log_name <<< "$log_info"
    if [ -f "$log_file" ]; then
        file_size_bytes=$(stat -f "%z" "$log_file" 2>/dev/null || echo "0")
        if [ "$file_size_bytes" -gt 104857600 ]; then  # 100MB
            if [ "$issues_found" = false ]; then
                echo "  以下の問題が検出されました:"
                issues_found=true
            fi
            echo "    ⚠️  $log_name のログファイルが大きくなっています (>100MB)"
        fi
    fi
done

if [ "$issues_found" = false ]; then
    echo "  🎉 現在、特別な対応が必要な問題は検出されていません"
else
    echo ""
    echo "  📋 対応方法:"
    echo "    - プロセス再起動: ./scripts/restart_production.sh"
    echo "    - ログローテーション: ./scripts/rotate_logs.sh"
    echo "    - システム再起動: ./scripts/stop_production.sh && ./scripts/start_production.sh"
fi

echo ""
log_info "✅ ステータス確認完了"