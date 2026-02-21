"""
Seed formulation workflow demo data via REST API.

Creates formulation records at various workflow stages (proposed, accepted,
applied, verified, rejected) to populate the FormulationPanel UI.

Prerequisites:
  - Backend running on localhost:8000 with SKIP_AUTH=true
  - seed_dev_data.py already executed (suppliers, materials, waste records, recipes)

Usage:
  python scripts/seed_formulation_demo.py
"""

import random
import sys

import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 15.0

random.seed(2026)

# Elution thresholds (土壌汚染対策法)
THRESHOLDS = {
    "Pb": 0.01, "As": 0.01, "Cd": 0.003, "Cr6": 0.05,
    "Hg": 0.0005, "Se": 0.01, "F": 0.8, "B": 1.0,
}


def get(path: str) -> dict:
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT)
    return r.json() if r.status_code == 200 else {}


def post(path: str, data: dict | None = None) -> dict:
    r = httpx.post(f"{BASE}{path}", json=data, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        print(f"  FAIL {path}: {r.status_code} {r.text[:200]}")
        return {}
    return r.json()


def rand_elution(passed: bool) -> dict:
    """Generate realistic elution test results."""
    result = {}
    for metal, limit in THRESHOLDS.items():
        if passed:
            result[metal] = round(random.uniform(limit * 0.05, limit * 0.7), 4)
        else:
            # Most pass, but 1-2 metals exceed
            if random.random() < 0.2:
                result[metal] = round(random.uniform(limit * 1.1, limit * 2.5), 4)
            else:
                result[metal] = round(random.uniform(limit * 0.1, limit * 0.8), 4)
    return result


def main() -> None:
    # ── Check connectivity ──
    print("Checking backend connectivity...")
    try:
        health = get("/health")
        if not health:
            print("ERROR: Backend not responding")
            sys.exit(1)
        print(f"Backend status: {health.get('status', 'unknown')}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to http://localhost:8000")
        sys.exit(1)

    # ── Fetch existing waste records with analysis ──
    print("\nFetching waste records...")
    waste_resp = get("/api/waste/records?limit=50&sort_by=created_at&sort_order=desc")
    all_waste = waste_resp.get("items", []) if isinstance(waste_resp, dict) else []
    # Filter to records with analysis data
    eligible = [w for w in all_waste if w.get("analysis") and len(w["analysis"]) > 0]
    print(f"  Found {len(eligible)} waste records with analysis data")

    if len(eligible) < 3:
        print("ERROR: Need at least 3 analyzed waste records. Run seed_dev_data.py first.")
        sys.exit(1)

    # ── Fetch existing recipes ──
    print("Fetching recipes...")
    recipe_resp = get("/api/v1/recipes?limit=10")
    recipes = recipe_resp.get("items", []) if isinstance(recipe_resp, dict) else []
    print(f"  Found {len(recipes)} recipes")

    # ── Scenario 1: Full happy path (proposed → accepted → applied → verified PASS) ──
    print("\n=== Scenario 1: Happy path (verified, pass) ===")
    w1 = eligible[0]
    print(f"  Waste: {w1['source']} / {w1['wasteType']}")

    # Manual creation
    f1 = post("/api/v1/formulations", {
        "waste_record_id": w1["id"],
        "source_type": "manual",
        "planned_formulation": {
            "solidifierType": "高炉セメントB種",
            "solidifierAmount": 120.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 2800.0,
        "confidence": 0.85,
        "reasoning": [
            "汚泥（一般）向け標準配合",
            "過去の類似案件で成功実績あり",
            "コスト効率が最も高い",
        ],
        "notes": "デモ: 手動作成の配合案",
    })
    if not f1:
        print("  FAIL: Could not create formulation")
        return
    fid1 = f1["id"]
    print(f"  Created: {fid1[:8]}... (proposed)")

    # Accept
    post(f"/api/v1/formulations/{fid1}/accept")
    print(f"  Accepted")

    # Apply with actuals
    post(f"/api/v1/formulations/{fid1}/apply", {
        "status": "applied",
        "actual_formulation": {
            "solidifierType": "高炉セメントB種",
            "solidifierAmount": 125.0,
            "solidifierUnit": "kg/t",
        },
        "actual_cost": 2950.0,
    })
    print(f"  Applied (actual_cost=2950)")

    # Verify (pass)
    elution_pass = rand_elution(passed=True)
    post(f"/api/v1/formulations/{fid1}/verify", {
        "status": "verified",
        "elution_result": elution_pass,
        "elution_passed": True,
        "notes": "全項目基準値以下。合格。",
    })
    print(f"  Verified (PASS)")

    # ── Scenario 2: Verified but failed ──
    print("\n=== Scenario 2: Verified (fail) ===")
    if len(eligible) > 4:
        w2 = eligible[4]
    else:
        w2 = eligible[min(1, len(eligible) - 1)]
    print(f"  Waste: {w2['source']} / {w2['wasteType']}")

    f2 = post("/api/v1/formulations", {
        "waste_record_id": w2["id"],
        "source_type": "rule",
        "planned_formulation": {
            "solidifierType": "マグネシア系固化材MG-100",
            "solidifierAmount": 150.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 5400.0,
        "confidence": 0.62,
        "reasoning": ["ルールベース推薦", "重金属高濃度のため固化材増量"],
        "notes": "デモ: ルールベース推薦（不合格ケース）",
    })
    if f2:
        fid2 = f2["id"]
        post(f"/api/v1/formulations/{fid2}/accept")
        post(f"/api/v1/formulations/{fid2}/apply", {
            "status": "applied",
            "actual_formulation": {
                "solidifierType": "マグネシア系固化材MG-100",
                "solidifierAmount": 145.0,
                "solidifierUnit": "kg/t",
            },
            "actual_cost": 5200.0,
        })
        elution_fail = rand_elution(passed=False)
        post(f"/api/v1/formulations/{fid2}/verify", {
            "status": "verified",
            "elution_result": elution_fail,
            "elution_passed": False,
            "notes": "Pb, Cr6 基準超過。再配合要。",
        })
        print(f"  Verified (FAIL)")

    # ── Scenario 3: Rejected ──
    print("\n=== Scenario 3: Rejected ===")
    w3 = eligible[min(2, len(eligible) - 1)]
    print(f"  Waste: {w3['source']} / {w3['wasteType']}")

    f3 = post("/api/v1/formulations", {
        "waste_record_id": w3["id"],
        "source_type": "optimization",
        "planned_formulation": {
            "solidifierType": "特殊固化材SF-200",
            "solidifierAmount": 250.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 8500.0,
        "confidence": 0.91,
        "reasoning": ["最適化ソルバーによる配合", "最大安全率を優先"],
        "notes": "デモ: コスト超過のため却下",
    })
    if f3:
        fid3 = f3["id"]
        post(f"/api/v1/formulations/{fid3}/reject", {
            "status": "rejected",
            "notes": "コスト超過（予算上限5,000円/t）。低コスト配合を再検討。",
        })
        print(f"  Rejected")

    # ── Scenario 4: Accepted (waiting for apply) ──
    print("\n=== Scenario 4: Accepted (待ち適用) ===")
    w4 = eligible[min(3, len(eligible) - 1)]
    print(f"  Waste: {w4['source']} / {w4['wasteType']}")

    f4 = post("/api/v1/formulations", {
        "waste_record_id": w4["id"],
        "source_type": "similarity",
        "planned_formulation": {
            "solidifierType": "生石灰CaO-95",
            "solidifierAmount": 100.0,
            "solidifierUnit": "kg/t",
            "suppressant": "鉛キレート剤LC-500",
            "suppressantAmount": 15.0,
        },
        "estimated_cost": 3200.0,
        "confidence": 0.78,
        "reasoning": [
            "類似度分析による推薦",
            "過去3ヶ月の類似廃棄物配合を参照",
            "鉛キレート剤を併用してPb溶出を抑制",
        ],
        "notes": "デモ: 承認済・適用待ち",
    })
    if f4:
        fid4 = f4["id"]
        post(f"/api/v1/formulations/{fid4}/accept")
        print(f"  Accepted (waiting for apply)")

    # ── Scenario 5: Applied (waiting for verify) ──
    print("\n=== Scenario 5: Applied (待ち検証) ===")
    w5 = eligible[min(1, len(eligible) - 1)]
    print(f"  Waste: {w5['source']} / {w5['wasteType']}")

    f5 = post("/api/v1/formulations", {
        "waste_record_id": w5["id"],
        "source_type": "ml",
        "planned_formulation": {
            "solidifierType": "高炉セメントB種",
            "solidifierAmount": 90.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 2100.0,
        "confidence": 0.88,
        "reasoning": [
            "ML予測モデル(RandomForest v3)による推薦",
            "有機汚泥向け低添加率配合",
            "過去120件の学習データに基づく",
        ],
        "notes": "デモ: 適用済・溶出検証待ち",
    })
    if f5:
        fid5 = f5["id"]
        post(f"/api/v1/formulations/{fid5}/accept")
        post(f"/api/v1/formulations/{fid5}/apply", {
            "status": "applied",
            "actual_formulation": {
                "solidifierType": "高炉セメントB種",
                "solidifierAmount": 92.0,
                "solidifierUnit": "kg/t",
            },
            "actual_cost": 2150.0,
        })
        print(f"  Applied (waiting for verify)")

    # ── Scenario 6: Multiple proposed (pending review) ──
    print("\n=== Scenario 6: Proposed (未レビュー) x3 ===")
    for i, w_idx in enumerate([min(5, len(eligible) - 1), min(6, len(eligible) - 1), min(7, len(eligible) - 1)]):
        if w_idx >= len(eligible):
            w_idx = i % len(eligible)
        w = eligible[w_idx]
        sources = ["ml", "similarity", "recipe"]
        amounts = [110.0, 130.0, 160.0]
        costs = [2500.0, 3100.0, 4200.0]
        confs = [0.82, 0.75, 0.69]

        f = post("/api/v1/formulations", {
            "waste_record_id": w["id"],
            "source_type": sources[i],
            "planned_formulation": {
                "solidifierType": "高炉セメントB種",
                "solidifierAmount": amounts[i],
                "solidifierUnit": "kg/t",
            },
            "estimated_cost": costs[i],
            "confidence": confs[i],
            "reasoning": [f"推薦元: {sources[i]}", f"添加量: {amounts[i]}kg/t"],
            "notes": f"デモ: 提案#{i + 1}（未レビュー）",
        })
        if f:
            print(f"  Proposed #{i + 1}: {w['source']} / {w['wasteType']} ({sources[i]})")

    # ── Summary ──
    print("\n" + "=" * 50)
    print("Formulation demo data seeded!")
    print("  Verified (pass):  1")
    print("  Verified (fail):  1")
    print("  Rejected:         1")
    print("  Accepted:         1")
    print("  Applied:          1")
    print("  Proposed:         3")
    print("  ─────────────────")
    print("  Total:            8")
    print("=" * 50)


if __name__ == "__main__":
    main()
