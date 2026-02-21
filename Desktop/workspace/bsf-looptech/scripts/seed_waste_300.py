"""
Generate 300 waste records over the past 2 months via REST API.
Usage: python scripts/seed_waste_300.py
"""

import random
import sys
from datetime import date, timedelta

import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 10.0

random.seed(42)

SOURCES = [
    "東日本環境サービス",
    "関西リサイクル",
    "中部産業廃棄物処理",
    "北海道グリーンテック",
    "九州エコソリューション",
]

WASTE_TYPES = [
    "汚泥（一般）",
    "焼却灰",
    "汚泥（有機）",
    "鉱さい",
    "ばいじん",
    "その他",
]

# Weights for waste type selection (general sludge & ash are most common)
WASTE_WEIGHTS = [30, 25, 15, 12, 10, 8]

# Elution thresholds (mg/L) from 土壌汚染対策法
THRESHOLDS = {
    "Pb": 0.01, "As": 0.01, "Cd": 0.003, "Cr6": 0.05,
    "Hg": 0.0005, "Se": 0.01, "F": 0.8, "B": 1.0,
}

# Typical pH/moisture/ignitionLoss ranges per waste type
TYPE_PROFILES = {
    "汚泥（一般）":  {"pH": (6.0, 8.0), "moisture": (55, 75), "ignitionLoss": (8, 20)},
    "焼却灰":       {"pH": (10.5, 12.5), "moisture": (10, 30), "ignitionLoss": (2, 8)},
    "汚泥（有機）":  {"pH": (5.5, 7.5), "moisture": (70, 85), "ignitionLoss": (25, 45)},
    "鉱さい":       {"pH": (8.5, 11.0), "moisture": (5, 20), "ignitionLoss": (1, 5)},
    "ばいじん":     {"pH": (9.0, 12.0), "moisture": (3, 15), "ignitionLoss": (0.5, 4)},
    "その他":       {"pH": (6.5, 9.0), "moisture": (30, 60), "ignitionLoss": (10, 30)},
}

# Typical weight ranges per waste type (tonnes)
WEIGHT_RANGES = {
    "汚泥（一般）":  (5, 25),
    "焼却灰":       (10, 35),
    "汚泥（有機）":  (3, 18),
    "鉱さい":       (15, 40),
    "ばいじん":     (2, 12),
    "その他":       (1, 15),
}

NOTES_TEMPLATES = {
    "汚泥（一般）": [
        "定期搬入。品質安定。",
        "下水処理場由来。含水率やや高め。",
        "工場排水処理汚泥。重金属注意。",
        "浄水場発生土。",
        "建設汚泥。土砂混じり。",
    ],
    "焼却灰": [
        "一般廃棄物焼却灰。",
        "産廃焼却施設由来。",
        "焼却飛灰。重金属濃度要確認。",
        "ストーカ炉主灰。",
        "流動床炉灰。粒度細かい。",
    ],
    "汚泥（有機）": [
        "食品工場排水汚泥。",
        "畜産系有機汚泥。臭気注意。",
        "製紙スラッジ。",
        "発酵残渣。",
        "有機物含有率高め。含水率注意。",
    ],
    "鉱さい": [
        "製鉄所高炉スラグ。",
        "電気炉スラグ。Cr注意。",
        "非鉄精錬スラグ。",
        "鋳物砂混合。",
        "転炉スラグ。粒度大きい。",
    ],
    "ばいじん": [
        "集塵灰。飛散防止要。",
        "電気炉ダスト。亜鉛含有。",
        "セメントキルンダスト。",
        "溶融飛灰。重金属高濃度。",
        "ボイラー灰。",
    ],
    "その他": [
        "建設混合廃棄物。種別確認済。",
        "廃石膏ボード粉砕物。",
        "ガラスくず混合。",
        "廃プラ焼却残渣。",
        "複合廃棄物。選別済み。",
    ],
}


def rand_range(lo: float, hi: float, decimals: int = 1) -> float:
    return round(random.uniform(lo, hi), decimals)


def generate_analysis(waste_type: str, severity: str) -> dict:
    """Generate analysis data.
    severity: 'pass' (all under 50% threshold), 'warn' (some 80-100%), 'fail' (some over)
    """
    profile = TYPE_PROFILES[waste_type]
    analysis = {
        "pH": rand_range(*profile["pH"]),
        "moisture": rand_range(*profile["moisture"]),
        "ignitionLoss": rand_range(*profile["ignitionLoss"]),
    }

    for metal, limit in THRESHOLDS.items():
        if severity == "pass":
            val = rand_range(limit * 0.05, limit * 0.5, 4)
        elif severity == "warn":
            # Some metals in warning zone (80-100% of limit)
            if random.random() < 0.35:
                val = rand_range(limit * 0.8, limit * 0.99, 4)
            else:
                val = rand_range(limit * 0.1, limit * 0.6, 4)
        else:  # fail
            if random.random() < 0.3:
                val = rand_range(limit * 1.1, limit * 3.0, 4)
            elif random.random() < 0.4:
                val = rand_range(limit * 0.8, limit * 0.99, 4)
            else:
                val = rand_range(limit * 0.1, limit * 0.6, 4)
        analysis[metal] = val

    return analysis


def _generate_formulation(analysis: dict, waste_type: str) -> dict:
    """Generate a formulation dict based on analysis (rule-based logic)."""
    moisture = analysis.get("moisture", 50.0)
    cr6 = analysis.get("Cr6", 0.0)

    # 汚染度スコア計算
    severity = 0.0
    for metal, limit in THRESHOLDS.items():
        val = analysis.get(metal, 0.0)
        if limit > 0 and val > limit:
            severity += (val / limit - 1.0)

    # 固化材タイプ
    if cr6 > 0.05:
        solidifier_type = "高炉セメントB種"
    else:
        solidifier_type = "普通ポルトランドセメント"

    # 固化材量
    base = 150 if "汚泥" in waste_type else 160
    solidifier_amount = round(
        base + max(0, moisture - 60) * 0.4 + severity * 55 + random.uniform(-10, 10)
    )
    solidifier_amount = max(80, min(350, solidifier_amount))

    # 抑制剤
    suppressant_type = ""
    suppressant_amount = 0.0
    if cr6 > 0.04:
        suppressant_type = "硫酸第一鉄"
        suppressant_amount = round(2.0 + severity * 3.0, 1)
    elif severity > 0.5:
        suppressant_type = "キレート剤A"
        suppressant_amount = round(2.0 + severity * 2.0, 1)

    return {
        "solidifierType": solidifier_type,
        "solidifierAmount": solidifier_amount,
        "solidifierUnit": "kg/t",
        "suppressorType": suppressant_type,
        "suppressorAmount": suppressant_amount,
        "suppressorUnit": "kg/t",
    }


def _generate_elution(analysis: dict, formulation: dict, passed: bool) -> dict:
    """Generate elution result dict."""
    solidifier_amount = formulation.get("solidifierAmount", 150)
    effectiveness = min(1.0, solidifier_amount / 250.0)

    elution = {}
    for metal, limit in THRESHOLDS.items():
        raw_val = analysis.get(metal, 0.0)
        if passed:
            suppressed = raw_val * (1.0 - effectiveness * 0.7)
            val = min(suppressed, limit * random.uniform(0.1, 0.85))
        else:
            if random.random() < 0.2:
                val = limit * random.uniform(1.1, 2.5)
            else:
                val = limit * random.uniform(0.1, 0.8)
        elution[metal] = round(max(0.0, val), 6)

    elution["passed"] = passed
    return elution


def generate_records(count: int = 300, days: int = 60) -> list[dict]:
    """Generate `count` waste records spread over `days` days."""
    today = date.today()
    records = []

    for i in range(count):
        day_offset = random.randint(0, days - 1)
        delivery = today - timedelta(days=day_offset)

        waste_type = random.choices(WASTE_TYPES, weights=WASTE_WEIGHTS, k=1)[0]
        source = random.choice(SOURCES)
        wt_range = WEIGHT_RANGES[waste_type]
        weight = rand_range(*wt_range)

        # 65% analyzed, 10% pending, 25% formulated
        roll = random.random()
        if roll < 0.10:
            status = "pending"
            analysis = None
            notes = f"分析待ち。{random.choice(NOTES_TEMPLATES[waste_type])}"
        elif roll < 0.35:
            status = "formulated"
            severity = random.choices(["pass", "warn", "fail"], weights=[50, 35, 15], k=1)[0]
            analysis = generate_analysis(waste_type, severity)
            notes = f"配合済。{random.choice(NOTES_TEMPLATES[waste_type])}"
        else:
            status = "analyzed"
            severity = random.choices(["pass", "warn", "fail"], weights=[50, 35, 15], k=1)[0]
            analysis = generate_analysis(waste_type, severity)
            notes = random.choice(NOTES_TEMPLATES[waste_type])

        record = {
            "source": source,
            "deliveryDate": str(delivery),
            "wasteType": waste_type,
            "weight": weight,
            "weightUnit": "t",
            "status": status,
            "notes": notes,
        }
        if analysis:
            record["analysis"] = analysis

        # 配合済レコードには配合データと溶出試験結果を付与
        if status == "formulated" and analysis:
            formulation = _generate_formulation(analysis, waste_type)
            record["formulation"] = formulation
            passed = random.random() < 0.8  # 80%合格
            record["elutionResult"] = _generate_elution(analysis, formulation, passed)

        records.append(record)

    # Sort by date for natural ordering
    records.sort(key=lambda r: r["deliveryDate"])
    return records


def main():
    print("Checking backend connectivity...")
    try:
        r = httpx.get(f"{BASE}/health", timeout=TIMEOUT)
        if r.status_code != 200:
            print("ERROR: Backend not healthy")
            sys.exit(1)
        print(f"Backend status: {r.json().get('status', 'unknown')}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to http://localhost:8000")
        sys.exit(1)

    records = generate_records(300, 60)
    print(f"\nGenerating {len(records)} waste records over 60 days...\n")

    success = 0
    fail = 0
    for i, rec in enumerate(records):
        r = httpx.post(
            f"{BASE}/api/waste/records",
            json=rec,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code in (200, 201):
            success += 1
        else:
            fail += 1
            if fail <= 3:
                print(f"  FAIL [{i}]: {r.status_code} {r.text[:120]}")

        # Progress every 50
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(records)} done ({success} ok, {fail} fail)")

    # Stats
    type_counts = {}
    status_counts = {}
    for rec in records:
        type_counts[rec["wasteType"]] = type_counts.get(rec["wasteType"], 0) + 1
        status_counts[rec["status"]] = status_counts.get(rec["status"], 0) + 1

    print(f"\n{'=' * 50}")
    print(f"Complete: {success} created, {fail} failed")
    print(f"\nBy waste type:")
    for wt, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {wt}: {cnt}")
    print(f"\nBy status:")
    for st, cnt in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {st}: {cnt}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
