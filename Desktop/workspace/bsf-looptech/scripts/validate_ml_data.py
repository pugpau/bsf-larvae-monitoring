"""
Production data quality check tool for ML training readiness.

Validates waste records via REST API and produces a JSON report
with PASS/WARN/FAIL verdicts for each quality dimension.

Overall verdict:
  - "production_ready": >=200 records, all checks PASS
  - "practical": >=50 records, no FAIL checks (synthetic augmentation recommended)
  - "insufficient": <50 records or critical failures

Prerequisites:
  - Backend running on localhost:8000

Usage:
  python scripts/validate_ml_data.py
  python scripts/validate_ml_data.py --output report.json
"""

import argparse
import json
import math
import sys
from typing import Any

import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 15.0

# ── ML閾値定義 ──

ML_MIN_RECORDS = 50
ML_PRACTICAL_RECORDS = 200
REQUIRED_WASTE_TYPES = ["汚泥", "焼却灰", "ばいじん", "鉱さい", "廃酸", "廃アルカリ"]
MIN_TYPE_COUNT = 5
ANALYSIS_FIELDS = ["pH", "moisture", "ignitionLoss", "Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B"]
FORMULATION_FIELDS = ["solidifierType", "solidifierAmount"]
ELUTION_FIELDS = ["Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B"]
PASS_RATE_MIN = 0.70
PASS_RATE_MAX = 0.90
OUTLIER_THRESHOLD = 0.05  # 外れ値比率の上限


def get(path: str) -> dict[str, Any]:
    """GET リクエスト送信。"""
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT)
    return r.json() if r.status_code == 200 else {}


def fetch_all_records() -> list[dict[str, Any]]:
    """全レコードをページネーションで取得。"""
    records: list[dict[str, Any]] = []
    offset = 0
    limit = 100

    while True:
        resp = get(f"/api/waste/records?limit={limit}&offset={offset}")
        items = resp.get("items", [])
        if not items:
            break
        records.extend(items)
        if len(items) < limit:
            break
        offset += limit

    return records


def check_record_count(records: list[dict[str, Any]]) -> dict[str, Any]:
    """総レコード数チェック。"""
    count = len(records)
    if count >= ML_PRACTICAL_RECORDS:
        verdict = "PASS"
        message = f"{count} records (>= {ML_PRACTICAL_RECORDS} production_ready threshold)"
    elif count >= ML_MIN_RECORDS:
        verdict = "WARN"
        message = f"{count} records (>= {ML_MIN_RECORDS} minimum, < {ML_PRACTICAL_RECORDS} practical)"
    else:
        verdict = "FAIL"
        message = f"{count} records (< {ML_MIN_RECORDS} minimum threshold)"

    return {"check": "record_count", "verdict": verdict, "count": count, "message": message}


def check_feature_completeness(records: list[dict[str, Any]]) -> dict[str, Any]:
    """特徴量完全性チェック（分析・配合・溶出の各項目）。"""
    total = len(records)
    if total == 0:
        return {
            "check": "feature_completeness",
            "verdict": "FAIL",
            "message": "No records to check",
        }

    analysis_complete = 0
    formulation_complete = 0
    elution_complete = 0
    full_cycle = 0

    for rec in records:
        analysis = rec.get("analysis") or {}
        formulation = rec.get("formulation") or {}
        elution = rec.get("elutionResult") or rec.get("elution_result") or {}

        has_analysis = sum(1 for f in ANALYSIS_FIELDS if analysis.get(f) is not None) >= 4
        has_formulation = all(formulation.get(f) is not None for f in FORMULATION_FIELDS)
        has_elution = sum(1 for f in ELUTION_FIELDS if elution.get(f) is not None) >= 4

        if has_analysis:
            analysis_complete += 1
        if has_formulation:
            formulation_complete += 1
        if has_elution:
            elution_complete += 1
        if has_analysis and has_formulation and has_elution:
            full_cycle += 1

    pct_analysis = analysis_complete / total * 100
    pct_formulation = formulation_complete / total * 100
    pct_elution = elution_complete / total * 100
    pct_full = full_cycle / total * 100

    if pct_full >= 80:
        verdict = "PASS"
    elif pct_full >= 50:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    return {
        "check": "feature_completeness",
        "verdict": verdict,
        "analysis_complete": f"{analysis_complete}/{total} ({pct_analysis:.0f}%)",
        "formulation_complete": f"{formulation_complete}/{total} ({pct_formulation:.0f}%)",
        "elution_complete": f"{elution_complete}/{total} ({pct_elution:.0f}%)",
        "full_cycle": f"{full_cycle}/{total} ({pct_full:.0f}%)",
        "message": f"Full cycle completeness: {pct_full:.0f}%",
    }


def check_waste_type_distribution(records: list[dict[str, Any]]) -> dict[str, Any]:
    """廃棄物種類分布チェック。"""
    type_counts: dict[str, int] = {}
    for rec in records:
        wt = rec.get("wasteType", rec.get("waste_type", "unknown"))
        type_counts[wt] = type_counts.get(wt, 0) + 1

    # 必須種類のうちカウントが十分なもの
    missing_types: list[str] = []
    low_types: list[str] = []
    for required in REQUIRED_WASTE_TYPES:
        # 部分一致も許容（「汚泥（一般）」→「汚泥」）
        matched_count = sum(
            cnt for wt, cnt in type_counts.items()
            if required in wt
        )
        if matched_count == 0:
            missing_types.append(required)
        elif matched_count < MIN_TYPE_COUNT:
            low_types.append(f"{required}({matched_count}件)")

    if not missing_types and not low_types:
        verdict = "PASS"
        message = f"All {len(REQUIRED_WASTE_TYPES)} types represented with >={MIN_TYPE_COUNT} records"
    elif not missing_types:
        verdict = "WARN"
        message = f"Low count types: {', '.join(low_types)}"
    else:
        verdict = "WARN"
        message = f"Missing types: {', '.join(missing_types)}"

    return {
        "check": "waste_type_distribution",
        "verdict": verdict,
        "distribution": type_counts,
        "missing_types": missing_types,
        "low_types": low_types,
        "message": message,
    }


def check_pass_fail_ratio(records: list[dict[str, Any]]) -> dict[str, Any]:
    """合格/不合格比率チェック。"""
    pass_count = 0
    fail_count = 0
    unknown = 0

    for rec in records:
        elution = rec.get("elutionResult") or rec.get("elution_result") or {}
        passed = elution.get("passed")
        if passed is True:
            pass_count += 1
        elif passed is False:
            fail_count += 1
        else:
            unknown += 1

    total_labeled = pass_count + fail_count
    if total_labeled == 0:
        return {
            "check": "pass_fail_ratio",
            "verdict": "FAIL",
            "message": "No labeled records (no elution_result.passed)",
        }

    pass_rate = pass_count / total_labeled

    if PASS_RATE_MIN <= pass_rate <= PASS_RATE_MAX:
        verdict = "PASS"
        message = f"Pass rate {pass_rate:.1%} within ideal range ({PASS_RATE_MIN:.0%}-{PASS_RATE_MAX:.0%})"
    elif 0.5 <= pass_rate <= 0.95:
        verdict = "WARN"
        message = f"Pass rate {pass_rate:.1%} outside ideal range but usable"
    else:
        verdict = "WARN"
        message = f"Pass rate {pass_rate:.1%} significantly imbalanced"

    return {
        "check": "pass_fail_ratio",
        "verdict": verdict,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unknown": unknown,
        "pass_rate": round(pass_rate, 4),
        "message": message,
    }


def check_outliers(records: list[dict[str, Any]]) -> dict[str, Any]:
    """外れ値検出（3x IQR法）。"""
    # 数値フィールドを収集
    field_values: dict[str, list[float]] = {f: [] for f in ANALYSIS_FIELDS}

    for rec in records:
        analysis = rec.get("analysis") or {}
        for field in ANALYSIS_FIELDS:
            val = analysis.get(field)
            if val is not None:
                try:
                    field_values[field].append(float(val))
                except (TypeError, ValueError):
                    pass

    total_values = 0
    outlier_count = 0
    outlier_details: dict[str, int] = {}

    for field, values in field_values.items():
        if len(values) < 10:
            continue

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - 3.0 * iqr
        upper = q3 + 3.0 * iqr

        field_outliers = sum(1 for v in values if v < lower or v > upper)
        if field_outliers > 0:
            outlier_details[field] = field_outliers
        outlier_count += field_outliers
        total_values += n

    outlier_ratio = outlier_count / max(total_values, 1)

    if outlier_ratio < OUTLIER_THRESHOLD:
        verdict = "PASS"
        message = f"Outlier ratio {outlier_ratio:.2%} < {OUTLIER_THRESHOLD:.0%} threshold"
    else:
        verdict = "WARN"
        message = f"Outlier ratio {outlier_ratio:.2%} >= {OUTLIER_THRESHOLD:.0%} threshold"

    return {
        "check": "outlier_detection",
        "verdict": verdict,
        "total_values": total_values,
        "outlier_count": outlier_count,
        "outlier_ratio": round(outlier_ratio, 4),
        "outlier_details": outlier_details,
        "message": message,
    }


def determine_overall_verdict(checks: list[dict[str, Any]], record_count: int) -> str:
    """総合判定を算出。"""
    verdicts = [c["verdict"] for c in checks]

    if "FAIL" in verdicts:
        return "insufficient"
    if record_count >= ML_PRACTICAL_RECORDS and all(v == "PASS" for v in verdicts):
        return "production_ready"
    if record_count >= ML_MIN_RECORDS:
        return "practical"
    return "insufficient"


def main() -> None:
    """データ品質検証を実行しレポートを出力。"""
    parser = argparse.ArgumentParser(description="Validate ML training data quality")
    parser.add_argument("--output", "-o", help="Output JSON report file path")
    args = parser.parse_args()

    print("=" * 60)
    print("ML Data Quality Validator")
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

    # ── データ取得 ──
    print("\nFetching records...")
    records = fetch_all_records()
    print(f"  Total records fetched: {len(records)}")

    # ── チェック実行 ──
    checks = [
        check_record_count(records),
        check_feature_completeness(records),
        check_waste_type_distribution(records),
        check_pass_fail_ratio(records),
        check_outliers(records),
    ]

    overall = determine_overall_verdict(checks, len(records))

    # ── コンソール出力 ──
    print(f"\n{'─' * 60}")
    print("Validation Results:")
    print(f"{'─' * 60}")

    for check in checks:
        verdict = check["verdict"]
        icon = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[verdict]
        print(f"  {icon} {check['check']}: {check['message']}")

    print(f"\n{'─' * 60}")
    verdict_display = {
        "production_ready": "PRODUCTION READY - ML model can operate independently",
        "practical": "PRACTICAL - ML usable with synthetic data augmentation",
        "insufficient": "INSUFFICIENT - More data needed before ML training",
    }
    print(f"  Overall: {overall.upper()} - {verdict_display[overall]}")
    print(f"{'─' * 60}")

    # ── JSONレポート ──
    report = {
        "total_records": len(records),
        "overall_verdict": overall,
        "checks": checks,
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nReport saved to: {args.output}")
    else:
        print(f"\nJSON Report:")
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
