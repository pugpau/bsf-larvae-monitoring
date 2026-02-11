"""
pgvector 動作確認スクリプト (Phase 2-6)

Docker PostgreSQL に接続し、pgvector 拡張の動作を検証する。
- CREATE EXTENSION vector
- vector 型テーブル作成
- ベクトル INSERT + cosine distance クエリ
- クリーンアップ

Usage:
    python scripts/validate_pgvector.py
"""

import asyncio
import os
import sys
import time
from typing import Final

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg is required. Install with: pip install asyncpg")
    sys.exit(1)

# Default connection parameters (match docker-compose.yml)
DB_HOST: Final[str] = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT: Final[int] = int(os.getenv("POSTGRES_PORT", "5432"))
DB_USER: Final[str] = os.getenv("POSTGRES_USER", "bsf_user")
DB_PASSWORD: Final[str] = os.getenv("POSTGRES_PASSWORD", "bsf_password")
DB_NAME: Final[str] = os.getenv("POSTGRES_DB", "bsf_system")

VECTOR_DIM: Final[int] = 384
TEST_TABLE: Final[str] = "_pgvector_validation_test"


async def run_validation() -> bool:
    """Run pgvector validation steps. Returns True if all pass."""
    results: list[tuple[str, bool, str]] = []

    print("=" * 60)
    print("pgvector Validation Script")
    print("=" * 60)
    print(f"Target: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print()

    conn: asyncpg.Connection | None = None
    try:
        # Step 1: Connect
        print("[1/6] Connecting to PostgreSQL...")
        t0 = time.monotonic()
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        elapsed = time.monotonic() - t0
        version = await conn.fetchval("SELECT version()")
        results.append(("Connection", True, f"{elapsed:.3f}s — {version[:60]}"))
        print(f"  OK ({elapsed:.3f}s)")

        # Step 2: CREATE EXTENSION
        print("[2/6] Creating vector extension...")
        t0 = time.monotonic()
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        elapsed = time.monotonic() - t0

        ext_version = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )
        results.append(("Extension", True, f"vector v{ext_version} ({elapsed:.3f}s)"))
        print(f"  OK — vector v{ext_version}")

        # Step 3: Create test table
        print(f"[3/6] Creating test table ({TEST_TABLE}, dim={VECTOR_DIM})...")
        await conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
        await conn.execute(f"""
            CREATE TABLE {TEST_TABLE} (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector({VECTOR_DIM})
            )
        """)
        results.append(("Table creation", True, f"vector({VECTOR_DIM})"))
        print("  OK")

        # Step 4: Insert sample vectors
        print("[4/6] Inserting sample vectors...")
        samples = [
            ("waste type A — high moisture", _make_vector(VECTOR_DIM, seed=1)),
            ("waste type B — low moisture", _make_vector(VECTOR_DIM, seed=2)),
            ("waste type C — mixed organic", _make_vector(VECTOR_DIM, seed=3)),
        ]
        for content, vec in samples:
            await conn.execute(
                f"INSERT INTO {TEST_TABLE} (content, embedding) VALUES ($1, $2)",
                content,
                vec,
            )
        count = await conn.fetchval(f"SELECT count(*) FROM {TEST_TABLE}")
        results.append(("Insert", True, f"{count} rows"))
        print(f"  OK — {count} rows inserted")

        # Step 5: Cosine distance query
        print("[5/6] Running cosine distance query (<=>)...")
        query_vec = _make_vector(VECTOR_DIM, seed=1)  # Should be closest to sample 1
        t0 = time.monotonic()
        rows = await conn.fetch(
            f"""
            SELECT id, content, embedding <=> $1 AS distance
            FROM {TEST_TABLE}
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_vec,
        )
        elapsed = time.monotonic() - t0
        print(f"  Query time: {elapsed:.3f}s")
        for row in rows:
            print(f"  id={row['id']} distance={row['distance']:.6f} — {row['content']}")

        closest = rows[0]["content"] if rows else "N/A"
        results.append(("Cosine query", True, f"closest='{closest}' ({elapsed:.3f}s)"))

        # Step 6: Cleanup
        print(f"[6/6] Cleaning up ({TEST_TABLE})...")
        await conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
        results.append(("Cleanup", True, "table dropped"))
        print("  OK")

    except Exception as e:
        results.append(("ERROR", False, str(e)))
        print(f"\n  FAILED: {e}")
    finally:
        if conn is not None:
            await conn.close()

    # Summary
    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}: {detail}")

    print()
    if all_pass:
        print("All checks PASSED. pgvector is ready.")
    else:
        print("Some checks FAILED. See above for details.")
    print("=" * 60)
    return all_pass


def _make_vector(dim: int, seed: int = 0) -> str:
    """Generate a deterministic unit-ish vector as a pgvector literal string."""
    import math

    values = []
    for i in range(dim):
        val = math.sin(seed * 1000 + i * 0.1) * 0.5
        values.append(f"{val:.6f}")
    return f"[{','.join(values)}]"


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)
