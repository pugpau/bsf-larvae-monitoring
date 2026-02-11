# データベースマイグレーションガイド

## 概要
このドキュメントは、BSF-LoopTechプロジェクトのデータベースマイグレーション管理方法について説明します。

## Alembic設定

### 設定ファイル
- `alembic.ini`: Alembic基本設定
- `alembic/env.py`: マイグレーション実行環境設定
- `.env.local`: ローカル開発用環境変数
- `.env`: 本番環境用環境変数

### 環境変数設定
```bash
# 開発環境
DATABASE_URL=postgresql+asyncpg://bsf_user:bsf_password@localhost:5432/bsf_system

# 本番環境
DATABASE_URL=postgresql+asyncpg://bsf_user:bsf_password@postgres:5432/bsf_system
```

## マイグレーション操作

### 1. 現在の状態確認
```bash
# 現在のマイグレーションバージョン確認
alembic current

# マイグレーション履歴表示
alembic history --verbose
```

### 2. 新しいマイグレーション作成
```bash
# モデル変更を自動検出してマイグレーション作成
alembic revision --autogenerate -m "マイグレーション説明"

# 手動でマイグレーション作成
alembic revision -m "マイグレーション説明"
```

### 3. マイグレーション適用
```bash
# 最新バージョンにアップグレード
alembic upgrade head

# 特定バージョンにアップグレード
alembic upgrade <revision_id>

# 一つ前のバージョンにダウングレード
alembic downgrade -1

# 特定バージョンにダウングレード
alembic downgrade <revision_id>
```

### 4. データベース初期化
```bash
# 新しいデータベースの場合
alembic upgrade head

# 既存データベースの場合（マイグレーション履歴同期）
alembic stamp head
```

## 管理スクリプトの使用

`scripts/manage_db.py`を使用して、より簡単にマイグレーション操作ができます：

```bash
# データベース接続テスト
python scripts/manage_db.py check

# マイグレーション環境初期化
python scripts/manage_db.py init

# 新しいマイグレーション作成
python scripts/manage_db.py create "マイグレーション説明"

# データベースアップグレード
python scripts/manage_db.py upgrade

# データベースダウングレード
python scripts/manage_db.py downgrade

# 現在バージョン表示
python scripts/manage_db.py current

# 履歴表示
python scripts/manage_db.py history

# 環境ファイル指定
python scripts/manage_db.py --env .env.local check
```

## 本番環境でのマイグレーション手順

### 1. 事前準備
```bash
# 1. データベースのバックアップを取得
pg_dump -h postgres -U bsf_user bsf_system > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 現在のマイグレーション状態確認
docker exec -it bsf-looptech_backend_1 alembic current

# 3. 適用予定のマイグレーション確認
docker exec -it bsf-looptech_backend_1 alembic history --verbose
```

### 2. マイグレーション実行
```bash
# 本番環境でのマイグレーション実行
docker exec -it bsf-looptech_backend_1 alembic upgrade head
```

### 3. 事後確認
```bash
# 1. マイグレーション状態確認
docker exec -it bsf-looptech_backend_1 alembic current

# 2. アプリケーション起動確認
docker exec -it bsf-looptech_backend_1 python -c "
from src.database.postgresql import get_database_session
from src.auth.models import User
print('Database connection test passed')
"

# 3. サービス再起動
docker-compose restart backend
```

## 緊急時のロールバック手順

### マイグレーション失敗時の対処
```bash
# 1. 失敗したマイグレーションを一つ前に戻す
docker exec -it bsf-looptech_backend_1 alembic downgrade -1

# 2. バックアップからの復元（最終手段）
psql -h postgres -U bsf_user -d bsf_system < backup_YYYYMMDD_HHMMSS.sql

# 3. マイグレーション状態を手動で同期
docker exec -it bsf-looptech_backend_1 alembic stamp <previous_revision_id>
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. 接続エラー
```
psycopg2.OperationalError: could not translate host name "postgres" to address
```
**解決方法**: 環境変数の設定を確認し、正しいホスト名を使用してください。

#### 2. テーブル重複エラー
```
psycopg2.errors.DuplicateTable: relation "table_name" already exists
```
**解決方法**: 既存のデータベース状態をマイグレーション履歴と同期してください。
```bash
alembic stamp head
```

#### 3. モジュールインポートエラー
```
ModuleNotFoundError: No module named 'src'
```
**解決方法**: PYTHONPATHを正しく設定してください。
```bash
PYTHONPATH=/path/to/project alembic current
```

## ベストプラクティス

### 1. マイグレーション作成時
- 意味のある説明文を使用する
- 大きな変更は複数のマイグレーションに分割する
- 本番適用前にステージング環境でテストする

### 2. 本番適用前
- 必ずデータベースのバックアップを取得
- ダウンタイム計画を立てる
- ロールバック手順を準備する

### 3. マイグレーションファイルの管理
- 自動生成されたマイグレーションを必ず確認・編集する
- データ損失のリスクがある操作は慎重に確認
- テストデータでの動作確認を実施

## モニタリング

### マイグレーション実行状況の確認
```bash
# マイグレーション実行ログを確認
docker logs bsf-looptech_backend_1 | grep alembic

# データベースの状態確認
docker exec -it bsf-looptech_postgres_1 psql -U bsf_user -d bsf_system -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
"
```

## 関連ファイル
- `alembic.ini`: Alembic設定ファイル
- `alembic/env.py`: 環境設定
- `alembic/versions/`: マイグレーションファイル格納
- `scripts/manage_db.py`: 管理スクリプト
- `src/auth/models.py`: 認証関連モデル
- `src/database/postgresql.py`: データベースモデル