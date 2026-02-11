#!/bin/bash

# BSF-LoopTech システム監視スクリプト
# 本番環境用リソース監視とアラート

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

# 監視設定
CPU_THRESHOLD=80           # CPU使用率アラート閾値（%）
MEMORY_THRESHOLD=80        # メモリ使用率アラート閾値（%）
DISK_THRESHOLD=85          # ディスク使用率アラート閾値（%）
LOG_SIZE_THRESHOLD=100     # ログファイルサイズ閾値（MB）

# アラートファイル
ALERT_LOG="logs/system_alerts.log"
MONITOR_LOG="logs/system_monitor.log"

# 現在時刻
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# ヘルパー関数
send_alert() {
    local level="$1"
    local message="$2"
    echo "[$CURRENT_TIME] [$level] $message" >> "$ALERT_LOG"
    
    case "$level" in
        "CRITICAL")
            log_error "CRITICAL: $message"
            ;;
        "WARNING")
            log_warn "WARNING: $message"
            ;;
        "INFO")
            log_info "INFO: $message"
            ;;
    esac
}

# 1. システムリソース監視
monitor_system_resources() {
    log_info "システムリソース監視中..."
    
    # CPU使用率
    cpu_usage=$(top -l 1 -s 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    cpu_usage_int=${cpu_usage%.*}  # 小数点以下を削除
    
    if [ "$cpu_usage_int" -gt "$CPU_THRESHOLD" ]; then
        send_alert "WARNING" "High CPU usage detected: ${cpu_usage}%"
    fi
    
    # メモリ使用率
    memory_info=$(vm_stat | grep -E "Pages (free|active|inactive|speculative|wired)")
    page_size=$(vm_stat | grep "page size" | awk '{print $8}')
    
    # メモリ使用率計算（簡易版）
    total_memory_gb=$(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024}')
    available_memory_gb=$(echo "$memory_info" | awk -v ps="$page_size" '
        /Pages free/ {free=$3}
        /Pages speculative/ {spec=$3}
        END {print (free+spec)*ps/1024/1024/1024}
    ')
    
    memory_usage=$(echo "$total_memory_gb $available_memory_gb" | awk '{printf "%.0f", (1-$2/$1)*100}')
    
    if [ "$memory_usage" -gt "$MEMORY_THRESHOLD" ]; then
        send_alert "WARNING" "High memory usage detected: ${memory_usage}%"
    fi
    
    # ディスク使用率
    disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt "$DISK_THRESHOLD" ]; then
        send_alert "CRITICAL" "High disk usage detected: ${disk_usage}%"
    fi
    
    # 監視ログに記録
    echo "[$CURRENT_TIME] CPU:${cpu_usage}% MEM:${memory_usage}% DISK:${disk_usage}%" >> "$MONITOR_LOG"
}

# 2. BSF-LoopTechプロセス監視
monitor_bsf_processes() {
    log_info "BSF-LoopTechプロセス監視中..."
    
    # 監視対象プロセス
    PROCESSES=(
        "uvicorn.*main:app:FastAPIアプリケーション"
        "python.*ml_pipeline_manager.py:MLパイプラインスケジューラー"
        "mosquitto.*mosquitto.conf:TLS MQTTブローカー"
    )
    
    for process_info in "${PROCESSES[@]}"; do
        IFS=':' read -r pattern name <<< "$process_info"
        
        if ! pgrep -f "$pattern" > /dev/null 2>&1; then
            send_alert "CRITICAL" "$name process is not running"
        else
            # プロセスのリソース使用量確認
            pids=$(pgrep -f "$pattern")
            for pid in $pids; do
                if ps -p "$pid" > /dev/null 2>&1; then
                    cpu_usage=$(ps -p "$pid" -o %cpu= | tr -d ' ')
                    memory_mb=$(ps -p "$pid" -o rss= | awk '{print $1/1024}')
                    
                    # 異常に高いリソース使用をチェック
                    if (( $(echo "$cpu_usage > 50" | bc -l 2>/dev/null || echo 0) )); then
                        send_alert "WARNING" "$name (PID:$pid) high CPU usage: ${cpu_usage}%"
                    fi
                    
                    if (( $(echo "$memory_mb > 1000" | bc -l 2>/dev/null || echo 0) )); then
                        send_alert "WARNING" "$name (PID:$pid) high memory usage: ${memory_mb}MB"
                    fi
                fi
            done
        fi
    done
}

# 3. データベース接続監視
monitor_databases() {
    log_info "データベース接続監視中..."
    
    # PostgreSQL監視
    if ! brew services list | grep postgresql | grep started > /dev/null; then
        send_alert "CRITICAL" "PostgreSQL service is not running"
    else
        # 簡易接続テスト
        if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
            send_alert "WARNING" "PostgreSQL connection test failed"
        fi
    fi
    
    # InfluxDB監視
    if ! brew services list | grep influxdb | grep started > /dev/null; then
        send_alert "CRITICAL" "InfluxDB service is not running"
    else
        # InfluxDB接続テスト
        if ! curl -s http://localhost:8086/health > /dev/null; then
            send_alert "WARNING" "InfluxDB connection test failed"
        fi
    fi
}

# 4. ネットワーク監視
monitor_network() {
    log_info "ネットワーク接続監視中..."
    
    # HTTP API監視
    if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null | grep -q "200\|404"; then
        send_alert "CRITICAL" "HTTP API (port 8000) is not responding"
    fi
    
    # MQTT TLS監視
    if ! timeout 5 mosquitto_pub -h localhost -p 8883 --cafile certs/ca.crt -t "monitor/test" -m "test" > /dev/null 2>&1; then
        send_alert "WARNING" "MQTT TLS (port 8883) connection failed"
    fi
    
    # MQTT標準監視
    if ! timeout 5 mosquitto_pub -h localhost -p 1883 -t "monitor/test" -m "test" > /dev/null 2>&1; then
        send_alert "WARNING" "MQTT Standard (port 1883) connection failed"
    fi
}

# 5. ログファイル監視
monitor_log_files() {
    log_info "ログファイル監視中..."
    
    LOG_FILES=(
        "logs/application.log"
        "logs/ml_pipeline.log"
        "logs/mosquitto.log"
        "logs/launchd_stderr.log"
    )
    
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            # ファイルサイズチェック
            file_size_bytes=$(stat -f "%z" "$log_file" 2>/dev/null || echo "0")
            file_size_mb=$((file_size_bytes / 1024 / 1024))
            
            if [ "$file_size_mb" -gt "$LOG_SIZE_THRESHOLD" ]; then
                send_alert "WARNING" "Large log file detected: $log_file (${file_size_mb}MB)"
            fi
            
            # 最新のエラーログチェック（過去1時間）
            if [ -s "$log_file" ]; then
                recent_errors=$(grep -i "error\|exception\|failed\|critical" "$log_file" | tail -10 | wc -l | tr -d ' ')
                if [ "$recent_errors" -gt 5 ]; then
                    send_alert "WARNING" "Multiple recent errors in $log_file ($recent_errors errors)"
                fi
            fi
        fi
    done
}

# 6. ディスク容量監視
monitor_disk_space() {
    log_info "ディスク容量監視中..."
    
    # 重要なディレクトリの容量確認
    DIRECTORIES=(
        "logs:ログディレクトリ"
        "data:データディレクトリ"
        "model_registry:モデルレジストリ"
        "backup:バックアップディレクトリ"
    )
    
    for dir_info in "${DIRECTORIES[@]}"; do
        IFS=':' read -r dir_path dir_name <<< "$dir_info"
        
        if [ -d "$dir_path" ]; then
            dir_size_mb=$(du -sm "$dir_path" 2>/dev/null | cut -f1)
            
            # 1GB以上の場合アラート
            if [ "$dir_size_mb" -gt 1024 ]; then
                send_alert "INFO" "$dir_name is using ${dir_size_mb}MB of disk space"
            fi
        fi
    done
}

# 7. システム稼働時間とパフォーマンス
monitor_system_performance() {
    log_info "システムパフォーマンス監視中..."
    
    # システム稼働時間
    uptime_info=$(uptime)
    load_average=$(echo "$uptime_info" | awk -F'load averages:' '{print $2}' | awk '{print $1}')
    
    # 負荷平均が2.0以上の場合アラート
    if (( $(echo "$load_average > 2.0" | bc -l 2>/dev/null || echo 0) )); then
        send_alert "WARNING" "High system load average: $load_average"
    fi
    
    # 温度監視（macOSの場合、簡易版）
    # Note: macOSでは温度センサーへの直接アクセスが制限されているため、
    # システム負荷やファン速度で間接的に判断
    
    # パフォーマンス統計をログに記録
    echo "[$CURRENT_TIME] Load:$load_average" >> "$MONITOR_LOG"
}

# メイン実行
main() {
    # ログディレクトリ作成
    mkdir -p logs
    
    # 引数チェック
    case "${1:-all}" in
        "resources")
            monitor_system_resources
            ;;
        "processes")
            monitor_bsf_processes
            ;;
        "databases")
            monitor_databases
            ;;
        "network")
            monitor_network
            ;;
        "logs")
            monitor_log_files
            ;;
        "disk")
            monitor_disk_space
            ;;
        "performance")
            monitor_system_performance
            ;;
        "all"|*)
            log_header "BSF-LoopTech システム監視"
            monitor_system_resources
            monitor_bsf_processes
            monitor_databases
            monitor_network
            monitor_log_files
            monitor_disk_space
            monitor_system_performance
            
            log_info "✅ 全監視項目完了"
            
            # アラート統計
            if [ -f "$ALERT_LOG" ]; then
                alert_count=$(grep "$(date '+%Y-%m-%d')" "$ALERT_LOG" | wc -l | tr -d ' ')
                if [ "$alert_count" -gt 0 ]; then
                    log_warn "本日のアラート数: $alert_count"
                    log_info "詳細: $ALERT_LOG"
                fi
            fi
            ;;
    esac
}

# スクリプト実行
main "$@"