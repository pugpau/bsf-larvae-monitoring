#!/bin/bash

# BSF-LoopTech バックアップシステム
# 本番環境用データ保護

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# バックアップ設定
BACKUP_BASE_DIR="$PROJECT_DIR/backup"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"
RETENTION_DAYS=30  # バックアップ保持期間

# 外部バックアップディレクトリ（例：外付けHDD、クラウドストレージ）
EXTERNAL_BACKUP_DIR="$HOME/BSF_Backups"

# バックアップ対象
BACKUP_TARGETS=(
    "logs:ログファイル"
    "data:データファイル"
    "model_registry:MLモデル"
    "certs:証明書"
    "config:設定ファイル"
    ".env:環境変数"
    "alembic:DBマイグレーション"
)

# データベースバックアップ設定
DB_BACKUP_NAME="postgresql_backup_$TIMESTAMP.sql"
INFLUXDB_BACKUP_NAME="influxdb_backup_$TIMESTAMP"

# バックアップ実行
perform_backup() {
    local backup_type="$1"
    
    case "$backup_type" in
        "full")
            log_header "完全バックアップ実行"
            backup_files
            backup_databases
            backup_system_config
            ;;
        "incremental")
            log_header "増分バックアップ実行"
            backup_files "incremental"
            backup_databases
            ;;
        "database")
            log_header "データベースバックアップ実行"
            backup_databases
            ;;
        "files")
            log_header "ファイルバックアップ実行"
            backup_files
            ;;
        *)
            log_error "不正なバックアップタイプ: $backup_type"
            echo "使用方法: $0 {full|incremental|database|files}"
            exit 1
            ;;
    esac
}

# ファイルバックアップ
backup_files() {
    local mode="${1:-full}"
    
    log_info "ファイルバックアップ開始 (モード: $mode)..."
    
    # バックアップディレクトリ作成
    mkdir -p "$BACKUP_DIR"
    
    # バックアップ情報ファイル作成
    cat > "$BACKUP_DIR/backup_info.txt" << EOF
BSF-LoopTech バックアップ情報
=============================
バックアップ日時: $(date)
バックアップタイプ: $mode
バックアップディレクトリ: $BACKUP_DIR
プロジェクトディレクトリ: $PROJECT_DIR
システム: $(uname -a)
EOF
    
    # 各ターゲットのバックアップ
    for target_info in "${BACKUP_TARGETS[@]}"; do
        IFS=':' read -r target_path target_name <<< "$target_info"
        
        if [ -e "$target_path" ]; then
            log_info "  バックアップ中: $target_name ($target_path)"
            
            if [ "$mode" = "incremental" ] && [ -d "$target_path" ]; then
                # 増分バックアップ（過去24時間の変更分のみ）
                find "$target_path" -mtime -1 -type f -exec cp --parents {} "$BACKUP_DIR/" \; 2>/dev/null || {
                    # macOSの場合、cpコマンドが--parentsオプションをサポートしていないため
                    rsync -av --include='*/' --include-from=<(find "$target_path" -mtime -1 -type f -printf '%P\n' 2>/dev/null || find "$target_path" -mtime -1 -type f | sed "s|^$target_path/||") --exclude='*' "$target_path/" "$BACKUP_DIR/$target_path/"
                }
            else
                # 完全バックアップ
                if [ -d "$target_path" ]; then
                    cp -R "$target_path" "$BACKUP_DIR/"
                else
                    cp "$target_path" "$BACKUP_DIR/"
                fi
            fi
            
            log_info "    ✅ 完了: $target_name"
        else
            log_warn "    ⚠️  見つかりません: $target_path"
        fi
    done
}

# データベースバックアップ
backup_databases() {
    log_info "データベースバックアップ開始..."
    
    mkdir -p "$BACKUP_DIR/databases"
    
    # PostgreSQLバックアップ
    log_info "  PostgreSQLバックアップ中..."
    if command -v pg_dump > /dev/null; then
        # 設定から接続情報を取得
        source .env 2>/dev/null || true
        
        POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
        POSTGRES_PORT="${POSTGRES_PORT:-5432}"
        POSTGRES_DB="${POSTGRES_DB:-bsf_system}"
        POSTGRES_USER="${POSTGRES_USER:-bsf_user}"
        
        # パスワードなしでのバックアップ試行
        if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_DIR/databases/$DB_BACKUP_NAME" 2>/dev/null; then
            log_info "    ✅ PostgreSQLバックアップ完了"
        else
            log_warn "    ⚠️  PostgreSQLバックアップ失敗（認証エラーまたは接続エラー）"
            # スキーマのみバックアップ
            pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only > "$BACKUP_DIR/databases/schema_$DB_BACKUP_NAME" 2>/dev/null || true
        fi
    else
        log_warn "    ⚠️  pg_dumpが見つかりません"
    fi
    
    # InfluxDBバックアップ
    log_info "  InfluxDBバックアップ中..."
    if command -v influx > /dev/null; then
        source .env 2>/dev/null || true
        
        INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
        INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-}"
        INFLUXDB_ORG="${INFLUXDB_ORG:-default_org}"
        INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-bsf_data}"
        
        # InfluxDBデータのエクスポート
        if [ -n "$INFLUXDB_TOKEN" ]; then
            mkdir -p "$BACKUP_DIR/databases/$INFLUXDB_BACKUP_NAME"
            
            # バケット情報を保存
            echo "InfluxDB Backup Information" > "$BACKUP_DIR/databases/$INFLUXDB_BACKUP_NAME/info.txt"
            echo "Organization: $INFLUXDB_ORG" >> "$BACKUP_DIR/databases/$INFLUXDB_BACKUP_NAME/info.txt"
            echo "Bucket: $INFLUXDB_BUCKET" >> "$BACKUP_DIR/databases/$INFLUXDB_BACKUP_NAME/info.txt"
            echo "Backup Time: $(date)" >> "$BACKUP_DIR/databases/$INFLUXDB_BACKUP_NAME/info.txt"
            
            # 簡易的なデータエクスポート（ここでは設定情報のみ）
            log_info "    ✅ InfluxDB設定情報バックアップ完了"
        else
            log_warn "    ⚠️  InfluxDBトークンが設定されていません"
        fi
    else
        log_warn "    ⚠️  influxコマンドが見つかりません"
    fi
}

# システム設定バックアップ
backup_system_config() {
    log_info "システム設定バックアップ中..."
    
    mkdir -p "$BACKUP_DIR/system"
    
    # システム情報
    cat > "$BACKUP_DIR/system/system_info.txt" << EOF
BSF-LoopTech システム情報
========================
日時: $(date)
ホスト名: $(hostname)
OS: $(uname -a)
Python バージョン: $(python3 --version 2>/dev/null || echo "不明")
Git ブランチ: $(git branch --show-current 2>/dev/null || echo "不明")
Git コミット: $(git rev-parse HEAD 2>/dev/null || echo "不明")

インストール済みHomebrew パッケージ:
$(brew list 2>/dev/null || echo "Homebrewが利用できません")

Python パッケージ:
$(pip list 2>/dev/null || echo "pipが利用できません")
EOF
    
    # 環境変数（機密情報を除く）
    env | grep -E '^(POSTGRES_|INFLUXDB_|MQTT_)' | sed 's/=.*TOKEN.*=/=***HIDDEN***/g' | sed 's/=.*PASSWORD.*=/=***HIDDEN***/g' > "$BACKUP_DIR/system/environment.txt" 2>/dev/null || true
    
    # crontab設定
    crontab -l > "$BACKUP_DIR/system/crontab.txt" 2>/dev/null || echo "crontabが設定されていません" > "$BACKUP_DIR/system/crontab.txt"
    
    # LaunchAgents設定
    if [ -f "$HOME/Library/LaunchAgents/com.bsf-looptech.production.plist" ]; then
        cp "$HOME/Library/LaunchAgents/com.bsf-looptech.production.plist" "$BACKUP_DIR/system/"
    fi
    
    log_info "  ✅ システム設定バックアップ完了"
}

# バックアップ圧縮
compress_backup() {
    log_info "バックアップ圧縮中..."
    
    cd "$BACKUP_BASE_DIR"
    tar -czf "${TIMESTAMP}_backup.tar.gz" "$TIMESTAMP"
    
    if [ $? -eq 0 ]; then
        # 圧縮成功時は元のディレクトリを削除
        rm -rf "$TIMESTAMP"
        log_info "  ✅ バックアップ圧縮完了: ${TIMESTAMP}_backup.tar.gz"
        
        # ファイルサイズ表示
        backup_size=$(du -h "${TIMESTAMP}_backup.tar.gz" | cut -f1)
        log_info "  📊 バックアップサイズ: $backup_size"
        
        echo "$TIMESTAMP:$(date):$backup_size" >> "$BACKUP_BASE_DIR/backup_history.log"
    else
        log_error "  ❌ バックアップ圧縮失敗"
        return 1
    fi
    
    cd "$PROJECT_DIR"
}

# 外部バックアップ
external_backup() {
    log_info "外部バックアップ中..."
    
    # 外部バックアップディレクトリ作成
    mkdir -p "$EXTERNAL_BACKUP_DIR"
    
    # 最新のバックアップファイルを外部にコピー
    latest_backup=$(ls -t "$BACKUP_BASE_DIR"/*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$latest_backup" ]; then
        cp "$latest_backup" "$EXTERNAL_BACKUP_DIR/"
        log_info "  ✅ 外部バックアップ完了: $EXTERNAL_BACKUP_DIR/$(basename "$latest_backup")"
    else
        log_warn "  ⚠️  バックアップファイルが見つかりません"
    fi
}

# 古いバックアップクリーンアップ
cleanup_old_backups() {
    log_info "古いバックアップクリーンアップ中..."
    
    # ローカルバックアップクリーンアップ
    deleted_count=0
    while IFS= read -r -d '' file; do
        rm "$file"
        deleted_count=$((deleted_count + 1))
    done < <(find "$BACKUP_BASE_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    log_info "  削除されたローカルバックアップ: $deleted_count 個"
    
    # 外部バックアップクリーンアップ
    if [ -d "$EXTERNAL_BACKUP_DIR" ]; then
        external_deleted_count=0
        while IFS= read -r -d '' file; do
            rm "$file"
            external_deleted_count=$((external_deleted_count + 1))
        done < <(find "$EXTERNAL_BACKUP_DIR" -name "*.tar.gz" -mtime +$((RETENTION_DAYS * 2)) -print0 2>/dev/null)
        
        log_info "  削除された外部バックアップ: $external_deleted_count 個"
    fi
}

# バックアップ統計
show_backup_stats() {
    log_info "バックアップ統計:"
    
    # ローカルバックアップ
    if [ -d "$BACKUP_BASE_DIR" ]; then
        local_count=$(find "$BACKUP_BASE_DIR" -name "*.tar.gz" | wc -l | tr -d ' ')
        local_size=$(du -sh "$BACKUP_BASE_DIR" 2>/dev/null | cut -f1)
        log_info "  ローカルバックアップ: $local_count 個 ($local_size)"
    fi
    
    # 外部バックアップ
    if [ -d "$EXTERNAL_BACKUP_DIR" ]; then
        external_count=$(find "$EXTERNAL_BACKUP_DIR" -name "*.tar.gz" | wc -l | tr -d ' ')
        external_size=$(du -sh "$EXTERNAL_BACKUP_DIR" 2>/dev/null | cut -f1)
        log_info "  外部バックアップ: $external_count 個 ($external_size)"
    fi
    
    # 最新のバックアップ
    latest_backup=$(ls -t "$BACKUP_BASE_DIR"/*.tar.gz 2>/dev/null | head -1)
    if [ -n "$latest_backup" ]; then
        latest_date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$latest_backup" 2>/dev/null || echo "不明")
        log_info "  最新バックアップ: $(basename "$latest_backup") ($latest_date)"
    fi
}

# メイン実行
main() {
    # バックアップディレクトリ作成
    mkdir -p "$BACKUP_BASE_DIR"
    
    # 引数に基づいて実行
    case "${1:-full}" in
        "full"|"incremental"|"database"|"files")
            perform_backup "$1"
            compress_backup
            external_backup
            cleanup_old_backups
            show_backup_stats
            
            log_info "✅ バックアップ処理完了"
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "stats")
            show_backup_stats
            ;;
        "restore")
            if [ -z "$2" ]; then
                log_error "復元するバックアップファイルを指定してください"
                echo "使用方法: $0 restore <backup_file.tar.gz>"
                exit 1
            fi
            restore_backup "$2"
            ;;
        *)
            echo "BSF-LoopTech バックアップシステム"
            echo ""
            echo "使用方法: $0 [COMMAND]"
            echo ""
            echo "COMMANDS:"
            echo "  full        完全バックアップ（デフォルト）"
            echo "  incremental 増分バックアップ"
            echo "  database    データベースのみ"
            echo "  files       ファイルのみ"
            echo "  cleanup     古いバックアップの削除"
            echo "  stats       バックアップ統計表示"
            echo "  restore     バックアップの復元"
            echo ""
            echo "例:"
            echo "  $0 full                    # 完全バックアップ"
            echo "  $0 incremental             # 増分バックアップ"
            echo "  $0 restore backup.tar.gz   # バックアップ復元"
            ;;
    esac
}

# 復元機能
restore_backup() {
    local backup_file="$1"
    
    log_header "バックアップ復元"
    
    if [ ! -f "$backup_file" ]; then
        log_error "バックアップファイルが見つかりません: $backup_file"
        exit 1
    fi
    
    log_warn "⚠️  警告: この操作は現在のデータを上書きします"
    read -p "続行しますか？ (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "復元をキャンセルしました"
        exit 0
    fi
    
    log_info "バックアップ復元中: $backup_file"
    
    # 復元用一時ディレクトリ
    restore_dir="temp/restore_$(date +%s)"
    mkdir -p "$restore_dir"
    
    # バックアップファイルを展開
    tar -xzf "$backup_file" -C "$restore_dir"
    
    # 復元実行
    extracted_dir=$(ls "$restore_dir")
    if [ -d "$restore_dir/$extracted_dir" ]; then
        log_info "ファイル復元中..."
        
        # 重要なファイルをバックアップから復元
        for target_info in "${BACKUP_TARGETS[@]}"; do
            IFS=':' read -r target_path target_name <<< "$target_info"
            
            if [ -e "$restore_dir/$extracted_dir/$target_path" ]; then
                log_info "  復元中: $target_name"
                cp -R "$restore_dir/$extracted_dir/$target_path" .
            fi
        done
        
        log_info "✅ ファイル復元完了"
    fi
    
    # 一時ディレクトリクリーンアップ
    rm -rf "$restore_dir"
    
    log_info "✅ バックアップ復元完了"
    log_warn "データベースの復元は手動で行ってください"
}

# スクリプト実行
main "$@"