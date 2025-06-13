import logging
from src.substrate.service import SubstrateService
from src.substrate.models import SubstrateType, SubstrateBatch, SubstrateTypeEnum, SubstrateMixComponent
from datetime import datetime, timedelta

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_substrate_management():
    """基質管理システムの機能をテストする"""
    service = SubstrateService()
    
    # 1. 基質タイプの作成
    logger.info("基質タイプの作成テスト")
    sewage_sludge = service.create_substrate_type(
        name="下水汚泥",
        type_enum=SubstrateTypeEnum.SEWAGE_SLUDGE,
        description="都市下水処理場からの汚泥",
        attributes=[
            {"name": "水分含有量", "value": 65.5, "unit": "%"},
            {"name": "有機物含有率", "value": 45.2, "unit": "%"}
        ]
    )
    
    if not sewage_sludge:
        logger.error("基質タイプの作成に失敗しました")
        return False
    
    logger.info(f"基質タイプ作成成功: {sewage_sludge.id}")
    
    # 2. 基質バッチの作成
    logger.info("基質バッチの作成テスト")
    batch_components = [
        {"substrate_type_id": sewage_sludge.id, "ratio": 70.0},
        {"substrate_type_id": sewage_sludge.id, "ratio": 30.0}
    ]
    
    substrate_batch = service.create_substrate_batch(
        farm_id="farm123",
        components=batch_components,
        name="春季混合基質 #1",
        description="下水汚泥を主成分とする基質バッチ",
        total_weight=500,
        weight_unit="kg",
        batch_number="B2025-001",
        location="保管エリアA"
    )
    
    if not substrate_batch:
        logger.error("基質バッチの作成に失敗しました")
        return False
    
    logger.info(f"基質バッチ作成成功: {substrate_batch.id}")
    
    # 3. 基質バッチの更新
    logger.info("基質バッチの更新テスト")
    substrate_batch.total_weight = 450  # 50kgを使用
    update_success = service.update_substrate_batch(
        batch=substrate_batch,
        change_reason="50kgを飼育エリアBで使用",
        changed_by="user123"
    )
    
    if not update_success:
        logger.error("基質バッチの更新に失敗しました")
        return False
    
    logger.info("基質バッチの更新成功")
    
    # 4. 基質バッチの状態変更
    logger.info("基質バッチの状態変更テスト")
    status_update_success = service.update_batch_status(
        batch_id=substrate_batch.id,
        new_status="depleted",
        change_reason="バッチの使用完了",
        changed_by="user123"
    )
    
    if not status_update_success:
        logger.error("基質バッチの状態変更に失敗しました")
        return False
    
    logger.info("基質バッチの状態変更成功")
    
    # 5. 変更履歴の取得
    logger.info("基質バッチ変更履歴の取得テスト")
    change_history = service.get_batch_change_history(batch_id=substrate_batch.id)
    
    if not change_history:
        logger.error("変更履歴の取得に失敗しました")
        return False
    
    logger.info(f"変更履歴取得成功: {len(change_history)}件の履歴")
    for log in change_history:
        logger.info(f"  - 変更タイプ: {log.change_type}, 変更日時: {log.timestamp}")
    
    return True

if __name__ == "__main__":
    test_result = test_substrate_management()
    
    if test_result:
        logger.info("基質管理システムのテストが正常に完了しました")
    else:
        logger.error("基質管理システムのテストに失敗しました")