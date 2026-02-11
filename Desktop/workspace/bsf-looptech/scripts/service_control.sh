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
