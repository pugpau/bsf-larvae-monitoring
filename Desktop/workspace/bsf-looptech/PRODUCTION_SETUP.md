# BSF-LoopTech 本番環境セットアップガイド

> **MacBook本番環境での数ヶ月運用のための完全ガイド**

## 📋 概要

このガイドは、BSF-LoopTechシステムをMacBook上で本番環境として数ヶ月間運用するためのセットアップ手順を記載しています。

## 🚀 クイックスタート

### 1. 初回セットアップ

```bash
# システムサービスのインストール
./scripts/install_service.sh

# 本番環境の起動
./scripts/start_production.sh
```

### 2. 日常的な操作

```bash
# システム状態確認
./scripts/status_production.sh

# システム再起動
./scripts/restart_production.sh

# システム停止
./scripts/stop_production.sh
```

## 📁 ディレクトリ構造

```
bsf-looptech/
├── scripts/                    # 運用スクリプト
│   ├── start_production.sh     # 本番環境起動
│   ├── stop_production.sh      # 本番環境停止
│   ├── restart_production.sh   # 本番環境再起動
│   ├── status_production.sh    # ステータス確認
│   ├── install_service.sh      # システムサービス設定
│   ├── service_control.sh      # サービス制御
│   ├── backup_system.sh        # バックアップシステム
│   ├── maintenance.sh          # メンテナンススクリプト
│   ├── rotate_logs.sh          # ログローテーション
│   ├── system_monitor.sh       # システム監視
│   └── ml_pipeline_manager.py  # MLパイプライン管理
├── certs/                      # TLS証明書
├── logs/                       # ログファイル
├── backup/                     # バックアップ
├── data/                       # データファイル
├── model_registry/             # MLモデル管理
└── temp/                       # 一時ファイル
```

## 🔧 詳細セットアップ手順

### ステップ1: 前提条件確認

```bash
# 必要なソフトウェアが利用可能か確認
brew list postgresql influxdb mosquitto

# Python仮想環境の確認
source venv/bin/activate
```

### ステップ2: データベース設定

```bash
# PostgreSQLとInfluxDBの起動
brew services start postgresql
brew services start influxdb

# データベースマイグレーション
alembic upgrade head
```

### ステップ3: MQTT証明書生成（既に完了）

```bash
# TLS証明書の確認
ls -la certs/
```

### ステップ4: システムサービス設定

```bash
# LaunchAgentとしてサービス登録
./scripts/install_service.sh

# サービス状態確認
./scripts/service_control.sh status
```

### ステップ5: 本番環境起動

```bash
# 本番環境の起動
./scripts/start_production.sh

# 起動確認
./scripts/status_production.sh
```

## 🔄 運用タスク

### 日次タスク

```bash
# システム状態確認
./scripts/status_production.sh

# システム監視実行
./scripts/system_monitor.sh
```

### 週次タスク

```bash
# ログローテーション
./scripts/rotate_logs.sh

# 完全バックアップ
./scripts/backup_system.sh full

# 定期メンテナンス
./scripts/maintenance.sh
```

### 月次タスク

```bash
# システム更新確認
./scripts/maintenance.sh updates

# セキュリティチェック
./scripts/maintenance.sh security

# バックアップクリーンアップ
./scripts/backup_system.sh cleanup
```

## 📊 監視とアラート

### システム監視

```bash
# 全項目監視
./scripts/system_monitor.sh

# 特定項目監視
./scripts/system_monitor.sh resources
./scripts/system_monitor.sh processes
./scripts/system_monitor.sh network
```

### ログ確認

```bash
# アプリケーションログ
tail -f logs/application.log

# MLパイプラインログ
tail -f logs/ml_pipeline.log

# システムアラート
tail -f logs/system_alerts.log

# メンテナンスログ
tail -f logs/maintenance.log
```

## 💾 バックアップ戦略

### バックアップの種類

1. **完全バックアップ**: 全データの完全コピー
2. **増分バックアップ**: 変更分のみのバックアップ
3. **データベースバックアップ**: DB専用バックアップ

### バックアップコマンド

```bash
# 完全バックアップ（推奨：週1回）
./scripts/backup_system.sh full

# 増分バックアップ（推奨：日1回）
./scripts/backup_system.sh incremental

# データベースのみ
./scripts/backup_system.sh database

# バックアップ統計
./scripts/backup_system.sh stats
```

### 復元方法

```bash
# バックアップから復元
./scripts/backup_system.sh restore backup/YYYYMMDD_HHMMSS_backup.tar.gz
```

## 🛡️ セキュリティ

### TLS証明書管理

- **CA証明書**: `certs/ca.crt`
- **サーバー証明書**: `certs/mqtt-server.crt`
- **クライアント証明書**: `certs/mqtt-client.crt`

### 証明書更新（年1回）

```bash
# 新しい証明書生成
python scripts/generate_mqtt_certs.py

# システム再起動
./scripts/restart_production.sh
```

### セキュリティチェック

```bash
# 定期セキュリティ監査
./scripts/maintenance.sh security
```

## 🔧 メンテナンス

### 定期メンテナンス

```bash
# 全項目メンテナンス
./scripts/maintenance.sh

# 個別メンテナンス
./scripts/maintenance.sh health      # ヘルスチェック
./scripts/maintenance.sh logs        # ログメンテナンス
./scripts/maintenance.sh database    # DB最適化
./scripts/maintenance.sh ml          # MLモデル管理
./scripts/maintenance.sh repair      # 自動修復
```

### 問題解決

#### プロセスが停止している場合

```bash
# システム再起動
./scripts/restart_production.sh

# または個別プロセス確認
ps aux | grep -E "(uvicorn|ml_pipeline|mosquitto)"
```

#### ディスク容量不足

```bash
# ログローテーション
./scripts/rotate_logs.sh

# 古いバックアップ削除
./scripts/backup_system.sh cleanup

# ディスク使用量確認
df -h .
du -sh logs/ backup/ model_registry/
```

#### パフォーマンス低下

```bash
# リソース使用量確認
./scripts/system_monitor.sh resources

# システム負荷確認
top -l 1 | head -20

# メモリ使用量確認
vm_stat
```

## 🚨 緊急時対応

### システム完全停止

```bash
# 緊急停止
./scripts/stop_production.sh

# プロセス強制終了
pkill -f "uvicorn.*main:app"
pkill -f "python.*ml_pipeline_manager.py"
pkill -f "mosquitto.*mosquitto.conf"
```

### データ復旧

```bash
# 最新バックアップから復元
latest_backup=$(ls -t backup/*.tar.gz | head -1)
./scripts/backup_system.sh restore "$latest_backup"

# データベース復元（手動）
# 詳細はバックアップファイル内のREADMEを参照
```

### 設定リセット

```bash
# サービス登録解除
launchctl unload ~/Library/LaunchAgents/com.bsf-looptech.production.plist

# 設定ファイル再生成
rm -f temp/*.pid
./scripts/install_service.sh
```

## 📈 パフォーマンス最適化

### システムリソース監視

- **CPU使用率**: 通常時10%以下
- **メモリ使用量**: BSFプロセス合計1GB以下
- **ディスク使用量**: 85%以下を維持

### 最適化のヒント

1. **ログローテーション**: 週1回実行
2. **バックアップクリーンアップ**: 月1回実行
3. **MLモデル整理**: 古いモデルの定期削除
4. **データベース最適化**: 統計情報の定期更新

## 🔗 重要なエンドポイント

### Webインターフェース
- **メインAPI**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **ヘルスチェック**: http://localhost:8000/health

### MQTT接続
- **TLS接続**: localhost:8883
- **標準接続**: localhost:1883

### データベース
- **PostgreSQL**: localhost:5432
- **InfluxDB**: localhost:8086

## 📞 サポート情報

### ログファイル
- `logs/application.log` - アプリケーション動作ログ
- `logs/ml_pipeline.log` - ML実行ログ
- `logs/system_alerts.log` - システムアラート
- `logs/maintenance.log` - メンテナンス履歴

### 設定ファイル
- `.env` - 環境変数設定
- `alembic.ini` - データベース設定
- `certs/mosquitto.conf` - MQTT設定

### 管理コマンド一覧

| コマンド | 用途 |
|---------|------|
| `./scripts/start_production.sh` | システム起動 |
| `./scripts/stop_production.sh` | システム停止 |
| `./scripts/status_production.sh` | 状態確認 |
| `./scripts/backup_system.sh` | バックアップ |
| `./scripts/maintenance.sh` | メンテナンス |
| `./scripts/system_monitor.sh` | 監視 |
| `python scripts/ml_pipeline_manager.py` | ML管理 |

---

## ✅ セットアップ完了チェックリスト

- [ ] 前提条件確認（PostgreSQL, InfluxDB, Mosquitto）
- [ ] Python仮想環境有効化
- [ ] データベースマイグレーション実行
- [ ] TLS証明書生成確認
- [ ] システムサービス登録
- [ ] 本番環境起動成功
- [ ] 全エンドポイント接続確認
- [ ] バックアップシステム設定
- [ ] 監視システム設定
- [ ] 緊急時対応手順確認

**🎉 本番環境セットアップ完了！**

**重要**: このガイドを定期的に確認し、システムの健全性を維持してください。