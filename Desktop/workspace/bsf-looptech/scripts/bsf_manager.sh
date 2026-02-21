#!/bin/bash

# BSF-LoopTech 統合管理スクリプト
# システム運用の簡素化とワンストップ管理

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# プロジェクトディレクトリの確認
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') - $1"
}

log_header() {
    echo ""
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo ""
}

# システム状態確認
check_system_status() {
    log_header "システム状態確認"
    
    local status_ok=true
    
    # プロセス確認
    echo -e "${CYAN}🔍 プロセス状態:${NC}"
    
    # FastAPI
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        echo -e "  ✅ FastAPI アプリケーション: ${GREEN}実行中${NC}"
    else
        echo -e "  ❌ FastAPI アプリケーション: ${RED}停止中${NC}"
        status_ok=false
    fi
    
    # ML Pipeline
    if pgrep -f "python.*ml_pipeline_manager.py" > /dev/null; then
        echo -e "  ✅ MLパイプライン: ${GREEN}実行中${NC}"
    else
        echo -e "  ⚠️  MLパイプライン: ${YELLOW}停止中${NC}"
    fi
    
    # MQTT Broker
    if pgrep -f "mosquitto" > /dev/null; then
        echo -e "  ✅ MQTT ブローカー: ${GREEN}実行中${NC}"
    else
        echo -e "  ❌ MQTT ブローカー: ${RED}停止中${NC}"
        status_ok=false
    fi
    
    echo ""
    echo -e "${CYAN}💾 データベース状態:${NC}"
    
    # PostgreSQL
    if brew services list | grep postgresql | grep started > /dev/null; then
        echo -e "  ✅ PostgreSQL: ${GREEN}実行中${NC}"
    else
        echo -e "  ❌ PostgreSQL: ${RED}停止中${NC}"
        status_ok=false
    fi
    
    # InfluxDB
    if brew services list | grep influxdb | grep started > /dev/null; then
        echo -e "  ✅ InfluxDB: ${GREEN}実行中${NC}"
    else
        echo -e "  ❌ InfluxDB: ${RED}停止中${NC}"
        status_ok=false
    fi
    
    echo ""
    echo -e "${CYAN}🌐 接続テスト:${NC}"
    
    # HTTP API
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  ✅ HTTP API: ${GREEN}接続可能${NC}"
    else
        echo -e "  ❌ HTTP API: ${RED}接続不可${NC}"
        status_ok=false
    fi
    
    # MQTT TLS
    if [ -f "certs/ca.crt" ] && mosquitto_pub -h localhost -p 8883 --cafile certs/ca.crt -t "test/health" -m "check" > /dev/null 2>&1; then
        echo -e "  ✅ MQTT TLS: ${GREEN}接続可能${NC}"
    else
        echo -e "  ⚠️  MQTT TLS: ${YELLOW}接続不可${NC}"
    fi
    
    echo ""
    if $status_ok; then
        echo -e "${GREEN}${BOLD}✅ システムは正常に動作しています${NC}"
        return 0
    else
        echo -e "${RED}${BOLD}❌ システムに問題があります${NC}"
        return 1
    fi
}

# システム起動
start_system() {
    log_header "システム起動"
    
    if [ -f "scripts/start_production.sh" ]; then
        log_info "本番環境起動スクリプトを実行中..."
        ./scripts/start_production.sh
    else
        log_error "起動スクリプトが見つかりません"
        return 1
    fi
}

# システム停止
stop_system() {
    log_header "システム停止"
    
    if [ -f "scripts/stop_production.sh" ]; then
        log_info "本番環境停止スクリプトを実行中..."
        ./scripts/stop_production.sh
    else
        log_error "停止スクリプトが見つかりません"
        return 1
    fi
}

# システム再起動
restart_system() {
    log_header "システム再起動"
    
    log_info "システムを停止中..."
    stop_system
    
    sleep 3
    
    log_info "システムを起動中..."
    start_system
}

# システムインストール
install_system() {
    log_header "システムインストール"
    
    if [ -f "install.sh" ]; then
        log_info "インストーラーを実行中..."
        ./install.sh
    else
        log_error "インストールスクリプトが見つかりません"
        return 1
    fi
}

# システムアンインストール
uninstall_system() {
    log_header "システムアンインストール"
    
    if [ -f "uninstall.sh" ]; then
        log_info "アンインストーラーを実行中..."
        ./uninstall.sh
    else
        log_error "アンインストールスクリプトが見つかりません"
        return 1
    fi
}

# ログ確認
view_logs() {
    local log_type="${1:-all}"
    
    log_header "ログ確認"
    
    case $log_type in
        "app"|"application")
            if [ -f "logs/application.log" ]; then
                log_info "アプリケーションログ (最新50行):"
                tail -n 50 logs/application.log
            else
                log_warn "アプリケーションログが見つかりません"
            fi
            ;;
        "mqtt")
            if [ -f "logs/mosquitto.log" ]; then
                log_info "MQTTログ (最新50行):"
                tail -n 50 logs/mosquitto.log
            else
                log_warn "MQTTログが見つかりません"
            fi
            ;;
        "ml")
            if [ -f "logs/ml_pipeline.log" ]; then
                log_info "MLパイプラインログ (最新50行):"
                tail -n 50 logs/ml_pipeline.log
            else
                log_warn "MLパイプラインログが見つかりません"
            fi
            ;;
        "all"|*)
            log_info "利用可能なログファイル:"
            if [ -d "logs" ]; then
                ls -la logs/*.log 2>/dev/null || log_warn "ログファイルが見つかりません"
            else
                log_warn "logsディレクトリが見つかりません"
            fi
            ;;
    esac
}

# バックアップ実行
backup_system() {
    log_header "システムバックアップ"
    
    if [ -f "scripts/backup_system.sh" ]; then
        log_info "バックアップスクリプトを実行中..."
        ./scripts/backup_system.sh full
    else
        log_error "バックアップスクリプトが見つかりません"
        return 1
    fi
}

# ヘルプメッセージ
show_help() {
    cat << EOF

${BLUE}${BOLD}BSF-LoopTech 統合管理スクリプト${NC}

${YELLOW}使用方法:${NC}
  $0 <command> [options]

${YELLOW}基本コマンド:${NC}
  ${GREEN}status${NC}     - システム状態確認
  ${GREEN}start${NC}      - システム起動
  ${GREEN}stop${NC}       - システム停止
  ${GREEN}restart${NC}    - システム再起動

${YELLOW}管理コマンド:${NC}
  ${GREEN}install${NC}    - システムインストール
  ${GREEN}uninstall${NC}  - システムアンインストール
  ${GREEN}backup${NC}     - システムバックアップ

${YELLOW}監視コマンド:${NC}
  ${GREEN}logs${NC}       - 全ログファイル一覧
  ${GREEN}logs app${NC}   - アプリケーションログ表示
  ${GREEN}logs mqtt${NC}  - MQTTログ表示
  ${GREEN}logs ml${NC}    - MLパイプラインログ表示

${YELLOW}例:${NC}
  $0 status          # システム状態確認
  $0 start           # システム起動
  $0 logs app        # アプリケーションログ確認
  $0 backup          # バックアップ実行

${YELLOW}個別スクリプト:${NC}
  インストール:      ./install.sh
  アンインストール:  ./uninstall.sh
  起動:             ./scripts/start_production.sh
  停止:             ./scripts/stop_production.sh

EOF
}

# メイン処理
main() {
    local command="${1:-help}"
    local subcommand="${2:-}"
    
    case $command in
        "status"|"s")
            check_system_status
            ;;
        "start")
            start_system
            ;;
        "stop")
            stop_system
            ;;
        "restart"|"r")
            restart_system
            ;;
        "install"|"i")
            install_system
            ;;
        "uninstall"|"u")
            uninstall_system
            ;;
        "logs"|"l")
            view_logs "$subcommand"
            ;;
        "backup"|"b")
            backup_system
            ;;
        "help"|"h"|*)
            show_help
            ;;
    esac
}

# ロゴ表示
echo -e "${BLUE}${BOLD}"
cat << 'EOF'
    ____  _____ ______      __                 ______          __  
   / __ )/ ___// ____/     / /   ____  ____  / ____/___  ____/ /_ 
  / __  |\__ \/ /_  ______/ /   / __ \/ __ \/ /_  / __ \/ __  / /_
 / /_/ /___/ / __/ /_____/ /___/ /_/ / /_/ / __/ / /_/ / /_/ / __/
/_____//____/_/         /_____/\____/\____/_/    \____/\__,_/_/   

統合管理システム v1.0
EOF
echo -e "${NC}"

# メイン実行
main "$@"