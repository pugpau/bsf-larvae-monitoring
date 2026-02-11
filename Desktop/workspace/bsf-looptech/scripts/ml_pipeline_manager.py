#!/usr/bin/env python3
"""
機械学習パイプライン管理ツール
パイプラインの実行、スケジューリング、監視を管理
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.pipeline_scheduler import (
    PipelineScheduler, ScheduledJob, TriggerCondition, ScheduleType, pipeline_scheduler
)
from src.analytics.training_pipeline import TrainingConfig, training_pipeline
from src.analytics.model_registry import ModelRegistry, ModelStatus, model_registry
from src.analytics.feature_engineering import FeatureType, WindowConfig, ScalingMethod
from src.analytics.ml_models import ModelType
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MLPipelineManager:
    """機械学習パイプライン管理"""
    
    def __init__(self):
        self.scheduler = pipeline_scheduler
        self.training_pipeline = training_pipeline
        self.model_registry = model_registry
    
    async def run_training_pipeline(
        self,
        measurement_types: List[str],
        training_days: int = 30,
        model_types: List[str] = None
    ):
        """訓練パイプラインを実行"""
        try:
            if model_types is None:
                model_types = ["random_forest_regressor", "linear_regression"]
            
            # ModelTypeのenumに変換
            model_type_enums = []
            for mt in model_types:
                try:
                    model_type_enums.append(ModelType(mt))
                except ValueError:
                    print(f"警告: 無効なモデルタイプ '{mt}' をスキップ")
            
            config = TrainingConfig(
                measurement_types=measurement_types,
                training_period_days=training_days,
                model_types=model_type_enums,
                feature_types=[FeatureType.STATISTICAL, FeatureType.TEMPORAL],
                window_config=WindowConfig(window_size=24, step_size=1),
                scaling_method=ScalingMethod.STANDARD,
                hyperparameter_tuning=True,
                include_anomaly_detection=True
            )
            
            print(f"パイプライン実行開始...")
            print(f"測定タイプ: {', '.join(measurement_types)}")
            print(f"訓練期間: {training_days}日")
            print(f"モデルタイプ: {', '.join([mt.value for mt in model_type_enums])}")
            
            result = await self.training_pipeline.run_training_pipeline(config)
            
            print(f"\n=== パイプライン実行結果 ===")
            print(f"ステータス: {result.status.value}")
            print(f"実行時間: {result.duration_seconds:.1f}秒")
            print(f"訓練モデル数: {len(result.trained_models)}")
            
            if result.best_models:
                print(f"\n最良モデル:")
                for measurement_type, model_id in result.best_models.items():
                    print(f"  {measurement_type}: {model_id}")
            
            # 結果をファイルに保存
            result_file = Path(f"pipeline_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(result_file, 'w') as f:
                json.dump(result.model_dump(), f, indent=2, default=str)
            print(f"\n詳細結果を保存: {result_file}")
            
            return result
            
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"Pipeline execution error: {e}")
            return None
    
    async def schedule_pipeline(
        self,
        job_name: str,
        measurement_types: List[str],
        schedule_type: str,
        time_of_day: str = None,
        interval_hours: int = None
    ):
        """パイプラインをスケジュール"""
        try:
            # トリガー条件を作成
            trigger = TriggerCondition(
                schedule_type=ScheduleType(schedule_type),
                time_of_day=time_of_day,
                interval_hours=interval_hours
            )
            
            # 訓練設定
            config = TrainingConfig(
                measurement_types=measurement_types,
                training_period_days=30,
                model_types=[ModelType.RANDOM_FOREST_REGRESSOR, ModelType.LINEAR_REGRESSION],
                include_anomaly_detection=True
            )
            
            # スケジュールジョブを作成
            job = ScheduledJob(
                job_id=f"scheduled_{job_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=job_name,
                description=f"Scheduled training for {', '.join(measurement_types)}",
                training_config=config,
                trigger_condition=trigger
            )
            
            job_id = await self.scheduler.add_scheduled_job(job)
            
            print(f"スケジュールジョブを追加しました:")
            print(f"  ジョブID: {job_id}")
            print(f"  名前: {job_name}")
            print(f"  スケジュール: {schedule_type}")
            if time_of_day:
                print(f"  実行時刻: {time_of_day}")
            if interval_hours:
                print(f"  実行間隔: {interval_hours}時間")
            
            return job_id
            
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"Schedule creation error: {e}")
            return None
    
    async def list_scheduled_jobs(self):
        """スケジュールされたジョブを一覧"""
        try:
            jobs = await self.scheduler.list_jobs()
            
            if not jobs:
                print("スケジュールされたジョブはありません")
                return
            
            print("=== スケジュールされたジョブ ===")
            for job in jobs:
                status = "有効" if job.is_active else "無効"
                print(f"\nジョブID: {job.job_id}")
                print(f"名前: {job.name}")
                print(f"ステータス: {status}")
                print(f"スケジュール: {job.trigger_condition.schedule_type.value}")
                print(f"実行回数: {job.execution_count}")
                
                if job.last_executed:
                    print(f"最終実行: {job.last_executed.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if job.next_execution:
                    print(f"次回実行: {job.next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if job.last_error:
                    print(f"最終エラー: {job.last_error}")
            
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"List jobs error: {e}")
    
    async def start_scheduler(self):
        """スケジューラーを開始"""
        try:
            await self.scheduler.start_scheduler()
            print("スケジューラーを開始しました")
            print("Ctrl+Cで停止...")
            
            # スケジューラーを実行し続ける
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nスケジューラーを停止中...")
                await self.scheduler.stop_scheduler()
                print("スケジューラーを停止しました")
                
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"Scheduler error: {e}")
    
    async def execute_job_now(self, job_id: str):
        """ジョブを即座に実行"""
        try:
            execution_id = await self.scheduler.execute_job_now(job_id)
            print(f"ジョブ {job_id} を実行しました")
            print(f"実行ID: {execution_id}")
            
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"Job execution error: {e}")
    
    async def list_models(self):
        """登録されたモデルを一覧"""
        try:
            models = await self.model_registry.list_models()
            
            if not models:
                print("登録されたモデルはありません")
                return
            
            print("=== 登録モデル ===")
            for model in models:
                print(f"\nモデル名: {model.model_name}")
                print(f"タイプ: {model.model_type.value}")
                print(f"タスク: {model.task_type.value}")
                print(f"測定タイプ: {model.measurement_type}")
                print(f"バージョン数: {len(model.versions)}")
                print(f"最新バージョン: {model.latest_version}")
                print(f"本番バージョン: {model.production_version}")
                
                # 本番モデルの性能
                if model.production_version and model.production_version in model.versions:
                    prod_version = model.versions[model.production_version]
                    if prod_version.performance_metrics:
                        print(f"本番性能: {prod_version.performance_metrics}")
                
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"List models error: {e}")
    
    async def deploy_model(self, model_name: str, version: str, target_status: str):
        """モデルをデプロイ"""
        try:
            from src.analytics.model_registry import DeploymentConfig
            
            config = DeploymentConfig(
                target_status=ModelStatus(target_status),
                traffic_percentage=100.0
            )
            
            success = await self.model_registry.deploy_model(model_name, version, config)
            
            if success:
                print(f"モデル {model_name} バージョン {version} を {target_status} にデプロイしました")
            else:
                print(f"デプロイに失敗しました")
                
        except Exception as e:
            print(f"エラー: {e}")
            logger.error(f"Model deployment error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="機械学習パイプライン管理ツール")
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    
    # 訓練実行
    train_parser = subparsers.add_parser("train", help="訓練パイプラインを実行")
    train_parser.add_argument("--measurement-types", nargs="+", required=True,
                             help="測定タイプ (例: temperature humidity)")
    train_parser.add_argument("--training-days", type=int, default=30,
                             help="訓練期間（日）")
    train_parser.add_argument("--model-types", nargs="+",
                             default=["random_forest_regressor", "linear_regression"],
                             help="モデルタイプ")
    
    # スケジューラー
    schedule_parser = subparsers.add_parser("schedule", help="パイプラインをスケジュール")
    schedule_parser.add_argument("--name", required=True, help="ジョブ名")
    schedule_parser.add_argument("--measurement-types", nargs="+", required=True)
    schedule_parser.add_argument("--schedule-type", required=True,
                                choices=["daily", "weekly", "monthly"],
                                help="スケジュールタイプ")
    schedule_parser.add_argument("--time", help="実行時刻 (HH:MM)")
    schedule_parser.add_argument("--interval-hours", type=int, help="実行間隔（時間）")
    
    # スケジュール管理
    subparsers.add_parser("list-jobs", help="スケジュールされたジョブを一覧")
    subparsers.add_parser("start-scheduler", help="スケジューラーを開始")
    
    execute_parser = subparsers.add_parser("execute-job", help="ジョブを即座に実行")
    execute_parser.add_argument("job_id", help="ジョブID")
    
    # モデル管理
    subparsers.add_parser("list-models", help="登録されたモデルを一覧")
    
    deploy_parser = subparsers.add_parser("deploy-model", help="モデルをデプロイ")
    deploy_parser.add_argument("model_name", help="モデル名")
    deploy_parser.add_argument("version", help="バージョン")
    deploy_parser.add_argument("--status", required=True,
                              choices=["development", "staging", "production"],
                              help="デプロイ先ステータス")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = MLPipelineManager()
    
    try:
        if args.command == "train":
            await manager.run_training_pipeline(
                measurement_types=args.measurement_types,
                training_days=args.training_days,
                model_types=args.model_types
            )
        
        elif args.command == "schedule":
            await manager.schedule_pipeline(
                job_name=args.name,
                measurement_types=args.measurement_types,
                schedule_type=args.schedule_type,
                time_of_day=args.time,
                interval_hours=args.interval_hours
            )
        
        elif args.command == "list-jobs":
            await manager.list_scheduled_jobs()
        
        elif args.command == "start-scheduler":
            await manager.start_scheduler()
        
        elif args.command == "execute-job":
            await manager.execute_job_now(args.job_id)
        
        elif args.command == "list-models":
            await manager.list_models()
        
        elif args.command == "deploy-model":
            await manager.deploy_model(args.model_name, args.version, args.status)
        
    except KeyboardInterrupt:
        print("\n操作がキャンセルされました")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())