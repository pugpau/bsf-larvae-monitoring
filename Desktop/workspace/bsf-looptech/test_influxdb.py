import os
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
from datetime import datetime
import logging
from src.database.influxdb import write_sensor_data, query_sensor_data

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_influxdb_connection():
    """InfluxDBへの接続をテストする"""
    logger.info("InfluxDB接続テスト開始")
    
    try:
        # .envファイルから環境変数を読み込む
        load_dotenv()

        # InfluxDB設定を取得
        url = os.getenv("INFLUXDB_URL")
        token = os.getenv("INFLUXDB_TOKEN")
        org = os.getenv("INFLUXDB_ORG")
        bucket = os.getenv("INFLUXDB_BUCKET")

        logger.info(f"URL: {url}")
        logger.info(f"Token: {token[:10]}...{token[-10:]}")  # トークンの一部のみ表示（セキュリティのため）
        logger.info(f"Organization: {org}")
        logger.info(f"Bucket: {bucket}")

        # InfluxDBクライアントを作成
        client = InfluxDBClient(url=url, token=token, org=org)
        
        # 組織APIを使用して組織情報を取得
        orgs_api = client.organizations_api()
        organizations = orgs_api.find_organizations()
        
        logger.info("組織一覧: " + str([org.name for org in organizations]))
        
        # バケットAPIを使用してバケット情報を取得
        buckets_api = client.buckets_api()
        
        # 組織IDを使用してバケットを取得
        org_id = organizations[0].id if organizations else None
        
        if org_id:
            logger.info("バケット情報の取得を試みます...")
            # バケットの取得方法を変更
            buckets = buckets_api.find_buckets(org_id=org_id)
            
            logger.info("利用可能なバケット:")
            for bucket in buckets.buckets:
                logger.info(f"  - ID: {bucket.id}, 名前: {bucket.name}")
        else:
            logger.warning("組織が見つかりませんでした。")
        
        # テストデータの書き込みと読み取り
        test_data = {
            "farm_id": "test_farm",
            "device_id": "test_device",
            "device_type": "test_sensor",
            "timestamp": datetime.utcnow(),
            "measurements": {
                "temperature": 22.5,
                "humidity": 60.0
            }
        }
        
        # データ書き込み
        write_success = write_sensor_data(test_data)
        if write_success:
            logger.info("テストデータの書き込みに成功しました")
            
            # データ読み取り
            results = query_sensor_data(
                farm_id="test_farm",
                device_id="test_device",
                device_type="test_sensor"
            )
            
            if results:
                logger.info(f"テストデータの読み取りに成功しました: {len(results)}件のデータを取得")
                for result in results[:3]:  # 最初の3件だけ表示
                    logger.info(f"  - {result}")
            else:
                logger.warning("テストデータの読み取りに失敗しました")
        else:
            logger.error("テストデータの書き込みに失敗しました")
        
        client.close()
        return True
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_influxdb_connection()