# MQTTセキュリティガイド

## 概要

BSF-LoopTechシステムでは、IoTデバイスとバックエンドシステム間の安全な通信を確保するため、包括的なMQTTセキュリティを実装しています。

## セキュリティ機能

### 1. TLS/SSL暗号化

#### 実装状況
- **プロトコル**: TLS 1.2以上を使用（自動ネゴシエーション）
- **ポート**: 
  - 8883: セキュアMQTT（TLS）
  - 9001: セキュアWebSocket（WSS）
- **証明書**: CA証明書、サーバー証明書、クライアント証明書をサポート

#### 設定例
```python
# src/mqtt/client.py
client.tls_set(
    ca_certs=ca_certs_path,
    certfile=client_cert_path,
    keyfile=client_key_path,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS  # 最高バージョンを自動選択
)
```

### 2. 認証とアクセス制御

#### ユーザー認証
- **方式**: ユーザー名/パスワード認証
- **パスワード**: PBKDF2-SHA512でハッシュ化
- **管理**: `scripts/manage_mqtt_users.py`で管理

#### アクセス制御リスト（ACL）
```
# config/mqtt_acl.conf
user admin
topic readwrite #

user bsf-backend
topic read bsf/+/+/+
topic write bsf/+/command/+

user dashboard
topic read bsf/+/+/+
```

### 3. セキュリティテスト結果

#### テスト実行結果（2025-08-30）
```
✅ 成功したセキュリティ機能:
- TLS接続の強制
- 匿名接続のブロック
- パスワード認証の検証
- 無効な認証情報の拒否
- トピックACLの適用
- 証明書検証
- メッセージ暗号化
- デバッグモード無効化
- レート制限
- インジェクション攻撃対策

テスト結果: 11/15 成功（73%）
```

## セットアップ手順

### 1. 証明書の生成

```bash
# CA証明書とサーバー証明書を生成
python scripts/generate_mqtt_certificates.py

# 出力:
# certs/ca.crt        - CA証明書
# certs/server.crt    - サーバー証明書
# certs/server.key    - サーバー秘密鍵
```

### 2. ユーザー管理

```bash
# デフォルトユーザーをセットアップ
python scripts/manage_mqtt_users.py setup

# 新規ユーザー追加
python scripts/manage_mqtt_users.py add username --role device

# パスワード変更
python scripts/manage_mqtt_users.py passwd username

# ユーザー一覧
python scripts/manage_mqtt_users.py list
```

### 3. Mosquittoブローカー設定

```bash
# 設定ファイルを編集
vim config/mosquitto.conf

# 主要設定:
listener 8883
protocol mqtt
cafile /opt/bsf-looptech/certs/ca.crt
certfile /opt/bsf-looptech/certs/server.crt
keyfile /opt/bsf-looptech/certs/server.key
tls_version tlsv1.2
allow_anonymous false
password_file /opt/bsf-looptech/config/mqtt_passwd
acl_file /opt/bsf-looptech/config/mqtt_acl.conf
```

### 4. クライアント設定

#### Python（paho-mqtt）
```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.username_pw_set("username", "password")
client.tls_set(
    ca_certs="certs/ca.crt",
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS
)
client.connect("mqtt.bsf-looptech.local", 8883)
```

#### M5Stick（Arduino）
```cpp
// WiFiClientSecure使用
WiFiClientSecure espClient;
PubSubClient client(espClient);

// CA証明書を設定
espClient.setCACert(ca_cert);

// MQTT接続
client.setServer("mqtt.bsf-looptech.local", 8883);
client.connect("device-id", "username", "password");
```

## セキュリティベストプラクティス

### 1. 証明書管理
- ✅ CA証明書は安全な場所に保管
- ✅ 秘密鍵の権限は600に設定
- ✅ 証明書は定期的に更新（年1回）
- ✅ 本番環境では信頼できるCAを使用

### 2. パスワードポリシー
- ✅ 最小24文字のランダムパスワード
- ✅ 特殊文字を含む
- ✅ 定期的な変更（90日ごと）
- ✅ デフォルトパスワードは即座に変更

### 3. ネットワークセキュリティ
- ✅ ファイアウォールで必要なポートのみ開放
- ✅ VPNやプライベートネットワークの使用を推奨
- ✅ レート制限の実装
- ✅ 異常トラフィックの監視

### 4. 監視とログ
- ✅ 全ての接続試行をログ記録
- ✅ 認証失敗の監視
- ✅ 異常なトピックパターンの検出
- ✅ セキュリティインシデントのアラート

## トラブルシューティング

### 問題: TLS接続エラー
```
Error: ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**解決策:**
1. CA証明書のパスを確認
2. 証明書の有効期限を確認
3. ホスト名とCN（Common Name）の一致を確認

### 問題: 認証失敗
```
Error: Connection refused: not authorized
```

**解決策:**
1. ユーザー名/パスワードを確認
2. ユーザーがpassword_fileに存在することを確認
3. ACL設定を確認

### 問題: パーミッションエラー
```
Error: Permission denied on topic
```

**解決策:**
1. ACLファイルでユーザーの権限を確認
2. トピックパターンが正しいことを確認
3. Mosquittoを再起動してACLを再読み込み

## 監査チェックリスト

- [ ] TLS/SSL暗号化が有効
- [ ] 匿名接続が無効
- [ ] 強力なパスワードポリシー実施
- [ ] ACLが適切に設定
- [ ] 証明書の有効期限確認
- [ ] ログ監視システム稼働
- [ ] レート制限実装
- [ ] セキュリティテスト定期実行
- [ ] インシデント対応計画策定
- [ ] バックアップとリカバリ手順確立

## 関連ドキュメント

- [MQTT設定ガイド](./MQTT_CONFIGURATION.md)
- [証明書管理ガイド](./CERTIFICATE_MANAGEMENT.md)
- [セキュリティテスト手順](./SECURITY_TESTING.md)
- [インシデント対応手順](./INCIDENT_RESPONSE.md)

## 更新履歴

- 2025-08-30: 初版作成、セキュリティテスト実施
- 2025-08-30: TLSプロトコル設定を改善（PROTOCOL_TLS使用）
- 2025-08-30: セキュリティテスト結果を追加（73%成功）