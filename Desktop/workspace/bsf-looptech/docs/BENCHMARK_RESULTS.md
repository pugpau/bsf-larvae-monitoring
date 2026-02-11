# Phase 2-6: LLM Benchmark Results

**Generated**: 2026-02-11T11:17:31.495200+00:00
**LLM API**: `http://127.0.0.1:1234/v1`
**Model**: `openai/gpt-oss-20b`

---

## 1. Connection Test

**Status**: OK

Available models:
- `openai/gpt-oss-20b`
- `openai/gpt-oss-20b:2`
- `openai/gpt-oss-20b:3`
- `text-embedding-nomic-embed-text-v1.5`
- `plamo-2-translate`
---

## 2. Inference Speed

| Prompt | Avg Latency | P95 Latency | Avg tok/s | Errors |
|--------|-------------|-------------|-----------|--------|
| short (~50 tokens) | 5.18s | 5.42s | 48.0 | 0 |
| medium (~200 tokens) | 5.52s | 5.61s | 46.1 | 0 |
| long (~500 tokens) | 5.69s | 5.80s | 44.4 | 0 |

Runs per prompt: 3
---

## 3. LangChain Integration

**Status**: OK (2.60s)

Response preview:
> BSF幼虫の最適飼育温度は **
---

## 4. Embedding Endpoint

**Status**: OK
**Model**: `text-embedding-nomic-embed-text-v1.5`
**Dimension**: 768
---

## 5. Memory Usage (Mac mini 32GB)

| Process | RSS |
|---------|-----|
| LM Studio | 24608 MB |
| PostgreSQL | 29 MB |
| Python/FastAPI | 0 MB |

- **Total measured**: 24637 MB
- **Remaining estimate**: 8131 MB / 32768 MB


---

## Raw Results (JSON)

```json
{
  "timestamp": "2026-02-11T11:17:31.495200+00:00",
  "llm_base_url": "http://127.0.0.1:1234/v1",
  "llm_model": "openai/gpt-oss-20b",
  "models": {
    "status": "ok",
    "models": [
      "openai/gpt-oss-20b",
      "openai/gpt-oss-20b:2",
      "openai/gpt-oss-20b:3",
      "text-embedding-nomic-embed-text-v1.5",
      "plamo-2-translate"
    ]
  },
  "inference": {
    "short (~50 tokens)": {
      "avg_latency": 5.184994500001873,
      "p95_latency": 5.423918958003924,
      "avg_tokens_per_sec": 47.99699033932213,
      "runs": 3,
      "errors": 0
    },
    "medium (~200 tokens)": {
      "avg_latency": 5.5230627223330275,
      "p95_latency": 5.610395374998916,
      "avg_tokens_per_sec": 46.11633448683914,
      "runs": 3,
      "errors": 0
    },
    "long (~500 tokens)": {
      "avg_latency": 5.690241055669806,
      "p95_latency": 5.795037709001917,
      "avg_tokens_per_sec": 44.40305566457798,
      "runs": 3,
      "errors": 0
    }
  },
  "langchain": {
    "status": "ok",
    "latency": 2.5962361249985406,
    "response_preview": "BSF幼虫の最適飼育温度は **"
  },
  "embedding": {
    "status": "ok",
    "model": "text-embedding-nomic-embed-text-v1.5",
    "dimension": 768
  },
  "memory": {
    "LM Studio": "24608 MB",
    "PostgreSQL": "29 MB",
    "Python/FastAPI": "0 MB",
    "total_measured": "24637 MB",
    "remaining_estimate": "8131 MB / 32768 MB"
  }
}
```
