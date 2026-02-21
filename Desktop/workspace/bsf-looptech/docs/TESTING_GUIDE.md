# テストガイド

## 概要

BSF-LoopTechプロジェクトでは、包括的なテストスイートを提供しています。このガイドでは、テストの実行方法、テスト作成のベストプラクティス、トラブルシューティングについて説明します。

## テスト構造

```
tests/
├── __init__.py                 # テストパッケージ初期化
├── conftest.py                 # 共通フィクスチャと設定
├── pytest.ini                 # Pytest設定
├── unit/                       # ユニットテスト
│   ├── test_auth.py           # 認証機能テスト
│   ├── test_mqtt_client.py    # MQTTクライアントテスト
│   └── ...
├── integration/               # 統合テスト
│   ├── test_api_endpoints.py  # APIエンドポイントテスト
│   ├── test_mqtt_integration.py # MQTT統合テスト
│   └── ...
└── e2e/                       # エンドツーエンドテスト
    └── test_full_workflow.py  # 完全ワークフローテスト
```

## テストの実行

### 1. 基本的な実行方法

```bash
# 全てのテストを実行
python scripts/run_tests.py all

# 特定のテストタイプを実行
python scripts/run_tests.py unit           # ユニットテスト
python scripts/run_tests.py integration    # 統合テスト
python scripts/run_tests.py e2e           # エンドツーエンドテスト

# 高速テスト（slowマーカーを除外）
python scripts/run_tests.py fast

# 詳細出力付き
python scripts/run_tests.py unit -v
```

### 2. 特定の機能テスト

```bash
# MQTTテスト
python scripts/run_tests.py mqtt

# 認証テスト
python scripts/run_tests.py auth

# データベーステスト
python scripts/run_tests.py database

# パフォーマンステスト
python scripts/run_tests.py performance
```

### 3. 特定のファイルやテスト関数

```bash
# 特定のテストファイル
python scripts/run_tests.py run tests/unit/test_auth.py

# 特定のテストクラス
python scripts/run_tests.py run tests/unit/test_auth.py::TestAuthService

# 特定のテスト関数
python scripts/run_tests.py run tests/unit/test_auth.py::TestAuthService::test_create_user_success
```

### 4. カバレッジレポート

```bash
# カバレッジ付きテスト実行
python scripts/run_tests.py coverage

# HTMLレポート生成
python scripts/run_tests.py coverage --html
# HTMLレポートは htmlcov/index.html で確認
```

## Pytestの直接利用

```bash
# 基本実行
pytest

# 特定のマーカー
pytest -m unit           # ユニットテストのみ
pytest -m "not slow"     # slowマーカーを除外
pytest -m "mqtt and integration"  # 複数条件

# 並列実行（pytest-xdistが必要）
pytest -n auto

# 失敗時のデバッグ
pytest --pdb            # 失敗時にデバッガー起動
pytest -s               # print文の出力を表示
pytest --tb=long        # 詳細なトレースバック
```

## テストマーカー

| マーカー | 説明 |
|---------|------|
| `unit` | ユニットテスト（単一コンポーネント） |
| `integration` | 統合テスト（複数コンポーネント） |
| `e2e` | エンドツーエンドテスト（完全ワークフロー） |
| `slow` | 実行時間が長いテスト（5秒以上） |
| `mqtt` | MQTTブローカーが必要 |
| `database` | データベースが必要 |
| `auth` | 認証機能のテスト |
| `performance` | パフォーマンステスト |
| `smoke` | スモークテスト（基本動作確認） |

## テスト環境の準備

### 1. 依存関係の確認

```bash
# 依存関係チェック
python scripts/run_tests.py check

# 必要なパッケージのインストール
pip install pytest pytest-asyncio httpx pytest-cov
```

### 2. 外部サービス

#### MQTTブローカー（Mosquitto）

```bash
# インストール
brew install mosquitto

# 起動
brew services start mosquitto

# または手動起動
mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf
```

#### InfluxDB（オプション）

```bash
# Dockerで起動
docker run -d -p 8086:8086 influxdb:2.7

# または直接インストール
brew install influxdb
brew services start influxdb
```

## フィクスチャとヘルパー

### 主要なフィクスチャ

```python
@pytest.fixture
async def async_session():
    """非同期データベースセッション"""

@pytest.fixture
def test_client():
    """FastAPIテストクライアント"""

@pytest.fixture
def auth_headers(test_user):
    """認証ヘッダー"""

@pytest.fixture
def mock_mqtt_client():
    """モックMQTTクライアント"""

@pytest.fixture
def sample_sensor_data():
    """サンプルセンサーデータ"""
```

### テストヘルパー

```python
# conftest.pyのTestHelpersクラス
def test_example(test_helpers):
    # モックMQTTメッセージ作成
    message = test_helpers.create_mock_mqtt_message(topic, payload)
    
    # 条件待機
    success = await test_helpers.wait_for_condition(
        lambda: check_condition(),
        timeout=5.0
    )
```

## テスト作成のベストプラクティス

### 1. ユニットテストの作成

```python
@pytest.mark.unit
@pytest.mark.auth
class TestAuthService:
    """AuthServiceのテスト"""
    
    @pytest.fixture
    def auth_service(self, async_session):
        return AuthService(async_session)
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, auth_service):
        """ユーザー作成成功テスト"""
        user_data = {...}
        user = await auth_service.create_user(**user_data)
        
        assert user.username == user_data["username"]
        assert user.hashed_password != user_data["password"]
```

### 2. 統合テストの作成

```python
@pytest.mark.integration
@pytest.mark.database
class TestAPIEndpoints:
    """APIエンドポイントの統合テスト"""
    
    def test_create_sensor_device(self, test_client, auth_headers):
        """センサーデバイス作成テスト"""
        response = test_client.post(
            "/sensors/devices",
            json=device_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        assert response.json()["device_id"] == device_data["device_id"]
```

### 3. E2Eテストの作成

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestSensorWorkflow:
    """センサーワークフローのE2Eテスト"""
    
    def test_complete_workflow(self, authenticated_client):
        """完全ワークフローテスト"""
        # 1. デバイス登録
        # 2. データ送信
        # 3. データ取得
        # 4. データ分析
```

### 4. モックの利用

```python
@patch('src.mqtt.client.sensor_service')
def test_mqtt_message_processing(self, mock_service):
    """MQTTメッセージ処理テスト"""
    mock_service.process_mqtt_message.return_value = True
    
    # テスト実行
    result = process_message(test_message)
    
    # 検証
    assert result is True
    mock_service.process_mqtt_message.assert_called_once()
```

## CI/CD統合

### GitHub Actions設定例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mosquitto:
        image: eclipse-mosquitto:2.0
        ports:
          - 1883:1883
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: python scripts/run_tests.py coverage --html
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## トラブルシューティング

### 1. よくある問題

#### MQTTテストの失敗

```bash
# MQTTブローカーの起動確認
brew services list | grep mosquitto

# ポート確認
lsof -i :1883

# テスト実行（MQTTテストをスキップ）
pytest -m "not mqtt"
```

#### データベーステストの失敗

```bash
# SQLiteの権限確認
ls -la bsf_system.db

# テンポラリファイルのクリーンアップ
rm -f /tmp/test_*.db
```

#### 非同期テストの問題

```python
# pytest-asyncioの設定確認
# pytest.iniまたはpyproject.tomlで
asyncio_mode = auto
```

### 2. デバッグ手法

```bash
# 失敗したテストのみ再実行
pytest --lf

# 特定のテストでデバッガー起動
pytest --pdb -s tests/unit/test_auth.py::test_specific_function

# 詳細ログ出力
pytest -s --log-cli-level=DEBUG
```

### 3. パフォーマンス問題

```bash
# 実行時間の長いテストを特定
pytest --durations=10

# プロファイリング（pytest-profileが必要）
pytest --profile
```

## カスタマイズ

### 新しいマーカーの追加

```python
# pytest.iniに追加
markers =
    custom: カスタムテストマーカー
```

### カスタムフィクスチャ

```python
# conftest.pyまたは個別テストファイルに追加
@pytest.fixture
def custom_fixture():
    """カスタムフィクスチャ"""
    # セットアップ
    yield value
    # クリーンアップ
```

### カスタムプラグイン

```python
# pytest_plugins.py
def pytest_configure(config):
    """カスタム設定"""
    pass

def pytest_runtest_setup(item):
    """テスト実行前の処理"""
    pass
```

## 参考リンク

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/python-testing/)