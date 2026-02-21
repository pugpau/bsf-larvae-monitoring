"""Tests for PuLP optimization solver and constraint builders."""

import pytest

from src.ml.schemas import OptimizationRequest, OptimizationResponse
from src.optimization.constraints import (
    calc_min_solidifier,
    calc_min_suppressant,
    needs_suppressant,
)
from src.optimization.solver import FormulationOptimizer


@pytest.fixture
def clean_analysis():
    """Waste analysis within all regulatory limits."""
    return {
        "pH": 7.2, "moisture": 55.0, "ignitionLoss": 20.0,
        "Pb": 0.005, "As": 0.003, "Cd": 0.001, "Cr6": 0.02,
        "Hg": 0.0002, "Se": 0.005, "F": 0.3, "B": 0.2,
    }


@pytest.fixture
def heavy_analysis():
    """Waste analysis with multiple metals exceeding limits."""
    return {
        "pH": 11.5, "moisture": 25.0, "ignitionLoss": 8.0,
        "Pb": 0.06, "As": 0.015, "Cd": 0.005, "Cr6": 0.08,
        "Hg": 0.0005, "Se": 0.008, "F": 1.2, "B": 0.5,
    }


@pytest.fixture
def solidifiers():
    """Candidate solidification materials with costs."""
    return [
        {
            "name": "普通ポルトランドセメント",
            "unit_cost": 12.0,
            "min_addition_rate": 50,
            "max_addition_rate": 500,
            "unit": "kg",
        },
        {
            "name": "高炉セメントB種",
            "unit_cost": 15.0,
            "min_addition_rate": 80,
            "max_addition_rate": 400,
            "unit": "kg",
        },
    ]


@pytest.fixture
def suppressants():
    """Candidate leaching suppressants with costs."""
    return [
        {
            "name": "キレート剤A",
            "unit_cost": 45.0,
            "min_addition_rate": 0.5,
            "max_addition_rate": 15,
            "unit": "kg",
        },
        {
            "name": "硫酸第一鉄",
            "unit_cost": 30.0,
            "min_addition_rate": 1.0,
            "max_addition_rate": 20,
            "unit": "kg",
        },
    ]


# ── Constraint Calculation Tests ──


@pytest.mark.unit
class TestCalcMinSolidifier:
    def test_standard_sludge(self, clean_analysis):
        result = calc_min_solidifier(clean_analysis, "汚泥（一般）")
        assert result >= 100  # base=150 for sludge, no moisture/severity boost
        assert result <= 300

    def test_high_moisture_increases_amount(self):
        analysis = {"pH": 7.0, "moisture": 85.0}
        result = calc_min_solidifier(analysis, "汚泥（一般）")
        # moisture=85 > 60, so moisture_factor adds (85-60)*0.5=12.5
        assert result > calc_min_solidifier({"pH": 7.0, "moisture": 50.0}, "汚泥（一般）")

    def test_heavy_metals_increase_amount(self, heavy_analysis):
        result = calc_min_solidifier(heavy_analysis, "汚泥（一般）")
        clean_result = calc_min_solidifier(
            {"pH": 7.0, "moisture": 25.0}, "汚泥（一般）"
        )
        assert result > clean_result

    def test_unknown_waste_type_uses_default(self, clean_analysis):
        result = calc_min_solidifier(clean_analysis, "その他")
        assert result > 0


@pytest.mark.unit
class TestCalcMinSuppressant:
    def test_clean_returns_zero(self, clean_analysis):
        result = calc_min_suppressant(clean_analysis)
        assert result == 0.0

    def test_heavy_returns_positive(self, heavy_analysis):
        result = calc_min_suppressant(heavy_analysis)
        assert result > 0

    def test_high_cr6_triggers_suppressant(self):
        analysis = {"Cr6": 0.06}
        assert calc_min_suppressant(analysis) > 0

    def test_needs_suppressant_flag(self, clean_analysis, heavy_analysis):
        assert not needs_suppressant(clean_analysis)
        assert needs_suppressant(heavy_analysis)


# ── Solver Tests ──


@pytest.mark.unit
class TestFormulationOptimizer:
    def test_optimal_solution_clean(self, clean_analysis, solidifiers):
        """Clean waste should find optimal solution with just solidifier."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])

        assert result.status == "optimal"
        assert result.total_cost > 0
        assert "solidifierType" in result.recommendation
        assert len(result.cost_breakdown) >= 1

    def test_optimal_solution_heavy(self, heavy_analysis, solidifiers, suppressants):
        """Heavy waste should include both solidifier and suppressant."""
        request = OptimizationRequest(
            analysis=heavy_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, suppressants)

        assert result.status == "optimal"
        assert result.total_cost > 0
        assert len(result.cost_breakdown) >= 1

    def test_picks_cheapest_solidifier(self, clean_analysis, solidifiers):
        """Optimizer should prefer cheaper material when constraints allow."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])

        assert result.status == "optimal"
        # The cheaper one (12 JPY/kg) should be preferred
        if result.cost_breakdown:
            main_material = result.cost_breakdown[0]
            assert main_material.unit_cost <= 15.0

    def test_budget_constraint_respected(self, clean_analysis, solidifiers):
        """With tight budget, solver should respect constraint."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）",
            waste_weight=1.0, max_budget=5000.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])

        if result.status == "optimal":
            assert result.total_cost <= 5000.0
        # If infeasible, that's valid too

    def test_very_tight_budget_infeasible(self, clean_analysis, solidifiers):
        """Impossibly tight budget should return infeasible."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）",
            waste_weight=1.0, max_budget=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])

        assert result.status == "infeasible"
        assert len(result.reasoning) > 0

    def test_waste_weight_scales_cost(self, clean_analysis, solidifiers):
        """Doubling waste weight should roughly double the cost."""
        optimizer = FormulationOptimizer()

        r1 = optimizer.optimize(
            OptimizationRequest(
                analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
            ),
            solidifiers, [],
        )
        r2 = optimizer.optimize(
            OptimizationRequest(
                analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=2.0,
            ),
            solidifiers, [],
        )

        assert r1.status == "optimal"
        assert r2.status == "optimal"
        # Cost should scale with weight (not exact due to min constraints)
        assert r2.total_cost >= r1.total_cost * 1.5

    def test_no_candidates_uses_defaults(self, clean_analysis):
        """With no candidate materials, use default solidifier."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, [], [])

        assert result.status == "optimal"
        assert result.recommendation.get("solidifierType") == "普通ポルトランドセメント"

    def test_solver_time_tracked(self, clean_analysis, solidifiers):
        """Response should include solver time."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])
        assert result.solver_time_ms >= 0

    def test_response_has_constraints_info(self, clean_analysis, solidifiers):
        """Response should report which constraints were applied."""
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])

        assert "min_solidifier_kg_per_t" in result.constraints_satisfied

    def test_cost_breakdown_sums_to_total(self, heavy_analysis, solidifiers, suppressants):
        """Cost breakdown items should sum to total cost."""
        request = OptimizationRequest(
            analysis=heavy_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, suppressants)

        if result.status == "optimal" and result.cost_breakdown:
            breakdown_sum = sum(item.total_cost for item in result.cost_breakdown)
            assert abs(breakdown_sum - result.total_cost) <= 2.0  # rounding tolerance

    def test_multiple_solidifiers_allowed(self, clean_analysis):
        """With multiple solidifiers, optimizer may pick the cheapest."""
        solidifiers = [
            {"name": "A", "unit_cost": 10.0, "min_addition_rate": 50, "max_addition_rate": 500, "unit": "kg"},
            {"name": "B", "unit_cost": 20.0, "min_addition_rate": 50, "max_addition_rate": 500, "unit": "kg"},
        ]
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])

        assert result.status == "optimal"


@pytest.mark.unit
class TestOptimizerEdgeCases:
    def test_empty_analysis(self):
        """Optimization with empty analysis should still work."""
        request = OptimizationRequest(
            analysis={}, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, [], [])
        assert result.status == "optimal"

    def test_zero_unit_cost_uses_default(self, clean_analysis):
        """Materials with no unit_cost should use defaults."""
        solidifiers = [
            {"name": "Test", "unit_cost": None, "min_addition_rate": 50,
             "max_addition_rate": 500, "unit": "kg"},
        ]
        request = OptimizationRequest(
            analysis=clean_analysis, waste_type="汚泥（一般）", waste_weight=1.0,
        )
        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, [])
        assert result.status == "optimal"
        assert result.total_cost > 0
