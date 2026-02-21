# M5StickCセンサー仕様

## ドキュメント情報
- **バージョン**: 1.4.0
- **最終更新**: 2025-10-01
- **ハードウェア**: M5StickC (ESP32-PICO-D4)
- **センサー**: MLX90614ESF-BCC (非接触温度センサー)

---

## 1. ハードウェア概要

### 1.1 M5StickC仕様

| 項目 | 仕様 |
|-----|------|
| **マイクロコントローラ** | ESP32-PICO-D4 |
| **CPU** | Dual-core Xtensa LX6, 240MHz |
| **RAM** | 520KB SRAM |
| **Flash** | 4MB |
| **WiFi** | 802.11 b/g/n |
| **Bluetooth** | BLE 4.2 |
| **ディスプレイ** | 0.96" TFT LCD (80x160px) |
| **バッテリー** | 95mAh リチウムポリマー |
| **電源管理** | AXP192 |
| **GPIO** | 限定的（GPIO0, GPIO26, GPIO32, GPIO33, GPIO36等） |
| **I2C** | Wire (SDA/SCL) |
| **ボタン** | A, B, 電源ボタン |

### 1.2 MLX90614ESF-BCC仕様

| 項目 | 仕様 |
|-----|------|
| **測定方式** | 非接触赤外線温度センサー |
| **測定範囲（物体温度）** | -70°C ～ +380°C |
| **測定範囲（環境温度）** | -40°C ～ +85°C |
| **精度** | ±0.5°C (0°C～50°C) |
| **視野角** | 50° (BCC型) |
| **測定距離** | 40～55cm（最適距離） |
| **インターフェース** | I2C (SMBus互換) |
| **I2Cアドレス** | 0x5A (デフォルト) |
| **動作電圧** | 3.3V |

---

## 2. ピン配置（最適化版）

### 2.1 G0/G26/G36ピン構成

```
M5StickC
┌─────────────────┐
│  [GPIO0 (SCL)]  │──→ MLX90614 SCL  ⚠️ ボタンA共用
│  [GPIO26(SDA)]  │──→ MLX90614 SDA
│  [GPIO36(ANA)]  │──→ 拡張機能（アナログ入力）
│      [3.3V]     │──→ MLX90614 VCC
│      [GND]      │──→ MLX90614 GND
└─────────────────┘

⚠️ 注意事項:
- GPIO0はブート制御ピン＆ボタンAと共用
- GPIO36は入力専用（出力不可）
- プルアップ抵抗が必要（I2C通信）
```

### 2.2 ピン定義

```cpp
#define MLX90614_SDA_PIN 26        // GPIO26: 汎用I/O（SDA）
#define MLX90614_SCL_PIN 0         // GPIO0: 汎用I/O（SCL、ボタンA共用）
#define ANALOG_INPUT_PIN 36        // GPIO36: 入力専用（拡張機能）
#define I2C_FREQUENCY 100000       // 100kHz
```

### 2.3 ピン特性

| GPIO | 機能 | タイプ | 特記事項 |
|------|------|--------|---------|
| **GPIO0** | SCL | 入出力 | ボタンA共用、ブート制御 |
| **GPIO26** | SDA | 入出力 | 汎用I/O、最適 |
| **GPIO36** | アナログ | 入力のみ | VP (ADC1_CH0) |

---

## 3. ファームウェア構成

### 3.1 ディレクトリ構造

```
m5stick_final_working/
├── m5stick_optimized_pins/      # G0/G26/G36最適化版
│   └── m5stick_optimized_pins.ino
├── m5stick_standard_pins/        # 標準I2Cピン版（GPIO21/22）
│   └── m5stick_standard_pins.ino
└── m5stick_debug_version/        # デバッグ版
    └── m5stick_debug_version.ino
```

### 3.2 依存ライブラリ

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| **M5StickC** | latest | M5StickC基本機能 |
| **WiFi** | ESP32標準 | WiFi接続 |
| **PubSubClient** | 2.8+ | MQTT通信 |
| **Wire** | ESP32標準 | I2C通信 |
| **Adafruit_MLX90614** | 2.1.0+ | MLX90614センサー |

---

## 4. 主要機能

### 4.1 センサーデータ取得

**測定項目:**
- 環境温度（Ambient Temperature）
- 物体温度（Object Temperature）
- GPIO36アナログ値（拡張機能）
- バッテリー電圧・残量

**測定間隔:**
- デフォルト: 2秒（SENSOR_INTERVAL）
- 調整可能: 1秒～60秒

**データ範囲検証:**
```cpp
if (ambient < -40 || ambient > 85 || object < -70 || object > 380) {
  // 範囲外エラー処理
}
```

### 4.2 MQTT通信

**トピック:**
```
bsf/sensors/m5stick-temp-01/data
bsf/sensors/m5stick-temp-01/status
bsf/sensors/m5stick-temp-01/info
```

**ペイロード例:**
```json
{
  "device_id": "m5stick-temp-01",
  "timestamp": 1234567890,
  "ambient_temp": 25.50,
  "object_temp": 30.20,
  "battery_level": 85.0,
  "battery_voltage": 3.80,
  "gpio36_analog": 1.234,
  "button_conflict": false,
  "firmware": "1.4.0"
}
```

### 4.3 ディスプレイ表示

**3つの表示モード:**

#### モード0: メインディスプレイ
```
┌──────────────────┐
│ BSF G0/G26/G36   │ ヘッダー
│                  │
│ Ambient:         │ 環境温度
│ 25.50 C          │
│                  │
│ Object:          │ 物体温度
│ 30.20 C          │
│                  │
│ G36: 1.234V      │ アナログ値
│ WiFi: OK         │ WiFi状態
│ MQTT: OK         │ MQTT状態
│ Batt: 85%        │ バッテリー
│                  │
│ A:Mode B:Read    │ 操作ガイド
└──────────────────┘
```

#### モード1: 診断ディスプレイ
```
┌──────────────────┐
│ Pin Diagnostics  │
│                  │
│ SDA: G26 OK      │ I2Cピン状態
│ SCL: G0 OK       │
│ ANA: G36 1.234V  │
│ I2C: OK          │
│ MLX: OK          │
│ Retry: 0         │
│                  │
│ G0=SCL+BtnA      │ ピン説明
│ G26=SDA          │
│ G36=Analog In    │
│                  │
│ A:Mode B:Test    │
└──────────────────┘
```

#### モード2: システム詳細
```
┌──────────────────┐
│ System Detail    │
│                  │
│ ID: m5stick-...  │ デバイスID
│ FW: 1.4.0        │ ファームウェア
│ Up: 120m         │ アップタイム
│ Batt: 3.80V      │ 電圧
│ Free: 256KB      │ メモリ
│ IP: 192.168...   │ IPアドレス
│ RSSI: -65dBm     │ WiFi信号強度
│ I2C: 100kHz      │ I2C周波数
│                  │
│ A:Mode B:Read    │
└──────────────────┘
```

### 4.4 ボタン操作

| ボタン | 操作 | 機能 |
|-------|------|------|
| **A** | 短押し | 表示モード切り替え |
| **A** | 長押し(3秒) | 再起動 |
| **B** | 短押し | 手動センサー読み取り＆MQTT送信 |
| **電源** | 短押し | スリープ/ウェイク |

**⚠️ ボタンA競合検出:**
GPIO0がSCLと共用のため、ボタンA押下時にI2C通信への影響を検出・警告します。

---

## 5. 診断機能

### 5.1 I2Cデバイススキャン

**機能:**
- I2Cバス上の全デバイス検出
- MLX90614（0x5A）検出確認
- AXP192（0x34）検出確認

**スキャン範囲:** 0x08 ～ 0x77

**出力例:**
```
=== I2C Device Scan (G0/G26) ===
SDA: GPIO26, SCL: GPIO0
Note: GPIO0 shared with Button A

I2C device found at 0x34 (AXP192 - Power Management)
I2C device found at 0x5A (MLX90614 - Temperature Sensor)
Total devices found: 2
```

### 5.2 センサー初期化診断

**チェック項目:**
1. I2Cバス準備確認
2. MLX90614通信確立
3. テスト読み取り（3回）
4. データ範囲検証

**リトライロジック:**
- 最大3回試行
- 各試行間に2秒待機
- 失敗時の詳細エラーメッセージ

### 5.3 GPIO36アナログ監視

**機能:**
- 12bit ADC (0-4095)
- 10サンプル平均
- 電圧換算 (0-3.3V)

**計算式:**
```cpp
float voltage = (adc_average / 4095.0) * 3.3;
```

---

## 6. バッテリー管理

### 6.1 AXP192電源管理

**測定項目:**
- バッテリー電圧（V）
- バッテリー残量（%）

**残量計算:**
```cpp
float getBatteryLevel() {
  float voltage = M5.Axp.GetBatVoltage();
  float percentage = (voltage - 3.0) / (4.2 - 3.0) * 100.0;
  return constrain(percentage, 0.0, 100.0);
}
```

**電圧範囲:**
- 最大: 4.2V (満充電)
- 最小: 3.0V (空)

---

## 7. WiFi接続管理

### 7.1 接続設定

```cpp
#define WIFI_SSID "bsf"
#define WIFI_PASSWORD "08230823"
#define WIFI_TIMEOUT 20000  // 20秒タイムアウト
```

### 7.2 再接続ロジック

**自動再接続:**
- WiFi切断検出（毎ループ）
- 30秒間隔で再接続試行
- 再接続成功時にMQTT再接続

---

## 8. MQTT設定

### 8.1 ブローカー設定

```cpp
#define MQTT_SERVER "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_USER "bsf_sensor"
#define MQTT_PASSWORD "bsf_password"
#define MQTT_RECONNECT_INTERVAL 30000  // 30秒
```

### 8.2 クライアントID

**動的生成:**
```cpp
String clientId = String(DEVICE_ID) + "_" + String(random(0xffff), HEX);
```

**例:** `m5stick-temp-01_a3f2`

### 8.3 デバイス情報送信

**送信トピック:**
```
bsf/sensors/m5stick-temp-01/info
```

**ペイロード:**
```json
{
  "device_id": "m5stick-temp-01",
  "name": "M5StickC Temperature Sensor",
  "firmware": "1.4.0",
  "sensor": "MLX90614",
  "pins": {
    "sda": 26,
    "scl": 0,
    "analog": 36
  },
  "features": {
    "analog_monitoring": true
  }
}
```

---

## 9. エラーハンドリング

### 9.1 センサーエラー

**エラータイプ:**
- `I2C not ready`: I2Cバス初期化失敗
- `Communication failed`: MLX90614通信失敗
- `Read test failed`: データ読み取り失敗
- `NaN read`: 不正な数値
- `Range error`: 測定範囲外

**エラー表示:**
- ディスプレイに赤色で表示
- シリアルログ出力
- MQTTステータス送信

### 9.2 接続エラー

**WiFiエラー:**
```cpp
if (WiFi.status() != WL_CONNECTED) {
  sys_status.wifi_connected = false;
  reconnectWiFi();
}
```

**MQTTエラー:**
```cpp
if (!client.connected()) {
  sys_status.mqtt_connected = false;
  reconnectMQTT();
}
```

---

## 10. デバッグ

### 10.1 シリアルモニター出力

**ボーレート:** 115200

**起動ログ例:**
```
==================================================
M5StickC + MLX90614 Temperature Sensor
Optimized G0/G26/G36 Pin Configuration
Firmware: 1.4.0
==================================================

🔧 Starting System Diagnostics...
Initializing I2C with G0/G26 pins...
I2C Clock: 100000 Hz
SDA Pin: GPIO26 (General Purpose)
SCL Pin: GPIO0 (Button A shared)
I2C bus initialized

=== I2C Device Scan (G0/G26) ===
I2C device found at 0x34 (AXP192 - Power Management)
I2C device found at 0x5A (MLX90614 - Temperature Sensor)
Total devices found: 2

=== Sensor Initialization (G0/G26) ===
Attempt 1: Initializing MLX90614...
Test read 1: Ambient=25.50°C, Object=30.20°C
✓ Sensor initialization successful

📊 Testing GPIO36 analog input...
GPIO36 analog value: 1.234V

📶 Connecting to WiFi...
Connecting to WiFi......... ✓ Connected!
IP: 192.168.1.150

📡 Setting up MQTT...
Connecting to MQTT 192.168.1.100:1883...
✓ MQTT Connected!

==================================================
📊 SYSTEM DIAGNOSTIC RESULTS
==================================================
I2C Bus:    ✓ OK (G26/G0)
MLX90614:   ✓ OK
WiFi:       ✓ OK
GPIO36:     1.234V (Active)
Battery:    3.80V (85%)
==================================================
🎉 System ready for operation!
Temperature: Ambient=25.50°C, Object=30.20°C
```

### 10.2 デバッグモード有効化

**コンパイル時定義:**
```cpp
#define DEBUG_MODE 1
#define VERBOSE_LOGGING 1
```

---

## 11. ファームウェアアップデート

### 11.1 Arduino IDE設定

**ボード:** ESP32 Dev Module
**Upload Speed:** 115200
**Flash Frequency:** 80MHz
**Flash Mode:** QIO
**Flash Size:** 4MB (32Mb)
**Partition Scheme:** Default

### 11.2 OTA対応（将来計画）

- WiFi経由ファームウェア更新
- バージョン管理
- ロールバック機能

---

## 12. 電力管理

### 12.1 消費電力

**動作モード:**
- アクティブ: 約100-150mA
- WiFi送信: 約200-300mA（ピーク）
- ディスプレイOFF: 約80mA

**バッテリー寿命:**
- 95mAh ÷ 120mA ≈ 0.8時間（連続動作）
- 実用: 約30-60分（表示・通信あり）

### 12.2 省電力化（将来対応）

- Deep Sleep モード
- WiFi省電力設定
- ディスプレイ自動オフ
- 測定間隔の動的調整

---

## 13. キャリブレーション

### 13.1 温度オフセット調整

**補正式:**
```cpp
float calibrated_temp = raw_temp + TEMP_OFFSET;
```

**推奨キャリブレーション:**
1. 既知温度の基準と比較
2. オフセット値を算出
3. ファームウェアに反映

---

## 14. トラブルシューティング

### 14.1 センサー未検出

**症状:** MLX90614が検出されない

**確認事項:**
1. 配線確認（SDA/SCL/VCC/GND）
2. プルアップ抵抗（4.7kΩ）
3. I2Cアドレス（0x5A）
4. センサー電源（3.3V）

### 14.2 WiFi接続失敗

**症状:** WiFi に接続できない

**確認事項:**
1. SSID/パスワード正確性
2. WiFiルーター電源
3. 信号強度（RSSI > -80dBm）
4. 2.4GHz帯対応確認

### 14.3 MQTT接続失敗

**症状:** MQTT ブローカーに接続できない

**確認事項:**
1. ブローカーIPアドレス
2. ポート番号（1883）
3. 認証情報
4. ネットワーク疎通確認

---

## 15. 今後の拡張

- [ ] TLS/SSL MQTT対応
- [ ] OTA ファームウェア更新
- [ ] Deep Sleep モード
- [ ] SDカードログ記録
- [ ] 複数センサー対応（I2C マルチプレクサ）
- [ ] LoRaWAN対応版
- [ ] バッテリー拡張モジュール対応
