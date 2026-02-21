"""
Seed development data via REST API.
Usage: python scripts/seed_dev_data.py
Requires: backend running on localhost:8000 with SKIP_AUTH=true
"""

import json
import sys
from datetime import date, timedelta

import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 10.0


def post(path: str, data: dict) -> dict:
    """POST helper with error reporting."""
    r = httpx.post(f"{BASE}{path}", json=data, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        print(f"  FAIL {path}: {r.status_code} {r.text[:200]}")
        return {}
    return r.json()


def get(path: str) -> dict:
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT)
    return r.json() if r.status_code == 200 else {}


# ---------------------------------------------------------------------------
# 1. Suppliers (仕入先) — 5件
# ---------------------------------------------------------------------------
SUPPLIERS = [
    {
        "name": "東日本環境サービス",
        "contact_person": "田中太郎",
        "phone": "03-1234-5678",
        "email": "tanaka@ej-env.example.com",
        "address": "東京都江東区豊洲1-2-3",
        "waste_types": ["汚泥（一般）", "焼却灰"],
        "notes": "月間搬入量約50t",
    },
    {
        "name": "関西リサイクル",
        "contact_person": "山本花子",
        "phone": "06-9876-5432",
        "email": "yamamoto@kr-recycle.example.com",
        "address": "大阪府堺市中区深井1-4-5",
        "waste_types": ["汚泥（有機）", "その他"],
        "notes": "有機汚泥専門",
    },
    {
        "name": "中部産業廃棄物処理",
        "contact_person": "佐藤一郎",
        "phone": "052-111-2222",
        "email": "sato@chubu-sanpai.example.com",
        "address": "愛知県名古屋市港区2-3-4",
        "waste_types": ["鉱さい", "ばいじん"],
        "notes": "製鉄所由来の鉱さいが中心",
    },
    {
        "name": "北海道グリーンテック",
        "contact_person": "鈴木次郎",
        "phone": "011-333-4444",
        "email": "suzuki@hkd-green.example.com",
        "address": "北海道札幌市白石区5-6-7",
        "waste_types": ["汚泥（一般）", "汚泥（有機）"],
        "notes": "冬季は搬入頻度低下",
    },
    {
        "name": "九州エコソリューション",
        "contact_person": "高橋美咲",
        "phone": "092-555-6666",
        "email": "takahashi@kyushu-eco.example.com",
        "address": "福岡県福岡市博多区8-9-10",
        "waste_types": ["焼却灰", "ばいじん", "その他"],
        "notes": "焼却施設3箇所から搬入",
    },
]

# ---------------------------------------------------------------------------
# 2. Solidification Materials (固化材) — 4件
# ---------------------------------------------------------------------------
SOLID_MATERIALS = [
    {
        "name": "高炉セメントB種",
        "material_type": "cement",
        "base_material": "高炉スラグ微粉末 + ポルトランドセメント",
        "effective_components": {"ite": 45, "ite": 30, "ite_calcium": 15},
        "applicable_soil_types": ["汚泥（一般）", "焼却灰"],
        "min_addition_rate": 50,
        "max_addition_rate": 200,
        "unit_cost": 12.5,
        "unit": "kg",
        "notes": "汎用性が高く、コスト効率良好",
    },
    {
        "name": "生石灰CaO-95",
        "material_type": "calcium",
        "base_material": "酸化カルシウム (CaO 95%以上)",
        "effective_components": {"CaO": 95, "MgO": 2},
        "applicable_soil_types": ["汚泥（有機）", "汚泥（一般）"],
        "min_addition_rate": 30,
        "max_addition_rate": 150,
        "unit_cost": 8.0,
        "unit": "kg",
        "notes": "含水率低減に効果的。発熱注意",
    },
    {
        "name": "マグネシア系固化材MG-100",
        "material_type": "ite",
        "base_material": "酸化マグネシウム (MgO 85%以上)",
        "effective_components": {"MgO": 85, "SiO2": 8},
        "applicable_soil_types": ["鉱さい", "ばいじん"],
        "min_addition_rate": 40,
        "max_addition_rate": 180,
        "unit_cost": 18.0,
        "unit": "kg",
        "notes": "重金属溶出抑制効果あり",
    },
    {
        "name": "特殊固化材SF-200",
        "material_type": "other",
        "base_material": "エトリンガイト系複合材",
        "effective_components": {"ite_calcium_aluminate": 60, "ite_calcium": 25},
        "applicable_soil_types": ["焼却灰", "ばいじん", "その他"],
        "min_addition_rate": 60,
        "max_addition_rate": 250,
        "unit_cost": 25.0,
        "unit": "kg",
        "notes": "高濃度重金属汚染に対応。コスト高",
    },
]

# ---------------------------------------------------------------------------
# 3. Leaching Suppressants (溶出抑制剤) — 3件
# ---------------------------------------------------------------------------
SUPPRESSANTS = [
    {
        "name": "鉛キレート剤LC-500",
        "suppressant_type": "キレート",
        "target_metals": ["Pb", "Cd", "Hg"],
        "min_addition_rate": 5,
        "max_addition_rate": 30,
        "ph_range_min": 6.0,
        "ph_range_max": 12.0,
        "unit_cost": 45.0,
        "unit": "kg",
        "notes": "鉛・カドミウム・水銀の不溶化に高い効果",
    },
    {
        "name": "六価クロム還元剤CR-300",
        "suppressant_type": "還元",
        "target_metals": ["Cr6"],
        "min_addition_rate": 10,
        "max_addition_rate": 50,
        "ph_range_min": 2.0,
        "ph_range_max": 9.0,
        "unit_cost": 35.0,
        "unit": "kg",
        "notes": "Cr6+をCr3+に還元。酸性域で効果大",
    },
    {
        "name": "複合型抑制剤MX-800",
        "suppressant_type": "複合",
        "target_metals": ["Pb", "As", "Cr6", "Se", "F", "B"],
        "min_addition_rate": 15,
        "max_addition_rate": 60,
        "ph_range_min": 5.0,
        "ph_range_max": 11.0,
        "unit_cost": 60.0,
        "unit": "kg",
        "notes": "広範囲の重金属に対応する複合型。高コスト",
    },
]

# ---------------------------------------------------------------------------
# 4. Waste Records (搬入記録) — 10件
# ---------------------------------------------------------------------------
today = date.today()

WASTE_RECORDS = [
    # --- pass: 全項目基準値以下 ---
    {
        "source": "東日本環境サービス",
        "deliveryDate": str(today - timedelta(days=1)),
        "wasteType": "汚泥（一般）",
        "weight": 12.5,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 7.2, "moisture": 65.3, "ignitionLoss": 12.1,
                     "Pb": 0.003, "As": 0.002, "Cd": 0.001, "Cr6": 0.01,
                     "Hg": 0.0001, "Se": 0.003, "F": 0.2, "B": 0.3},
        "notes": "定期搬入。品質安定。",
    },
    {
        "source": "北海道グリーンテック",
        "deliveryDate": str(today - timedelta(days=2)),
        "wasteType": "汚泥（有機）",
        "weight": 8.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 6.8, "moisture": 78.5, "ignitionLoss": 35.2,
                     "Pb": 0.002, "As": 0.001, "Cd": 0.0005, "Cr6": 0.005,
                     "Hg": 0.00005, "Se": 0.002, "F": 0.15, "B": 0.1},
        "notes": "有機物含有率高め。含水率注意。",
    },
    # --- warn: 一部項目が基準値の80%超 ---
    {
        "source": "九州エコソリューション",
        "deliveryDate": str(today - timedelta(days=3)),
        "wasteType": "焼却灰",
        "weight": 20.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 11.5, "moisture": 22.0, "ignitionLoss": 5.3,
                     "Pb": 0.009, "As": 0.008, "Cd": 0.002, "Cr6": 0.042,
                     "Hg": 0.0004, "Se": 0.009, "F": 0.7, "B": 0.85},
        "notes": "Pb, F, B が警告域。配合調整要。",
    },
    {
        "source": "東日本環境サービス",
        "deliveryDate": str(today - timedelta(days=5)),
        "wasteType": "焼却灰",
        "weight": 15.3,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 12.0, "moisture": 18.5, "ignitionLoss": 3.8,
                     "Pb": 0.008, "As": 0.004, "Cd": 0.0025, "Cr6": 0.035,
                     "Hg": 0.0003, "Se": 0.005, "F": 0.65, "B": 0.5},
        "notes": "Cd 警告域。前回より改善。",
    },
    # --- fail: 基準値超過あり ---
    {
        "source": "中部産業廃棄物処理",
        "deliveryDate": str(today - timedelta(days=4)),
        "wasteType": "鉱さい",
        "weight": 30.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 9.8, "moisture": 15.0, "ignitionLoss": 2.1,
                     "Pb": 0.025, "As": 0.015, "Cd": 0.005, "Cr6": 0.08,
                     "Hg": 0.0002, "Se": 0.012, "F": 1.2, "B": 1.5},
        "notes": "Pb, As, Cd, Cr6, Se, F, B 全て基準超過。特別配合必要。",
    },
    {
        "source": "中部産業廃棄物処理",
        "deliveryDate": str(today - timedelta(days=7)),
        "wasteType": "ばいじん",
        "weight": 5.5,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 10.5, "moisture": 8.2, "ignitionLoss": 1.5,
                     "Pb": 0.018, "As": 0.003, "Cd": 0.004, "Cr6": 0.06,
                     "Hg": 0.0008, "Se": 0.008, "F": 0.9, "B": 0.6},
        "notes": "Pb, Cd, Cr6, Hg, F 超過。溶出抑制剤併用要。",
    },
    # --- pending: 分析待ち ---
    {
        "source": "関西リサイクル",
        "deliveryDate": str(today),
        "wasteType": "汚泥（有機）",
        "weight": 10.0,
        "weightUnit": "t",
        "status": "pending",
        "notes": "本日搬入。分析待ち。",
    },
    {
        "source": "九州エコソリューション",
        "deliveryDate": str(today),
        "wasteType": "その他",
        "weight": 3.2,
        "weightUnit": "t",
        "status": "pending",
        "notes": "建設混合廃棄物。種別要確認。",
    },
    # --- additional analyzed records ---
    {
        "source": "関西リサイクル",
        "deliveryDate": str(today - timedelta(days=10)),
        "wasteType": "その他",
        "weight": 7.8,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 7.8, "moisture": 45.0, "ignitionLoss": 20.5,
                     "Pb": 0.005, "As": 0.003, "Cd": 0.001, "Cr6": 0.02,
                     "Hg": 0.0001, "Se": 0.004, "F": 0.35, "B": 0.4},
        "notes": "建設発生土混合。問題なし。",
    },
    {
        "source": "北海道グリーンテック",
        "deliveryDate": str(today - timedelta(days=14)),
        "wasteType": "汚泥（一般）",
        "weight": 18.0,
        "weightUnit": "t",
        "status": "analyzed",
        "analysis": {"pH": 6.5, "moisture": 70.0, "ignitionLoss": 15.0,
                     "Pb": 0.004, "As": 0.002, "Cd": 0.0008, "Cr6": 0.008,
                     "Hg": 0.00008, "Se": 0.002, "F": 0.25, "B": 0.2},
        "notes": "冬季搬入分。含水率高め。",
    },
]


def seed_suppliers() -> dict[str, str]:
    """Create suppliers. Returns {name: id} mapping."""
    print("\n=== Suppliers (仕入先) ===")
    mapping = {}
    for s in SUPPLIERS:
        resp = post("/api/v1/suppliers", s)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (id={resp['id'][:8]}...)")
    return mapping


def seed_solidification_materials() -> dict[str, str]:
    """Create solidification materials. Returns {name: id} mapping."""
    print("\n=== Solidification Materials (固化材) ===")
    mapping = {}
    for m in SOLID_MATERIALS:
        resp = post("/api/v1/solidification-materials", m)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (id={resp['id'][:8]}...)")
    return mapping


def seed_suppressants() -> dict[str, str]:
    """Create leaching suppressants. Returns {name: id} mapping."""
    print("\n=== Leaching Suppressants (溶出抑制剤) ===")
    mapping = {}
    for s in SUPPRESSANTS:
        resp = post("/api/v1/leaching-suppressants", s)
        if resp:
            mapping[resp["name"]] = resp["id"]
            print(f"  OK: {resp['name']} (id={resp['id'][:8]}...)")
    return mapping


def seed_waste_records():
    """Create waste records."""
    print("\n=== Waste Records (搬入記録) ===")
    for w in WASTE_RECORDS:
        resp = post("/api/waste/records", w)
        if resp:
            rid = resp.get("id", "?")[:8]
            print(f"  OK: {w['source']} / {w['wasteType']} / {w['weight']}t (id={rid}...)")


def seed_recipes(solid_ids: dict[str, str], supp_ids: dict[str, str]):
    """Create recipes with details referencing material IDs."""
    print("\n=== Recipes (配合レシピ) ===")

    solid_list = list(solid_ids.values())
    supp_list = list(supp_ids.values())

    if len(solid_list) < 2 or len(supp_list) < 1:
        print("  SKIP: Not enough materials created for recipes")
        return

    recipes = [
        {
            "name": "汚泥標準配合A",
            "waste_type": "汚泥（一般）",
            "target_strength": 200.0,
            "status": "active",
            "notes": "汚泥（一般）向け標準配合。実績多数。",
            "details": [
                {"material_id": solid_list[0], "material_type": "solidification",
                 "addition_rate": 120.0, "order_index": 1, "notes": "高炉セメント 120kg/t"},
                {"material_id": supp_list[0], "material_type": "suppressant",
                 "addition_rate": 10.0, "order_index": 2, "notes": "鉛キレート剤 10kg/t"},
            ],
        },
        {
            "name": "焼却灰高強度配合B",
            "waste_type": "焼却灰",
            "target_strength": 500.0,
            "status": "active",
            "notes": "焼却灰向け。高強度が必要なケース。",
            "details": [
                {"material_id": solid_list[3] if len(solid_list) > 3 else solid_list[0],
                 "material_type": "solidification",
                 "addition_rate": 200.0, "order_index": 1, "notes": "特殊固化材 200kg/t"},
                {"material_id": solid_list[1], "material_type": "solidification",
                 "addition_rate": 80.0, "order_index": 2, "notes": "生石灰 80kg/t（含水率低減）"},
                {"material_id": supp_list[2] if len(supp_list) > 2 else supp_list[0],
                 "material_type": "suppressant",
                 "addition_rate": 25.0, "order_index": 3, "notes": "複合型抑制剤 25kg/t"},
            ],
        },
        {
            "name": "鉱さい試験配合C（ドラフト）",
            "waste_type": "鉱さい",
            "target_strength": 350.0,
            "status": "draft",
            "notes": "試験中。Cr6対策を強化した配合案。",
            "details": [
                {"material_id": solid_list[2] if len(solid_list) > 2 else solid_list[0],
                 "material_type": "solidification",
                 "addition_rate": 150.0, "order_index": 1, "notes": "マグネシア系 150kg/t"},
                {"material_id": supp_list[1] if len(supp_list) > 1 else supp_list[0],
                 "material_type": "suppressant",
                 "addition_rate": 35.0, "order_index": 2, "notes": "六価クロム還元剤 35kg/t"},
            ],
        },
    ]

    for r in recipes:
        resp = post("/api/v1/recipes", r)
        if resp:
            n_details = len(resp.get("details", []))
            print(f"  OK: {resp['name']} ({resp['status']}, {n_details} details)")


def main():
    # Check backend is reachable
    print("Checking backend connectivity...")
    try:
        health = get("/health")
        if not health:
            print("ERROR: Backend not responding on http://localhost:8000")
            sys.exit(1)
        print(f"Backend status: {health.get('status', 'unknown')}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to http://localhost:8000")
        print("Start the backend first: python -m uvicorn src.main:app --port 8000 --reload")
        sys.exit(1)

    # Seed data
    supplier_ids = seed_suppliers()
    solid_ids = seed_solidification_materials()
    supp_ids = seed_suppressants()
    seed_waste_records()
    seed_recipes(solid_ids, supp_ids)

    # Summary
    print("\n" + "=" * 50)
    print("Seed data creation complete!")
    print(f"  Suppliers:       {len(supplier_ids)}")
    print(f"  Solid Materials: {len(solid_ids)}")
    print(f"  Suppressants:    {len(supp_ids)}")
    print(f"  Waste Records:   {len(WASTE_RECORDS)}")
    print(f"  Recipes:         3")
    print("=" * 50)


if __name__ == "__main__":
    main()
