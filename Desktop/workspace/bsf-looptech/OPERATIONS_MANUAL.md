# BSF-LoopTech 運用マニュアル

## 目次

1. [システム概要](#1-システム概要)
2. [日常運用](#2-日常運用)
3. [Blue-Green デプロイ](#3-blue-green-デプロイ)
4. [バックアップ・リストア](#4-バックアップリストア)
5. [ML パイプライン管理](#5-ml-パイプライン管理)
6. [トラブルシューティング](#6-トラブルシューティング)
7. [緊急ロールバック](#7-緊急ロールバック)
8. [定期チェック](#8-定期チェック)
9. [SSL 証明書管理](#9-ssl-証明書管理)
10. [監視自動化](#10-監視自動化)
11. [シークレットローテーション](#11-シークレットローテーション)

---

## 1. システム概要

### アーキテクチャ

BSF-LoopTech は Docker Compose による 5 サービス構成です。

```
                           ┌──────────────────────┐
                           │   frontend-builder   │
                           │  (React 18 + nginx)  │
                           └──────────┬───────────┘
                                      │ static files
            ┌─────────────────────────▼──────────────────────────┐
            │                   router (nginx)                   │
            │          HTTP :3000 / HTTPS :443                   │
            │   ┌─────────────────────────────────────────────┐  │
            │   │  upstream: backend-blue OR backend-green    │  │
            │   └─────────────────────────────────────────────┘  │
            └──────┬──────────────────────────────┬──────────────┘
                   │                              │
        ┌──────────▼──────────┐      ┌────────────▼────────────┐
        │   backend-blue      │      │    backend-green        │
        │   (FastAPI :8000)   │      │    (FastAPI :8000)      │
        │   Active / Standby  │      │    Active / Standby     │
        └──────────┬──────────┘      └────────────┬────────────┘
                   │                              │
                   └──────────────┬───────────────┘
                                  │
                   ┌──────────────▼──────────────┐
                   │        postgres             │
                   │   (pgvector/pgvector:pg15)  │
                   │        port 5432            │
                   └─────────────────────────────┘
```

### エンドポイント一覧

| サービス | URL | 用途 |
|----------|-----|------|
| Web UI (HTTP) | http://localhost:3000 | フロントエンド |
| Web UI (HTTPS) | https://localhost | フロントエンド (SSL) |
| API (via router) | http://localhost:3000/api/v1 | REST API |
| Swagger UI | http://localhost:3000/api/v1/docs | API ドキュメント |
| Health | http://localhost:3000/health | ヘルスチェック (200=正常) |
| Ready | http://localhost:3000/ready | デプロイ用 (503=DB不可) |
| PostgreSQL | localhost:5432 | DB (コンテナ内) |

### 主要ファイル

| ファイル | 用途 |
|---------|------|
| `docker-compose.prod.yml` | 本番環境定義 |
| `.env.production` | 環境変数 |
| `config/active-slot` | アクティブスロット (blue/green) |
| `config/nginx-router.conf.template` | nginx 設定テンプレート |
| `scripts/deploy-blue-green.sh` | デプロイスクリプト |
| `scripts/backup_databases.sh` | DB バックアップ |
| `scripts/system_monitor.sh` | システム監視 |

---

## 2. 日常運用

### システム起動

```bash
# Docker Compose で全サービス起動
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 起動確認
docker compose -f docker-compose.prod.yml ps
```

### システム停止

```bash
docker compose -f docker-compose.prod.yml down
```

### 状態確認

```bash
# コンテナ状態
docker compose -f docker-compose.prod.yml ps

# Blue-Green デプロイ状態
./scripts/deploy-blue-green.sh status

# システム監視（手動実行）
./scripts/system_monitor.sh
```

### ヘルスチェック

```bash
# /health (200 = 正常, degraded でも 200)
curl -s http://localhost:3000/health | python3 -m json.tool

# /ready (200 = DB接続OK, 503 = DB不可)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ready
```

### ログ確認

```bash
# バックエンド (アクティブスロット)
docker compose -f docker-compose.prod.yml logs -f backend-blue
# or
docker compose -f docker-compose.prod.yml logs -f backend-green

# router (nginx)
docker compose -f docker-compose.prod.yml logs -f router

# PostgreSQL
docker compose -f docker-compose.prod.yml logs -f postgres

# 全サービス（直近100行）
docker compose -f docker-compose.prod.yml logs --tail=100
```

### 毎朝のチェックリスト

1. `./scripts/deploy-blue-green.sh status` でコンテナ状態確認
2. `curl -s http://localhost:3000/health` でヘルスチェック
3. `docker compose -f docker-compose.prod.yml logs --tail=50 | grep ERROR` でエラー確認
4. launchd ログ確認: `tail -20 logs/monitor_stdout.log`
5. バックアップ確認: `ls -lt ~/BSF_Backups/postgres/ | head -3`

---

## 3. Blue-Green デプロイ

### 概要

Blue-Green デプロイにより、ダウンタイムなしでバックエンドを更新できます。

- **blue**: `bsf-backend-blue` コンテナ
- **green**: `bsf-backend-green` コンテナ
- **active-slot**: `config/active-slot` ファイルで管理

### 初期化（初回のみ）

```bash
./scripts/deploy-blue-green.sh init
```

これにより:
1. Docker イメージをビルド
2. PostgreSQL + blue バックエンド + router を起動
3. `config/active-slot` に `blue` を書き込み
4. ヘルスチェック後、nginx 設定を生成

### 新バージョンのデプロイ

```bash
./scripts/deploy-blue-green.sh deploy
```

処理フロー:
1. 現在のアクティブスロットを確認（例: blue）
2. スタンバイスロット（例: green）のイメージをビルド
3. スタンバイスロットを起動
4. `/ready` エンドポイントでヘルスチェック
5. nginx 設定を切り替え、router をリロード
6. `config/active-slot` を更新
7. 旧スロットを停止

### ロールバック

```bash
./scripts/deploy-blue-green.sh rollback
```

前回のスロットに戻します。旧スロットのコンテナが残っている場合にのみ可能です。

### 状態確認

```bash
./scripts/deploy-blue-green.sh status
```

---

## 4. バックアップ・リストア

### 自動バックアップ

launchd により **毎日 3:00 AM JST** に自動実行されます。

- **設定ファイル**: `config/com.bsf-looptech.backup.plist`
- **スクリプト**: `scripts/backup_databases.sh`
- **保存先**: `~/BSF_Backups/postgres/`
- **形式**: `bsf_YYYYMMDD_HHMMSS.sql.gz` (gzip 圧縮)
- **保持期間**: 30日（古いファイルは自動削除）

### 手動バックアップ

```bash
./scripts/backup_databases.sh
```

### バックアップ確認

```bash
# 最新バックアップ
ls -lt ~/BSF_Backups/postgres/ | head -5

# バックアップサイズ
du -sh ~/BSF_Backups/postgres/

# launchd ログ
tail -20 logs/backup_stdout.log
```

### リストア手順

```bash
# 1. バックエンドを停止
docker compose -f docker-compose.prod.yml stop backend-blue backend-green

# 2. バックアップファイルを解凍してリストア
gunzip -c ~/BSF_Backups/postgres/bsf_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i bsf-postgres psql -U bsf_user -d postgres

# 3. バックエンドを再起動
docker compose -f docker-compose.prod.yml start backend-blue
# (または deploy-blue-green.sh deploy)
```

### launchd 登録

```bash
# バックアップの登録
cp config/com.bsf-looptech.backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.bsf-looptech.backup.plist

# 登録確認
launchctl list | grep bsf-looptech

# 手動トリガー（テスト用）
launchctl start com.bsf-looptech.backup
```

---

## 5. ML パイプライン管理

### バッチジョブ

APScheduler により 3 つの定期ジョブが自動実行されます（`BATCH_ENABLED=true` 時）。

| ジョブ | スケジュール | 内容 |
|--------|-------------|------|
| `daily_aggregation` | 毎日 03:00 | データ集計 |
| `weekly_ml_retrain` | 毎週日曜 02:00 | ML モデル再学習 |
| `monthly_report` | 毎月1日 04:00 | 月次レポート生成 |

### バッチ API

```bash
# ジョブ一覧
curl -s http://localhost:3000/api/v1/batch/jobs | python3 -m json.tool

# ジョブ手動実行
curl -X POST http://localhost:3000/api/v1/batch/jobs/weekly_ml_retrain/trigger

# ジョブ詳細
curl -s http://localhost:3000/api/v1/batch/jobs/daily_aggregation | python3 -m json.tool

# 実行ステータス
curl -s http://localhost:3000/api/v1/batch/status | python3 -m json.tool
```

### ML モデル管理

```bash
# モデル一覧
curl -s http://localhost:3000/api/v1/ml/models | python3 -m json.tool

# 手動学習
curl -X POST http://localhost:3000/api/v1/ml/train

# 予測精度確認
curl -s http://localhost:3000/api/v1/ml/accuracy | python3 -m json.tool
```

### KPI ダッシュボード

```bash
# リアルタイム KPI
curl -s http://localhost:3000/api/v1/kpi/realtime | python3 -m json.tool

# KPI トレンド
curl -s "http://localhost:3000/api/v1/kpi/trends?days=30" | python3 -m json.tool

# KPI アラート
curl -s http://localhost:3000/api/v1/kpi/alerts | python3 -m json.tool
```

---

## 6. トラブルシューティング

### コンテナが起動しない

```bash
# ログ確認
docker compose -f docker-compose.prod.yml logs backend-blue

# コンテナの詳細状態
docker inspect bsf-backend-blue | grep -A5 State

# イメージ再ビルド
docker compose -f docker-compose.prod.yml build backend-blue
docker compose -f docker-compose.prod.yml up -d backend-blue
```

### PostgreSQL 接続エラー

```bash
# PostgreSQL 接続確認
docker exec bsf-postgres pg_isready -U bsf_user -d bsf_system

# PostgreSQL ログ
docker compose -f docker-compose.prod.yml logs postgres

# DB サイズ確認
docker exec bsf-postgres psql -U bsf_user -d bsf_system \
  -c "SELECT pg_size_pretty(pg_database_size('bsf_system'));"

# アクティブ接続数
docker exec bsf-postgres psql -U bsf_user -d bsf_system \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname='bsf_system';"
```

### /health が degraded を返す

```bash
# DB 接続を確認
docker exec bsf-postgres pg_isready -U bsf_user -d bsf_system

# PostgreSQL コンテナ再起動
docker compose -f docker-compose.prod.yml restart postgres

# バックエンド再起動
docker compose -f docker-compose.prod.yml restart backend-blue
```

### フロントエンドが表示されない

```bash
# router ログ確認
docker compose -f docker-compose.prod.yml logs router

# nginx 設定検証
docker exec bsf-router nginx -t

# 静的ファイル確認
docker exec bsf-router ls /usr/share/nginx/html/index.html

# フロントエンド再ビルド
docker compose -f docker-compose.prod.yml build frontend-builder
docker compose -f docker-compose.prod.yml up -d frontend-builder router
```

### ディスク容量不足

```bash
# ディスク使用量
df -h /

# Docker リソース
docker system df

# 不要なイメージ・コンテナ削除
docker system prune -a --volumes

# 古いバックアップ手動削除
find ~/BSF_Backups/postgres -name "*.sql.gz" -mtime +14 -delete
```

### LLM/RAG チャットが動作しない

```bash
# LM Studio 稼働確認 (host.docker.internal)
curl -s http://localhost:1234/v1/models | python3 -m json.tool

# コンテナ内からの接続確認
docker exec bsf-backend-blue curl -s http://host.docker.internal:1234/v1/models

# .env.production の LLM 設定確認
grep LLM .env.production
```

---

## 7. 緊急ロールバック

### Blue-Green ロールバック

```bash
# 前のスロットに戻す
./scripts/deploy-blue-green.sh rollback
```

### コンテナ全停止

```bash
# 全サービス停止
docker compose -f docker-compose.prod.yml down

# データボリュームを保持したまま停止
docker compose -f docker-compose.prod.yml down  # (volumes は明示的に --volumes を付けない限り残る)
```

### データベース復旧

```bash
# 1. バックエンド停止
docker compose -f docker-compose.prod.yml stop backend-blue backend-green

# 2. 最新バックアップを確認
ls -lt ~/BSF_Backups/postgres/ | head -5

# 3. リストア
gunzip -c ~/BSF_Backups/postgres/bsf_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i bsf-postgres psql -U bsf_user -d postgres

# 4. バックエンド再起動
docker compose -f docker-compose.prod.yml start backend-blue
```

### 完全リセット（最後の手段）

```bash
# 全コンテナ+ボリューム削除
docker compose -f docker-compose.prod.yml down --volumes

# 再初期化
./scripts/deploy-blue-green.sh init
```

注意: `--volumes` を付けると PostgreSQL データも消えます。必ずバックアップを確認してから実行してください。

---

## 8. 定期チェック

### 日次

| 項目 | コマンド |
|------|---------|
| コンテナ状態 | `./scripts/deploy-blue-green.sh status` |
| ヘルスチェック | `curl -s http://localhost:3000/health` |
| エラーログ | `docker compose -f docker-compose.prod.yml logs --tail=50 \| grep ERROR` |
| バックアップ確認 | `ls -lt ~/BSF_Backups/postgres/ \| head -3` |
| ディスク容量 | `df -h /` |

### 週次

| 項目 | コマンド |
|------|---------|
| DB サイズ | `docker exec bsf-postgres psql -U bsf_user -d bsf_system -c "SELECT pg_size_pretty(pg_database_size('bsf_system'));"` |
| Docker リソース | `docker system df` |
| バックアップ総数 | `ls ~/BSF_Backups/postgres/*.sql.gz \| wc -l` |
| ML モデル精度 | `curl -s http://localhost:3000/api/v1/ml/accuracy` |
| KPI アラート | `curl -s http://localhost:3000/api/v1/kpi/alerts` |

### 月次

| 項目 | 内容 |
|------|------|
| PostgreSQL VACUUM | `docker exec bsf-postgres psql -U bsf_user -d bsf_system -c "VACUUM ANALYZE;"` |
| Docker イメージ整理 | `docker image prune -a` |
| SSL 証明書有効期限 | `openssl x509 -in config/ssl/server.crt -noout -enddate` |
| セキュリティ更新 | `pip list --outdated` (コンテナ内) |
| バックアップリストアテスト | テスト DB にリストアして検証 |

---

## 9. SSL 証明書管理

### 自己署名証明書の生成

```bash
# 初回生成
./scripts/generate_ssl_cert.sh

# カスタムホスト名で生成
./scripts/generate_ssl_cert.sh bsf-looptech.local
```

生成場所:
- 証明書: `config/ssl/server.crt`
- 秘密鍵: `config/ssl/server.key`

### 証明書情報の確認

```bash
# 有効期限確認
openssl x509 -in config/ssl/server.crt -noout -enddate

# 詳細情報
openssl x509 -in config/ssl/server.crt -noout -text

# SAN (Subject Alternative Name) 確認
openssl x509 -in config/ssl/server.crt -noout -ext subjectAltName
```

### 証明書の更新

```bash
# 1. 新しい証明書を生成
./scripts/generate_ssl_cert.sh

# 2. router をリロード
docker compose -f docker-compose.prod.yml exec router nginx -s reload
```

注意: 自己署名証明書のため、ブラウザで「安全でない接続」警告が表示されます。閉域ネットワーク用途では問題ありません。

---

## 10. 監視自動化

### launchd サービス一覧

| サービス | plist ファイル | スケジュール |
|---------|---------------|-------------|
| 本番環境起動 | `com.bsf-looptech.production` | システム起動時 |
| システム監視 | `com.bsf-looptech.monitor` | 30分ごと |
| DB バックアップ | `com.bsf-looptech.backup` | 毎日 3:00 AM |

### launchd 登録手順

```bash
# 全サービス登録
cp config/com.bsf-looptech.*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.bsf-looptech.production.plist
launchctl load ~/Library/LaunchAgents/com.bsf-looptech.monitor.plist
launchctl load ~/Library/LaunchAgents/com.bsf-looptech.backup.plist

# 登録確認
launchctl list | grep bsf-looptech
```

### launchd 解除

```bash
launchctl unload ~/Library/LaunchAgents/com.bsf-looptech.production.plist
launchctl unload ~/Library/LaunchAgents/com.bsf-looptech.monitor.plist
launchctl unload ~/Library/LaunchAgents/com.bsf-looptech.backup.plist
rm ~/Library/LaunchAgents/com.bsf-looptech.*.plist
```

### 監視ログ確認

```bash
# 監視ログ
tail -50 logs/monitor_stdout.log

# バックアップログ
tail -50 logs/backup_stdout.log

# launchd 起動ログ
tail -50 logs/launchd_stdout.log

# エラーログ
tail -50 logs/monitor_stderr.log
tail -50 logs/backup_stderr.log
tail -50 logs/launchd_stderr.log
```

### ログディレクトリ作成（初回のみ）

```bash
mkdir -p logs
```

---

## 付録: API エンドポイント一覧

### 認証

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/auth/login` | ログイン |
| POST | `/api/v1/auth/register` | ユーザー登録 |
| POST | `/api/v1/auth/refresh` | トークン更新 |

### 廃棄物管理

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/waste/records` | 搬入記録一覧 |
| POST | `/api/v1/waste/records` | 搬入記録作成 |
| POST | `/api/v1/waste/recommend` | AI 配合推薦 |

### マスタ管理

| メソッド | パス | 説明 |
|---------|------|------|
| GET/POST | `/api/v1/materials/suppliers` | 搬入業者 |
| GET/POST | `/api/v1/materials/solidification-materials` | 固化材 |
| GET/POST | `/api/v1/materials/leaching-suppressants` | 溶出抑制剤 |
| GET/POST | `/api/v1/materials/recipes` | レシピ |

### ML/最適化

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/predict/formulation` | 配合予測 |
| POST | `/api/v1/predict/elution` | 溶出予測 |
| GET | `/api/v1/ml/models` | モデル一覧 |
| POST | `/api/v1/ml/train` | モデル学習 |
| GET | `/api/v1/ml/accuracy` | 精度情報 |
| POST | `/api/v1/optimization/optimize` | 配合最適化 |

### チャット/RAG

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/chat/sessions` | セッション作成 |
| POST | `/api/v1/chat/sessions/{id}/ask` | 質問 |
| GET | `/api/v1/chat/sessions/{id}/ask/stream` | ストリーミング |
| POST | `/api/v1/chat/knowledge` | ナレッジ登録 |

### バッチ/KPI

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/batch/jobs` | ジョブ一覧 |
| POST | `/api/v1/batch/jobs/{name}/trigger` | ジョブ実行 |
| GET | `/api/v1/kpi/realtime` | リアルタイム KPI |
| GET | `/api/v1/kpi/trends` | KPI トレンド |
| GET | `/api/v1/kpi/alerts` | KPI アラート |

### システム

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/ready` | デプロイ準備確認 |

---

**重要事項**

1. `.env.production` のプレースホルダー (`CHANGE_ME_...`) は必ず本番値に変更してください
2. `config/ssl/` 内の証明書・秘密鍵は `.gitignore` で除外されています
3. バックアップは `~/BSF_Backups/postgres/` に 30 日分保持されます
4. LM Studio は Mac mini ホスト上で起動し、Docker コンテナからは `host.docker.internal:1234` でアクセスします

---

## 11. シークレットローテーション

### 背景

初期コミット (`48f53d6`) で `.env.production.secure` がgit履歴に含まれました。
ファイルは既に `.gitignore` に追加済みですが、git履歴には残っています。

### ローテーションが必要なシークレット

| シークレット | 場所 | 対応 |
|-------------|------|------|
| `SECRET_KEY` | `.env.production` | **即時変更必須** — 新しい値を生成 |
| `POSTGRES_PASSWORD` | `.env.production` | DB接続パスワード変更 |
| `INFLUXDB_TOKEN` | `.env.production` | InfluxDB未使用のため不要 |

### ローテーション手順

```bash
# 1. 新しい SECRET_KEY を生成
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. .env.production を更新
#    SECRET_KEY=<新しい値>
#    POSTGRES_PASSWORD=<新しい値>

# 3. PostgreSQL パスワードを変更
docker exec -it bsf-postgres psql -U bsf_user -d bsf_system -c \
  "ALTER USER bsf_user PASSWORD '<新しいパスワード>';"

# 4. Blue-Green デプロイで新設定を適用
./scripts/deploy-blue-green.sh deploy

# 5. 動作確認
curl -s http://localhost/health | python3 -m json.tool
```

### git履歴のクリーンアップ (オプション)

閉域ネットワーク運用のため優先度は低いですが、必要に応じて:

```bash
# git filter-branch で該当ファイルを履歴から除去
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env.production.secure' \
  --prune-empty --tag-name-filter cat -- --all

# 全リモートに強制プッシュ (要チーム合意)
git push origin --force --all
```

### 定期ローテーション推奨

- `SECRET_KEY`: 6ヶ月ごと (JWT全無効化を伴うため計画的に)
- `POSTGRES_PASSWORD`: 年1回
- SSL証明書: 有効期限の30日前 (セクション9参照)
