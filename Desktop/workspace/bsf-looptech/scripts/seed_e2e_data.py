"""
Seed deterministic E2E test data via REST API.

Creates a complete dataset for Playwright E2E tests with fixed, recognizable
names suitable for assertion matching.

Prerequisites:
  - Backend running on localhost:8000 with SKIP_AUTH=true
  - Database is empty or freshly migrated

Usage:
  python scripts/seed_e2e_data.py
"""

import random
import sys
from datetime import date, timedelta
from typing import Any

import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 15.0

# Fixed seed for deterministic data
random.seed(20260221)


# ── HTTP helpers ──


def get(path: str) -> dict[str, Any]:
    """GET helper."""
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT)
    return r.json() if r.status_code == 200 else {}


def post(path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """POST helper with error reporting."""
    r = httpx.post(f"{BASE}{path}", json=data, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        print(f"  FAIL {path}: {r.status_code} {r.text[:200]}")
        return {}
    return r.json()


def put(path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """PUT helper."""
    r = httpx.put(f"{BASE}{path}", json=data, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        print(f"  FAIL {path}: {r.status_code} {r.text[:200]}")
        return {}
    return r.json()


# ── Elution data generators ──

THRESHOLDS = {
    "Pb": 0.01, "As": 0.01, "Cd": 0.003, "Cr6": 0.05,
    "Hg": 0.0005, "Se": 0.01, "F": 0.8, "B": 1.0,
}


def rand_elution(passed: bool) -> dict[str, float]:
    """Generate realistic elution test results."""
    result: dict[str, float] = {}
    for metal, limit in THRESHOLDS.items():
        if passed:
            result[metal] = round(random.uniform(limit * 0.05, limit * 0.7), 4)
        else:
            if random.random() < 0.2:
                result[metal] = round(random.uniform(limit * 1.1, limit * 2.5), 4)
            else:
                result[metal] = round(random.uniform(limit * 0.1, limit * 0.8), 4)
    return result


# ══════════════════════════════════════════════
#  Data definitions (fixed, recognizable names)
# ══════════════════════════════════════════════

SUPPLIERS = [
    {
        "name": "テスト業者A",
        "contact_person": "田中一郎",
        "phone": "03-1111-1111",
        "email": "tanaka@test-a.example.com",
        "address": "東京都千代田区テスト町1-1-1",
        "waste_types": ["汚泥（一般）", "焼却灰"],
        "notes": "E2Eテスト用業者A",
    },
    {
        "name": "テスト業者B",
        "contact_person": "山田花子",
        "phone": "06-2222-2222",
        "email": "yamada@test-b.example.com",
        "address": "大阪府大阪市テスト区2-2-2",
        "waste_types": ["汚泥（有機）", "鉱さい"],
        "notes": "E2Eテスト用業者B",
    },
    {
        "name": "テスト業者C",
        "contact_person": "佐藤三郎",
        "phone": "052-3333-3333",
        "email": "sato@test-c.example.com",
        "address": "愛知県名古屋市テスト町3-3-3",
        "waste_types": ["ばいじん", "その他"],
        "notes": "E2Eテスト用業者C",
    },
]

SOLIDIFICATION_MATERIALS = [
    {
        "name": "E2Eテスト固化材A",
        "material_type": "cement",
        "base_material": "高炉スラグ微粉末+ポルトランドセメント",
        "effective_components": {"ite": 45, "calcium": 30},
        "applicable_soil_types": ["汚泥（一般）", "焼却灰"],
        "min_addition_rate": 50,
        "max_addition_rate": 200,
        "unit_cost": 12.5,
        "unit": "kg",
        "notes": "E2Eテスト用固化材A（汎用）",
    },
    {
        "name": "E2Eテスト固化材B",
        "material_type": "calcium",
        "base_material": "酸化カルシウム",
        "effective_components": {"CaO": 95},
        "applicable_soil_types": ["汚泥（有機）"],
        "min_addition_rate": 30,
        "max_addition_rate": 150,
        "unit_cost": 8.0,
        "unit": "kg",
        "notes": "E2Eテスト用固化材B（有機汚泥向け）",
    },
    {
        "name": "E2Eテスト固化材C",
        "material_type": "other",
        "base_material": "エトリンガイト系複合材",
        "effective_components": {"aluminate": 60},
        "applicable_soil_types": ["焼却灰", "ばいじん"],
        "min_addition_rate": 60,
        "max_addition_rate": 250,
        "unit_cost": 25.0,
        "unit": "kg",
        "notes": "E2Eテスト用固化材C（高濃度対応）",
    },
]

LEACHING_SUPPRESSANTS = [
    {
        "name": "E2Eテスト抑制剤A",
        "suppressant_type": "キレート",
        "target_metals": ["Pb", "Cd", "Hg"],
        "min_addition_rate": 5,
        "max_addition_rate": 30,
        "ph_range_min": 6.0,
        "ph_range_max": 12.0,
        "unit_cost": 45.0,
        "unit": "kg",
        "notes": "E2Eテスト用抑制剤A（鉛キレート）",
    },
    {
        "name": "E2Eテスト抑制剤B",
        "suppressant_type": "還元",
        "target_metals": ["Cr6"],
        "min_addition_rate": 10,
        "max_addition_rate": 50,
        "ph_range_min": 2.0,
        "ph_range_max": 9.0,
        "unit_cost": 35.0,
        "unit": "kg",
        "notes": "E2Eテスト用抑制剤B（Cr6還元）",
    },
]

today = date.today()

WASTE_RECORDS = [
    {
        "source": "テスト業者A",
        "deliveryDate": str(today - timedelta(days=1)),
        "wasteType": "汚泥（一般）",
        "weight": 12.5,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {
            "pH": 7.2, "moisture": 65.3, "ignitionLoss": 12.1,
            "Pb": 0.003, "As": 0.002, "Cd": 0.001, "Cr6": 0.01,
            "Hg": 0.0001, "Se": 0.003, "F": 0.2, "B": 0.3,
        },
        "notes": "E2Eテスト: 分析済み汚泥（合格）",
    },
    {
        "source": "テスト業者A",
        "deliveryDate": str(today - timedelta(days=3)),
        "wasteType": "焼却灰",
        "weight": 20.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {
            "pH": 11.5, "moisture": 22.0, "ignitionLoss": 5.3,
            "Pb": 0.009, "As": 0.008, "Cd": 0.002, "Cr6": 0.042,
            "Hg": 0.0004, "Se": 0.009, "F": 0.7, "B": 0.85,
        },
        "notes": "E2Eテスト: 分析済み焼却灰（警告域）",
    },
    {
        "source": "テスト業者B",
        "deliveryDate": str(today - timedelta(days=5)),
        "wasteType": "汚泥（有機）",
        "weight": 8.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {
            "pH": 6.8, "moisture": 78.5, "ignitionLoss": 35.2,
            "Pb": 0.002, "As": 0.001, "Cd": 0.0005, "Cr6": 0.005,
            "Hg": 0.00005, "Se": 0.002, "F": 0.15, "B": 0.1,
        },
        "notes": "E2Eテスト: 分析済み有機汚泥（合格）",
    },
    {
        "source": "テスト業者B",
        "deliveryDate": str(today - timedelta(days=7)),
        "wasteType": "鉱さい",
        "weight": 30.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {
            "pH": 9.8, "moisture": 15.0, "ignitionLoss": 2.1,
            "Pb": 0.025, "As": 0.015, "Cd": 0.005, "Cr6": 0.08,
            "Hg": 0.0002, "Se": 0.012, "F": 1.2, "B": 1.5,
        },
        "notes": "E2Eテスト: 分析済み鉱さい（超過）",
    },
    {
        "source": "テスト業者C",
        "deliveryDate": str(today),
        "wasteType": "ばいじん",
        "weight": 5.5,
        "weightUnit": "t",
        "status": "pending",
        "notes": "E2Eテスト: 分析待ちばいじん",
    },
]


# ══════════════════════════════════════════════
#  Seed functions
# ══════════════════════════════════════════════


def seed_demo_user() -> bool:
    """Register demo/demo user."""
    print("\n=== Demo User ===")
    resp = post("/auth/register", {
        "username": "demo",
        "password": "demo",
    })
    if resp:
        print(f"  OK: demo user created (id={resp.get('id', '?')[:8]}...)")
        return True
    # User may already exist
    print("  SKIP: demo user may already exist")
    return True


def seed_suppliers() -> dict[str, str]:
    """Create suppliers. Returns {name: id} mapping."""
    print("\n=== Suppliers (搬入先) ===")
    mapping: dict[str, str] = {}
    for s in SUPPLIERS:
        resp = post("/api/v1/suppliers", s)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (id={resp['id'][:8]}...)")
    return mapping


def seed_solidification_materials() -> dict[str, str]:
    """Create solidification materials. Returns {name: id} mapping."""
    print("\n=== Solidification Materials (固化材) ===")
    mapping: dict[str, str] = {}
    for m in SOLIDIFICATION_MATERIALS:
        resp = post("/api/v1/solidification-materials", m)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (id={resp['id'][:8]}...)")
    return mapping


def seed_leaching_suppressants() -> dict[str, str]:
    """Create leaching suppressants. Returns {name: id} mapping."""
    print("\n=== Leaching Suppressants (溶出抑制剤) ===")
    mapping: dict[str, str] = {}
    for s in LEACHING_SUPPRESSANTS:
        resp = post("/api/v1/leaching-suppressants", s)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (id={resp['id'][:8]}...)")
    return mapping


def seed_recipes(
    solid_ids: dict[str, str],
    supp_ids: dict[str, str],
) -> list[str]:
    """Create recipes with details. Returns list of recipe IDs."""
    print("\n=== Recipes (配合レシピ) ===")
    recipe_ids: list[str] = []

    solid_list = list(solid_ids.values())
    supp_list = list(supp_ids.values())

    if len(solid_list) < 2 or len(supp_list) < 1:
        print("  SKIP: Not enough materials for recipes")
        return recipe_ids

    recipes = [
        {
            "name": "E2Eテストレシピ汚泥標準",
            "waste_type": "汚泥（一般）",
            "target_strength": 200.0,
            "status": "active",
            "notes": "E2Eテスト用: 汚泥標準配合",
            "details": [
                {
                    "material_id": solid_list[0],
                    "material_type": "solidification",
                    "addition_rate": 120.0,
                    "order_index": 1,
                    "notes": "固化材A 120kg/t",
                },
                {
                    "material_id": supp_list[0],
                    "material_type": "suppressant",
                    "addition_rate": 10.0,
                    "order_index": 2,
                    "notes": "抑制剤A 10kg/t",
                },
            ],
        },
        {
            "name": "E2Eテストレシピ焼却灰高強度",
            "waste_type": "焼却灰",
            "target_strength": 500.0,
            "status": "active",
            "notes": "E2Eテスト用: 焼却灰高強度配合",
            "details": [
                {
                    "material_id": solid_list[2] if len(solid_list) > 2 else solid_list[0],
                    "material_type": "solidification",
                    "addition_rate": 200.0,
                    "order_index": 1,
                    "notes": "固化材C 200kg/t",
                },
                {
                    "material_id": supp_list[1] if len(supp_list) > 1 else supp_list[0],
                    "material_type": "suppressant",
                    "addition_rate": 25.0,
                    "order_index": 2,
                    "notes": "抑制剤B 25kg/t",
                },
            ],
        },
    ]

    for r in recipes:
        resp = post("/api/v1/recipes", r)
        if resp:
            recipe_ids.append(resp["id"])
            n_details = len(resp.get("details", []))
            print(f"  OK: {resp['name']} ({n_details} details)")

    return recipe_ids


def seed_incoming_materials(supplier_ids: dict[str, str]) -> dict[str, str]:
    """Create incoming materials. Returns {name: id} mapping."""
    print("\n=== Incoming Materials (搬入物) ===")
    mapping: dict[str, str] = {}

    materials_data = [
        {
            "supplier_name": "テスト業者A",
            "material_category": "汚泥",
            "name": "E2Eテスト搬入物:一般汚泥",
            "description": "一般汚泥（下水処理場由来）",
            "default_weight_unit": "t",
            "notes": "E2Eテスト用",
        },
        {
            "supplier_name": "テスト業者B",
            "material_category": "焼却残渣",
            "name": "E2Eテスト搬入物:焼却灰",
            "description": "一般廃棄物焼却灰",
            "default_weight_unit": "t",
            "notes": "E2Eテスト用",
        },
        {
            "supplier_name": "テスト業者C",
            "material_category": "ばいじん",
            "name": "E2Eテスト搬入物:ばいじん",
            "description": "集塵灰",
            "default_weight_unit": "t",
            "notes": "E2Eテスト用",
        },
    ]

    for m in materials_data:
        supplier_name = m.pop("supplier_name")
        supplier_id = supplier_ids.get(supplier_name)
        if not supplier_id:
            print(f"  SKIP: supplier '{supplier_name}' not found")
            continue
        m["supplier_id"] = supplier_id
        resp = post("/api/v1/incoming-materials", m)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (supplier={supplier_name})")

    return mapping


def seed_delivery_schedules(
    incoming_material_ids: dict[str, str],
) -> list[dict[str, Any]]:
    """Create delivery schedules with various statuses. Returns created records."""
    print("\n=== Delivery Schedules (搬入予定) ===")
    created: list[dict[str, Any]] = []

    mat_list = list(incoming_material_ids.values())
    mat_names = list(incoming_material_ids.keys())

    if not mat_list:
        print("  SKIP: No incoming materials available")
        return created

    schedules = [
        {
            "incoming_material_id": mat_list[0],
            "scheduled_date": str(today + timedelta(days=3)),
            "estimated_weight": 15.0,
            "weight_unit": "t",
            "notes": "E2Eテスト: 予定ステータス",
        },
        {
            "incoming_material_id": mat_list[0],
            "scheduled_date": str(today + timedelta(days=7)),
            "estimated_weight": 10.0,
            "weight_unit": "t",
            "notes": "E2Eテスト: 予定ステータス(2件目)",
        },
        {
            "incoming_material_id": mat_list[1 % len(mat_list)],
            "scheduled_date": str(today - timedelta(days=1)),
            "estimated_weight": 20.0,
            "weight_unit": "t",
            "notes": "E2Eテスト: 搬入済みに変更予定",
        },
        {
            "incoming_material_id": mat_list[1 % len(mat_list)],
            "scheduled_date": str(today - timedelta(days=3)),
            "estimated_weight": 8.0,
            "weight_unit": "t",
            "notes": "E2Eテスト: 搬入済みステータス",
        },
        {
            "incoming_material_id": mat_list[2 % len(mat_list)],
            "scheduled_date": str(today - timedelta(days=5)),
            "estimated_weight": 5.5,
            "weight_unit": "t",
            "notes": "E2Eテスト: 配合準備完了ステータス",
        },
    ]

    for i, s in enumerate(schedules):
        resp = post("/api/v1/delivery-schedules", s)
        if resp:
            created.append(resp)
            mat_idx = mat_list.index(s["incoming_material_id"]) if s["incoming_material_id"] in mat_list else 0
            print(f"  OK: Schedule #{i + 1} ({mat_names[mat_idx]}, {s['scheduled_date']})")

    # Update statuses for schedules 4 and 5
    if len(created) >= 4:
        schedule_4 = created[3]
        put(f"/api/v1/delivery-schedules/{schedule_4['id']}/status", {
            "status": "delivered",
            "actual_weight": 7.8,
        })
        print(f"  STATUS: Schedule #4 -> delivered")

    if len(created) >= 5:
        schedule_5 = created[4]
        put(f"/api/v1/delivery-schedules/{schedule_5['id']}/status", {
            "status": "delivered",
            "actual_weight": 5.5,
        })
        print(f"  STATUS: Schedule #5 -> delivered")
        # Then update to ready_for_formulation
        put(f"/api/v1/delivery-schedules/{schedule_5['id']}/status", {
            "status": "ready_for_formulation",
        })
        print(f"  STATUS: Schedule #5 -> ready_for_formulation")

    return created


def seed_waste_records() -> list[dict[str, Any]]:
    """Create waste records. Returns created records."""
    print("\n=== Waste Records (搬入記録) ===")
    created: list[dict[str, Any]] = []

    for w in WASTE_RECORDS:
        resp = post("/api/waste/records", w)
        if resp:
            created.append(resp)
            print(f"  OK: {w['source']} / {w['wasteType']} / {w['weight']}t ({w['status']})")

    return created


def seed_formulations(waste_records: list[dict[str, Any]]) -> None:
    """Create formulation records at various workflow stages."""
    print("\n=== Formulations (配合記録) ===")

    # Filter to records with analysis data
    eligible = [w for w in waste_records if w.get("analysis") and len(w["analysis"]) > 0]
    if len(eligible) < 3:
        print("  SKIP: Need at least 3 analyzed waste records")
        return

    # ── Formulation 1: proposed (pending review) ──
    print("\n  --- Formulation 1: Proposed ---")
    f1 = post("/api/v1/formulations", {
        "waste_record_id": eligible[0]["id"],
        "source_type": "manual",
        "planned_formulation": {
            "solidifierType": "E2Eテスト固化材A",
            "solidifierAmount": 120.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 2800.0,
        "confidence": 0.85,
        "reasoning": [
            "汚泥（一般）向け標準配合",
            "過去の類似案件で成功実績あり",
        ],
        "notes": "E2Eテスト: 提案ステータス",
    })
    if f1:
        print(f"    Created: {f1['id'][:8]}... (proposed)")

    # ── Formulation 2: accepted (happy path) ──
    print("\n  --- Formulation 2: Accepted ---")
    f2 = post("/api/v1/formulations", {
        "waste_record_id": eligible[1]["id"],
        "source_type": "rule",
        "planned_formulation": {
            "solidifierType": "E2Eテスト固化材B",
            "solidifierAmount": 150.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 3500.0,
        "confidence": 0.72,
        "reasoning": ["ルールベース推薦", "焼却灰向け高添加率"],
        "notes": "E2Eテスト: 承認済みステータス",
    })
    if f2:
        post(f"/api/v1/formulations/{f2['id']}/accept")
        print(f"    Created + Accepted: {f2['id'][:8]}...")

    # ── Formulation 3: verified (full workflow) ──
    print("\n  --- Formulation 3: Verified ---")
    f3 = post("/api/v1/formulations", {
        "waste_record_id": eligible[2]["id"],
        "source_type": "similarity",
        "planned_formulation": {
            "solidifierType": "E2Eテスト固化材A",
            "solidifierAmount": 100.0,
            "solidifierUnit": "kg/t",
        },
        "estimated_cost": 2400.0,
        "confidence": 0.90,
        "reasoning": [
            "類似度分析による推薦",
            "過去の類似廃棄物配合を参照",
        ],
        "notes": "E2Eテスト: 検証済みステータス（合格）",
    })
    if f3:
        fid3 = f3["id"]
        post(f"/api/v1/formulations/{fid3}/accept")
        post(f"/api/v1/formulations/{fid3}/apply", {
            "status": "applied",
            "actual_formulation": {
                "solidifierType": "E2Eテスト固化材A",
                "solidifierAmount": 105.0,
                "solidifierUnit": "kg/t",
            },
            "actual_cost": 2550.0,
        })
        elution = rand_elution(passed=True)
        post(f"/api/v1/formulations/{fid3}/verify", {
            "status": "verified",
            "elution_result": elution,
            "elution_passed": True,
            "notes": "E2Eテスト: 全項目基準値以下。合格。",
        })
        print(f"    Created -> Accepted -> Applied -> Verified (PASS): {fid3[:8]}...")


# ══════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════


def main() -> None:
    # ── Check connectivity ──
    print("=" * 60)
    print("BSF-LoopTech E2E Test Data Seeder")
    print("=" * 60)
    print("\nChecking backend connectivity...")
    try:
        health = get("/health")
        if not health:
            print("ERROR: Backend not responding on http://localhost:8000")
            sys.exit(1)
        print(f"Backend status: {health.get('status', 'unknown')}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to http://localhost:8000")
        print("Start the backend: python -m uvicorn src.main:app --port 8000 --reload")
        sys.exit(1)

    # ── Seed in dependency order ──
    seed_demo_user()
    supplier_ids = seed_suppliers()
    solid_ids = seed_solidification_materials()
    supp_ids = seed_leaching_suppressants()
    recipe_ids = seed_recipes(solid_ids, supp_ids)
    incoming_material_ids = seed_incoming_materials(supplier_ids)
    delivery_schedules = seed_delivery_schedules(incoming_material_ids)
    waste_records = seed_waste_records()
    seed_formulations(waste_records)

    # ── Summary ──
    print("\n" + "=" * 60)
    print("E2E Test Data Seeding Complete!")
    print("-" * 60)
    print(f"  Demo User:              1")
    print(f"  Suppliers:              {len(supplier_ids)}")
    print(f"  Solidification Mats:    {len(solid_ids)}")
    print(f"  Leaching Suppressants:  {len(supp_ids)}")
    print(f"  Recipes:                {len(recipe_ids)}")
    print(f"  Incoming Materials:     {len(incoming_material_ids)}")
    print(f"  Delivery Schedules:     {len(delivery_schedules)}")
    print(f"  Waste Records:          {len(waste_records)}")
    print(f"  Formulations:           3 (proposed, accepted, verified)")
    print("=" * 60)


if __name__ == "__main__":
    main()
