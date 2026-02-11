# MQTT/IoT 通信仕様

## ドキュメント情報
- **バージョン**: 0.1.0
- **最終更新**: 2025-10-01
- **MQTTブローカー**: Eclipse Mosquitto 2.0
- **通信プロトコル**: MQTT 3.1.1 / 5.0

---

## 1. MQTT概要

### 1.1 MQTTとは

MQTT (Message Queuing Telemetry Transport) は、軽量なパブリッシュ/サブスクライブ型メッセージングプロトコルで、IoTデバイス通信に最適化されています。

### 1.2 BSF-LoopTechでの利用

- センサーデバイス → バックエンド間のデータ通信
- リアルタイムデータストリーミング
- 双方向通信（制御信号送信）
- 低帯域幅・高レイテンシ環境対応

---

## 2. MQTTブローカー設定

### 2.1 Mosquitto設定

#### docker-compose.yml
```yaml
mosquitto:
  image: eclipse-mosquitto:2.0-openssl
  container_name: bsf-mosquitto
  volumes:
    - ./config/mosquitto-docker.conf:/mosquitto/config/mosquitto.conf:ro
    - ./config/mqtt/password.txt:/mosquitto/config/password.txt:ro
    - ./config/mqtt_acl.conf:/mosquitto/config/acl.conf:ro
    - ./certs:/mosquitto/certs:ro
  ports:
    - "1883:1883"   # MQTT (非暗号化)
    - "8883:8883"   # MQTT over TLS
    - "9001:9001"   # WebSockets
  networks:
    - bsf-network
```

#### mosquitto.conf
```conf
# リスナー設定
listener 1883
protocol mqtt

listener 8883
protocol mqtt
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate false

listener 9001
protocol websockets

# 認証設定
allow_anonymous false
password_file /mosquitto/config/password.txt
acl_file /mosquitto/config/acl.conf

# ログ設定
log_type all
log_dest stdout

# セッション設定
max_keepalive 300
persistent_client_expiration 1h

# メッセージ設定
max_qos_size 0
message_size_limit 8192
```

### 2.2 認証設定

#### パスワードファイル生成
```bash
mosquitto_passwd -c /mosquitto/config/password.txt bsf_sensor
mosquitto_passwd /mosquitto/config/password.txt bsf_backend
```

#### ACL (アクセス制御リスト)
```conf
# bsf_sensor ユーザー: センサーデバイス用
user bsf_sensor
topic write bsf/+/+/+
topic read bsf/control/#

# bsf_backend ユーザー: バックエンド用
user bsf_backend
topic read bsf/#
topic write bsf/control/#
```

---

## 3. トピック構造

### 3.1 トピック命名規則

```
bsf/{farm_id}/{device_type}/{device_id}[/{sub_topic}]
```

**パラメータ:**
- `farm_id`: ファームID (例: farm001, farm002)
- `device_type`: デバイスタイプ (temperature, humidity, gas, etc.)
- `device_id`: デバイス固有ID (例: sensor001, m5stick-temp-01)
- `sub_topic`: オプショナルサブトピック (data, status, config)

### 3.2 トピック例

#### センサーデータ送信
```
bsf/farm001/temperature/sensor001/data
bsf/farm001/humidity/sensor002/data
bsf/farm001/gas/sensor003/data
```

#### デバイスステータス
```
bsf/farm001/temperature/sensor001/status
```

#### 制御コマンド
```
bsf/control/farm001/temperature/sensor001/config
```

#### システムトピック
```
bsf/system/alerts
bsf/system/health
```

---

## 4. メッセージペイロード

### 4.1 センサーデータメッセージ

#### JSON形式
```json
{
  "device_id": "m5stick-temp-01",
  "device_name": "M5StickC Temperature Sensor",
  "firmware": "1.4.0",
  "timestamp": 1696151234000,
  "measurements": [
    {
      "type": "ambient_temperature",
      "value": 25.5,
      "unit": "°C"
    },
    {
      "type": "object_temperature",
      "value": 30.2,
      "unit": "°C"
    }
  ],
  "location": {
    "area": "area1",
    "x": 10.5,
    "y": 20.3,
    "z": 5.0
  },
  "battery": {
    "level": 85.0,
    "voltage": 3.8
  },
  "metadata": {
    "wifi_rssi": -65,
    "uptime": 3600
  }
}
```

#### MessagePack形式（将来対応）
バイナリフォーマットで帯域幅削減

### 4.2 ステータスメッセージ

```json
{
  "device_id": "sensor001",
  "status": "online",
  "timestamp": 1696151234000,
  "health": {
    "cpu_usage": 45.2,
    "memory_usage": 60.5,
    "temperature": 42.0
  },
  "connectivity": {
    "wifi_ssid": "bsf",
    "wifi_rssi": -65,
    "mqtt_connected": true
  }
}
```

### 4.3 アラートメッセージ

```json
{
  "alert_id": "alert-uuid",
  "device_id": "sensor001",
  "timestamp": 1696151234000,
  "severity": "high",
  "type": "threshold_exceeded",
  "measurement_type": "temperature",
  "value": 45.0,
  "threshold": 35.0,
  "message": "温度が閾値を超えました"
}
```

---

## 5. QoS（Quality of Service）レベル

### 5.1 QoS レベル定義

| レベル | 名称 | 保証 | 用途 |
|-------|-----|------|------|
| **0** | At most once | 最大1回配信 | ステータス更新 |
| **1** | At least once | 最低1回配信 | センサーデータ |
| **2** | Exactly once | 正確に1回配信 | 制御コマンド |

### 5.2 BSF-LoopTechでの使用

- **センサーデータ**: QoS 1（少なくとも1回配信）
- **アラート**: QoS 1
- **制御コマンド**: QoS 2（正確に1回配信）
- **ステータス**: QoS 0（最大1回配信）

---

## 6. TLS/SSL暗号化

### 6.1 証明書構成

#### CA証明書（認証局）
```bash
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt
```

#### サーバー証明書（Mosquittoブローカー）
```bash
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 3650
```

#### クライアント証明書（センサーデバイス）
```bash
openssl genrsa -out mqtt-client.key 2048
openssl req -new -key mqtt-client.key -out mqtt-client.csr
openssl x509 -req -in mqtt-client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out mqtt-client.crt -days 3650
```

### 6.2 TLS設定（バックエンド）

```python
# src/config.py
MQTT_TLS_ENABLED = True
MQTT_CA_CERTS = "/app/certs/ca.crt"
MQTT_CLIENT_CERT = "/app/certs/mqtt-client.crt"
MQTT_CLIENT_KEY = "/app/certs/mqtt-client.key"
```

```python
# src/mqtt/client.py
if settings.MQTT_TLS_ENABLED:
    client.tls_set(
        ca_certs=settings.MQTT_CA_CERTS,
        certfile=settings.MQTT_CLIENT_CERT,
        keyfile=settings.MQTT_CLIENT_KEY,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    client.tls_insecure_set(False)
```

---

## 7. バックエンドMQTTクライアント

### 7.1 クライアント実装（Python）

#### 接続設定
```python
import paho.mqtt.client as mqtt
from src.config import settings

def create_mqtt_client():
    client_id = f"bsf-backend-client-{os.getpid()}"
    client = mqtt.Client(client_id=client_id)

    # 認証設定
    client.username_pw_set(
        settings.MQTT_USERNAME,
        settings.MQTT_PASSWORD
    )

    # TLS設定
    if settings.MQTT_TLS_ENABLED:
        client.tls_set(
            ca_certs=settings.MQTT_CA_CERTS,
            certfile=settings.MQTT_CLIENT_CERT,
            keyfile=settings.MQTT_CLIENT_KEY
        )

    # コールバック設定
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    return client
```

#### メッセージ処理
```python
def on_message(client, userdata, msg):
    logger.info(f"Received: {msg.topic}")

    # トピック解析
    match = re.match(r"bsf/([^/]+)/([^/]+)/([^/]+)", msg.topic)
    if not match:
        logger.error(f"Invalid topic: {msg.topic}")
        return

    farm_id, device_type, device_id = match.groups()

    # ペイロード解析
    payload = json.loads(msg.payload.decode('utf-8'))

    # データベース保存
    sensor_service.process_mqtt_message(msg.topic, payload)

    # リアルタイムストリーミング
    await sensor_streamer.process_mqtt_message(msg.topic, payload)
```

### 7.2 サブスクリプション

```python
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker")

        # ワイルドカード購読
        client.subscribe("bsf/+/+/+/data", qos=1)
        client.subscribe("bsf/+/+/+/status", qos=0)
        client.subscribe("bsf/system/#", qos=1)
```

---

## 8. IoTデバイス実装

### 8.1 M5StickC実装例

```cpp
// WiFi & MQTT設定
#define WIFI_SSID "bsf"
#define WIFI_PASSWORD "08230823"
#define MQTT_SERVER "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_USER "bsf_sensor"
#define MQTT_PASSWORD "bsf_password"

// MQTTクライアント
WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  // WiFi接続
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  // MQTT接続
  client.setServer(MQTT_SERVER, MQTT_PORT);
  reconnectMQTT();
}

void reconnectMQTT() {
  while (!client.connected()) {
    String clientId = "m5stick-temp-01";
    if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
      Serial.println("MQTT Connected");
    } else {
      delay(5000);
    }
  }
}

void publishSensorData() {
  String topic = "bsf/farm001/temperature/m5stick-temp-01/data";

  // JSONペイロード作成
  String payload = "{";
  payload += "\"device_id\":\"m5stick-temp-01\",";
  payload += "\"timestamp\":" + String(millis()) + ",";
  payload += "\"ambient_temp\":" + String(ambientTemp, 2) + ",";
  payload += "\"object_temp\":" + String(objectTemp, 2) + ",";
  payload += "\"battery_level\":" + String(batteryLevel, 1);
  payload += "}";

  client.publish(topic.c_str(), payload.c_str(), false);
}
```

---

## 9. WebSocket ブリッジ

### 9.1 MQTT → WebSocket変換

```python
# src/mqtt/websocket_bridge.py
from fastapi import WebSocket
from typing import Dict, List

class WebSocketBridge:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_mqtt_message(self, topic: str, payload: dict):
        message = {
            "type": "mqtt_message",
            "topic": topic,
            "data": payload
        }

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection)
```

---

## 10. エラーハンドリング

### 10.1 再接続ロジック

```python
def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected: rc={rc}")

    if rc != 0:
        logger.info("Attempting reconnection...")
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                client.reconnect()
                logger.info("Reconnected successfully")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Reconnection failed: {e}")
                time.sleep(5 * retry_count)
```

### 10.2 メッセージエラー処理

```python
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        process_message(payload)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON: {msg.payload}")
    except Exception as e:
        logger.error(f"Processing error: {e}")
```

---

## 11. パフォーマンス最適化

### 11.1 メッセージバッファリング

- クライアント側でメッセージバッファリング
- バッチ送信（複数測定値を1メッセージに）
- 圧縮（MessagePack等）

### 11.2 Keep-Alive設定

```python
client.connect(
    settings.MQTT_BROKER_HOST,
    settings.MQTT_BROKER_PORT,
    keepalive=60  # 60秒間隔でping
)
```

---

## 12. セキュリティベストプラクティス

### 12.1 実装済み対策

- ✅ TLS 1.2/1.3 暗号化通信
- ✅ ユーザー認証（username/password）
- ✅ ACLによるトピックアクセス制御
- ✅ 証明書ベース認証（オプション）
- ✅ 匿名接続禁止

### 12.2 推奨対策

- 証明書の定期更新
- パスワードの定期変更
- ファイアウォール設定
- 監査ログ記録

---

## 13. モニタリング

### 13.1 接続監視

```bash
# アクティブ接続数
mosquitto_sub -h localhost -t \$SYS/broker/clients/connected

# メッセージレート
mosquitto_sub -h localhost -t \$SYS/broker/messages/received
```

### 13.2 ログ監視

```bash
docker logs -f bsf-mosquitto
```

---

## 14. トラブルシューティング

### 14.1 接続問題

**症状:** クライアントが接続できない

**確認事項:**
1. ネットワーク接続
2. ポート開放状況
3. 認証情報
4. 証明書有効性

**デバッグコマンド:**
```bash
# 接続テスト
mosquitto_pub -h localhost -p 1883 -u bsf_sensor -P password -t test -m "hello"

# TLS接続テスト
mosquitto_pub -h localhost -p 8883 --cafile ca.crt -u bsf_sensor -P password -t test -m "hello"
```

### 14.2 メッセージ配信問題

**症状:** メッセージが届かない

**確認事項:**
1. トピック名の正確性
2. QoSレベル
3. ACL設定
4. ブローカーログ

---

## 15. 今後の拡張

- [ ] MQTT 5.0対応
- [ ] メッセージ圧縮（MessagePack）
- [ ] クラスタリング（高可用性）
- [ ] メッセージ永続化
- [ ] Retained Messageの活用
- [ ] Last Will and Testament (LWT) 実装
