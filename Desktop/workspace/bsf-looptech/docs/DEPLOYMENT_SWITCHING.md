# BSF-LoopTech デプロイ環境切り替えガイド

このドキュメントでは、クラウド環境（Render）とオンプレミス環境の切り替え方法を説明します。

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────────┐
│                     同一コードベース                              │
│                   (環境変数で切り替え)                            │
├─────────────────────────┬───────────────────────────────────────┤
│    クラウド環境          │        オンプレミス環境                 │
│    (Render)             │        (Docker Compose)               │
├─────────────────────────┼───────────────────────────────────────┤
│ FastAPI: Render Web     │ FastAPI: Docker Container            │
│ PostgreSQL: Supabase    │ PostgreSQL: Docker Container         │
│ InfluxDB: InfluxDB Cloud│ InfluxDB: Docker Container           │
│ MQTT: HiveMQ Cloud      │ MQTT: Mosquitto Container            │
│ Frontend: Vercel        │ Frontend: Docker/Nginx               │
└─────────────────────────┴───────────────────────────────────────┘
```

## クラウド環境 → オンプレミスへの切り替え

### 1. 必要なファイル

オンプレミス環境に必要なファイルは既にリポジトリに含まれています：

```bash
# Docker設定
docker-compose.yml          # メイン構成
docker-compose.prod.yml     # 本番環境用
Dockerfile.backend          # バックエンドイメージ

# 環境変数
.env.local                  # ローカル環境変数テンプレート
```

### 2. 環境変数の設定

```bash
# .env.local を編集（オンプレミス用）
cp .env.local.example .env.local

# 主要な設定項目
DATABASE_URL=postgresql+asyncpg://bsf_user:bsf_password@localhost:5432/bsf_system
INFLUXDB_URL=http://localhost:8086
MQTT_BROKER_HOST=localhost
```

### 3. 起動コマンド

```bash
# 全サービス起動
docker-compose up -d

# 特定サービスのみ起動
docker-compose up -d postgres influxdb mosquitto backend

# ログ確認
docker-compose logs -f backend

# 停止
docker-compose down
```

### 4. データ移行（クラウド → オンプレミス）

```bash
# PostgreSQLデータのエクスポート（Supabaseから）
pg_dump -h aws-0-ap-northeast-1.pooler.supabase.com \
  -U postgres.xxxxx -d postgres > backup.sql

# オンプレミスPostgreSQLへインポート
docker exec -i bsf-postgres psql -U bsf_user -d bsf_system < backup.sql

# InfluxDBデータのエクスポート
influx backup /path/to/backup --host https://your-influxdb-cloud.com \
  --token your-token --org your-org

# オンプレミスInfluxDBへインポート
docker exec -it bsf-influxdb influx restore /path/to/backup
```

## オンプレミス → クラウド環境への切り替え

### 1. 環境変数の更新

Render Dashboard で以下の環境変数を設定：

| 変数名 | 値 |
|--------|-----|
| DATABASE_URL | Supabase接続文字列 |
| INFLUXDB_URL | InfluxDB CloudのURL |
| MQTT_BROKER_HOST | HiveMQ Cloudのホスト |
| CORS_ORIGINS | VercelのフロントエンドURL |

### 2. フロントエンドの更新

```bash
# Vercel環境変数を更新
NEXT_PUBLIC_API_BASE_URL=https://bsf-looptech-api.onrender.com
```

### 3. データ移行（オンプレミス → クラウド）

```bash
# PostgreSQLデータのエクスポート
docker exec -t bsf-postgres pg_dump -U bsf_user bsf_system > backup.sql

# Supabaseへインポート
psql -h aws-0-ap-northeast-1.pooler.supabase.com \
  -U postgres.xxxxx -d postgres < backup.sql
```

## 環境変数比較表

| 設定項目 | オンプレミス | クラウド（Render） |
|----------|-------------|-------------------|
| DATABASE_URL | `postgresql+asyncpg://bsf_user:bsf_password@localhost:5432/bsf_system` | `postgresql+asyncpg://postgres.xxx:@aws-xxx.supabase.com:5432/postgres` |
| INFLUXDB_URL | `http://localhost:8086` | `https://ap-northeast-1-1.aws.cloud2.influxdata.com` |
| MQTT_BROKER_HOST | `localhost` | `xxx.hivemq.cloud` |
| MQTT_BROKER_PORT | `1883` (非TLS) or `8883` (TLS) | `8883` (TLS必須) |
| MQTT_TLS_ENABLED | `false` (開発) / `true` (本番) | `true` |
| CORS_ORIGINS | `http://localhost:3000` | `https://your-app.vercel.app` |

## 切り替えチェックリスト

### クラウド → オンプレミス

- [ ] Docker/Docker Composeがインストールされている
- [ ] ポート 5432, 8086, 1883, 8883, 8000 が利用可能
- [ ] `.env.local` ファイルを更新
- [ ] SSL証明書を配置（TLS使用時）
- [ ] `docker-compose up -d` で起動
- [ ] ヘルスチェック確認: `curl http://localhost:8000/health`
- [ ] データ移行完了（必要な場合）

### オンプレミス → クラウド

- [ ] Render アカウント作成
- [ ] Supabase データベース準備
- [ ] InfluxDB Cloud アカウント作成
- [ ] HiveMQ Cloud アカウント作成
- [ ] Render 環境変数設定
- [ ] Vercel 環境変数更新
- [ ] デプロイ完了確認
- [ ] データ移行完了（必要な場合）

## トラブルシューティング

### オンプレミス環境

```bash
# コンテナ状態確認
docker-compose ps

# ログ確認
docker-compose logs backend
docker-compose logs postgres
docker-compose logs influxdb

# データベース接続テスト
docker exec -it bsf-postgres psql -U bsf_user -d bsf_system -c "SELECT 1;"

# InfluxDB接続テスト
docker exec -it bsf-influxdb influx ping
```

### クラウド環境

```bash
# Render ログ確認
# Render Dashboard > Services > bsf-looptech-api > Logs

# ヘルスチェック
curl https://bsf-looptech-api.onrender.com/health
```

## コスト比較

| 項目 | オンプレミス | クラウド（無料枠） | クラウド（有料） |
|------|-------------|-------------------|-----------------|
| サーバー | 自前ハードウェア | 無料 | ~$7/月 (Render) |
| PostgreSQL | 含む | Supabase無料枠 | ~$25/月 |
| InfluxDB | 含む | InfluxDB Cloud無料枠 | 使用量による |
| MQTT | 含む | HiveMQ Cloud無料枠 | ~$5/月 |
| **合計** | ハードウェア費のみ | **$0** | **~$37/月** |

## 推奨使用シナリオ

| シナリオ | 推奨環境 | 理由 |
|----------|---------|------|
| 開発・テスト | オンプレミス | コスト0、高速な反復 |
| デモ・PoC | クラウド（無料枠） | すぐに公開可能 |
| 小規模本番 | クラウド（有料） | 運用負荷低い |
| 大規模本番 | オンプレミス or ハイブリッド | コスト最適化、データ主権 |
