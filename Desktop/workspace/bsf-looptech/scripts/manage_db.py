#!/usr/bin/env python3
"""
データベースマイグレーション管理スクリプト
Alembicコマンドのラッパー
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        os.chdir(self.project_root)
        
    def run_command(self, cmd: list, check: bool = True):
        """コマンドを実行して結果を返す"""
        logger.info(f"実行中: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(result.stderr, file=sys.stderr)
        return result
        
    def check_current(self):
        """現在のマイグレーション状態を確認"""
        logger.info("現在のマイグレーション状態を確認中...")
        self.run_command(["alembic", "current"])
        
    def check_history(self):
        """マイグレーション履歴を表示"""
        logger.info("マイグレーション履歴:")
        self.run_command(["alembic", "history", "--verbose"])
        
    def create_migration(self, message: str, autogenerate: bool = True):
        """新しいマイグレーションを作成"""
        logger.info(f"新しいマイグレーションを作成中: {message}")
        cmd = ["alembic", "revision"]
        if autogenerate:
            cmd.append("--autogenerate")
        cmd.extend(["-m", message])
        self.run_command(cmd)
        
    def upgrade(self, revision: str = "head"):
        """指定のリビジョンまでアップグレード"""
        logger.info(f"データベースをアップグレード中: {revision}")
        self.run_command(["alembic", "upgrade", revision])
        
    def downgrade(self, revision: str):
        """指定のリビジョンまでダウングレード"""
        logger.info(f"データベースをダウングレード中: {revision}")
        self.run_command(["alembic", "downgrade", revision])
        
    def stamp(self, revision: str = "head"):
        """現在のデータベースを指定のリビジョンとしてマーク"""
        logger.info(f"データベースをスタンプ中: {revision}")
        self.run_command(["alembic", "stamp", revision])
        
    def init_db(self):
        """データベースを初期化（全テーブル作成）"""
        logger.info("データベースを初期化中...")
        
        # Pythonスクリプトで直接テーブルを作成
        try:
            import sys
            sys.path.insert(0, str(self.project_root))
            
            from src.database.postgresql import Base, engine
            from src.auth.models import User, UserSession, LoginAttempt, APIKey
            from src.database.postgresql import (
                SensorDevice, SubstrateType, SubstrateBatch,
                SubstrateBatchComponent, AlertRule, AnomalyRule, AnomalyDetection
            )
            
            # 同期エンジンを作成
            from sqlalchemy import create_engine
            from src.config import settings
            
            # async URLを同期URLに変換
            db_url = settings.DATABASE_URL
            if db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            elif db_url.startswith("sqlite+aiosqlite://"):
                db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
                
            sync_engine = create_engine(db_url)
            
            # テーブル作成
            Base.metadata.create_all(bind=sync_engine)
            logger.info("全テーブルを作成しました")
            
            # 初期マイグレーションとしてスタンプ
            self.stamp("head")
            
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise
            
    def backup_db(self, backup_dir: str = "backups"):
        """データベースをバックアップ"""
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # SQLiteの場合
        db_file = self.project_root / "bsf_system.db"
        if db_file.exists():
            backup_file = backup_path / f"bsf_system_{timestamp}.db"
            import shutil
            shutil.copy2(db_file, backup_file)
            logger.info(f"データベースをバックアップしました: {backup_file}")
        else:
            logger.warning("バックアップ対象のデータベースファイルが見つかりません")
            
    def check_models(self):
        """モデルとデータベースの差分を確認"""
        logger.info("モデルとデータベースの差分を確認中...")
        result = self.run_command(["alembic", "check"], check=False)
        if result.returncode == 0:
            logger.info("✅ モデルとデータベースは同期しています")
        else:
            logger.warning("⚠️ モデルとデータベースに差分があります")
            logger.info("'python scripts/manage_db.py create -m \"説明\"' で新しいマイグレーションを作成してください")

def main():
    parser = argparse.ArgumentParser(description="データベースマイグレーション管理ツール")
    
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    
    # 状態確認
    status_parser = subparsers.add_parser("status", help="現在の状態を確認")
    
    # 履歴表示
    history_parser = subparsers.add_parser("history", help="マイグレーション履歴を表示")
    
    # マイグレーション作成
    create_parser = subparsers.add_parser("create", help="新しいマイグレーションを作成")
    create_parser.add_argument("-m", "--message", required=True, help="マイグレーションの説明")
    create_parser.add_argument("--manual", action="store_true", help="自動生成を無効化")
    
    # アップグレード
    upgrade_parser = subparsers.add_parser("upgrade", help="データベースをアップグレード")
    upgrade_parser.add_argument("revision", nargs="?", default="head", help="対象リビジョン")
    
    # ダウングレード
    downgrade_parser = subparsers.add_parser("downgrade", help="データベースをダウングレード")
    downgrade_parser.add_argument("revision", help="対象リビジョン")
    
    # 初期化
    init_parser = subparsers.add_parser("init", help="データベースを初期化")
    
    # バックアップ
    backup_parser = subparsers.add_parser("backup", help="データベースをバックアップ")
    backup_parser.add_argument("--dir", default="backups", help="バックアップディレクトリ")
    
    # モデルチェック
    check_parser = subparsers.add_parser("check", help="モデルとDBの差分を確認")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    manager = DatabaseManager()
    
    try:
        if args.command == "status":
            manager.check_current()
        elif args.command == "history":
            manager.check_history()
        elif args.command == "create":
            manager.create_migration(args.message, not args.manual)
        elif args.command == "upgrade":
            manager.upgrade(args.revision)
        elif args.command == "downgrade":
            manager.downgrade(args.revision)
        elif args.command == "init":
            manager.init_db()
        elif args.command == "backup":
            manager.backup_db(args.dir)
        elif args.command == "check":
            manager.check_models()
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()