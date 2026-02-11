# BSF-LoopTech 本番環境デプロイメントガイド

## 概要

このガイドでは、BSF-LoopTech システムを開発環境から本番環境（Docker）に移行する手順を説明します。

## 🎯 デプロイメント対象

### 現在の開発環境
- **バックエンド**: http://localhost:8000 (FastAPI)
- **フロントエンド**: http://localhost:3000 (React)
- **データベース**: SQLite (PostgreSQL代替)
- **MQTT**: 非TLS (localhost:1883)

### 本番環境（Docker）
- **全サービス**: Docker Compose管理
- **データベース**: PostgreSQL + InfluxDB
- **MQTT**: TLS有効 (ポート8883)
- **監視**: ヘルスチェック、自動再起動

## 📋 前提条件

### システム要件
- **Docker**: 28.0+ 
- **Docker Compose**: 2.27+
- **メモリ**: 最小8GB推奨
- **ディスク容量**: 10GB以上

### 確認事項
```bash
# Docker環境確認
docker --version
docker-compose --version
docker system info
```

## 🚀 デプロイメント手順

### 1. 事前準備

#### 現在のサービス停止
```bash
# 開発環境のサービス停止
ps aux | grep -E "(uvicorn|npm)" | grep -v grep | awk '{print $2}' | xargs kill -9
```

#### データディレクトリ作成
```bash
mkdir -p data/postgres data/influxdb backups logs
chmod 755 data backups logs
```

### 2. 環境変数設定

#### 本番環境用設定ファイル
```bash
cp .env.production .env
```

#### 重要な設定項目確認
- `SECRET_KEY`: 本番用秘密鍵
- `INFLUXDB_TOKEN`: InfluxDB認証トークン
- `MQTT_TLS_ENABLED`: true

### 3. Docker環境起動

#### 段階的サービス起動
```bash
# 1. データベースサービス起動
docker-compose up -d postgres influxdb

# 2. MQTTブローカー起動
docker-compose up -d mosquitto

# 3. アプリケーションサービス起動
docker-compose up -d backend frontend

# 4. ML パイプライン起動
docker-compose up -d ml-scheduler
```

#### 全サービス一括起動
```bash
docker-compose up -d
```

### 4. サービス状態確認

#### コンテナ状態確認
```bash
docker-compose ps
docker-compose logs backend
docker-compose logs frontend
```

#### ヘルスチェック確認
```bash
# API稼働確認
curl -f http://localhost:8000/docs

# フロントエンド確認
curl -f http://localhost:3000

# データベース接続確認
docker-compose exec postgres pg_isready -U bsf_user

# InfluxDB接続確認
docker-compose exec influxdb influx ping
```

### 5. データマイグレーション

#### データベーススキーマ適用
```bash
# Alembic マイグレーション実行
docker-compose exec backend alembic upgrade head

# 初期データ投入（オプション）
docker-compose exec backend python scripts/init_sample_data.py
```

### 6. MQTT接続テスト

#### TLS接続確認
```bash
# 証明書を使用したMQTT接続テスト
mosquitto_pub -h localhost -p 8883 \
  --cafile certs/ca.crt \
  --cert certs/mqtt-client.crt \
  --key certs/mqtt-client.key \
  -t "bsf/test" -m "production test"
```

## 🔧 設定差異の確認

### 主要な変更点

| 項目 | 開発環境 | 本番環境 |
|------|----------|----------|
| **データベース** | SQLite | PostgreSQL |
| **MQTT** | 非TLS (1883) | TLS (8883) |
| **プロセス管理** | 手動起動 | Docker自動管理 |
| **ログ** | コンソール | ファイル出力 |
| **監視** | なし | ヘルスチェック |

### 環境別設定ファイル
- `.env` - 開発環境（SQLite）
- `.env.production` - 本番環境（PostgreSQL）

## 📊 監視とメンテナンス

### ログ監視
```bash
# リアルタイムログ監視
docker-compose logs -f backend
docker-compose logs -f frontend

# エラーログ確認
docker-compose logs backend | grep ERROR
```

### リソース監視
```bash
# コンテナリソース使用量
docker stats

# ディスク使用量
docker system df
```

### バックアップ実行
```bash
# データベースバックアップ
docker-compose --profile backup run backup

# 手動バックアップ
docker-compose exec postgres pg_dump -U bsf_user bsf_system > backups/backup_$(date +%Y%m%d).sql
```

## 🛠️ トラブルシューティング

### よくある問題

#### 1. PostgreSQL接続エラー
```bash
# コンテナログ確認
docker-compose logs postgres

# データベース再初期化
docker-compose down
docker volume rm bsf-looptech_postgres_data
docker-compose up -d postgres
```

#### 2. MQTT TLS接続エラー
```bash
# 証明書確認
ls -la certs/
openssl x509 -in certs/ca.crt -text -noout

# 非TLSでのテスト
mosquitto_pub -h localhost -p 1883 -t test -m "non-tls test"
```

#### 3. メモリ不足
```bash
# Dockerメモリ設定増加
# Docker Desktop > Settings > Resources > Memory: 8GB+

# 不要なコンテナ削除
docker system prune -a
```

## 🔄 ロールバック手順

### 開発環境への復帰
```bash
# Docker環境停止
docker-compose down

# 開発環境再起動
cp .env.development .env
python -m uvicorn src.main:app --reload &
cd frontend && npm start &
```

## 📈 本番運用推奨事項

### 1. 自動起動設定
```bash
# システム起動時の自動開始
echo "@reboot cd /path/to/bsf-looptech && docker-compose up -d" | crontab -
```

### 2. 定期バックアップ
```bash
# 毎日0時にバックアップ実行
echo "0 0 * * * cd /path/to/bsf-looptech && docker-compose --profile backup run backup" | crontab -
```

### 3. ログローテーション
```bash
# Docker ログ設定で自動ローテーション設定済み
# max-size: "10m", max-file: "5"
```

## 🎉 デプロイメント完了チェックリスト

- [ ] Dockerサービス全て起動中
- [ ] ヘルスチェック全て合格
- [ ] フロントエンド正常表示 (http://localhost:3000)
- [ ] API正常動作 (http://localhost:8000/docs)
- [ ] MQTT TLS接続成功
- [ ] データベースマイグレーション完了
- [ ] バックアップ機能動作確認
- [ ] ログ出力確認

---

**注意**: 本番環境では、セキュリティとパフォーマンスが開発環境と大きく異なります。定期的な監視とメンテナンスを実施してください。