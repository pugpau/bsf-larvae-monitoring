# 開発計画書 (keikaku.md)

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| **案件名** | 材料・プロセスデータベースシステム（汚泥リサイクルDX） |
| **クライアント** | アース・コーポレーション |
| **技術提案書** | TECH-2025-002-R1 |
| **総工数** | 20.9人月 |
| **期間** | 2026年3月 〜 2026年9月30日 |
| **デプロイ先** | オンプレミス Mac mini / Docker / 閉域ネットワーク |

---

## 戦略的意思決定（2026-02-10 確定）

### SD-1: TypeScript移行 → 段階的移行

| 項目 | 内容 |
|------|------|
| **決定** | `allowJs: true` で混在運用。新規ファイルのみTSX、既存JSは温存 |
| **根拠** | 全面移行は1.5人月のオーバーヘッド。Phase 4のLLMリスクに対するバッファ確保を優先 |
| **実施** | Phase 1開始時に `tsconfig.json` 追加（1-2時間）。新規UIコンポーネントはTSXで記述 |
| **期待結果** | プロジェクト終了時に全体の60-70%がTS化。提案書要件を実質的に満たせる |

### SD-2: 未コミット変更 → 2段階コミット

| 項目 | 内容 |
|------|------|
| **決定** | 段階的にレビュー・テスト後コミット |
| **手順** | コミット1: 死コード削除（60ファイル） → `pytest`確認 → コミット2: UI/UX改善 → `npm start`確認 |
| **根拠** | 一括コミットはロールバック不能。`OptimizedDataContext` のimport矛盾など検証が必要 |
| **所要時間** | 2-3時間 |

### SD-3: DBスキーマ拡張 → ドメイン駆動3マイグレーション

| 項目 | 内容 |
|------|------|
| **決定** | ビジネスドメイン単位で3回に分けてマイグレーション |
| **構成** | Migration 1: suppliers + materials拡張 / Migration 2: solidification_materials + leaching_suppressants / Migration 3: recipes + recipe_details |
| **根拠** | 個別ロールバック可能、テストを段階的に追加可能 |
| **material_types戦略** | 既存テーブル温存。新テーブルに分離後、データマイグレーションで移行 |

### SD-4: LLMリスク軽減 → アダプターパターン + 5月末検証

| 項目 | 内容 |
|------|------|
| **決定** | LM Studio + gpt-oss-20b をローカルLLMとして使用。LangChainからOpenAI互換APIで接続 |
| **根拠** | LM StudioのOpenAI互換APIにより、LangChainから `openai/gpt-oss-20b` を直接利用可能。インフラリスク解消 |
| **LLM構成** | モデル: `openai/gpt-oss-20b` / エンドポイント: `http://127.0.0.1:1234` / LM Studio経由 |
| **検証内容** | gpt-oss-20b 推論速度、pgvector動作確認、メモリ使用量測定 |
| **Mac miniメモリ配分** | PostgreSQL 4GB + FastAPI 2GB + LM Studio(gpt-oss-20b Q4) 12-15GB + OS 4GB = 22-25GB / 32GB |

### SD-5: 開発順序 → 並列化 + 3タスク前倒し

| 項目 | 内容 |
|------|------|
| **決定** | Phase 4のPuLP最適化を7月に前倒し。8月はRAG/LLMに集中 |
| **早期開始タスク** | (1) ML学習データ要件定義(4月) (2) pgvector検証(5月末) (3) PuLP前倒し(7月) |
| **根拠** | Phase 4が最大リスク。PuLPはLLMと独立しており前倒し可能 |
| **バッファ** | 最適化後 18.2人月。提案書20.2人月との差分2.0人月をPhase 4に充当 |

---

## 現状分析（2026-02-10時点）

### 完了済みフェーズ（Phase 1〜7）

| # | フェーズ | 状態 | 備考 |
|---|---------|------|------|
| 1 | 死コード削除（Bootstrap/IoT） | 完了 | -20,218行 |
| 2 | バックエンドAPI接続 | 完了 | WasteRecord/MaterialType |
| 3 | AI配合最適化 | 完了 | similarity + rule-based |
| 4 | バックエンド死コード完全削除 | 完了 | 120→22ファイル |
| 5 | Alembicマイグレーション | 完了 | 6テーブル |
| 6 | テストスイート | 完了 | 52テスト全パス |
| 7 | 認証+Docker整理 | 完了 | JWT + 3サービス構成 |

### 未コミット作業（進行中）

- **死コード削除 Phase 8**: sensors, alerts, analytics, MQTT, WebSocket, InfluxDB (-25,506行、60ファイル)
- **UI/UX改善**: App.js（13→5タブ化）、index.css（Fira Sans/Code導入）、substrate コンポーネントリファクタ

### 現在のスタック

| 層 | 技術 | バージョン |
|---|------|----------|
| Frontend | React + MUI v5 | 18.x (JavaScript) |
| Backend | FastAPI + SQLAlchemy async | 0.100+ / 2.0 |
| DB | PostgreSQL | 14 |
| Auth | JWT + API Key + RBAC | bcrypt |
| AI | similarity + rule-based | 自前実装 |
| Infra | Docker Compose | 3サービス構成 |
| Test | pytest + pytest-asyncio | 52テスト |

### 現在のDB構造（6テーブル）

```
users, sessions, login_attempts, api_keys
waste_records, material_types
```

---

## 最適化タイムライン

```
2026年
 3月  Phase 1-A: 未コミット整理 + DB設計 + Alembicマイグレーション
      ├── [SD-2] 2段階コミット（死コード削除 → UI/UX改善）
      ├── [SD-1] tsconfig.json + allowJs 設定
      ├── [SD-3] Migration 1: suppliers + materials拡張
      └── [SD-3] Migration 2: solidification_materials + leaching_suppressants

 4月  Phase 1-B: CRUD API + フロントエンド
      ├── suppliers/materials/recipes CRUD API
      ├── [SD-3] Migration 3: recipes + recipe_details
      ├── 5タブ内のUI構築（新規コンポーネントはTSX）
      └── [SD-5] ML学習データ要件定義（0.5人日、Phase 3準備）
           └── waste_recordsに必要な特徴量の洗い出し

 5月  Phase 2: マスタデータ拡張
      ├── 複合条件検索（ts_vector/ts_query）
      ├── CSV/Excelインポート・エクスポート
      ├── Blue-Greenデプロイ基盤
      └── [SD-4][SD-5] pgvector検証 + LLMベンチマーク（1-2日）
           ├── docker-compose.yml に pgvector/pgvector:pg14 追加
           └── LM Studio + openai/gpt-oss-20b 推論速度・メモリ測定

 6月  Phase 3-A: MLパイプライン
      ├── scikit-learn Random Forest モデル構築
      ├── 特徴量エンジニアリング（汚泥種類、水分率、重金属、pH）
      └── モデルバージョニング（joblib）

 7月  Phase 3-B + Phase 4-A（PuLP前倒し）
      ├── 統計ダッシュボード（Recharts）
      ├── 予測API（/api/v1/predict/formulation, /elution）
      └── [SD-5] PuLP最適化エンジン（Phase 4から前倒し）
           ├── 目的関数: コスト最小化
           ├── 制約: 溶出基準、強度基準、材料在庫
           └── API: POST /api/v1/optimize/formulation

 8月  Phase 4-B: RAG + LLMチャット（PuLP完了済み、LLMに集中）
      ├── [SD-4] LangChain + embedding パイプライン
      ├── pgvector ベクトルストア統合
      ├── LLMチャットUI（会話履歴、参照元表示）
      └── [SD-5] バッチ処理基盤設計（Phase 5準備）

 9月  Phase 5: バッチ処理 + KPI + 本番デプロイ
      ├── APScheduler統合（日次/週次/月次）
      ├── KPIダッシュボード
      ├── Mac mini 本番環境構築
      └── 受入テスト + 運用マニュアル

 9/30 ──────────────────── 納品期限
```

---

## Phase 0: 即時アクション（Phase 1開始前）

Phase 1 開始前に完了すべき作業:

| # | アクション | 所要時間 | 対応SD |
|---|-----------|---------|--------|
| 1 | 死コード削除のコミット（-25,506行） | 1時間 | SD-2 |
| 2 | `pytest` 52テスト全パス確認 | 10分 | SD-2 |
| 3 | UI/UX改善のコミット + `OptimizedDataContext.js` 削除 | 1時間 | SD-2 |
| 4 | `npm start` フロントエンド動作確認 | 30分 | SD-2 |
| 5 | `plan.md` の削除（本計画書に置換） | 5分 | - |

---

## 提案書フェーズ詳細

### Phase 1: 基本DBシステム構築（3月〜4月 / 5.5人月 → 見込み4.5人月）

#### 目標
搬入先、材料、レシピの基本データ管理システムを構築

#### DB拡張（3マイグレーション戦略 [SD-3]）

**Migration 1: 搬入先・材料マスタ**

| テーブル | 状態 | 対応 |
|---------|------|------|
| `suppliers` | 新規 | 搬入先マスタ（名称、連絡先、廃棄物種類） |
| `materials` | 拡張 | MaterialType 温存 + カラム追加（比重、粒度、pH、cost_per_unit等） |

**Migration 2: 配合材料マスタ**

| テーブル | 状態 | 対応 |
|---------|------|------|
| `solidification_materials` | 新規 | 固化材マスタ（セメント系、石灰系、分類・属性） |
| `leaching_suppressants` | 新規 | 溶出抑制剤マスタ（種類、適用重金属、添加率範囲） |

**Migration 3: レシピ管理**

| テーブル | 状態 | 対応 |
|---------|------|------|
| `recipes` | 新規 | 配合レシピヘッダ（FK: suppliers, 目標強度、目標溶出値） |
| `recipe_details` | 新規 | 配合明細（FK: recipes + materials、配合率、順序） |

#### タスク一覧

```
Phase1-1: [SD-2] 未コミット変更の2段階コミット
Phase1-2: [SD-1] TypeScript段階的移行設定
  - tsconfig.json 追加（allowJs: true, strict: true）
  - 新規コンポーネントはTSX、既存JSは温存
Phase1-3: [SD-3] DBスキーマ設計・3マイグレーション
  - Migration 1: suppliers + materials拡張
  - Migration 2: solidification_materials + leaching_suppressants
  - Migration 3: recipes + recipe_details
Phase1-4: バックエンドAPI（CRUD + バリデーション）
  - /api/v1/suppliers (CRUD)
  - /api/v1/materials (CRUD + 拡張フィールド)
  - /api/v1/solidification-materials (CRUD)
  - /api/v1/leaching-suppressants (CRUD)
  - /api/v1/recipes (CRUD + 明細管理)
Phase1-5: フロントエンド（5タブ統合、新規はTSX）
  - 搬入管理タブ: 搬入先選択UI改善
  - 配合管理タブ: レシピ作成・編集UI
  - マスタ管理タブ: 材料・固化材・抑制剤マスタ管理
Phase1-6: テスト（80%カバレッジ目標）
  - ユニットテスト: 各モデル・サービス
  - 統合テスト: APIエンドポイント
  - 既存52テストの維持
Phase1-7: [SD-5] ML学習データ要件定義（4月末、0.5人日）
  - waste_recordsに必要な特徴量の洗い出し
  - 学習データのスキーマ設計
```

#### 再利用可能な既存資産

- 認証基盤（JWT + RBAC）→ そのまま利用
- DB接続・ORM基盤 → engine, session, Base を共有
- APIルーティングパターン → waste.py をテンプレートに
- テストインフラ → conftest.py, fixture パターン

---

### Phase 2: マスタデータ拡張（5月 / 2.9人月 → 見込み2.7人月）

#### 目標
検索・フィルタリング強化、Blue-Greenデプロイ準備、Phase 4早期検証

#### タスク一覧

```
Phase2-1: 高度検索・フィルタAPI
  - 複合条件検索（材料名、カテゴリ、pH範囲、コスト範囲）
  - 全文検索（PostgreSQL ts_vector/ts_query）
  - ページネーション（カーソルベース）
Phase2-2: データインポート/エクスポート
  - CSV/Excelインポート（pandas + openpyxl）
  - テンプレートダウンロード
  - バリデーション付きバルクインサート
Phase2-3: Blue-Greenデプロイ基盤
  - Docker Compose プロファイル（blue/green）
  - Alembic online migration 対応
  - ヘルスチェック強化
Phase2-4: UI改善
  - データテーブル高度化（ソート、フィルタ、ページング）
  - フォームバリデーション強化
Phase2-5: テスト拡充
  - インポート/エクスポートのE2Eテスト
  - 検索パフォーマンステスト
Phase2-6: [SD-4][SD-5] Phase 4早期検証（5月末、1-2日）
  - docker-compose.yml に pgvector/pgvector:pg14 追加・テスト
  - LM Studio + openai/gpt-oss-20b ベンチマーク（推論速度、メモリ消費）
  - LangChain → http://127.0.0.1:1234 接続テスト
  - Mac mini 全サービス同時起動時のリソース測定
```

---

### Phase 3: ML予測・統計分析（6月〜7月 / 4.3人月 → 見込み3.8人月）

#### 目標
scikit-learn Random Forestによる配合予測、統計ダッシュボード、PuLP前倒し

#### タスク一覧

```
Phase3-1: MLパイプライン構築（6月）
  - scikit-learn Random Forest モデル
  - 特徴量: 汚泥種類、水分率、重金属濃度、pH
  - 目標変数: 固化材配合率、抑制剤添加量
  - 現行recommender.py（similarity + rule-based）をMLモデルに段階的置換
Phase3-2: モデル管理（6月）
  - モデルバージョニング（joblib保存）
  - 学習データ管理
  - 再学習パイプライン
Phase3-3: 統計ダッシュボード（7月前半）
  - 分析ダッシュボードタブの機能強化
  - グラフ: Recharts
  - KPI表示: 配合成功率、溶出基準達成率
Phase3-4: 予測API（7月前半）
  - POST /api/v1/predict/formulation
  - POST /api/v1/predict/elution
  - モデルメタデータ取得API
Phase3-5: [SD-5] PuLP最適化エンジン（7月後半、Phase 4から前倒し）
  - 目的関数: コスト最小化
  - 制約: 溶出基準、強度基準、材料在庫
  - API: POST /api/v1/optimize/formulation
Phase3-6: テスト
  - モデル精度テスト（交差検証）
  - 予測APIの統合テスト
  - 最適化結果の妥当性テスト
```

#### 既存資産の活用

- `recommender.py`（282行）→ MLモデルのフォールバックとして維持
- `ELUTION_THRESHOLDS`（土壌汚染対策法基準値）→ そのまま利用
- waste_records テーブル → 学習データソースとして活用

---

### Phase 4: RAG + LLMチャット（8月 / 4.6人月 → 見込み4.5人月）

#### 目標
RAG + LLMによる知識ベースチャット（PuLP最適化は7月に完了済み [SD-5]）

#### タスク一覧

```
Phase4-1: [SD-4] RAG基盤構築
  - pgvector 拡張（Phase 2-6で検証済み）
  - LangChain + テキスト分割 + embedding
  - ベクトルストア: PGVector
  - LLMアダプターパターン（LangChainで自然に実現）
Phase4-2: LLMチャット
  - LM Studio + openai/gpt-oss-20b（ローカル推論）
  - エンドポイント: http://127.0.0.1:1234
  - LangChain接続: ChatOpenAI(base_url="http://127.0.0.1:1234/v1", model="openai/gpt-oss-20b")
  - 閉域ネットワーク対応（完全ローカル、外部通信なし）
Phase4-3: チャットUI
  - RAG検索 + LLM応答の統合UI
  - 会話履歴管理
  - 参照元ドキュメント表示
Phase4-4: テスト
  - RAG検索精度テスト
  - LLM応答品質テスト
  - メモリ使用量モニタリング
```

#### リスク評価（更新版）

| リスク | 影響度 | 対策 | 状態 |
|--------|--------|------|------|
| gpt-oss-20bインフラ | ~~高~~ → **解消** | LM Studio経由でローカル提供確定 | 解消 |
| Mac miniでのgpt-oss-20b推論性能 | 中 | [SD-5] 5月末にLM Studioで実機ベンチマーク | 5月検証 |
| pgvector導入工数 | 中 | [SD-5] 5月末に事前検証予定 | 5月検証 |
| Phase 4工数不足 | **高** → 低 | [SD-5] PuLP前倒し + LLMインフラ確定で大幅軽減 | 軽減済み |

#### Mac mini メモリ配分計画 [SD-4]

```
PostgreSQL (pgvector含む):  4GB shared_buffers
FastAPI + workers:          2GB
LM Studio (gpt-oss-20b):   12-15GB（20Bモデル Q4量子化時）
OS + フロントエンド:          4GB
────────────────────────────────
合計:                       22-25GB / 32GB ✓（余裕 7-10GB）
```

---

### Phase 5: バッチ処理+KPIダッシュボード（9月 / 2.9人月 → 見込み2.7人月）

#### 目標
定期バッチ処理、KPIダッシュボード、本番デプロイ

#### タスク一覧

```
Phase5-1: バッチ処理
  - APScheduler（閉域のため軽量版）
  - 日次: データ集計、レポート生成
  - 週次: モデル再学習トリガー
  - 月次: 統計レポート自動生成
Phase5-2: KPIダッシュボード
  - リアルタイムKPI: 処理量、成功率、コスト
  - 月次トレンド: グラフ可視化
  - アラート: 基準値逸脱通知
Phase5-3: 本番デプロイ
  - Mac mini 環境構築
  - Docker Compose 本番設定
  - バックアップ・リストア手順（pg_dump + cron）
  - 運用マニュアル
Phase5-4: 受入テスト
  - 全機能E2Eテスト
  - パフォーマンステスト
  - セキュリティ監査
```

---

## 工数見積もり（最適化後）

| フェーズ | 提案書 | 最適化後見込み | 差分 | 備考 |
|---------|--------|--------------|------|------|
| Phase 1 | 5.5人月 | 4.5人月 | **-1.0** | 既存資産活用で短縮 |
| Phase 2 | 2.9人月 | 2.7人月 | -0.2 | PostgreSQL組み込み検索で効率化 |
| Phase 3 | 4.3人月 | 3.8人月 | **-0.5** | recommender.py活用 + PuLP前倒し |
| Phase 4 | 4.6人月 | 4.5人月 | -0.1 | PuLP前倒し済み、LLMに集中 |
| Phase 5 | 2.9人月 | 2.7人月 | -0.2 | バッチ設計の早期開始 |
| **合計** | **20.2人月** | **18.2人月** | **-2.0** | バッファをPhase 4 LLMリスクに充当 |

**バッファ: 2.0人月** → Phase 4のLLMインフラ問題発生時に充当可能

---

## 技術方針

### フロントエンド [SD-1]

- **言語**: JS/TS混在（`allowJs: true`）。新規ファイルのみTSX
- **UI**: MUI v5 + Fira Sans/Code（MASTER.md準拠）
- **状態管理**: React Context + localStorage hybrid
- **グラフ**: Recharts
- **5タブ構成**: 搬入管理、配合管理、分析ダッシュボード、品質管理、マスタ管理

### バックエンド

- **フレームワーク**: FastAPI + SQLAlchemy async
- **DB**: PostgreSQL 14 → PostgreSQL 14 + pgvector（Phase 4〜）
- **ML**: scikit-learn Random Forest（Phase 3〜）
- **最適化**: PuLP（Phase 3-B / 7月〜）
- **RAG**: LangChain + pgvector（Phase 4〜） [SD-4]
- **LLM**: LM Studio + openai/gpt-oss-20b @ `http://127.0.0.1:1234` [SD-4]
- **バッチ**: APScheduler（Phase 5〜）

### インフラ

- **デプロイ**: Docker Compose on Mac mini（Blue-Green対応 Phase 2〜）
- **ネットワーク**: 閉域（外部データ送信なし）
- **バックアップ**: pg_dump + cron
- **CI**: GitHub Actions（開発時）

---

*最終更新: 2026-02-10*
*作成者: Claude Code + yasu*
