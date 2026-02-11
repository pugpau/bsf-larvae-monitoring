#!/bin/bash

# BSF-LoopTech メンテナンススクリプト
# 本番環境の定期メンテナンスタスク

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_section() {
    echo -e "${CYAN}--- $1 ---${NC}"
}

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# メンテナンスログ
MAINTENANCE_LOG="logs/maintenance.log"

# メンテナンス記録
log_maintenance() {
    echo "$(date): $1" >> "$MAINTENANCE_LOG"
}

# 1. システムヘルスチェック
health_check() {
    log_section "システムヘルスチェック"
    
    local issues_found=0
    
    # プロセス確認
    CRITICAL_PROCESSES=(
        "uvicorn.*main:app:FastAPIアプリケーション"
        "python.*ml_pipeline_manager.py:MLパイプラインスケジューラー"
        "mosquitto.*mosquitto.conf:TLS MQTTブローカー"
    )
    
    for process_info in "${CRITICAL_PROCESSES[@]}"; do
        IFS=':' read -r pattern name <<< "$process_info"
        
        if ! pgrep -f "$pattern" > /dev/null 2>&1; then
            log_error "$name が実行されていません"
            issues_found=$((issues_found + 1))
        else
            log_info "$name は正常に実行中"
        fi
    done
    
    # サービス確認
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_error "HTTP API が応答していません"
        issues_found=$((issues_found + 1))
    else
        log_info "HTTP API は正常に動作中"
    fi
    
    # データベース確認
    if ! brew services list | grep postgresql | grep started > /dev/null; then
        log_error "PostgreSQL が実行されていません"
        issues_found=$((issues_found + 1))
    else
        log_info "PostgreSQL は正常に実行中"
    fi
    
    if ! brew services list | grep influxdb | grep started > /dev/null; then
        log_error "InfluxDB が実行されていません"
        issues_found=$((issues_found + 1))
    else
        log_info "InfluxDB は正常に実行中"
    fi
    
    if [ $issues_found -eq 0 ]; then
        log_info "✅ システムヘルスチェック: 全て正常"
        log_maintenance "Health check passed - no issues found"
    else
        log_warn "⚠️  システムヘルスチェック: $issues_found 個の問題を検出"
        log_maintenance "Health check found $issues_found issues"
    fi
    
    return $issues_found
}

# 2. ログメンテナンス
log_maintenance_task() {
    log_section "ログメンテナンス"
    
    # ログローテーション実行
    if [ -f "scripts/rotate_logs.sh" ]; then
        log_info "ログローテーション実行中..."
        ./scripts/rotate_logs.sh
        log_maintenance "Log rotation completed"
    else
        log_warn "ログローテーションスクリプトが見つかりません"
    fi
    
    # 空のログファイル削除
    empty_logs_count=0
    find logs -name "*.log" -size 0 -delete 2>/dev/null || true
    empty_logs_count=$(find logs -name "*.log" -size 0 | wc -l | tr -d ' ')
    
    if [ $empty_logs_count -gt 0 ]; then
        log_info "$empty_logs_count 個の空のログファイルを削除しました"
    fi
}

# 3. データベースメンテナンス
database_maintenance() {
    log_section "データベースメンテナンス"
    
    # PostgreSQL統計更新
    log_info "PostgreSQL統計更新中..."
    if command -v psql > /dev/null; then
        source .env 2>/dev/null || true
        
        POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
        POSTGRES_PORT="${POSTGRES_PORT:-5432}"
        POSTGRES_DB="${POSTGRES_DB:-bsf_system}"
        POSTGRES_USER="${POSTGRES_USER:-bsf_user}"
        
        # 統計情報更新
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ANALYZE;" 2>/dev/null || {
            log_warn "PostgreSQL統計更新に失敗しました（認証エラーの可能性）"
        }
    else
        log_warn "psqlコマンドが見つかりません"
    fi
    
    # InfluxDBメンテナンス（設定確認）
    log_info "InfluxDB設定確認中..."
    if curl -s http://localhost:8086/health > /dev/null; then
        log_info "InfluxDBは正常に動作中"
    else
        log_warn "InfluxDB接続確認に失敗しました"
    fi
    
    log_maintenance "Database maintenance completed"
}

# 4. MLモデルメンテナンス
ml_model_maintenance() {
    log_section "MLモデルメンテナンス"
    
    # モデルレジストリクリーンアップ
    if [ -d "model_registry" ]; then
        registry_size=$(du -sh model_registry | cut -f1)
        log_info "モデルレジストリサイズ: $registry_size"
        
        # 古いモデルファイルをチェック（例：90日以上古い）
        old_models_count=$(find model_registry -name "*.pkl" -mtime +90 | wc -l | tr -d ' ')
        if [ $old_models_count -gt 0 ]; then
            log_info "$old_models_count 個の古いモデルファイルが見つかりました"
            log_warn "古いモデルの手動確認を推奨します"
        fi
    fi
    
    # ML パイプライン統計確認
    log_info "MLパイプライン統計確認中..."
    python scripts/ml_pipeline_manager.py list-models > /dev/null 2>&1 || {
        log_warn "MLパイプライン統計取得に失敗しました"
    }
    
    log_maintenance "ML model maintenance completed"
}

# 5. セキュリティチェック
security_check() {
    log_section "セキュリティチェック"
    
    # 証明書有効期限チェック
    if [ -f "certs/ca.crt" ]; then
        cert_expiry=$(openssl x509 -in certs/ca.crt -noout -enddate | cut -d= -f2)
        cert_expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$cert_expiry" "+%s" 2>/dev/null || echo "0")
        current_epoch=$(date "+%s")
        days_until_expiry=$(( (cert_expiry_epoch - current_epoch) / 86400 ))
        
        if [ $days_until_expiry -lt 30 ]; then
            log_warn "⚠️  CA証明書の有効期限が近づいています: $days_until_expiry 日"
        else
            log_info "CA証明書有効期限: $days_until_expiry 日"
        fi
    fi
    
    # ファイル権限チェック
    log_info "重要ファイルの権限確認中..."
    
    # 秘密鍵ファイルの権限確認
    find certs -name "*.key" -exec stat -f "%Sp %N" {} \; | while read permissions file; do
        if [[ "$permissions" != "-rw-------" ]]; then
            log_warn "秘密鍵ファイルの権限が適切でありません: $file ($permissions)"
        fi
    done
    
    # .envファイルの権限確認
    if [ -f ".env" ]; then
        env_permissions=$(stat -f "%Sp" .env)
        if [[ "$env_permissions" != "-rw-------" ]] && [[ "$env_permissions" != "-rw-r--r--" ]]; then
            log_warn ".envファイルの権限を確認してください: $env_permissions"
        fi
    fi
    
    log_maintenance "Security check completed"
}

# 6. システムリソースチェック
resource_check() {
    log_section "システムリソースチェック"
    
    # ディスク使用量
    disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
    log_info "ディスク使用量: ${disk_usage}%"
    
    if [ $disk_usage -gt 85 ]; then
        log_warn "⚠️  ディスク使用量が高くなっています: ${disk_usage}%"
        log_maintenance "High disk usage warning: ${disk_usage}%"
    fi
    
    # メモリ使用量（BSFプロセス）
    bsf_memory_total=0
    bsf_pids=$(pgrep -f "uvicorn.*main:app|python.*ml_pipeline_manager.py|mosquitto.*mosquitto.conf" 2>/dev/null || echo "")
    
    if [ -n "$bsf_pids" ]; then
        for pid in $bsf_pids; do
            if ps -p "$pid" > /dev/null 2>&1; then
                memory_mb=$(ps -p "$pid" -o rss= | awk '{print $1/1024}')
                bsf_memory_total=$(echo "$bsf_memory_total + $memory_mb" | bc 2>/dev/null || echo $bsf_memory_total)
            fi
        done
    fi
    
    log_info "BSF-LoopTechメモリ使用量: ${bsf_memory_total}MB"
    
    # CPU負荷
    load_average=$(uptime | awk -F'load averages:' '{print $2}' | awk '{print $1}')
    log_info "システム負荷: $load_average"
    
    log_maintenance "Resource check completed - Disk: ${disk_usage}%, Memory: ${bsf_memory_total}MB, Load: $load_average"
}

# 7. バックアップ確認
backup_check() {
    log_section "バックアップ確認"
    
    if [ -d "backup" ]; then
        # 最新のバックアップ確認
        latest_backup=$(ls -t backup/*.tar.gz 2>/dev/null | head -1)
        if [ -n "$latest_backup" ]; then
            backup_age_hours=$(( ($(date +%s) - $(stat -f %m "$latest_backup")) / 3600 ))
            log_info "最新バックアップ: $(basename "$latest_backup") (${backup_age_hours}時間前)"
            
            if [ $backup_age_hours -gt 48 ]; then
                log_warn "⚠️  最新バックアップが48時間以上古くなっています"
                log_maintenance "Old backup warning: ${backup_age_hours} hours old"
            fi
        else
            log_warn "⚠️  バックアップファイルが見つかりません"
            log_maintenance "No backup files found"
        fi
        
        # バックアップディレクトリサイズ
        backup_size=$(du -sh backup | cut -f1)
        log_info "バックアップディレクトリサイズ: $backup_size"
    else
        log_warn "バックアップディレクトリが見つかりません"
    fi
}

# 8. アップデートチェック
update_check() {
    log_section "アップデートチェック"
    
    # Git状態確認
    if git status > /dev/null 2>&1; then
        # リモートブランチとの差分確認
        git fetch > /dev/null 2>&1 || true
        
        local_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        remote_commit=$(git rev-parse origin/$(git branch --show-current) 2>/dev/null || echo "unknown")
        
        if [ "$local_commit" != "$remote_commit" ] && [ "$remote_commit" != "unknown" ]; then
            log_warn "⚠️  リモートリポジトリに新しいコミットがあります"
            log_maintenance "Remote updates available"
        else
            log_info "Gitリポジトリは最新です"
        fi
        
        # 未コミットの変更確認
        if ! git diff --quiet 2>/dev/null; then
            log_info "未コミットの変更があります"
        fi
    else
        log_warn "Gitリポジトリではありません"
    fi
    
    # Homebrewパッケージアップデート確認
    if command -v brew > /dev/null; then
        log_info "Homebrewアップデート確認中..."
        outdated_count=$(brew outdated | wc -l | tr -d ' ')
        if [ $outdated_count -gt 0 ]; then
            log_info "$outdated_count 個のパッケージにアップデートがあります"
            log_maintenance "Homebrew packages need updates: $outdated_count"
        else
            log_info "Homebrewパッケージは最新です"
        fi
    fi
}

# 9. 自動修復機能
auto_repair() {
    log_section "自動修復"
    
    repairs_made=0
    
    # 必要なディレクトリを再作成
    REQUIRED_DIRS=("logs" "data" "backup" "temp")
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "ディレクトリを再作成: $dir"
            repairs_made=$((repairs_made + 1))
        fi
    done
    
    # 重要なログファイルが存在しない場合は作成
    REQUIRED_LOGS=("logs/application.log" "logs/system.log" "logs/maintenance.log")
    for log_file in "${REQUIRED_LOGS[@]}"; do
        if [ ! -f "$log_file" ]; then
            touch "$log_file"
            chmod 644 "$log_file"
            log_info "ログファイルを作成: $log_file"
            repairs_made=$((repairs_made + 1))
        fi
    done
    
    # 権限修復
    if [ -d "certs" ]; then
        find certs -name "*.key" -exec chmod 600 {} \; 2>/dev/null || true
        find certs -name "*.crt" -exec chmod 644 {} \; 2>/dev/null || true
        log_info "証明書ファイルの権限を修復しました"
    fi
    
    if [ $repairs_made -gt 0 ]; then
        log_info "✅ $repairs_made 個の項目を自動修復しました"
        log_maintenance "Auto repair completed: $repairs_made items fixed"
    else
        log_info "修復が必要な項目はありませんでした"
    fi
}

# 10. メンテナンス報告生成
generate_report() {
    log_section "メンテナンス報告生成"
    
    report_file="logs/maintenance_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
BSF-LoopTech メンテナンス報告
=============================
日時: $(date)
システム: $(uname -a)

実行されたメンテナンスタスク:
- システムヘルスチェック
- ログメンテナンス
- データベースメンテナンス
- MLモデルメンテナンス
- セキュリティチェック
- システムリソースチェック
- バックアップ確認
- アップデートチェック
- 自動修復

システム状況:
- プロジェクトディレクトリ: $PROJECT_DIR
- ディスク使用量: $(df -h . | tail -1 | awk '{print $5}')
- メモリ使用量: $(vm_stat | grep "Pages free" | awk '{print $3*4096/1024/1024 " MB free"}')
- システム負荷: $(uptime | awk -F'load averages:' '{print $2}')

最近のメンテナンスログ:
$(tail -10 "$MAINTENANCE_LOG" 2>/dev/null || echo "メンテナンスログが見つかりません")
EOF
    
    log_info "メンテナンス報告書を生成: $report_file"
    log_maintenance "Maintenance report generated: $report_file"
}

# メイン実行
main() {
    case "${1:-all}" in
        "health")
            health_check
            ;;
        "logs")
            log_maintenance_task
            ;;
        "database")
            database_maintenance
            ;;
        "ml")
            ml_model_maintenance
            ;;
        "security")
            security_check
            ;;
        "resources")
            resource_check
            ;;
        "backup")
            backup_check
            ;;
        "updates")
            update_check
            ;;
        "repair")
            auto_repair
            ;;
        "report")
            generate_report
            ;;
        "all"|*)
            log_header "BSF-LoopTech 定期メンテナンス"
            log_maintenance "Maintenance started - mode: ${1:-all}"
            
            health_check
            log_maintenance_task
            database_maintenance
            ml_model_maintenance
            security_check
            resource_check
            backup_check
            update_check
            auto_repair
            generate_report
            
            log_header "メンテナンス完了"
            log_info "🎉 全てのメンテナンスタスクが完了しました"
            log_maintenance "Maintenance completed successfully"
            ;;
    esac
}

# スクリプト実行
main "$@"