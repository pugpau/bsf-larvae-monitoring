# バックエンドAPI仕様

## ドキュメント情報
- **バージョン**: 0.1.0
- **最終更新**: 2025-10-01
- **API フレームワーク**: FastAPI
- **Python バージョン**: 3.10+

---

## 1. アーキテクチャ概要

### 1.1 アプリケーション構造

```
src/
├── main.py                   # FastAPIメインアプリケーション
├── config.py                 # 環境設定管理
├── api/                      # APIエンドポイント
│   └── routes/
│       ├── auth.py           # 認証API
│       ├── sensors.py        # センサーAPI
│       ├── substrate.py      # 基質管理API
│       ├── analytics.py      # 分析API
│       └── websocket.py      # WebSocket通信
├── auth/                     # 認証・認可
│   ├── models.py             # 認証モデル
│   ├── security.py           # セキュリティ機能
│   ├── middleware.py         # 認証ミドルウェア
│   └── repository.py         # 認証データ操作
├── database/                 # データベース管理
│   ├── postgresql.py         # PostgreSQL接続
│   ├── influxdb.py           # InfluxDB接続
│   └── connection_pool.py    # コネクションプール
├── sensors/                  # センサーロジック
│   ├── models.py             # センサーモデル
│   ├── service.py            # センサーサービス
│   └── repository.py         # センサーデータ操作
├── substrate/                # 基質管理
│   ├── models.py             # 基質モデル
│   ├── service.py            # 基質サービス
│   └── repository.py         # 基質データ操作
├── analytics/                # データ分析
│   ├── models.py             # 分析モデル
│   ├── anomaly_detector.py   # 異常検知
│   ├── prediction_service.py # 予測サービス
│   └── statistics.py         # 統計分析
├── mqtt/                     # MQTT通信
│   ├── client.py             # MQTTクライアント
│   └── optimized_client.py   # 最適化版クライアント
├── realtime/                 # リアルタイム処理
│   ├── sensor_streamer.py    # センサーストリーム
│   └── alert_manager.py      # アラート管理
└── utils/                    # ユーティリティ
    └── logging.py            # ロギング設定
```

### 1.2 技術スタック

| コンポーネント | 技術 | バージョン |
|-------------|------|-----------|
| **Webフレームワーク** | FastAPI | latest |
| **ASGIサーバー** | Uvicorn | standard |
| **非同期処理** | asyncio, asyncpg | - |
| **データベースORM** | SQLAlchemy | >=1.4.0 |
| **マイグレーション** | Alembic | latest |
| **時系列DB** | InfluxDB Client | latest |
| **MQTT** | paho-mqtt | latest |
| **認証** | python-jose, passlib | latest |
| **データ処理** | pandas, numpy, scipy | latest |
| **機械学習** | scikit-learn | latest |

---

## 2. 環境設定

### 2.1 環境変数 (config.py)

```python
# MQTT設定
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=bsf_sensor
MQTT_PASSWORD=bsf_password
MQTT_TLS_ENABLED=true
MQTT_CA_CERTS=/app/certs/ca.crt
MQTT_CLIENT_CERT=/app/certs/mqtt-client.crt
MQTT_CLIENT_KEY=/app/certs/mqtt-client.key

# InfluxDB設定
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=bsf-secret-token
INFLUXDB_ORG=bsf_org
INFLUXDB_BUCKET=bsf_data

# PostgreSQL設定
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=bsf_user
POSTGRES_PASSWORD=bsf_password
POSTGRES_DB=bsf_system
DATABASE_URL=postgresql+asyncpg://...

# セキュリティ
SECRET_KEY=your-secret-key
LOG_LEVEL=INFO

# ERP連携 (将来用)
ERP_API_ENDPOINT=https://erp.example.com/api
ERP_API_KEY=your-erp-api-key
```

---

## 3. データモデル

### 3.1 センサーデータモデル

#### SensorReading (センサー読み取り)
```python
{
  "id": "uuid",
  "farm_id": "farm123",
  "device_id": "sensor001",
  "device_type": "temperature",
  "timestamp": "2025-10-01T10:00:00Z",
  "measurement_type": "temperature",
  "value": 25.5,
  "unit": "°C",
  "location": "area1",
  "substrate_batch_id": "batch123",
  "x_position": 10.5,
  "y_position": 20.3,
  "z_position": 5.0,
  "metadata": {}
}
```

#### SensorDevice (センサーデバイス)
```python
{
  "id": "uuid",
  "farm_id": "farm123",
  "device_id": "sensor001",
  "device_type": "temperature",
  "name": "温度センサー1号機",
  "description": "エリア1温度監視用",
  "location": "area1",
  "x_position": 10.5,
  "y_position": 20.3,
  "z_position": 5.0,
  "status": "active",  // active, inactive, maintenance
  "last_seen": "2025-10-01T10:00:00Z",
  "substrate_batch_id": "batch123",
  "metadata": {},
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-10-01T10:00:00Z"
}
```

### 3.2 認証モデル

#### User (ユーザー)
```python
{
  "id": "uuid",
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "管理者",
  "role": "admin",  // admin, operator, viewer
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-10-01T10:00:00Z"
}
```

#### Token (認証トークン)
```python
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 3.3 基質管理モデル

#### SubstrateType (基質タイプ)
```python
{
  "id": "uuid",
  "name": "下水汚泥",
  "description": "処理済み下水汚泥",
  "category": "organic_waste",
  "properties": {
    "moisture_content": 80.0,
    "organic_matter": 60.0,
    "nitrogen_content": 3.5
  },
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### SubstrateBatch (基質バッチ)
```python
{
  "id": "uuid",
  "batch_number": "BATCH-2025-001",
  "substrate_type_id": "uuid",
  "start_date": "2025-01-01",
  "end_date": "2025-01-15",
  "quantity": 1000.0,
  "unit": "kg",
  "location": "area1",
  "status": "active",
  "composition": [
    {"substrate_type_id": "uuid1", "percentage": 60.0},
    {"substrate_type_id": "uuid2", "percentage": 40.0}
  ],
  "metadata": {}
}
```

---

## 4. APIエンドポイント

### 4.1 認証エンドポイント (`/auth`)

#### POST `/auth/login`
**ユーザーログイン**

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

#### POST `/auth/refresh`
**トークンリフレッシュ**

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### GET `/auth/me`
**現在のユーザー情報取得**

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "管理者",
  "role": "admin",
  "is_active": true
}
```

### 4.2 センサーエンドポイント (`/sensors`)

#### POST `/sensors/readings`
**センサーデータ登録**

**Request:**
```json
{
  "farm_id": "farm123",
  "device_id": "sensor001",
  "device_type": "temperature",
  "measurement_type": "temperature",
  "value": 25.5,
  "unit": "°C",
  "location": "area1",
  "substrate_batch_id": "batch123"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "farm_id": "farm123",
  "device_id": "sensor001",
  "timestamp": "2025-10-01T10:00:00Z",
  "measurement_type": "temperature",
  "value": 25.5,
  "unit": "°C"
}
```

#### GET `/sensors/readings`
**センサーデータ取得（フィルタ付き）**

**Query Parameters:**
- `farm_id` (required): ファームID
- `device_type` (optional): デバイスタイプフィルタ
- `device_id` (optional): デバイスIDフィルタ
- `measurement_type` (optional): 計測タイプフィルタ
- `location` (optional): ロケーションフィルタ
- `substrate_batch_id` (optional): バッチIDフィルタ
- `start_time` (optional): 開始時刻 (ISO 8601)
- `end_time` (optional): 終了時刻 (ISO 8601)
- `limit` (optional): 取得件数制限 (デフォルト: 100)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "farm_id": "farm123",
    "device_id": "sensor001",
    "device_type": "temperature",
    "timestamp": "2025-10-01T10:00:00Z",
    "measurement_type": "temperature",
    "value": 25.5,
    "unit": "°C",
    "location": "area1"
  }
]
```

#### GET `/sensors/readings/latest`
**最新センサーデータ取得**

**Query Parameters:**
- `farm_id` (required): ファームID
- `device_type` (optional): デバイスタイプフィルタ
- `location` (optional): ロケーションフィルタ

**Response:** `200 OK`
```json
{
  "sensor001": {
    "id": "uuid",
    "device_id": "sensor001",
    "timestamp": "2025-10-01T10:00:00Z",
    "value": 25.5,
    "unit": "°C"
  },
  "sensor002": { ... }
}
```

#### POST `/sensors/devices`
**センサーデバイス登録**

**Request:**
```json
{
  "farm_id": "farm123",
  "device_id": "sensor001",
  "device_type": "temperature",
  "name": "温度センサー1号機",
  "location": "area1",
  "x_position": 10.5,
  "y_position": 20.3,
  "z_position": 5.0
}
```

**Response:** `201 Created`

#### GET `/sensors/devices`
**センサーデバイス一覧取得**

**Response:** `200 OK`

#### GET `/sensors/devices/{device_id}`
**センサーデバイス詳細取得**

**Response:** `200 OK`

#### PUT `/sensors/devices/{device_id}`
**センサーデバイス更新**

**Response:** `200 OK`

#### DELETE `/sensors/devices/{device_id}`
**センサーデバイス削除**

**Response:** `204 No Content`

### 4.3 基質管理エンドポイント (`/substrate`)

#### POST `/substrate/types`
**基質タイプ作成**

**Request:**
```json
{
  "name": "下水汚泥",
  "description": "処理済み下水汚泥",
  "category": "organic_waste",
  "properties": {
    "moisture_content": 80.0,
    "organic_matter": 60.0
  }
}
```

**Response:** `201 Created`

#### GET `/substrate/types`
**基質タイプ一覧取得**

**Response:** `200 OK`

#### POST `/substrate/batches`
**基質バッチ作成**

**Request:**
```json
{
  "batch_number": "BATCH-2025-001",
  "substrate_type_id": "uuid",
  "start_date": "2025-01-01",
  "quantity": 1000.0,
  "unit": "kg",
  "location": "area1",
  "composition": [
    {"substrate_type_id": "uuid1", "percentage": 60.0}
  ]
}
```

**Response:** `201 Created`

#### GET `/substrate/batches`
**基質バッチ一覧取得**

**Response:** `200 OK`

#### GET `/substrate/batches/{batch_id}`
**基質バッチ詳細取得**

**Response:** `200 OK`

### 4.4 分析エンドポイント (`/analytics`)

#### GET `/analytics/statistics`
**統計データ取得**

**Query Parameters:**
- `farm_id`: ファームID
- `start_time`: 開始時刻
- `end_time`: 終了時刻
- `measurement_type`: 計測タイプ

**Response:** `200 OK`
```json
{
  "temperature": {
    "mean": 25.5,
    "std_dev": 2.3,
    "min": 20.0,
    "max": 30.0,
    "count": 1440
  }
}
```

#### GET `/analytics/trends`
**トレンド分析データ取得**

**Response:** `200 OK`

#### GET `/analytics/anomalies`
**異常検知結果取得**

**Response:** `200 OK`
```json
[
  {
    "timestamp": "2025-10-01T10:00:00Z",
    "device_id": "sensor001",
    "measurement_type": "temperature",
    "value": 45.0,
    "anomaly_score": 0.95,
    "severity": "high"
  }
]
```

### 4.5 WebSocketエンドポイント (`/ws`)

#### WS `/ws/sensors`
**リアルタイムセンサーデータ配信**

**接続パラメータ:**
```
ws://localhost:8000/ws/sensors?token=<auth_token>&farm_id=farm123
```

**受信メッセージフォーマット:**
```json
{
  "type": "sensor_reading",
  "data": {
    "device_id": "sensor001",
    "timestamp": "2025-10-01T10:00:00Z",
    "measurement_type": "temperature",
    "value": 25.5,
    "unit": "°C"
  }
}
```

#### WS `/ws/alerts`
**リアルタイムアラート配信**

**受信メッセージフォーマット:**
```json
{
  "type": "alert",
  "data": {
    "alert_id": "uuid",
    "device_id": "sensor001",
    "severity": "high",
    "message": "温度が閾値を超えました",
    "timestamp": "2025-10-01T10:00:00Z"
  }
}
```

### 4.6 ヘルスチェックエンドポイント

#### GET `/health`
**システムヘルスチェック**

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "services": {
    "api": "ok",
    "postgresql": "ok",
    "influxdb": "ok",
    "mqtt": "ok"
  },
  "details": {}
}
```

---

## 5. 認証・セキュリティ

### 5.1 JWT認証

**トークン構造:**
```json
{
  "sub": "user_id",
  "username": "admin",
  "role": "admin",
  "exp": 1633072800
}
```

**トークン有効期限:** 1時間
**リフレッシュトークン:** 7日間

### 5.2 ミドルウェア

#### AuthenticationMiddleware
- JWTトークン検証
- ユーザー情報抽出
- 権限チェック
- 除外パス: `/docs`, `/health`, `/auth/login`

#### RateLimitMiddleware
- レート制限: 60 requests/分
- IPベース制限
- 超過時: `429 Too Many Requests`

#### CORSMiddleware
- 許可オリジン: `http://localhost:3000`, `http://localhost:3001`
- 許可メソッド: 全て
- 認証情報: 許可

### 5.3 パスワードセキュリティ

- **ハッシュアルゴリズム**: BCrypt
- **ソルト**: 自動生成
- **強度要件**: 8文字以上

---

## 6. データベース設計

### 6.1 PostgreSQL (メタデータ)

**テーブル:**
- `users` - ユーザー情報
- `sensor_devices` - センサーデバイス情報
- `substrate_types` - 基質タイプ
- `substrate_batches` - 基質バッチ
- `alerts` - アラート定義
- `thresholds` - 閾値設定

### 6.2 InfluxDB (時系列データ)

**Measurement:** `sensor_readings`

**Tags:**
- `farm_id`
- `device_id`
- `device_type`
- `measurement_type`
- `location`

**Fields:**
- `value` (float)
- `unit` (string)

---

## 7. エラーハンドリング

### 7.1 HTTPステータスコード

| コード | 説明 |
|-------|------|
| 200 | 成功 |
| 201 | 作成成功 |
| 204 | 削除成功（レスポンスなし） |
| 400 | リクエストエラー |
| 401 | 認証エラー |
| 403 | 権限エラー |
| 404 | リソース未検出 |
| 422 | バリデーションエラー |
| 429 | レート制限超過 |
| 500 | サーバーエラー |

### 7.2 エラーレスポンス形式

```json
{
  "detail": "エラーメッセージ",
  "type": "ValidationError",
  "errors": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 8. ロギング

### 8.1 ログレベル

- **DEBUG**: 詳細デバッグ情報
- **INFO**: 一般情報（デフォルト）
- **WARNING**: 警告
- **ERROR**: エラー
- **CRITICAL**: クリティカルエラー

### 8.2 ログフォーマット

```
2025-10-01 10:00:00 [INFO] main: Starting BSF API
2025-10-01 10:00:01 [INFO] main: Successfully connected to PostgreSQL
2025-10-01 10:00:02 [ERROR] sensors: Failed to read sensor data: Connection timeout
```

---

## 9. パフォーマンス最適化

### 9.1 非同期処理
- `async/await` パターン
- `asyncpg` による非同期PostgreSQL接続
- 非同期MQTT処理

### 9.2 コネクションプール
- PostgreSQL: 最大20接続
- InfluxDB: 再利用可能接続

### 9.3 キャッシング
- メモリキャッシュ（閾値設定等）
- データ圧縮（InfluxDB）

---

## 10. テスト

### 10.1 テストフレームワーク
- **pytest**: 単体テスト・統合テスト
- **pytest-asyncio**: 非同期テスト

### 10.2 テストカバレッジ目標
- **全体**: 80%以上
- **コアロジック**: 90%以上

---

## 11. デプロイメント

### 11.1 Docker構成
```yaml
backend:
  build: Dockerfile.backend
  ports: ["8000:8000"]
  environment:
    - DATABASE_URL
    - INFLUXDB_URL
    - MQTT_BROKER_HOST
```

### 11.2 起動コマンド
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

---

## 12. API ドキュメント

### 12.1 Swagger UI
- URL: `http://localhost:8000/docs`
- OpenAPI 3.0仕様

### 12.2 ReDoc
- URL: `http://localhost:8000/redoc`
- 読みやすいドキュメント形式

---

## 13. 今後の拡張

- [ ] GraphQL API対応
- [ ] gRPC通信対応
- [ ] マルチテナント対応
- [ ] ERP連携API実装
- [ ] 機械学習モデルAPI統合
