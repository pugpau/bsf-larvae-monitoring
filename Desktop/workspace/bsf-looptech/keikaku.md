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

## 現状分析（2026-02-11 更新）

### 完了済み準備フェーズ（Phase 0-1〜0-7）

| # | フェーズ | 状態 | 備考 |
|---|---------|------|------|
| 0-1 | 死コード削除（Bootstrap/IoT） | 完了 | -20,218行 |
| 0-2 | バックエンドAPI接続 | 完了 | WasteRecord/MaterialType |
| 0-3 | AI配合最適化 | 完了 | similarity + rule-based |
| 0-4 | バックエンド死コード完全削除 | 完了 | 120→22ファイル |
| 0-5 | Alembicマイグレーション | 完了 | 6テーブル |
| 0-6 | テストスイート | 完了 | 52テスト全パス |
| 0-7 | 認証+Docker整理 | 完了 | JWT + 3サービス構成 |

### Phase 1 進捗（基本DBシステム構築）

| タスク | 状態 | 備考 |
|--------|------|------|
| Phase 1-1: 未コミット変更整理 [SD-2] | **完了** | 2段階コミット実施 |
| Phase 1-2: TypeScript段階的移行 [SD-1] | **完了** | tsconfig.json + allowJs:true |
| Phase 1-3: DBスキーマ3マイグレーション [SD-3] | **完了** | 5テーブル追加（suppliers, solidification_materials, leaching_suppressants, recipes, recipe_details） |
| Phase 1-4: CRUD API | **完了** | 29エンドポイント（suppliers 5 + solidification 5 + suppressants 5 + recipes 7 + waste 7） |
| Phase 1-5: フロントエンド | **完了** | 8 TSXファイル + App.js統合、ビルド検証済 |
| Phase 1-6: テスト 80%カバレッジ | **完了** | 284テスト全パス、カバレッジ80%達成 |
| Phase 1-7: ML学習データ要件定義 | **完了** | `docs/ML_TRAINING_DATA_REQUIREMENTS.md` |

### カバレッジ詳細（2026-02-10 更新）

| モジュール | カバレッジ | 備考 |
|-----------|----------|------|
| materials/schemas.py | 100% | 完全 |
| materials/repository.py | 71% | エラーパス未テスト |
| api/routes/materials.py | 64% | エラーハンドリング未テスト |
| waste/recommender.py | 97% | ほぼ完全 |
| waste/models.py | 100% | 完全 |
| waste/service.py | 100% | 完全 |
| waste/repository.py | 81% | CRUD全パターン |
| auth/models.py | 97% | ほぼ完全 |
| auth/repository.py | 72% | CRUD + 認証 + APIKey |
| auth/service.py | 80% | Authentication + UserManagement + Security + APIKey |
| auth/security.py | 74% | JWT + パスワード + マスキング |
| auth/middleware.py | 49% | exempt_paths + rate limit + CORS |
| utils/logging.py | 96% | StructuredFormatter + decorators |
| database/exceptions.py | 100% | 全7例外クラス |
| **全体** | **80%** | 目標達成（284テスト） |

### 現在のスタック

| 層 | 技術 | バージョン |
|---|------|----------|
| Frontend | React + MUI v5 | 18.x (JS/TSX混在) |
| Backend | FastAPI + SQLAlchemy async | 0.100+ / 2.0 |
| DB | PostgreSQL | 15（13テーブル: 既存11 + ml_models + ml_predictions） |
| Auth | JWT + API Key + RBAC | bcrypt |
| AI/ML | scikit-learn RF + PuLP最適化 + similarity/rule fallback | Phase 3完了 |
| Infra | Docker Compose (Blue-Green) | 5サービス構成 (prod) |
| Test | pytest + pytest-asyncio + pytest-cov | 448テスト / 80%+カバレッジ |

### 現在のDB構造（11テーブル）

```
# 認証系
users, user_sessions, login_attempts, api_keys

# 廃棄物管理
waste_records, material_types

# Phase 1 拡張（マスタ・配合管理）
suppliers, solidification_materials, leaching_suppressants
recipes, recipe_details
```

---

## 最適化タイムライン

```
2026年
 2月  Phase 1-A/B: ★前倒し完了★
      ├── [SD-2] 2段階コミット ✅
      ├── [SD-1] tsconfig.json + allowJs 設定 ✅
      ├── [SD-3] 3マイグレーション（5テーブル追加） ✅
      ├── CRUD API 29エンドポイント ✅
      ├── フロントエンド8 TSXコンポーネント ✅
      └── 284テスト全パス（カバレッジ80%達成） ✅

 2月  Phase 1 全完了 ✅
      └── Phase 1-7: ML学習データ要件定義 ✅

 2月  Phase 2 早期着手 ✅
      ├── Phase 2-1: 検索・ページネーション・CSV入出力 バックエンド ✅
      └── Phase 2-4: フロントエンドUI改善（検索・ページネーション・CSV） ✅

 2月  Phase 3 ★前倒し完了★ ✅
      ├── Phase 3-1: MLパイプライン基盤（scikit-learn/joblib/PuLP） ✅
      ├── Phase 3-2: MLパイプライン（7ファイル: trainer, predictor, etc.） ✅
      ├── Phase 3-3: 予測API（7エンドポイント） ✅
      ├── Phase 3-4: PuLP最適化エンジン ✅
      ├── Phase 3-5: フロントエンド（4 TSXコンポーネント） ✅
      └── Phase 3-6: テスト（351→442テスト） ✅

 2月  本番デプロイ基盤 ★前倒し完了★ ✅
      ├── CI/CD（4 Jobs: test, build, security, docker） ✅
      └── Blue-Green ゼロダウンタイムデプロイ ✅
           ├── docker-compose.prod.yml（5サービス） ✅
           ├── deploy-blue-green.sh（init/deploy/rollback/status） ✅
           └── /ready プローブ + pool_size最適化 ✅

 2月  Phase 2-6: [SD-4][SD-5] pgvector検証 + LLMベンチマーク ✅
      ├── pgvector/pgvector:pg14(dev)/pg15(prod) Docker切替 ✅
      ├── pgvector vector(384) cosine distance 動作確認 ✅
      ├── LM Studio gpt-oss-20b ~45 tok/s ベンチマーク ✅
      ├── LangChain ChatOpenAI 統合テスト ✅
      ├── nomic-embed-text-v1.5 (dim=768) embedding確認 ✅
      └── メモリ: LM Studio ~25GB, 残り ~8GB/32GB ✅

 ─── ここから未着手 ───

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

 ★ Phase 3 + CI/CD + Blue-Green が4ヶ月前倒し完了。
   バッファ 2.0人月 → 4.0+人月に拡大。Phase 4 LLMリスクに余裕あり。
```

---

## Phase 0: 即時アクション（Phase 1開始前）— **全完了**

| # | アクション | 状態 | 対応SD |
|---|-----------|------|--------|
| 1 | 死コード削除のコミット（-25,506行） | **完了** | SD-2 |
| 2 | `pytest` テスト全パス確認 | **完了**（77テスト） | SD-2 |
| 3 | UI/UX改善のコミット + `OptimizedDataContext.js` 削除 | **完了** | SD-2 |
| 4 | `npm run build` フロントエンド動作確認 | **完了** | SD-2 |
| 5 | `plan.md` の削除（本計画書に置換） | **完了** | - |

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
Phase2-1: 高度検索・フィルタAPI ✅
  - ILIKE テキスト検索（エンティティごとに検索カラム設定可能）
  - オフセットベースページネーション（PaginatedResponse<T>）
  - ソート（sort_by, sort_order）、フィルタ（status, material_type等）
Phase2-2: データインポート/エクスポート ✅（Phase 2-1と統合実施）
  - CSV エクスポート（BOM付きUTF-8、Excel対応）
  - CSV インポート（行バリデーション付き、ImportResult返却）
  - 3エンティティ対応（suppliers, solidification_materials, leaching_suppressants）
Phase2-3: Blue-Greenデプロイ基盤 → Phase 5に延期
  - Docker Compose プロファイル（blue/green）
  - Alembic online migration 対応
  - ヘルスチェック強化
Phase2-4: UI改善 ✅
  - 検索バー（テキスト入力 + ステータスフィルタ）
  - MUI TablePagination（25/50/100件、日本語ラベル）
  - CSVエクスポート/インポートボタン（全4リスト画面）
  - PaginatedResponse対応（materialsApi.ts + types/api.ts）
Phase2-5: テスト拡充 ✅
  - Unit: リポジトリ検索・ページネーション・ソート・エクスポート（39テスト）
  - Integration: 検索・CSV export/import・ラウンドトリップ（28テスト）
  - 合計 351テスト（284→351, +67テスト追加）
Phase2-6: [SD-4][SD-5] Phase 4早期検証（5月末、1-2日）
  - docker-compose.yml に pgvector/pgvector:pg14 追加・テスト
  - LM Studio + openai/gpt-oss-20b ベンチマーク（推論速度、メモリ消費）
  - LangChain → http://127.0.0.1:1234 接続テスト
  - Mac mini 全サービス同時起動時のリソース測定
```

---

### Phase 3: ML予測・統計分析（6月〜7月 / 4.3人月 → 実績: 2月完了 ★4ヶ月前倒し★）

#### 目標
scikit-learn Random Forestによる配合予測、統計ダッシュボード、PuLP前倒し

#### タスク一覧

```
Phase3-1: MLパイプライン基盤 ✅（2月完了）
  - scikit-learn/joblib/imbalanced-learn/pulp 導入
  - MLModel/MLPrediction テーブル + Alembic migration
Phase3-2: MLパイプライン ✅（2月完了）
  - src/ml/ 7ファイル: schemas, data_pipeline, feature_engineering,
    synthetic_data, trainer, model_registry, predictor
  - RandomForest classifier + regressor, SMOTE, 5-fold CV
  - ML→similarity→rule フォールバックチェーン
Phase3-3: 予測API ✅（2月完了）
  - 7エンドポイント: predict/formulation, predict/elution,
    ml/models, ml/train, ml/accuracy, ml/trends
Phase3-4: PuLP最適化エンジン ✅（2月完了）
  - src/optimization/ 3ファイル: constraints, solver + API route
  - 目的関数: コスト最小化
  - 制約: 溶出基準、強度基準、材料在庫
Phase3-5: フロントエンド ✅（2月完了）
  - 4 TSX: MLPredictionPanel, OptimizationPanel, TrendAnalysis, PredictionAccuracy
  - apiClient.js ML API統合
Phase3-6: テスト ✅（2月完了）
  - 442テスト（+62 ML unit + 21 optimization unit + 19 integration）
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
| Mac miniでのgpt-oss-20b推論性能 | ~~中~~ → **解消** | ~45tok/s ベンチマーク完了 | 解消 |
| pgvector導入工数 | ~~中~~ → **解消** | vector v0.8.1 動作確認済み | 解消 |
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

| フェーズ | 提案書 | 最適化後見込み | 実績 | 備考 |
|---------|--------|--------------|------|------|
| Phase 1 | 5.5人月 | 4.5人月 | **完了** | 2月完了、既存資産活用 |
| Phase 2 | 2.9人月 | 2.7人月 | **完了** | 2月全完了（2-6含む） |
| Phase 3 | 4.3人月 | 3.8人月 | **完了** | 2月完了★4ヶ月前倒し |
| CI/CD+BG | - | - | **完了** | Phase 4(CI/CD) + Blue-Green |
| Phase 4 | 4.6人月 | 4.5人月 | 未着手 | RAG + LLM（8月予定） |
| Phase 5 | 2.9人月 | 2.7人月 | 未着手 | バッチ + KPI + 本番（9月予定） |
| **合計** | **20.2人月** | **18.2人月** | | |

**バッファ: 4.0+人月** → Phase 3の4ヶ月前倒しにより大幅拡大。Phase 4 LLMリスクに十分な余裕

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

### 改善提案（2026-02-10 レビュー結果）

| 優先度 | 提案 | 対応時期 |
|--------|------|---------|
| ~~HIGH~~ | ~~テストカバレッジ80%達成~~ | **完了**（2月達成） |
| MEDIUM | Blue-Green デプロイを Phase 5 に移動（Phase 2 は検索+インポートに集中） | Phase 2 計画時 |
| MEDIUM | ML学習データ量の現実的見積もり（不足時は合成データ計画） | 3月末 |
| MEDIUM | 受入テスト仕様の早期定義（クライアントと合意） | 4月 |
| LOW | 共通 useNotification フック作成（Snackbar 重複削減） | Phase 2 UI改善時 |
| LOW | Tab 2/3 の責務再定義（分析 vs 品質管理） | Phase 3 ダッシュボード時 |

*最終更新: 2026-02-11*
*作成者: Claude Code + yasu*
