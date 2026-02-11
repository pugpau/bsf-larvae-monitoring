"""
Pytest configuration for BSF-LoopTech waste treatment system.
"""

import os
import sys
import uuid as uuid_module
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test environment variables (set before importing app)
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "LOG_LEVEL": "DEBUG",
    "CORS_ORIGINS": "http://localhost:3000",
    "SKIP_AUTH": "true",
})

# ---------------------------------------------------------------------------
# Patch: SQLAlchemy UUID bind_processor for SQLite compatibility
# Repository methods pass str UUIDs (works natively on PostgreSQL).
# On SQLite the character-based bind_processor calls value.hex which needs
# a uuid.UUID object, so we convert strings before calling .hex.
# ---------------------------------------------------------------------------
from sqlalchemy import types as _sqltypes  # noqa: E402

_orig_uuid_bp = _sqltypes.Uuid.bind_processor


def _patched_uuid_bind_processor(self, dialect):
    character_based_uuid = not dialect.supports_native_uuid or not self.native_uuid
    if character_based_uuid:
        if self.as_uuid:
            def process(value):
                if value is not None:
                    if isinstance(value, str):
                        value = uuid_module.UUID(value)
                    value = value.hex
                return value
            return process
        else:
            def process(value):
                if value is not None:
                    if isinstance(value, uuid_module.UUID):
                        value = str(value)
                    value = value.replace("-", "")
                return value
            return process
    else:
        return None


_sqltypes.Uuid.bind_processor = _patched_uuid_bind_processor

from src.database.postgresql import Base


@pytest.fixture
async def async_session():
    """In-memory SQLite async session for unit tests."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await test_engine.dispose()


@pytest.fixture
def sample_waste_analysis():
    """Typical waste analysis data."""
    return {
        "pH": 7.2, "moisture": 78.5, "ignitionLoss": 32.1,
        "Pb": 0.008, "As": 0.002, "Cd": 0.001, "Cr6": 0.02,
        "Hg": 0.0003, "Se": 0.001, "F": 0.15, "B": 0.08,
    }


@pytest.fixture
def sample_heavy_waste_analysis():
    """Waste analysis with values exceeding regulatory limits."""
    return {
        "pH": 11.8, "moisture": 20.0, "ignitionLoss": 6.5,
        "Pb": 0.065, "As": 0.011, "Cd": 0.0035, "Cr6": 0.10,
        "Hg": 0.0005, "Se": 0.007, "F": 0.95, "B": 0.20,
    }


@pytest.fixture
def sample_formulation():
    """A typical formulation."""
    return {
        "solidifierType": "普通ポルトランドセメント",
        "solidifierAmount": 150,
        "solidifierUnit": "kg/t",
        "suppressorType": "キレート剤A",
        "suppressorAmount": 3.5,
        "suppressorUnit": "kg/t",
    }


@pytest.fixture
def formulated_history(sample_waste_analysis, sample_formulation):
    """List of past formulated records for similarity testing."""
    base = {
        "status": "formulated",
        "analysis": sample_waste_analysis,
        "formulation": sample_formulation,
        "elutionResult": {"passed": True},
    }
    return [
        {**base, "id": f"rec_{i}", "source": f"工場{chr(65+i)}", "deliveryDate": f"2026-01-{10+i:02d}"}
        for i in range(5)
    ]
