# データベースマイグレーションガイド

## 概要

BSF-LoopTechプロジェクトでは、Alembicを使用してデータベースのスキーマ管理を行います。このドキュメントでは、マイグレーションの作成、適用、管理方法について説明します。

## セットアップ

### 必要な依存関係

```bash
pip install alembic sqlalchemy asyncpg aiosqlite
```

### 初期設定

プロジェクトには既にAlembicが設定されています：
- `alembic.ini`: Alembic設定ファイル
- `alembic/env.py`: マイグレーション環境設定
- `alembic/versions/`: マイグレーションファイル格納ディレクトリ

## 管理スクリプト

`scripts/manage_db.py` を使用してマイグレーションを管理します：

### 使用方法

```bash
# 現在のマイグレーション状態を確認
python scripts/manage_db.py status

# マイグレーション履歴を表示
python scripts/manage_db.py history

# モデルとデータベースの差分を確認
python scripts/manage_db.py check

# 新しいマイグレーションを作成（自動生成）
python scripts/manage_db.py create -m "Add new column to sensor_devices"

# データベースを最新状態にアップグレード
python scripts/manage_db.py upgrade

# 特定のリビジョンにアップグレード
python scripts/manage_db.py upgrade <revision>

# 前のリビジョンにダウングレード
python scripts/manage_db.py downgrade -1

# データベースをバックアップ
python scripts/manage_db.py backup

# データベースを初期化（新規環境用）
python scripts/manage_db.py init
```

## マイグレーションワークフロー

### 1. モデルの変更

```python
# src/database/postgresql.py または src/auth/models.py でモデルを変更
class SensorDevice(Base):
    __tablename__ = 'sensor_devices'
    
    # 新しいカラムを追加
    calibration_date = Column(DateTime, nullable=True)
```

### 2. マイグレーションの作成

```bash
# モデルの変更を確認
python scripts/manage_db.py check

# マイグレーションファイルを自動生成
python scripts/manage_db.py create -m "Add calibration_date to sensor_devices"
```

### 3. マイグレーションの確認

生成されたファイルを確認：
```python
# alembic/versions/xxxx_add_calibration_date_to_sensor_devices.py
def upgrade():
    op.add_column('sensor_devices', 
        sa.Column('calibration_date', sa.DateTime(), nullable=True)
    )

def downgrade():
    op.drop_column('sensor_devices', 'calibration_date')
```

### 4. マイグレーションの適用

```bash
# 適用前にバックアップ（推奨）
python scripts/manage_db.py backup

# マイグレーションを適用
python scripts/manage_db.py upgrade
```

## 環境別設定

### 開発環境（SQLite）

```bash
# .env
DATABASE_URL=sqlite+aiosqlite:///./bsf_system.db
```

### 本番環境（PostgreSQL）

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/bsf_system
```

## トラブルシューティング

### マイグレーションエラー

```bash
# 現在の状態を確認
alembic current

# 履歴を詳細表示
alembic history --verbose

# 強制的に特定のリビジョンにマーク
alembic stamp <revision>
```

### データベースリセット

```bash
# SQLiteの場合
rm bsf_system.db
python scripts/manage_db.py init

# PostgreSQLの場合
psql -U postgres -c "DROP DATABASE bsf_system;"
psql -U postgres -c "CREATE DATABASE bsf_system;"
python scripts/manage_db.py init
```

### マイグレーションの修正

開発中のマイグレーションを修正する場合：

```bash
# 1. ダウングレード
python scripts/manage_db.py downgrade -1

# 2. マイグレーションファイルを削除
rm alembic/versions/xxxx_migration_name.py

# 3. 新しいマイグレーションを作成
python scripts/manage_db.py create -m "Fixed migration"
```

## ベストプラクティス

### 1. マイグレーション作成前

- 必ずモデルの変更をテスト
- `check` コマンドで差分を確認
- 本番環境ではバックアップを取得

### 2. 命名規則

- 明確で説明的なメッセージを使用
- 例: "Add calibration_date to sensor_devices"
- 例: "Create index on sensor_data timestamp"

### 3. データ移行

データの変換が必要な場合：

```python
def upgrade():
    # スキーマ変更
    op.add_column('table', sa.Column('new_col', sa.String()))
    
    # データ移行
    connection = op.get_bind()
    result = connection.execute('SELECT id, old_col FROM table')
    for row in result:
        connection.execute(
            f"UPDATE table SET new_col = '{transform(row.old_col)}' WHERE id = {row.id}"
        )
```

### 4. テスト環境

- マイグレーションは必ずテスト環境で検証
- アップグレードとダウングレードの両方をテスト

## 高度な使用方法

### 複数データベース対応

```python
# alembic/env.py で設定
def run_migrations_online():
    # メインDB
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        context.run_migrations()
    
    # 分析DB（将来の拡張用）
    # with analytics_connectable.connect() as connection:
    #     context.configure(connection=connection, target_metadata=analytics_metadata)
    #     context.run_migrations()
```

### カスタムマイグレーション操作

```python
# 大量データの効率的な処理
def upgrade():
    # バッチ処理でインデックス作成
    op.create_index(
        'idx_sensor_data_timestamp',
        'sensor_data',
        ['timestamp'],
        postgresql_using='btree',
        postgresql_concurrently=True  # 本番環境でのダウンタイム回避
    )
```

## 参考リンク

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Migration Guide](https://docs.sqlalchemy.org/en/14/core/migration.html)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Database_Schema_Changes)