"""
LLM ベンチマークスクリプト (Phase 2-6)

LM Studio OpenAI 互換 API に対してベンチマークを実行し、
結果を docs/BENCHMARK_RESULTS.md に出力する。

テスト項目:
1. 接続テスト (/v1/models)
2. 推論速度測定 (短文/中文/長文, 各3回)
3. LangChain 統合テスト
4. Embedding エンドポイント確認
5. メモリ使用量スナップショット

Usage:
    python scripts/benchmark_llm.py
"""

import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)

LLM_BASE_URL: Final[str] = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
LLM_MODEL: Final[str] = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
DOCS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "docs"
OUTPUT_FILE: Final[Path] = DOCS_DIR / "BENCHMARK_RESULTS.md"
RUNS_PER_PROMPT: Final[int] = 3


def main() -> None:
    results: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
    }
    sections: list[str] = []

    print("=" * 60)
    print("LLM Benchmark Script (Phase 2-6)")
    print(f"Target: {LLM_BASE_URL}")
    print(f"Model:  {LLM_MODEL}")
    print("=" * 60)

    # --- 1. Connection test ---
    print("\n[1/5] Connection test (/v1/models)...")
    models_data = _test_connection()
    if models_data is None:
        print("  FAILED — LM Studio is not reachable. Aborting.")
        _write_failure_report(sections)
        return
    results["models"] = models_data
    sections.append(_format_connection_section(models_data))

    # --- 2. Inference speed ---
    print("\n[2/5] Inference speed measurement...")
    prompts = {
        "short (~50 tokens)": "BSFの幼虫飼育に最適な温度範囲を教えてください。",
        "medium (~200 tokens)": (
            "BSF（ブラックソルジャーフライ）の幼虫を使った有機廃棄物処理システムにおいて、"
            "基材の配合比率を最適化するための主要なパラメータと、"
            "それぞれが処理効率に与える影響について詳しく説明してください。"
        ),
        "long (~500 tokens)": (
            "BSF幼虫による有機廃棄物処理プラントの設計において考慮すべき要素を包括的に説明してください。"
            "具体的には、(1) 基材の前処理方法と配合最適化、(2) 飼育環境の温湿度管理、"
            "(3) 幼虫の成長ステージ別の給餌戦略、(4) 処理残渣の品質管理と溶出試験基準、"
            "(5) スケールアップ時の設備設計とコスト最適化について、"
            "それぞれの技術的課題と推奨されるアプローチを述べてください。"
        ),
    }
    speed_results = _benchmark_inference(prompts)
    results["inference"] = speed_results
    sections.append(_format_inference_section(speed_results))

    # --- 3. LangChain integration ---
    print("\n[3/5] LangChain integration test...")
    lc_result = _test_langchain()
    results["langchain"] = lc_result
    sections.append(_format_langchain_section(lc_result))

    # --- 4. Embedding test ---
    print("\n[4/5] Embedding endpoint test...")
    emb_result = _test_embedding()
    results["embedding"] = emb_result
    sections.append(_format_embedding_section(emb_result))

    # --- 5. Memory snapshot ---
    print("\n[5/5] Memory usage snapshot...")
    mem_result = _memory_snapshot()
    results["memory"] = mem_result
    sections.append(_format_memory_section(mem_result))

    # --- Write report ---
    _write_report(sections, results)
    print(f"\nReport written to: {OUTPUT_FILE}")
    print("=" * 60)


# ──────────────────────────────────────────
# Test functions
# ──────────────────────────────────────────


def _test_connection() -> dict[str, Any] | None:
    try:
        resp = httpx.get(f"{LLM_BASE_URL}/models", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  OK — {len(models)} model(s) available:")
        for m in models:
            print(f"    - {m.get('id', 'unknown')}")
        return {"status": "ok", "models": [m.get("id") for m in models]}
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def _benchmark_inference(prompts: dict[str, str]) -> dict[str, Any]:
    all_results: dict[str, Any] = {}

    for label, prompt in prompts.items():
        print(f"\n  [{label}] — {RUNS_PER_PROMPT} runs")
        latencies: list[float] = []
        token_rates: list[float] = []

        for i in range(RUNS_PER_PROMPT):
            t0 = time.monotonic()
            try:
                resp = httpx.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    json={
                        "model": LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 256,
                        "temperature": 0.7,
                    },
                    timeout=120.0,
                )
                resp.raise_for_status()
                elapsed = time.monotonic() - t0
                data = resp.json()

                usage = data.get("usage", {})
                completion_tokens = usage.get("completion_tokens", 0)
                tps = completion_tokens / elapsed if elapsed > 0 else 0

                latencies.append(elapsed)
                token_rates.append(tps)
                print(
                    f"    run {i + 1}: {elapsed:.2f}s, "
                    f"{completion_tokens} tokens, "
                    f"{tps:.1f} tok/s"
                )
            except Exception as e:
                latencies.append(-1)
                token_rates.append(0)
                print(f"    run {i + 1}: ERROR — {e}")

        valid_latencies = [x for x in latencies if x > 0]
        valid_rates = [x for x in token_rates if x > 0]

        all_results[label] = {
            "avg_latency": statistics.mean(valid_latencies) if valid_latencies else -1,
            "p95_latency": (
                sorted(valid_latencies)[int(len(valid_latencies) * 0.95)]
                if valid_latencies
                else -1
            ),
            "avg_tokens_per_sec": statistics.mean(valid_rates) if valid_rates else 0,
            "runs": RUNS_PER_PROMPT,
            "errors": sum(1 for x in latencies if x < 0),
        }

    return all_results


def _test_langchain() -> dict[str, Any]:
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            base_url=LLM_BASE_URL,
            api_key="not-needed",
            model=LLM_MODEL,
            temperature=0.3,
            max_tokens=128,
        )
        prompt = ChatPromptTemplate.from_messages(
            [("user", "BSF幼虫の最適飼育温度は？簡潔に答えてください。")]
        )
        chain = prompt | llm | StrOutputParser()

        t0 = time.monotonic()
        result = chain.invoke({})
        elapsed = time.monotonic() - t0

        print(f"  OK ({elapsed:.2f}s) — response: {result[:80]}...")
        return {"status": "ok", "latency": elapsed, "response_preview": result[:200]}
    except ImportError as e:
        msg = f"Missing dependency: {e}"
        print(f"  SKIP — {msg}")
        return {"status": "skip", "reason": msg}
    except Exception as e:
        print(f"  ERROR — {e}")
        return {"status": "error", "reason": str(e)}


def _test_embedding() -> dict[str, Any]:
    # Try dedicated embedding model first, then fallback to LLM model
    embedding_models = [
        "text-embedding-nomic-embed-text-v1.5",
        LLM_MODEL,
    ]
    for model_name in embedding_models:
        result = _try_embedding(model_name)
        if result["status"] == "ok":
            return result
    return result  # Return last attempt result


def _try_embedding(model_name: str) -> dict[str, Any]:
    try:
        resp = httpx.post(
            f"{LLM_BASE_URL}/embeddings",
            json={
                "model": model_name,
                "input": "BSF幼虫の有機廃棄物処理",
            },
            timeout=30.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            emb = data.get("data", [{}])[0].get("embedding", [])
            dim = len(emb)
            print(f"  OK — model={model_name}, dim={dim}")
            return {"status": "ok", "model": model_name, "dimension": dim}
        else:
            msg = f"HTTP {resp.status_code} for {model_name}: {resp.text[:200]}"
            print(f"  NOT SUPPORTED — {msg}")
            return {
                "status": "not_supported",
                "reason": msg,
                "fallback": "sentence-transformers (all-MiniLM-L6-v2, dim=384)",
            }
    except Exception as e:
        print(f"  ERROR — {e}")
        return {
            "status": "error",
            "reason": str(e),
            "fallback": "sentence-transformers (all-MiniLM-L6-v2, dim=384)",
        }


def _memory_snapshot() -> dict[str, Any]:
    """Capture RSS memory for key processes via ps."""
    processes = {
        "LM Studio": "LM Studio",
        "PostgreSQL": "postgres",
        "Python/FastAPI": "uvicorn",
    }
    snapshot: dict[str, Any] = {}
    total_mb = 0.0

    for label, pattern in processes.items():
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            rss_kb = 0
            for line in result.stdout.splitlines():
                if pattern.lower() in line.lower():
                    parts = line.split()
                    if len(parts) >= 6:
                        try:
                            rss_kb += int(parts[5])
                        except ValueError:
                            pass
            rss_mb = rss_kb / 1024
            snapshot[label] = f"{rss_mb:.0f} MB"
            total_mb += rss_mb
            print(f"  {label}: {rss_mb:.0f} MB")
        except Exception as e:
            snapshot[label] = f"error: {e}"
            print(f"  {label}: error — {e}")

    total_system_mb = 32 * 1024  # Mac mini 32GB
    remaining_mb = total_system_mb - total_mb
    snapshot["total_measured"] = f"{total_mb:.0f} MB"
    snapshot["remaining_estimate"] = f"{remaining_mb:.0f} MB / {total_system_mb} MB"
    print(f"  Total measured: {total_mb:.0f} MB, Remaining: ~{remaining_mb:.0f} MB")

    return snapshot


# ──────────────────────────────────────────
# Report formatting
# ──────────────────────────────────────────


def _format_connection_section(data: dict[str, Any]) -> str:
    models_list = "\n".join(f"- `{m}`" for m in data.get("models", []))
    return f"""## 1. Connection Test

**Status**: {data['status'].upper()}

Available models:
{models_list}
"""


def _format_inference_section(data: dict[str, Any]) -> str:
    rows = []
    for label, metrics in data.items():
        avg_lat = metrics["avg_latency"]
        p95_lat = metrics["p95_latency"]
        avg_tps = metrics["avg_tokens_per_sec"]
        errors = metrics["errors"]
        rows.append(
            f"| {label} | {avg_lat:.2f}s | {p95_lat:.2f}s | {avg_tps:.1f} | {errors} |"
        )
    rows_str = "\n".join(rows)
    return f"""## 2. Inference Speed

| Prompt | Avg Latency | P95 Latency | Avg tok/s | Errors |
|--------|-------------|-------------|-----------|--------|
{rows_str}

Runs per prompt: {RUNS_PER_PROMPT}
"""


def _format_langchain_section(data: dict[str, Any]) -> str:
    status = data["status"].upper()
    if data["status"] == "ok":
        return f"""## 3. LangChain Integration

**Status**: {status} ({data['latency']:.2f}s)

Response preview:
> {data.get('response_preview', 'N/A')}
"""
    return f"""## 3. LangChain Integration

**Status**: {status}
**Reason**: {data.get('reason', 'N/A')}
"""


def _format_embedding_section(data: dict[str, Any]) -> str:
    status = data["status"].upper()
    if data["status"] == "ok":
        return f"""## 4. Embedding Endpoint

**Status**: {status}
**Model**: `{data.get('model', 'N/A')}`
**Dimension**: {data['dimension']}
"""
    fallback = data.get("fallback", "N/A")
    return f"""## 4. Embedding Endpoint

**Status**: {status}
**Reason**: {data.get('reason', 'N/A')}
**Fallback plan**: {fallback}
"""


def _format_memory_section(data: dict[str, Any]) -> str:
    rows = []
    for key, val in data.items():
        if key not in ("total_measured", "remaining_estimate"):
            rows.append(f"| {key} | {val} |")
    rows_str = "\n".join(rows)
    return f"""## 5. Memory Usage (Mac mini 32GB)

| Process | RSS |
|---------|-----|
{rows_str}

- **Total measured**: {data.get('total_measured', 'N/A')}
- **Remaining estimate**: {data.get('remaining_estimate', 'N/A')}
"""


def _write_report(sections: list[str], raw_results: dict[str, Any]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = raw_results["timestamp"]

    content = f"""# Phase 2-6: LLM Benchmark Results

**Generated**: {timestamp}
**LLM API**: `{raw_results['llm_base_url']}`
**Model**: `{raw_results['llm_model']}`

---

{"---\n\n".join(sections)}

---

## Raw Results (JSON)

```json
{json.dumps(raw_results, indent=2, ensure_ascii=False, default=str)}
```
"""
    OUTPUT_FILE.write_text(content, encoding="utf-8")


def _write_failure_report(sections: list[str]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    content = f"""# Phase 2-6: LLM Benchmark Results

**Generated**: {timestamp}
**Status**: FAILED — LM Studio not reachable at `{LLM_BASE_URL}`

Ensure LM Studio is running with a model loaded before running this benchmark.
"""
    OUTPUT_FILE.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
