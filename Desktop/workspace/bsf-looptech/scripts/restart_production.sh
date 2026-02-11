#!/bin/bash

# BSF-LoopTech 本番環境再起動スクリプト
# 安全な再起動プロセス

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

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
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}${BOLD}================================${NC}"
}

# 確認関数
confirm() {
    local prompt="$1"
    local response
    
    while true; do
        echo -ne "${CYAN}$prompt (y/n): ${NC}"
        read response
        case "$response" in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "y または n を入力してください。";;
        esac
    done
}

# 安全な再起動実行
safe_restart() {
    log_header "BSF-LoopTech システム再起動"
    
    # 事前確認
    echo ""
    log_warn "この操作により、現在実行中のシステムが一時的に停止します。"
    echo ""
    
    if ! confirm "システムの再起動を実行しますか？"; then
        log_info "再起動をキャンセルしました"
        exit 0
    fi
    
    # 1. 現在の状況確認
    log_info "1. 再起動前のシステム状況確認..."
    
    local running_processes=()
    
    # プロセス確認
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        running_processes+=("FastAPI")
        log_info "  ✓ FastAPI アプリケーション実行中"
    fi
    
    if pgrep -f "python.*ml_pipeline_manager.py" > /dev/null; then
        running_processes+=("MLPipeline")
        log_info "  ✓ MLパイプライン実行中"
    fi
    
    if pgrep -f "mosquitto.*mosquitto.conf" > /dev/null; then
        running_processes+=("MQTT")
        log_info "  ✓ MQTT ブローカー実行中"
    fi
    
    if [ ${#running_processes[@]} -eq 0 ]; then
        log_warn "実行中のプロセスが見つかりません。起動のみ実行します。"
        if confirm "システムを起動しますか？"; then
            start_system
        fi
        return 0
    fi
    
    log_info "再起動対象: ${running_processes[*]}"
    
    # 2. システム停止
    log_info "2. システム停止中..."
    
    if [ -f "scripts/stop_production.sh" ]; then
        ./scripts/stop_production.sh
    else
        log_error "停止スクリプトが見つかりません"
        return 1
    fi
    
    # 3. 停止確認
    log_info "3. 停止確認中..."
    sleep 3
    
    local stop_success=true
    
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        log_warn "  ⚠️  FastAPIプロセスがまだ実行中です"
        stop_success=false
    else
        log_info "  ✓ FastAPIプロセス停止完了"
    fi
    
    if pgrep -f "python.*ml_pipeline_manager.py" > /dev/null; then
        log_warn "  ⚠️  MLパイプラインプロセスがまだ実行中です"
        stop_success=false
    else
        log_info "  ✓ MLパイプラインプロセス停止完了"
    fi
    
    if ! $stop_success; then
        log_warn "一部プロセスの停止が確認できませんでした"
        if confirm "強制的に再起動を続行しますか？"; then
            log_info "強制停止を実行します..."
            pkill -f "uvicorn.*main:app" 2>/dev/null || true
            pkill -f "python.*ml_pipeline_manager.py" 2>/dev/null || true
            sleep 2
        else
            log_error "再起動を中止しました"
            return 1
        fi
    fi
    
    # 4. 一時停止
    log_info "4. システム初期化待機中..."
    sleep 5
    
    # 5. システム起動
    log_info "5. システム起動中..."
    
    if [ -f "scripts/start_production.sh" ]; then
        ./scripts/start_production.sh
    else
        log_error "起動スクリプトが見つかりません"
        return 1
    fi
    
    # 6. 起動確認
    log_info "6. 再起動完了確認中..."
    sleep 5
    
    local restart_success=true
    
    # プロセス確認
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        log_info "  ✓ FastAPIアプリケーション起動完了"
    else
        log_warn "  ⚠️  FastAPIアプリケーションの起動を確認できません"
        restart_success=false
    fi
    
    # HTTP API確認
    local retry_count=0
    while [ $retry_count -lt 10 ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_info "  ✓ HTTP API接続確認完了"
            break
        fi
        retry_count=$((retry_count + 1))
        sleep 2
    done
    
    if [ $retry_count -eq 10 ]; then
        log_warn "  ⚠️  HTTP API接続確認がタイムアウトしました"
        restart_success=false
    fi
    
    # 7. 結果表示
    log_header "再起動結果"
    
    if $restart_success; then
        echo ""
        log_info "🎉 システムの再起動が正常に完了しました"
        echo ""
        log_info "📊 アクセス情報:"
        log_info "  - Web API: http://localhost:8000"
        log_info "  - API Documentation: http://localhost:8000/docs"
        log_info "  - システム状態: ./scripts/status_production.sh"
        echo ""
    else
        echo ""
        log_warn "⚠️  再起動は完了しましたが、一部のサービスで問題が発生している可能性があります"
        echo ""
        log_info "📋 トラブルシューティング:"
        log_info "  - 詳細状態確認: ./scripts/status_production.sh"
        log_info "  - ログ確認: ./scripts/bsf_manager.sh logs"
        log_info "  - 手動起動: ./scripts/start_production.sh"
        echo ""
    fi
    
    log_info "再起動ログ: $(date) - Restart completed" >> logs/system.log
}

# システム起動のみ
start_system() {
    log_header "システム起動"
    
    if [ -f "scripts/start_production.sh" ]; then
        ./scripts/start_production.sh
    else
        log_error "起動スクリプトが見つかりません"
        return 1
    fi
}

# メイン実行
main() {
    case "${1:-restart}" in
        "start")
            start_system
            ;;
        "restart"|*)
            safe_restart
            ;;
    esac
}

# 実行
main "$@"