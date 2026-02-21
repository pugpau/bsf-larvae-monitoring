import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

# MQTTブローカー設定
broker_host = "localhost"  # ローカルのMosquittoブローカーを使用
broker_port = 1883
username = None  # 認証が必要な場合は設定
password = None  # 認証が必要な場合は設定

# クライアント作成
client = mqtt.Client()
if username and password:
    client.username_pw_set(username, password)

# 接続
try:
    print(f"MQTTブローカー {broker_host}:{broker_port} に接続しています...")
    client.connect(broker_host, broker_port, 60)
    print("接続成功")
except Exception as e:
    print(f"接続エラー: {e}")
    exit(1)

# テストデータ
farm_id = "farm123"
device_types = ["sensor"]
device_ids = ["temp001", "temp002", "humid001"]

# メッセージ送信
try:
    for i in range(5):  # 5回のデータを送信
        for device_type in device_types:
            for device_id in device_ids:
                topic = f"bsf/{farm_id}/{device_type}/{device_id}"
                
                # センサーごとに異なるデータを生成
                if "temp" in device_id:
                    temp = 25.0 + (i * 0.5)  # 温度を少しずつ上げる
                    humidity = 65.0
                    data = {
                        "measurements": {
                            "temperature": temp,
                            "humidity": humidity
                        },
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                elif "humid" in device_id:
                    humidity = 65.0 - (i * 1.0)  # 湿度を少しずつ下げる
                    data = {
                        "measurements": {
                            "humidity": humidity
                        },
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                
                # JSON形式に変換してパブリッシュ
                payload = json.dumps(data)
                print(f"トピック {topic} にパブリッシュ: {payload}")
                client.publish(topic, payload, qos=1)
                
                # 少し待機
                time.sleep(1)
        
        # 各ラウンド間で待機
        time.sleep(2)
    
    print("テストデータのパブリッシュが完了しました")
    
finally:
    # 切断
    client.disconnect()
    print("MQTTブローカーから切断しました")