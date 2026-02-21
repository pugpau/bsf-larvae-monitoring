# フロントエンド仕様

## ドキュメント情報
- **バージョン**: 0.1.0
- **最終更新**: 2025-10-01
- **フレームワーク**: React 18.2.0
- **UIライブラリ**: Material-UI 5.14.5

---

## 1. アーキテクチャ概要

### 1.1 技術スタック

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|-----------|------|
| **コアフレームワーク** | React | 18.2.0 | UIフレームワーク |
| **状態管理** | React Context API | - | グローバル状態管理 |
| **ルーティング** | React Router | 6.11.2 | SPA ルーティング |
| **UIコンポーネント** | Material-UI | 5.14.5 | UIコンポーネントライブラリ |
| **UIアイコン** | Lucide React | 0.515.0 | アイコンライブラリ |
| **チャート** | Chart.js, Recharts | 4.4.9, 2.15.3 | データ可視化 |
| **3D可視化** | Plotly.js | 3.0.1 | 3Dビジュアライゼーション |
| **HTTPクライアント** | Axios | 1.4.0 | REST API通信 |
| **WebSocket** | Socket.io-client | 4.7.2 | リアルタイム通信 |
| **フォーム** | React Hook Form | 7.45.4 | フォーム管理 |
| **スタイリング** | Bootstrap, TailwindCSS | 5.3.6 | CSSフレームワーク |
| **日付処理** | date-fns | 4.1.0 | 日付操作 |
| **ユーティリティ** | clsx, tailwind-merge | - | クラス名管理 |

### 1.2 ディレクトリ構造

```
frontend/
├── public/                    # 静的ファイル
├── src/
│   ├── components/            # Reactコンポーネント
│   │   ├── ui/                # 共通UIコンポーネント
│   │   │   ├── card.tsx
│   │   │   ├── button.tsx
│   │   │   ├── alert.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── DocumentCard.js
│   │   │   └── OceanInspiredHeader.js
│   │   ├── auth/              # 認証コンポーネント
│   │   │   ├── LoginForm.js
│   │   │   └── PrivateRoute.js
│   │   ├── dashboard/         # ダッシュボード
│   │   │   └── RealTimeDashboard.js
│   │   ├── sensors/           # センサー関連
│   │   │   ├── SensorDeviceList.js
│   │   │   ├── SensorDeviceForm.js
│   │   │   ├── SensorReadingsList.js
│   │   │   ├── SensorRealTimeDisplay.js
│   │   │   ├── SensorChartsRealTime.js
│   │   │   ├── Sensor3DVisualization.js
│   │   │   ├── SensorProphetAnalysis.js
│   │   │   ├── TemperatureSensorCard.js
│   │   │   └── TemperatureSensorDashboard.js
│   │   ├── substrate/         # 基質管理
│   │   │   ├── SubstrateTypeForm.js
│   │   │   ├── SubstrateTypeList.js
│   │   │   ├── SubstrateBatchForm.js
│   │   │   └── SubstrateBatchList.js
│   │   ├── analytics/         # 分析コンポーネント
│   │   │   ├── AnalyticsDashboard.js
│   │   │   ├── StatisticsOverview.js
│   │   │   ├── TrendAnalysisCharts.js
│   │   │   ├── CorrelationAnalysis.js
│   │   │   ├── AnomalyDetectionPanel.js
│   │   │   ├── RealtimeMonitor.js
│   │   │   ├── RealtimeMonitorV2.js
│   │   │   └── MLModelManager.js
│   │   ├── alerts/            # アラート機能
│   │   │   ├── AlertSettings.js
│   │   │   ├── AlertHistory.js
│   │   │   ├── AlertNotificationCenter.js
│   │   │   ├── NotificationSettings.js
│   │   │   ├── ThresholdSettings.js
│   │   │   ├── AlertTestingPanel.js
│   │   │   └── MQTTTestPanel.js
│   │   ├── batch/             # バッチ管理
│   │   │   ├── BatchComparison.js
│   │   │   ├── ProfitabilityDashboard.js
│   │   │   └── FeedEfficiencyTracker.js
│   │   └── optimized/         # 最適化コンポーネント
│   │       └── MemoizedSensorCharts.js
│   ├── contexts/              # Context API
│   │   ├── AuthContext.js
│   │   └── OptimizedDataContext.js
│   ├── hooks/                 # カスタムフック
│   │   ├── useWebSocket.js
│   │   ├── useRealtimeData.js
│   │   ├── useAlertSystem.js
│   │   └── useAlertDetection.js
│   ├── services/              # APIサービス
│   │   ├── mqttService.js
│   │   └── websocketService.js
│   ├── utils/                 # ユーティリティ
│   │   ├── api.js
│   │   ├── axiosConfig.js
│   │   ├── errorHandler.js
│   │   ├── storage.js
│   │   └── unifiedData.js
│   ├── styles/                # スタイル
│   │   ├── ocean-theme.css
│   │   ├── theme-colors.css
│   │   ├── responsive-16-10.css
│   │   └── responsive-utilities.css
│   ├── theme/                 # テーマ設定
│   │   └── materialTheme.js
│   ├── lib/                   # ライブラリ
│   │   └── utils.ts
│   ├── App.js                 # メインアプリケーション
│   ├── index.js               # エントリーポイント
│   └── index.css              # グローバルCSS
├── package.json               # 依存関係
├── Dockerfile                 # Dockerイメージ
└── nginx.conf                 # Nginx設定
```

---

## 2. 主要機能モジュール

### 2.1 認証機能

#### LoginForm.js
**機能:**
- ユーザーログインフォーム
- JWT認証
- ログイン状態管理

**Props:**
```javascript
// なし（内部状態管理）
```

**使用例:**
```jsx
<LoginForm />
```

#### PrivateRoute.js
**機能:**
- 認証保護されたルート
- 未認証ユーザーをログインページにリダイレクト

**Props:**
```javascript
{
  children: ReactNode  // 保護されたコンポーネント
}
```

**使用例:**
```jsx
<PrivateRoute>
  <Dashboard />
</PrivateRoute>
```

#### AuthContext.js
**機能:**
- グローバル認証状態管理
- ユーザー情報保持
- ログイン/ログアウト処理

**提供される値:**
```javascript
{
  user: User | null,
  login: (username, password) => Promise<void>,
  logout: () => void,
  isAuthenticated: boolean,
  loading: boolean
}
```

---

### 2.2 ダッシュボード機能

#### RealTimeDashboard.js
**機能:**
- リアルタイムセンサーデータ統合表示
- センサー監視パネル
- リアルタイムチャート
- アラート通知

**主要機能:**
- ファーム選択
- 自動更新設定（デフォルト5秒）
- 一時停止/再開
- フルスクリーン表示
- 統計情報表示

**State:**
```javascript
{
  selectedFarm: string,
  dashboardSettings: {
    autoRefresh: boolean,
    refreshInterval: number,
    showAlerts: boolean,
    showCharts: boolean,
    fullscreen: boolean
  }
}
```

---

### 2.3 センサー機能

#### SensorDeviceList.js
**機能:**
- センサーデバイス一覧表示
- デバイス詳細表示
- デバイス編集/削除
- ステータス表示

**表示項目:**
- デバイスID
- デバイスタイプ
- ロケーション
- ステータス（active/inactive/maintenance）
- 最終更新時刻

#### SensorRealTimeDisplay.js
**機能:**
- リアルタイムセンサーデータ表示
- WebSocket接続によるライブ更新
- 複数デバイス同時監視
- カラーコード状態表示

**接続設定:**
```javascript
const config = {
  autoStart: true,
  updateInterval: 2000,
  maxDataPoints: 100,
  farmId: 'farm001'
};
```

#### SensorChartsRealTime.js
**機能:**
- リアルタイムチャート表示
- Chart.js ベース
- 時系列データプロット
- 複数センサー同時表示

**チャート設定:**
```javascript
{
  type: 'line',
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 750
  }
}
```

#### Sensor3DVisualization.js
**機能:**
- 3Dセンサー配置ビジュアライゼーション
- Plotly.js ベース
- X/Y/Z座標表示
- インタラクティブな3D操作

#### TemperatureSensorDashboard.js
**機能:**
- 温度センサー専用ダッシュボード
- M5StickC/AtomS3連携
- 温度グラフ表示
- アラート表示

---

### 2.4 基質管理機能

#### SubstrateTypeForm.js
**機能:**
- 基質タイプ登録フォーム
- カテゴリ選択
- プロパティ設定

**フォームフィールド:**
```javascript
{
  name: string,              // 基質名
  description: string,       // 説明
  category: string,          // カテゴリ
  properties: {
    moisture_content: number,
    organic_matter: number,
    nitrogen_content: number
  }
}
```

#### SubstrateBatchForm.js
**機能:**
- 基質バッチ登録フォーム
- 複数基質配合
- 配合比率設定

**フォームフィールド:**
```javascript
{
  batch_number: string,
  substrate_type_id: string,
  start_date: Date,
  end_date: Date,
  quantity: number,
  unit: string,
  location: string,
  composition: Array<{
    substrate_type_id: string,
    percentage: number
  }>
}
```

#### SubstrateTypeList.js / SubstrateBatchList.js
**機能:**
- 基質タイプ/バッチ一覧表示
- 検索・フィルタ機能
- 編集/削除機能
- ページネーション

---

### 2.5 分析機能

#### AnalyticsDashboard.js
**機能:**
- データ分析ダッシュボード
- 統計情報表示
- トレンド分析
- 相関分析

**表示内容:**
- 平均値、標準偏差
- 最大/最小値
- データ件数
- 時系列トレンド

#### TrendAnalysisCharts.js
**機能:**
- トレンド分析チャート
- 移動平均線
- トレンド予測
- 異常値検出表示

#### CorrelationAnalysis.js
**機能:**
- センサーデータ相関分析
- ヒートマップ表示
- 相関係数計算
- 散布図プロット

#### AnomalyDetectionPanel.js
**機能:**
- 異常検知結果表示
- 異常スコア表示
- 異常履歴
- アラート連携

#### MLModelManager.js
**機能:**
- 機械学習モデル管理
- モデル選択
- トレーニング実行
- 予測結果表示

---

### 2.6 アラート機能

#### AlertSettings.js
**機能:**
- アラート設定画面
- 閾値設定
- 通知設定
- アラートルール管理

#### AlertHistory.js
**機能:**
- アラート履歴表示
- 時系列フィルタ
- 重要度フィルタ
- 詳細表示

#### AlertNotificationCenter.js
**機能:**
- リアルタイムアラート通知
- トースト通知
- アラート音
- 未読管理

#### ThresholdSettings.js
**機能:**
- 閾値設定インターフェース
- センサータイプ別設定
- 上限/下限設定
- UIベース設定

**設定項目:**
```javascript
{
  measurement_type: string,
  high_threshold: number,
  low_threshold: number,
  severity: 'low' | 'medium' | 'high',
  enabled: boolean
}
```

#### MQTTTestPanel.js
**機能:**
- MQTT接続テストパネル
- メッセージ送信テスト
- 接続状態確認
- デバッグ情報表示

---

### 2.7 バッチ管理機能

#### BatchComparison.js
**機能:**
- バッチ間比較分析
- 成長率比較
- 収率比較
- グラフ表示

#### ProfitabilityDashboard.js
**機能:**
- 収益性ダッシュボード
- コスト分析
- 収益予測
- ROI計算

#### FeedEfficiencyTracker.js
**機能:**
- 飼料効率追跡
- 飼料転換率計算
- 効率トレンド
- 最適化提案

---

## 3. カスタムフック

### 3.1 useWebSocket
**機能:**
- WebSocket接続管理
- 自動再接続
- メッセージ送受信

**使用例:**
```javascript
const {
  isConnected,
  lastMessage,
  sendMessage
} = useWebSocket('ws://localhost:8000/ws/sensors');
```

### 3.2 useRealtimeData
**機能:**
- リアルタイムデータ管理
- データバッファリング
- 統計情報計算

**使用例:**
```javascript
const {
  data,
  isRunning,
  stats
} = useRealtimeData({
  autoStart: true,
  updateInterval: 2000,
  maxDataPoints: 100
});
```

### 3.3 useAlertSystem
**機能:**
- アラートシステム管理
- 閾値監視
- 通知トリガー

### 3.4 useAlertDetection
**機能:**
- リアルタイム異常検知
- 閾値ベース検出
- アラート生成

---

## 4. APIクライアント

### 4.1 axiosConfig.js
**機能:**
- Axios インスタンス設定
- ベースURL設定
- リクエスト/レスポンスインターセプター
- JWT認証ヘッダー自動付与

**設定:**
```javascript
const axiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

### 4.2 api.js
**機能:**
- API エンドポイントラッパー
- 認証API
- センサーAPI
- 基質管理API

**使用例:**
```javascript
import { api } from './utils/api';

// センサーデータ取得
const readings = await api.getSensorReadings({
  farm_id: 'farm001',
  start_time: '2025-10-01T00:00:00Z'
});

// ログイン
const token = await api.login('username', 'password');
```

---

## 5. スタイリング

### 5.1 テーマシステム

#### materialTheme.js
Material-UI カスタムテーマ設定

```javascript
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});
```

### 5.2 CSSファイル

#### ocean-theme.css
オーシャンインスパイアードデザイン

**特徴:**
- 海洋テーマカラー
- グラデーション背景
- 波模様エフェクト

#### responsive-16-10.css
16:10アスペクト比対応

#### responsive-utilities.css
レスポンシブユーティリティクラス

---

## 6. 状態管理

### 6.1 AuthContext
**役割:**
- グローバル認証状態
- ユーザー情報管理
- トークン管理

**State:**
```javascript
{
  user: {
    id: string,
    username: string,
    email: string,
    role: string
  },
  token: string,
  isAuthenticated: boolean
}
```

### 6.2 OptimizedDataContext
**役割:**
- データキャッシング
- パフォーマンス最適化
- データ共有

---

## 7. ルーティング

### 7.1 ルート構成

```javascript
<Routes>
  <Route path="/login" element={<LoginForm />} />
  <Route path="/" element={
    <PrivateRoute>
      <Dashboard />
    </PrivateRoute>
  } />
</Routes>
```

### 7.2 主要ルート

| パス | コンポーネント | 認証要否 |
|-----|-------------|---------|
| `/login` | LoginForm | 不要 |
| `/` | Dashboard | 必要 |
| `/sensors` | SensorList | 必要 |
| `/analytics` | AnalyticsDashboard | 必要 |
| `/substrate` | SubstrateManagement | 必要 |

---

## 8. リアルタイム通信

### 8.1 WebSocket接続

**エンドポイント:**
```
ws://localhost:8000/ws/sensors?token=<jwt_token>&farm_id=<farm_id>
```

**メッセージフォーマット:**
```javascript
{
  type: 'sensor_reading',
  data: {
    device_id: 'sensor001',
    timestamp: '2025-10-01T10:00:00Z',
    measurement_type: 'temperature',
    value: 25.5,
    unit: '°C'
  }
}
```

### 8.2 Socket.io 統合

**接続設定:**
```javascript
const socket = io('http://localhost:8000', {
  transports: ['websocket'],
  auth: {
    token: authToken
  }
});
```

---

## 9. パフォーマンス最適化

### 9.1 実装済み最適化

- **React.memo**: コンポーネントメモ化
- **useMemo**: 計算結果キャッシング
- **useCallback**: 関数メモ化
- **仮想化**: 大量データ表示最適化
- **遅延ローディング**: コード分割
- **デバウンス**: 検索・フィルタ処理

### 9.2 チャート最適化

- データポイント制限（最大100〜200点）
- アニメーション制限
- Canvas描画最適化

---

## 10. ビルド・デプロイ

### 10.1 ビルドコマンド

```bash
# 開発サーバー起動
npm start

# プロダクションビルド
npm run build

# テスト実行
npm test
```

### 10.2 環境変数

```bash
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_MQTT_WS_URL=ws://localhost:9001
```

### 10.3 Docker構成

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

---

## 11. テスト

### 11.1 テスト構成

- **単体テスト**: Jest + React Testing Library
- **E2Eテスト**: (将来計画)

### 11.2 テストカバレッジ目標

- **コンポーネント**: 70%以上
- **ユーティリティ**: 90%以上

---

## 12. アクセシビリティ

### 12.1 実装済み対応

- セマンティックHTML
- ARIAラベル
- キーボードナビゲーション
- カラーコントラスト

---

## 13. 今後の拡張

- [ ] PWA対応
- [ ] モバイルアプリ（React Native）
- [ ] オフライン対応
- [ ] 多言語対応（i18n）
- [ ] ダークモード
- [ ] アドバンスドフィルタ
- [ ] データエクスポート機能
- [ ] カスタムダッシュボード
