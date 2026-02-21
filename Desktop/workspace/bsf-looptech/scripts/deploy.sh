#!/bin/bash

# BSF-LoopTech 本番環境デプロイメントスクリプト
# 開発環境から本番環境（Docker）への自動移行

set -e

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

# 前提条件チェック
check_prerequisites() {
    log_header "前提条件チェック"
    
    # Docker確認
    if ! command -v docker &> /dev/null; then
        log_error "Docker がインストールされていません"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose がインストールされていません"
        exit 1
    fi
    
    # Docker デーモン確認
    if ! docker ps &> /dev/null; then
        log_error "Docker デーモンが起動していません"
        log_info "Docker Desktop を起動してください"
        exit 1
    fi
    
    log_info "Docker: $(docker --version)"
    log_info "Docker Compose: $(docker-compose --version)"
}

# 開発環境停止
stop_development() {
    log_header "開発環境停止"
    
    log_info "開発環境のプロセスを停止しています..."
    
    # uvicorn プロセス停止
    if pgrep -f "uvicorn" > /dev/null; then
        log_info "バックエンドAPI (uvicorn) を停止中..."
        pkill -f "uvicorn" || true
    fi
    
    # npm プロセス停止
    if pgrep -f "npm start" > /dev/null; then
        log_info "フロントエンド (npm start) を停止中..."
        pkill -f "npm start" || true
    fi
    
    log_info "開発環境の停止完了"
}

# 環境準備
prepare_environment() {
    log_header "環境準備"
    
    # データディレクトリ作成
    log_info "データディレクトリを作成中..."
    mkdir -p data/postgres backups logs
    chmod 755 data backups logs
    
    # 環境変数ファイル準備
    if [ -f ".env.production" ]; then
        log_info "本番環境設定を適用中..."
        cp .env.production .env
    else
        log_warn ".env.production が見つかりません。現在の .env を使用します"
    fi
    
    log_info "環境準備完了"
}

# Docker イメージビルド
build_images() {
    log_header "Docker イメージビルド"
    
    log_info "Docker イメージをビルド中..."
    docker-compose build --no-cache
    
    log_info "イメージビルド完了"
}

# サービス起動
start_services() {
    log_header "本番サービス起動"
    
    # 既存コンテナ停止・削除
    log_info "既存のコンテナを停止・削除中..."
    docker-compose down --remove-orphans
    
    # データベースサービス起動
    log_info "データベースサービス起動中..."
    docker-compose up -d postgres
    
    # ヘルスチェック待機
    log_info "データベースの起動を待機中..."
    sleep 30
    
    # アプリケーションサービス起動
    log_info "アプリケーションサービス起動中..."
    docker-compose up -d backend frontend
    sleep 20
    
    log_info "全サービス起動完了"
}

# ヘルスチェック
health_check() {
    log_header "ヘルスチェック"
    
    local max_attempts=30
    local attempt=1
    
    # バックエンド API チェック
    log_info "バックエンド API の確認中..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
            log_info "✅ バックエンド API: 正常"
            break
        fi
        log_warn "バックエンド API 応答待機中... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "❌ バックエンド API の起動に失敗しました"
        return 1
    fi
    
    # フロントエンド チェック
    log_info "フロントエンドの確認中..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:3000 > /dev/null 2>&1; then
            log_info "✅ フロントエンド: 正常"
            break
        fi
        log_warn "フロントエンド 応答待機中... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "❌ フロントエンドの起動に失敗しました"
        return 1
    fi
    
    # データベース接続チェック
    log_info "データベース接続確認中..."
    if docker-compose exec -T postgres pg_isready -U bsf_user > /dev/null 2>&1; then
        log_info "✅ PostgreSQL: 正常"
    else
        log_error "❌ PostgreSQL 接続エラー"
        return 1
    fi
    
    return 0
}

# データベースマイグレーション
run_migrations() {
    log_header "データベースマイグレーション"
    
    log_info "Alembic マイグレーション実行中..."
    if docker-compose exec -T backend alembic upgrade head; then
        log_info "✅ マイグレーション完了"
    else
        log_error "❌ マイグレーション失敗"
        return 1
    fi
}

# デプロイメント状況表示
show_status() {
    log_header "デプロイメント完了"
    
    echo ""
    log_info "🎉 BSF-LoopTech 本番環境デプロイメント完了"
    echo ""
    echo -e "${GREEN}アクセス URL:${NC}"
    echo -e "  📱 フロントエンド: ${BLUE}http://localhost:3000${NC}"
    echo -e "  🔧 API管理画面:   ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${GREEN}管理コマンド:${NC}"
    echo -e "  📊 ログ監視:      ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  📈 コンテナ状態:  ${YELLOW}docker-compose ps${NC}"
    echo -e "  🛑 停止:          ${YELLOW}docker-compose down${NC}"
    echo -e "  🔄 再起動:        ${YELLOW}docker-compose restart${NC}"
    echo ""
}

# エラーハンドリング
cleanup_on_error() {
    log_error "デプロイメント中にエラーが発生しました"
    log_info "ログを確認してください: docker-compose logs"
    exit 1
}

# メイン実行
main() {
    log_header "BSF-LoopTech 本番環境デプロイメント開始"
    
    # エラー時のクリーンアップ設定
    trap cleanup_on_error ERR
    
    # 実行確認
    echo -e "${YELLOW}本番環境デプロイメントを開始します。${NC}"
    echo -e "${YELLOW}開発環境のプロセスは停止されます。${NC}"
    echo ""
    read -p "続行しますか? [y/N]: " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "デプロイメントがキャンセルされました"
        exit 0
    fi
    
    # デプロイメント実行
    check_prerequisites
    stop_development
    prepare_environment
    build_images
    start_services
    
    # ヘルスチェック実行
    if health_check; then
        run_migrations
        show_status
    else
        log_error "ヘルスチェックに失敗しました"
        log_info "ログを確認してください: docker-compose logs"
        exit 1
    fi
}

# スクリプト実行
main "$@"