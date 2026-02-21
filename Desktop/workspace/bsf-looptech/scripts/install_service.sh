#!/bin/bash

# BSF-LoopTech システムサービスインストールスクリプト
# macOS LaunchDaemon設定

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# プロジェクトディレクトリ
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

log_header "BSF-LoopTech システムサービスインストール"

# 1. 前提条件確認
log_info "1. 前提条件確認中..."

# macOSバージョン確認
macos_version=$(sw_vers -productVersion)
log_info "macOS バージョン: $macos_version"

# 管理者権限確認
if [ "$EUID" -eq 0 ]; then
    log_error "このスクリプトはrootユーザーで実行しないでください"
    log_error "通常ユーザーで実行し、必要に応じてsudoを使用します"
    exit 1
fi

# 必要なファイル確認
required_files=(
    "scripts/start_production.sh"
    "scripts/stop_production.sh"
    "config/com.bsf-looptech.production.plist"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "必要なファイルが見つかりません: $file"
        exit 1
    fi
done

log_info "✅ 前提条件確認完了"

# 2. LaunchAgent設定（ユーザーレベル）
log_info "2. LaunchAgent設定中..."

# ユーザーのLaunchAgentsディレクトリ
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.bsf-looptech.production.plist"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# ディレクトリ作成
mkdir -p "$LAUNCH_AGENTS_DIR"

# 現在のパスに合わせてplistファイルを更新
log_info "plistファイルをユーザー環境に合わせて更新中..."

# 動的にパスを設定したplistファイルを生成
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bsf-looptech.production</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/scripts/start_production.sh</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <false/>
    
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/launchd_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/launchd_stderr.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>60</integer>
    
    <key>ExitTimeOut</key>
    <integer>30</integer>
    
</dict>
</plist>
EOF

log_info "✅ plistファイルを作成: $PLIST_PATH"

# 3. サービス登録
log_info "3. サービス登録中..."

# 既存のサービスを停止・削除
if launchctl list | grep "com.bsf-looptech.production" > /dev/null; then
    log_info "既存のサービスを停止中..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# 新しいサービスを登録
log_info "サービスを登録中..."
launchctl load "$PLIST_PATH"

# サービス状態確認
sleep 2
if launchctl list | grep "com.bsf-looptech.production" > /dev/null; then
    log_info "✅ サービス登録成功"
else
    log_error "❌ サービス登録失敗"
    exit 1
fi

# 4. 必要なディレクトリ作成
log_info "4. 必要なディレクトリ作成中..."

directories=("logs" "data" "backup" "temp")
for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    log_info "ディレクトリ作成: $dir"
done

# ログファイルの初期化
touch logs/launchd_stdout.log logs/launchd_stderr.log
chmod 644 logs/launchd_stdout.log logs/launchd_stderr.log

# 5. システムサービス管理スクリプト作成
log_info "5. システムサービス管理スクリプト作成中..."

cat > scripts/service_control.sh << 'EOF'
#!/bin/bash

# BSF-LoopTech サービス制御スクリプト

set -e

PLIST_PATH="$HOME/Library/LaunchAgents/com.bsf-looptech.production.plist"
SERVICE_NAME="com.bsf-looptech.production"

case "$1" in
    start)
        echo "BSF-LoopTechサービスを開始中..."
        launchctl load "$PLIST_PATH"
        echo "✅ サービス開始完了"
        ;;
    stop)
        echo "BSF-LoopTechサービスを停止中..."
        launchctl unload "$PLIST_PATH"
        echo "✅ サービス停止完了"
        ;;
    restart)
        echo "BSF-LoopTechサービスを再起動中..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        sleep 2
        launchctl load "$PLIST_PATH"
        echo "✅ サービス再起動完了"
        ;;
    status)
        echo "BSF-LoopTechサービス状態確認中..."
        if launchctl list | grep "$SERVICE_NAME" > /dev/null; then
            echo "✅ サービス実行中"
            launchctl list | grep "$SERVICE_NAME"
        else
            echo "❌ サービス停止中"
        fi
        ;;
    logs)
        echo "最新のサービスログ:"
        echo "--- stdout ---"
        tail -20 logs/launchd_stdout.log 2>/dev/null || echo "ログファイルが見つかりません"
        echo "--- stderr ---"
        tail -20 logs/launchd_stderr.log 2>/dev/null || echo "ログファイルが見つかりません"
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x scripts/service_control.sh
log_info "✅ サービス制御スクリプト作成完了"

# 6. 自動起動テスト
log_info "6. 自動起動テスト中..."

# 一度サービスを停止して再起動
launchctl unload "$PLIST_PATH"
sleep 2
launchctl load "$PLIST_PATH"
sleep 5

# サービス状態確認
if launchctl list | grep "com.bsf-looptech.production" > /dev/null; then
    log_info "✅ 自動起動テスト成功"
else
    log_warn "⚠️  自動起動テストで問題が発生しました"
fi

log_header "システムサービスインストール完了"

echo ""
log_info "🎉 BSF-LoopTechシステムサービスのインストールが完了しました"
echo ""
log_info "📋 サービス管理コマンド:"
log_info "  - 開始: ./scripts/service_control.sh start"
log_info "  - 停止: ./scripts/service_control.sh stop"  
log_info "  - 再起動: ./scripts/service_control.sh restart"
log_info "  - 状態確認: ./scripts/service_control.sh status"
log_info "  - ログ確認: ./scripts/service_control.sh logs"
echo ""
log_info "📁 設定ファイル: $PLIST_PATH"
log_info "📊 ログファイル: logs/launchd_*.log"
echo ""
log_info "⚠️  重要な注意事項:"
log_info "  - システム再起動後、サービスは自動的に開始されます"
log_info "  - ユーザーログイン不要で動作します"
log_info "  - サービス削除: launchctl unload $PLIST_PATH"
echo ""

log_info "✅ システムサービスインストール完了"