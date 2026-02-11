#!/bin/bash

# BSF-LoopTech 本番環境起動スクリプト
# MacBook本番運用用

set -e  # エラー時に停止

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# プロジェクトディレクトリの確認
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

log_header "BSF-LoopTech 本番環境起動"

# 1. 環境確認
log_info "1. 環境確認中..."

# 必要なディレクトリの作成
mkdir -p logs data backup temp

# Python仮想環境の確認
if [ ! -d "venv" ]; then
    log_error "Python仮想環境が見つかりません。setup.shを実行してください。"
    exit 1
fi

# 仮想環境を有効化
source venv/bin/activate
log_info "Python仮想環境を有効化"

# 2. データベース準備
log_info "2. データベース準備中..."

# PostgreSQLの起動確認
if ! brew services list | grep postgresql | grep started > /dev/null; then
    log_info "PostgreSQLを起動中..."
    brew services start postgresql
    sleep 3
fi

# InfluxDBの起動確認
if ! brew services list | grep influxdb | grep started > /dev/null; then
    log_info "InfluxDBを起動中..."
    brew services start influxdb
    sleep 3
fi

# データベースマイグレーション実行
log_info "データベースマイグレーション実行中..."
alembic upgrade head

# 3. MQTT ブローカー起動
log_info "3. MQTT ブローカー起動中..."

# Mosquittoの起動確認
if ! brew services list | grep mosquitto | grep started > /dev/null; then
    log_info "Mosquittoを起動中..."
    # brew servicesのエラーを無視して続行
    brew services restart mosquitto 2>/dev/null || {
        log_warn "brew servicesでのMosquitto起動に失敗しました。直接起動を試みます..."
        # 直接起動を試みる
        /opt/homebrew/opt/mosquitto/sbin/mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf -d 2>/dev/null || log_warn "Mosquittoの直接起動も失敗しました"
    }
    sleep 2
fi

# TLS対応Mosquittoの起動（設定ファイル使用）
if [ -f "certs/mosquitto.conf" ]; then
    log_info "TLS対応MQTT ブローカーを起動中..."
    # 既存のmosquittoプロセスを確認
    if pgrep -f "mosquitto.*mosquitto.conf" > /dev/null; then
        log_info "TLS MQTT ブローカーは既に実行中です"
    else
        # バックグラウンドでMQTT ブローカーを起動
        nohup mosquitto -c certs/mosquitto.conf > logs/mosquitto.log 2>&1 &
        echo $! > temp/mosquitto.pid
        sleep 2
        log_info "TLS MQTT ブローカーを起動しました (PID: $(cat temp/mosquitto.pid))"
    fi
else
    log_warn "MQTT TLS設定ファイルが見つかりません。標準のMosquittoを使用します。"
fi

# 4. ログシステム準備
log_info "4. ログシステム準備中..."

# ログディレクトリの権限設定
chmod 755 logs
touch logs/application.log logs/mqtt.log logs/ml_pipeline.log
chmod 644 logs/*.log

# 5. MLパイプラインスケジューラー起動
log_info "5. MLパイプラインスケジューラー起動中..."

# スケジューラーをバックグラウンドで起動
nohup python scripts/ml_pipeline_manager.py start-scheduler > logs/ml_pipeline.log 2>&1 &
ML_SCHEDULER_PID=$!
echo $ML_SCHEDULER_PID > temp/ml_scheduler.pid
log_info "MLパイプラインスケジューラーを起動しました (PID: $ML_SCHEDULER_PID)"

# 6. メインアプリケーション起動
log_info "6. メインアプリケーション起動中..."

# FastAPI アプリケーション起動準備
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# アプリケーション起動スクリプトの確認
if [ ! -f "src/main.py" ]; then
    log_warn "main.pyが見つかりません。FastAPIアプリケーションを手動で起動してください。"
else
    # Uvicornでアプリケーション起動
    log_info "FastAPIアプリケーションを起動中..."
    nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > logs/application.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > temp/app.pid
    log_info "FastAPIアプリケーションを起動しました (PID: $APP_PID)"
fi

# 7. 起動確認
log_info "7. システム起動確認中..."
sleep 5

# プロセス確認
PROCESSES=(
    "mosquitto:$(cat temp/mosquitto.pid 2>/dev/null || echo 'N/A')"
    "ml_scheduler:$(cat temp/ml_scheduler.pid 2>/dev/null || echo 'N/A')"
    "app:$(cat temp/app.pid 2>/dev/null || echo 'N/A')"
)

log_info "実行中のプロセス:"
for process in "${PROCESSES[@]}"; do
    name="${process%%:*}"
    pid="${process##*:}"
    if [ "$pid" != "N/A" ] && kill -0 "$pid" 2>/dev/null; then
        log_info "  ✅ $name (PID: $pid)"
    else
        log_warn "  ❌ $name (停止中)"
    fi
done

# 8. 接続テスト
log_info "8. システム接続テスト中..."

# HTTP API テスト
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log_info "  ✅ HTTP API接続成功"
else
    log_warn "  ⚠️  HTTP API接続確認できません（起動中の可能性があります）"
fi

# MQTT接続テスト
if mosquitto_pub -h localhost -p 8883 --cafile certs/ca.crt -t "test/connection" -m "test" > /dev/null 2>&1; then
    log_info "  ✅ MQTT TLS接続成功"
else
    log_warn "  ⚠️  MQTT TLS接続確認できません"
fi

# 9. システム情報表示
log_header "システム起動完了"

echo ""
log_info "🎉 BSF-LoopTech本番環境の起動が完了しました"
echo ""
log_info "📊 アクセス情報:"
log_info "  - Web API: http://localhost:8000"
log_info "  - API Documentation: http://localhost:8000/docs"
log_info "  - MQTT Broker: localhost:8883 (TLS)"
log_info "  - MQTT Standard: localhost:1883"
echo ""
log_info "📁 重要なファイル:"
log_info "  - アプリケーションログ: logs/application.log"
log_info "  - MLパイプラインログ: logs/ml_pipeline.log"
log_info "  - MQTTブローカーログ: logs/mosquitto.log"
log_info "  - プロセスID: temp/*.pid"
echo ""
log_info "🔧 管理コマンド:"
log_info "  - 停止: ./scripts/stop_production.sh"
log_info "  - 再起動: ./scripts/restart_production.sh"
log_info "  - ステータス確認: ./scripts/status_production.sh"
log_info "  - MLパイプライン管理: python scripts/ml_pipeline_manager.py --help"
echo ""
log_info "⚠️  本番運用注意事項:"
log_info "  - ログファイルは定期的にローテーションしてください"
log_info "  - データベースのバックアップを定期実行してください"
log_info "  - システムリソースを監視してください"
echo ""

# システム起動完了マーカーファイル作成
echo "$(date)" > temp/production_started.marker

log_info "✅ 本番環境起動プロセス完了"