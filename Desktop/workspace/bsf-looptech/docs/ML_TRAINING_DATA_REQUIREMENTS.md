# ML学習データ要件定義書

## Phase 1-7: ML学習データ要件定義
**作成日**: 2026-02-11
**対象**: Phase 3 scikit-learn Random Forest モデル構築の前提資料

---

## 1. 現行システム分析

### 1.1 現行推奨エンジン (`recommender.py`)

| 項目 | 現行実装 |
|------|---------|
| 手法 | 類似度ベース + ルールベース フォールバック |
| 類似度計算 | 重み付きユークリッド距離（11特徴量） |
| ルールベース | 廃棄物種類別の固定係数 |
| 閾値 | 過去実績 ≥ 3件で類似度モード、< 3件でルールモード |
| 出力 | 固化材タイプ・量、抑制剤タイプ・量、信頼度 |

### 1.2 現行データフロー

```
搬入 → 分析 → 配合推奨 → 配合実施 → 溶出試験 → 合格/不合格
         ↓         ↓           ↓           ↓
      analysis  recommend   formulation  elution_result
       (JSON)   (engine)     (JSON)       (JSON+passed)
```

### 1.3 現行テーブル構造の ML 関連フィールド

| テーブル | フィールド | ML利用 |
|---------|----------|--------|
| waste_records.analysis | `{pH, moisture, ignitionLoss, Pb, As, Cd, Cr6, Hg, Se, F, B}` | **入力特徴量** |
| waste_records.waste_type | 廃棄物種類（汚泥、焼却灰等） | **カテゴリ特徴量** |
| waste_records.source | 搬入元名称 | カテゴリ特徴量（補助） |
| waste_records.formulation | `{solidifierType, solidifierAmount, suppressorType, suppressorAmount}` | **目標変数** |
| waste_records.elution_result | `{Pb, As, ..., passed}` | **ラベル（成否）** |
| suppliers.waste_types | 搬入先の主要廃棄物種類 | 補助特徴量 |
| solidification_materials | 固化材マスタ（添加率範囲、コスト等） | 制約条件 |
| leaching_suppressants | 抑制剤マスタ（対象重金属、pH範囲等） | 制約条件 |

---

## 2. ML モデル設計

### 2.1 問題定義

**タスク**: 廃棄物分析結果から最適な配合（固化材・抑制剤の種類と量）を予測する

| 項目 | 内容 |
|------|------|
| 学習タイプ | 教師あり学習（回帰 + 分類） |
| アルゴリズム | scikit-learn Random Forest |
| モデル構成 | 2段階: (1) 材料選択（分類） → (2) 添加量予測（回帰） |
| フォールバック | 現行 `recommender.py` をデータ不足時に使用 |

### 2.2 モデル A: 材料選択（分類）

| 出力 | 型 | クラス例 |
|------|-----|---------|
| solidifier_type | カテゴリ | 普通ポルトランドセメント, 高炉セメントB種, 石灰系固化材 |
| suppressant_type | カテゴリ | なし, 硫酸第一鉄, キレート剤A, キレート剤B |

### 2.3 モデル B: 添加量予測（回帰）

| 出力 | 型 | 単位 | 典型的範囲 |
|------|-----|------|-----------|
| solidifier_amount | float | kg/t | 100–300 |
| suppressant_amount | float | kg/t | 0–15 |

---

## 3. 特徴量定義

### 3.1 数値特徴量（連続値）

| 特徴量 | フィールド | 単位 | 典型範囲 | ML重要度 | 現行データ有無 |
|--------|----------|------|---------|---------|-------------|
| pH | analysis.pH | - | 4.0–13.0 | 高 | **有** |
| 水分率 | analysis.moisture | % | 10–95 | 高 | **有** |
| 強熱減量 | analysis.ignitionLoss | % | 2–60 | 中 | **有** |
| 鉛 (Pb) | analysis.Pb | mg/L | 0–0.2 | 最高 | **有** |
| 砒素 (As) | analysis.As | mg/L | 0–0.05 | 最高 | **有** |
| カドミウム (Cd) | analysis.Cd | mg/L | 0–0.01 | 最高 | **有** |
| 六価クロム (Cr6) | analysis.Cr6 | mg/L | 0–0.3 | 最高 | **有** |
| 水銀 (Hg) | analysis.Hg | mg/L | 0–0.002 | 最高 | **有** |
| セレン (Se) | analysis.Se | mg/L | 0–0.03 | 高 | **有** |
| フッ素 (F) | analysis.F | mg/L | 0–2.0 | 高 | **有** |
| ほう素 (B) | analysis.B | mg/L | 0–1.5 | 中 | **有** |

### 3.2 追加推奨特徴量（Phase 3 で waste_records.analysis に追加）

| 特徴量 | フィールド | 単位 | 典型範囲 | 根拠 |
|--------|----------|------|---------|------|
| 密度 | analysis.density | g/cm³ | 1.0–2.5 | 配合量の体積換算に影響 |
| 粒度 (D50) | analysis.particleSize | mm | 0.001–10 | 固化反応速度に影響 |
| 有機物含有量 | analysis.organicContent | % | 0–30 | 固化阻害要因 |
| 塩化物イオン | analysis.Cl | mg/L | 0–5000 | セメント系固化材の選択に影響 |
| 硫酸イオン | analysis.SO4 | mg/L | 0–3000 | セメント耐久性に影響 |

### 3.3 カテゴリ特徴量

| 特徴量 | フィールド | エンコーディング | カテゴリ例 |
|--------|----------|----------------|----------|
| 廃棄物種類 | waste_type | One-Hot | 汚泥（一般）, 焼却灰, 飛灰, 汚染土壌, 建設汚泥 |
| 搬入元 | source / supplier_id | Target Encoding | 工場A, 工場B, ... |

### 3.4 導出特徴量（Feature Engineering）

| 特徴量 | 計算式 | 根拠 |
|--------|--------|------|
| severity_score | Σ max(0, metal/limit - 1) × weight | 溶出基準超過度 |
| metal_count_exceeded | count(metal > limit) | 超過項目数 |
| max_exceedance_ratio | max(metal/limit) | 最大超過倍率 |
| ph_deviation | abs(pH - 7.0) | 中性からの偏差 |
| moisture_high | moisture > 60 ? 1 : 0 | 高含水フラグ |

---

## 4. 目標変数定義

### 4.1 直接目標変数

| 変数 | 型 | 格納先 | 備考 |
|------|-----|--------|------|
| solidifier_type | str | formulation.solidifierType | 分類タスク |
| solidifier_amount | float | formulation.solidifierAmount | 回帰タスク |
| suppressant_type | str | formulation.suppressorType | 分類タスク |
| suppressant_amount | float | formulation.suppressorAmount | 回帰タスク |

### 4.2 評価ラベル

| 変数 | 型 | 格納先 | 備考 |
|------|-----|--------|------|
| elution_passed | bool | elution_result.passed | 配合の成否判定 |

---

## 5. 学習データ要件

### 5.1 必要データ量

| 段階 | レコード数 | 精度目標 | 備考 |
|------|----------|---------|------|
| 最小起動 | 50件 | R² ≥ 0.5 | ルールベースの補強程度 |
| 実用レベル | 200件 | R² ≥ 0.7 | 類似度ベースを上回る |
| 高精度 | 500件以上 | R² ≥ 0.85 | 独立した予測が可能 |

### 5.2 データ品質要件

| 要件 | 内容 |
|------|------|
| **完全な処理サイクル** | analysis → formulation → elution_result の3段階すべて記録済み |
| **ラベル付き** | elution_result.passed が true/false で記録済み |
| **必須特徴量** | pH, moisture, 重金属8項目のうち最低5項目以上が非null |
| **廃棄物種類分布** | 各waste_typeで最低10件以上のサンプル |
| **結果のバランス** | passed=true と passed=false の比率が 9:1 以下（不均衡対策必要） |

### 5.3 データ収集クエリ（学習データ抽出条件）

```sql
SELECT
    wr.id,
    wr.waste_type,
    wr.source,
    wr.analysis,
    wr.formulation,
    wr.elution_result,
    wr.delivery_date,
    s.name AS supplier_name,
    s.waste_types AS supplier_waste_types
FROM waste_records wr
LEFT JOIN suppliers s ON wr.supplier_id = s.id
WHERE
    wr.status = 'formulated'
    AND wr.analysis IS NOT NULL
    AND wr.formulation IS NOT NULL
    AND wr.elution_result IS NOT NULL
    AND (wr.elution_result->>'passed') IS NOT NULL
    AND wr.analysis->>'pH' IS NOT NULL
ORDER BY wr.delivery_date;
```

---

## 6. 学習データスキーマ

### 6.1 フラット化スキーマ（ML入力用）

学習時に `waste_records` の JSON カラムをフラット化して使用する。
新規テーブルは不要。`pandas DataFrame` に変換して処理。

```python
# training_data_schema.py

FEATURE_COLUMNS = {
    # 数値特徴量（analysis JSONから抽出）
    "pH": float,
    "moisture": float,
    "ignitionLoss": float,
    "Pb": float,
    "As": float,
    "Cd": float,
    "Cr6": float,
    "Hg": float,
    "Se": float,
    "F": float,
    "B": float,
    # Phase 3 追加（任意）
    "density": float,
    "particleSize": float,
    "organicContent": float,
    "Cl": float,
    "SO4": float,
}

CATEGORY_COLUMNS = {
    "waste_type": str,      # One-Hot encoding
    "supplier_id": str,     # Target encoding
}

TARGET_COLUMNS = {
    "solidifier_type": str,    # Classification
    "solidifier_amount": float, # Regression
    "suppressant_type": str,    # Classification
    "suppressant_amount": float, # Regression
}

LABEL_COLUMN = {
    "elution_passed": bool,    # Overall success/failure
}
```

### 6.2 データ抽出パイプライン

```
waste_records (DB)
  ↓ SQLAlchemy query
JSON rows
  ↓ flatten analysis/formulation/elution_result
pandas DataFrame (フラット化済み)
  ↓ Feature engineering (導出特徴量追加)
  ↓ Encoding (One-Hot, Target)
  ↓ Imputation (欠損値処理: median for numeric, mode for category)
  ↓ Normalization (StandardScaler for numeric)
Training-ready numpy arrays
  ↓ train_test_split (80/20, stratified by waste_type)
Model training (RandomForestClassifier / RandomForestRegressor)
```

---

## 7. 合成データ戦略

### 7.1 データ不足時の対策

実運用データが 50 件に満たない初期段階では、合成データで補完する。

| 手法 | 適用場面 | 実装 |
|------|---------|------|
| **ルールベース合成** | 初期段階（0–50件） | `recommender.py` の既知ルールからサンプル生成 |
| **摂動ベース** | 中間段階（50–200件） | 既存データ ± ガウスノイズ |
| **SMOTE** | 不均衡対策 | `imblearn.over_sampling.SMOTE` |

### 7.2 合成データ生成スクリプト設計

```python
# scripts/generate_training_data.py（Phase 3で実装）

def generate_synthetic_records(n: int = 100) -> list[dict]:
    """
    ルールベースで合成学習データを生成。
    recommender.py の SOLIDIFIER_RULES + ELUTION_LIMITS を基準にする。
    """
    # 1. ランダムな analysis を生成（FEATURE_RANGES 内）
    # 2. rule_based_recommendation で formulation を決定
    # 3. formulation の品質に基づいて elution_result を模擬
    # 4. ノイズを加えてバリエーション確保
    ...
```

---

## 8. モデル評価基準

### 8.1 分類モデル（材料選択）

| 指標 | 目標 |
|------|------|
| Accuracy | ≥ 80% |
| F1-score (weighted) | ≥ 0.75 |
| 交差検証 (5-fold) | 標準偏差 < 0.1 |

### 8.2 回帰モデル（添加量予測）

| 指標 | 目標 |
|------|------|
| R² score | ≥ 0.7 |
| MAE (固化材) | < 30 kg/t |
| MAE (抑制剤) | < 3 kg/t |
| 交差検証 (5-fold) | 標準偏差 < 0.15 |

### 8.3 実用評価（溶出試験合格率）

| 指標 | 目標 |
|------|------|
| 予測配合での溶出合格率 | ≥ 85% |
| 現行ルールベース比の改善 | ≥ +10% |

---

## 9. 実装ロードマップ

| 時期 | タスク | 入力 | 出力 |
|------|--------|------|------|
| **2月 (本書)** | 要件定義 | 現行システム分析 | 本ドキュメント |
| **6月前半** | データ抽出パイプライン | waste_records | pandas DataFrame |
| **6月前半** | 特徴量エンジニアリング | DataFrame | 学習用行列 |
| **6月中旬** | モデル構築・学習 | 学習データ | joblib モデルファイル |
| **6月後半** | 評価・チューニング | テストデータ | 精度レポート |
| **7月前半** | 予測API実装 | モデル | `/api/v1/predict/*` |
| **7月前半** | recommender.py 統合 | API | ML優先 + ルールフォールバック |

---

## 10. 既存コードとの統合方針

### 10.1 recommender.py の段階的置換

```
Phase 3 開始時:
  recommender.py (現行) ← そのまま稼働

Phase 3 中盤:
  ml_predictor.py (新規) ← Random Forest 推論
  recommender.py ← フォールバック専用

Phase 3 完了時:
  recommend_formulation() が内部で切り替え:
    if ml_model_available and data_count >= 50:
        return ml_predictor.predict(analysis)
    else:
        return rule_based_recommendation(analysis)
```

### 10.2 既存定数の再利用

| 定数 | 現在地 | ML利用 |
|------|--------|--------|
| `ELUTION_LIMITS` | recommender.py | 導出特徴量 (severity_score) + 制約条件 |
| `FEATURE_WEIGHTS` | recommender.py | 特徴量重要度の初期値参考 |
| `FEATURE_RANGES` | recommender.py | 正規化範囲の初期値 |
| `SOLIDIFIER_RULES` | recommender.py | 合成データ生成のルール |
| `ELUTION_THRESHOLDS` | service.py | 評価ラベル算出 |

---

## 11. analysis JSON スキーマ標準化

現行の `waste_records.analysis` は任意のJSON。ML利用のためスキーマを明確化する。

### 11.1 必須フィールド（学習データとして使用する最低条件）

```json
{
  "pH": 7.5,
  "moisture": 45.0,
  "Pb": 0.005,
  "As": 0.003
}
```

最低4項目（pH + moisture + 重金属2項目以上）

### 11.2 推奨フィールド（精度向上のため）

```json
{
  "pH": 7.5,
  "moisture": 45.0,
  "ignitionLoss": 15.0,
  "Pb": 0.005,
  "As": 0.003,
  "Cd": 0.001,
  "Cr6": 0.02,
  "Hg": 0.0002,
  "Se": 0.005,
  "F": 0.3,
  "B": 0.5
}
```

### 11.3 formulation JSON スキーマ標準化

```json
{
  "solidifierType": "普通ポルトランドセメント",
  "solidifierAmount": 160,
  "solidifierUnit": "kg/t",
  "suppressorType": "キレート剤A",
  "suppressorAmount": 3.5,
  "suppressorUnit": "kg/t"
}
```

### 11.4 elution_result JSON スキーマ標準化

```json
{
  "Pb": 0.003,
  "As": 0.002,
  "Cd": 0.001,
  "Cr6": 0.01,
  "Hg": 0.0001,
  "Se": 0.004,
  "F": 0.2,
  "B": 0.3,
  "passed": true
}
```

---

## 付録: DBスキーマ変更は不要

現行の `waste_records` テーブル構造で ML 学習データの格納・抽出が可能。
理由:
- analysis/formulation/elution_result は JSON カラムで柔軟
- フラット化は抽出時に pandas で実施
- 追加特徴量 (density, particleSize 等) も analysis JSON に追加するだけ

Phase 3 で必要な新規テーブルは **モデル管理用のみ**:
- `ml_models` (モデルバージョン、精度、ファイルパス)
- `ml_predictions` (予測ログ、フィードバック追跡)

これらは Phase 3 開始時にマイグレーションで追加する。

---

## 12. 現実的データ量見積もり

### 12.1 クライアント搬入スループット

実運用環境でのデータ蓄積速度を見積もる。
搬入→分析→配合→溶出試験の完全サイクルを経たレコードのみがML学習データとして利用可能。

| 指標 | 見積値 | 備考 |
|------|--------|------|
| 1日あたりの搬入件数 | 5〜10件 | 施設規模・稼働日による |
| 分析完了率 | 90% | 一部は分析省略（定型搬入） |
| 配合実施率 | 70% | 分析結果により処理不要のケースあり |
| 溶出試験実施率 | 80% | 配合後に試験実施 |
| **完全サイクル到達率** | **約50%** | 5〜10件/日 × 50% = 2.5〜5件/日 |

### 12.2 ML準備レベル到達タイムライン

稼働日数を月20日と仮定し、1日あたり2.5〜5件の完全レコードが蓄積される場合：

| 経過月数 | 累積レコード数（低） | 累積レコード数（高） | ML準備レベル | 推奨戦略 |
|---------|-------------------|-------------------|-------------|---------|
| 1ヶ月 | 50 | 100 | **最小起動** (R²≥0.5) | 合成データ併用、ルールベースをメインに |
| 2ヶ月 | 100 | 200 | **実用レベル接近** | 合成データ比率を徐々に低下 |
| 3ヶ月 | 150 | 300 | **実用レベル** (R²≥0.7) | ML予測をプライマリに切替 |
| 6ヶ月 | 300 | 600 | **高精度** (R²≥0.85) | ML単独運用可能 |
| 12ヶ月 | 600 | 1200 | **安定運用** | 継続的再学習で精度維持 |

### 12.3 合成データ併用戦略

実データが不足する初期段階では、合成データで補完しながら段階的にMLモデルの精度を向上させる。

```
Phase 1: 実データ 0〜50件（1ヶ月目前半）
  → 合成データ 250件 + 実データ → 合成比率 80%以上
  → ルールベース推薦をメイン、MLは参考値として表示
  → scripts/seed_ml_training_data.py で初期データ投入

Phase 2: 実データ 50〜200件（1〜3ヶ月目）
  → 合成データ 150件 + 実データ → 合成比率 40〜75%
  → MLモデルを週次で再学習
  → 合成データの摂動バリエーションを追加（augment_with_perturbation）

Phase 3: 実データ 200件以上（3ヶ月目以降）
  → 合成データ不要 → 実データのみで学習
  → MLモデルをプライマリ推薦エンジンに昇格
  → ルールベースはフォールバック専用

Phase 4: 実データ 500件以上（6ヶ月目以降）
  → モデルの定期再学習（月次バッチ）
  → A/Bテストで新旧モデルを比較
  → 特徴量重要度の定期レビュー
```

### 12.4 データ品質モニタリング

`scripts/validate_ml_data.py` を定期実行し、以下を監視：

| チェック項目 | 閾値 | 判定 |
|-------------|------|------|
| 総レコード数 | ≥50 | PASS/FAIL |
| 特徴量完全性 | ≥80% | PASS/WARN/FAIL |
| 廃棄物種類分布 | 全6種 ≥5件 | PASS/WARN |
| 合格/不合格比率 | 70〜90% pass | PASS/WARN |
| 外れ値比率 | <5% | PASS/WARN |
| **総合判定** | — | production_ready / practical / insufficient |

### 12.5 合成データ生成ツール

| ツール | 用途 | レコード数 |
|--------|------|-----------|
| `scripts/seed_ml_training_data.py` | 初期ML学習データ投入（API経由） | 250件 |
| `src/ml/synthetic_data.py` | プログラマティック合成（学習パイプライン内部） | 任意 |
| `scripts/seed_waste_300.py` | デモ用搬入データ（配合済25%含む） | 300件 |
| `scripts/validate_ml_data.py` | データ品質検証レポート | — |
