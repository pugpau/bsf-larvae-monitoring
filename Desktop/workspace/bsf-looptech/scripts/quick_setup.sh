#!/bin/bash

# BSF-LoopTech クイックセットアップ
# 簡単インストール用のラッパースクリプト

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
    echo ""
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo ""
}

# ウェルカムメッセージ
show_welcome() {
    clear
    echo -e "${BLUE}${BOLD}"
    cat << 'EOF'
    ____  _____ ______      __                 ______          __  
   / __ )/ ___// ____/     / /   ____  ____  / ____/___  ____/ /_ 
  / __  |\__ \/ /_  ______/ /   / __ \/ __ \/ /_  / __ \/ __  / /_
 / /_/ /___/ / __/ /_____/ /___/ /_/ / /_/ / __/ / /_/ / /_/ / __/
/_____//____/_/         /_____/\____/\____/_/    \____/\__,_/_/   

               Black Soldier Fly IoT 監視システム
                   クイックセットアップ v1.0
EOF
    echo -e "${NC}"
    
    echo -e "${CYAN}このセットアップウィザードは、BSF-LoopTech システムを素早く起動するための${NC}"
    echo -e "${CYAN}簡単なインストール・設定を提供します。${NC}"
    echo ""
}

# 環境チェック
check_environment() {
    log_header "環境チェック"
    
    local checks_passed=true
    
    # macOS確認
    if [[ "$(uname -s)" == "Darwin" ]]; then
        log_info "✅ macOS環境を確認"
    else
        log_error "❌ このスクリプトはmacOS専用です"
        checks_passed=false
    fi
    
    # Homebrewチェック
    if command -v brew > /dev/null; then
        log_info "✅ Homebrew インストール済み"
    else
        log_warn "⚠️  Homebrew未インストール（インストールスクリプトで対応）"
    fi
    
    # Python3チェック
    if command -v python3 > /dev/null; then
        log_info "✅ Python3 利用可能"
    else
        log_error "❌ Python3が必要です"
        checks_passed=false
    fi
    
    # ディスク容量チェック
    local available_gb=$(df -h . | tail -1 | awk '{print $4}' | sed 's/G.*//')
    if [ "$available_gb" -gt 5 ] 2>/dev/null; then
        log_info "✅ ディスク容量十分 (${available_gb}GB利用可能)"
    else
        log_warn "⚠️  ディスク容量不足の可能性 (${available_gb}GB利用可能)"
    fi
    
    return $checks_passed
}

# セットアップタイプ選択
select_setup_type() {
    log_header "セットアップタイプの選択"
    
    echo -e "${MAGENTA}どのようなセットアップを実行しますか？${NC}"
    echo ""
    echo -e "${YELLOW}1)${NC} 🚀 推奨セットアップ - 一般的な設定でフルインストール"
    echo -e "${YELLOW}2)${NC} ⚡ 軽量セットアップ - 最小限のリソースで動作"
    echo -e "${YELLOW}3)${NC} 🧪 開発者セットアップ - 開発・テスト用設定"
    echo -e "${YELLOW}4)${NC} 🔧 カスタムセットアップ - 完全なインストーラーを実行"
    echo -e "${YELLOW}5)${NC} 📊 ステータス確認のみ - インストール状況の確認"
    echo ""
    
    while true; do
        echo -ne "${CYAN}選択してください (1-5): ${NC}"
        read choice
        
        case $choice in
            1) export SETUP_TYPE="recommended"; break;;
            2) export SETUP_TYPE="minimal"; break;;
            3) export SETUP_TYPE="developer"; break;;
            4) export SETUP_TYPE="custom"; break;;
            5) export SETUP_TYPE="status"; break;;
            *) log_error "無効な選択です。1-5の数字を入力してください。";;
        esac
    done
    
    log_info "選択されたセットアップ: $SETUP_TYPE"
}

# ステータス確認のみ
status_only() {
    log_header "システム状態確認"
    
    if [ -f "scripts/status_production.sh" ]; then
        ./scripts/status_production.sh
    else
        log_error "ステータススクリプトが見つかりません"
        return 1
    fi
    
    echo ""
    log_info "管理コマンド:"
    echo "  統合管理: ./scripts/bsf_manager.sh"
    echo "  詳細インストール: ./install.sh"
}

# 推奨セットアップ
recommended_setup() {
    log_header "推奨セットアップ実行"
    
    log_info "自動的に最適な設定でインストールを実行します..."
    
    # 環境変数でデフォルト設定
    export INSTALL_TYPE="full"
    export DATABASE_TYPE="postgresql_influxdb"
    export MQTT_SECURITY="full_tls"
    export ML_FEATURES="full_pipeline"
    export MONITORING_LEVEL="full"
    export BACKUP_LOCATION="local"
    export AUTO_START="system_boot"
    export HEADLESS_INSTALL="true"
    
    ./install.sh
}

# 軽量セットアップ
minimal_setup() {
    log_header "軽量セットアップ実行"
    
    log_info "最小限のリソースで動作する設定でインストールします..."
    
    export INSTALL_TYPE="minimal"
    export DATABASE_TYPE="sqlite_only"
    export MQTT_SECURITY="auth_only"
    export ML_FEATURES="disabled"
    export MONITORING_LEVEL="basic"
    export BACKUP_LOCATION="local"
    export AUTO_START="manual"
    export HEADLESS_INSTALL="true"
    
    ./install.sh
}

# 開発者セットアップ
developer_setup() {
    log_header "開発者セットアップ実行"
    
    log_info "開発・テスト用設定でインストールします..."
    
    export INSTALL_TYPE="developer"
    export DATABASE_TYPE="sqlite_influxdb"
    export MQTT_SECURITY="none"
    export ML_FEATURES="basic_ml"
    export MONITORING_LEVEL="basic"
    export BACKUP_LOCATION="local"
    export AUTO_START="manual"
    export HEADLESS_INSTALL="true"
    
    ./install.sh
}

# カスタムセットアップ
custom_setup() {
    log_header "カスタムセットアップ実行"
    
    log_info "完全なインストーラーを起動します..."
    ./install.sh
}

# セットアップ完了後の処理
post_setup() {
    log_header "セットアップ完了"
    
    echo -e "${GREEN}${BOLD}🎉 BSF-LoopTech のセットアップが完了しました！${NC}"
    echo ""
    
    echo -e "${BOLD}📋 次のステップ:${NC}"
    echo -e "  1. システム起動: ${CYAN}./scripts/bsf_manager.sh start${NC}"
    echo -e "  2. 状態確認: ${CYAN}./scripts/bsf_manager.sh status${NC}"
    echo -e "  3. Web UI: ${CYAN}http://localhost:8000/docs${NC}"
    echo ""
    
    echo -e "${BOLD}🔧 管理コマンド:${NC}"
    echo -e "  統合管理ツール: ${CYAN}./scripts/bsf_manager.sh${NC}"
    echo -e "  詳細ステータス: ${CYAN}./scripts/status_production.sh${NC}"
    echo ""
    
    # 自動起動確認
    if [[ "$AUTO_START" != "manual" ]]; then
        echo -e "${YELLOW}💡 システムは自動起動に設定されています${NC}"
        if confirm "今すぐシステムを起動しますか？"; then
            ./scripts/bsf_manager.sh start
        fi
    else
        if confirm "今すぐシステムを起動しますか？"; then
            ./scripts/bsf_manager.sh start
        fi
    fi
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

# メイン実行
main() {
    show_welcome
    
    if ! check_environment; then
        log_error "環境チェックに失敗しました。要件を満たしてから再実行してください。"
        exit 1
    fi
    
    select_setup_type
    
    case $SETUP_TYPE in
        "recommended")
            recommended_setup
            post_setup
            ;;
        "minimal")
            minimal_setup
            post_setup
            ;;
        "developer")
            developer_setup
            post_setup
            ;;
        "custom")
            custom_setup
            ;;
        "status")
            status_only
            ;;
    esac
}

# 実行
main "$@"