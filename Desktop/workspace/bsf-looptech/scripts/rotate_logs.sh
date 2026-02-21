#!/bin/bash

# BSF-LoopTech ログローテーションスクリプト
# 本番環境用ログ管理

set -e

# 色付き出力用
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

log_header "BSF-LoopTech ログローテーション"

# 設定
MAX_LOG_SIZE_MB=50
ARCHIVE_DAYS=30
COMPRESS_DAYS=7

# 現在の日時
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# アーカイブディレクトリ作成
mkdir -p logs/archive

# 1. ログファイル一覧
LOG_FILES=(
    "logs/application.log"
    "logs/ml_pipeline.log"
    "logs/mosquitto.log"
    "logs/system.log"
    "logs/launchd_stdout.log"
    "logs/launchd_stderr.log"
)

log_info "ログローテーション開始..."

# 2. 各ログファイルの処理
for log_file in "${LOG_FILES[@]}"; do
    if [ ! -f "$log_file" ]; then
        log_warn "ログファイルが見つかりません: $log_file"
        continue
    fi
    
    # ファイルサイズ確認（MB単位）
    file_size_bytes=$(stat -f "%z" "$log_file" 2>/dev/null || echo "0")
    file_size_mb=$((file_size_bytes / 1024 / 1024))
    
    log_info "処理中: $log_file (${file_size_mb}MB)"
    
    # サイズ制限チェック
    if [ "$file_size_mb" -gt "$MAX_LOG_SIZE_MB" ]; then
        log_info "  サイズ制限超過 (>${MAX_LOG_SIZE_MB}MB) - ローテーション実行"
        
        # ファイル名から拡張子を取得
        base_name="${log_file%.*}"
        extension="${log_file##*.}"
        
        # アーカイブファイル名
        archive_name="${base_name}.${TIMESTAMP}.${extension}"
        
        # ファイルをアーカイブに移動
        mv "$log_file" "logs/archive/$(basename "$archive_name")"
        
        # 新しい空のログファイルを作成
        touch "$log_file"
        chmod 644 "$log_file"
        
        log_info "  ✅ ローテーション完了: logs/archive/$(basename "$archive_name")"
    else
        log_info "  サイズ制限内 (${file_size_mb}MB) - ローテーション不要"
    fi
done

# 3. 古いアーカイブファイルの圧縮
log_info "古いアーカイブファイルの圧縮中..."

find logs/archive -name "*.log" -mtime +$COMPRESS_DAYS -exec gzip {} \; 2>/dev/null || true

compressed_count=$(find logs/archive -name "*.gz" | wc -l | tr -d ' ')
log_info "圧縮完了: ${compressed_count}個のファイル"

# 4. 非常に古いアーカイブファイルの削除
log_info "古いアーカイブファイルのクリーンアップ中..."

deleted_count=0

# 古い.logファイル削除
while IFS= read -r -d '' file; do
    rm "$file"
    deleted_count=$((deleted_count + 1))
done < <(find logs/archive -name "*.log" -mtime +$ARCHIVE_DAYS -print0 2>/dev/null)

# 古い.gzファイル削除
while IFS= read -r -d '' file; do
    rm "$file"
    deleted_count=$((deleted_count + 1))
done < <(find logs/archive -name "*.gz" -mtime +$ARCHIVE_DAYS -print0 2>/dev/null)

log_info "クリーンアップ完了: ${deleted_count}個のファイル削除"

# 5. ログディレクトリのサイズ統計
log_info "ログディレクトリ統計:"

# 現在のログディレクトリサイズ
current_logs_size=$(du -sh logs 2>/dev/null | cut -f1)
archive_logs_size=$(du -sh logs/archive 2>/dev/null | cut -f1)

log_info "  現在のログ: $current_logs_size"
log_info "  アーカイブ: $archive_logs_size"

# アーカイブファイル数
archive_file_count=$(find logs/archive -type f | wc -l | tr -d ' ')
log_info "  アーカイブファイル数: $archive_file_count"

# 6. システムログに記録
echo "$(date): Log rotation completed - deleted: $deleted_count, compressed: $compressed_count" >> logs/system.log

log_header "ログローテーション完了"

log_info "🔄 ログローテーションが完了しました"
log_info "📊 統計: 削除 ${deleted_count}件, 圧縮 ${compressed_count}件"
log_info "💾 ディスク使用量: 現在ログ $current_logs_size, アーカイブ $archive_logs_size"

echo ""
log_info "📋 推奨事項:"
log_info "  - このスクリプトを定期実行（週1回）してください"
log_info "  - crontabに追加: 0 2 * * 0 /path/to/rotate_logs.sh"
log_info "  - ディスク容量を定期的に監視してください"