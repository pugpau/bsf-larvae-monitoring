# 進捗メモ (memo.md)

## 2026-02-10 — 現状分析・計画策定・戦略的意思決定

### 実施内容

- プロジェクト現状の全体精査（バックエンド22モジュール、フロントエンド17ファイル、52テスト）
- 技術提案書（TECH-2025-002-R1）とのギャップ分析
- 開発計画書（keikaku.md）の作成
- 5つの戦略的意思決定（SD-1〜SD-5）の分析・確定

### 戦略的意思決定サマリー

| ID | 決定事項 | 結論 | 影響 |
|----|---------|------|------|
| SD-1 | TypeScript移行 | 段階的移行（`allowJs: true`） | 1.5人月節約→Phase 4バッファ |
| SD-2 | 未コミット変更 | 2段階コミット（死コード→UI/UX） | ロールバック安全性確保 |
| SD-3 | DB拡張 | ドメイン駆動3マイグレーション | 段階的テスト可能 |
| SD-4 | LLM構成 | LM Studio + openai/gpt-oss-20b @ 127.0.0.1:1234 | インフラリスク解消 |
| SD-5 | 開発順序 | PuLP前倒し+3タスク先行開始 | バッファ2.0人月創出 |

### 現在の状態

| 項目 | 状態 |
|------|------|
| Phase 1〜7（既存開発） | コミット済み |
| 死コード削除 Phase 8 | 未コミット（-25,506行、60ファイル） |
| UI/UX改善（Fira Sans/Code, 5タブ化） | 未コミット（進行中） |
| keikaku.md | 作成完了（SD-1〜5反映済み） |
| memo.md | 作成完了 |

### 未コミット変更の内訳

**削除済み（死コード）:**
- `frontend/src/components/alerts/` — AlertNotificationCenter
- `frontend/src/components/dashboard/` — RealTimeDashboard
- `frontend/src/components/sensors/` — 全8ファイル（3D, Charts, RealTime, Prophet等）
- `frontend/src/hooks/useWebSocket.js`
- `frontend/src/utils/api.js`
- `src/analytics/` — 全12ファイル（anomaly, ML, prediction, report等）
- `src/api/routes/analytics.py, sensors.py, substrate.py, websocket.py`
- `src/database/influxdb.py`
- `src/mqtt/client.py`
- `src/realtime/` — alert_manager, sensor_streamer
- `src/sensors/` — 全4ファイル
- `src/substrate/` — 全4ファイル
- `src/websocket/manager.py`

**修正済み:**
- `frontend/src/App.js` — 13タブ→5タブ、不要importの削除
- `frontend/src/index.css` — Fira Sans/Code、Tailwind除去
- `frontend/src/components/substrate/` — 4ファイルリファクタ
- `src/main.py` — 不要ルート登録の削除
- `src/config.py` — MQTT/InfluxDB設定の削除
- `src/database/__init__.py` — influxdb import の削除
- `src/auth/middleware.py` — 不要exempt_pathsの整理
- `src/api/routes/__init__.py` — 削除ルートのimport整理

### 検出済み課題

| # | 課題 | 優先度 | 対応タイミング |
|---|------|--------|-------------|
| 1 | OptimizedDataContext.js がimport残骸として残存 | **高** | Phase 0（即時） |
| 2 | plan.md が旧IoT監視計画のまま | 低 | Phase 0（削除） |
| 3 | gpt-oss-20b 推論性能（Mac mini上） | 中 | SD-4: 5月末にLM Studioでベンチマーク |
| 4 | E2Eテスト未整備（tests/e2e/ 空） | 中 | Phase 2-5〜 |
| 5 | material_types → 新テーブル分離時のデータ移行 | 中 | Phase 1 Migration 1 |

### 決定事項

- 開発計画を keikaku.md として管理
- 進捗を memo.md で継続記録
- 既存の認証・DB・APIパターンを最大限再利用
- 最適化後の総工数: 18.2人月（バッファ2.0人月をPhase 4に充当）

### 今後のアクション

**Phase 0（即時）:**
1. [ ] [SD-2] 死コード削除のコミット（コミット1）
2. [ ] pytest 52テスト全パス確認
3. [ ] [SD-2] UI/UX改善 + OptimizedDataContext.js 削除のコミット（コミット2）
4. [ ] npm start フロントエンド動作確認
5. [ ] plan.md の削除

**Phase 1開始（3月）:**
6. [ ] [SD-1] tsconfig.json 追加（allowJs: true）
7. [ ] [SD-3] Migration 1: suppliers + materials拡張
8. [ ] [SD-3] Migration 2: solidification_materials + leaching_suppressants
9. [ ] CRUD API 実装（suppliers, materials, solidification_materials, leaching_suppressants）
10. [ ] [SD-3] Migration 3: recipes + recipe_details
11. [ ] CRUD API 実装（recipes + recipe_details）
12. [ ] フロントエンドUI構築（新規TSX）
13. [ ] テスト（80%カバレッジ目標）
14. [ ] [SD-5] ML学習データ要件定義（4月末）

---

*次回セッションの開始点: Phase 0（未コミット変更の2段階コミット [SD-2]）*
