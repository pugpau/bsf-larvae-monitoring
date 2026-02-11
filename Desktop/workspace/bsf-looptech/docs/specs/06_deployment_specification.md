# BSF-LoopTech デプロイメント仕様書

## バージョン情報
- **ドキュメントバージョン**: 1.0.0
- **最終更新日**: 2025-10-01
- **対象システム**: BSF-LoopTech v0.1.0

---

## 目次
1. [デプロイメント概要](#1-デプロイメント概要)
2. [システム要件](#2-システム要件)
3. [インストール手順](#3-インストール手順)
4. [本番環境セットアップ](#4-本番環境セットアップ)
5. [起動・停止・再起動](#5-起動停止再起動)
6. [バックアップ・復元](#6-バックアップ復元)
7. [監視・ログ管理](#7-監視ログ管理)
8. [トラブルシューティング](#8-トラブルシューティング)
9. [セキュリティ設定](#9-セキュリティ設定)
10. [スケーリング・最適化](#10-スケーリング最適化)

---

## 1. デプロイメント概要

### 1.1 デプロイメント方式

BSF-LoopTechは以下の3つのデプロイメント方式をサポートしています：

| 方式 | 環境 | 用途 | 難易度 |
|------|------|------|--------|
| **ローカル開発** | macOS (開発機) | 開発・テスト | ⭐ 易 |
| **オンプレミス本番** | macOS (専用マシン) | 小規模本番運用 | ⭐⭐ 中 |
| **クラウドデプロイ** | AWS/Azure/GCP | 大規模本番運用 | ⭐⭐⭐ 難 |

### 1.2 アーキテクチャ構成

```
┌─────────────────────────────────────────────────────────┐
│              ロードバランサー (将来対応)                   │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
┌───────▼────────┐                 ┌────────▼───────┐
│  Frontend      │                 │  FastAPI       │
│  (React)       │◄───REST/WS─────►│  Backend       │
│  Port: 3000    │                 │  Port: 8000    │
└────────────────┘                 └────────┬───────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
            ┌───────▼────────┐     ┌───────▼────────┐    ┌────────▼───────┐
            │  PostgreSQL    │     │  InfluxDB      │    │  MQTT Broker   │
            │  Port: 5432    │     │  Port: 8086    │    │  Port: 8883    │
            │  (メタデータ)   │     │  (時系列)       │    │  (TLS有効)      │
            └────────────────┘     └────────────────┘    └────────────────┘
                                                                  │
                                                        ┌─────────▼─────────┐
                                                        │  M5StickC         │
                                                        │  IoTセンサー群     │
                                                        └───────────────────┘
```

### 1.3 デプロイメントコンポーネント

| コンポーネント | 技術 | デプロイ方式 |
|--------------|------|------------|
| FastAPI バックエンド | Python 3.10+ + Uvicorn | ネイティブプロセス / Docker |
| React フロントエンド | Node.js 18+ | ビルド済み静的ファイル / Docker |
| PostgreSQL | PostgreSQL 14 | Homebrew / Docker |
| InfluxDB | InfluxDB 2.7 | Homebrew / Docker |
| MQTT Broker | Mosquitto 2.0 | Homebrew / Docker |
| ML スケジューラー | Python バックグラウンド | ネイティブプロセス |

---

## 2. システム要件

### 2.1 ハードウェア要件

#### 最小要件（開発環境）
- **CPU**: 2コア以上
- **RAM**: 4GB以上
- **ストレージ**: 10GB以上の空き容量
- **ネットワーク**: WiFi/有線LAN接続

#### 推奨要件（本番環境）
- **CPU**: 4コア以上（Apple M1/M2推奨）
- **RAM**: 8GB以上（16GB推奨）
- **ストレージ**: 50GB以上の空き容量（SSD推奨）
- **ネットワーク**: 安定した有線LAN接続

#### 大規模環境要件
- **CPU**: 8コア以上
- **RAM**: 16GB以上
- **ストレージ**: 100GB以上（データ保持期間により増加）
- **外部ストレージ**: バックアップ用外付けHDD/SSD

### 2.2 ソフトウェア要件

#### オペレーティングシステム
- **macOS**: 11.0 (Big Sur) 以降
  - Apple Silicon (M1/M2) 対応
  - Intel Mac 対応
- **Linux**: Ubuntu 20.04 LTS 以降（将来対応）

#### 必須ソフトウェア
- **Homebrew**: 最新版
- **Python**: 3.10 以降
- **Node.js**: 18.x 以降
- **Git**: 2.30 以降

#### データベース
- **PostgreSQL**: 14 以降
- **InfluxDB**: 2.7 以降

#### その他
- **OpenSSL**: 1.1.1 以降（TLS証明書生成用）
- **Mosquitto**: 2.0 以降

---

## 3. インストール手順

### 3.1 クイックスタート（自動インストール）

```bash
# 1. リポジトリクローン
git clone https://github.com/your-org/bsf-looptech.git
cd bsf-looptech

# 2. インストーラー実行（対話型）
chmod +x install.sh
./install.sh
```

インストーラーは以下の選択肢を提供します：
- ✅ **フルインストール**（推奨）- 全機能を含む完全セットアップ
- ⚡ **軽量インストール** - 基本機能のみ
- 🔧 **カスタムインストール** - 個別に機能選択
- 🧪 **開発者インストール** - 開発・テスト環境向け

### 3.2 手動インストール

#### ステップ1: Homebrew依存関係インストール

```bash
# Homebrewパッケージインストール
brew install postgresql@14
brew install influxdb
brew install mosquitto
brew install openssl
brew install git

# サービス起動
brew services start postgresql@14
brew services start influxdb
brew services start mosquitto
```

#### ステップ2: Python環境セットアップ

```bash
# Python仮想環境作成
python3 -m venv venv
source venv/bin/activate

# Python依存関係インストール
pip install --upgrade pip
pip install -r requirements.txt
```

#### ステップ3: Node.js環境セットアップ

```bash
cd frontend

# Node.js依存関係インストール
npm install

# フロントエンドビルド
npm run build

cd ..
```

#### ステップ4: データベース初期化

```bash
# PostgreSQLデータベース作成
createdb bsf_system

# ユーザー作成と権限付与
psql postgres << EOF
CREATE USER bsf_user WITH PASSWORD 'bsf_password';
GRANT ALL PRIVILEGES ON DATABASE bsf_system TO bsf_user;
\q
EOF

# データベースマイグレーション実行
alembic upgrade head
```

#### ステップ5: InfluxDB初期設定

```bash
# InfluxDB Web UIにアクセス
open http://localhost:8086

# 初期セットアップ手順（Web UI）:
# 1. ユーザー名: admin
# 2. パスワード: (安全なパスワード)
# 3. Organization: bsf_org
# 4. Bucket: bsf_data
# 5. API Token生成（コピーして.envに保存）
```

#### ステップ6: 環境変数設定

```bash
# .envファイル作成
cp .env.production .env

# .envファイル編集
vim .env
```

`.env`ファイル例：
```bash
# データベース
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=bsf_user
POSTGRES_PASSWORD=bsf_password
POSTGRES_DB=bsf_system

# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=YOUR_INFLUXDB_TOKEN_HERE
INFLUXDB_ORG=bsf_org
INFLUXDB_BUCKET=bsf_data

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=8883
MQTT_TLS_ENABLED=true

# セキュリティ
SECRET_KEY=$(openssl rand -base64 32)
```

#### ステップ7: TLS証明書生成

```bash
# MQTT TLS証明書生成
python scripts/generate_mqtt_certs.py

# 生成される証明書:
# - certs/ca.crt        (CA証明書)
# - certs/ca.key        (CA秘密鍵)
# - certs/server.crt    (サーバー証明書)
# - certs/server.key    (サーバー秘密鍵)
# - certs/mqtt-client.crt  (クライアント証明書)
# - certs/mqtt-client.key  (クライアント秘密鍵)
```

---

## 4. 本番環境セットアップ

### 4.1 本番環境設定ファイル

本番環境では`.env.production`を使用します：

```bash
# 本番環境設定ファイルコピー
cp .env.production .env

# 設定編集
vim .env
```

**重要な本番設定項目**：
- `SECRET_KEY`: 強力なランダム文字列に変更
- `LOG_LEVEL`: `INFO`に設定（本番）、`DEBUG`は開発時のみ
- `INFLUXDB_TOKEN`: InfluxDBで生成したトークン
- `MQTT_PASSWORD`: 強力なパスワードに変更

### 4.2 管理者ユーザー作成

```bash
# 管理者ユーザー作成（デフォルト）
python scripts/create_admin_user.py --default

# カスタム管理者ユーザー作成
python scripts/create_admin_user.py \
  --username admin \
  --email admin@example.com \
  --password secure_password
```

### 4.3 ディレクトリ構成

```bash
# 必要なディレクトリを作成
mkdir -p logs data backup temp model_registry

# 権限設定
chmod 755 logs data backup temp model_registry
```

ディレクトリの用途：
- `logs/` - アプリケーションログ、MQTTログ、MLログ
- `data/` - 一時データ、キャッシュ
- `backup/` - データベースバックアップ
- `temp/` - 一時ファイル、プロセスPIDファイル
- `model_registry/` - 機械学習モデル保存

---

## 5. 起動・停止・再起動

### 5.1 本番環境起動

```bash
# 本番環境起動スクリプト実行
./scripts/start_production.sh
```

**起動プロセス**：
1. ✅ 環境確認（Python仮想環境、ディレクトリ）
2. ✅ データベース準備（PostgreSQL、InfluxDB起動）
3. ✅ MQTTブローカー起動（TLS対応）
4. ✅ ログシステム準備
5. ✅ MLパイプラインスケジューラー起動
6. ✅ FastAPIアプリケーション起動
7. ✅ 起動確認とヘルスチェック

**起動後のアクセス情報**：
- Web API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MQTT Broker (TLS): localhost:8883
- MQTT Standard: localhost:1883

### 5.2 ステータス確認

```bash
# システムステータス確認
./scripts/status_production.sh
```

**確認内容**：
- プロセス実行状態（FastAPI、MLスケジューラー、MQTT）
- データベース接続状態
- ログファイルサイズ
- ディスク使用量
- 最終起動時刻

### 5.3 本番環境停止

```bash
# 本番環境停止スクリプト実行
./scripts/stop_production.sh
```

**停止プロセス**：
1. ✅ FastAPIアプリケーション停止
2. ✅ MLパイプラインスケジューラー停止
3. ✅ MQTTブローカー停止
4. ✅ 残存プロセス確認と停止
5. ✅ 一時ファイルクリーンアップ
6. ✅ 停止ログ記録

**注意**: PostgreSQL、InfluxDBは他のアプリケーションでも使用される可能性があるため、デフォルトでは停止しません。

### 5.4 再起動

```bash
# 本番環境再起動
./scripts/restart_production.sh

# または、停止→起動を手動実行
./scripts/stop_production.sh
./scripts/start_production.sh
```

### 5.5 サービス管理（macOS LaunchAgent）

自動起動設定を行った場合：

```bash
# サービスステータス確認
launchctl list | grep bsf-looptech

# サービス手動起動
launchctl load ~/Library/LaunchAgents/com.bsf-looptech.production.plist

# サービス手動停止
launchctl unload ~/Library/LaunchAgents/com.bsf-looptech.production.plist
```

---

## 6. バックアップ・復元

### 6.1 バックアップの種類

| バックアップタイプ | 説明 | 実行頻度 | 保持期間 |
|-----------------|------|---------|---------|
| **完全バックアップ** | 全データ・設定のバックアップ | 週1回 | 30日 |
| **増分バックアップ** | 変更分のみのバックアップ | 毎日 | 7日 |
| **データベースバックアップ** | DBのみのバックアップ | 毎日 | 14日 |
| **ファイルバックアップ** | ログ・モデル・設定ファイル | 毎日 | 30日 |

### 6.2 バックアップ実行

```bash
# 完全バックアップ実行
./scripts/backup_system.sh full

# 増分バックアップ実行
./scripts/backup_system.sh incremental

# データベースのみバックアップ
./scripts/backup_system.sh database

# ファイルのみバックアップ
./scripts/backup_system.sh files
```

### 6.3 バックアップ統計確認

```bash
# バックアップ統計表示
./scripts/backup_system.sh stats
```

出力例：
```
バックアップ統計:
  ローカルバックアップ: 12 個 (2.3GB)
  外部バックアップ: 5 個 (1.8GB)
  最新バックアップ: 20251001_090000_backup.tar.gz (2025-10-01 09:00)
```

### 6.4 バックアップ対象

**含まれるもの**：
- ✅ ログファイル (`logs/`)
- ✅ データファイル (`data/`)
- ✅ MLモデル (`model_registry/`)
- ✅ 証明書 (`certs/`)
- ✅ 設定ファイル (`.env`, `alembic/`)
- ✅ PostgreSQLデータベースダンプ
- ✅ InfluxDB設定情報

**含まれないもの**：
- ❌ Python仮想環境 (`venv/`)
- ❌ Node.jsモジュール (`frontend/node_modules/`)
- ❌ 一時ファイル (`temp/`)
- ❌ Gitリポジトリ (`.git/`)

### 6.5 バックアップ復元

```bash
# バックアップファイルを指定して復元
./scripts/backup_system.sh restore backup/20251001_090000_backup.tar.gz
```

**復元プロセス**：
1. ⚠️ 警告確認（現在のデータが上書きされます）
2. バックアップファイルの展開
3. ファイル復元
4. データベース復元は手動実行が必要

**データベース手動復元**：
```bash
# PostgreSQL復元
psql -h localhost -U bsf_user -d bsf_system < backup/20251001_090000/databases/postgresql_backup_20251001_090000.sql

# InfluxDB復元
# InfluxDB Web UIから手動インポート
```

### 6.6 自動バックアップ設定

crontabによる定期実行設定：

```bash
# crontab編集
crontab -e

# 以下を追加
# 完全バックアップ: 毎週月曜日 午前3時
0 3 * * 1 /Users/tonton/Desktop/workspace/bsf-looptech/scripts/backup_system.sh full

# 増分バックアップ: 毎日 午前1時
0 1 * * * /Users/tonton/Desktop/workspace/bsf-looptech/scripts/backup_system.sh incremental
```

---

## 7. 監視・ログ管理

### 7.1 ログファイル一覧

| ログファイル | 内容 | 場所 |
|------------|------|------|
| `application.log` | FastAPIアプリケーションログ | `logs/` |
| `mqtt.log` | MQTTブローカーログ | `logs/` |
| `mosquitto.log` | Mosquitto詳細ログ | `logs/` |
| `ml_pipeline.log` | ML学習・予測ログ | `logs/` |
| `system.log` | システム起動・停止ログ | `logs/` |
| `backup_history.log` | バックアップ履歴 | `backup/` |

### 7.2 ログ監視

```bash
# アプリケーションログのリアルタイム監視
tail -f logs/application.log

# MQTTログの監視
tail -f logs/mqtt.log

# MLパイプラインログの監視
tail -f logs/ml_pipeline.log

# すべてのログを一括監視
tail -f logs/*.log
```

### 7.3 ログローテーション

```bash
# ログローテーションスクリプト実行
./scripts/rotate_logs.sh
```

**ローテーション設定**：
- サイズ閾値: 100MB超過時
- 保持期間: 30日
- 圧縮形式: gzip

### 7.4 システムモニタリング

```bash
# システムモニタースクリプト実行
./scripts/system_monitor.sh
```

**監視項目**：
- CPU使用率
- メモリ使用率
- ディスク使用率
- プロセス実行状態
- ネットワーク接続
- データベース接続数
- MQTT接続クライアント数

### 7.5 ヘルスチェック

```bash
# HTTPヘルスチェック
curl http://localhost:8000/health

# レスポンス例
{
  "status": "healthy",
  "timestamp": "2025-10-01T12:00:00Z",
  "services": {
    "database": "connected",
    "influxdb": "connected",
    "mqtt": "connected"
  }
}
```

### 7.6 アラート設定

本番環境では以下の条件でアラートを発生させることを推奨：
- ❌ APIヘルスチェック失敗
- ❌ データベース接続エラー
- ❌ ディスク使用率 > 90%
- ❌ メモリ使用率 > 95%
- ❌ センサーデータ受信なし（30分以上）

---

## 8. トラブルシューティング

### 8.1 起動エラー

#### エラー: "Python仮想環境が見つかりません"

**原因**: Python仮想環境が作成されていない

**解決方法**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### エラー: "PostgreSQL接続エラー"

**原因**: PostgreSQLが起動していない、または認証エラー

**解決方法**:
```bash
# PostgreSQL起動確認
brew services list | grep postgresql

# 起動していない場合
brew services start postgresql@14

# 接続テスト
psql -h localhost -U bsf_user -d bsf_system
```

#### エラー: "MQTT TLS接続失敗"

**原因**: TLS証明書が生成されていない、または証明書パスが間違っている

**解決方法**:
```bash
# 証明書生成
python scripts/generate_mqtt_certs.py

# 証明書確認
ls -l certs/

# 証明書テスト
mosquitto_pub -h localhost -p 8883 --cafile certs/ca.crt -t "test" -m "test"
```

### 8.2 パフォーマンス問題

#### 問題: APIレスポンスが遅い

**診断**:
```bash
# プロセスリソース確認
top -o cpu

# ログ確認
tail -n 100 logs/application.log
```

**対策**:
- データベース接続プール設定の調整
- InfluxDBクエリの最適化
- キャッシング機能の有効化

#### 問題: メモリ使用量が高い

**診断**:
```bash
# メモリ使用状況確認
ps aux | grep -E 'uvicorn|python'
```

**対策**:
- MLモデルのメモリ使用量削減
- ワーカープロセス数の調整
- ログレベルの見直し

### 8.3 データベース問題

#### 問題: PostgreSQL接続プール枯渇

**診断**:
```bash
# 接続数確認
psql -h localhost -U bsf_user -d bsf_system -c "SELECT count(*) FROM pg_stat_activity;"
```

**対策**:
- `DATABASE_URL`の接続プールサイズ増加
- 不要な接続のクローズ確認

#### 問題: InfluxDBデータ書き込みエラー

**診断**:
```bash
# InfluxDB接続テスト
curl http://localhost:8086/health

# InfluxDBログ確認
tail -f /opt/homebrew/var/log/influxdb.log
```

**対策**:
- トークンの確認
- Organization/Bucket名の確認
- InfluxDB再起動

### 8.4 MQTT問題

#### 問題: M5StickCがMQTTに接続できない

**診断**:
```bash
# MQTTブローカーログ確認
tail -f logs/mosquitto.log

# MQTT接続テスト
mosquitto_sub -h localhost -p 8883 --cafile certs/ca.crt -t "#" -v
```

**対策**:
- WiFi接続の確認
- MQTTブローカーIPアドレスの確認
- TLS証明書の有効期限確認
- ファイアウォール設定の確認

### 8.5 よくあるエラーメッセージ

| エラーメッセージ | 原因 | 解決方法 |
|---------------|------|---------|
| `Port 8000 already in use` | ポート競合 | 既存プロセスを終了、または別ポートを使用 |
| `Database connection refused` | DB未起動 | `brew services start postgresql` |
| `InfluxDB token invalid` | トークン間違い | `.env`のトークン確認 |
| `MQTT certificate verification failed` | 証明書エラー | 証明書再生成 |
| `ModuleNotFoundError` | Python依存関係不足 | `pip install -r requirements.txt` |

---

## 9. セキュリティ設定

### 9.1 TLS/SSL設定

#### MQTT TLS証明書生成

```bash
# 証明書生成スクリプト実行
python scripts/generate_mqtt_certs.py

# カスタム設定で生成
python scripts/generate_mqtt_certs.py \
  --country JP \
  --state Tokyo \
  --city Chiyoda \
  --organization "BSF-LoopTech" \
  --validity 365
```

**証明書の有効期限管理**:
```bash
# 証明書有効期限確認
openssl x509 -in certs/server.crt -noout -enddate

# 有効期限切れ前に再生成を推奨（90日前）
```

### 9.2 認証設定

#### JWT設定

`.env`ファイル設定：
```bash
SECRET_KEY=$(openssl rand -base64 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### MQTT認証

```bash
# MQTTユーザー管理
python scripts/manage_mqtt_users.py add --username sensor01 --password secure_password
python scripts/manage_mqtt_users.py list
python scripts/manage_mqtt_users.py delete --username sensor01
```

### 9.3 ファイアウォール設定

macOS標準ファイアウォール設定：
```bash
# ファイアウォール有効化
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on

# 特定ポート許可
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/uvicorn
```

### 9.4 セキュリティベストプラクティス

1. **パスワード強度**
   - 最低12文字以上
   - 大文字・小文字・数字・記号を含む
   - デフォルトパスワードは必ず変更

2. **認証トークン管理**
   - SECRET_KEYは環境ごとに変える
   - JWTトークン有効期限は30分以内
   - InfluxDBトークンは読み取り専用権限を推奨

3. **ネットワークセキュリティ**
   - MQTTは必ずTLS有効化
   - 本番環境では外部公開ポートを最小限に
   - VPN経由でのアクセスを推奨

4. **監査ログ**
   - 認証失敗ログの監視
   - 異常なAPIアクセスパターンの検知
   - 定期的なセキュリティログレビュー

---

## 10. スケーリング・最適化

### 10.1 水平スケーリング

#### センサーノード拡張

初期15エリア → 最大1000エリア対応：

```bash
# センサーノード追加設定
# 1. M5StickC ファームウェアに固有のデバイスIDを設定
# 2. MQTTトピック命名規則に従う: bsf/{farm_id}/{device_type}/{device_id}
# 3. データベースにセンサー登録

python scripts/register_sensor.py \
  --device-id m5stick-temp-050 \
  --farm-id farm001 \
  --device-type temperature \
  --location "エリアB-5"
```

#### バックエンドスケーリング

Uvicornワーカー数の調整：
```bash
# ワーカー数を増やしてスケール
uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop
```

### 10.2 垂直スケーリング

#### データベース最適化

**PostgreSQL**:
```bash
# PostgreSQL設定調整 (postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
max_connections = 100
```

**InfluxDB**:
```bash
# InfluxDB書き込みバッファ最適化
# config.toml
[data]
  cache-max-memory-size = "1g"
  cache-snapshot-memory-size = "25m"
```

#### メモリキャッシング

```bash
# Redis導入（将来対応）
brew install redis
brew services start redis

# .envにRedis設定追加
REDIS_URL=redis://localhost:6379/0
```

### 10.3 パフォーマンス最適化

#### APIレスポンス最適化

1. **データベースクエリ最適化**
   - インデックス作成
   - N+1問題の回避
   - クエリ結果のキャッシング

2. **InfluxDBクエリ最適化**
   - 時間範囲を適切に制限
   - ダウンサンプリングの活用
   - 集計クエリの事前計算

3. **WebSocket最適化**
   - 送信頻度の調整（5秒間隔推奨）
   - データ圧縮の有効化
   - 接続プールの管理

#### フロントエンド最適化

```bash
# 本番ビルド最適化
cd frontend
npm run build

# ビルド最適化設定（package.json）
"build": "GENERATE_SOURCEMAP=false react-scripts build"
```

### 10.4 リソース監視と自動スケーリング

```bash
# システムリソース監視スクリプト
./scripts/system_monitor.sh

# 閾値ベースの自動アクション設定（cron）
*/5 * * * * /path/to/bsf-looptech/scripts/auto_scale.sh
```

**自動スケーリング条件例**:
- CPU使用率 > 80% → ワーカー数増加
- メモリ使用率 > 85% → 古いログのアーカイブ
- ディスク使用率 > 90% → 古いデータの削除・圧縮

---

## 11. 付録

### 11.1 スクリプト一覧

| スクリプト | 用途 | 使用頻度 |
|----------|------|---------|
| `install.sh` | 対話型インストーラー | 初回のみ |
| `start_production.sh` | 本番環境起動 | 毎回起動時 |
| `stop_production.sh` | 本番環境停止 | 毎回停止時 |
| `restart_production.sh` | 本番環境再起動 | 更新時 |
| `status_production.sh` | ステータス確認 | 随時 |
| `backup_system.sh` | バックアップ実行 | 毎日（自動） |
| `system_monitor.sh` | システム監視 | 5分ごと（自動） |
| `rotate_logs.sh` | ログローテーション | 毎週（自動） |
| `generate_mqtt_certs.py` | MQTT証明書生成 | 初回・更新時 |
| `create_admin_user.py` | 管理者作成 | 初回のみ |
| `ml_pipeline_manager.py` | ML管理 | 随時 |

### 11.2 環境変数一覧

**データベース関連**:
```bash
DATABASE_URL=postgresql+asyncpg://bsf_user:bsf_password@localhost:5432/bsf_system
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=bsf_user
POSTGRES_PASSWORD=bsf_password
POSTGRES_DB=bsf_system
```

**InfluxDB関連**:
```bash
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=bsf_org
INFLUXDB_BUCKET=bsf_data
```

**MQTT関連**:
```bash
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=8883
MQTT_TLS_ENABLED=true
MQTT_CA_CERTS=certs/ca.crt
MQTT_CLIENT_CERT=certs/mqtt-client.crt
MQTT_CLIENT_KEY=certs/mqtt-client.key
MQTT_USERNAME=bsf-backend
MQTT_PASSWORD=secure_mqtt_password
```

**アプリケーション関連**:
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here
API_BASE_URL=http://backend:8000
CORS_ORIGINS=["http://localhost:3000"]
```

**機械学習関連**:
```bash
ML_MODEL_PATH=/app/model_registry/models
ML_TRAINING_ENABLED=true
ML_PREDICTION_THRESHOLD=0.85
```

### 11.3 ポート一覧

| ポート | サービス | プロトコル | 用途 |
|-------|---------|-----------|------|
| 3000 | React Frontend | HTTP | フロントエンドUI |
| 8000 | FastAPI Backend | HTTP | REST API / WebSocket |
| 5432 | PostgreSQL | TCP | メタデータベース |
| 8086 | InfluxDB | HTTP | 時系列データベース |
| 1883 | Mosquitto MQTT | TCP | MQTT (非暗号化) |
| 8883 | Mosquitto MQTT | TCP | MQTT (TLS/SSL) |
| 9001 | Mosquitto WebSocket | WS | MQTT over WebSocket |

### 11.4 システム図（詳細）

```
┌──────────────────────────────────────────────────────────────────────┐
│                        BSF-LoopTech System                           │
│                                                                      │
│  ┌────────────┐       ┌──────────────┐       ┌──────────────┐     │
│  │ M5StickC   │──────►│ MQTT Broker  │◄─────►│  Backend     │     │
│  │ Sensors    │  WiFi │ (Mosquitto)  │ Sub   │  (FastAPI)   │     │
│  │ (15-1000)  │       │  Port: 8883  │       │  Port: 8000  │     │
│  └────────────┘       └──────────────┘       └──────┬───────┘     │
│                                                      │              │
│                                   ┌──────────────────┼──────┐      │
│                                   │                  │      │      │
│                           ┌───────▼──────┐  ┌───────▼──────┐      │
│                           │ PostgreSQL   │  │  InfluxDB    │      │
│                           │ (Metadata)   │  │ (Time-series)│      │
│                           │ Port: 5432   │  │ Port: 8086   │      │
│                           └──────────────┘  └──────────────┘      │
│                                                                     │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐  │
│  │  Frontend    │◄─────►│   Backend    │◄─────►│  ML Pipeline │  │
│  │  (React)     │ REST/ │   (FastAPI)  │       │  Scheduler   │  │
│  │  Port: 3000  │  WS   │  Port: 8000  │       │ (Background) │  │
│  └──────────────┘       └──────────────┘       └──────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Monitoring & Logging System                     │ │
│  │  - Application Logs                                          │ │
│  │  - MQTT Logs                                                 │ │
│  │  - ML Pipeline Logs                                          │ │
│  │  - System Health Monitoring                                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 12. まとめ

### 12.1 運用チェックリスト

#### 日次タスク
- [ ] システムステータス確認 (`./scripts/status_production.sh`)
- [ ] ログファイル確認（エラー・警告の有無）
- [ ] センサーデータ受信確認
- [ ] 自動バックアップ完了確認

#### 週次タスク
- [ ] 完全バックアップ実行確認
- [ ] ディスク使用量確認
- [ ] パフォーマンスレビュー
- [ ] セキュリティログレビュー

#### 月次タスク
- [ ] バックアップ復元テスト
- [ ] 依存パッケージ更新確認
- [ ] TLS証明書有効期限確認
- [ ] システムリソース最適化

### 12.2 緊急時対応

**システム障害時**:
1. ログ確認 (`tail -f logs/application.log`)
2. プロセス状態確認 (`./scripts/status_production.sh`)
3. 必要に応じて再起動 (`./scripts/restart_production.sh`)
4. バックアップから復元（データ損失時）

**データベース障害時**:
1. データベース接続テスト
2. 最新バックアップから復元
3. データ整合性確認

**センサー通信障害時**:
1. WiFi接続確認
2. MQTTブローカーログ確認
3. センサーデバイス再起動

### 12.3 サポート・問い合わせ

技術的な問題が発生した場合：
- **GitHub Issues**: プロジェクトリポジトリにIssue作成
- **ドキュメント**: `docs/specs/` 配下の仕様書を参照
- **会話履歴**: `kaiwa.md` で過去の相談内容を確認

---

**ドキュメント終了**
