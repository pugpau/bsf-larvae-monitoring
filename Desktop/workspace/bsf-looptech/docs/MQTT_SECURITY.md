# MQTT セキュリティ設定ガイド

## 概要

このドキュメントでは、BSF-LoopTechプロジェクトにおけるMQTTブローカー（Mosquitto）のセキュリティ設定について説明します。

## セキュリティ機能

### 1. TLS/SSL暗号化

- **ポート**: 8883（MQTT over TLS）、9001（WebSocket over TLS）
- **TLSバージョン**: TLS 1.2以上
- **証明書**: CA証明書、サーバー証明書、クライアント証明書（オプション）

### 2. 認証

- **方式**: ユーザー名/パスワード認証
- **匿名アクセス**: 無効化
- **パスワード管理**: mosquitto_passwdによるハッシュ化

### 3. アクセス制御（ACL）

- **ユーザー別権限**: 読み取り、書き込み、読み書き
- **トピック別制御**: パターンマッチングによる細かい制御
- **デフォルトポリシー**: 最小権限の原則

## セットアップ手順

### 1. 証明書の生成

```bash
# 開発環境用の自己署名証明書を生成
python scripts/generate_mqtt_certificates.py \
  --hostname localhost \
  --client-ids device1 device2 \
  --show-config

# 本番環境ではLet's Encryptなどの正式な証明書を使用
```

### 2. ユーザーの作成

```bash
# デフォルトユーザーをセットアップ
python scripts/manage_mqtt_users.py setup

# 個別ユーザーの追加
python scripts/manage_mqtt_users.py add <username> --password <password>

# ユーザー一覧の確認
python scripts/manage_mqtt_users.py list
```

### 3. Mosquittoの設定

```bash
# 設定ファイルをコピー
sudo cp config/mosquitto.conf /etc/mosquitto/mosquitto.conf
sudo cp config/mqtt_acl.conf /opt/bsf-looptech/config/
sudo cp config/mqtt_passwd /opt/bsf-looptech/config/

# 証明書をコピー
sudo cp -r certs /opt/bsf-looptech/

# Mosquittoを再起動
sudo systemctl restart mosquitto
```

### 4. クライアント設定

#### Python クライアント（backend）

```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.username_pw_set("bsf-backend", "password")
client.tls_set(
    ca_certs="/path/to/ca.crt",
    certfile=None,  # クライアント証明書（オプション）
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.connect("mqtt.bsf-looptech.com", 8883, 60)
```

#### M5StickC デバイス

```cpp
// Arduino IDE
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

WiFiClientSecure espClient;
PubSubClient client(espClient);

// CA証明書を設定
const char* ca_cert = R"EOF(
-----BEGIN CERTIFICATE-----
... CA証明書の内容 ...
-----END CERTIFICATE-----
)EOF";

espClient.setCACert(ca_cert);
client.setServer("mqtt.bsf-looptech.com", 8883);
```

## ACL設定詳細

### ユーザー権限

| ユーザー | 権限 | 説明 |
|---------|------|------|
| admin | 全トピック読み書き | システム管理者 |
| bsf-backend | センサーデータ読み取り、コマンド送信 | バックエンドサーバー |
| dashboard | センサーデータ読み取り専用 | ダッシュボード表示用 |
| alert-system | センサーデータ読み取り、アラート送信 | アラートシステム |
| device_* | 自デバイストピックへの書き込み | M5Stickデバイス |

### トピック構造

```
bsf/
├── {farm_id}/
│   ├── sensor/
│   │   └── {device_id}        # センサーデータ
│   ├── environmental/
│   │   └── {device_id}        # 環境データ
│   └── command/
│       └── {device_id}        # デバイスへのコマンド
├── system/
│   ├── status/
│   │   ├── health            # ヘルスチェック
│   │   └── version           # バージョン情報
│   └── config/               # システム設定（機密）
└── alerts/
    └── {alert_type}          # アラート通知
```

## セキュリティベストプラクティス

### 1. 証明書管理

- 証明書の定期的な更新（年次）
- 秘密鍵の安全な保管
- 証明書の有効期限監視

### 2. パスワード管理

- 強力なパスワードの使用（16文字以上）
- 定期的なパスワード変更
- パスワードの安全な共有方法

### 3. ネットワークセキュリティ

- ファイアウォールでポートを制限
- VPNの利用を検討
- 侵入検知システムの導入

### 4. 監査とログ

- アクセスログの定期的な確認
- 異常なアクセスパターンの検知
- セキュリティインシデントへの対応計画

## トラブルシューティング

### TLS接続エラー

```bash
# 証明書の検証
openssl s_client -connect localhost:8883 -CAfile certs/ca.crt

# ログの確認
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### 認証エラー

```bash
# ユーザーの確認
python scripts/manage_mqtt_users.py list

# パスワードのリセット
python scripts/manage_mqtt_users.py update <username>
```

### ACLエラー

```bash
# ACL設定の確認
sudo mosquitto_sub -h localhost -p 8883 \
  --cafile certs/ca.crt \
  -u <username> -P <password> \
  -t "bsf/+/+/+" -v
```

## 参考リンク

- [Mosquitto Documentation](https://mosquitto.org/documentation/)
- [MQTT Security Fundamentals](https://www.hivemq.com/mqtt-security-fundamentals/)
- [TLS Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)