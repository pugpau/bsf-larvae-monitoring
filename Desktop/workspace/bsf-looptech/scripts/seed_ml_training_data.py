"""
Generate 250 complete labeled ML training records via REST API.

Each record contains:
- waste_record: analysis JSON (pH, moisture, ignitionLoss, 8 metals)
- formulation: solidifier + suppressant configuration
- elution_result: 8 metal measurements + passed boolean

Uses rule-based logic from recommender.py and synthetic data patterns
from src/ml/synthetic_data.py for realistic data generation.

Prerequisites:
  - Backend running on localhost:8000 with SKIP_AUTH=true
  - Database initialized (tables exist)

Usage:
  python scripts/seed_ml_training_data.py
"""

import random
import sys
from datetime import date, timedelta
from typing import Any

import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 15.0

random.seed(2026_02_21)

# ── 廃棄物種類定義 ──

WASTE_TYPES = ["汚泥", "焼却灰", "ばいじん", "鉱さい", "廃酸", "廃アルカリ"]
WASTE_WEIGHTS = [30, 25, 15, 12, 10, 8]

SOURCES = [
    "東日本環境サービス",
    "関西リサイクル",
    "中部産業廃棄物処理",
    "北海道グリーンテック",
    "九州エコソリューション",
]

# ── 溶出基準（土壌汚染対策法）──

ELUTION_LIMITS: dict[str, float] = {
    "Pb": 0.01, "As": 0.01, "Cd": 0.003, "Cr6": 0.05,
    "Hg": 0.0005, "Se": 0.01, "F": 0.8, "B": 1.0,
}

METALS = list(ELUTION_LIMITS.keys())

# ── 廃棄物種類別プロファイル ──

TYPE_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "汚泥":     {"pH": (5.5, 8.5),  "moisture": (55, 85), "ignitionLoss": (8, 35)},
    "焼却灰":   {"pH": (10.0, 12.5), "moisture": (10, 30), "ignitionLoss": (2, 8)},
    "ばいじん": {"pH": (9.0, 12.0),  "moisture": (3, 15),  "ignitionLoss": (0.5, 4)},
    "鉱さい":   {"pH": (8.5, 11.0),  "moisture": (5, 20),  "ignitionLoss": (1, 5)},
    "廃酸":     {"pH": (1.0, 4.0),   "moisture": (85, 98), "ignitionLoss": (0.5, 3)},
    "廃アルカリ": {"pH": (10.0, 13.0), "moisture": (80, 95), "ignitionLoss": (1, 5)},
}

# ── 固化材ルール（recommender.py 準拠）──

SOLIDIFIER_TYPES = [
    "普通ポルトランドセメント",
    "高炉セメントB種",
    "マグネシア系固化材MG-100",
    "生石灰CaO-95",
    "特殊固化材SF-200",
]

SUPPRESSANT_TYPES = [
    "",  # なし
    "硫酸第一鉄",
    "キレート剤A",
    "鉛キレート剤LC-500",
]

NOTES_TEMPLATES: dict[str, list[str]] = {
    "汚泥":     ["定期搬入。品質安定。", "下水処理場由来。", "工場排水処理汚泥。"],
    "焼却灰":   ["一般廃棄物焼却灰。", "産廃焼却施設由来。", "ストーカ炉主灰。"],
    "ばいじん": ["集塵灰。飛散防止要。", "電気炉ダスト。", "溶融飛灰。重金属高濃度。"],
    "鉱さい":   ["製鉄所高炉スラグ。", "電気炉スラグ。Cr注意。", "非鉄精錬スラグ。"],
    "廃酸":     ["酸洗浄廃液。", "エッチング廃液。", "電池廃液。中和処理要。"],
    "廃アルカリ": ["脱脂廃液。", "写真廃液。", "アルカリ洗浄排水。"],
}


def rand_range(lo: float, hi: float, decimals: int = 4) -> float:
    """指定範囲内の乱数を生成。"""
    return round(random.uniform(lo, hi), decimals)


def generate_analysis(waste_type: str, severity: str) -> dict[str, float]:
    """廃棄物分析データを生成。

    Args:
        waste_type: 廃棄物種類
        severity: 'clean'(基準値以下), 'marginal'(80-100%), 'exceed'(基準超過)
    """
    profile = TYPE_PROFILES[waste_type]
    analysis: dict[str, float] = {
        "pH": rand_range(*profile["pH"], decimals=1),
        "moisture": rand_range(*profile["moisture"], decimals=1),
        "ignitionLoss": rand_range(*profile["ignitionLoss"], decimals=1),
    }

    for metal, limit in ELUTION_LIMITS.items():
        if severity == "clean":
            val = rand_range(limit * 0.02, limit * 0.5)
        elif severity == "marginal":
            if random.random() < 0.3:
                val = rand_range(limit * 0.7, limit * 0.99)
            else:
                val = rand_range(limit * 0.05, limit * 0.5)
        else:  # exceed
            if random.random() < 0.35:
                val = rand_range(limit * 1.1, limit * 3.0)
            elif random.random() < 0.3:
                val = rand_range(limit * 0.8, limit * 1.05)
            else:
                val = rand_range(limit * 0.1, limit * 0.6)
        analysis[metal] = val

    return analysis


def compute_severity_score(analysis: dict[str, float]) -> float:
    """溶出基準超過度スコアを算出（recommender.py 準拠）。"""
    score = 0.0
    for metal, limit in ELUTION_LIMITS.items():
        val = analysis.get(metal, 0.0)
        if limit > 0 and val > limit:
            score += (val / limit - 1.0)
    return score


def generate_formulation(
    analysis: dict[str, float], waste_type: str
) -> dict[str, Any]:
    """ルールベースで配合データを生成（recommender.py の _rule_based_recommendation 準拠）。"""
    moisture = analysis.get("moisture", 50.0)
    cr6 = analysis.get("Cr6", 0.0)
    severity = compute_severity_score(analysis)

    # 固化材タイプ決定
    if cr6 > 0.05:
        solidifier_type = "高炉セメントB種"
    elif waste_type in ("廃酸", "廃アルカリ"):
        solidifier_type = "生石灰CaO-95"
    elif severity > 1.0:
        solidifier_type = "マグネシア系固化材MG-100"
    else:
        solidifier_type = random.choice(["普通ポルトランドセメント", "高炉セメントB種"])

    # 固化材量決定
    base = 160 if waste_type not in ("汚泥",) else 150
    solidifier_amount = round(
        base
        + max(0, moisture - 60) * 0.4
        + severity * 55
        + random.uniform(-10, 10)
    )
    solidifier_amount = max(80, min(350, solidifier_amount))

    # 抑制剤決定
    suppressant_type = ""
    suppressant_amount = 0.0
    if cr6 > 0.04:
        suppressant_type = "硫酸第一鉄"
        suppressant_amount = round(2.0 + severity * 3.0 + random.uniform(-0.5, 0.5), 1)
    elif severity > 0.5:
        suppressant_type = "キレート剤A"
        suppressant_amount = round(2.0 + severity * 2.0 + random.uniform(-0.3, 0.3), 1)
    elif random.random() < 0.15:
        suppressant_type = "鉛キレート剤LC-500"
        suppressant_amount = round(random.uniform(1.0, 4.0), 1)

    suppressant_amount = max(0.0, suppressant_amount)

    return {
        "solidifierType": solidifier_type,
        "solidifierAmount": solidifier_amount,
        "solidifierUnit": "kg/t",
        "suppressorType": suppressant_type,
        "suppressorAmount": suppressant_amount,
        "suppressorUnit": "kg/t",
    }


def simulate_elution(
    analysis: dict[str, float],
    formulation: dict[str, Any],
    target_passed: bool,
) -> dict[str, Any]:
    """溶出試験結果をシミュレーション生成。

    Args:
        analysis: 分析データ
        formulation: 配合データ
        target_passed: 目標合否（80:20 比率制御用）
    """
    solidifier_amount = formulation.get("solidifierAmount", 150)
    # 処理効果: 固化材量が多いほど抑制効果大
    effectiveness = min(1.0, solidifier_amount / 250.0)

    elution: dict[str, Any] = {}
    all_passed = True

    for metal, limit in ELUTION_LIMITS.items():
        raw_val = analysis.get(metal, 0.0)

        if target_passed:
            # 合格ケース: 基準値以下に抑制
            suppressed = raw_val * (1.0 - effectiveness * 0.7)
            val = min(suppressed, limit * random.uniform(0.1, 0.85))
        else:
            # 不合格ケース: 1-2 項目が基準超過
            if random.random() < 0.2:
                val = limit * random.uniform(1.1, 2.5)
                all_passed = False
            else:
                val = limit * random.uniform(0.1, 0.8)

        elution[metal] = round(max(0.0, val), 6)

    # 不合格ターゲットだが全項目が偶然パスした場合、最悪の1項目を超過させる
    if not target_passed and all_passed:
        worst_metal = max(METALS, key=lambda m: analysis.get(m, 0.0) / ELUTION_LIMITS[m])
        elution[worst_metal] = round(ELUTION_LIMITS[worst_metal] * random.uniform(1.2, 2.0), 6)

    elution["passed"] = target_passed
    return elution


def post(path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """POST リクエスト送信。"""
    r = httpx.post(f"{BASE}{path}", json=data, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        return {}
    return r.json()


def get(path: str) -> dict[str, Any]:
    """GET リクエスト送信。"""
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT)
    return r.json() if r.status_code == 200 else {}


def main() -> None:
    """250件の完全ラベル付きML学習データを生成・投入。"""
    total = 250
    pass_count = 200  # 80%
    fail_count = 50   # 20%

    print("=" * 60)
    print("ML Training Data Seeder")
    print(f"  Target: {total} records (pass={pass_count}, fail={fail_count})")
    print("=" * 60)

    # ── 接続確認 ──
    print("\nChecking backend connectivity...")
    try:
        health = get("/health")
        if not health:
            print("ERROR: Backend not responding")
            sys.exit(1)
        print(f"Backend status: {health.get('status', 'unknown')}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to http://localhost:8000")
        sys.exit(1)

    # ── レコード生成 ──
    today = date.today()
    success = 0
    fail_api = 0
    type_counts: dict[str, int] = {}
    pass_fail_counts = {"pass": 0, "fail": 0}

    # 合否ラベルのシャッフル（80:20）
    labels = [True] * pass_count + [False] * fail_count
    random.shuffle(labels)

    for i in range(total):
        waste_type = random.choices(WASTE_TYPES, weights=WASTE_WEIGHTS, k=1)[0]
        source = random.choice(SOURCES)
        target_passed = labels[i]

        # 不合格データは汚染度の高い分析データを生成
        if target_passed:
            severity = random.choices(
                ["clean", "marginal", "exceed"],
                weights=[50, 35, 15],
                k=1,
            )[0]
        else:
            severity = random.choices(
                ["marginal", "exceed"],
                weights=[30, 70],
                k=1,
            )[0]

        # 搬入日: 過去6ヶ月に分散
        day_offset = random.randint(0, 180)
        delivery = today - timedelta(days=day_offset)

        analysis = generate_analysis(waste_type, severity)
        formulation = generate_formulation(analysis, waste_type)
        elution = simulate_elution(analysis, formulation, target_passed)

        weight = round(random.uniform(3, 30), 1)
        notes = random.choice(NOTES_TEMPLATES[waste_type])

        # ── Step 1: WasteRecord 作成 ──
        waste_record = {
            "source": source,
            "deliveryDate": str(delivery),
            "wasteType": waste_type,
            "weight": weight,
            "weightUnit": "t",
            "status": "formulated",
            "notes": f"ML学習データ。{notes}",
            "analysis": analysis,
            "formulation": formulation,
            "elutionResult": elution,
        }

        resp = post("/api/waste/records", waste_record)
        if resp:
            success += 1
            type_counts[waste_type] = type_counts.get(waste_type, 0) + 1
            pass_fail_counts["pass" if target_passed else "fail"] += 1
        else:
            fail_api += 1
            if fail_api <= 5:
                print(f"  FAIL [{i}]: API error for {waste_type}")

        # 進捗表示（50件ごと）
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{total} done ({success} ok, {fail_api} fail)")

    # ── サマリ ──
    print(f"\n{'=' * 60}")
    print(f"ML Training Data Seeding Complete")
    print(f"  Total: {success} created, {fail_api} failed")
    print(f"\nBy waste type:")
    for wt, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {wt}: {cnt}")
    print(f"\nPass/Fail distribution:")
    print(f"  Pass: {pass_fail_counts['pass']} ({pass_fail_counts['pass']/max(success,1)*100:.0f}%)")
    print(f"  Fail: {pass_fail_counts['fail']} ({pass_fail_counts['fail']/max(success,1)*100:.0f}%)")
    print(f"\nML readiness: {'READY (>=50)' if success >= 50 else 'INSUFFICIENT (<50)'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
