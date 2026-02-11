# BSF-LoopTech システム運用ガイド

## 📋 概要

BSF-LoopTech システムの日常運用に必要なコマンドとプロセスをまとめたガイドです。

## 🚀 クイックスタート

### 新規インストール（初回のみ）
```bash
# 推奨セットアップ
./scripts/quick_setup.sh

# または詳細設定
./install.sh
```

### 基本運用コマンド
```bash
# システム状態確認
./scripts/bsf_manager.sh status

# システム起動
./scripts/bsf_manager.sh start

# システム停止
./scripts/bsf_manager.sh stop

# システム再起動
./scripts/bsf_manager.sh restart
```

## 📁 運用スクリプト一覧

### 🔧 統合管理ツール
| スクリプト | 説明 | 使用例 |
|------------|------|---------|
| `scripts/bsf_manager.sh` | メイン管理ツール | `./scripts/bsf_manager.sh status` |
| `scripts/quick_setup.sh` | 簡単セットアップ | `./scripts/quick_setup.sh` |

### 🔄 システム制御
| スクリプト | 説明 | 使用例 |
|------------|------|---------|
| `scripts/start_production.sh` | 本番環境起動 | `./scripts/start_production.sh` |
| `scripts/stop_production.sh` | 本番環境停止 | `./scripts/stop_production.sh` |
| `scripts/restart_production.sh` | 安全な再起動 | `./scripts/restart_production.sh` |
| `scripts/status_production.sh` | 詳細ステータス | `./scripts/status_production.sh` |

### 📦 インストール・アンインストール
| スクリプト | 説明 | 使用例 |
|------------|------|---------|
| `install.sh` | 詳細インストーラー | `./install.sh` |
| `uninstall.sh` | アンインストーラー | `./uninstall.sh` |

## 🎯 統合管理ツール使用方法

### 基本コマンド
```bash
# ヘルプ表示
./scripts/bsf_manager.sh help

# システム状態確認
./scripts/bsf_manager.sh status

# システム起動
./scripts/bsf_manager.sh start

# システム停止
./scripts/bsf_manager.sh stop

# システム再起動
./scripts/bsf_manager.sh restart
```

### 管理コマンド
```bash
# システムインストール
./scripts/bsf_manager.sh install

# システムアンインストール
./scripts/bsf_manager.sh uninstall

# バックアップ実行
./scripts/bsf_manager.sh backup
```

### ログ確認
```bash
# 全ログファイル一覧
./scripts/bsf_manager.sh logs

# アプリケーションログ
./scripts/bsf_manager.sh logs app

# MQTTログ
./scripts/bsf_manager.sh logs mqtt

# MLパイプラインログ
./scripts/bsf_manager.sh logs ml
```

## 📊 システム監視

### リアルタイム監視
```bash
# 詳細ステータス確認
./scripts/status_production.sh

# 簡易ステータス確認
./scripts/bsf_manager.sh status

# ログリアルタイム表示
tail -f logs/application.log
tail -f logs/mosquitto.log
```

### ヘルスチェック
```bash
# HTTP API確認
curl http://localhost:8000/health

# MQTT確認
mosquitto_pub -h localhost -p 1883 -t "test/health" -m "check"

# データベース確認
psql postgres -c "SELECT 1;"
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. システムが起動しない
```bash
# 詳細ステータス確認
./scripts/status_production.sh

# ログ確認
./scripts/bsf_manager.sh logs app

# 強制停止後再起動
pkill -f "uvicorn.*main:app"
./scripts/start_production.sh
```

#### 2. MQTT接続エラー
```bash
# MQTT ブローカー状態確認
brew services list | grep mosquitto

# MQTT ブローカー再起動
brew services restart mosquitto

# TLS証明書確認
ls -la certs/
```

#### 3. データベース接続エラー
```bash
# データベース状態確認
brew services list | grep -E "postgresql|influxdb"

# データベース起動
brew services start postgresql
brew services start influxdb
```

#### 4. ログファイルが大きくなりすぎた
```bash
# ログローテーション
./scripts/rotate_logs.sh

# または手動ローテーション
mv logs/application.log logs/application.log.old
touch logs/application.log
```

### 緊急時の対応

#### 完全リセット
```bash
# システム停止
./scripts/stop_production.sh

# プロセス強制終了
pkill -f "bsf-looptech"

# 一時ファイル削除
rm -rf temp/*

# 再起動
./scripts/start_production.sh
```

#### データ復旧
```bash
# バックアップからの復旧
./scripts/backup_system.sh restore

# または手動復旧
cp backup/latest_backup.tar.gz ./
tar -xzf latest_backup.tar.gz
```

## 📈 パフォーマンス最適化

### リソース監視
```bash
# CPU・メモリ使用量確認
top -pid $(pgrep -f "uvicorn.*main:app")

# ディスク使用量確認
du -sh logs/ data/ model_registry/

# プロセス一覧
ps aux | grep bsf
```

### 最適化設定
```bash
# MLパイプライン調整
python scripts/ml_pipeline_manager.py configure

# データベース最適化
vacuum analyze;  # PostgreSQL
```

## 🔒 セキュリティ

### 証明書管理
```bash
# 証明書生成
python scripts/generate_mqtt_certs.py

# 証明書確認
openssl x509 -in certs/ca.crt -text -noout
```

### アクセス制御
```bash
# MQTTユーザー管理
python scripts/manage_mqtt_users.py

# APIキー管理
# Web UIで管理 (http://localhost:8000/docs)
```

## 🚨 緊急連絡先・サポート

### ログファイル場所
- アプリケーション: `logs/application.log`
- MQTT: `logs/mosquitto.log`
- MLパイプライン: `logs/ml_pipeline.log`
- システム: `logs/system.log`

### 設定ファイル場所
- メイン設定: `.env`
- データベース: `alembic.ini`
- MQTT: `certs/mosquitto.conf`

### バックアップ場所
- ローカル: `backup/`
- 外部: 設定による

## 📞 よく使うコマンド一覧

```bash
# === 基本操作 ===
./scripts/bsf_manager.sh status     # ステータス確認
./scripts/bsf_manager.sh start      # 起動
./scripts/bsf_manager.sh stop       # 停止
./scripts/bsf_manager.sh restart    # 再起動

# === ログ確認 ===
./scripts/bsf_manager.sh logs       # ログ一覧
tail -f logs/application.log        # リアルタイムログ

# === トラブル対応 ===
./scripts/status_production.sh      # 詳細診断
./scripts/restart_production.sh     # 安全な再起動

# === 管理作業 ===
./scripts/bsf_manager.sh backup     # バックアップ
./install.sh                        # 再インストール
./uninstall.sh                      # アンインストール
```

---

**注意**: 本番環境での操作は慎重に行ってください。不明な点がある場合は、まずテスト環境で確認することを推奨します。