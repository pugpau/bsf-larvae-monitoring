"""End-to-end test: complete formulation workflow via API.

Flow: 搬入記録作成 → AI推薦 → 承認 → 適用 → 溶出検証(合格) → WasteRecord完了確認
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@pytest.fixture
async def api_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session, engine
        await session.rollback()
    await engine.dispose()


@pytest.fixture
async def client(api_session):
    session, engine = api_session
    from src.main import app
    from src.database.postgresql import get_async_session

    async def override():
        yield session

    app.dependency_overrides[get_async_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestFullFormulationWorkflowE2E:
    """Complete happy-path: create waste → recommend → accept → apply → verify → completed."""

    @pytest.mark.asyncio
    async def test_full_workflow_happy_path(self, client):
        # ── Step 1: 搬入記録作成 (分析データ付き) ──
        waste_data = {
            "source": "E2Eテスト業者",
            "deliveryDate": "2026-03-15",
            "wasteType": "汚泥（一般）",
            "weight": 15.0,
            "weightUnit": "t",
            "status": "pending",
            "analysis": {
                "pH": 8.5,
                "moisture": 35.0,
                "ignitionLoss": 12.0,
                "Pb": 0.008,
                "As": 0.003,
                "Cd": 0.001,
                "Cr6": 0.02,
                "Hg": 0.0002,
                "Se": 0.004,
                "F": 0.4,
                "B": 0.3,
            },
        }
        r = await client.post("/api/waste/records", json=waste_data)
        assert r.status_code == 201
        waste = r.json()
        waste_id = waste["id"]

        # ── Step 2: AI推薦 ──
        r = await client.post("/api/v1/formulations/recommend", json={
            "waste_record_id": waste_id,
            "top_k": 3,
        })
        assert r.status_code == 200
        recommend = r.json()
        assert len(recommend["candidates"]) >= 1
        candidate = recommend["candidates"][0]
        formulation_id = candidate["id"]
        assert candidate["status"] == "proposed"
        assert candidate["waste_record_id"] == waste_id

        # ── Step 3: 承認 ──
        r = await client.post(f"/api/v1/formulations/{formulation_id}/accept")
        assert r.status_code == 200
        accepted = r.json()
        assert accepted["status"] == "accepted"

        # ── Step 4: 適用 (実績値入力) ──
        r = await client.post(f"/api/v1/formulations/{formulation_id}/apply", json={
            "status": "applied",
            "actual_formulation": {
                "solidifierType": "普通ポルトランドセメント",
                "solidifierAmount": 180.0,
                "solidifierUnit": "kg/t",
            },
            "actual_cost": 3200.0,
        })
        assert r.status_code == 200
        applied = r.json()
        assert applied["status"] == "applied"
        assert applied["actual_cost"] == 3200.0

        # WasteRecord が formulated に遷移していること
        r = await client.get(f"/api/waste/records/{waste_id}")
        assert r.status_code == 200
        waste_mid = r.json()
        assert waste_mid["status"] == "formulated"
        assert waste_mid["formulation"] is not None

        # ── Step 5: 溶出検証 (合格) ──
        r = await client.post(f"/api/v1/formulations/{formulation_id}/verify", json={
            "status": "verified",
            "elution_result": {
                "Pb": 0.003,
                "As": 0.001,
                "Cd": 0.0005,
                "Cr6": 0.008,
                "Hg": 0.0001,
                "Se": 0.002,
                "F": 0.2,
                "B": 0.15,
            },
            "elution_passed": True,
            "notes": "E2Eテスト: 全金属基準値以下",
        })
        assert r.status_code == 200
        verified = r.json()
        assert verified["status"] == "verified"
        assert verified["elution_passed"] is True

        # ── Step 6: WasteRecord が completed に遷移 ──
        r = await client.get(f"/api/waste/records/{waste_id}")
        assert r.status_code == 200
        waste_final = r.json()
        assert waste_final["status"] == "completed"
        assert waste_final["elutionResult"] is not None

    @pytest.mark.asyncio
    async def test_workflow_reject_path(self, client):
        """Reject path: create waste → recommend → reject."""
        waste_data = {
            "source": "E2E却下テスト",
            "deliveryDate": "2026-03-16",
            "wasteType": "汚泥（有害）",
            "weight": 5.0,
            "weightUnit": "t",
            "status": "pending",
            "analysis": {"pH": 6.0, "moisture": 50.0, "Pb": 0.015, "As": 0.008},
        }
        r = await client.post("/api/waste/records", json=waste_data)
        assert r.status_code == 201
        waste_id = r.json()["id"]

        # Recommend
        r = await client.post("/api/v1/formulations/recommend", json={
            "waste_record_id": waste_id,
            "top_k": 2,
        })
        assert r.status_code == 200
        candidate_id = r.json()["candidates"][0]["id"]

        # Reject with notes
        r = await client.post(f"/api/v1/formulations/{candidate_id}/reject", json={
            "status": "rejected",
            "notes": "コスト超過のため却下",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"
        assert r.json()["notes"] == "コスト超過のため却下"

    @pytest.mark.asyncio
    async def test_workflow_verify_fail_path(self, client):
        """Fail path: apply → verify(failed) → WasteRecord status = failed."""
        waste_data = {
            "source": "E2E不合格テスト",
            "deliveryDate": "2026-03-17",
            "wasteType": "汚泥（一般）",
            "weight": 8.0,
            "weightUnit": "t",
            "status": "pending",
            "analysis": {"pH": 7.5, "moisture": 45.0, "Pb": 0.01, "As": 0.005},
        }
        r = await client.post("/api/waste/records", json=waste_data)
        assert r.status_code == 201
        waste_id = r.json()["id"]

        # Create manual formulation
        r = await client.post("/api/v1/formulations", json={
            "waste_record_id": waste_id,
            "source_type": "manual",
            "planned_formulation": {"solidifierAmount": 100.0},
        })
        assert r.status_code == 201
        fid = r.json()["id"]

        # Accept → Apply → Verify (failed)
        await client.post(f"/api/v1/formulations/{fid}/accept")
        await client.post(f"/api/v1/formulations/{fid}/apply")
        r = await client.post(f"/api/v1/formulations/{fid}/verify", json={
            "status": "verified",
            "elution_result": {"Pb": 0.05},
            "elution_passed": False,
        })
        assert r.status_code == 200
        assert r.json()["elution_passed"] is False

        # WasteRecord should be failed
        r = await client.get(f"/api/waste/records/{waste_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "failed"

    @pytest.mark.asyncio
    async def test_recommend_no_analysis_blocked(self, client):
        """Recommend is blocked when waste record has no analysis."""
        waste_data = {
            "source": "E2E分析なし",
            "deliveryDate": "2026-03-18",
            "wasteType": "がれき類",
            "weight": 20.0,
            "weightUnit": "t",
            "status": "pending",
        }
        r = await client.post("/api/waste/records", json=waste_data)
        assert r.status_code == 201
        waste_id = r.json()["id"]

        r = await client.post("/api/v1/formulations/recommend", json={
            "waste_record_id": waste_id,
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_transition_blocked(self, client):
        """Invalid status transitions are rejected."""
        waste_data = {
            "source": "E2E遷移テスト",
            "deliveryDate": "2026-03-19",
            "wasteType": "汚泥（一般）",
            "weight": 10.0,
            "weightUnit": "t",
            "status": "pending",
            "analysis": {"pH": 7.0, "moisture": 40.0, "Pb": 0.005},
        }
        r = await client.post("/api/waste/records", json=waste_data)
        assert r.status_code == 201
        waste_id = r.json()["id"]

        r = await client.post("/api/v1/formulations", json={
            "waste_record_id": waste_id,
            "source_type": "manual",
            "planned_formulation": {"solidifierAmount": 150.0},
        })
        assert r.status_code == 201
        fid = r.json()["id"]

        # proposed → verify is invalid (must go through accepted → applied first)
        r = await client.post(f"/api/v1/formulations/{fid}/verify", json={
            "status": "verified",
            "elution_result": {"Pb": 0.001},
            "elution_passed": True,
        })
        assert r.status_code == 400

        # proposed → apply is invalid (must accept first)
        r = await client.post(f"/api/v1/formulations/{fid}/apply")
        assert r.status_code == 400
